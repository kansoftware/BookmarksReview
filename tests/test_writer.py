"""
Модуль test_writer.py
Unit-тесты для модуля writer.py
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

from src.writer import FileSystemWriter
from src.models import ProcessedPage, BookmarkFolder, Bookmark
from src.config import Config


@pytest.fixture
def temp_dir():
    """Создает временную директорию для тестов."""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path)


@pytest.fixture
def test_config(temp_dir):
    """Создает тестовую конфигурацию."""
    return Config(
        llm_api_key="test_key",
        llm_base_url="https://api.test.com",
        llm_model="test-model",
        llm_max_tokens=1000,
        llm_temperature=0.7,
        llm_rate_limit=3,
        fetch_timeout=30,
        fetch_max_concurrent=10,
        fetch_max_size_mb=5,
        fetch_retry_attempts=3,
        fetch_retry_delay=1.5,
        output_dir=str(temp_dir),
        markdown_include_metadata=True,
        generate_mermaid_diagram=True,
        prompt_file="./prompts/test_prompt.txt",
        log_level="INFO",
        log_file="test.log"
    )


@pytest.fixture
def writer(test_config):
    """Создает экземпляр FileSystemWriter для тестов."""
    return FileSystemWriter(test_config)


@pytest.fixture
def sample_processed_page():
    """Создает образец обработанной страницы."""
    return ProcessedPage(
        url="https://example.com",
        title="Example Page",
        summary="## Основная тема\nПример страницы\n\n## Ключевые моменты\n- Пункт 1\n- Пункт 2\n\n## Вывод\nЗаключение",
        fetch_date=datetime(2025, 10, 25, 21, 8, 0),
        status="success"
    )


@pytest.fixture
def sample_bookmark():
    """Создает образец закладки."""
    return Bookmark(
        title="Test Bookmark",
        url="https://test.com",
        date_added=datetime(2025, 10, 25, 21, 8, 0)
    )


@pytest.fixture
def sample_folder():
    """Создает образец папки с закладками."""
    child_folder = BookmarkFolder(
        name="Child Folder",
        children=[],
        bookmarks=[
            Bookmark("Child Bookmark", "https://child.com", datetime.now())
        ]
    )
    
    return BookmarkFolder(
        name="Root Folder",
        children=[child_folder],
        bookmarks=[
            Bookmark("Root Bookmark", "https://root.com", datetime.now())
        ]
    )


class TestFileSystemWriter:
    """Тесты для класса FileSystemWriter."""
    
    def test_init_creates_output_directory(self, test_config, temp_dir):
        """Проверяет, что конструктор создает выходную директорию."""
        writer = FileSystemWriter(test_config)
        assert temp_dir.exists()
        assert writer.output_dir == temp_dir
    
    def test_create_folder_structure(self, writer, sample_folder, temp_dir):
        """Проверяет создание структуры папок."""
        writer.create_folder_structure(sample_folder)
        
        # Проверяем создание корневой папки
        root_path = temp_dir / "Root Folder"
        assert root_path.exists()
        assert root_path.is_dir()
        
        # Проверяем создание дочерней папки
        child_path = root_path / "Child Folder"
        assert child_path.exists()
        assert child_path.is_dir()
    
    def test_write_markdown_with_metadata(self, writer, sample_processed_page, temp_dir):
        """Проверяет запись Markdown-файла с метаданными."""
        file_path = temp_dir / "test_file.md"
        writer.write_markdown(sample_processed_page, file_path)
        
        assert file_path.exists()
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Проверяем наличие YAML frontmatter
        assert content.startswith("---")
        assert "url: https://example.com" in content
        assert "title: Example Page" in content
        assert "status: success" in content
        
        # Проверяем основное содержимое
        assert "# Example Page" in content
        assert "## Основная тема" in content
        assert "Источник: https://example.com" in content
    
    def test_write_markdown_without_metadata(self, test_config, sample_processed_page, temp_dir):
        """Проверяет запись Markdown-файла без метаданных."""
        test_config.markdown_include_metadata = False
        writer = FileSystemWriter(test_config)
        
        file_path = temp_dir / "test_file.md"
        writer.write_markdown(sample_processed_page, file_path)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Проверяем отсутствие YAML frontmatter
        assert not content.startswith("---")
        
        # Проверяем основное содержимое
        assert "# Example Page" in content
        assert "Источник: https://example.com" in content
    
    def test_sanitize_filename_basic(self, writer):
        """Проверяет базовую санитизацию имен файлов."""
        # Удаление недопустимых символов
        assert writer._sanitize_filename('file<>name') == 'filename'
        assert writer._sanitize_filename('file"name') == 'filename'
        assert writer._sanitize_filename('file:name') == 'filename'
        assert writer._sanitize_filename('file/name') == 'filename'
        assert writer._sanitize_filename('file\\name') == 'filename'
        assert writer._sanitize_filename('file|name') == 'filename'
        assert writer._sanitize_filename('file?name') == 'filename'
        assert writer._sanitize_filename('file*name') == 'filename'
    
    def test_sanitize_filename_whitespace(self, writer):
        """Проверяет обработку пробелов."""
        assert writer._sanitize_filename('  file name  ') == 'file name'
        assert writer._sanitize_filename('file    name') == 'file name'
        assert writer._sanitize_filename('file\tname') == 'file name'
    
    def test_sanitize_filename_cyrillic(self, writer):
        """Проверяет сохранение кириллицы."""
        assert writer._sanitize_filename('Тестовый файл') == 'Тестовый файл'
        assert writer._sanitize_filename('Файл с русскими буквами') == 'Файл с русскими буквами'
    
    def test_sanitize_filename_length_limit(self, writer):
        """Проверяет ограничение длины имени файла."""
        long_name = 'a' * 300
        sanitized = writer._sanitize_filename(long_name)
        assert len(sanitized) <= 255
    
    def test_sanitize_filename_empty_result(self, writer):
        """Проверяет обработку случая, когда имя становится пустым."""
        assert writer._sanitize_filename('<>:"/\\|?*') == 'unnamed'
        assert writer._sanitize_filename('   ') == 'unnamed'
    
    def test_generate_metadata(self, writer, sample_processed_page):
        """Проверяет генерацию YAML метаданных."""
        metadata = writer._generate_metadata(sample_processed_page)
        
        assert 'url: https://example.com' in metadata
        assert 'title: Example Page' in metadata
        assert 'status: success' in metadata
        assert 'date_processed:' in metadata
    
    def test_get_bookmark_file_path(self, writer, sample_bookmark, temp_dir):
        """Проверяет определение пути к файлу закладки."""
        file_path = writer.get_bookmark_file_path(sample_bookmark)
        
        expected_path = temp_dir / "Test Bookmark.md"
        assert file_path == expected_path
    
    def test_get_bookmark_file_path_with_md_extension(self, writer, sample_bookmark, temp_dir):
        """Проверяет, что к имени файла добавляется расширение .md."""
        sample_bookmark.title = "test.md"
        file_path = writer.get_bookmark_file_path(sample_bookmark)
        
        # Не должно быть двойного расширения
        assert str(file_path).endswith('.md')
        assert not str(file_path).endswith('.md.md')
    
    def test_save_and_load_progress(self, writer, temp_dir):
        """Проверяет сохранение и загрузку прогресса."""
        processed_urls = ["https://example1.com", "https://example2.com"]
        failed_urls = ["https://failed.com"]
        
        # Сохраняем прогресс
        writer.save_progress(processed_urls, failed_urls)
        
        progress_file = temp_dir / 'progress.json'
        assert progress_file.exists()
        
        # Загружаем прогресс
        loaded_progress = writer.load_progress()
        
        assert 'processed_urls' in loaded_progress
        assert 'failed_urls' in loaded_progress
        assert 'timestamp' in loaded_progress
        assert loaded_progress['processed_urls'] == processed_urls
        assert loaded_progress['failed_urls'] == failed_urls
    
    def test_load_progress_no_file(self, writer):
        """Проверяет загрузку прогресса при отсутствии файла."""
        progress = writer.load_progress()
        assert progress == {}
    
    def test_format_markdown_content(self, writer, sample_processed_page):
        """Проверяет форматирование содержимого Markdown."""
        content = writer._format_markdown_content(sample_processed_page)
        
        # Проверяем структуру содержимого
        assert content.startswith("---")  # YAML frontmatter
        assert "# Example Page" in content
        assert "## Основная тема" in content
        assert "Источник: https://example.com" in content
        assert content.endswith("---\nИсточник: https://example.com")
    
    def test_write_markdown_creates_directories(self, writer, sample_processed_page, temp_dir):
        """Проверяет, что write_markdown создает необходимые директории."""
        nested_path = temp_dir / "nested" / "directory" / "test.md"
        writer.write_markdown(sample_processed_page, nested_path)
        
        assert nested_path.exists()
        assert nested_path.parent.exists()
    
    @patch('builtins.open', side_effect=IOError("Permission denied"))
    def test_write_markdown_error_handling(self, mock_open, writer, sample_processed_page, temp_dir):
        """Проверяет обработку ошибок при записи файла."""
        file_path = temp_dir / "test.md"
        
        with pytest.raises(IOError):
            writer.write_markdown(sample_processed_page, file_path)
    
    def test_create_folder_structure_with_base_path(self, writer, sample_folder, temp_dir):
        """Проверяет создание структуры папок с указанием базового пути."""
        base_path = temp_dir / "custom_base"
        writer.create_folder_structure(sample_folder, base_path)
        
        # Проверяем создание папок в указанной базовой директории
        root_path = base_path / "Root Folder"
        assert root_path.exists()
        
        child_path = root_path / "Child Folder"
        assert child_path.exists()