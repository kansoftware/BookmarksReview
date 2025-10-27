"""
Модуль test_integration_long_paths.py
Содержит интеграционные тесты для проверки обработки длинных имен файлов.
"""

import pytest
import tempfile
from datetime import datetime
from pathlib import Path

from src.config import Config
from src.models import Bookmark, BookmarkFolder, ProcessedPage
from src.writer import FileSystemWriter


class TestIntegrationLongPaths:
    """Интеграционные тесты для проверки обработки длинных путей."""

    @pytest.fixture
    def config(self) -> Config:
        """Создает конфигурацию для тестирования."""
        with tempfile.TemporaryDirectory() as temp_dir:
            return Config(
                output_dir=temp_dir,
                markdown_include_metadata=True,
                generate_mermaid_diagram=True,
                llm_api_key="test_key",
                llm_base_url="https://api.example.com",
                llm_model="gpt-3.5-turbo",
                llm_max_tokens=1000,
                llm_temperature=0.7,
                llm_rate_limit=10,
                fetch_timeout=30,
                fetch_max_concurrent=5,
                fetch_max_size_mb=5,
                fetch_retry_attempts=3,
                fetch_retry_delay=1,
                fetch_max_redirects=5,
                prompt_file="prompts/summarize_prompt.txt",
                log_level="INFO",
                log_file="bookmarks_export.log",
            )

    @pytest.fixture
    def writer(self, config: Config) -> FileSystemWriter:
        """Создает экземпляр FileSystemWriter для тестирования."""
        return FileSystemWriter(config)

    def test_create_folder_with_long_name(self, writer: FileSystemWriter):
        """Тестирует создание папки с длинным именем."""
        long_folder_name = "Very Long Folder Name " * 10 # Создаем очень длинное имя
        folder = BookmarkFolder(name=long_folder_name, children=[], bookmarks=[])
        
        # Проверяем, что папка создается без ошибок
        result_path = writer.create_folder_structure(folder)
        
        # Проверяем, что папка была создана
        assert result_path.exists()
        assert result_path.is_dir()

    def test_create_file_with_long_name(self, writer: FileSystemWriter):
        """Тестирует создание файла с длинным именем."""
        # Создаем закладку с очень длинным заголовком
        long_title = "Very Long Bookmark Title " * 10
        bookmark = Bookmark(
            title=long_title,
            url="https://example.com",
            date_added=datetime.now()
        )
        
        # Создаем обработанную страницу
        processed_page = ProcessedPage(
            url="https://example.com",
            title=long_title,
            summary="Test summary",
            fetch_date=datetime.now(),
            status="success"
        )
        
        # Получаем путь для файла
        file_path = writer.get_bookmark_file_path(bookmark)
        
        # Проверяем, что имя файла было ограничено
        assert len(file_path.name) <= 255
        
        # Проверяем, что файл может быть записан без ошибок
        writer.write_markdown(processed_page, file_path)
        
        # Проверяем, что файл был создан
        assert file_path.exists()
        assert file_path.is_file()

    def test_nested_structure_with_long_names(self, writer: FileSystemWriter):
        """Тестирует создание вложенной структуры с длинными именами."""
        # Создаем вложенную структуру с длинными именами
        very_long_name = "Extremely Long Name " * 15
        
        # Создаем дочернюю папку
        child_folder = BookmarkFolder(
            name=very_long_name + " Child",
            children=[],
            bookmarks=[]
        )
        
        # Создаем родительскую папку
        parent_folder = BookmarkFolder(
            name=very_long_name + " Parent",
            children=[child_folder],
            bookmarks=[]
        )
        
        # Добавляем закладку с длинным именем в дочернюю папку
        long_title = "Very Long Bookmark Title " * 10
        bookmark = Bookmark(
            title=long_title,
            url="https://example.com",
            date_added=datetime.now()
        )
        child_folder.bookmarks.append(bookmark)
        
        # Создаем обработанную страницу
        processed_page = ProcessedPage(
            url="https://example.com",
            title=long_title,
            summary="Test summary",
            fetch_date=datetime.now(),
            status="success"
        )
        
        # Создаем структуру папок
        result_path = writer.create_folder_structure(parent_folder)
        
        # Получаем путь для файла
        file_path = writer.get_bookmark_file_path(
            bookmark, 
            base_path=result_path / writer._sanitize_filename(child_folder.name, parent_path=result_path)
        )
        
        # Проверяем, что файл может быть записан без ошибок
        writer.write_markdown(processed_page, file_path)
        
        # Проверяем, что файл был создан
        assert file_path.exists()
        assert file_path.is_file()