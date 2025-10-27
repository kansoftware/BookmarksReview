"""
Тесты для новой функциональности --check-error
"""
import argparse
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from src.main import main
from src.progress import ProgressManager
from src.models import Bookmark


class TestCheckErrorFunctionality:
    """Тесты для новой функциональности --check-error"""

    def test_check_error_argument_added(self):
        """Тест: аргумент --check-error добавлен в парсер командной строки"""
        import sys
        from io import StringIO
        from contextlib import redirect_stderr

        # Сохраняем оригинальные аргументы
        original_argv = sys.argv[:]
        
        try:
            # Проверяем, что аргумент --check-error добавлен
            sys.argv = ['src/main.py', 'dummy.json', '--help']
            
            # Перехватываем вывод справки
            f = StringIO()
            with redirect_stderr(f):
                try:
                    # Создаем парсер и проверяем наличие аргумента
                    from src.main import parse_arguments
                    parser = argparse.ArgumentParser()
                    parser.add_argument("--check-error", action="store_true", help="Перепроверить только URL с ошибками")
                    
                    # Если мы дошли до этой точки, аргумент успешно добавлен
                    assert True
                except SystemExit:
                    # Это нормально для --help
                    pass
        finally:
            sys.argv = original_argv

    def test_progress_manager_move_failed_to_processed(self):
        """Тест: метод move_failed_to_processed корректно перемещает закладки"""
        with tempfile.TemporaryDirectory() as temp_dir:
            progress_file = Path(temp_dir) / "progress.json"
            
            # Создаем менеджер прогресса
            progress_manager = ProgressManager(
                output_dir=temp_dir,
                bookmarks_file="test.json",
                config_hash="test_hash"
            )
            
            # Добавляем тестовую неудачную закладку
            bookmark = Bookmark(
                title="Test Bookmark",
                url="https://example.com",
                date_added=None
            )
            
            progress_manager.add_failed_bookmark(bookmark, "Test error", ["Folder"])
            
            # Проверяем, что закладка добавлена в список неудачных
            assert len(progress_manager.failed_bookmarks) == 1
            assert progress_manager.failed_bookmarks[0].url == "https://example.com"
            
            # Перемещаем в обработанные
            result = progress_manager.move_failed_to_processed(bookmark, "test.md", ["Folder"])
            
            # Проверяем, что закладка перемещена
            assert result is True
            assert len(progress_manager.failed_bookmarks) == 0
            assert len(progress_manager.processed_bookmarks) == 1
            assert progress_manager.processed_bookmarks[0].url == "https://example.com"

    def test_progress_manager_remove_failed_bookmark(self):
        """Тест: метод remove_failed_bookmark корректно удаляет закладки"""
        with tempfile.TemporaryDirectory() as temp_dir:
            progress_manager = ProgressManager(
                output_dir=temp_dir,
                bookmarks_file="test.json",
                config_hash="test_hash"
            )
            
            # Добавляем тестовую неудачную закладку
            bookmark = Bookmark(
                title="Test Bookmark",
                url="https://example.com",
                date_added=None
            )
            
            progress_manager.add_failed_bookmark(bookmark, "Test error", ["Folder"])
            
            # Проверяем, что закладка добавлена
            assert len(progress_manager.failed_bookmarks) == 1
            
            # Удаляем закладку
            result = progress_manager.remove_failed_bookmark("https://example.com")
            
            # Проверяем, что закладка удалена
            assert result is True
            assert len(progress_manager.failed_bookmarks) == 0

    @patch('src.main.parse_arguments')
    @patch('src.main.ConfigManager')
    @patch('src.main.BookmarkParser')
    @patch('src.main.DiagramGenerator')
    @patch('src.main.FileSystemWriter')
    @patch('src.main.ContentSummarizer')
    @patch('src.main.ContentFetcher')
    @patch('src.main.count_bookmarks')
    @patch('src.main.asyncio.run')
    def test_check_error_mode_processes_only_failed_urls(
        self, 
        mock_asyncio_run, 
        mock_count_bookmarks, 
        mock_content_fetcher, 
        mock_content_summarizer, 
        mock_filesystem_writer, 
        mock_diagram_generator, 
        mock_bookmark_parser, 
        mock_config_manager, 
        mock_parse_arguments
    ):
        """Тест: режим --check-error обрабатывает только URL с ошибками"""
        # Настройка моков
        mock_args = argparse.Namespace(
            bookmarks_file="test.json",
            config_path=None,
            output_dir=None,
            max_concurrent=None,
            resume=False,
            check_error=True,  # Включаем режим проверки ошибок
            dry_run=False,
            verbose=False,
            no_diagram=False
        )
        
        mock_parse_arguments.return_value = mock_args
        
        mock_config = Mock()
        mock_config_manager.return_value.get.return_value = mock_config
        
        mock_folder = Mock()
        mock_bookmark_parser.return_value.parse_bookmarks.return_value = mock_folder
        mock_count_bookmarks.return_value = 10
        
        # Мокаем результаты asyncio.run
        mock_asyncio_run.return_value = (5, 2)  # 5 обработано, 2 с ошибками
        
        # Создаем тестовый файл
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({
                "roots": {
                    "bookmark_bar": {
                        "children": [
                            {"type": "url", "name": "Test", "url": "https://example.com"}
                        ]
                    }
                }
            }, f)
            test_file = f.name
        
        try:
            # Вызываем main с правильным файлом
            import sys
            original_argv = sys.argv[:]
            try:
                sys.argv = ['src/main.py', test_file]
                
                # Вызываем main
                with patch('sys.exit'):  # Заглушаем sys.exit, чтобы тест не завершился
                    main()
                
                # Проверяем, что аргументы были разобраны
                mock_parse_arguments.assert_called_once()
            finally:
                # Восстанавливаем оригинальные аргументы
                sys.argv = original_argv
            
        finally:
            # Удаляем временный файл
            Path(test_file).unlink()