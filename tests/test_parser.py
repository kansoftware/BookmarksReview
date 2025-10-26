"""
Тесты для модуля parser.py
"""
import json
import tempfile
import os
from datetime import datetime
from src.parser import BookmarkParser
from src.models import Bookmark, BookmarkFolder


def test_parse_chrome_bookmarks():
    """Тестирует парсинг JSON-файла закладок Chrome"""
    # Создаем временный файл с тестовыми данными закладок
    test_data = {
        "checksum": "12345",
        "roots": {
            "bookmark_bar": {
                "children": [
                    {
                        "date_added": "13321112345678901",
                        "id": "1",
                        "name": "Test Bookmark",
                        "type": "url",
                        "url": "https://example.com"
                    },
                    {
                        "children": [
                            {
                                "date_added": "13321112345678902",
                                "id": "3",
                                "name": "Nested Bookmark",
                                "type": "url",
                                "url": "https://nested-example.com"
                            }
                        ],
                        "date_added": "13321112345678900",
                        "id": "2",
                        "name": "Test Folder",
                        "type": "folder"
                    }
                ],
                "date_added": "13321112345678900",
                "id": "0",
                "name": "Bookmark Bar",
                "type": "folder"
            },
            "other": {
                "children": [],
                "date_added": "13321112345678900",
                "id": "4",
                "name": "Other bookmarks",
                "type": "folder"
            },
            "synced": {
                "children": [],
                "date_added": "13321112345678900",
                "id": "5",
                "name": "Mobile bookmarks",
                "type": "folder"
            }
        },
        "version": 1
    }

    # Создаем временный файл
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as temp_file:
        json.dump(test_data, temp_file)
        temp_file_path = temp_file.name

    try:
        # Вызываем функцию парсинга
        parser = BookmarkParser()
        data = parser.load_json(temp_file_path)
        result = parser.parse_bookmarks(data)

        # Проверяем результат
        assert isinstance(result, BookmarkFolder)
        assert result.name == "Root"
        assert len(result.children) == 3  # Bookmark Bar, Other и Mobile папки

        # Находим папку Bookmark Bar
        bookmark_bar = None
        other_folder = None
        mobile_folder = None
        
        for child in result.children:
            if child.name == "Bookmark Bar":
                bookmark_bar = child
            elif child.name == "Other bookmarks":
                other_folder = child
            elif child.name == "Mobile bookmarks":
                mobile_folder = child
        
        assert bookmark_bar is not None
        assert other_folder is not None
        assert mobile_folder is not None
        
        # Проверяем, что Other и Mobile папки пусты
        assert len(other_folder.children) == 0
        assert len(other_folder.bookmarks) == 0
        assert len(mobile_folder.children) == 0
        assert len(mobile_folder.bookmarks) == 0

        # Проверяем, что дочерние элементы Bookmark Bar корректны
        assert len(bookmark_bar.children) == 1  # Папка "Test Folder"
        assert len(bookmark_bar.bookmarks) == 1  # Закладка "Test Bookmark"

        # Проверяем папку
        test_folder = bookmark_bar.children[0]
        assert test_folder.name == "Test Folder"
        assert len(test_folder.bookmarks) == 1
        assert test_folder.bookmarks[0].title == "Nested Bookmark"
        assert test_folder.bookmarks[0].url == "https://nested-example.com"

        # Проверяем закладку
        test_bookmark = bookmark_bar.bookmarks[0]
        assert test_bookmark.title == "Test Bookmark"
        assert test_bookmark.url == "https://example.com"
        assert isinstance(test_bookmark.date_added, datetime)

        print("Все тесты пройдены успешно!")
    finally:
        # Удаляем временный файл
        os.unlink(temp_file_path)


if __name__ == "__main__":
    test_parse_chrome_bookmarks()