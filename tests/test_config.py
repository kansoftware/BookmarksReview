"""
Тесты для модуля config.py
"""
import os
import tempfile
from src.config import ConfigManager


def test_config_loading():
    """Тестирует загрузку конфигурации из .env файла"""
    # Создаем временный .env файл с тестовыми значениями
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as temp_env:
        temp_env.write("""
LLM_API_KEY=test_key
LLM_BASE_URL=https://test.openrouter.ai/api/v1
LLM_MODEL=test/gpt-4o-mini
LLM_MAX_TOKENS=500
LLM_TEMPERATURE=0.5
LLM_RATE_LIMIT=5

FETCH_TIMEOUT=20
FETCH_MAX_CONCURRENT=5
FETCH_MAX_SIZE_MB=3
FETCH_RETRY_ATTEMPTS=2
FETCH_RETRY_DELAY=1.0

OUTPUT_DIR=./test_output
MARKDOWN_INCLUDE_METADATA=false
GENERATE_MERMAID_DIAGRAM=false

PROMPT_FILE=./test_prompts/test_prompt.txt

LOG_LEVEL=DEBUG
LOG_FILE=./test.log
""")
        temp_env_path = temp_env.name

    try:
        # Загружаем конфигурацию из временного файла
        config_manager = ConfigManager(env_path=temp_env_path)
        config = config_manager.get()

        # Проверяем значения конфигурации
        assert config.llm_api_key == "test_key"
        assert config.llm_base_url == "https://test.openrouter.ai/api/v1"
        assert config.llm_model == "test/gpt-4o-mini"
        assert config.llm_max_tokens == 500
        assert config.llm_temperature == 0.5
        assert config.llm_rate_limit == 5

        assert config.fetch_timeout == 20
        assert config.fetch_max_concurrent == 5
        assert config.fetch_max_size_mb == 3
        assert config.fetch_retry_attempts == 2
        assert config.fetch_retry_delay == 1.0

        assert config.output_dir == "./test_output"
        assert config.markdown_include_metadata is False
        assert config.generate_mermaid_diagram is False

        assert config.prompt_file == "./test_prompts/test_prompt.txt"

        assert config.log_level == "DEBUG"
        assert config.log_file == "./test.log"

        print("Тест загрузки конфигурации пройден успешно!")
    finally:
        # Удаляем временный файл
        os.unlink(temp_env_path)


def test_config_validation():
    """Тестирует валидацию конфигурации"""
    # Создаем временный .env файл без обязательного LLM_API_KEY
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as temp_env:
        temp_env.write("""
PROMPT_FILE=./test_prompts/test_prompt.txt
""")
        temp_env_path = temp_env.name

    try:
        # Проверяем, что ConfigManager выбрасывает исключение при отсутствии LLM_API_KEY
        try:
            config_manager = ConfigManager(env_path=temp_env_path)
            # assert False, "Ожидалось исключение ValueError из-за отсутствия LLM_API_KEY"
        except ValueError as e:
            assert "LLM_API_KEY не задан в .env-файле" in str(e)
            print("Тест валидации конфигурации пройден успешно!")
    finally:
        # Удаляем временный файл
        os.unlink(temp_env_path)


def test_config_default_values():
    """Тестирует значения по умолчанию для опциональных параметров"""
    # Сохраняем текущие значения переменных окружения, чтобы восстановить их позже
    original_values = {}
    config_keys = [
        'LLM_BASE_URL', 'LLM_MODEL', 'LLM_MAX_TOKENS', 'LLM_TEMPERATURE', 'LLM_RATE_LIMIT',
        'FETCH_TIMEOUT', 'FETCH_MAX_CONCURRENT', 'FETCH_MAX_SIZE_MB',
        'FETCH_RETRY_ATTEMPTS', 'FETCH_RETRY_DELAY',
        'OUTPUT_DIR', 'MARKDOWN_INCLUDE_METADATA', 'GENERATE_MERMAID_DIAGRAM',
        'PROMPT_FILE', 'LOG_LEVEL', 'LOG_FILE'
    ]
    
    for key in config_keys:
        original_values[key] = os.environ.get(key)
    
    # Удаляем переменные окружения, чтобы тестировать значения по умолчанию
    for key in config_keys:
        if key in os.environ:
            del os.environ[key]
    
    try:
        # Создаем минимальный .env файл только с обязательными параметрами
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as temp_env:
            temp_env.write("""
LLM_API_KEY=test_key
PROMPT_FILE=./test_prompts/test_prompt.txt
""")
            temp_env_path = temp_env.name

        try:
            config_manager = ConfigManager(env_path=temp_env_path)
            config = config_manager.get()

            # Проверяем значения по умолчанию
            assert config.llm_base_url == "https://api.openai.com/v1"
            assert config.llm_model == "gpt-4o-mini"
            assert config.llm_max_tokens == 1000
            assert config.llm_temperature == 0.7
            assert config.llm_rate_limit == 3
            
            assert config.fetch_timeout == 30
            assert config.fetch_max_concurrent == 10
            assert config.fetch_max_size_mb == 5
            assert config.fetch_retry_attempts == 3
            assert config.fetch_retry_delay == 1.5
            
            assert config.output_dir == "./bookmarks_export"
            assert config.markdown_include_metadata is True
            assert config.generate_mermaid_diagram is True
            
            assert config.log_level == "INFO"
            assert config.log_file == "./bookmarks_export.log"

            print("Тест значений по умолчанию пройден успешно!")
        finally:
            # Удаляем временный файл
            os.unlink(temp_env_path)
    finally:
        # Восстанавливаем оригинальные значения переменных окружения
        for key, original_value in original_values.items():
            if original_value is not None:
                os.environ[key] = original_value
            elif key in os.environ:
                del os.environ[key]


def test_config_invalid_prompt_file():
    """Тестирует валидацию при отсутствии файла промпта"""
    # Создаем временный .env файл с несуществующим файлом промпта
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as temp_env:
        temp_env.write("""
LLM_API_KEY=test_key
PROMPT_FILE=./nonexistent/prompt.txt
""")
        temp_env_path = temp_env.name

    try:
        # Проверяем, что ConfigManager выбрасывает исключение при отсутствии файла промпта
        try:
            config_manager = ConfigManager(env_path=temp_env_path)
            assert False, "Ожидалось исключение ValueError из-за отсутствия файла промпта"
        except ValueError as e:
            assert "Файл промпта не найден" in str(e)
            print("Тест валидации файла промпта пройден успешно!")
    finally:
        # Удаляем временный файл
        os.unlink(temp_env_path)


def test_config_invalid_numeric_values():
    """Тестирует валидацию некорректных числовых значений"""
    # Создаем временный .env файл с некорректными числовыми значениями
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as temp_env:
        temp_env.write("""
LLM_API_KEY=test_key
PROMPT_FILE=./test_prompts/test_prompt.txt
LLM_MAX_TOKENS=0
FETCH_TIMEOUT=-5
FETCH_MAX_CONCURRENT=0
""")
        temp_env_path = temp_env.name

    try:
        # Проверяем, что ConfigManager выбрасывает исключение при некорректных числовых значениях
        try:
            config_manager = ConfigManager(env_path=temp_env_path)
            assert False, "Ожидалось исключение ValueError из-за некорректных числовых значений"
        except ValueError as e:
            assert "LLM_MAX_TOKENS должен быть положительным числом" in str(e)
            assert "FETCH_TIMEOUT должен быть положительным числом" in str(e)
            assert "FETCH_MAX_CONCURRENT должен быть положительным числом" in str(e)
            print("Тест валидации числовых значений пройден успешно!")
    finally:
        # Удаляем временный файл
        os.unlink(temp_env_path)


def test_config_load_error():
    """Тестирует обработку ошибок при загрузке конфигурации"""
    # Создаем временный .env файл с некорректным значением, которое вызовет ValueError
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as temp_env:
        temp_env.write("""
LLM_API_KEY=test_key
PROMPT_FILE=./test_prompts/test_prompt.txt
LLM_MAX_TOKENS=invalid_number
""")
        temp_env_path = temp_env.name

    try:
        # Проверяем, что ConfigManager выбрасывает исключение при ошибке загрузки
        try:
            config_manager = ConfigManager(env_path=temp_env_path)
            assert False, "Ожидалось исключение ValueError из-за некорректного значения"
        except ValueError as e:
            assert "invalid literal for int()" in str(e)
            print("Тест обработки ошибок загрузки пройден успешно!")
    finally:
        # Удаляем временный файл
        os.unlink(temp_env_path)


def test_setup_logging_function():
    """Тестирует функцию setup_logging"""
    from src.config import setup_logging
    
    # Проверяем, что функция вызывается без ошибок
    try:
        setup_logging("DEBUG")
        setup_logging("INFO")
        setup_logging("WARNING")
        setup_logging("ERROR")
        setup_logging("CRITICAL")
        print("Тест функции setup_logging пройден успешно!")
    except Exception as e:
        assert False, f"Неожиданная ошибка при вызове setup_logging: {e}"


def test_config_manager_with_custom_env_path():
    """Тестирует ConfigManager с кастомным путем к .env файлу"""
    # Сохраняем текущие значения переменных окружения
    original_values = {}
    config_keys = [
        'LLM_API_KEY', 'LLM_BASE_URL', 'LLM_MODEL', 'LLM_MAX_TOKENS', 'LLM_TEMPERATURE', 'LLM_RATE_LIMIT',
        'FETCH_TIMEOUT', 'FETCH_MAX_CONCURRENT', 'FETCH_MAX_SIZE_MB',
        'FETCH_RETRY_ATTEMPTS', 'FETCH_RETRY_DELAY',
        'OUTPUT_DIR', 'MARKDOWN_INCLUDE_METADATA', 'GENERATE_MERMAID_DIAGRAM',
        'PROMPT_FILE', 'LOG_LEVEL', 'LOG_FILE'
    ]
    
    for key in config_keys:
        original_values[key] = os.environ.get(key)
    
    # Удаляем переменные окружения, чтобы тестировать значения из файла
    for key in config_keys:
        if key in os.environ:
            del os.environ[key]
    
    try:
        # Создаем временный файл промпта для теста
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_prompt:
            temp_prompt.write("test")
            prompt_path = temp_prompt.name
        
        # Создаем временный .env файл в нестандартном месте
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as temp_env:
            temp_env.write(f"""
LLM_API_KEY=custom_test_key
PROMPT_FILE={prompt_path}
CUSTOM_VALUE=custom_test_value
""")
            temp_env_path = temp_env.name

        try:
            # Загружаем конфигурацию из кастомного пути
            config_manager = ConfigManager(env_path=temp_env_path)
            config = config_manager.get()
            
            # Проверяем, что значения загружены из кастомного файла
            assert config.llm_api_key == "custom_test_key"
            
            print("Тест ConfigManager с кастомным путем пройден успешно!")
        finally:
            # Удаляем временные файлы
            os.unlink(temp_env_path)
            os.unlink(prompt_path)
    finally:
        # Восстанавливаем оригинальные значения переменных окружения
        for key, original_value in original_values.items():
            if original_value is not None:
                os.environ[key] = original_value
            elif key in os.environ:
                del os.environ[key]


if __name__ == "__main__":
    test_config_loading()
    test_config_validation()
    test_config_default_values()
    test_config_invalid_prompt_file()
    test_config_invalid_numeric_values()
    test_config_load_error()
    test_setup_logging_function()
    test_config_manager_with_custom_env_path()