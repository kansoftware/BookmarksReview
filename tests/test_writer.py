"""
Модуль test_writer.py
Содержит unit-тесты для модуля writer.py.
"""

import pytest
from pathlib import Path

from src.config import Config
from src.writer import FileSystemWriter


class TestFileSystemWriter:
    """Тесты для класса FileSystemWriter."""

    @pytest.fixture
    def config(self) -> Config:
        """Создает конфигурацию для тестирования."""
        return Config(
            output_dir="test_output",
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

    def test_sanitize_filename_basic(self, writer: FileSystemWriter):
        """Тестирует базовую нормализацию имени файла."""
        assert writer._sanitize_filename("test") == "test"
        assert writer._sanitize_filename("тест") == "тест"
        assert writer._sanitize_filename("test 123") == "test 123"

    def test_sanitize_filename_trims_spaces(self, writer: FileSystemWriter):
        """Тестирует удаление пробелов в начале и конце."""
        assert writer._sanitize_filename("  test  ") == "test"
        assert writer._sanitize_filename("  тест  ") == "тест"

    def test_sanitize_filename_very_long_name(self, writer: FileSystemWriter):
        """Тестирует обработку очень длинных имен."""
        long_name = "a" * 500
        result = writer._sanitize_filename(long_name)
        # Проверяем, что длина результата в байтах не превышает max_path_len
        assert len(result.encode('utf-8')) <= 255
        # Учитываем, что функция резервирует место для расширения файла (3 байта для ".md")
        # и 1 байт для разделителя пути (даже если родительского пути нет, функция может учитывать это)
        expected_max_length = 255 - 3  # 252 байта (3 для ".md")
        assert len(result.encode('utf-8')) <= expected_max_length
        # Проверяем, что результат не пустой
        assert result

    def test_sanitize_filename_with_parent_path(self, writer: FileSystemWriter):
        """Тестирует нормализацию с учетом родительского пути."""
        parent_path = Path("/very/long/path/to/directory")
        long_name = "b" * 500
        result = writer._sanitize_filename(long_name, parent_path=parent_path)
        # Проверяем, что длина результата в байтах учитывает родительский путь
        full_path = parent_path / f"{result}.md"
        assert len(str(full_path).encode('utf-8')) <= 255

    def test_sanitize_filename_empty_after_sanitization(self, writer: FileSystemWriter):
        """Тестирует обработку имен, которые становятся пустыми после очистки."""
        # Символы "<>:" заменяются на подчеркивания, поэтому результат будет "___"
        # Пустое имя после санитизации возникает, когда все символы удаляются
        result = writer._sanitize_filename("<>:")
        # После замены недопустимых символов на подчеркивания получим "___"
        # Это не пустое имя, поэтому оно не заменяется на "unnamed"
        assert result == "___"
        
    def test_sanitize_filename_truly_empty_after_sanitization(self, writer: FileSystemWriter):
        """Тестирует обработку имен, которые становятся пустыми после очистки."""
        # Пробелы после санитизации становятся пустой строкой, которая затем заменяется на "unnamed"
        result = writer._sanitize_filename("   ")
        assert result == "unnamed"
        
    def test_sanitize_filename_only_invalid_chars(self, writer: FileSystemWriter):
        """Тестирует обработку имен, состоящих только из недопустимых символов."""
        # Все символы "<>:" заменяются на подчеркивания, и мы получаем "___"
        # Это не пустая строка, поэтому она не заменяется на "unnamed"
        result = writer._sanitize_filename("<>:")
        assert result == "___"
        
    def test_sanitize_filename_only_spaces_after_sanitization(self, writer: FileSystemWriter):
        """Тестирует обработку имен, которые становятся состоящими только из пробелов после замены недопустимых символов."""
        # Строка, в которой все символы будут заменены на пробелы, а затем убраны
        result = writer._sanitize_filename("   ")
        assert result == "unnamed"

    def test_sanitize_filename_preserves_valid_chars(self, writer: FileSystemWriter):
        """Тестирует сохранение допустимых символов."""
        assert writer._sanitize_filename("test-file_name123") == "test-file_name123"

    def test_sanitize_filename_custom_max_path_len(self, writer: FileSystemWriter):
        """Тестирует использование пользовательского лимита длины пути."""
        long_name = "d" * 500
        parent_path = Path("/path")
        result = writer._sanitize_filename(long_name, parent_path=parent_path, max_path_len=100)
        # Проверяем, что длина результата в байтах учитывает пользовательский лимит
        full_path = parent_path / f"{result}.md"
        assert len(str(full_path).encode('utf-8')) <= 100

    def test_sanitize_filename_unicode_support(self, writer: FileSystemWriter):
        """Тестирует поддержку Unicode."""
        result = writer._sanitize_filename("тест-файл")
        assert result == "тест-файл"
        # Проверяем, что длина в байтах корректно учитывается
        assert len(result.encode('utf-8')) == len("тест-файл".encode('utf-8'))
    
    def test_sanitize_filename_utf8_bytes_length(self, writer: FileSystemWriter):
        """Тестирует корректную обработку длины в байтах для UTF-8 символов."""
        # Используем строку с символами, которые занимают несколько байт в UTF-8
        utf8_name = "тест_файл_с_длинным_названием_и_символами_разной_длины_в_байтах_∞∑"
        result = writer._sanitize_filename(utf8_name)
        # Результат должен быть таким же, но с учетом ограничений длины в байтах
        assert result.encode('utf-8')  # Проверяем, что результат можно закодировать в UTF-8
        # Проверяем, что длина в байтах не превышает лимит
        assert len(result.encode('utf-8')) <= 255 - 4  # 251 байт (3 для ".md" и 1 для разделителя пути)
    
    def test_sanitize_filename_utf8_bytes_length_with_parent_path(self, writer: FileSystemWriter):
        """Тестирует корректную обработку длины в байтах для UTF-8 символов с родительским путем."""
        # Родительский путь с UTF-8 символами
        parent_path = Path("/путь/к/директории")
        # Имя файла с UTF-8 символами
        utf8_name = "тест_файл_с_utf8_символами_∞∑"
        result = writer._sanitize_filename(utf8_name, parent_path=parent_path)
        # Общая длина пути в байтах не должна превышать max_path_len
        full_path = parent_path / f"{result}.md"
        assert len(str(full_path).encode('utf-8')) <= 255

    def test_sanitize_filename_backward_compatibility(self, writer: FileSystemWriter):
        """Тестирует обратную совместимость."""
        result = writer._sanitize_filename("test")
        assert result == "test"

    def test_sanitize_filename_with_long_parent_path(self, writer: FileSystemWriter):
        """Тестирует обработку длинного родительского пути."""
        # Длинный родительский путь
        long_parent_path = Path("/" + "a" * 200 + "/subdir")
        # Длинное имя файла
        long_name = "b" * 10
        result = writer._sanitize_filename(long_name, parent_path=long_parent_path)
        # Общая длина пути в байтах не должна превышать max_path_len
        total_path = long_parent_path / f"{result}.md"
        assert len(str(total_path).encode('utf-8')) <= 255
        # Должно быть обрезано с учетом длины родительского пути
        assert len(result.encode('utf-8')) < 100  # Должно быть усечено