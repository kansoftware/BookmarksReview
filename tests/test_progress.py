"""
Тесты для модуля progress.py
Проверяют функционал сохранения и восстановления прогресса обработки закладок.
"""
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from src.progress import (
    ProgressManager, ProcessedBookmark, FailedBookmark, 
    CurrentPosition, ProgressStatistics, calculate_config_hash
)
from src.models import Bookmark


class TestProgressManager:
    """Тесты для класса ProgressManager."""
    
    @pytest.fixture
    def temp_dir(self):
        """Создает временную директорию для тестов."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def sample_config(self):
        """Создает пример конфигурации."""
        config = Mock()
        config.llm_model = "gpt-4o-mini"
        config.llm_max_tokens = 1000
        config.llm_temperature = 0.7
        config.output_dir = "./test_output"
        config.markdown_include_metadata = True
        config.generate_mermaid_diagram = True
        return config
    
    @pytest.fixture
    def progress_manager(self, temp_dir, sample_config):
        """Создает экземпляр ProgressManager для тестов."""
        config_hash = calculate_config_hash(sample_config)
        return ProgressManager(
            output_dir=str(temp_dir),
            bookmarks_file="test_bookmarks.json",
            config_hash=config_hash
        )
    
    @pytest.fixture
    def sample_bookmark(self):
        """Создает пример закладки."""
        return Bookmark(
            title="Test Bookmark",
            url="https://example.com",
            date_added=datetime.now()
        )
    
    def test_init_progress_manager(self, temp_dir, sample_config):
        """Тест инициализации ProgressManager."""
        config_hash = calculate_config_hash(sample_config)
        manager = ProgressManager(
            output_dir=str(temp_dir),
            bookmarks_file="test_bookmarks.json",
            config_hash=config_hash
        )
        
        assert manager.output_dir == temp_dir
        assert manager.bookmarks_file == "test_bookmarks.json"
        assert manager.config_hash == config_hash
        assert manager.progress_file == temp_dir / "progress.json"
        assert manager.save_interval == 10
        assert len(manager.processed_bookmarks) == 0
        assert len(manager.failed_bookmarks) == 0
    
    def test_save_and_load_progress(self, progress_manager, sample_bookmark, temp_dir):
        """Тест сохранения и загрузки прогресса."""
        # Добавляем обработанную закладку
        folder_path = ["Root", "Subfolder"]
        progress_manager.add_processed_bookmark(
            sample_bookmark, 
            "test_file.md", 
            folder_path
        )
        
        # Добавляем неудачную закладку
        progress_manager.add_failed_bookmark(
            sample_bookmark, 
            "Test error", 
            folder_path
        )
        
        # Обновляем позицию
        progress_manager.update_current_position(folder_path, 5, 10)
        
        # Инициализируем статистику
        progress_manager.initialize_statistics(20)
        
        # Принудительно сохраняем
        result = progress_manager.force_save()
        assert result is True
        
        # Проверяем существование файла
        assert progress_manager.progress_file.exists()
        
        # Создаем новый менеджер и загружаем прогресс
        config_hash = progress_manager.config_hash
        new_manager = ProgressManager(
            output_dir=str(temp_dir),
            bookmarks_file="test_bookmarks.json",
            config_hash=config_hash
        )
        
        # Загружаем прогресс
        result = new_manager.load_progress()
        assert result is True
        
        # Проверяем загруженные данные
        assert len(new_manager.processed_bookmarks) == 1
        assert len(new_manager.failed_bookmarks) == 1
        assert new_manager.processed_bookmarks[0].url == sample_bookmark.url
        assert new_manager.failed_bookmarks[0].url == sample_bookmark.url
        assert new_manager.current_position is not None
        assert new_manager.current_position.folder_path == folder_path
        assert new_manager.current_position.bookmark_index == 5
        assert new_manager.statistics is not None
        assert new_manager.statistics.total_bookmarks == 20
    
    def test_load_progress_incompatible_config(self, progress_manager, temp_dir):
        """Тест загрузки прогресса с несовместимой конфигурацией."""
        # Создаем файл прогресса с другим хешем
        progress_data = {
            "version": "1.0",
            "timestamp": datetime.now().isoformat(),
            "bookmarks_file": "test_bookmarks.json",
            "config_hash": "different_hash",
            "processed_urls": [],
            "failed_urls": []
        }
        
        with open(progress_manager.progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f)
        
        # Пытаемся загрузить прогресс
        result = progress_manager.load_progress()
        assert result is False
    
    def test_get_processed_urls(self, progress_manager, sample_bookmark):
        """Тест получения множества обработанных URL."""
        # Добавляем обработанные закладки
        progress_manager.add_processed_bookmark(
            sample_bookmark, 
            "test_file.md", 
            ["Root"]
        )
        
        # Создаем вторую закладку
        bookmark2 = Bookmark(
            title="Test Bookmark 2",
            url="https://example2.com",
            date_added=datetime.now()
        )
        progress_manager.add_processed_bookmark(
            bookmark2, 
            "test_file2.md", 
            ["Root"]
        )
        
        # Получаем множество URL
        urls = progress_manager.get_processed_urls()
        assert len(urls) == 2
        assert sample_bookmark.url in urls
        assert bookmark2.url in urls
    
    def test_get_failed_urls(self, progress_manager, sample_bookmark):
        """Тест получения множества URL с ошибками."""
        # Добавляем неудачные закладки
        progress_manager.add_failed_bookmark(
            sample_bookmark, 
            "Error 1", 
            ["Root"]
        )
        
        # Создаем вторую закладку
        bookmark2 = Bookmark(
            title="Test Bookmark 2",
            url="https://example2.com",
            date_added=datetime.now()
        )
        progress_manager.add_failed_bookmark(
            bookmark2, 
            "Error 2", 
            ["Root"]
        )
        
        # Получаем множество URL
        urls = progress_manager.get_failed_urls()
        assert len(urls) == 2
        assert sample_bookmark.url in urls
        assert bookmark2.url in urls
    
    def test_get_resume_position(self, progress_manager):
        """Тест получения позиции для возобновления."""
        # Устанавливаем текущую позицию
        folder_path = ["Root", "Subfolder"]
        progress_manager.update_current_position(folder_path, 5, 10)
        
        # Получаем позицию для возобновления
        position = progress_manager.get_resume_position()
        assert position is not None
        assert position[0] == folder_path
        assert position[1] == 5
    
    def test_clear_progress(self, progress_manager, sample_bookmark, temp_dir):
        """Тест очистки прогресса."""
        # Добавляем данные
        progress_manager.add_processed_bookmark(
            sample_bookmark, 
            "test_file.md", 
            ["Root"]
        )
        
        # Сохраняем
        progress_manager.force_save()
        assert progress_manager.progress_file.exists()
        
        # Очищаем
        result = progress_manager.clear_progress()
        assert result is True
        assert not progress_manager.progress_file.exists()
        assert len(progress_manager.processed_bookmarks) == 0
        assert len(progress_manager.failed_bookmarks) == 0
    
    def test_periodic_save(self, progress_manager, sample_bookmark):
        """Тест периодического сохранения прогресса."""
        # Устанавливаем интервал сохранения
        progress_manager.save_interval = 1
        
        # Добавляем закладку (должно сохраниться)
        progress_manager.add_processed_bookmark(
            sample_bookmark,
            "test_file.md",
            ["Root"]
        )
        
        # Файл должен создаться
        assert progress_manager.progress_file.exists()
        
        # Добавляем еще одну закладку (должно сохраниться)
        bookmark2 = Bookmark(
            title="Test Bookmark 2",
            url="https://example2.com",
            date_added=datetime.now()
        )
        progress_manager.add_processed_bookmark(
            bookmark2,
            "test_file2.md",
            ["Root"]
        )
        
        # Проверяем, что файл существует и содержит данные
        assert progress_manager.progress_file.exists()
        
        with open(progress_manager.progress_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert len(data['processed_urls']) == 2


class TestCalculateConfigHash:
    """Тесты для функции calculate_config_hash."""
    
    def test_calculate_config_hash(self):
        """Тест вычисления хеша конфигурации."""
        config = Mock()
        config.llm_model = "gpt-4o-mini"
        config.llm_max_tokens = 1000
        config.llm_temperature = 0.7
        config.output_dir = "./test_output"
        config.markdown_include_metadata = True
        config.generate_mermaid_diagram = True
        
        hash1 = calculate_config_hash(config)
        
        # Изменяем один параметр
        config.llm_temperature = 0.8
        hash2 = calculate_config_hash(config)
        
        # Хеши должны быть разными
        assert hash1 != hash2
        
        # Возвращаем исходное значение
        config.llm_temperature = 0.7
        hash3 = calculate_config_hash(config)
        
        # Хеши должны быть одинаковыми
        assert hash1 == hash3


class TestProcessedBookmark:
    """Тесты для класса ProcessedBookmark."""
    
    def test_processed_bookmark_creation(self):
        """Тест создания ProcessedBookmark."""
        bookmark = ProcessedBookmark(
            url="https://example.com",
            title="Test Bookmark",
            processed_at="2025-10-26T12:00:00",
            file_path="test.md",
            folder_path=["Root", "Subfolder"]
        )
        
        assert bookmark.url == "https://example.com"
        assert bookmark.title == "Test Bookmark"
        assert bookmark.processed_at == "2025-10-26T12:00:00"
        assert bookmark.file_path == "test.md"
        assert bookmark.folder_path == ["Root", "Subfolder"]


class TestFailedBookmark:
    """Тесты для класса FailedBookmark."""
    
    def test_failed_bookmark_creation(self):
        """Тест создания FailedBookmark."""
        bookmark = FailedBookmark(
            url="https://example.com",
            title="Test Bookmark",
            failed_at="2025-10-26T12:00:00",
            error="Connection timeout",
            folder_path=["Root", "Subfolder"]
        )
        
        assert bookmark.url == "https://example.com"
        assert bookmark.title == "Test Bookmark"
        assert bookmark.failed_at == "2025-10-26T12:00:00"
        assert bookmark.error == "Connection timeout"
        assert bookmark.folder_path == ["Root", "Subfolder"]


class TestCurrentPosition:
    """Тесты для класса CurrentPosition."""
    
    def test_current_position_creation(self):
        """Тест создания CurrentPosition."""
        position = CurrentPosition(
            folder_path=["Root", "Subfolder"],
            bookmark_index=5,
            total_in_folder=10
        )
        
        assert position.folder_path == ["Root", "Subfolder"]
        assert position.bookmark_index == 5
        assert position.total_in_folder == 10


class TestProgressStatistics:
    """Тесты для класса ProgressStatistics."""
    
    def test_progress_statistics_creation(self):
        """Тест создания ProgressStatistics."""
        stats = ProgressStatistics(
            total_bookmarks=100,
            processed_count=50,
            failed_count=5,
            skipped_count=0,
            start_time="2025-10-26T10:00:00",
            last_update="2025-10-26T12:00:00"
        )
        
        assert stats.total_bookmarks == 100
        assert stats.processed_count == 50
        assert stats.failed_count == 5
        assert stats.skipped_count == 0
        assert stats.start_time == "2025-10-26T10:00:00"
        assert stats.last_update == "2025-10-26T12:00:00"