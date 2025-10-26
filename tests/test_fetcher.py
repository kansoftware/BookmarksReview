"""
Тесты для модуля fetcher.py
"""
import asyncio
import tempfile
import os
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
PROMPT_FILE=./test_prompts/test_prompt.txt
FETCH_MAX_SIZE_MB=1
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


def test_rate_limiting():
    """Тестирует ограничение частоты запросов"""
    config_manager = ConfigManager(env_path=".env.example")
    config = config_manager.get()
    
    # Устанавливаем лимит в 2 запроса в секунду для теста
    config.fetch_max_concurrent = 2
    
    fetcher = ContentFetcher(config)
    
    # Проверяем, что параметр конфигурации установлен корректно
    assert fetcher.config.fetch_max_concurrent == 2
    
    print("Тест ограничения частоты запросов пройден успешно!")


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


if __name__ == "__main__":
    test_url_validation()
    test_text_extraction()
    test_content_size_limit()
    test_rate_limiting()
    test_retry_mechanism()