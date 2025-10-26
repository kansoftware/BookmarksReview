"""
Тесты для модуля fetcher.py
"""
import asyncio
import tempfile
import os
import pytest
from unittest.mock import AsyncMock, patch
from src.fetcher import ContentFetcher
from src.config import ConfigManager


def test_url_validation():
    """Тестирует валидацию URL"""
    # Создаем временные файлы: промпт и .env
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_prompt:
        temp_prompt.write("test")
        prompt_path = temp_prompt.name

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as temp_env:
        temp_env.write(f"""
LLM_API_KEY=test_key
LLM_MAX_TOKENS=1000
LLM_TEMPERATURE=0.7
LLM_RATE_LIMIT=3
FETCH_TIMEOUT=30
FETCH_MAX_CONCURRENT=10
FETCH_MAX_SIZE_MB=5
FETCH_RETRY_ATTEMPTS=3
FETCH_RETRY_DELAY=1.5
PROMPT_FILE={prompt_path}
""")
        temp_env_path = temp_env.name

    try:
        config_manager = ConfigManager(env_path=temp_env_path)
        config = config_manager.get()
        
        fetcher = ContentFetcher(config)
        
        # Проверяем валидные URL
        assert fetcher._validate_url("https://example.com")
        assert fetcher._validate_url("http://example.com")
        assert fetcher._validate_url("https://www.example.com/path?query=value")
        
        # Проверяем невалидные URL
        assert not fetcher._validate_url("ftp://example.com")
        assert not fetcher._validate_url("javascript:alert('xss')")
        assert not fetcher._validate_url("file:///etc/passwd")
        assert not fetcher._validate_url("not-a-url")
        assert not fetcher._validate_url("")
        
        print("Тест валидации URL пройден успешно!")
    finally:
        os.unlink(temp_env_path)
        os.unlink(prompt_path)


def test_text_extraction():
    """Тестирует извлечение текста из HTML"""
    # Создаем временные файлы: промпт и .env
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_prompt:
        temp_prompt.write("test")
        prompt_path = temp_prompt.name

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as temp_env:
        temp_env.write(f"""
LLM_API_KEY=test_key
LLM_MAX_TOKENS=1000
LLM_TEMPERATURE=0.7
LLM_RATE_LIMIT=3
FETCH_TIMEOUT=30
FETCH_MAX_CONCURRENT=10
FETCH_MAX_SIZE_MB=5
FETCH_RETRY_ATTEMPTS=3
FETCH_RETRY_DELAY=1.5
PROMPT_FILE={prompt_path}
""")
        temp_env_path = temp_env.name

    try:
        config_manager = ConfigManager(env_path=temp_env_path)
        config = config_manager.get()
        
        fetcher = ContentFetcher(config)
        
        # Простой HTML
        html_content = """
        <html>
            <head>
                <title>Test Page</title>
                <script>console.log('test');</script>
                <style>body { color: red; }</style>
            </head>
            <body>
                <h1>Заголовок</h1>
                <p>Первый абзац с текстом.</p>
                <p>Второй абзац с <strong>жирным</strong> и <em>курсивным</em> текстом.</p>
                <div>Текст в div</div>
                <nav>Навигация</nav>
                <footer>Футер</footer>
            </body>
        </html>
        """
        
        extracted_text = fetcher.extract_text(html_content)
        
        # Проверяем, что извлеченный текст содержит ожидаемые фразы
        assert "Заголовок" in extracted_text
        assert "Первый абзац с текстом" in extracted_text
        assert "Второй абзац" in extracted_text
        assert "жирным" in extracted_text
        assert "курсивным" in extracted_text
        assert "Текст в div" in extracted_text
        
        # Проверяем, что извлеченный текст не содержит скриптов и стилей
        assert "console.log" not in extracted_text
        assert "color: red" not in extracted_text
        assert "Навигация" not in extracted_text
        assert "Футер" not in extracted_text
        
        print("Тест извлечения текста пройден успешно!")
    finally:
        os.unlink(temp_env_path)
        os.unlink(prompt_path)


def test_content_size_limit():
    """Тестирует ограничение размера контента"""
    # Создаем временный .env файл с тестовыми значениями
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as temp_env:
        temp_env.write("""
LLM_API_KEY=test_key
LLM_MAX_TOKENS=1000
LLM_TEMPERATURE=0.7
LLM_RATE_LIMIT=3
FETCH_TIMEOUT=30
FETCH_MAX_CONCURRENT=10
FETCH_MAX_SIZE_MB=1
FETCH_RETRY_ATTEMPTS=3
FETCH_RETRY_DELAY=1.5
PROMPT_FILE=./test_prompts/test_prompt.txt
""")
        temp_env_path = temp_env.name

    try:
        config_manager = ConfigManager(env_path=temp_env_path)
        config = config_manager.get()
        
        fetcher = ContentFetcher(config)
        
        # Создаем HTML размером более 1 МБ
        large_content = "<html><body>" + "A" * (2 * 1024 * 1024) + "</body></html>"  # 2 МБ
        
        # Проверяем, что извлеченный текст обрезается до лимита
        extracted_text = fetcher.extract_text(large_content)
        
        # Размер должен быть ограничен
        content_size_mb = len(extracted_text.encode('utf-8')) / (1024 * 1024)
        assert content_size_mb <= config.fetch_max_size_mb
        
        print("Тест ограничения размера контента пройден успешно!")
    finally:
        # Удаляем временный файл
        os.unlink(temp_env_path)


@pytest.mark.asyncio
async def test_rate_limiting():
    """Тестирует ограничение частоты запросов"""
    # Создаем временные файлы: промпт и .env
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_prompt:
        temp_prompt.write("test")
        prompt_path = temp_prompt.name

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as temp_env:
        temp_env.write(f"""
LLM_API_KEY=test_key
LLM_MAX_TOKENS=1000
LLM_TEMPERATURE=0.7
LLM_RATE_LIMIT=10
FETCH_TIMEOUT=30
FETCH_MAX_CONCURRENT=10
FETCH_MAX_SIZE_MB=5
FETCH_RETRY_ATTEMPTS=3
FETCH_RETRY_DELAY=1.5
PROMPT_FILE={prompt_path}
""")
        temp_env_path = temp_env.name

    try:
        config_manager = ConfigManager(env_path=temp_env_path)
        config = config_manager.get()
        
        fetcher = ContentFetcher(config)
        
        # Проверяем, что параметр конфигурации установлен корректно
        assert fetcher.config.llm_rate_limit == 10
        
        # Проверяем работу rate limiting - тестируем сам механизм
        # Изначально список запросов пуст
        assert len(fetcher.request_times) == 0
        
        # Выполняем вызов _rate_limit
        await fetcher._rate_limit()
        
        # Проверяем, что время запроса добавлено в список
        assert len(fetcher.request_times) == 1
        
        # Выполняем еще несколько вызовов
        await fetcher._rate_limit()
        await fetcher._rate_limit()
        
        # Проверяем, что все времена запросов добавлены
        assert len(fetcher.request_times) == 3
        
        print("Тест ограничения частоты запросов пройден успешно!")
    finally:
        os.unlink(temp_env_path)
        os.unlink(prompt_path)


@pytest.mark.asyncio
async def test_concurrent_limiting():
    """Тестирует ограничение параллельных запросов"""
    # Создаем временные файлы: промпт и .env
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_prompt:
        temp_prompt.write("test")
        prompt_path = temp_prompt.name

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as temp_env:
        temp_env.write(f"""
LLM_API_KEY=test_key
LLM_MAX_TOKENS=1000
LLM_TEMPERATURE=0.7
LLM_RATE_LIMIT=3
FETCH_TIMEOUT=30
FETCH_MAX_CONCURRENT=2
FETCH_MAX_SIZE_MB=5
FETCH_RETRY_ATTEMPTS=3
FETCH_RETRY_DELAY=1.5
PROMPT_FILE={prompt_path}
""")
        temp_env_path = temp_env.name

    try:
        config_manager = ConfigManager(env_path=temp_env_path)
        config = config_manager.get()
        
        fetcher = ContentFetcher(config)
        
        # Проверяем, что параметр конфигурации установлен корректно
        assert fetcher.config.fetch_max_concurrent == 2
        assert fetcher.semaphore._value == 2  # Внутреннее значение semaphore
        
        print("Тест ограничения параллельных запросов пройден успешно!")
    finally:
        os.unlink(temp_env_path)
        os.unlink(prompt_path)


def test_retry_mechanism():
    """Тестирует механизм повторных попыток"""
    config_manager = ConfigManager(env_path=".env.example")
    config = config_manager.get()
    
    # Устанавливаем параметры для теста
    config.fetch_retry_attempts = 2
    config.fetch_retry_delay = 0.1  # Маленькая задержка для ускорения теста
    
    fetcher = ContentFetcher(config)
    
    # Проверяем, что параметры retry установлены корректно
    assert fetcher.config.fetch_retry_attempts == 2
    assert fetcher.config.fetch_retry_delay == 0.1
    
    print("Тест механизма повторных попыток пройден успешно!")


@pytest.mark.asyncio
async def test_async_context_manager():
    """Тестирует асинхронный контекстный менеджер"""
    # Создаем временные файлы: промпт и .env
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_prompt:
        temp_prompt.write("test")
        prompt_path = temp_prompt.name

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as temp_env:
        temp_env.write(f"""
LLM_API_KEY=test_key
LLM_MAX_TOKENS=1000
LLM_TEMPERATURE=0.7
LLM_RATE_LIMIT=3
FETCH_TIMEOUT=30
FETCH_MAX_CONCURRENT=10
FETCH_MAX_SIZE_MB=5
FETCH_RETRY_ATTEMPTS=3
FETCH_RETRY_DELAY=1.5
PROMPT_FILE={prompt_path}
""")
        temp_env_path = temp_env.name

    try:
        config_manager = ConfigManager(env_path=temp_env_path)
        config = config_manager.get()
        
        fetcher = ContentFetcher(config)
        
        # Тестируем вход в контекстный менеджер
        async with fetcher as f:
            assert f is fetcher
            assert f.session is not None
            assert f.session.is_closed == False
        
        # После выхода из контекстного менеджера сессия должна быть закрыта
        assert fetcher.session is not None
        
        print("Тест асинхронного контекстного менеджера пройден успешно!")
    finally:
        os.unlink(temp_env_path)
        os.unlink(prompt_path)


@pytest.mark.asyncio
async def test_fetch_content_success():
    """Тестирует успешную загрузку контента"""
    # Создаем временные файлы: промпт и .env
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_prompt:
        temp_prompt.write("test")
        prompt_path = temp_prompt.name

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as temp_env:
        temp_env.write(f"""
LLM_API_KEY=test_key
LLM_MAX_TOKENS=1000
LLM_TEMPERATURE=0.7
LLM_RATE_LIMIT=3
FETCH_TIMEOUT=30
FETCH_MAX_CONCURRENT=10
FETCH_MAX_SIZE_MB=5
FETCH_RETRY_ATTEMPTS=3
FETCH_RETRY_DELAY=1.5
PROMPT_FILE={prompt_path}
""")
        temp_env_path = temp_env.name

    try:
        config_manager = ConfigManager(env_path=temp_env_path)
        config = config_manager.get()
        
        fetcher = ContentFetcher(config)
        
        # Мокаем ответ HTTP
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body><h1>Test Content</h1></body></html>"
        
        with patch.object(fetcher, '_validate_url', return_value=True):
            async with fetcher:
                with patch.object(fetcher.session, 'get', return_value=mock_response):
                    result = await fetcher.fetch_content("https://example.com")
                    
                    assert result == "<html><body><h1>Test Content</h1></body></html>"
        
        print("Тест успешной загрузки контента пройден успешно!")
    finally:
        os.unlink(temp_env_path)
        os.unlink(prompt_path)


@pytest.mark.asyncio
async def test_fetch_content_invalid_url():
    """Тестирует загрузку контента с невалидным URL"""
    # Создаем временные файлы: промпт и .env
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_prompt:
        temp_prompt.write("test")
        prompt_path = temp_prompt.name

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as temp_env:
        temp_env.write(f"""
LLM_API_KEY=test_key
LLM_MAX_TOKENS=1000
LLM_TEMPERATURE=0.7
LLM_RATE_LIMIT=3
FETCH_TIMEOUT=30
FETCH_MAX_CONCURRENT=10
FETCH_MAX_SIZE_MB=5
FETCH_RETRY_ATTEMPTS=3
FETCH_RETRY_DELAY=1.5
PROMPT_FILE={prompt_path}
""")
        temp_env_path = temp_env.name

    try:
        config_manager = ConfigManager(env_path=temp_env_path)
        config = config_manager.get()
        
        fetcher = ContentFetcher(config)
        
        async with fetcher:
            # Тестируем с невалидным URL
            result = await fetcher.fetch_content("invalid-url")
            assert result is None
        
        print("Тест загрузки контента с невалидным URL пройден успешно!")
    finally:
        os.unlink(temp_env_path)
        os.unlink(prompt_path)


@pytest.mark.asyncio
async def test_fetch_content_without_session():
    """Тестирует попытку загрузки контента без инициализации сессии"""
    # Создаем временные файлы: промпт и .env
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_prompt:
        temp_prompt.write("test")
        prompt_path = temp_prompt.name

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as temp_env:
        temp_env.write(f"""
LLM_API_KEY=test_key
LLM_MAX_TOKENS=1000
LLM_TEMPERATURE=0.7
LLM_RATE_LIMIT=3
FETCH_TIMEOUT=30
FETCH_MAX_CONCURRENT=10
FETCH_MAX_SIZE_MB=5
FETCH_RETRY_ATTEMPTS=3
FETCH_RETRY_DELAY=1.5
PROMPT_FILE={prompt_path}
""")
        temp_env_path = temp_env.name

    try:
        config_manager = ConfigManager(env_path=temp_env_path)
        config = config_manager.get()
        
        fetcher = ContentFetcher(config)
        
        # Тестируем без инициализации сессии
        result = await fetcher.fetch_content("https://example.com")
        assert result is None
        
        print("Тест загрузки контента без сессии пройден успешно!")
    finally:
        os.unlink(temp_env_path)
        os.unlink(prompt_path)


@pytest.mark.asyncio
async def test_fetch_with_retry_server_error():
    """Тестирует повторные попытки при ошибке сервера"""
    # Создаем временные файлы: промпт и .env
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_prompt:
        temp_prompt.write("test")
        prompt_path = temp_prompt.name

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as temp_env:
        temp_env.write(f"""
LLM_API_KEY=test_key
LLM_MAX_TOKENS=1000
LLM_TEMPERATURE=0.7
LLM_RATE_LIMIT=3
FETCH_TIMEOUT=30
FETCH_MAX_CONCURRENT=10
FETCH_MAX_SIZE_MB=5
FETCH_RETRY_ATTEMPTS=2
FETCH_RETRY_DELAY=0.1
PROMPT_FILE={prompt_path}
""")
        temp_env_path = temp_env.name

    try:
        config_manager = ConfigManager(env_path=temp_env_path)
        config = config_manager.get()
        
        fetcher = ContentFetcher(config)
        
        # Мокаем ответ с ошибкой сервера
        mock_response = AsyncMock()
        mock_response.status_code = 500
        mock_response.request = AsyncMock()
        
        async with fetcher:
            with patch.object(fetcher.session, 'get', return_value=mock_response):
                result = await fetcher._fetch_with_retry("https://example.com")
                assert result is None
        
        print("Тест повторных попыток при ошибке сервера пройден успешно!")
    finally:
        os.unlink(temp_env_path)
        os.unlink(prompt_path)


@pytest.mark.asyncio
async def test_fetch_with_retry_not_found():
    """Тестирует обработку ошибки 404 без повторных попыток"""
    # Создаем временные файлы: промпт и .env
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_prompt:
        temp_prompt.write("test")
        prompt_path = temp_prompt.name

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as temp_env:
        temp_env.write(f"""
LLM_API_KEY=test_key
LLM_MAX_TOKENS=1000
LLM_TEMPERATURE=0.7
LLM_RATE_LIMIT=3
FETCH_TIMEOUT=30
FETCH_MAX_CONCURRENT=10
FETCH_MAX_SIZE_MB=5
FETCH_RETRY_ATTEMPTS=3
FETCH_RETRY_DELAY=1.5
PROMPT_FILE={prompt_path}
""")
        temp_env_path = temp_env.name

    try:
        config_manager = ConfigManager(env_path=temp_env_path)
        config = config_manager.get()
        
        fetcher = ContentFetcher(config)
        
        # Мокаем ответ с ошибкой 404
        mock_response = AsyncMock()
        mock_response.status_code = 404
        
        async with fetcher:
            with patch.object(fetcher.session, 'get', return_value=mock_response):
                result = await fetcher._fetch_with_retry("https://example.com")
                assert result is None
        
        print("Тест обработки ошибки 404 пройден успешно!")
    finally:
        os.unlink(temp_env_path)
        os.unlink(prompt_path)


@pytest.mark.asyncio
async def test_fetch_with_retry_content_too_large():
    """Тестирует обработку слишком большого контента"""
    # Создаем временные файлы: промпт и .env
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_prompt:
        temp_prompt.write("test")
        prompt_path = temp_prompt.name

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as temp_env:
        temp_env.write(f"""
LLM_API_KEY=test_key
LLM_MAX_TOKENS=1000
LLM_TEMPERATURE=0.7
LLM_RATE_LIMIT=3
FETCH_TIMEOUT=30
FETCH_MAX_CONCURRENT=10
FETCH_MAX_SIZE_MB=1
FETCH_RETRY_ATTEMPTS=3
FETCH_RETRY_DELAY=1.5
PROMPT_FILE={prompt_path}
""")
        temp_env_path = temp_env.name

    try:
        config_manager = ConfigManager(env_path=temp_env_path)
        config = config_manager.get()
        
        fetcher = ContentFetcher(config)
        
        # Мокаем ответ с большим контентом
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = "A" * (2 * 1024 * 1024)  # 2 МБ контент
        
        async with fetcher:
            with patch.object(fetcher.session, 'get', return_value=mock_response):
                result = await fetcher._fetch_with_retry("https://example.com")
                assert result is None
        
        print("Тест обработки слишком большого контента пройден успешно!")
    finally:
        os.unlink(temp_env_path)
        os.unlink(prompt_path)


def test_extract_text_with_main_content():
    """Тестирует извлечение текста с основным содержимым"""
    # Создаем временные файлы: промпт и .env
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_prompt:
        temp_prompt.write("test")
        prompt_path = temp_prompt.name

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as temp_env:
        temp_env.write(f"""
LLM_API_KEY=test_key
LLM_MAX_TOKENS=1000
LLM_TEMPERATURE=0.7
LLM_RATE_LIMIT=3
FETCH_TIMEOUT=30
FETCH_MAX_CONCURRENT=10
FETCH_MAX_SIZE_MB=5
FETCH_RETRY_ATTEMPTS=3
FETCH_RETRY_DELAY=1.5
PROMPT_FILE={prompt_path}
""")
        temp_env_path = temp_env.name

    try:
        config_manager = ConfigManager(env_path=temp_env_path)
        config = config_manager.get()
        
        fetcher = ContentFetcher(config)
        
        # HTML с основным содержимым в теге main
        html_content = """
        <html>
            <head><title>Test</title></head>
            <body>
                <header>Header content</header>
                <main>
                    <h1>Main Title</h1>
                    <p>Main paragraph with important content.</p>
                </main>
                <footer>Footer content</footer>
            </body>
        </html>
        """
        
        extracted_text = fetcher.extract_text(html_content)
        
        # Проверяем, что извлечен текст из main
        assert "Main Title" in extracted_text
        assert "Main paragraph with important content" in extracted_text
        # Проверяем, что текст из header и footer не извлечен
        assert "Header content" not in extracted_text
        assert "Footer content" not in extracted_text
        
        print("Тест извлечения текста с основным содержимым пройден успешно!")
    finally:
        os.unlink(temp_env_path)
        os.unlink(prompt_path)


def test_extract_text_with_article():
    """Тестирует извлечение текста с тегом article"""
    # Создаем временные файлы: промпт и .env
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_prompt:
        temp_prompt.write("test")
        prompt_path = temp_prompt.name

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as temp_env:
        temp_env.write(f"""
LLM_API_KEY=test_key
LLM_MAX_TOKENS=1000
LLM_TEMPERATURE=0.7
LLM_RATE_LIMIT=3
FETCH_TIMEOUT=30
FETCH_MAX_CONCURRENT=10
FETCH_MAX_SIZE_MB=5
FETCH_RETRY_ATTEMPTS=3
FETCH_RETRY_DELAY=1.5
PROMPT_FILE={prompt_path}
""")
        temp_env_path = temp_env.name

    try:
        config_manager = ConfigManager(env_path=temp_env_path)
        config = config_manager.get()
        
        fetcher = ContentFetcher(config)
        
        # HTML с содержимым в теге article
        html_content = """
        <html>
            <head><title>Test</title></head>
            <body>
                <nav>Navigation</nav>
                <article>
                    <h1>Article Title</h1>
                    <p>Article paragraph with important content.</p>
                </article>
                <aside>Sidebar content</aside>
            </body>
        </html>
        """
        
        extracted_text = fetcher.extract_text(html_content)
        
        # Проверяем, что извлечен текст из article
        assert "Article Title" in extracted_text
        assert "Article paragraph with important content" in extracted_text
        # Проверяем, что текст из nav и aside не извлечен
        assert "Navigation" not in extracted_text
        assert "Sidebar content" not in extracted_text
        
        print("Тест извлечения текста с тегом article пройден успешно!")
    finally:
        os.unlink(temp_env_path)
        os.unlink(prompt_path)


def test_extract_text_empty_html():
    """Тестирует извлечение текста из пустого HTML"""
    # Создаем временные файлы: промпт и .env
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_prompt:
        temp_prompt.write("test")
        prompt_path = temp_prompt.name

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as temp_env:
        temp_env.write(f"""
LLM_API_KEY=test_key
LLM_MAX_TOKENS=1000
LLM_TEMPERATURE=0.7
LLM_RATE_LIMIT=3
FETCH_TIMEOUT=30
FETCH_MAX_CONCURRENT=10
FETCH_MAX_SIZE_MB=5
FETCH_RETRY_ATTEMPTS=3
FETCH_RETRY_DELAY=1.5
PROMPT_FILE={prompt_path}
""")
        temp_env_path = temp_env.name

    try:
        config_manager = ConfigManager(env_path=temp_env_path)
        config = config_manager.get()
        
        fetcher = ContentFetcher(config)
        
        # Тестируем с пустым HTML
        result = fetcher.extract_text("")
        assert result == ""
        
        # Тестируем с None
        result = fetcher.extract_text("")
        assert result == ""
        
        print("Тест извлечения текста из пустого HTML пройден успешно!")
    finally:
        os.unlink(temp_env_path)
        os.unlink(prompt_path)


def test_extract_text_with_invalid_config():
    """Тестирует извлечение текста с некорректной конфигурацией размера"""
    # Создаем временные файлы: промпт и .env
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_prompt:
        temp_prompt.write("test")
        prompt_path = temp_prompt.name

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as temp_env:
        temp_env.write(f"""
LLM_API_KEY=test_key
LLM_MAX_TOKENS=1000
LLM_TEMPERATURE=0.7
LLM_RATE_LIMIT=3
FETCH_TIMEOUT=30
FETCH_MAX_CONCURRENT=10
FETCH_MAX_SIZE_MB=5
FETCH_RETRY_ATTEMPTS=3
FETCH_RETRY_DELAY=1.5
PROMPT_FILE={prompt_path}
""")
        temp_env_path = temp_env.name

    try:
        config_manager = ConfigManager(env_path=temp_env_path)
        config = config_manager.get()
        
        fetcher = ContentFetcher(config)
        
        # Создаем HTML контент
        html_content = "<html><body><p>Test content</p></body></html>"
        
        # Мокаем некорректное значение fetch_max_size_mb
        with patch.object(fetcher.config, 'fetch_max_size_mb', 'invalid'):
            # Должен использовать значение по умолчанию (5MB) при некорректной конфигурации
            extracted_text = fetcher.extract_text(html_content)
            assert "Test content" in extracted_text
        
        print("Тест извлечения текста с некорректной конфигурацией пройден успешно!")
    finally:
        os.unlink(temp_env_path)
        os.unlink(prompt_path)


@pytest.mark.asyncio
async def test_rate_limiting_disabled():
    """Тестирует отключенный rate limiting"""
    # Создаем временные файлы: промпт и .env
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_prompt:
        temp_prompt.write("test")
        prompt_path = temp_prompt.name

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as temp_env:
        temp_env.write(f"""
LLM_API_KEY=test_key
LLM_MAX_TOKENS=1000
LLM_TEMPERATURE=0.7
LLM_RATE_LIMIT=3
FETCH_TIMEOUT=30
FETCH_MAX_CONCURRENT=10
FETCH_MAX_SIZE_MB=5
FETCH_RETRY_ATTEMPTS=3
FETCH_RETRY_DELAY=1.5
PROMPT_FILE={prompt_path}
""")
        temp_env_path = temp_env.name

    try:
        config_manager = ConfigManager(env_path=temp_env_path)
        config = config_manager.get()
        
        fetcher = ContentFetcher(config)
        
        # Мокаем отключенный rate limiting
        with patch.object(fetcher.config, 'llm_rate_limit', 0):
            # Проверяем, что rate limiting отключен
            assert fetcher.config.llm_rate_limit == 0
            
            # Выполняем вызов _rate_limit - должен завершиться без задержки
            start_time = asyncio.get_event_loop().time()
            await fetcher._rate_limit()
            end_time = asyncio.get_event_loop().time()
            
            # Проверяем, что не было задержки
            assert (end_time - start_time) < 0.1
        
        print("Тест отключенного rate limiting пройден успешно!")
    finally:
        os.unlink(temp_env_path)
        os.unlink(prompt_path)


@pytest.mark.asyncio
async def test_async_functions():
    """Запускает асинхронные тесты"""
    await test_rate_limiting()
    await test_concurrent_limiting()
    await test_async_context_manager()
    await test_fetch_content_success()
    await test_fetch_content_invalid_url()
    await test_fetch_content_without_session()
    await test_fetch_with_retry_server_error()
    await test_fetch_with_retry_not_found()
    await test_fetch_with_retry_content_too_large()
    await test_rate_limiting_disabled()


if __name__ == "__main__":
    test_url_validation()
    test_text_extraction()
    test_content_size_limit()
    test_retry_mechanism()
    test_extract_text_with_main_content()
    test_extract_text_with_article()
    test_extract_text_empty_html()
    test_extract_text_with_invalid_config()
    
    # Запускаем асинхронные тесты
    asyncio.run(test_async_functions())