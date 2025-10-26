"""
Модуль test_utils.py
Содержит unit-тесты для вспомогательных утилит из модуля src/utils.py.
"""
import pytest
import tempfile
import time
import asyncio
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

from src.utils import (
    PathUtils, TextUtils, DateUtils, ValidationUtils, 
    ErrorUtils, HashUtils, ProgressTracker
)


class TestPathUtils:
    """Тесты для утилит работы с путями."""
    
    def test_ensure_dir_creates_directory(self):
        """Тест создания директории."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = Path(temp_dir) / "new_dir" / "sub_dir"
            result = PathUtils.ensure_dir(test_path)
            
            assert result.exists()
            assert result.is_dir()
            assert result == test_path
    
    def test_ensure_dir_existing_directory(self):
        """Тест работы с существующей директорией."""
        with tempfile.TemporaryDirectory() as temp_dir:
            existing_path = Path(temp_dir)
            result = PathUtils.ensure_dir(existing_path)
            
            assert result.exists()
            assert result == existing_path
    
    def test_safe_filename_removes_invalid_chars(self):
        """Тест удаления недопустимых символов из имени файла."""
        invalid_name = 'file<>:"/\\|?*name'
        result = PathUtils.safe_filename(invalid_name)
        
        assert '<' not in result
        assert '>' not in result
        assert ':' not in result
        assert '"' not in result
        assert '/' not in result
        assert '\\' not in result
        assert '|' not in result
        assert '?' not in result
        assert '*' not in result
    
    def test_safe_filename_normalizes_whitespace(self):
        """Тест нормализации пробелов в имени файла."""
        name_with_spaces = 'file    name   with   spaces'
        result = PathUtils.safe_filename(name_with_spaces)
        
        assert result == 'file name with spaces'
    
    def test_safe_filename_limits_length(self):
        """Тест ограничения длины имени файла."""
        long_name = 'a' * 300
        result = PathUtils.safe_filename(long_name)
        
        assert len(result) <= 255
    
    def test_safe_filename_empty_result(self):
        """Т обработки пустого результата после очистки."""
        invalid_name = '<>:"/\\|?*'
        result = PathUtils.safe_filename(invalid_name)
        
        assert result == "unnamed"
    
    def test_get_relative_path(self):
        """Тест вычисления относительного пути."""
        base = Path("/home/user/documents")
        target = Path("/home/user/documents/projects/test")
        result = PathUtils.get_relative_path(target, base)
        
        assert str(result) == "projects/test"
    
    def test_get_relative_path_not_relative(self):
        """Тест обработки пути не относительного к базе."""
        base = Path("/home/user/documents")
        target = Path("/etc/config")
        result = PathUtils.get_relative_path(target, base)
        
        assert result == target


class TestTextUtils:
    """Тесты для утилит обработки текста."""
    
    def test_clean_text_removes_extra_whitespace(self):
        """Тест удаления лишних пробелов."""
        dirty_text = "  Text   with   extra   \n   whitespace  "
        result = TextUtils.clean_text(dirty_text)
        
        assert result == "Text with extra whitespace"
    
    def test_clean_text_empty_string(self):
        """Тест обработки пустой строки."""
        result = TextUtils.clean_text("")
        
        assert result == ""
    
    def test_clean_text_none(self):
        """Тест обработки None."""
        result = TextUtils.clean_text(None)
        
        assert result == ""
    
    def test_truncate_text_shorter_than_limit(self):
        """Тест обрезки текста короче лимита."""
        text = "Short text"
        result = TextUtils.truncate_text(text, 20)
        
        assert result == "Short text"
    
    def test_truncate_text_longer_than_limit(self):
        """Тест обрезки текста длиннее лимита."""
        text = "This is a very long text that should be truncated"
        result = TextUtils.truncate_text(text, 20)
        
        assert len(result) <= 20
        assert result.endswith("...")
    
    def test_extract_domain_valid_url(self):
        """Тест извлечения домена из корректного URL."""
        url = "https://www.example.com/path/to/page"
        result = TextUtils.extract_domain(url)
        
        assert result == "www.example.com"
    
    def test_extract_domain_invalid_url(self):
        """Тест извлечения домена из некорректного URL."""
        url = "not-a-valid-url"
        result = TextUtils.extract_domain(url)
        
        assert result is None
    
    def test_normalize_whitespace(self):
        """Тест нормализации пробельных символов."""
        text = "Text   with\t\n   multiple   whitespace"
        result = TextUtils.normalize_whitespace(text)
        
        assert result == "Text with multiple whitespace"


class TestDateUtils:
    """Тесты для утилит работы с датами."""
    
    def test_chrome_timestamp_to_datetime_valid(self):
        """Тест преобразования временной метки Chrome."""
        # Используем известную временную метку
        chrome_timestamp = "13284263264000000"  # Пример временной метки
        result = DateUtils.chrome_timestamp_to_datetime(chrome_timestamp)
        
        assert isinstance(result, datetime)
    
    def test_chrome_timestamp_to_datetime_invalid(self):
        """Тест преобразования некорректной временной метки."""
        invalid_timestamp = "not-a-timestamp"
        result = DateUtils.chrome_timestamp_to_datetime(invalid_timestamp)
        
        assert result is None
    
    def test_format_duration_seconds(self):
        """Тест форматирования продолжительности в секундах."""
        result = DateUtils.format_duration(30.5)
        
        assert "30.5 сек" in result
    
    def test_format_duration_minutes(self):
        """Тест форматирования продолжительности в минутах."""
        result = DateUtils.format_duration(150)
        
        assert "2.5 мин" in result
    
    def test_format_duration_hours(self):
        """Тест форматирования продолжительности в часах."""
        result = DateUtils.format_duration(7200)
        
        assert "2.0 час" in result
    
    def test_now_iso(self):
        """Тест получения текущего времени в ISO формате."""
        result = DateUtils.now_iso()
        
        assert isinstance(result, str)
        # Проверяем формат ISO (должен содержать 'T' и быть валидной датой)
        assert 'T' in result
        # Проверяем что можно распарсить как ISO дату
        datetime.fromisoformat(result)


class TestValidationUtils:
    """Тесты для утилит валидации."""
    
    def test_is_valid_url_http(self):
        """Тест валидации HTTP URL."""
        url = "http://example.com"
        result = ValidationUtils.is_valid_url(url)
        
        assert result is True
    
    def test_is_valid_url_https(self):
        """Тест валидации HTTPS URL."""
        url = "https://example.com"
        result = ValidationUtils.is_valid_url(url)
        
        assert result is True
    
    def test_is_valid_url_invalid_scheme(self):
        """Тест валидации URL с некорректной схемой."""
        url = "ftp://example.com"
        result = ValidationUtils.is_valid_url(url)
        
        assert result is False
    
    def test_is_valid_url_no_scheme(self):
        """Тест валидации URL без схемы."""
        url = "example.com"
        result = ValidationUtils.is_valid_url(url)
        
        assert result is False
    
    def test_validate_json_structure_valid(self):
        """Тест валидации корректной JSON структуры."""
        data = {"key1": "value1", "key2": "value2"}
        required_keys = ["key1", "key2"]
        result = ValidationUtils.validate_json_structure(data, required_keys)
        
        assert result is True
    
    def test_validate_json_structure_missing_key(self):
        """Тест валидации JSON структуры с отсутствующим ключом."""
        data = {"key1": "value1"}
        required_keys = ["key1", "key2"]
        result = ValidationUtils.validate_json_structure(data, required_keys)
        
        assert result is False
    
    def test_validate_json_structure_not_dict(self):
        """Тест валидации не-словаря."""
        data = "not a dict"
        required_keys = ["key1"]
        result = ValidationUtils.validate_json_structure(data, required_keys)
        
        assert result is False
    
    def test_is_safe_path_safe(self):
        """Тест проверки безопасного пути."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            safe_path = base / "subdir" / "file.txt"
            result = ValidationUtils.is_safe_path(safe_path, base)
            
            assert result is True
    
    def test_is_safe_path_unsafe(self):
        """Тест проверки небезопасного пути."""
        base = Path("/home/user/documents")
        unsafe_path = Path("/etc/passwd")
        result = ValidationUtils.is_safe_path(unsafe_path, base)
        
        assert result is False


class TestErrorUtils:
    """Тесты для утилит обработки ошибок."""
    
    def test_safe_execute_success(self):
        """Тест безопасного выполнения успешной функции."""
        def func(x, y):
            return x + y
        
        result = ErrorUtils.safe_execute(func, default=0, log_error=False, x=2, y=3)
        
        assert result == 5
    
    def test_safe_execute_error(self):
        """Тест безопасного выполнения функции с ошибкой."""
        def func():
            raise ValueError("Test error")
        
        result = ErrorUtils.safe_execute(func, default="error", log_error=False)
        
        assert result == "error"
    
    @pytest.mark.asyncio
    async def test_safe_execute_async_success(self):
        """Тест безопасного выполнения успешной асинхронной функции."""
        async def async_func(x, y):
            await asyncio.sleep(0.01)  # Имитация асинхронной операции
            return x + y
        
        result = await ErrorUtils.safe_execute_async(async_func, default=0, log_error=False, x=2, y=3)
        
        assert result == 5
    
    @pytest.mark.asyncio
    async def test_safe_execute_async_error(self):
        """Тест безопасного выполнения асинхронной функции с ошибкой."""
        async def async_func():
            raise ValueError("Test async error")
        
        result = await ErrorUtils.safe_execute_async(async_func, default="error", log_error=False)
        
        assert result == "error"
    
    def test_retry_with_backoff_success(self):
        """Тест повторных попыток с успешным результатом."""
        call_count = 0
        
        def func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Temporary error")
            return "success"
        
        result = ErrorUtils.retry_with_backoff(func, max_retries=3, base_delay=0.01)
        
        assert result == "success"
        assert call_count == 2
    
    def test_retry_with_backoff_failure(self):
        """Тест повторных попыток с неудачным результатом."""
        def func():
            raise ValueError("Permanent error")
        
        with pytest.raises(ValueError, match="Permanent error"):
            ErrorUtils.retry_with_backoff(func, max_retries=2, base_delay=0.01)
    
    @pytest.mark.asyncio
    async def test_retry_with_backoff_async_success(self):
        """Тест асинхронных повторных попыток с успешным результатом."""
        call_count = 0
        
        async def async_func():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            if call_count < 2:
                raise ValueError("Temporary async error")
            return "async success"
        
        result = await ErrorUtils.retry_with_backoff_async(
            async_func, max_retries=3, base_delay=0.01
        )
        
        assert result == "async success"
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_retry_with_backoff_async_failure(self):
        """Тест асинхронных повторных попыток с неудачным результатом."""
        async def async_func():
            raise ValueError("Permanent async error")
        
        with pytest.raises(ValueError, match="Permanent async error"):
            await ErrorUtils.retry_with_backoff_async(
                async_func, max_retries=2, base_delay=0.01
            )


class TestHashUtils:
    """Тесты для утилит хеширования."""
    
    def test_generate_file_hash(self):
        """Тест генерации хеша файла."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content for hashing")
            temp_path = Path(f.name)
        
        try:
            result = HashUtils.generate_file_hash(temp_path, "md5")
            
            assert isinstance(result, str)
            assert len(result) == 32  # MD5 хеш имеет длину 32 символа
        finally:
            temp_path.unlink()
    
    def test_generate_file_hash_invalid_algorithm(self):
        """Тест генерации хеша файла с неверным алгоритмом."""
        with tempfile.NamedTemporaryFile() as f:
            temp_path = Path(f.name)
        
        with pytest.raises(ValueError, match="Неподдерживаемый алгоритм"):
            HashUtils.generate_file_hash(temp_path, "invalid_algorithm")
    
    def test_generate_text_hash(self):
        """Тест генерации хеша текста."""
        text = "test content for hashing"
        result = HashUtils.generate_text_hash(text, "md5")
        
        assert isinstance(result, str)
        assert len(result) == 32  # MD5 хеш имеет длину 32 символа
    
    def test_generate_text_hash_invalid_algorithm(self):
        """Тест генерации хеша текста с неверным алгоритмом."""
        with pytest.raises(ValueError, match="Неподдерживаемый алгоритм"):
            HashUtils.generate_text_hash("test", "invalid_algorithm")


class TestProgressTracker:
    """Тесты для трекера прогресса."""
    
    def test_initialization(self):
        """Тест инициализации трекера."""
        tracker = ProgressTracker(100, "Test operation")
        
        assert tracker.total_items == 100
        assert tracker.processed_items == 0
        assert tracker.description == "Test operation"
        assert tracker.start_time > 0
    
    def test_update_progress(self):
        """Тест обновления прогресса."""
        tracker = ProgressTracker(10)
        
        tracker.update(5)
        
        assert tracker.processed_items == 5
        assert tracker.get_progress_percentage() == 50.0
    
    def test_get_progress_percentage(self):
        """Тест получения процента выполнения."""
        tracker = ProgressTracker(200)
        
        tracker.update(50)
        
        assert tracker.get_progress_percentage() == 25.0
    
    def test_get_progress_percentage_zero_total(self):
        """Тест получения процента выполнения с нулевым общим количеством."""
        tracker = ProgressTracker(0)
        
        percentage = tracker.get_progress_percentage()
        
        assert percentage == 100.0
    
    def test_get_elapsed_time(self):
        """Тест получения затраченного времени."""
        tracker = ProgressTracker(10)
        
        time.sleep(0.1)
        elapsed = tracker.get_elapsed_time()
        
        assert elapsed >= 0.1
    
    def test_get_estimated_remaining_time(self):
        """Тест оценки оставшегося времени."""
        tracker = ProgressTracker(10)
        
        # Обрабатываем половину элементов
        tracker.update(5)
        time.sleep(0.1)
        
        remaining = tracker.get_estimated_remaining_time()
        
        assert remaining is not None
        assert remaining > 0
    
    def test_get_estimated_remaining_time_no_progress(self):
        """Тест оценки оставшегося времени без прогресса."""
        tracker = ProgressTracker(10)
        
        remaining = tracker.get_estimated_remaining_time()
        
        assert remaining is None
    
    @patch('src.utils.logger')
    def test_log_progress(self, mock_logger):
        """Тест логирования прогресса."""
        tracker = ProgressTracker(10, "Test")
        
        # Устанавливаем время последнего лога в прошлое для принудительного логирования
        tracker.last_log_time = 0
        tracker.update(5, "test item")
        
        # Проверяем, что logger.info был вызван
        mock_logger.info.assert_called()