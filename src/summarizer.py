"""
Модуль summarizer.py
Взаимодействует с LLM API для генерации описаний страниц.
Поддерживает любые провайдеры с OpenAI-совместимым API (OpenRouter, OpenAI и др.).
"""
import asyncio
import time
from typing import Optional

from openai import AsyncOpenAI
from src.config import Config
from src.models import ProcessedPage
from src.logger import get_logger, log_function_call, log_performance, log_error_with_context

logger = get_logger(__name__)


class ContentSummarizer:
    """
    Класс для генерации описаний веб-страниц с использованием LLM.
    """
    
    def __init__(self, config: Config):
        """
        Инициализация генератора описаний.
        
        Аргументы:
            config: Объект конфигурации приложения
        """
        log_function_call("ContentSummarizer.__init__", (), {"config": config})
        
        self.config = config
        self.client = AsyncOpenAI(
            api_key=config.llm_api_key,
            base_url=config.llm_base_url
        )
        self.prompt_template = self._load_prompt_template()
        # Для rate limiting
        self.requests_times = []
        self.rate_limit_delay = 60 / config.llm_rate_limit if config.llm_rate_limit > 0 else 0
        
        logger.info(f"ContentSummarizer инициализирован: model={config.llm_model}, "
                   f"max_tokens={config.llm_max_tokens}, rate_limit={config.llm_rate_limit}/min")
        logger.debug(f"Base URL: {config.llm_base_url}")
    
    def _load_prompt_template(self) -> str:
        """
        Загружает шаблон промпта из файла.
        
        Возвращает:
            str: Содержимое файла промпта
        """
        log_function_call("_load_prompt_template", (), {"prompt_file": self.config.prompt_file})
        
        try:
            with open(self.config.prompt_file, 'r', encoding='utf-8') as f:
                template = f.read()
            
            logger.debug(f"Промпт успешно загружен из файла: {self.config.prompt_file}")
            logger.debug(f"Длина шаблона промпта: {len(template)} символов")
            return template
            
        except FileNotFoundError:
            log_error_with_context(
                FileNotFoundError(f"Файл промпта не найден: {self.config.prompt_file}"),
                {"prompt_file": self.config.prompt_file, "operation": "_load_prompt_template"}
            )
            raise
        except Exception as e:
            log_error_with_context(
                e,
                {"prompt_file": self.config.prompt_file, "operation": "_load_prompt_template"}
            )
            raise
    
    def _prepare_prompt(self, text: str, title: str) -> str:
        """
        Подготавливает промпт для генерации описания.
        
        Аргументы:
            text: Текст содержимого страницы
            title: Заголовок страницы
            
        Возвращает:
            str: Подготовленный промпт
        """
        log_function_call("_prepare_prompt", (), {"title": title, "text_length": len(text)})
        
        # Ограничиваем длину текста, чтобы не превысить лимит токенов
        max_content_length = self.config.llm_max_tokens * 3  # Примерное соотношение токенов к символам
        original_length = len(text)
        
        if len(text) > max_content_length:
            text = text[:max_content_length]
            logger.info(f"Текст обрезан с {original_length} до {max_content_length} символов для экономии токенов")
        
        prompt = self.prompt_template.format(title=title, content=text)
        logger.debug(f"Промпт подготовлен, длина: {len(prompt)} символов")
        
        return prompt
    
    async def _rate_limit(self):
        """
        Ограничивает частоту запросов к LLM API в соответствии с настройками.
        """
        if self.rate_limit_delay <= 0:
            logger.debug("Rate limiting отключен для LLM API")
            return
            
        current_time = time.time()
        # Удаляем времена запросов, которые были более 60 секунд назад
        old_count = len(self.requests_times)
        self.requests_times = [req_time for req_time in self.requests_times if current_time - req_time < 60]
        removed_count = old_count - len(self.requests_times)
        
        if removed_count > 0:
            logger.debug(f"Удалено {removed_count} устаревших записей из LLM rate limit истории")
        
        # Если количество запросов в минуту достигло лимита, ждем
        if len(self.requests_times) >= self.config.llm_rate_limit:
            sleep_time = 60 - (current_time - self.requests_times[0])
            if sleep_time > 0:
                logger.debug(f"Ожидание {sleep_time:.2f} секунд из-за LLM rate limiting "
                           f"(текущий запрос: {len(self.requests_times)}/{self.config.llm_rate_limit})")
                await asyncio.sleep(sleep_time)
                # После ожидания снова проверяем список запросов
                current_time = time.time()
                self.requests_times = [req_time for req_time in self.requests_times if current_time - req_time < 60]
        
        # Добавляем текущий запрос
        self.requests_times.append(current_time)
        logger.debug(f"LLM запрос добавлен в rate limit историю: {len(self.requests_times)}/{self.config.llm_rate_limit}")
    
    async def generate_summary(self, text: str, title: str) -> str:
        """
        Генерирует краткое описание страницы с помощью LLM.
        
        Аргументы:
            text: Текст содержимого страницы
            title: Заголовок страницы
            
        Возвращает:
            str: Сгенерированное описание в формате Markdown
        """
        start_time = time.time()
        log_function_call("generate_summary", (title,), {"text_length": len(text)})
        
        try:
            # Ограничение частоты запросов
            await self._rate_limit()
            
            prompt = self._prepare_prompt(text, title)
            
            logger.debug(f"Отправка запроса к LLM API: model={self.config.llm_model}, "
                        f"max_tokens={self.config.llm_max_tokens}, temperature={self.config.llm_temperature}")
            
            response = await self.client.chat.completions.create(
                model=self.config.llm_model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.config.llm_max_tokens,
                temperature=self.config.llm_temperature
            )
            
            summary = response.choices[0].message.content
            if summary is None:
                logger.warning(f"LLM вернул пустое описание для страницы: {title}")
                summary = "Описание не сформировано: LLM не вернул содержимое"
            else:
                duration = time.time() - start_time
                log_performance("generate_summary", duration, f"title={title}, success=True")
                logger.info(f"Успешно сгенерировано описание для страницы: {title} (длина: {len(summary)} символов)")
            
            return summary
            
        except Exception as e:
            duration = time.time() - start_time
            log_performance("generate_summary", duration, f"title={title}, success=False")
            log_error_with_context(e, {"title": title, "operation": "generate_summary", "text_length": len(text)})
            return f"Ошибка генерации описания: {str(e)}"