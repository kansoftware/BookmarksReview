"""
Модуль utils.py
Содержит вспомогательные утилиты для различных операций проекта.
Обеспечивает переиспользуемые функции для работы с путями, текстом, датами и валидацией.
"""

import asyncio
import hashlib
import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional, Union
from urllib.parse import urlparse

# Настройка логера для модуля
logger = logging.getLogger(__name__)


class PathUtils:
    """Утилиты для работы с путями файловой системы."""

    @staticmethod
    def ensure_dir(path: Union[str, Path]) -> Path:
        """
        Гарантирует существование директории.

        Аргументы:
            path: Путь к директории

        Возвращает:
            Path: Объект Path созданной директории
        """
        path_obj = Path(path)
        path_obj.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Директория создана или уже существует: {path_obj}")
        return path_obj

    @staticmethod
    def safe_filename(filename: str) -> str:
        """
        Создает безопасное имя файла, удаляя недопустимые символы.

        Аргументы:
            filename: Исходное имя файла

        Возвращает:
            str: Безопасное имя файла
        """
        # Удаляем или заменяем недопустимые символы
        # Сохраняем кириллицу, латиницу, цифры, пробелы, дефисы и подчеркивания
        sanitized = re.sub(r'[<>:"/\\|?*]', "", filename)

        # Заменяем множественные пробелы на один
        sanitized = re.sub(r"\s+", " ", sanitized)

        # Удаляем пробелы в начале и конце
        sanitized = sanitized.strip()

        # Ограничиваем длину имени (максимум 255 символов для большинства файловых систем)
        max_length = 255
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length].rstrip()

        # Если имя стало пустым после очистки, используем значение по умолчанию
        if not sanitized:
            sanitized = "unnamed"

        return sanitized

    @staticmethod
    def get_relative_path(path: Path, base: Path) -> Path:
        """
        Вычисляет относительный путь.

        Аргументы:
            path: Целевой путь
            base: Базовый путь

        Возвращает:
            Path: Относительный путь
        """
        try:
            return path.relative_to(base)
        except ValueError:
            # Если путь не является относительным к базе, возвращаем исходный
            logger.warning(f"Путь {path} не является относительным к базе {base}")
            return path


class TextUtils:
    """Утилиты для обработки текста и строк."""

    @staticmethod
    def clean_text(text: Optional[str]) -> str:
        """
        Очищает текст от лишних пробелов и символов.

        Аргументы:
            text: Исходный текст (может быть None)

        Возвращает:
            str: Очищенный текст
        """
        if not text:
            return ""

        # Удаляем лишние пробелы и символы переноса строки
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split(" "))
        cleaned_text = " ".join(chunk for chunk in chunks if chunk)

        return cleaned_text

    @staticmethod
    def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
        """
        Обрезает текст до указанной длины.

        Аргументы:
            text: Исходный текст
            max_length: Максимальная длина
            suffix: Суффикс для обозначения обрезки

        Возвращает:
            str: Обрезанный текст
        """
        if len(text) <= max_length:
            return text

        return text[: max_length - len(suffix)] + suffix

    @staticmethod
    def extract_domain(url: str) -> Optional[str]:
        """
        Извлекает домен из URL.

        Аргументы:
            url: URL-адрес

        Возвращает:
            str: Домен или None при ошибке
        """
        try:
            parsed = urlparse(url)
            return parsed.netloc if parsed.netloc else None
        except Exception:
            return None

    @staticmethod
    def normalize_whitespace(text: str) -> str:
        """
        Нормализует пробельные символы.

        Аргументы:
            text: Исходный текст

        Возвращает:
            str: Текст с нормализованными пробелами
        """
        # Заменяем последовательности пробельных символов на один пробел
        return re.sub(r"\s+", " ", text).strip()


class DateUtils:
    """Утилиты для работы с датами и временем."""

    @staticmethod
    def chrome_timestamp_to_datetime(chrome_timestamp: str) -> Optional[datetime]:
        """
        Преобразует временную метку Chrome в datetime.

        Аргументы:
            chrome_timestamp: Временная метка Chrome (микросекунды с 1601 года)

        Возвращает:
            datetime: Объект datetime или None при ошибке
        """
        try:
            # Chrome использует формат времени в микросекундах с 1 января 1601 года
            # Преобразуем в формат Unix timestamp (с 1 января 1970 года)
            # Chrome время - это количество микросекунд с 1601 года
            # Разница между 1601 и 1970 годами в микросекундах: 11644473600000000
            chrome_ts = int(chrome_timestamp)
            unix_timestamp = (chrome_ts - 11644473600000000) / 1000000.0
            return datetime.fromtimestamp(unix_timestamp)
        except (ValueError, OSError) as e:
            logger.error(f"Ошибка преобразования временной метки Chrome: {e}")
            return None

    @staticmethod
    def format_duration(seconds: float) -> str:
        """
        Форматирует продолжительность в человекочитаемый вид.

        Аргументы:
            seconds: Продолжительность в секундах

        Возвращает:
            str: Отформатированная продолжительность
        """
        if seconds < 60:
            return f"{seconds:.1f} сек"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f} мин"
        else:
            hours = seconds / 3600
            return f"{hours:.1f} час"

    @staticmethod
    def now_iso() -> str:
        """
        Возвращает текущее время в ISO формате.

        Возвращает:
            str: Текущее время в ISO формате
        """
        return datetime.now().isoformat()


class ValidationUtils:
    """Утилиты для валидации данных."""

    @staticmethod
    def is_valid_url(url: str) -> bool:
        """
        Проверяет корректность URL.

        Аргументы:
            url: URL для проверки

        Возвращает:
            bool: True если URL корректный, иначе False
        """
        try:
            result = urlparse(url)
            return all([result.scheme in ["http", "https"], result.netloc])
        except Exception:
            return False

    @staticmethod
    def validate_json_structure(
        data: Union[dict[str, Any], Any], required_keys: list[str]
    ) -> bool:
        """
        Валидирует структуру JSON.

        Аргументы:
            data: Словарь с данными для валидации (может быть любого типа)
            required_keys: Список обязательных ключей

        Возвращает:
            bool: True если структура валидна, иначе False
        """
        if not isinstance(data, dict):
            return False

        for key in required_keys:
            if key not in data:
                logger.warning(f"Отсутствует обязательный ключ в JSON: {key}")
                return False

        return True

    @staticmethod
    def is_safe_path(path: Union[str, Path], base_path: Union[str, Path]) -> bool:
        """
        Проверяет безопасность пути (предотвращение path traversal).

        Аргументы:
            path: Путь для проверки
            base_path: Базовый путь

        Возвращает:
            bool: True если путь безопасный, иначе False
        """
        try:
            path_obj = Path(path).resolve()
            base_obj = Path(base_path).resolve()
            return str(path_obj).startswith(str(base_obj))
        except Exception:
            return False


class ErrorUtils:
    """Утилиты для обработки ошибок."""

    @staticmethod
    def safe_execute(
        func: Callable[..., Any],
        default: Any = None,
        log_error: bool = True,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """
        Безопасно выполняет функцию, обрабатывая исключения.

        Аргументы:
            func: Функция для выполнения
            default: Значение по умолчанию при ошибке
            log_error: Флаг логирования ошибок
            *args: Позиционные аргументы для функции
            **kwargs: Именованные аргументы для функции

        Возвращает:
            Результат функции или значение по умолчанию
        """
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if log_error:
                logger.error(f"Ошибка при выполнении функции {func.__name__}: {e}")
            return default

    @staticmethod
    async def safe_execute_async(
        func: Callable[..., Any],
        default: Any = None,
        log_error: bool = True,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """
        Безопасно выполняет асинхронную функцию, обрабатывая исключения.

        Аргументы:
            func: Асинхронная функция для выполнения
            default: Значение по умолчанию при ошибке
            log_error: Флаг логирования ошибок
            *args: Позиционные аргументы для функции
            **kwargs: Именованные аргументы для функции

        Возвращает:
            Результат функции или значение по умолчанию
        """
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            if log_error:
                logger.error(
                    f"Ошибка при выполнении асинхронной функции {func.__name__}: {e}"
                )
            return default

    @staticmethod
    def retry_with_backoff(
        func: Callable[..., Any],
        max_retries: int = 3,
        base_delay: float = 1.0,
        backoff_factor: float = 2.0,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """
        Выполняет функцию с повторными попытками и экспоненциальной задержкой.

        Аргументы:
            func: Функция для выполнения
            max_retries: Максимальное количество попыток
            base_delay: Базовая задержка в секундах
            backoff_factor: Множитель для экспоненциальной задержки
            *args: Позиционные аргументы для функции
            **kwargs: Именованные аргументы для функции

        Возвращает:
            Результат функции

        Raises:
            Последнее исключение при неудаче всех попыток
        """
        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < max_retries:
                    delay = base_delay * (backoff_factor**attempt)
                    logger.warning(
                        f"Попытка {attempt + 1} не удалась. Повтор через {delay:.2f} сек. Ошибка: {e}"
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        f"Все {max_retries + 1} попыток не удались. Последняя ошибка: {e}"
                    )

        if last_exception is not None:
            raise last_exception

    @staticmethod
    async def retry_with_backoff_async(
        func: Callable[..., Any],
        max_retries: int = 3,
        base_delay: float = 1.0,
        backoff_factor: float = 2.0,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """
        Асинхронно выполняет функцию с повторными попытками и экспоненциальной задержкой.

        Аргументы:
            func: Асинхронная функция для выполнения
            max_retries: Максимальное количество попыток
            base_delay: Базовая задержка в секундах
            backoff_factor: Множитель для экспоненциальной задержки
            *args: Позиционные аргументы для функции
            **kwargs: Именованные аргументы для функции

        Возвращает:
            Результат функции

        Raises:
            Последнее исключение при неудаче всех попыток
        """
        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < max_retries:
                    delay = base_delay * (backoff_factor**attempt)
                    logger.warning(
                        f"Попытка {attempt + 1} не удалась. Повтор через {delay:.2f} сек. Ошибка: {e}"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"Все {max_retries + 1} попыток не удались. Последняя ошибка: {e}"
                    )

        if last_exception is not None:
            raise last_exception


class HashUtils:
    """Утилиты для хеширования данных."""

    @staticmethod
    def generate_file_hash(file_path: Path, algorithm: str = "md5") -> str:
        """
        Генерирует хеш файла.

        Аргументы:
            file_path: Путь к файлу
            algorithm: Алгоритм хеширования (md5, sha1, sha256)

        Возвращает:
            str: Хеш файла

        Raises:
            FileNotFoundError: Если файл не найден
            ValueError: Если указан неподдерживаемый алгоритм
        """
        if algorithm not in hashlib.algorithms_available:
            raise ValueError(f"Неподдерживаемый алгоритм хеширования: {algorithm}")

        hash_obj = hashlib.new(algorithm)

        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_obj.update(chunk)

        return hash_obj.hexdigest()

    @staticmethod
    def generate_text_hash(text: str, algorithm: str = "md5") -> str:
        """
        Генерирует хеш текста.

        Аргументы:
            text: Текст для хеширования
            algorithm: Алгоритм хеширования (md5, sha1, sha256)

        Возвращает:
            str: Хеш текста

        Raises:
            ValueError: Если указан неподдерживаемый алгоритм
        """
        if algorithm not in hashlib.algorithms_available:
            raise ValueError(f"Неподдерживаемый алгоритм хеширования: {algorithm}")

        hash_obj = hashlib.new(algorithm)
        hash_obj.update(text.encode("utf-8"))
        return hash_obj.hexdigest()


class ProgressTracker:
    """Класс для отслеживания прогресса выполнения операций."""

    def __init__(self, total_items: int, description: str = "Обработка"):
        """
        Инициализация трекера прогресса.

        Аргументы:
            total_items: Общее количество элементов
            description: Описание операции
        """
        self.total_items = total_items
        self.processed_items = 0
        self.description = description
        self.start_time = time.time()
        self.last_log_time = 0.0
        self.log_interval = 5  # Логировать не чаще чем раз в 5 секунд

    def update(self, processed: int = 1, item_description: str = "") -> None:
        """
        Обновляет прогресс.

        Аргументы:
            processed: Количество обработанных элементов
            item_description: Описание текущего элемента
        """
        self.processed_items += processed
        current_time = time.time()

        # Логируем прогресс с определенной периодичностью
        if (
            current_time - self.last_log_time >= self.log_interval
            or self.processed_items >= self.total_items
        ):
            self._log_progress(item_description)
            self.last_log_time = current_time

    def get_progress_percentage(self) -> float:
        """
        Возвращает процент выполнения.

        Возвращает:
            float: Процент выполнения (0-100)
        """
        if self.total_items == 0:
            return 100.0
        return (self.processed_items / self.total_items) * 100.0

    def get_elapsed_time(self) -> float:
        """
        Возвращает затраченное время.

        Возвращает:
            float: Затраченное время в секундах
        """
        return time.time() - self.start_time

    def get_estimated_remaining_time(self) -> Optional[float]:
        """
        Возвращает оценку оставшегося времени.

        Возвращает:
            float: Оставшееся время в секундах или None если невозможно оценить
        """
        if self.processed_items == 0:
            return None

        elapsed_time = self.get_elapsed_time()
        items_per_second = self.processed_items / elapsed_time
        remaining_items = self.total_items - self.processed_items

        return remaining_items / items_per_second if items_per_second > 0 else None

    def _log_progress(self, item_description: str = "") -> None:
        """
        Логирует текущий прогресс.

        Аргументы:
            item_description: Описание текущего элемента
        """
        percentage = self.get_progress_percentage()
        elapsed = DateUtils.format_duration(self.get_elapsed_time())

        remaining_time = self.get_estimated_remaining_time()
        remaining_str = (
            f", осталось: {DateUtils.format_duration(remaining_time)}"
            if remaining_time
            else ""
        )

        item_str = f" ({item_description})" if item_description else ""

        logger.info(
            f"{self.description}: {self.processed_items}/{self.total_items} "
            f"({percentage:.1f}%), затрачено: {elapsed}{remaining_str}{item_str}"
        )
