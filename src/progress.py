"""
Модуль progress.py
Содержит классы для управления прогрессом обработки закладок.
Обеспечивает сохранение и восстановление состояния обработки.
"""

import json
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .logger import (
    get_logger,
    log_error_with_context,
    log_function_call,
    log_performance,
)
from .models import Bookmark
from .utils import HashUtils

logger = get_logger(__name__)


@dataclass
class ProcessedBookmark:
    """
    Информация об обработанной закладке.
    """

    url: str
    title: str
    processed_at: str
    file_path: Optional[str] = None
    folder_path: Optional[list[str]] = None


@dataclass
class FailedBookmark:
    """
    Информация о закладке с ошибкой.
    """

    url: str
    title: str
    failed_at: str
    error: str
    folder_path: Optional[list[str]] = None


@dataclass
class CurrentPosition:
    """
    Текущая позиция в обработке.
    """

    folder_path: list[str]
    bookmark_index: int
    total_in_folder: int


@dataclass
class ProgressStatistics:
    """
    Статистика прогресса обработки.
    """

    total_bookmarks: int
    processed_count: int
    failed_count: int
    skipped_count: int
    start_time: str
    last_update: str


class ProgressManager:
    """
    Менеджер прогресса обработки закладок.

    Обеспечивает сохранение и восстановление состояния обработки,
    периодическое сохранение прогресса и атомарные операции.
    """

    def __init__(self, output_dir: str, bookmarks_file: str, config_hash: str):
        """
        Инициализация менеджера прогресса.

        Аргументы:
            output_dir: Директория для сохранения результатов
            bookmarks_file: Путь к файлу закладок
            config_hash: Хеш конфигурации для проверки совместимости
        """
        log_function_call(
            "ProgressManager.__init__",
            (output_dir, bookmarks_file),
            {"config_hash": config_hash},
        )

        self.output_dir = Path(output_dir)
        self.bookmarks_file = bookmarks_file
        self.config_hash = config_hash
        self.progress_file = self.output_dir / "progress.json"
        self.lock_file = self.output_dir / "progress.lock"

        # Данные прогресса
        self.processed_bookmarks: list[ProcessedBookmark] = []
        self.failed_bookmarks: list[FailedBookmark] = []
        self.current_position: Optional[CurrentPosition] = None
        self.statistics: Optional[ProgressStatistics] = None

        # Настройки сохранения
        self.save_interval = 10  # Сохранять каждые 10 закладок
        self.last_save_count = 0

        # Блокировка для потокобезопасности
        self._lock = threading.Lock()

        logger.info(f"ProgressManager инициализирован: {self.progress_file}")

    def load_progress(self) -> bool:
        """
        Загружает прогресс из файла.

        Возвращает:
            bool: True если прогресс успешно загружен, иначе False
        """
        start_time = time.time()
        log_function_call("ProgressManager.load_progress", ())

        if not self.progress_file.exists():
            logger.debug(f"Файл прогресса не найден: {self.progress_file}")
            return False

        try:
            with self._lock:
                with open(self.progress_file, encoding="utf-8") as f:
                    data = json.load(f)

                # Проверка версии
                if data.get("version") != "1.0":
                    logger.warning(
                        f"Несовместимая версия прогресса: {data.get('version')}"
                    )
                    return False

                # Проверка конфигурации
                if data.get("config_hash") != self.config_hash:
                    logger.warning(
                        "Хеш конфигурации не совпадает, прогресс несовместим"
                    )
                    return False

                # Проверка файла закладок
                if data.get("bookmarks_file") != self.bookmarks_file:
                    logger.warning("Файл закладок не совпадает, прогресс несовместим")
                    return False

                # Загрузка обработанных закладок
                processed_items: list[dict[str, Any]] = data.get("processed_urls", [])
                self.processed_bookmarks = [
                    ProcessedBookmark(**item) for item in processed_items
                ]

                # Загрузка неудачных закладок
                failed_items: list[dict[str, Any]] = data.get("failed_urls", [])
                self.failed_bookmarks = [
                    FailedBookmark(**item) for item in failed_items
                ]

                # Загрузка текущей позиции
                pos_data = data.get("current_position")
                if pos_data:
                    self.current_position = CurrentPosition(**pos_data)

                # Загрузка статистики
                stats_data = data.get("statistics")
                if stats_data:
                    self.statistics = ProgressStatistics(**stats_data)

                duration = time.time() - start_time
                log_performance(
                    "ProgressManager.load_progress",
                    duration,
                    f"processed={len(self.processed_bookmarks)}, failed={len(self.failed_bookmarks)}",
                )

                logger.info(
                    f"Прогресс загружен: {len(self.processed_bookmarks)} обработано, "
                    f"{len(self.failed_bookmarks)} с ошибками"
                )

                return True

        except Exception as e:
            duration = time.time() - start_time
            log_performance("ProgressManager.load_progress", duration, "success=False")
            log_error_with_context(
                e,
                {
                    "progress_file": str(self.progress_file),
                    "operation": "load_progress",
                },
            )
            return False

    def save_progress(self, force: bool = False) -> bool:
        """
        Сохраняет прогресс в файл.

        Аргументы:
            force: Принудительно сохранить независимо от интервала

        Возвращает:
            bool: True если прогресс успешно сохранен, иначе False
        """
        start_time = time.time()
        log_function_call("ProgressManager.save_progress", (), {"force": force})

        # Проверяем интервал сохранения
        total_processed = len(self.processed_bookmarks) + len(self.failed_bookmarks)
        if not force and total_processed - self.last_save_count < self.save_interval:
            return False

        try:
            with self._lock:
                # Создаем директорию если нужно
                self.output_dir.mkdir(parents=True, exist_ok=True)

                # Подготовка данных для сохранения
                data = {
                    "version": "1.0",
                    "timestamp": datetime.now().isoformat(),
                    "bookmarks_file": self.bookmarks_file,
                    "config_hash": self.config_hash,
                    "processed_urls": [
                        asdict(item) for item in self.processed_bookmarks
                    ],
                    "failed_urls": [asdict(item) for item in self.failed_bookmarks],
                }

                # Добавляем текущую позицию если есть
                if self.current_position:
                    data["current_position"] = asdict(self.current_position)  # type: ignore

                # Добавляем статистику если есть
                if self.statistics:
                    data["statistics"] = asdict(self.statistics)  # type: ignore

                # Атомарное сохранение через временный файл
                temp_file = self.progress_file.with_suffix(".tmp")
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

                # Переименовываем временный файл
                temp_file.replace(self.progress_file)

                self.last_save_count = total_processed

                duration = time.time() - start_time
                log_performance(
                    "ProgressManager.save_progress",
                    duration,
                    f"processed={len(self.processed_bookmarks)}, failed={len(self.failed_bookmarks)}",
                )

                logger.debug(
                    f"Прогресс сохранен: {len(self.processed_bookmarks)} обработано, "
                    f"{len(self.failed_bookmarks)} с ошибками"
                )

                return True

        except Exception as e:
            duration = time.time() - start_time
            log_performance("ProgressManager.save_progress", duration, "success=False")
            log_error_with_context(
                e,
                {
                    "progress_file": str(self.progress_file),
                    "operation": "save_progress",
                },
            )
            return False

    def add_processed_bookmark(
        self, bookmark: Bookmark, file_path: str, folder_path: list[str]
    ) -> None:
        """
        Добавляет информацию об обработанной закладке.

        Аргументы:
            bookmark: Обработанная закладка
            file_path: Путь к сохраненному файлу
            folder_path: Путь в иерархии папок
        """
        log_function_call(
            "ProgressManager.add_processed_bookmark",
            (bookmark.title,),
            {"url": bookmark.url, "file_path": file_path},
        )

        processed = ProcessedBookmark(
            url=bookmark.url,
            title=bookmark.title,
            processed_at=datetime.now().isoformat(),
            file_path=file_path,
            folder_path=folder_path,
        )

        with self._lock:
            self.processed_bookmarks.append(processed)

        # Периодическое сохранение
        self.save_progress()

    def add_failed_bookmark(
        self, bookmark: Bookmark, error: str, folder_path: list[str]
    ) -> None:
        """
        Добавляет информацию о закладке с ошибкой.

        Аргументы:
            bookmark: Закладка с ошибкой
            error: Текст ошибки
            folder_path: Путь в иерархии папок
        """
        log_function_call(
            "ProgressManager.add_failed_bookmark",
            (bookmark.title,),
            {"url": bookmark.url, "error": error},
        )

        failed = FailedBookmark(
            url=bookmark.url,
            title=bookmark.title,
            failed_at=datetime.now().isoformat(),
            error=error,
            folder_path=folder_path,
        )

        with self._lock:
            self.failed_bookmarks.append(failed)

        # Периодическое сохранение
        self.save_progress()

    def update_current_position(
        self, folder_path: list[str], bookmark_index: int, total_in_folder: int
    ) -> None:
        """
        Обновляет текущую позицию в обработке.

        Аргументы:
            folder_path: Путь в иерархии папок
            bookmark_index: Индекс текущей закладки
            total_in_folder: Всего закладок в папке
        """
        log_function_call(
            "ProgressManager.update_current_position",
            ("/".join(folder_path),),
            {"bookmark_index": bookmark_index},
        )

        with self._lock:
            self.current_position = CurrentPosition(
                folder_path=folder_path,
                bookmark_index=bookmark_index,
                total_in_folder=total_in_folder,
            )

    def initialize_statistics(self, total_bookmarks: int) -> None:
        """
        Инициализирует статистику прогресса.

        Аргументы:
            total_bookmarks: Общее количество закладок
        """
        log_function_call("ProgressManager.initialize_statistics", (total_bookmarks,))

        with self._lock:
            now = datetime.now().isoformat()
            self.statistics = ProgressStatistics(
                total_bookmarks=total_bookmarks,
                processed_count=len(self.processed_bookmarks),
                failed_count=len(self.failed_bookmarks),
                skipped_count=0,
                start_time=now,
                last_update=now,
            )

    def update_statistics(self) -> None:
        """Обновляет статистику прогресса."""
        with self._lock:
            if self.statistics:
                self.statistics.processed_count = len(self.processed_bookmarks)
                self.statistics.failed_count = len(self.failed_bookmarks)
                self.statistics.last_update = datetime.now().isoformat()

    def get_processed_urls(self) -> set[str]:
        """
        Возвращает множество обработанных URL.

        Возвращает:
            set[str]: Множество обработанных URL
        """
        with self._lock:
            return {item.url for item in self.processed_bookmarks}

    def get_failed_urls(self) -> set[str]:
        """
        Возвращает множество URL с ошибками.

        Возвращает:
            set[str]: Множество URL с ошибками
        """
        with self._lock:
            return {item.url for item in self.failed_bookmarks}

    def get_resume_position(self) -> Optional[tuple[list[str], int]]:
        """
        Возвращает позицию для возобновления обработки.

        Возвращает:
            Optional[Tuple[list[str], int]]: Кортеж (путь папки, индекс закладки) или None
        """
        with self._lock:
            if self.current_position:
                return (
                    self.current_position.folder_path,
                    self.current_position.bookmark_index,
                )
            return None

    def get_statistics(self) -> Optional[ProgressStatistics]:
        """
        Возвращает текущую статистику.

        Возвращает:
            Optional[ProgressStatistics]: Статистика прогресса или None
        """
        with self._lock:
            return self.statistics

    def force_save(self) -> bool:
        """
        Принудительно сохраняет прогресс.

        Возвращает:
            bool: True если прогресс успешно сохранен, иначе False
        """
        return self.save_progress(force=True)

    def clear_progress(self) -> bool:
        """
        Очищает сохраненный прогресс.

        Возвращает:
            bool: True если прогресс успешно очищен, иначе False
        """
        log_function_call("ProgressManager.clear_progress", ())

        try:
            with self._lock:
                if self.progress_file.exists():
                    self.progress_file.unlink()

                # Сбрасываем данные в памяти
                self.processed_bookmarks.clear()
                self.failed_bookmarks.clear()
                self.current_position = None
                self.statistics = None
                self.last_save_count = 0

                logger.info("Прогресс успешно очищен")
                return True

        except Exception as e:
            log_error_with_context(
                e,
                {
                    "progress_file": str(self.progress_file),
                    "operation": "clear_progress",
                },
            )
            return False


def calculate_config_hash(config: Any) -> str:
    """
    Вычисляет хеш конфигурации для проверки совместимости прогресса.

    Аргументы:
        config: Объект конфигурации

    Возвращает:
        str: Хеш конфигурации
    """
    # Создаем словарь с ключевыми параметрами конфигурации
    config_data = {
        "llm_model": config.llm_model,
        "llm_max_tokens": config.llm_max_tokens,
        "llm_temperature": config.llm_temperature,
        "output_dir": config.output_dir,
        "markdown_include_metadata": config.markdown_include_metadata,
        "generate_mermaid_diagram": config.generate_mermaid_diagram,
    }

    # Сериализуем и хешируем
    config_str = json.dumps(config_data, sort_keys=True)
    return HashUtils.generate_text_hash(config_str, "sha256")
