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
    parse_arguments, setup_application_logging, load_progress_data,
    save_progress_data, process_single_bookmark, traverse_and_process_folder,
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
        mock_setup_logging.assert_called_once_with("INFO")
    
    def test_load_progress_data(self):
        """Тест загрузки данных о прогрессе."""
        # Создаем тестовый файл прогресса
        progress_file = self.temp_path / "progress.json"
        test_progress = {
            'timestamp': '2023-01-01T00:00:00',
            'processed_urls': ['https://example.com'],
            'failed_urls': ['https://failed.com']
        }
        
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(test_progress, f)
        
        # Вызываем функцию
        result = load_progress_data(self.temp_path)
        
        # Проверяем результат
        self.assertEqual(result, test_progress)
        
        # Тест с отсутствующим файлом
        empty_result = load_progress_data(Path("/nonexistent/path"))
        self.assertEqual(empty_result, {})
    
    def test_save_progress_data(self):
        """Тест сохранения данных о прогрессе."""
        processed_urls = ['https://example.com']
        failed_urls = ['https://failed.com']
        
        # Вызываем функцию
        save_progress_data(self.temp_path, processed_urls, failed_urls)
        
        # Проверяем результат
        progress_file = self.temp_path / "progress.json"
        self.assertTrue(progress_file.exists())
        
        with open(progress_file, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        
        self.assertEqual(saved_data['processed_urls'], processed_urls)
        self.assertEqual(saved_data['failed_urls'], failed_urls)
        self.assertIn('timestamp', saved_data)
    
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
        
        # Вызываем функцию
        result = await process_single_bookmark(
            self.test_bookmark, mock_fetcher, mock_summarizer, processed_urls, failed_urls
        )
        
        # Проверяем результат
        self.assertIsNotNone(result)
        self.assertIsInstance(result, ProcessedPage)
        self.assertEqual(result.url, self.test_bookmark.url)
        self.assertEqual(result.title, self.test_bookmark.title)
        self.assertEqual(result.summary, "Test summary")
        self.assertEqual(result.status, 'success')
        self.assertIn(self.test_bookmark.url, processed_urls)
        self.assertNotIn(self.test_bookmark.url, failed_urls)
        
        # Проверяем вызовы mock объектов
        mock_fetcher.fetch_content.assert_called_once_with(self.test_bookmark.url)
        mock_fetcher.extract_text.assert_called_once_with("<html><body>Test content</body></html>")
        mock_summarizer.generate_summary.assert_called_once_with("Test content", self.test_bookmark.title)
    
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
    @patch('src.main.load_progress_data')
    @patch('src.main.save_progress_data')
    def test_process_bookmarks(self, mock_save_progress, mock_load_progress,
                              mock_diagram_gen, mock_writer_class,
                              mock_summarizer_class, mock_fetcher_class):
        """Тест основной функции обработки закладок."""
        # Создаем mock объекты
        mock_args = MagicMock()
        mock_args.resume = False
        mock_args.dry_run = False
        mock_args.no_diagram = False
        
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
        
        mock_load_progress.return_value = {}
        
        # Вызываем функцию через asyncio.run
        processed, failed = asyncio.run(process_bookmarks(mock_args, self.test_config, self.test_folder))
        
        # Проверяем результат
        self.assertEqual(processed, 1)
        self.assertEqual(failed, 0)
        
        # Проверяем вызовы mock объектов
        mock_writer.create_folder_structure.assert_called_once()
        mock_diagram.generate_structure_diagram.assert_called_once()
        mock_diagram.save_diagram.assert_called_once()
        mock_save_progress.assert_called_once()
    
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
        
        # Вызываем функцию
        result = await process_single_bookmark(
            self.test_bookmark, mock_fetcher, mock_summarizer, processed_urls, failed_urls
        )
        
        # Проверяем результат
        self.assertIsNotNone(result)
        self.assertIsInstance(result, ProcessedPage)
        self.assertEqual(result.url, self.test_bookmark.url)
        self.assertEqual(result.title, self.test_bookmark.title)
        self.assertEqual(result.summary, "Test summary")
        self.assertEqual(result.status, 'success')
        self.assertIn(self.test_bookmark.url, processed_urls)
        self.assertNotIn(self.test_bookmark.url, failed_urls)
    
    async def test_process_single_bookmark_failure(self):
        """Тест обработки закладки с ошибкой."""
        # Создаем mock объекты
        mock_fetcher = AsyncMock()
        mock_summarizer = AsyncMock()
        
        # Настраиваем mock для ошибки загрузки
        mock_fetcher.fetch_content.return_value = None
        
        processed_urls = set()
        failed_urls = set()
        
        # Вызываем функцию
        result = await process_single_bookmark(
            self.test_bookmark, mock_fetcher, mock_summarizer, processed_urls, failed_urls
        )
        
        # Проверяем результат
        self.assertIsNone(result)
        self.assertNotIn(self.test_bookmark.url, processed_urls)
        self.assertIn(self.test_bookmark.url, failed_urls)
    
    async def test_process_single_bookmark_skip_processed(self):
        """Тест пропуска уже обработанной закладки."""
        # Создаем mock объекты
        mock_fetcher = AsyncMock()
        mock_summarizer = AsyncMock()
        
        processed_urls = {self.test_bookmark.url}
        failed_urls = set()
        
        # Вызываем функцию
        result = await process_single_bookmark(
            self.test_bookmark, mock_fetcher, mock_summarizer, processed_urls, failed_urls
        )
        
        # Проверяем результат
        self.assertIsNone(result)
        # Проверяем, что fetch_content не вызывался
        mock_fetcher.fetch_content.assert_not_called()


if __name__ == '__main__':
    unittest.main()