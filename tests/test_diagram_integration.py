"""
Интеграционные тесты для проверки генерации Mermaid-диаграмм.
Тестируют создание диаграмм для различных структур закладок.
"""
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.diagram import DiagramGenerator
from src.parser import BookmarkParser
from tests.conftest import create_test_bookmark, create_test_folder


class TestDiagramIntegration:
    """Интеграционные тесты для генератора диаграмм."""
    
    def test_simple_structure_diagram(self, temp_dir):
        """Тест генерации диаграммы для простой структуры."""
        # Создаем тестовую структуру
        bookmark1 = create_test_bookmark("Test Bookmark 1", "https://example1.com")
        bookmark2 = create_test_bookmark("Test Bookmark 2", "https://example2.com")
        
        root_folder = create_test_folder(
            name="Root",
            bookmarks=[bookmark1, bookmark2],
            children=[]
        )
        
        # Создаем генератор диаграмм
        diagram_gen = DiagramGenerator()
        
        # Генерируем диаграмму
        diagram_code = diagram_gen.generate_structure_diagram(root_folder)
        
        # Проверяем результат
        assert diagram_code is not None
        assert "graph TD" in diagram_code
        assert "folder_" in diagram_code
        assert "bookmark_" in diagram_code
        assert "Test Bookmark 1" in diagram_code
        assert "Test Bookmark 2" in diagram_code
        
        # Сохраняем диаграмму
        diagram_path = temp_dir / "test_diagram.md"
        diagram_gen.save_diagram(diagram_code, str(diagram_path))
        
        # Проверяем наличие файла
        assert diagram_path.exists()
        
        # Проверяем содержимое файла
        with open(diagram_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "```mermaid" in content
            assert diagram_code in content
    
    def test_nested_structure_diagram(self, temp_dir):
        """Тест генерации диаграммы для вложенной структуры."""
        # Создаем вложенную структуру
        bookmark1 = create_test_bookmark("Deep Bookmark", "https://deep.example.com")
        
        subfolder = create_test_folder(
            name="Subfolder",
            bookmarks=[bookmark1],
            children=[]
        )
        
        bookmark2 = create_test_bookmark("Top Bookmark", "https://top.example.com")
        
        root_folder = create_test_folder(
            name="Root",
            bookmarks=[bookmark2],
            children=[subfolder]
        )
        
        # Создаем генератор диаграмм
        diagram_gen = DiagramGenerator()
        
        # Генерируем диаграмму
        diagram_code = diagram_gen.generate_structure_diagram(root_folder)
        
        # Проверяем результат
        assert diagram_code is not None
        assert "graph TD" in diagram_code
        
        # Проверяем наличие всех элементов
        assert "Subfolder" in diagram_code or "folder_" in diagram_code
        assert "Deep Bookmark" in diagram_code
        assert "Top Bookmark" in diagram_code
        
        # Проверяем структуру связей
        lines = diagram_code.split('\n')
        folder_lines = [line for line in lines if 'folder_' in line and '-->' not in line]
        connection_lines = [line for line in lines if '-->' in line]
        
        # Должно быть как минимум 2 папки и 2 связи
        assert len(folder_lines) >= 2
        assert len(connection_lines) >= 2
    
    def test_empty_structure_diagram(self, temp_dir):
        """Тест генерации диаграммы для пустой структуры."""
        # Создаем пустую структуру
        root_folder = create_test_folder(
            name="Empty Root",
            bookmarks=[],
            children=[]
        )
        
        # Создаем генератор диаграмм
        diagram_gen = DiagramGenerator()
        
        # Генерируем диаграмму
        diagram_code = diagram_gen.generate_structure_diagram(root_folder)
        
        # Проверяем результат
        assert diagram_code is not None
        assert "graph TD" in diagram_code
        
        # В пустой структуре должна быть только папка
        lines = diagram_code.split('\n')
        non_empty_lines = [line for line in lines if line.strip()]
        
        # Должна быть как минимум одна папка
        assert len(non_empty_lines) >= 1
        
        # Сохраняем диаграмму
        diagram_path = temp_dir / "empty_diagram.md"
        diagram_gen.save_diagram(diagram_code, str(diagram_path))
        
        # Проверяем наличие файла
        assert diagram_path.exists()
    
    def test_complex_nested_structure_diagram(self, temp_dir):
        """Тест генерации диаграммы для сложной вложенной структуры."""
        # Создаем сложную структуру с несколькими уровнями вложенности
        bookmark1 = create_test_bookmark("Bookmark 1", "https://example1.com")
        bookmark2 = create_test_bookmark("Bookmark 2", "https://example2.com")
        bookmark3 = create_test_bookmark("Bookmark 3", "https://example3.com")
        
        # Вложенные папки
        subfolder1 = create_test_folder(
            name="Subfolder 1",
            bookmarks=[bookmark1, bookmark2],
            children=[]
        )
        
        subfolder2 = create_test_folder(
            name="Subfolder 2",
            bookmarks=[bookmark3],
            children=[]
        )
        
        # Корневая папка
        root_folder = create_test_folder(
            name="Complex Root",
            bookmarks=[],
            children=[subfolder1, subfolder2]
        )
        
        # Создаем генератор диаграмм
        diagram_gen = DiagramGenerator()
        
        # Генерируем диаграмму
        diagram_code = diagram_gen.generate_structure_diagram(root_folder)
        
        # Проверяем результат
        assert diagram_code is not None
        assert "graph TD" in diagram_code
        
        # Проверяем наличие всех элементов
        assert "Subfolder 1" in diagram_code or "folder_" in diagram_code
        assert "Subfolder 2" in diagram_code or "folder_" in diagram_code
        assert "Bookmark 1" in diagram_code
        assert "Bookmark 2" in diagram_code
        assert "Bookmark 3" in diagram_code
        
        # Проверяем структуру связей
        lines = diagram_code.split('\n')
        folder_lines = [line for line in lines if 'folder_' in line and '-->' not in line]
        bookmark_lines = [line for line in lines if 'bookmark_' in line]
        connection_lines = [line for line in lines if '-->' in line]
        
        # Должно быть 3 папки и 3 закладки
        assert len(folder_lines) >= 3
        assert len(bookmark_lines) >= 3
        assert len(connection_lines) >= 5  # Минимум 5 связей
    
    def test_diagram_with_special_characters(self, temp_dir):
        """Тест генерации диаграммы с специальными символами в именах."""
        # Создаем структуру со специальными символами
        bookmark1 = create_test_bookmark("Test & Bookmark", "https://example1.com")
        bookmark2 = create_test_bookmark("Test \"Quote\" Bookmark", "https://example2.com")
        
        folder1 = create_test_folder(
            name="Folder (Special)",
            bookmarks=[bookmark1],
            children=[]
        )
        
        folder2 = create_test_folder(
            name="Folder [Brackets]",
            bookmarks=[bookmark2],
            children=[]
        )
        
        root_folder = create_test_folder(
            name="Root",
            bookmarks=[],
            children=[folder1, folder2]
        )
        
        # Создаем генератор диаграмм
        diagram_gen = DiagramGenerator()
        
        # Генерируем диаграмму
        diagram_code = diagram_gen.generate_structure_diagram(root_folder)
        
        # Проверяем результат
        assert diagram_code is not None
        assert "graph TD" in diagram_code
        
        # Сохраняем диаграмму
        diagram_path = temp_dir / "special_chars_diagram.md"
        diagram_gen.save_diagram(diagram_code, str(diagram_path))
        
        # Проверяем наличие файла
        assert diagram_path.exists()
        
        # Проверяем, что файл можно прочитать
        with open(diagram_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "```mermaid" in content
            assert diagram_code in content
    
    def test_diagram_integration_with_parser(self, temp_dir, simple_bookmarks_file):
        """Тест интеграции генератора диаграмм с парсером."""
        # Парсим закладки из файла
        parser = BookmarkParser()
        data = parser.load_json(simple_bookmarks_file)
        root_folder = parser.parse_bookmarks(data)
        
        # Создаем генератор диаграмм
        diagram_gen = DiagramGenerator()
        
        # Генерируем диаграмму
        diagram_code = diagram_gen.generate_structure_diagram(root_folder)
        
        # Проверяем результат
        assert diagram_code is not None
        assert "graph TD" in diagram_code
        
        # Сохраняем диаграмму
        diagram_path = temp_dir / "parser_integration_diagram.md"
        diagram_gen.save_diagram(diagram_code, str(diagram_path))
        
        # Проверяем наличие файла
        assert diagram_path.exists()
        
        # Проверяем содержимое
        with open(diagram_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "```mermaid" in content
            assert "Test Bookmark 1" in content or "bookmark_" in content
            assert "Test Bookmark 2" in content or "bookmark_" in content
    
    def test_diagram_node_counter_reset(self, temp_dir):
        """Тест сброса счетчика узлов при создании нескольких диаграмм."""
        # Создаем первую структуру
        bookmark1 = create_test_bookmark("Bookmark 1", "https://example1.com")
        root_folder1 = create_test_folder(
            name="Root 1",
            bookmarks=[bookmark1],
            children=[]
        )
        
        # Создаем вторую структуру
        bookmark2 = create_test_bookmark("Bookmark 2", "https://example2.com")
        root_folder2 = create_test_folder(
            name="Root 2",
            bookmarks=[bookmark2],
            children=[]
        )
        
        # Создаем генератор диаграмм
        diagram_gen = DiagramGenerator()
        
        # Генерируем первую диаграмму
        diagram_code1 = diagram_gen.generate_structure_diagram(root_folder1)
        
        # Генерируем вторую диаграмму
        diagram_code2 = diagram_gen.generate_structure_diagram(root_folder2)
        
        # Проверяем, что обе диаграммы содержат узлы
        assert "folder_" in diagram_code1
        assert "bookmark_" in diagram_code1
        assert "folder_" in diagram_code2
        assert "bookmark_" in diagram_code2
        
        # Проверяем, что нумерация начинается с 0 для каждой диаграммы
        # Это косвенная проверка - мы не можем напрямую проверить счетчик
        # но можем убедиться, что структура корректна
        lines1 = diagram_code1.split('\n')
        lines2 = diagram_code2.split('\n')
        
        folder_lines1 = [line for line in lines1 if 'folder_' in line and '-->' not in line]
        folder_lines2 = [line for line in lines2 if 'folder_' in line and '-->' not in line]
        
        # В каждой диаграмме должна быть как минимум одна папка
        assert len(folder_lines1) >= 1
        assert len(folder_lines2) >= 1
    
    def test_diagram_file_creation(self, temp_dir):
        """Тест создания файла диаграммы с различными путями."""
        # Создаем простую структуру
        bookmark = create_test_bookmark("Test Bookmark", "https://example.com")
        root_folder = create_test_folder(
            name="Root",
            bookmarks=[bookmark],
            children=[]
        )
        
        # Создаем генератор диаграмм
        diagram_gen = DiagramGenerator()
        
        # Генерируем диаграмму
        diagram_code = diagram_gen.generate_structure_diagram(root_folder)
        
        # Тестируем сохранение в разных путях
        paths_to_test = [
            temp_dir / "diagram1.md",
            temp_dir / "subdir" / "diagram2.md",
            temp_dir / "diagram with spaces.md"
        ]
        
        for path in paths_to_test:
            # Создаем директорию если нужно
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Сохраняем диаграмму
            diagram_gen.save_diagram(diagram_code, str(path))
            
            # Проверяем наличие файла
            assert path.exists()
            
            # Проверяем содержимое
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                assert "```mermaid" in content
                assert diagram_code in content