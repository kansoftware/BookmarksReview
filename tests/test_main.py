"""
Модуль test_main.py
Содержит unit-тесты для основного модуля приложения.
"""
import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from datetime import datetime

from src.main import (
    parse_arguments, setup_application_logging, create_progress_manager,
    process_single_bookmark, traverse_and_process_folder,
    process_bookmarks, count_bookmarks, main
)
from src.models import Bookmark, BookmarkFolder, ProcessedPage
from src.config import Config


class TestMainModule(unittest.TestCase):
    """Тесты для основного модуля приложения."""
    
    def setUp(self):
        """Подготовка тестового окружения."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        
        # Создаем тестовую конфигурацию
        self.test_config = Config(
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
            fetch_max_redirects=5,
            output_dir=str(self.temp_path / "output"),
            markdown_include_metadata=True,
            generate_mermaid_diagram=True,
            prompt_file=str(self.temp_path / "prompt.txt"),
            log_level="INFO",
            log_file=str(self.temp_path / "test.log")
        )
        
        # Создаем тестовые закладки
        self.test_bookmark = Bookmark(
            title="Test Bookmark",
            url="https://example.com",
            date_added=datetime.now()
        )
        
        self.test_folder = BookmarkFolder(
            name="Test Folder",
            children=[],
            bookmarks=[self.test_bookmark]
        )
    
    def tearDown(self):
        """Очистка тестового окружения."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_parse_arguments(self):
        """Тест парсинга аргументов командной строки."""
        # Тест с обязательным аргументом
        with patch('sys.argv', ['main.py', 'bookmarks.json']):
            args = parse_arguments()
            self.assertEqual(args.bookmarks_file, 'bookmarks.json')
            self.assertFalse(args.resume)
            self.assertFalse(args.dry_run)
            self.assertFalse(args.verbose)
            self.assertFalse(args.no_diagram)
        
        # Тест со всеми опциями
        with patch('sys.argv', [
            'main.py', 'bookmarks.json',
            '--config', 'custom.env',
            '--output-dir', './custom_output',
            '--resume',
            '--dry-run',
            '--verbose',
            '--no-diagram',
            '--max-concurrent', '5'
        ]):
            args = parse_arguments()
            self.assertEqual(args.bookmarks_file, 'bookmarks.json')
            self.assertEqual(args.config_path, 'custom.env')
            self.assertEqual(args.output_dir, './custom_output')
            self.assertTrue(args.resume)
            self.assertTrue(args.dry_run)
            self.assertTrue(args.verbose)
            self.assertTrue(args.no_diagram)
            self.assertEqual(args.max_concurrent, 5)
    
    @patch('src.main.setup_logging')
    def test_setup_application_logging(self, mock_setup_logging):
        """Тест настройки логирования приложения."""
        # Создаем mock объект для args
        mock_args = MagicMock()
        mock_args.verbose = False
        
        # Вызываем функцию
        setup_application_logging(mock_args, self.test_config)
        
        # Проверяем, что функция была вызвана с правильными параметрами
        mock_setup_logging.assert_called_once_with(self.test_config)
    
    def test_create_progress_manager(self):
        """Тест создания менеджера прогресса."""
        from src.progress import ProgressManager
        
        # Создаем mock объекты
        mock_args = MagicMock()
        mock_args.resume = False
        
        # Вызываем функцию
        progress_manager = create_progress_manager(mock_args, self.test_config, "test_bookmarks.json")
        
        # Проверяем результат
        self.assertIsNotNone(progress_manager)
        self.assertEqual(progress_manager.output_dir, Path(self.test_config.output_dir))
        self.assertEqual(progress_manager.bookmarks_file, "test_bookmarks.json")
    
    @unittest.skip("Требует асинхронного контекста")
    async def test_process_single_bookmark(self):
        """Тест обработки одной закладки."""
        # Создаем mock объекты
        mock_fetcher = AsyncMock()
        mock_summarizer = AsyncMock()
        
        # Настраиваем mock для успешной загрузки
        mock_fetcher.fetch_content.return_value = "<html><body>Test content</body></html>"
        mock_fetcher.extract_text.return_value = "Test content"
        mock_summarizer.generate_summary.return_value = "Test summary"
        
        processed_urls = set()
        failed_urls = set()
        
        # Создаем mock менеджер прогресса
        mock_progress_manager = MagicMock()
        mock_progress_manager.get_processed_urls.return_value = processed_urls
        mock_progress_manager.get_failed_urls.return_value = failed_urls
        mock_progress_manager.add_processed_bookmark = MagicMock()
        mock_progress_manager.add_failed_bookmark = MagicMock()
        
        # Создаем mock аргументов
        mock_args = MagicMock()
        mock_args.check_error = False
        
        # Вызываем функцию
        result = await process_single_bookmark(
            self.test_bookmark, mock_fetcher, mock_summarizer, mock_progress_manager, ["Test Folder"], mock_args
        )
        
        # Проверяем результат
        self.assertIsNotNone(result)
        self.assertIsInstance(result, ProcessedPage)
        self.assertEqual(result.url, self.test_bookmark.url)
        self.assertEqual(result.title, self.test_bookmark.title)
        self.assertEqual(result.summary, "Test summary")
        self.assertEqual(result.status, 'success')
        
        # Проверяем вызовы mock объектов
        mock_fetcher.fetch_content.assert_called_once_with(self.test_bookmark.url)
        mock_fetcher.extract_text.assert_called_once()
        mock_summarizer.generate_summary.assert_called_once()
        mock_progress_manager.add_processed_bookmark.assert_called_once()
    
    def test_count_bookmarks(self):
        """Тест подсчета закладок."""
        # Создаем сложную структуру папок
        child_folder = BookmarkFolder(
            name="Child Folder",
            children=[],
            bookmarks=[
                Bookmark("Child Bookmark 1", "https://child1.com", None),
                Bookmark("Child Bookmark 2", "https://child2.com", None)
            ]
        )
        
        root_folder = BookmarkFolder(
            name="Root Folder",
            children=[child_folder],
            bookmarks=[
                Bookmark("Root Bookmark 1", "https://root1.com", None),
                Bookmark("Root Bookmark 2", "https://root2.com", None)
            ]
        )
        
        # Вызываем функцию
        count = count_bookmarks(root_folder)
        
        # Проверяем результат
        self.assertEqual(count, 4)  # 2 в корне + 2 в дочерней папке
    
    @patch('src.main.ContentFetcher')
    @patch('src.main.ContentSummarizer')
    @patch('src.main.FileSystemWriter')
    @patch('src.main.DiagramGenerator')
    @patch('src.main.create_progress_manager')
    def test_process_bookmarks(self, mock_create_progress_manager, mock_diagram_gen, mock_writer_class,
                              mock_summarizer_class, mock_fetcher_class):
        """Тест основной функции обработки закладок."""
        # Создаем mock объекты
        mock_args = MagicMock()
        mock_args.resume = False
        mock_args.dry_run = False
        mock_args.no_diagram = False
        mock_args.check_error = False  # Добавляем это для правильной работы функции
        
        mock_fetcher = AsyncMock()
        mock_fetcher_class.return_value.__aenter__.return_value = mock_fetcher
        mock_fetcher.fetch_content.return_value = "<html>Test</html>"
        mock_fetcher.extract_text.return_value = "Test content"
        
        mock_summarizer = AsyncMock()
        mock_summarizer_class.return_value = mock_summarizer
        mock_summarizer.generate_summary.return_value = "Test summary"
        
        mock_writer = MagicMock()
        mock_writer_class.return_value = mock_writer
        mock_writer._sanitize_filename.return_value = "test"
        
        mock_diagram = MagicMock()
        mock_diagram_gen.return_value = mock_diagram
        mock_diagram.generate_structure_diagram.return_value = "diagram_code"
        
        mock_progress_manager = MagicMock()
        mock_create_progress_manager.return_value = mock_progress_manager
        mock_progress_manager.load_progress.return_value = False
        mock_progress_manager.get_processed_urls.return_value = set()  # Добавляем это
        mock_progress_manager.get_failed_urls.return_value = set()     # Добавляем это
        mock_progress_manager.initialize_statistics = MagicMock()
        mock_progress_manager.get_resume_position.return_value = None
        mock_progress_manager.update_statistics = MagicMock()
        mock_progress_manager.force_save = MagicMock()
        mock_progress_manager.add_processed_bookmark = MagicMock() # Добавляем это
        mock_progress_manager.add_failed_bookmark = MagicMock()     # Добавляем это
        
        # Вызываем функцию через asyncio.run
        processed, failed = asyncio.run(process_bookmarks(mock_args, self.test_config, self.test_folder, "test_bookmarks.json"))
        
        # Проверяем результат
        self.assertEqual(processed, 1)
        self.assertEqual(failed, 0)
        
        # Проверяем вызовы mock объектов
        mock_writer.create_folder_structure.assert_called_once()
        mock_diagram.generate_structure_diagram.assert_called_once()
        mock_diagram.save_diagram.assert_called_once()
        mock_progress_manager.initialize_statistics.assert_called_once()
        mock_progress_manager.force_save.assert_called_once()
    
    @patch('src.main.parse_arguments')
    @patch('src.main.ConfigManager')
    @patch('src.main.setup_application_logging')
    @patch('src.main.BookmarkParser')
    @patch('src.main.asyncio.run')
    @patch('pathlib.Path.exists')
    def test_main_function(self, mock_exists, mock_asyncio_run,
                          mock_parser_class, mock_setup_logging,
                          mock_config_manager, mock_parse_arguments):
        """Тест главной функции."""
        # Настраиваем mock объекты
        mock_args = MagicMock()
        mock_args.bookmarks_file = "test_bookmarks.json"
        mock_args.config_path = None
        mock_args.output_dir = None
        mock_args.max_concurrent = None
        mock_args.verbose = False
        mock_parse_arguments.return_value = mock_args
        
        mock_exists.return_value = True
        
        mock_config = MagicMock()
        mock_config.output_dir = str(self.temp_path / "output")
        mock_config.log_level = "INFO"
        mock_config_manager.return_value.get.return_value = mock_config
        
        mock_parser = MagicMock()
        mock_data = {"roots": {}}
        mock_parser.load_json.return_value = mock_data
        mock_parser.parse_bookmarks.return_value = self.test_folder
        mock_parser_class.return_value = mock_parser
        
        mock_asyncio_run.return_value = (1, 0)
        
        # Вызываем функцию
        main()
        
        # Проверяем вызовы
        mock_parse_arguments.assert_called_once()
        mock_config_manager.assert_called_once_with(None)
        mock_setup_logging.assert_called_once()
        mock_parser.load_json.assert_called_once_with("test_bookmarks.json")
        mock_parser.parse_bookmarks.assert_called_once_with(mock_data)
        mock_asyncio_run.assert_called_once()


class TestMainModuleAsync(unittest.IsolatedAsyncioTestCase):
    """Асинхронные тесты для основного модуля."""
    
    def setUp(self):
        """Подготовка тестового окружения."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        
        self.test_bookmark = Bookmark(
            title="Test Bookmark",
            url="https://example.com",
            date_added=datetime.now()
        )
    
    def tearDown(self):
        """Очистка тестового окружения."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    async def test_process_single_bookmark_success(self):
        """Тест успешной обработки одной закладки."""
        # Создаем mock объекты
        mock_fetcher = AsyncMock()
        mock_summarizer = AsyncMock()
        
        # Настраиваем mock для успешной загрузки
        mock_fetcher.fetch_content.return_value = "<html><body>Test content</body></html>"
        mock_fetcher.extract_text.return_value = "Test content"
        mock_summarizer.generate_summary.return_value = "Test summary"
        
        processed_urls = set()
        failed_urls = set()
        
        # Создаем mock менеджер прогресса
        mock_progress_manager = MagicMock()
        mock_progress_manager.get_processed_urls.return_value = processed_urls
        mock_progress_manager.get_failed_urls.return_value = failed_urls
        mock_progress_manager.add_processed_bookmark = MagicMock()
        mock_progress_manager.add_failed_bookmark = MagicMock()
        
        # Создаем mock аргументов
        mock_args = MagicMock()
        mock_args.check_error = False
        
        # Вызываем функцию
        result = await process_single_bookmark(
            self.test_bookmark, mock_fetcher, mock_summarizer, mock_progress_manager, ["Test Folder"], mock_args
        )
        
        # Проверяем результат
        self.assertIsNotNone(result)
        self.assertIsInstance(result, ProcessedPage)
        self.assertEqual(result.url, self.test_bookmark.url)
        self.assertEqual(result.title, self.test_bookmark.title)
        self.assertEqual(result.summary, "Test summary")
        self.assertEqual(result.status, 'success')
        
        # Проверяем вызовы mock объектов
        mock_fetcher.fetch_content.assert_called_once_with(self.test_bookmark.url)
        mock_fetcher.extract_text.assert_called_once()
        mock_summarizer.generate_summary.assert_called_once()
        # В process_single_bookmark не вызывается add_processed_bookmark
        # Это происходит в traverse_and_process_folder
        mock_progress_manager.add_processed_bookmark.assert_not_called()
    
    async def test_process_single_bookmark_failure(self):
        """Тест обработки закладки с ошибкой."""
        # Создаем mock объекты
        mock_fetcher = AsyncMock()
        mock_summarizer = AsyncMock()
        
        # Настраиваем mock для ошибки загрузки
        mock_fetcher.fetch_content.return_value = None
        
        processed_urls = set()
        failed_urls = set()
        
        # Создаем mock менеджер прогресса
        mock_progress_manager = MagicMock()
        mock_progress_manager.get_processed_urls.return_value = processed_urls
        mock_progress_manager.get_failed_urls.return_value = failed_urls
        mock_progress_manager.add_processed_bookmark = MagicMock()
        mock_progress_manager.add_failed_bookmark = MagicMock()
        
        # Создаем mock аргументов
        mock_args = MagicMock()
        mock_args.check_error = False
        
        # Вызываем функцию
        result = await process_single_bookmark(
            self.test_bookmark, mock_fetcher, mock_summarizer, mock_progress_manager, ["Test Folder"], mock_args
        )
        
        # Проверяем результат
        self.assertIsNone(result)
        mock_progress_manager.add_failed_bookmark.assert_called_once()
    
    async def test_process_single_bookmark_skip_processed(self):
        """Тест пропуска уже обработанной закладки."""
        # Создаем mock объекты
        mock_fetcher = AsyncMock()
        mock_summarizer = AsyncMock()
        
        processed_urls = {self.test_bookmark.url}
        failed_urls = set()
        
        # Создаем mock менеджер прогресса
        mock_progress_manager = MagicMock()
        mock_progress_manager.get_processed_urls.return_value = processed_urls
        mock_progress_manager.get_failed_urls.return_value = failed_urls
        mock_progress_manager.add_processed_bookmark = MagicMock()
        mock_progress_manager.add_failed_bookmark = MagicMock()
        
        # Создаем mock аргументов
        mock_args = MagicMock()
        mock_args.check_error = False
        
        # Вызываем функцию
        result = await process_single_bookmark(
            self.test_bookmark, mock_fetcher, mock_summarizer, mock_progress_manager, ["Test Folder"], mock_args
        )
        
        # Проверяем результат
        self.assertIsNone(result)
        # Проверяем, что fetch_content не вызывался
        mock_fetcher.fetch_content.assert_not_called()


if __name__ == '__main__':
    unittest.main()