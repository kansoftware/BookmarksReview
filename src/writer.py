"""
Модуль writer.py
Отвечает за создание файловой структуры и запись Markdown-файлов.
Обеспечивает нормализацию имен файлов и генерацию метаданных.
"""

import re
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

from src.config import Config
from src.logger import (
    get_logger,
    log_error_with_context,
    log_function_call,
    log_performance,
)
from src.models import Bookmark, BookmarkFolder, ProcessedPage

logger = get_logger(__name__)


class FileSystemWriter:
    """
    Класс для записи файловой структуры и Markdown-файлов.

    Отвечает за создание директорий согласно иерархии закладок и сохранение обработанных страниц в формате Markdown.
    """

    def __init__(self, config: Config):
        """
        Инициализация файлового писателя.

        Аргументы:
            config: Объект конфигурации приложения
        """
        log_function_call("FileSystemWriter.__init__", (), {"config": config})

        self.config = config
        self.output_dir = Path(config.output_dir)

        # Создаем выходную директорию, если она не существует
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Выходная директория создана/проверена: {self.output_dir}")
        logger.debug(
            f"Конфигурация FileSystemWriter: markdown_include_metadata={config.markdown_include_metadata}"
        )

    def create_folder_structure(
        self, folder: BookmarkFolder, base_path: Optional[str | Path] = None
    ) -> Path:
        """
        Создает структуру папок согласно иерархии закладок.

        Аргументы:
            folder: Корневая папка закладок
            base_path: Базовый путь для создания структуры (по умолчанию output_dir)

        Возвращает:
            Path: Путь к созданной корневой папке
        """
        start_time = time.time()
        log_function_call(
            "create_folder_structure", (folder.name,), {"base_path": base_path}
        )

        if base_path is None:
            base_path = self.output_dir
        elif isinstance(base_path, str):
            base_path = Path(base_path)

        # Рекурсивно создаем структуру папок
        self._create_folder_recursive(folder, base_path)

        duration = time.time() - start_time
        log_performance(
            "create_folder_structure", duration, f"root_folder={folder.name}"
        )
        logger.info(f"Структура папок создана для: {folder.name}")

        return base_path

    def _create_folder_recursive(
        self, folder: BookmarkFolder, parent_path: Path
    ) -> None:
        """
        Рекурсивно создает папки и их вложенные элементы.

        Аргументы:
            folder: Текущая папка для создания
            parent_path: Путь к родительской директории
        """
        log_function_call(
            "_create_folder_recursive",
            (folder.name,),
            {"parent_path": str(parent_path)},
        )

        # Создаем текущую папку с нормализованным именем
        folder_name = self._sanitize_filename(folder.name, parent_path=parent_path, is_folder=True)
        folder_path = parent_path / folder_name
        folder_path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Создана папка: {folder_path}")

        # Рекурсивно обрабатываем вложенные папки
        for child_folder in folder.children:
            self._create_folder_recursive(child_folder, folder_path)

        logger.debug(
            f"Папка {folder.name} содержит {len(folder.children)} подпапок и {len(folder.bookmarks)} закладок"
        )

    def write_markdown(self, page: ProcessedPage, file_path: Path) -> None:
        """
        Записывает обработанную страницу в Markdown-файл.

        Аргументы:
            page: Обработанная страница с контентом
            file_path: Путь для сохранения файла
        """
        start_time = time.time()
        log_function_call(
            "write_markdown", (page.title,), {"file_path": str(file_path)}
        )

        try:
            # Убеждаемся, что директория существует
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Формируем содержимое файла
            content = self._format_markdown_content(page)

            # Записываем файл
            assert len(file_path.name) < 255
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            duration = time.time() - start_time
            log_performance(
                "write_markdown", duration, f"file={file_path}, size={len(content)}"
            )
            logger.info(
                f"Файл успешно сохранен: {file_path} (размер: {len(content)} байт)"
            )

        except Exception as e:
            duration = time.time() - start_time
            log_performance(
                "write_markdown", duration, f"file={file_path}, success=False"
            )
            log_error_with_context(
                e, {"file_path": str(file_path), "operation": "write_markdown"}
            )
            raise

    def _format_markdown_content(self, page: ProcessedPage) -> str:
        """
        Форматирует содержимое Markdown-файла.

        Аргументы:
            page: Обработанная страница

        Возвращает:
            str: Отформатированное содержимое файла
        """
        log_function_call(
            "_format_markdown_content",
            (page.title,),
            {
                "include_metadata": self.config.markdown_include_metadata,
                "summary_length": len(page.summary) if page.summary else 0,
            },
        )

        content_parts = []

        # Добавляем метаданные, если включено в конфигурации
        if self.config.markdown_include_metadata:
            metadata = self._generate_metadata(page)
            content_parts.append("---")
            content_parts.append(metadata)
            content_parts.append("---")
            content_parts.append("")
            logger.debug(f"Добавлены метаданные для страницы: {page.title}")

        # Добавляем заголовок
        content_parts.append(f"# {page.title}")
        content_parts.append("")

        # Добавляем основное содержимое (summary)
        if page.summary:
            content_parts.append(page.summary)
            content_parts.append("")
            logger.debug(
                f"Добавлено описание для страницы: {page.title} (длина: {len(page.summary)})"
            )

        # Добавляем источник
        content_parts.append("---")
        content_parts.append(f"Источник: {page.url}")

        content = "\n".join(content_parts)
        logger.debug(
            f"Содержимое Markdown отформатировано для: {page.title} (общая длина: {len(content)})"
        )

        return content

    def _generate_metadata(self, page: ProcessedPage) -> str:
        """
        Генерирует YAML frontmatter для Markdown-файла.

        Аргументы:
            page: Обработанная страница

        Возвращает:
            str: YAML-метаданные в виде строки
        """
        log_function_call("_generate_metadata", (page.title,))

        metadata = {
            "url": page.url,
            "title": page.title,
            "date_processed": page.fetch_date.isoformat(),
            "status": page.status,
        }

        # Конвертируем в YAML строку
        yaml_str = yaml.dump(metadata, default_flow_style=False, allow_unicode=True)
        result: str = yaml_str.strip()

        logger.debug(f"Сгенерированы метаданные для: {page.title}")
        return result

    def _sanitize_filename(self, name: str, parent_path: Optional[Path] = None, max_path_len: int = 255, is_folder: bool = False) -> str:
        """
        Нормализует имя файла, удаляя недопустимые символы и ограничивая длину с учетом родительского пути.
        Учитывает, что символы могут быть в UTF-8, где 1 символ != 1 байт.

        Аргументы:
            name: Исходное имя файла или папки
            parent_path: Родительский путь для учета общей длины (опционально)
            max_path_len: Максимальная длина всего пути в байтах (включая имя и расширение) (по умолчанию 255)
            is_folder: Флаг, указывающий, является ли имя папкой (по умолчанию False)

        Возвращает:
            str: Нормализованное имя файла
        """
        log_function_call("_sanitize_filename", (name, parent_path, max_path_len))
        logger.debug(f"Входные данные _sanitize_filename: name='{name}', parent_path='{parent_path}', max_path_len={max_path_len}, is_folder={is_folder}")

        original_name = name

        # Проверяем, не является ли переданный путь None или пустым
        if not name:
            sanitized = "unnamed"
            logger.debug("Пустое имя файла заменено на 'unnamed'")
            return sanitized

        # Санитизация: удаление или замена недопустимых символов
        sanitized = self._sanitize_invalid_chars(name)
        
        # Ограничение длины имени в зависимости от родительского пути
        # Учитываем, что длина пути измеряется в байтах, а не в символах
        sanitized = self._limit_name_length(sanitized, original_name, parent_path, max_path_len, is_folder)

        if original_name != sanitized:
            logger.debug(f"Имя файла санитизировано: '{original_name}' -> '{sanitized}'")

        return sanitized

    def _sanitize_invalid_chars(self, name: str) -> str:
        """
        Удаляет или заменяет недопустимые символы в имени файла.

        Аргументы:
            name: Исходное имя файла или папки

        Возвращает:
            str: Имя с удаленными недопустимыми символами
        """
        # Заменяем недопустимые символы на подчеркивание
        # Используем кешированный паттерн для оптимизации
        if not hasattr(self, '_invalid_chars_pattern'):
            self._invalid_chars_pattern = re.compile(r'[<>:"/\\|?*]')
        sanitized = self._invalid_chars_pattern.sub("_", name)
        
        # Заменяем последовательности пробелов на один пробел
        if not hasattr(self, '_whitespace_pattern'):
            self._whitespace_pattern = re.compile(r"\s+")
        sanitized = self._whitespace_pattern.sub(" ", sanitized)
        
        # Убираем пробелы в начале и конце
        sanitized = sanitized.strip()
        logger.debug(f"После санитизации недопустимых символов: '{sanitized}'")
        return sanitized

    def _calculate_path_overhead(self, parent_path: Optional[Path], is_folder: bool) -> int:
        """
        Рассчитывает дополнительную длину пути в байтах, зависящую от типа элемента (файл или папка).

        Аргументы:
            parent_path: Родительский путь
            is_folder: Флаг, указывающий, является ли элемент папкой

        Возвращает:
            int: Дополнительная длина пути в байтах
        """
        if is_folder:
            # Для папки: только разделитель пути (если есть родительский путь)
            return 1 if parent_path else 0
        else:
            # Для файла: разделитель пути + расширение .md (в UTF-8 это 3 байта)
            return 1 + len(".md".encode('utf-8')) if parent_path else len(".md".encode('utf-8'))

    def _limit_name_length(self, sanitized: str, original_name: str, parent_path: Optional[Path], max_path_len: int, is_folder: bool) -> str:
        """
        Ограничивает длину имени файла в зависимости от родительского пути и максимальной длины пути.
        Учитывает, что длина пути измеряется в байтах для UTF-8 строк.

        Аргументы:
            sanitized: Санитизированное имя
            original_name: Оригинальное имя
            parent_path: Родительский путь
            max_path_len: Максимальная длина всего пути в байтах
            is_folder: Флаг, указывающий, является ли элемент папкой

        Возвращает:
            str: Имя с ограниченной длиной
        """
        # Проверяем, что parent_path не None перед использованием
        current_path_str = str(parent_path) if parent_path else ""
        # Рассчитываем длину родительского пути в байтах (для UTF-8)
        current_path_len = len(current_path_str.encode('utf-8'))
        
        # Рассчитываем overhead в зависимости от типа (файл или папка)
        # Для файлов: разделитель пути + расширение .md (3 символа, но в UTF-8 это может быть больше байт)
        if is_folder:
            path_overhead = 1 if current_path_len > 0 else 0  # байт для разделителя пути
        else:
            # Для файла: 1 байт для разделителя пути + длина ".md" в UTF-8 (обычно 3 байта)
            path_overhead = 1 + len(".md".encode('utf-8')) if current_path_len > 0 else len(".md".encode('utf-8'))
        
        # Определяем максимальную длину имени в байтах
        max_name_length_bytes = max_path_len - current_path_len - path_overhead
        
        logger.debug(f"current_path_len_bytes={current_path_len}, path_overhead={path_overhead}, max_name_length_bytes={max_name_length_bytes}")
        logger.debug(f"Расчет максимальной длины имени в байтах: max_path_len={max_path_len} - current_path_len={current_path_len} - path_overhead={path_overhead} = {max_name_length_bytes}")

        if max_name_length_bytes <= 0:
            # Если даже минимальное имя не помещается, сразу используем хеш
            return self._generate_hash_name(original_name, "item",
                f"Имя файла заменено на хеш из-за слишком длинного родительского пути (parent_path='{parent_path}', max_path_len={max_path_len})")

        # Обрезаем имя, учитывая ограничение в байтах
        # Для этого конвертируем строку в байты, обрезаем, затем декодируем обратно
        sanitized_bytes = sanitized.encode('utf-8')
        if len(sanitized_bytes) > max_name_length_bytes:
            # Обрезаем байты до максимально допустимой длины
            truncated_bytes = sanitized_bytes[:max_name_length_bytes]
            # Декодируем обратно в строку, обрабатывая возможные ошибки
            # (например, обрезание посередине многобайтового символа)
            try:
                sanitized = truncated_bytes.decode('utf-8')
            except UnicodeDecodeError:
                # Если декодирование не удалось из-за обрезания символа,
                # пробуем обрезать до последнего полного символа
                sanitized = truncated_bytes.decode('utf-8', errors='ignore')
                # Или пытаемся найти последний полный символ
                while truncated_bytes and truncated_bytes[-1] & 0xC0 == 0x80:  # Проверяем, является ли последний байт продолжением символа
                    truncated_bytes = truncated_bytes[:-1]
                try:
                    sanitized = truncated_bytes.decode('utf-8')
                except UnicodeDecodeError:
                    # Если все еще не удается декодировать, используем хеш
                    return self._generate_hash_name(original_name, "item",
                        f"Имя файла заменено на хеш из-за проблем с UTF-8 декодированием (parent_path='{parent_path}', max_path_len={max_path_len})")
            
            logger.debug(
                f"Имя файла обрезано с {len(original_name.encode('utf-8'))} до {len(sanitized.encode('utf-8'))} байт "
                f"с учетом родительского пути '{parent_path}' и лимита {max_path_len} байт. "
                f"Результат: '{sanitized}'"
            )

        # Если имя стало пустым после очистки, используем значение по умолчанию
        if not sanitized:
            sanitized = "unnamed"
            logger.debug("Пустое имя файла заменено на 'unnamed'")

        # ФИНАЛЬНАЯ ПРОВЕРКА: убедимся, что полный путь не превышает лимит в байтах
        if parent_path:
            full_path_candidate = self._construct_full_path(parent_path, sanitized, is_folder)
            full_path_candidate_bytes_len = len(str(full_path_candidate).encode('utf-8'))
            logger.debug(f"Финальная проверка пути: '{full_path_candidate}' (длина: {full_path_candidate_bytes_len} байт)")
            if full_path_candidate_bytes_len > max_path_len:
                return self._generate_hash_name(original_name, "item",
                    f"Имя файла заменено на хеш из-за превышения общего лимита пути (parent_path='{parent_path}', max_path_len={max_path_len}, full_path_candidate_bytes_len={full_path_candidate_bytes_len})")

        return sanitized

    def _construct_full_path(self, parent_path: Path, sanitized_name: str, is_folder: bool) -> Path:
        """
        Конструирует полный путь для проверки длины.

        Аргументы:
            parent_path: Родительский путь
            sanitized_name: Санитизированное имя
            is_folder: Флаг, указывающий, является ли элемент папкой

        Возвращает:
            Path: Полный путь
        """
        if is_folder:
            # Для папки: полный путь = parent_path + "/" + sanitized
            return parent_path / sanitized_name
        else:
            # Для файла: полный путь = parent_path + "/" + sanitized + ".md"
            return parent_path / f"{sanitized_name}.md"

    def _generate_hash_name(self, original_name: str, prefix: str, warning_msg: str) -> str:
        """
        Генерирует хешированное имя файла в случае проблем с длиной пути.

        Аргументы:
            original_name: Оригинальное имя
            prefix: Префикс для хешированного имени
            warning_msg: Сообщение для логирования

        Возвращает:
            str: Хешированное имя файла
        """
        import hashlib
        hash_name = hashlib.md5(original_name.encode()).hexdigest()[:8]
        hashed_name = f"{prefix}_{hash_name}"
        logger.warning(warning_msg)
        return hashed_name

    def get_bookmark_file_path(
        self, bookmark: Bookmark, base_path: Optional[Path] = None
    ) -> Path:
        """
        Определяет путь для сохранения файла закладки.

        Аргументы:
            bookmark: Закладка для определения пути
            base_path: Базовый путь (по умолчанию output_dir)

        Возвращает:
            Path: Полный путь к файлу закладки
        """
        log_function_call(
            "get_bookmark_file_path", (bookmark.title,), {"base_path": base_path}
        )
        logger.debug(f"Входные данные get_bookmark_file_path: title='{bookmark.title}', base_path='{base_path}'")

        if base_path is None:
            base_path = self.output_dir

        # Нормализуем заголовок для использования как имени файла
        # Передаем base_path как parent_path, чтобы _sanitize_filename мог учесть его длину
        filename = self._sanitize_filename(bookmark.title, parent_path=base_path, is_folder=False)
        logger.debug(f"Имя файла после _sanitize_filename: '{filename}'")

        # Добавляем расширение .md
        if not filename.endswith(".md"):
            filename += ".md"

        file_path = base_path / filename
        
        logger.debug(f"Определен путь для файла закладки: {file_path}")

        return file_path

    def save_progress(self, processed_urls: list[str], failed_urls: list[str]) -> None:
        """
        Сохраняет прогресс обработки в JSON-файл.

        Аргументы:
            processed_urls: Список успешно обработанных URL
            failed_urls: Список URL с ошибками
        """
        import json

        start_time = time.time()
        log_function_call(
            "save_progress",
            (),
            {"processed_count": len(processed_urls), "failed_count": len(failed_urls)},
        )

        progress_data = {
            "timestamp": datetime.now().isoformat(),
            "processed_urls": processed_urls,
            "failed_urls": failed_urls,
        }

        progress_file = self.output_dir / "progress.json"

        try:
            with open(progress_file, "w", encoding="utf-8") as f:
                json.dump(progress_data, f, indent=2, ensure_ascii=False)

            duration = time.time() - start_time
            log_performance("save_progress", duration, f"file={progress_file}")
            logger.info(
                f"Прогресс сохранен в: {progress_file} "
                f"(обработано: {len(processed_urls)}, ошибок: {len(failed_urls)})"
            )

        except Exception as e:
            duration = time.time() - start_time
            log_performance(
                "save_progress", duration, f"file={progress_file}, success=False"
            )
            log_error_with_context(
                e, {"progress_file": str(progress_file), "operation": "save_progress"}
            )

    def load_progress(self) -> dict[str, object]:
        """
        Загружает прогресс обработки из JSON-файла.

        Возвращает:
            dict: Данные о прогрессе или пустой словарь, если файл не найден
        """
        import json

        start_time = time.time()
        log_function_call("load_progress", ())

        progress_file = self.output_dir / "progress.json"

        if not progress_file.exists():
            logger.debug(f"Файл прогресса не найден: {progress_file}")
            return {}

        try:
            with open(progress_file, encoding="utf-8") as f:
                progress_data = json.load(f)

            duration = time.time() - start_time
            log_performance("load_progress", duration, f"file={progress_file}")

            processed_count = len(progress_data.get("processed_urls", []))
            failed_count = len(progress_data.get("failed_urls", []))
            logger.info(
                f"Прогресс загружен из: {progress_file} "
                f"(обработано: {processed_count}, ошибок: {failed_count})"
            )

            return progress_data  # type: ignore[no-any-return]

        except Exception as e:
            duration = time.time() - start_time
            log_performance(
                "load_progress", duration, f"file={progress_file}, success=False"
            )
            log_error_with_context(
                e, {"progress_file": str(progress_file), "operation": "load_progress"}
            )
            return {}
