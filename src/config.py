"""
Модуль config.py
Управляет конфигурацией приложения через .env-файл.
Обеспечивает валидацию и доступ к параметрам конфигурации.
"""

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

from .logger import get_logger

logger = get_logger(__name__)


@dataclass
class Config:
    """
    Класс конфигурации приложения.
    Все поля загружаются из .env-файла.
    """

    # LLM API настройки
    llm_api_key: str
    llm_base_url: str
    llm_model: str
    llm_max_tokens: int
    llm_temperature: float
    llm_rate_limit: int

    # Настройки загрузки контента
    fetch_timeout: int
    fetch_max_concurrent: int
    fetch_max_size_mb: int
    fetch_retry_attempts: int
    fetch_retry_delay: float
    fetch_max_redirects: int

    # Настройки вывода
    output_dir: str
    markdown_include_metadata: bool
    generate_mermaid_diagram: bool

    # Путь к файлу с промптом
    prompt_file: str

    # Настройки логирования
    log_level: str
    log_file: str
    
    # Опциональные настройки LLM API
    llm_socks5_proxy: Optional[str] = None


class ConfigManager:
    """
    Менеджер конфигурации приложения.
    Загружает параметры из .env-файла и предоставляет валидацию.
    """

    def __init__(self, env_path: Optional[str] = None):
        """
        Инициализация менеджера конфигурации.

        Аргументы:
            env_path: Путь к .env-файлу (по умолчанию .env в корне проекта)
        """
        logger.debug(f"Инициализация ConfigManager с env_path: {env_path}")

        load_dotenv(env_path or ".env", override=True)
        self.config = self._load_config()
        self._validate_config()

        logger.info("ConfigManager успешно инициализирован")
        logger.debug(
            f"Загружена конфигурация: output_dir={self.config.output_dir}, "
            f"log_level={self.config.log_level}"
        )

    def _load_config(self) -> Config:
        """
        Загружает конфигурацию из переменных окружения.

        Возвращает:
            Config: Объект с загруженной конфигурацией
        """
        logger.debug("Загрузка конфигурации из переменных окружения")

        try:
            config = Config(
                llm_api_key=os.getenv("LLM_API_KEY", ""),
                llm_base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
                llm_model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
                llm_max_tokens=int(os.getenv("LLM_MAX_TOKENS", "1000")),
                llm_temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
                llm_rate_limit=int(os.getenv("LLM_RATE_LIMIT", "3")),
                fetch_timeout=int(os.getenv("FETCH_TIMEOUT", "30")),
                fetch_max_concurrent=int(os.getenv("FETCH_MAX_CONCURRENT", "10")),
                fetch_max_size_mb=int(os.getenv("FETCH_MAX_SIZE_MB", "5")),
                fetch_retry_attempts=int(os.getenv("FETCH_RETRY_ATTEMPTS", "3")),
                fetch_retry_delay=float(os.getenv("FETCH_RETRY_DELAY", "1.5")),
                fetch_max_redirects=int(os.getenv("FETCH_MAX_REDIRECTS", "5")),
                output_dir=os.getenv("OUTPUT_DIR", "./bookmarks_export"),
                markdown_include_metadata=os.getenv(
                    "MARKDOWN_INCLUDE_METADATA", "true"
                ).lower()
                == "true",
                generate_mermaid_diagram=os.getenv(
                    "GENERATE_MERMAID_DIAGRAM", "true"
                ).lower()
                == "true",
                prompt_file=os.getenv("PROMPT_FILE", "./prompts/summarize_prompt.txt"),
                log_level=os.getenv("LOG_LEVEL", "INFO"),
                log_file=os.getenv("LOG_FILE", "./bookmarks_export.log"),
                llm_socks5_proxy=os.getenv("LLM_SOCKS5_PROXY"),
            )

            logger.debug("Конфигурация успешно загружена из переменных окружения")
            return config

        except ValueError as e:
            logger.error(f"Ошибка при загрузке конфигурации: {e}")
            raise

    def _validate_config(self) -> None:
        """
        Валидирует обязательные параметры конфигурации.
        Вызывает исключение при отсутствии критичных параметров.

        Raises:
            ValueError: Если отсутствуют обязательные параметры
        """
        logger.debug("Валидация конфигурации")

        validation_errors = []

        if not self.config.llm_api_key:
            error_msg = "LLM_API_KEY не задан в .env-файле"
            validation_errors.append(error_msg)
            logger.error(error_msg)

        if not os.path.exists(self.config.prompt_file):
            error_msg = f"Файл промпта не найден: {self.config.prompt_file}"
            validation_errors.append(error_msg)
            logger.error(error_msg)

        # Проверка корректности числовых параметров
        if self.config.llm_max_tokens <= 0:
            error_msg = f"LLM_MAX_TOKENS должен быть положительным числом: {self.config.llm_max_tokens}"
            validation_errors.append(error_msg)
            logger.error(error_msg)

        if self.config.fetch_timeout <= 0:
            error_msg = f"FETCH_TIMEOUT должен быть положительным числом: {self.config.fetch_timeout}"
            validation_errors.append(error_msg)
            logger.error(error_msg)

        if self.config.fetch_max_concurrent <= 0:
            error_msg = f"FETCH_MAX_CONCURRENT должен быть положительным числом: {self.config.fetch_max_concurrent}"
            validation_errors.append(error_msg)
            logger.error(error_msg)

        if self.config.fetch_max_redirects < 0:
            error_msg = f"FETCH_MAX_REDIRECTS должен быть неотрицательным числом: {self.config.fetch_max_redirects}"
            validation_errors.append(error_msg)
            logger.error(error_msg)

        if validation_errors:
            logger.error(
                f"Валидация конфигурации не пройдена: {len(validation_errors)} ошибок"
            )
            raise ValueError(
                f"Ошибки валидации конфигурации: {'; '.join(validation_errors)}"
            )

        logger.info("Валидация конфигурации успешно пройдена")

    def get(self) -> Config:
        """
        Возвращает объект конфигурации.

        Возвращает:
            Config: Объект с конфигурацией
        """
        logger.debug("Запрос объекта конфигурации")
        return self.config


def setup_logging(log_level: str = "INFO") -> None:
    """
    Настраивает логирование для приложения.

    Аргументы:
        log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Примечание:
        Эта функция оставлена для обратной совместимости.
        Рекомендуется использовать функцию setup_logging из модуля logger.
    """
    logger.warning(
        "Используется устаревшая функция setup_logging из config.py. "
        "Рекомендуется использовать setup_logging из модуля logger."
    )
