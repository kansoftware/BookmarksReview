"""
Модуль writer.py
Отвечает за создание файловой структуры и запись Markdown-файлов.
Обеспечивает нормализацию имен файлов и генерацию метаданных.
"""
import os
import re
import yaml
from pathlib import Path
from typing import Optional
from datetime import datetime
import time

from src.models import ProcessedPage, BookmarkFolder, Bookmark
from src.config import Config
from src.logger import get_logger, log_function_call, log_performance, log_error_with_context

logger = get_logger(__name__)


class FileSystemWriter:
    """
    Класс для записи файловой структуры и Markdown-файлов.
    
    Отвечает за создание директорий согласно иерархии закладок
    и сохранение обработанных страниц в формате Markdown.
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
        logger.debug(f"Конфигурация FileSystemWriter: markdown_include_metadata={config.markdown_include_metadata}")
    
    def create_folder_structure(self, folder: BookmarkFolder, base_path: Optional[Path] = None) -> Path:
        """
        Создает структуру папок согласно иерархии закладок.
        
        Аргументы:
            folder: Корневая папка закладок
            base_path: Базовый путь для создания структуры (по умолчанию output_dir)
            
        Возвращает:
            Path: Путь к созданной корневой папке
        """
        start_time = time.time()
        log_function_call("create_folder_structure", (folder.name,), {"base_path": base_path})
        
        if base_path is None:
            base_path = self.output_dir
        
        # Рекурсивно создаем структуру папок
        self._create_folder_recursive(folder, base_path)
        
        duration = time.time() - start_time
        log_performance("create_folder_structure", duration, f"root_folder={folder.name}")
        logger.info(f"Структура папок создана для: {folder.name}")
        
        return base_path
    
    def _create_folder_recursive(self, folder: BookmarkFolder, parent_path: Path) -> None:
        """
        Рекурсивно создает папки и их вложенные элементы.
        
        Аргументы:
            folder: Текущая папка для создания
            parent_path: Путь к родительской директории
        """
        log_function_call("_create_folder_recursive", (folder.name,), {"parent_path": str(parent_path)})
        
        # Создаем текущую папку с нормализованным именем
        folder_name = self._sanitize_filename(folder.name)
        folder_path = parent_path / folder_name
        folder_path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Создана папка: {folder_path}")
        
        # Рекурсивно обрабатываем вложенные папки
        for child_folder in folder.children:
            self._create_folder_recursive(child_folder, folder_path)
        
        logger.debug(f"Папка {folder.name} содержит {len(folder.children)} подпапок и {len(folder.bookmarks)} закладок")
    
    def write_markdown(self, page: ProcessedPage, file_path: Path) -> None:
        """
        Записывает обработанную страницу в Markdown-файл.
        
        Аргументы:
            page: Обработанная страница с контентом
            file_path: Путь для сохранения файла
        """
        start_time = time.time()
        log_function_call("write_markdown", (page.title,), {"file_path": str(file_path)})
        
        try:
            # Убеждаемся, что директория существует
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Формируем содержимое файла
            content = self._format_markdown_content(page)
            
            # Записываем файл
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            duration = time.time() - start_time
            log_performance("write_markdown", duration, f"file={file_path}, size={len(content)}")
            logger.info(f"Файл успешно сохранен: {file_path} (размер: {len(content)} байт)")
            
        except Exception as e:
            duration = time.time() - start_time
            log_performance("write_markdown", duration, f"file={file_path}, success=False")
            log_error_with_context(e, {"file_path": str(file_path), "operation": "write_markdown"})
            raise
    
    def _format_markdown_content(self, page: ProcessedPage) -> str:
        """
        Форматирует содержимое Markdown-файла.
        
        Аргументы:
            page: Обработанная страница
            
        Возвращает:
            str: Отформатированное содержимое файла
        """
        log_function_call("_format_markdown_content", (page.title,), {
            "include_metadata": self.config.markdown_include_metadata,
            "summary_length": len(page.summary) if page.summary else 0
        })
        
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
            logger.debug(f"Добавлено описание для страницы: {page.title} (длина: {len(page.summary)})")
        
        # Добавляем источник
        content_parts.append("---")
        content_parts.append(f"Источник: {page.url}")
        
        content = "\n".join(content_parts)
        logger.debug(f"Содержимое Markdown отформатировано для: {page.title} (общая длина: {len(content)})")
        
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
            'url': page.url,
            'title': page.title,
            'date_processed': page.fetch_date.isoformat(),
            'status': page.status
        }
        
        # Конвертируем в YAML строку
        yaml_str = yaml.dump(metadata, default_flow_style=False, allow_unicode=True)
        result = yaml_str.strip()
        
        logger.debug(f"Сгенерированы метаданные для: {page.title}")
        return result
    
    def _sanitize_filename(self, name: str) -> str:
        """
        Нормализует имя файла, удаляя недопустимые символы.
        
        Аргументы:
            name: Исходное имя файла или папки
            
        Возвращает:
            str: Нормализованное имя файла
        """
        log_function_call("_sanitize_filename", (name,))
        
        original_name = name
        
        # Удаляем или заменяем недопустимые символы
        # Сохраняем кириллицу, латиницу, цифры, пробелы, дефисы и подчеркивания
        sanitized = re.sub(r'[<>:"/\\|?*]', '', name)
        
        # Заменяем множественные пробелы на один
        sanitized = re.sub(r'\s+', ' ', sanitized)
        
        # Удаляем пробелы в начале и конце
        sanitized = sanitized.strip()
        
        # Ограничиваем длину имени (максимум 255 символов для большинства файловых систем)
        max_length = 255
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length].rstrip()
            logger.debug(f"Имя файла обрезано с {len(original_name)} до {len(sanitized)} символов")
        
        # Если имя стало пустым после очистки, используем значение по умолчанию
        if not sanitized:
            sanitized = "unnamed"
            logger.debug(f"Пустое имя файла заменено на 'unnamed'")
        
        if original_name != sanitized:
            logger.debug(f"Имя файла санитизировано: '{original_name}' -> '{sanitized}'")
        
        return sanitized
    
    def get_bookmark_file_path(self, bookmark: Bookmark, base_path: Optional[Path] = None) -> Path:
        """
        Определяет путь для сохранения файла закладки.
        
        Аргументы:
            bookmark: Закладка для определения пути
            base_path: Базовый путь (по умолчанию output_dir)
            
        Возвращает:
            Path: Полный путь к файлу закладки
        """
        log_function_call("get_bookmark_file_path", (bookmark.title,), {"base_path": base_path})
        
        if base_path is None:
            base_path = self.output_dir
        
        # Нормализуем заголовок для использования как имени файла
        filename = self._sanitize_filename(bookmark.title)
        
        # Добавляем расширение .md
        if not filename.endswith('.md'):
            filename += '.md'
        
        file_path = base_path / filename
        logger.debug(f"Определен путь для файла закладки: {file_path}")
        
        return file_path
    
    def save_progress(self, processed_urls: list, failed_urls: list) -> None:
        """
        Сохраняет прогресс обработки в JSON-файл.
        
        Аргументы:
            processed_urls: Список успешно обработанных URL
            failed_urls: Список URL с ошибками
        """
        import json
        
        start_time = time.time()
        log_function_call("save_progress", (), {
            "processed_count": len(processed_urls),
            "failed_count": len(failed_urls)
        })
        
        progress_data = {
            'timestamp': datetime.now().isoformat(),
            'processed_urls': processed_urls,
            'failed_urls': failed_urls
        }
        
        progress_file = self.output_dir / 'progress.json'
        
        try:
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, indent=2, ensure_ascii=False)
            
            duration = time.time() - start_time
            log_performance("save_progress", duration, f"file={progress_file}")
            logger.info(f"Прогресс сохранен в: {progress_file} "
                       f"(обработано: {len(processed_urls)}, ошибок: {len(failed_urls)})")
            
        except Exception as e:
            duration = time.time() - start_time
            log_performance("save_progress", duration, f"file={progress_file}, success=False")
            log_error_with_context(e, {"progress_file": str(progress_file), "operation": "save_progress"})
    
    def load_progress(self) -> dict:
        """
        Загружает прогресс обработки из JSON-файла.
        
        Возвращает:
            dict: Данные о прогрессе или пустой словарь, если файл не найден
        """
        import json
        
        start_time = time.time()
        log_function_call("load_progress", ())
        
        progress_file = self.output_dir / 'progress.json'
        
        if not progress_file.exists():
            logger.debug(f"Файл прогресса не найден: {progress_file}")
            return {}
        
        try:
            with open(progress_file, 'r', encoding='utf-8') as f:
                progress_data = json.load(f)
            
            duration = time.time() - start_time
            log_performance("load_progress", duration, f"file={progress_file}")
            
            processed_count = len(progress_data.get('processed_urls', []))
            failed_count = len(progress_data.get('failed_urls', []))
            logger.info(f"Прогресс загружен из: {progress_file} "
                       f"(обработано: {processed_count}, ошибок: {failed_count})")
            
            return progress_data
            
        except Exception as e:
            duration = time.time() - start_time
            log_performance("load_progress", duration, f"file={progress_file}, success=False")
            log_error_with_context(e, {"progress_file": str(progress_file), "operation": "load_progress"})
            return {}