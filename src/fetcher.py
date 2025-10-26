"""
Модуль fetcher.py
Отвечает за загрузку HTML-контента веб-страниц.
Поддерживает асинхронные запросы, retry-механизм и rate limiting.
"""
import asyncio
import re
from typing import Optional
from urllib.parse import urlparse
import time

import httpx
from bs4 import BeautifulSoup

from .config import Config
from .models import ProcessedPage
from .logger import get_logger, log_function_call, log_performance, log_error_with_context

logger = get_logger(__name__)


class ContentFetcher:
    """
    Класс для загрузки контента веб-страниц.
    
    Аргументы:
        config: Объект конфигурации приложения
    """
    
    def __init__(self, config: Config):
        """
        Инициализация загрузчика контента.
        
        Аргументы:
            config: Объект конфигурации приложения
        """
        log_function_call("ContentFetcher.__init__", (), {"config": config})
        
        self.config = config
        self.timeout = httpx.Timeout(
            timeout=config.fetch_timeout,
            connect=config.fetch_timeout
        )
        self.semaphore = asyncio.Semaphore(config.fetch_max_concurrent)
        self.session = None
        # Для rate limiting - отслеживаем время запросов
        self.request_times = []
        
        logger.info(f"ContentFetcher инициализирован: timeout={config.fetch_timeout}s, "
                   f"max_concurrent={config.fetch_max_concurrent}, "
                   f"max_size={config.fetch_max_size_mb}MB")
        
    async def __aenter__(self):
        """
        Асинхронный контекстный менеджер для создания сессии.
        """
        log_function_call("ContentFetcher.__aenter__")
        
        limits = httpx.Limits(max_keepalive_connections=20, max_connections=100)
        self.session = httpx.AsyncClient(
            timeout=self.timeout,
            limits=limits,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        )
        
        logger.debug("HTTP сессия создана для ContentFetcher")
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Асинхронный контекстный менеджер для закрытия сессии.
        """
        log_function_call("ContentFetcher.__aexit__", (), {"exc_type": exc_type})
        
        if self.session:
            await self.session.aclose()
            logger.debug("HTTP сессия закрыта для ContentFetcher")
    
    async def fetch_content(self, url: str) -> Optional[str]:
        """
        Асинхронно загружает HTML-контент по URL.
        
        Аргументы:
            url: URL-адрес страницы для загрузки
            
        Возвращает:
            Строка с HTML-контентом или None в случае ошибки
        """
        start_time = time.time()
        log_function_call("fetch_content", (url,))
        
        if not self._validate_url(url):
            logger.warning(f"Некорректный URL: {url}")
            return None
            
        if self.session is None:
            logger.error("Попытка вызова fetch_content без инициализации сессии. Используйте async with ContentFetcher(config) as fetcher:")
            return None
            
        try:
            async with self.semaphore:
                await self._rate_limit()
                result = await self._fetch_with_retry(url)
                
                duration = time.time() - start_time
                log_performance("fetch_content", duration, f"url={url}, success={result is not None}")
                
                return result
        except Exception as e:
            duration = time.time() - start_time
            log_performance("fetch_content", duration, f"url={url}, success=False")
            log_error_with_context(e, {"url": url, "operation": "fetch_content"})
            return None
    
    async def _fetch_with_retry(self, url: str) -> Optional[str]:
        """
        Выполняет загрузку с повторными попытками при ошибках.
        
        Аргументы:
            url: URL-адрес страницы для загрузки
            
        Возвращает:
            Строка с HTML-контентом или None в случае ошибки
        """
        log_function_call("_fetch_with_retry", (url,),
                        {"max_attempts": self.config.fetch_retry_attempts + 1})
        
        last_exception = None
        
        if self.session is None:
            logger.error("Попытка вызова _fetch_with_retry без инициализации сессии")
            return None
            
        for attempt in range(self.config.fetch_retry_attempts + 1):
            try:
                logger.debug(f"Попытка загрузки {attempt + 1}/{self.config.fetch_retry_attempts + 1}: {url}")
                response = await self.session.get(url)
                
                # Проверяем статус ответа
                if response.status_code == 200:
                    content = response.text
                    
                    # Проверяем размер контента
                    content_size_mb = len(content.encode('utf-8')) / (1024 * 1024)
                    if content_size_mb > self.config.fetch_max_size_mb:
                        logger.warning(f"Размер контента превышает лимит: {url}, {content_size_mb:.2f}MB")
                        return None
                    
                    logger.debug(f"Контент успешно загружен: {url}, размер: {content_size_mb:.2f}MB")
                    return content
                elif response.status_code in [404, 410]:
                    # Не пытаемся повторно загружать если страница не найдена
                    logger.warning(f"Страница не найдена ({response.status_code}): {url}")
                    return None
                elif response.status_code >= 500:
                    # Ошибки сервера - повторяем попытку
                    logger.warning(f"Ошибка сервера ({response.status_code}): {url}")
                    last_exception = httpx.HTTPStatusError(
                        f"Server error {response.status_code}",
                        request=response.request,
                        response=response
                    )
                else:
                    # Другие ошибки - повторяем попытку
                    logger.warning(f"Ошибка HTTP ({response.status_code}): {url}")
                    last_exception = httpx.HTTPStatusError(
                        f"HTTP error {response.status_code}",
                        request=response.request,
                        response=response
                    )
                    
            except Exception as e:
                logger.warning(f"Ошибка загрузки ({attempt + 1}/{self.config.fetch_retry_attempts + 1}): {url}, {str(e)}")
                last_exception = e
                
            if attempt < self.config.fetch_retry_attempts:
                # Экспоненциальная задержка
                delay = self.config.fetch_retry_delay * (2 ** attempt)
                logger.debug(f"Задержка перед следующей попыткой: {delay:.2f}с")
                await asyncio.sleep(delay)
        
        log_error_with_context(
            Exception(f"Не удалось загрузить страницу после {self.config.fetch_retry_attempts + 1} попыток"),
            {"url": url, "attempts": self.config.fetch_retry_attempts + 1, "last_error": str(last_exception)}
        )
        return None
    
    def extract_text(self, html: str) -> str:
        """
        Извлекает текстовое содержимое из HTML.
        
        Аргументы:
            html: HTML-контент для извлечения текста
            
        Возвращает:
            Извлеченный текст
        """
        log_function_call("extract_text", (), {"html_length": len(html) if html else 0})
        
        if not html:
            logger.debug("Пустой HTML контент, возвращаем пустую строку")
            return ""
            
        try:
            soup = BeautifulSoup(html, 'html.parser')
            logger.debug("HTML успешно распарсен с BeautifulSoup")
            
            # Удаляем скрипты и стили
            removed_tags = ["script", "style", "nav", "footer", "header"]
            for tag in removed_tags:
                for element in soup.find_all(tag):
                    element.decompose()
            logger.debug(f"Удалены теги: {removed_tags}")
                
            # Ищем основное содержимое страницы
            main_content = soup.find('main') or soup.find('article') or soup.find('div', class_=re.compile(r'main|content|article'))
            
            if main_content:
                text = main_content.get_text()
                logger.debug("Найдено основное содержимое страницы через main/article/div")
            else:
                text = soup.get_text()
                logger.debug("Использовано полное содержимое страницы")
                
            # Очищаем текст от лишних пробелов
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split(" "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            # Ограничение размера извлеченного текста в соответствии с FETCH_MAX_SIZE_MB
            try:
                max_size_bytes = int(self.config.fetch_max_size_mb * 1024 * 1024)
            except Exception:
                # Безопасное значение по умолчанию на случай некорректной конфигурации
                max_size_bytes = 5 * 1024 * 1024
                logger.warning(f"Некорректная конфигурация fetch_max_size_mb, использовано значение по умолчанию: 5MB")
                
            text_bytes = text.encode('utf-8')
            original_length = len(text_bytes)
            
            if len(text_bytes) > max_size_bytes:
                logger.warning(
                    f"Извлеченный текст превышает лимит {self.config.fetch_max_size_mb}MB, выполняется обрезка"
                )
                # Обрезаем по байтам и декодируем, игнорируя неполные многобайтные последовательности
                text = text_bytes[:max_size_bytes].decode('utf-8', errors='ignore')
                logger.debug(f"Текст обрезан с {original_length} до {len(text.encode('utf-8'))} байт")
            
            logger.debug(f"Текст успешно извлечен, длина: {len(text)} символов")
            return text
            
        except Exception as e:
            log_error_with_context(e, {"operation": "extract_text", "html_length": len(html) if html else 0})
            return ""
    
    def _validate_url(self, url: str) -> bool:
        """
        Проверяет корректность URL.
        
        Аргументы:
            url: URL для проверки
            
        Возвращает:
            True если URL корректный, иначе False
        """
        log_function_call("_validate_url", (url,))
        
        try:
            result = urlparse(url)
            is_valid = all([result.scheme in ['http', 'https'], result.netloc])
            
            if not is_valid:
                logger.debug(f"Некорректный URL: scheme={result.scheme}, netloc={result.netloc}")
            else:
                logger.debug(f"URL корректен: {url}")
                
            return is_valid
        except Exception as e:
            log_error_with_context(e, {"url": url, "operation": "_validate_url"})
            return False
    
    async def _rate_limit(self):
        """
        Ограничивает частоту запросов в соответствии с настройками.
        """
        # Ограничение по умолчанию: 3 запроса в минуту (если не указано иное)
        max_requests_per_minute = getattr(self.config, 'llm_rate_limit', 3)
        
        if max_requests_per_minute <= 0:
            logger.debug("Rate limiting отключен (llm_rate_limit <= 0)")
            return  # Отключаем rate limiting если лимит <= 0
            
        current_time = asyncio.get_event_loop().time()
        
        # Удаляем старые временные метки (старше 60 секунд)
        old_count = len(self.request_times)
        self.request_times = [time for time in self.request_times if current_time - time < 60]
        removed_count = old_count - len(self.request_times)
        
        if removed_count > 0:
            logger.debug(f"Удалено {removed_count} устаревших записей из rate limit истории")
        
        # Если достигнут лимит запросов в минуту, ждем
        if len(self.request_times) >= max_requests_per_minute:
            sleep_time = 60 - (current_time - self.request_times[0])
            if sleep_time > 0:
                logger.debug(f"Rate limiting: ждем {sleep_time:.2f} секунд (текущий запрос: {len(self.request_times)}/{max_requests_per_minute})")
                await asyncio.sleep(sleep_time)
                # После ожидания снова проверяем лимит
                current_time = asyncio.get_event_loop().time()
                self.request_times = [time for time in self.request_times if current_time - time < 60]
        
        # Добавляем текущее время запроса
        self.request_times.append(current_time)
        logger.debug(f"Запрос добавлен в rate limit историю: {len(self.request_times)}/{max_requests_per_minute}")