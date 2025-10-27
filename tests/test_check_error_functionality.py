"""
Тесты для проверки функциональности --check-error с обработкой URL с полем error в processed_urls
"""
import json
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

import pytest

from src.progress import ProgressManager, ProcessedBookmark, FailedBookmark, CurrentPosition
from src.models import Bookmark


class TestCheckErrorFunctionality:
    """Тесты для расширенной функциональности --check-error"""

    def test_get_failed_urls_with_error_from_processed(self, tmp_path):
        """Тест получения всех URL с ошибками (из failed_urls и processed_urls с полем error)"""
        progress_file = tmp_path / "progress.json"
        progress_manager = ProgressManager(
            output_dir=str(tmp_path),
            bookmarks_file="test_bookmarks.json",
            config_hash="test_hash",
            progress_file_path=str(progress_file)
        )

        # Добавляем закладки в processed с ошибками и без
        processed_with_error = ProcessedBookmark(
            url="http://example-with-error.com",
            title="Example with error",
            processed_at=datetime.now().isoformat(),
            error="Some error occurred",
            folder_path=["test"]
        )
        
        processed_success = ProcessedBookmark(
            url="http://example-success.com",
            title="Example success",
            processed_at=datetime.now().isoformat(),
            file_path="test.md",
            folder_path=["test"]
        )
        
        failed_bookmark = FailedBookmark(
            url="http://failed-example.com",
            title="Failed example",
            failed_at=datetime.now().isoformat(),
            error="Failed to load",
            folder_path=["test"]
        )

        progress_manager.processed_bookmarks = [processed_with_error, processed_success]
        progress_manager.failed_bookmarks = [failed_bookmark]

        # Проверяем, что get_failed_urls без параметра возвращает только из failed_bookmarks
        failed_only = progress_manager.get_failed_urls()
        assert failed_only == {"http://failed-example.com"}

        # Проверяем, что get_failed_urls с параметром возвращает из обоих списков
        all_errors = progress_manager.get_failed_urls(include_error_from_processed=True)
        assert all_errors == {"http://failed-example.com", "http://example-with-error.com"}

    def test_move_failed_to_processed_moves_from_processed_with_error(self, tmp_path):
        """Тест перемещения закладки из processed с ошибкой в processed без ошибки"""
        progress_file = tmp_path / "progress.json"
        progress_manager = ProgressManager(
            output_dir=str(tmp_path),
            bookmarks_file="test_bookmarks.json",
            config_hash="test_hash",
            progress_file_path=str(progress_file)
        )

        # Добавляем закладку в processed с ошибкой
        bookmark_with_error = ProcessedBookmark(
            url="http://example.com",
            title="Example with error",
            processed_at=datetime.now().isoformat(),
            error="Some error occurred",
            folder_path=["test"]
        )
        progress_manager.processed_bookmarks = [bookmark_with_error]

        bookmark = Bookmark(url="http://example.com", title="Example with error", date_added=datetime.now())

        # Перемещаем из processed с ошибкой в processed без ошибки
        result = progress_manager.move_failed_to_processed(
            bookmark=bookmark,
            file_path="example.md",
            folder_path=["test"]
        )

        assert result is True

        # Проверяем, что закладка теперь в списке processed без ошибки
        processed_urls = progress_manager.get_processed_urls()
        assert "http://example.com" in processed_urls

        # Находим обновленную закладку и проверяем, что у нее нет ошибки
        updated_bookmark = None
        for item in progress_manager.processed_bookmarks:
            if item.url == "http://example.com":
                updated_bookmark = item
                break

        assert updated_bookmark is not None
        assert updated_bookmark.error is None
        assert updated_bookmark.file_path == "example.md"

    def test_get_processed_urls_exclude_with_error(self, tmp_path):
        """Тест получения обработанных URL с исключением тех, у кого есть ошибка"""
        progress_file = tmp_path / "progress.json"
        progress_manager = ProgressManager(
            output_dir=str(tmp_path),
            bookmarks_file="test_bookmarks.json",
            config_hash="test_hash",
            progress_file_path=str(progress_file)
        )

        # Добавляем закладки с ошибками и без
        processed_with_error = ProcessedBookmark(
            url="http://with-error.com",
            title="With error",
            processed_at=datetime.now().isoformat(),
            error="Some error",
            folder_path=["test"]
        )
        
        processed_success = ProcessedBookmark(
            url="http://success.com",
            title="Success",
            processed_at=datetime.now().isoformat(),
            file_path="success.md",
            folder_path=["test"]
        )

        progress_manager.processed_bookmarks = [processed_with_error, processed_success]

        # Проверяем, что по умолчанию возвращаются только URL без ошибок
        processed_urls = progress_manager.get_processed_urls()
        assert processed_urls == {"http://success.com"}

        # Проверяем, что с параметром возвращаются все URL
        all_processed_urls = progress_manager.get_processed_urls(exclude_with_error=False)
        assert all_processed_urls == {"http://with-error.com", "http://success.com"}

    def test_check_error_logic_with_processed_urls_having_error(self, tmp_path):
        """Тест логики check_error с URL из processed_urls, у которых есть поле error"""
        progress_file = tmp_path / "progress.json"
        
        # Создаем JSON файл с прогрессом, содержащий processed_urls с полем error
        progress_data = {
            "version": "1.0",
            "timestamp": datetime.now().isoformat(),
            "bookmarks_file": "test_bookmarks.json",
            "config_hash": "test_hash",
            "processed_urls": [
                {
                    "url": "http://processed-with-error.com",
                    "title": "Processed with error",
                    "processed_at": datetime.now().isoformat(),
                    "file_path": "test.md",
                    "folder_path": ["test"],
                    "error": "Some processing error"
                },
                {
                    "url": "http://processed-success.com",
                    "title": "Processed success",
                    "processed_at": datetime.now().isoformat(),
                    "file_path": "test2.md",
                    "folder_path": ["test"]
                }
            ],
            "failed_urls": [
                {
                    "url": "http://failed.com",
                    "title": "Failed",
                    "failed_at": datetime.now().isoformat(),
                    "error": "Failed to load",
                    "folder_path": ["test"]
                }
            ],
            "current_position": {
                "folder_path": ["test"],
                "bookmark_index": 0,
                "total_in_folder": 1
            },
            "statistics": {
                "total_bookmarks": 3,
                "processed_count": 2,
                "failed_count": 1,
                "skipped_count": 0,
                "start_time": datetime.now().isoformat(),
                "last_update": datetime.now().isoformat()
            }
        }

        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, indent=2, ensure_ascii=False)

        progress_manager = ProgressManager(
            output_dir=str(tmp_path),
            bookmarks_file="test_bookmarks.json",
            config_hash="test_hash",
            progress_file_path=str(progress_file)
        )

        # Загружаем прогресс
        progress_manager.load_progress()

        # Проверяем, что get_failed_urls без параметра возвращает только failed_urls
        failed_only = progress_manager.get_failed_urls()
        assert failed_only == {"http://failed.com"}

        # Проверяем, что get_failed_urls с параметром возвращает все ошибки
        all_errors = progress_manager.get_failed_urls(include_error_from_processed=True)
        assert all_errors == {"http://failed.com", "http://processed-with-error.com"}

        # Проверяем, что get_processed_urls возвращает только успешно обработанные
        processed_only = progress_manager.get_processed_urls()
        assert processed_only == {"http://processed-success.com"}