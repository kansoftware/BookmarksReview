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


if __name__ == "__main__":
    test_config_loading()
    test_config_validation()
    test_config_default_values()