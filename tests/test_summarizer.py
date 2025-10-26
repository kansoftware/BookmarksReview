"""
Тесты для модуля summarizer.py
"""
import os
import tempfile
import asyncio
import pytest
from unittest.mock import AsyncMock, patch
from src.summarizer import ContentSummarizer
from src.config import ConfigManager


def test_summarizer_initialization():
    """Тестирует инициализацию ContentSummarizer"""
    # Создаем временный файл промпта
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', prefix='test_prompt_') as temp_prompt:
        temp_prompt.write("Тестовый шаблон: {title} - {content}")
        temp_prompt_path = temp_prompt.name

    # Создаем временный .env файл с правильным путем к файлу промпта
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as temp_env:
        temp_env.write(f"""
LLM_API_KEY=test_key
LLM_BASE_URL=https://test.openrouter.ai/api/v1
LLM_MODEL=test/gpt-4o-mini
LLM_MAX_TOKENS=500
LLM_TEMPERATURE=0.5
LLM_RATE_LIMIT=5

PROMPT_FILE={temp_prompt_path}
""")
        temp_env_path = temp_env.name

    try:
        config_manager = ConfigManager(env_path=temp_env_path)
        config = config_manager.get()
        
        summarizer = ContentSummarizer(config)
        
        # Проверяем, что объект создался корректно
        assert summarizer.config == config
        assert summarizer.rate_limit_delay == 60 / 5  # 60 секунд / 5 запросов = 12 секунд
        
        print("Тест инициализации генератора описаний пройден успешно!")
    finally:
        # Удаляем временные файлы
        os.unlink(temp_env_path)
        os.unlink(temp_prompt_path)


def test_prompt_template_loading():
    """Тестирует загрузку шаблона промпта"""
    # Создаем временный файл промпта
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', prefix='test_prompt_') as temp_prompt:
        temp_prompt.write("Тестовый шаблон: {title} - {content}")
        temp_prompt_path = temp_prompt.name

    # Создаем временный .env файл с правильным путем к файлу промпта
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as temp_env:
        temp_env.write(f"""
LLM_API_KEY=test_key
PROMPT_FILE={temp_prompt_path}
""")
        temp_env_path = temp_env.name

    try:
        config_manager = ConfigManager(env_path=temp_env_path)
        config = config_manager.get()
        
        summarizer = ContentSummarizer(config)
        
        # Проверяем, что шаблон загружен правильно
        assert summarizer.prompt_template == f"Тестовый шаблон: {{title}} - {{content}}"
        
        print("Тест загрузки шаблона промпта пройден успешно!")
    finally:
        # Удаляем временные файлы
        os.unlink(temp_env_path)
        os.unlink(temp_prompt_path)


def test_prepare_prompt():
    """Тестирует подготовку промпта"""
    # Создаем временный файл промпта
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', prefix='test_prompt_') as temp_prompt:
        temp_prompt.write("Заголовок: {title}\nСодержимое: {content}")
        temp_prompt_path = temp_prompt.name

    # Создаем временный .env файл с правильным путем к файлу промпта
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as temp_env:
        temp_env.write(f"""
LLM_API_KEY=test_key
LLM_MAX_TOKENS=100
PROMPT_FILE={temp_prompt_path}
""")
        temp_env_path = temp_env.name

    try:
        config_manager = ConfigManager(env_path=temp_env_path)
        config = config_manager.get()
        
        summarizer = ContentSummarizer(config)
        
        # Подготавливаем тестовые данные
        test_content = "Тестовое содержимое страницы с достаточной длиной для проверки ограничения"
        test_title = "Тестовый заголовок"
        
        # Подготавливаем промпт
        prepared_prompt = summarizer._prepare_prompt(test_content, test_title)
        
        # Проверяем, что промпт подготовлен правильно
        expected_prompt = f"Заголовок: {test_title}\nСодержимое: {test_content}"
        assert prepared_prompt == expected_prompt
        
        print("Тест подготовки промпта пройден успешно!")
    finally:
        # Удаляем временные файлы
        os.unlink(temp_env_path)
        os.unlink(temp_prompt_path)


@patch('src.summarizer.AsyncOpenAI')
def test_generate_summary_success(mock_openai_client):
    """Тестирует успешную генерацию описания"""
    # Создаем мок-ответ от API
    mock_response = AsyncMock()
    mock_response.choices = [AsyncMock()]
    mock_response.choices[0].message = AsyncMock()
    mock_response.choices[0].message.content = "Тестовое описание страницы"
    
    mock_client_instance = AsyncMock()
    mock_client_instance.chat.completions.create = AsyncMock(return_value=mock_response)
    mock_openai_client.return_value = mock_client_instance

    # Создаем временный файл промпта
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', prefix='test_prompt_') as temp_prompt:
        temp_prompt.write("Заголовок: {title}\nСодержимое: {content}")
        temp_prompt_path = temp_prompt.name

    # Создаем временный .env файл с правильным путем к файлу промпта
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as temp_env:
        temp_env.write(f"""
LLM_API_KEY=test_key
LLM_BASE_URL=https://test.openrouter.ai/api/v1
LLM_MODEL=test/gpt-4o-mini
LLM_MAX_TOKENS=500
LLM_TEMPERATURE=0.5
LLM_RATE_LIMIT=5

PROMPT_FILE={temp_prompt_path}
""")
        temp_env_path = temp_env.name

    try:
        config_manager = ConfigManager(env_path=temp_env_path)
        config = config_manager.get()
        
        summarizer = ContentSummarizer(config)
        
        # Тестируем генерацию описания
        test_content = "Тестовое содержимое"
        test_title = "Тестовый заголовок"
        
        result = asyncio.run(summarizer.generate_summary(test_content, test_title))
        
        # Проверяем результат
        assert result == "Тестовое описание страницы"
        
        # Проверяем, что метод API был вызван с правильными параметрами
        mock_client_instance.chat.completions.create.assert_called_once_with(
            model=config.llm_model,
            messages=[{"role": "user", "content": f"Заголовок: {test_title}\nСодержимое: {test_content}"}],
            max_tokens=config.llm_max_tokens,
            temperature=config.llm_temperature
        )
        
        print("Тест успешной генерации описания пройден успешно!")
    finally:
        # Удаляем временные файлы
        os.unlink(temp_env_path)
        os.unlink(temp_prompt_path)


@patch('src.summarizer.AsyncOpenAI')
def test_generate_summary_empty_response(mock_openai_client):
    """Тестирует генерацию описания при пустом ответе от LLM"""
    # Создаем мок-ответ от API с пустым содержимым
    mock_response = AsyncMock()
    mock_response.choices = [AsyncMock()]
    mock_response.choices[0].message = AsyncMock()
    mock_response.choices[0].message.content = None  # Пустой ответ
    
    mock_client_instance = AsyncMock()
    mock_client_instance.chat.completions.create = AsyncMock(return_value=mock_response)
    mock_openai_client.return_value = mock_client_instance

    # Создаем временный файл промпта
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', prefix='test_prompt_') as temp_prompt:
        temp_prompt.write("Заголовок: {title}\nСодержимое: {content}")
        temp_prompt_path = temp_prompt.name

    # Создаем временный .env файл с правильным путем к файлу промпта
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as temp_env:
        temp_env.write(f"""
LLM_API_KEY=test_key
LLM_BASE_URL=https://test.openrouter.ai/api/v1
LLM_MODEL=test/gpt-4o-mini
LLM_MAX_TOKENS=500
LLM_TEMPERATURE=0.5
LLM_RATE_LIMIT=5

PROMPT_FILE={temp_prompt_path}
""")
        temp_env_path = temp_env.name

    try:
        config_manager = ConfigManager(env_path=temp_env_path)
        config = config_manager.get()
        
        summarizer = ContentSummarizer(config)
        
        # Тестируем генерацию описания с пустым ответом
        test_content = "Тестовое содержимое"
        test_title = "Тестовый заголовок"
        
        result = asyncio.run(summarizer.generate_summary(test_content, test_title))
        
        # Проверяем, что возвращается сообщение об ошибке
        assert result == "Описание не сформировано: LLM не вернул содержимое"
        
        print("Тест генерации описания при пустом ответе пройден успешно!")
    finally:
        # Удаляем временные файлы
        os.unlink(temp_env_path)
        os.unlink(temp_prompt_path)


@patch('src.summarizer.AsyncOpenAI')
def test_generate_summary_exception(mock_openai_client):
    """Тестирует генерацию описания при возникновении исключения"""
    # Мокаем выброс исключения
    mock_client_instance = AsyncMock()
    mock_client_instance.chat.completions.create.side_effect = Exception("API Error")
    mock_openai_client.return_value = mock_client_instance

    # Создаем временный файл промпта
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', prefix='test_prompt_') as temp_prompt:
        temp_prompt.write("Заголовок: {title}\nСодержимое: {content}")
        temp_prompt_path = temp_prompt.name

    # Создаем временный .env файл с правильным путем к файлу промпта
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as temp_env:
        temp_env.write(f"""
LLM_API_KEY=test_key
LLM_BASE_URL=https://test.openrouter.ai/api/v1
LLM_MODEL=test/gpt-4o-mini
LLM_MAX_TOKENS=500
LLM_TEMPERATURE=0.5
LLM_RATE_LIMIT=5

PROMPT_FILE={temp_prompt_path}
""")
        temp_env_path = temp_env.name

    try:
        config_manager = ConfigManager(env_path=temp_env_path)
        config = config_manager.get()
        
        summarizer = ContentSummarizer(config)
        
        # Тестируем генерацию описания с исключением
        test_content = "Тестовое содержимое"
        test_title = "Тестовый заголовок"
        
        result = asyncio.run(summarizer.generate_summary(test_content, test_title))
        
        # Проверяем, что возвращается сообщение об ошибке
        assert result == "Ошибка генерации описания: API Error"
        
        print("Тест генерации описания при исключении пройден успешно!")
    finally:
        # Удаляем временные файлы
        os.unlink(temp_env_path)
        os.unlink(temp_prompt_path)


@pytest.mark.asyncio
async def test_rate_limiting():
    """Тестирует ограничение частоты запросов к LLM API"""
    # Создаем временный файл промпта
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', prefix='test_prompt_') as temp_prompt:
        temp_prompt.write("Тестовый шаблон: {title} - {content}")
        temp_prompt_path = temp_prompt.name

    # Создаем временный .env файл с правильным путем к файлу промпта
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as temp_env:
        temp_env.write(f"""
LLM_API_KEY=test_key
LLM_RATE_LIMIT=10
PROMPT_FILE={temp_prompt_path}
""")
        temp_env_path = temp_env.name

    try:
        config_manager = ConfigManager(env_path=temp_env_path)
        config = config_manager.get()
        
        summarizer = ContentSummarizer(config)
        
        # Проверяем, что параметр конфигурации установлен корректно
        assert summarizer.config.llm_rate_limit == 10
        assert summarizer.rate_limit_delay == 60 / 10  # 6 секунд между запросами
        
        # Проверяем работу rate limiting - тестируем сам механизм
        # Изначально список запросов пуст
        assert len(summarizer.requests_times) == 0
        
        # Выполняем вызов _rate_limit
        await summarizer._rate_limit()
        
        # Проверяем, что время запроса добавлено в список
        assert len(summarizer.requests_times) == 1
        
        # Выполняем еще несколько вызовов
        await summarizer._rate_limit()
        await summarizer._rate_limit()
        
        # Проверяем, что все времена запросов добавлены
        assert len(summarizer.requests_times) == 3
        
        print("Тест ограничения частоты запросов к LLM API пройден успешно!")
    finally:
        # Удаляем временные файлы
        os.unlink(temp_env_path)
        os.unlink(temp_prompt_path)


@pytest.mark.asyncio
async def test_async_functions():
    """Запускает асинхронные тесты"""
    await test_rate_limiting()


if __name__ == "__main__":
    test_summarizer_initialization()
    test_prompt_template_loading()
    test_prepare_prompt()
    test_generate_summary_success()
    test_generate_summary_empty_response()
    test_generate_summary_exception()
    
    # Запускаем асинхронные тесты
    asyncio.run(test_async_functions())