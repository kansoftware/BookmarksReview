"""
Модуль parser.py
Обеспечивает парсинг JSON-файлов закладок браузера Chrome.
Строит древовидную структуру папок и закладок.
"""
import json
from typing import Dict, Any, Union
from datetime import datetime

from .models import Bookmark, BookmarkFolder
from .logger import get_logger, log_function_call, log_error_with_context

logger = get_logger(__name__)


class BookmarkParser:
    """
    Класс для парсинга JSON-файла закладок Chrome.
    Строит древовидную структуру папок и закладок.
    """
    
    def load_json(self, file_path: str) -> dict:
        """
        Загружает и валидирует JSON-файл закладок.

        Аргументы:
            file_path: Путь к JSON-файлу закладок

        Возвращает:
            dict: Словарь с данными закладок

        Raises:
            FileNotFoundError: Если файл не найден
            json.JSONDecodeError: Если файл содержит некорректный JSON
            ValueError: Если структура JSON некорректна
        """
        log_function_call("load_json", (file_path,))
        
        logger.info(f"Загрузка JSON-файла закладок: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
            logger.debug(f"Файл успешно открыт и прочитан: {file_path}")
        except FileNotFoundError:
            log_error_with_context(
                FileNotFoundError(f"Файл не найден: {file_path}"),
                {"file_path": file_path, "operation": "load_json"}
            )
            raise
        except json.JSONDecodeError as e:
            log_error_with_context(
                e,
                {"file_path": file_path, "operation": "json_parse", "error_line": e.lineno}
            )
            raise
        
        # Валидация структуры
        validation_errors = []
        if not isinstance(data, dict):
            validation_errors.append("JSON должен быть словарем")
        elif 'roots' not in data:
            validation_errors.append("Отсутствует обязательное поле 'roots'")
        elif not isinstance(data['roots'], dict):
            validation_errors.append("Поле 'roots' должно быть словарем")
        
        if validation_errors:
            error_msg = f"Некорректная структура JSON в файле {file_path}: {'; '.join(validation_errors)}"
            log_error_with_context(
                ValueError(error_msg),
                {"file_path": file_path, "validation_errors": validation_errors}
            )
            raise ValueError(error_msg)
        
        logger.info(f"Файл JSON успешно загружен и валидирован: {file_path}")
        logger.debug(f"Структура JSON содержит корневые разделы: {list(data['roots'].keys())}")
        return data
    
    def parse_bookmarks(self, data: dict) -> BookmarkFolder:
        """
        Парсит структуру закладок и возвращает корневую папку.

        Аргументы:
            data: Словарь с данными закладок (результат load_json)

        Возвращает:
            BookmarkFolder: Корневая папка с закладками
        """
        log_function_call("parse_bookmarks", (data,))
        
        logger.info("Начало парсинга структуры закладок")
        
        roots = data.get("roots", {})
        logger.debug(f"Найдены корневые разделы: {list(roots.keys())}")
        
        # Обрабатываем каждый из корневых узлов
        bookmark_bar = roots.get("bookmark_bar", {})
        other = roots.get("other", {})
        synced = roots.get("synced", {})
        
        root_folder = BookmarkFolder(name="Root", children=[], bookmarks=[])
        
        # Обработка корневых папок
        root_sections = [
            ("Bookmark Bar", bookmark_bar),
            ("Other", other),
            ("Mobile", synced)
        ]
        
        for folder_name, folder_data in root_sections:
            if folder_data:
                logger.debug(f"Обработка корневого раздела: {folder_name}")
                folder = self._traverse_node(folder_data, folder_name)
                if folder:
                    if isinstance(folder, BookmarkFolder):
                        root_folder.children.append(folder)
                        logger.debug(f"Добавлена папка: {folder.name} с {len(folder.children)} подпапками и {len(folder.bookmarks)} закладками")
                    elif isinstance(folder, Bookmark):
                        root_folder.bookmarks.append(folder)
                        logger.debug(f"Добавлена закладка: {folder.title}")
        
        total_bookmarks = len(root_folder.bookmarks)
        total_folders = len(root_folder.children)
        logger.info(f"Парсинг завершен. Найдено {total_folders} корневых папок и {total_bookmarks} закладок")
        
        return root_folder
    
    def _traverse_node(self, node: Dict[str, Any], default_name: str = "Untitled") -> Union[BookmarkFolder, Bookmark, None]:
        """
        Рекурсивно обходит узел закладок и возвращает BookmarkFolder или Bookmark.

        Аргументы:
            node: Узел из JSON-файла закладок
            default_name: Имя по умолчанию для узла

        Возвращает:
            BookmarkFolder или Bookmark: Объект модели закладки или папки
        """
        node_type = node.get("type", "").lower()
        title = node.get("name", default_name) or default_name
        
        logger.debug(f"Обработка узла: type={node_type}, title={title}")
        
        # Если это папка
        if node_type == "folder":
            children = []
            bookmarks = []
            
            # Обрабатываем дочерние элементы
            child_nodes = node.get("children", [])
            logger.debug(f"Обработка папки '{title}' с {len(child_nodes)} дочерними элементами")
            
            for i, child in enumerate(child_nodes):
                parsed_child = self._traverse_node(child)
                if parsed_child:
                    if isinstance(parsed_child, BookmarkFolder):
                        children.append(parsed_child)
                        logger.debug(f"  [{i}] Добавлена подпапка: {parsed_child.name}")
                    elif isinstance(parsed_child, Bookmark):
                        bookmarks.append(parsed_child)
                        logger.debug(f"  [{i}] Добавлена закладка: {parsed_child.title}")
                else:
                    logger.debug(f"  [{i}] Пропущен пустой дочерний элемент")
            
            folder = BookmarkFolder(name=title, children=children, bookmarks=bookmarks)
            logger.debug(f"Создана папка '{title}': {len(children)} подпапок, {len(bookmarks)} закладок")
            return folder
        
        # Если это закладка
        elif node_type == "url":
            url = node.get("url", "")
            if not url:
                logger.warning(f"Найдена закладка без URL: {title}")
                return None
            
            # Преобразуем дату добавления из строки в datetime
            date_added_str = node.get("date_added", "")
            date_added = None
            if date_added_str:
                try:
                    # Chrome использует формат времени в микросекундах с 1 января 1601 года
                    # Преобразуем в формат Unix timestamp (с 1 января 1970 года)
                    # Chrome время - это количество микросекунд с 1601 года
                    # Разница между 1601 и 1970 годами в микросекундах: 1164447360000
                    chrome_timestamp = int(date_added_str)
                    unix_timestamp = (chrome_timestamp - 1164447360000) / 100000.0
                    date_added = datetime.fromtimestamp(unix_timestamp)
                    logger.debug(f"Преобразована дата добавления для '{title}': {date_added}")
                except (ValueError, OSError) as e:
                    logger.warning(f"Невозможно преобразовать дату добавления для закладки '{title}': {date_added_str}, ошибка: {e}")
            
            bookmark = Bookmark(title=title, url=url, date_added=date_added)
            logger.debug(f"Создана закладка: {title} -> {url}")
            return bookmark
        
        else:
            logger.warning(f"Неизвестный тип узла закладки: {node_type}, заголовок: {title}")
            return None