"""
Тесты для модуля summarizer.py
"""
import os
import tempfile
import asyncio
import pytest
import time
from unittest.mock import AsyncMock, patch, MagicMock
from src.summarizer import ContentSummarizer
from src.config import ConfigManager


class TestContentSummarizer:
    """Тесты для класса ContentSummarizer"""
    
    def setup_method(self):
        """Настройка для каждого теста"""
        # Создаем временный файл промпта
        self.temp_prompt = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', prefix='test_prompt_')
        self.temp_prompt.write("Тестовый шаблон: {title} - {content}")
        self.temp_prompt_path = self.temp_prompt.name
        self.temp_prompt.close()
        
        # Создаем временный .env файл с правильным путем к файлу промпта
        self.temp_env = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env')
        self.temp_env.write(f"""
LLM_API_KEY=test_key
LLM_BASE_URL=https://test.openrouter.ai/api/v1
LLM_MODEL=test/gpt-4o-mini
LLM_MAX_TOKENS=500
LLM_TEMPERATURE=0.5
LLM_RATE_LIMIT=5

PROMPT_FILE={self.temp_prompt_path}
""")
        self.temp_env_path = self.temp_env.name
        self.temp_env.close()
        
        # Инициализируем конфигурацию
        self.config_manager = ConfigManager(env_path=self.temp_env_path)
        self.config = self.config_manager.get()
    
    def teardown_method(self):
        """Очистка после каждого теста"""
        # Удаляем временные файлы
        if os.path.exists(self.temp_env_path):
            os.unlink(self.temp_env_path)
        if os.path.exists(self.temp_prompt_path):
            os.unlink(self.temp_prompt_path)
    
    def test_summarizer_initialization(self):
        """Тестирует инициализацию ContentSummarizer"""
        summarizer = ContentSummarizer(self.config)
        
        # Проверяем, что объект создался корректно
        assert summarizer.config == self.config
        assert summarizer.rate_limit_delay == 60 / 5  # 60 секунд / 5 запросов = 12 секунд
        assert summarizer.prompt_template == "Тестовый шаблон: {title} - {content}"
        assert len(summarizer.requests_times) == 0
    
    def test_load_prompt_template_file_not_found(self):
        """Тестирует обработку отсутствующего файла промпта"""
        # Создаем временный .env файл с неверным путем к файлу промпта
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as temp_env:
            temp_env.write(f"""
LLM_API_KEY=test_key
PROMPT_FILE=/nonexistent/prompt.txt
""")
            temp_env_path = temp_env.name
        
        try:
            # Проверяем, что ConfigManager вызывает исключение при валидации
            with pytest.raises(ValueError, match="Файл промпта не найден"):
                ConfigManager(env_path=temp_env_path)
        finally:
            os.unlink(temp_env_path)
    
    def test_prepare_prompt_with_long_content(self):
        """Тестирует подготовку промпта с длинным содержимым"""
        summarizer = ContentSummarizer(self.config)
        
        # Создаем очень длинный контент
        long_content = "a" * 2000  # 2000 символов
        test_title = "Тестовый заголовок"
        
        # Подготавливаем промпт
        prepared_prompt = summarizer._prepare_prompt(long_content, test_title)
        
        # Проверяем, что контент был обрезан
        max_content_length = self.config.llm_max_tokens * 3  # 1500 символов
        assert len(long_content) > max_content_length
        assert len(prepared_prompt) < len(long_content)
        assert test_title in prepared_prompt
    
    def test_prepare_prompt_with_short_content(self):
        """Тестирует подготовку промпта с коротким содержимым"""
        summarizer = ContentSummarizer(self.config)
        
        # Создаем короткий контент
        short_content = "Короткий контент"
        test_title = "Тестовый заголовок"
        
        # Подготавливаем промпт
        prepared_prompt = summarizer._prepare_prompt(short_content, test_title)
        
        # Проверяем, что контент не был обрезан
        expected_prompt = f"Тестовый шаблон: {test_title} - {short_content}"
        assert prepared_prompt == expected_prompt
    
    @patch('src.summarizer.AsyncOpenAI')
    def test_generate_summary_success(self, mock_openai_client):
        """Тестирует успешную генерацию описания"""
        # Создаем мок-ответ от API
        mock_response = AsyncMock()
        mock_response.choices = [AsyncMock()]
        mock_response.choices[0].message = AsyncMock()
        mock_response.choices[0].message.content = "Тестовое описание страницы"
        
        mock_client_instance = AsyncMock()
        mock_client_instance.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai_client.return_value = mock_client_instance
        
        summarizer = ContentSummarizer(self.config)
        
        # Тестируем генерацию описания
        test_content = "Тестовое содержимое"
        test_title = "Тестовый заголовок"
        
        result = asyncio.run(summarizer.generate_summary(test_content, test_title))
        
        # Проверяем результат
        assert result == "Тестовое описание страницы"
        
        # Проверяем, что метод API был вызван с правильными параметрами
        mock_client_instance.chat.completions.create.assert_called_once_with(
            model=self.config.llm_model,
            messages=[{"role": "user", "content": f"Тестовый шаблон: {test_title} - {test_content}"}],
            max_tokens=self.config.llm_max_tokens,
            temperature=self.config.llm_temperature
        )
    
    @patch('src.summarizer.AsyncOpenAI')
    def test_generate_summary_empty_response(self, mock_openai_client):
        """Тестирует генерацию описания при пустом ответе от LLM"""
        # Создаем мок-ответ от API с пустым содержимым
        mock_response = AsyncMock()
        mock_response.choices = [AsyncMock()]
        mock_response.choices[0].message = AsyncMock()
        mock_response.choices[0].message.content = None  # Пустой ответ
        
        mock_client_instance = AsyncMock()
        mock_client_instance.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai_client.return_value = mock_client_instance
        
        summarizer = ContentSummarizer(self.config)
        
        # Тестируем генерацию описания с пустым ответом
        test_content = "Тестовое содержимое"
        test_title = "Тестовый заголовок"
        
        result = asyncio.run(summarizer.generate_summary(test_content, test_title))
        
        # Проверяем, что возвращается сообщение об ошибке
        assert result == "Описание не сформировано: LLM не вернул содержимое"
    
    @patch('src.summarizer.AsyncOpenAI')
    def test_generate_summary_exception(self, mock_openai_client):
        """Тестирует генерацию описания при возникновении исключения"""
        # Мокаем выброс исключения
        mock_client_instance = AsyncMock()
        mock_client_instance.chat.completions.create.side_effect = Exception("API Error")
        mock_openai_client.return_value = mock_client_instance
        
        summarizer = ContentSummarizer(self.config)
        
        # Тестируем генерацию описания с исключением
        test_content = "Тестовое содержимое"
        test_title = "Тестовый заголовок"
        
        result = asyncio.run(summarizer.generate_summary(test_content, test_title))
        
        # Проверяем, что возвращается сообщение об ошибке
        assert result == "Ошибка генерации описания: API Error"
    
    @pytest.mark.asyncio
    async def test_rate_limit_disabled(self):
        """Тестирует отключенный rate limiting"""
        # Создаем временный .env файл с отключенным rate limiting
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as temp_env:
            temp_env.write(f"""
LLM_API_KEY=test_key
LLM_RATE_LIMIT=0
PROMPT_FILE={self.temp_prompt_path}
""")
            temp_env_path = temp_env.name
        
        try:
            config_manager = ConfigManager(env_path=temp_env_path)
            config = config_manager.get()
            
            summarizer = ContentSummarizer(config)
            
            # Проверяем, что rate limiting отключен
            assert summarizer.rate_limit_delay == 0
            
            # Вызываем _rate_limit и проверяем, что нет ожидания
            start_time = time.time()
            await summarizer._rate_limit()
            end_time = time.time()
            
            # Проверяем, что функция завершилась мгновенно
            assert end_time - start_time < 0.1
        finally:
            os.unlink(temp_env_path)
    
    @pytest.mark.asyncio
    async def test_rate_limit_with_old_requests(self):
        """Тестирует rate limiting со старыми запросами"""
        summarizer = ContentSummarizer(self.config)
        
        # Добавляем старые запросы (более 60 секунд назад)
        old_time = time.time() - 70  # 70 секунд назад
        summarizer.requests_times = [old_time, old_time + 10, old_time + 20]
        
        # Вызываем _rate_limit и проверяем, что старые запросы удалены
        await summarizer._rate_limit()
        
        # Проверяем, что старые запросы удалены
        # Должен остаться только один запрос (текущий)
        # Но также может остаться второй запрос, если он не старше 60 секунд
        # Это зависит от точного времени выполнения теста
        assert len(summarizer.requests_times) <= 2
        assert len(summarizer.requests_times) >= 1
    
    @pytest.mark.asyncio
    async def test_rate_limit_with_wait(self):
        """Тестирует rate limiting с ожиданием"""
        # Создаем временный .env файл с низким лимитом
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as temp_env:
            temp_env.write(f"""
LLM_API_KEY=test_key
LLM_RATE_LIMIT=2
PROMPT_FILE={self.temp_prompt_path}
""")
            temp_env_path = temp_env.name
        
        try:
            config_manager = ConfigManager(env_path=temp_env_path)
            config = config_manager.get()
            
            summarizer = ContentSummarizer(config)
            
            # Добавляем запросы, чтобы достичь лимита
            current_time = time.time()
            summarizer.requests_times = [current_time - 10, current_time - 5]
            
            # Вызываем _rate_limit и измеряем время ожидания
            start_time = time.time()
            await summarizer._rate_limit()
            end_time = time.time()
            
            # Проверяем, что было ожидание
            # Время ожидания должно быть примерно 50 секунд (60 - 10)
            assert end_time - start_time > 40  # Даем небольшой запас
        finally:
            os.unlink(temp_env_path)
    
    @pytest.mark.asyncio
    async def test_rate_limit_cleanup_after_wait(self):
        """Тестирует очистку старых запросов после ожидания"""
        # Создаем временный .env файл с низким лимитом
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as temp_env:
            temp_env.write(f"""
LLM_API_KEY=test_key
LLM_RATE_LIMIT=1
PROMPT_FILE={self.temp_prompt_path}
""")
            temp_env_path = temp_env.name
        
        try:
            config_manager = ConfigManager(env_path=temp_env_path)
            config = config_manager.get()
            
            summarizer = ContentSummarizer(config)
            
            # Добавляем запрос, чтобы достичь лимита
            current_time = time.time()
            summarizer.requests_times = [current_time - 30]  # 30 секунд назад
            
            # Вызываем _rate_limit
            await summarizer._rate_limit()
            
            # Проверяем, что после ожидания список запросов был очищен
            assert len(summarizer.requests_times) == 1
            # И новый запрос был добавлен
            assert summarizer.requests_times[0] > current_time
        finally:
            os.unlink(temp_env_path)


if __name__ == "__main__":
    pytest.main([__file__])