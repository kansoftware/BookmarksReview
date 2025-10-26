"""
Тесты для модуля parser.py
"""
import json
import tempfile
import os
import pytest
from datetime import datetime
from unittest.mock import patch, mock_open
from src.parser import BookmarkParser
from src.models import Bookmark, BookmarkFolder


class TestBookmarkParser:
    """Тесты для класса BookmarkParser"""
    
    def test_parse_chrome_bookmarks(self):
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
        finally:
            # Удаляем временный файл
            os.unlink(temp_file_path)
    
    def test_load_json_file_not_found(self):
        """Тестирует обработку отсутствующего файла"""
        parser = BookmarkParser()
        with pytest.raises(FileNotFoundError):
            parser.load_json("nonexistent_file.json")
    
    def test_load_json_invalid_json(self):
        """Тестирует обработку некорректного JSON"""
        # Создаем временный файл с некорректным JSON
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as temp_file:
            temp_file.write('{"invalid": json}')
            temp_file_path = temp_file.name
        
        try:
            parser = BookmarkParser()
            with pytest.raises(json.JSONDecodeError):
                parser.load_json(temp_file_path)
        finally:
            os.unlink(temp_file_path)
    
    def test_load_json_invalid_structure(self):
        """Тестирует валидацию структуры JSON"""
        # Тест 1: JSON не является словарем
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as temp_file:
            json.dump(["not", "a", "dict"], temp_file)
            temp_file_path = temp_file.name
        
        try:
            parser = BookmarkParser()
            with pytest.raises(ValueError, match="JSON должен быть словарем"):
                parser.load_json(temp_file_path)
        finally:
            os.unlink(temp_file_path)
        
        # Тест 2: Отсутствует поле 'roots'
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as temp_file:
            json.dump({"not_roots": {}}, temp_file)
            temp_file_path = temp_file.name
        
        try:
            parser = BookmarkParser()
            with pytest.raises(ValueError, match="Отсутствует обязательное поле 'roots'"):
                parser.load_json(temp_file_path)
        finally:
            os.unlink(temp_file_path)
        
        # Тест 3: Поле 'roots' не является словарем
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as temp_file:
            json.dump({"roots": "not_a_dict"}, temp_file)
            temp_file_path = temp_file.name
        
        try:
            parser = BookmarkParser()
            with pytest.raises(ValueError, match="Поле 'roots' должно быть словарем"):
                parser.load_json(temp_file_path)
        finally:
            os.unlink(temp_file_path)
    
    def test_parse_bookmarks_empty_roots(self):
        """Тестирует парсинг с пустыми корневыми разделами"""
        parser = BookmarkParser()
        data = {"roots": {}}
        result = parser.parse_bookmarks(data)
        
        assert isinstance(result, BookmarkFolder)
        assert result.name == "Root"
        assert len(result.children) == 0
        assert len(result.bookmarks) == 0
    
    def test_parse_bookmarks_missing_roots(self):
        """Тестирует парсинг с отсутствующим полем roots"""
        parser = BookmarkParser()
        data = {}
        result = parser.parse_bookmarks(data)
        
        assert isinstance(result, BookmarkFolder)
        assert result.name == "Root"
        assert len(result.children) == 0
        assert len(result.bookmarks) == 0
    
    def test_traverse_node_folder_without_type(self):
        """Тестирует обработку папки без указания типа"""
        parser = BookmarkParser()
        node = {
            "name": "Folder without type",
            "children": [
                {
                    "name": "Bookmark",
                    "type": "url",
                    "url": "https://example.com"
                }
            ]
        }
        
        result = parser._traverse_node(node)
        
        assert isinstance(result, BookmarkFolder)
        assert result.name == "Folder without type"
        assert len(result.children) == 0
        assert len(result.bookmarks) == 1
        assert result.bookmarks[0].title == "Bookmark"
        assert result.bookmarks[0].url == "https://example.com"
    
    def test_traverse_node_empty_title(self):
        """Тестирует обработку узла с пустым заголовком"""
        parser = BookmarkParser()
        node = {
            "name": "",
            "type": "url",
            "url": "https://example.com"
        }
        
        result = parser._traverse_node(node)
        # Проверяем, что для пустого заголовка используется значение по умолчанию "Untitled"
        assert result is not None
        assert isinstance(result, Bookmark)
        assert result.title == "Untitled"
        assert result.url == "https://example.com"
    
    def test_traverse_node_unknown_type(self):
        """Тестирует обработку узла с неизвестным типом"""
        parser = BookmarkParser()
        node = {
            "name": "Unknown type node",
            "type": "unknown_type"
        }
        
        result = parser._traverse_node(node)
        assert result is None
    
    def test_traverse_node_bookmark_without_url(self):
        """Тестирует обработку закладки без URL"""
        parser = BookmarkParser()
        node = {
            "name": "Bookmark without URL",
            "type": "url"
        }
        
        result = parser._traverse_node(node)
        assert result is None
    
    def test_traverse_node_invalid_date_added(self):
        """Тестирует обработку закладки с некорректной датой"""
        parser = BookmarkParser()
        node = {
            "name": "Bookmark with invalid date",
            "type": "url",
            "url": "https://example.com",
            "date_added": "invalid_date"
        }
        
        result = parser._traverse_node(node)
        
        assert isinstance(result, Bookmark)
        assert result.title == "Bookmark with invalid date"
        assert result.url == "https://example.com"
        assert result.date_added is None
    
    def test_traverse_node_nested_structure(self):
        """Тестирует обработку вложенной структуры папок и закладок"""
        parser = BookmarkParser()
        node = {
            "name": "Root Folder",
            "type": "folder",
            "children": [
                {
                    "name": "Subfolder 1",
                    "type": "folder",
                    "children": [
                        {
                            "name": "Deep Bookmark",
                            "type": "url",
                            "url": "https://deep.example.com",
                            "date_added": "13321112345678901"
                        }
                    ]
                },
                {
                    "name": "Subfolder 2",
                    "type": "folder",
                    "children": []
                },
                {
                    "name": "Root Bookmark",
                    "type": "url",
                    "url": "https://root.example.com",
                    "date_added": "13321112345678902"
                }
            ]
        }
        
        result = parser._traverse_node(node)
        
        assert isinstance(result, BookmarkFolder)
        assert result.name == "Root Folder"
        assert len(result.children) == 2  # Subfolder 1 и Subfolder 2
        assert len(result.bookmarks) == 1  # Root Bookmark
        
        # Проверяем Subfolder 1
        subfolder1 = result.children[0]
        assert subfolder1.name == "Subfolder 1"
        assert len(subfolder1.children) == 0
        assert len(subfolder1.bookmarks) == 1
        assert subfolder1.bookmarks[0].title == "Deep Bookmark"
        assert subfolder1.bookmarks[0].url == "https://deep.example.com"
        
        # Проверяем Subfolder 2
        subfolder2 = result.children[1]
        assert subfolder2.name == "Subfolder 2"
        assert len(subfolder2.children) == 0
        assert len(subfolder2.bookmarks) == 0
        
        # Проверяем Root Bookmark
        root_bookmark = result.bookmarks[0]
        assert root_bookmark.title == "Root Bookmark"
        assert root_bookmark.url == "https://root.example.com"
    
    def test_parse_bookmarks_with_special_characters(self):
        """Тестирует парсинг закладок со специальными символами в названиях"""
        test_data = {
            "roots": {
                "bookmark_bar": {
                    "children": [
                        {
                            "date_added": "13321112345678901",
                            "id": "1",
                            "name": "Закладка с русскими символами & символами",
                            "type": "url",
                            "url": "https://example.com"
                        },
                        {
                            "children": [],
                            "date_added": "13321112345678900",
                            "id": "2",
                            "name": "Папка с 'кавычками' и \"двойными кавычками\"",
                            "type": "folder"
                        }
                    ],
                    "date_added": "13321112345678900",
                    "id": "0",
                    "name": "Bookmark Bar",
                    "type": "folder"
                }
            }
        }
        
        parser = BookmarkParser()
        result = parser.parse_bookmarks(test_data)
        
        assert isinstance(result, BookmarkFolder)
        assert len(result.children) == 1
        assert len(result.children[0].bookmarks) == 1
        assert len(result.children[0].children) == 1
        
        # Проверяем закладку со специальными символами
        bookmark = result.children[0].bookmarks[0]
        assert "русскими символами" in bookmark.title
        
        # Проверяем папку со специальными символами
        folder = result.children[0].children[0]
        assert "кавычками" in folder.name


if __name__ == "__main__":
    pytest.main([__file__])