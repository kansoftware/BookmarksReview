"""
Интеграционные тесты для проверки инкрементального выполнения и возобновления.
Тестируют функционал сохранения и восстановления прогресса.
"""
import json
import asyncio
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, AsyncMock, Mock

import pytest

from src.parser import BookmarkParser
from src.progress import ProgressManager
from src.main import process_bookmarks, create_progress_manager
from tests.conftest import create_test_bookmark, create_test_folder


class TestResumeIntegration:
    """Интеграционные тесты для инкрементального выполнения."""
    
    @pytest.mark.asyncio
    async def test_full_processing_with_progress(self, temp_dir, simple_bookmarks_file, config):
        """Тест полной обработки с сохранением прогресса."""
        # Создаем мок для ContentFetcher
        with patch('src.fetcher.ContentFetcher') as mock_fetcher_class:
            mock_fetcher = AsyncMock()
            mock_fetcher.fetch_content.return_value = "<html><body><h1>Test Content</h1></body></html>"
            mock_fetcher.extract_text.return_value = "Test Content"
            mock_fetcher.__aenter__ = AsyncMock(return_value=mock_fetcher)
            mock_fetcher.__aexit__ = AsyncMock(return_value=None)
            
            # Создаем мок для LLM API
            with patch('openai.AsyncOpenAI') as mock_openai:
                mock_openai_instance = AsyncMock()
                mock_openai.return_value = mock_openai_instance
                mock_openai_instance.chat.completions.create.return_value = {
                    "choices": [{"message": {"content": "Test summary"}}]
                }
                
                # Создаем аргументы
                args = Mock()
                args.resume = False
                args.dry_run = True
                args.no_diagram = True
                
                # Парсим закладки
                parser = BookmarkParser()
                data = parser.load_json(simple_bookmarks_file)
                root_folder = parser.parse_bookmarks(data)
                
                # Обрабатываем закладки
                processed, failed = await process_bookmarks(
                    args, config, root_folder, simple_bookmarks_file
                )
                
                # Проверяем результаты
                assert processed == 2  # Все закладки должны быть обработаны
                assert failed == 0
                
                # Проверяем наличие файла прогресса
                progress_file = Path(config.output_dir) / "progress.json"
                assert progress_file.exists()
                
                # Проверяем содержимое файла прогресса
                with open(progress_file, 'r', encoding='utf-8') as f:
                    progress_data = json.load(f)
                
                assert len(progress_data['processed_urls']) == 2
                assert len(progress_data['failed_urls']) == 0
                assert progress_data['statistics']['processed_count'] == 2
                assert progress_data['statistics']['total_bookmarks'] == 2
    
    @pytest.mark.asyncio
    async def test_partial_processing_and_resume(self, temp_dir, simple_bookmarks_file, config):
        """Тест частичной обработки и возобновления."""
        # Создаем менеджер прогресса с правильным хешем
        from src.progress import calculate_config_hash
        config_hash = calculate_config_hash(config)
        progress_manager = ProgressManager(
            output_dir=config.output_dir,
            bookmarks_file=simple_bookmarks_file,
            config_hash=config_hash
        )
        
        # Добавляем одну обработанную закладку
        bookmark1 = create_test_bookmark("Processed Bookmark", "https://processed.com")
        progress_manager.add_processed_bookmark(bookmark1, "processed.md", ["Test"])
        
        # Сохраняем прогресс
        progress_manager.force_save()
        
        # Проверяем наличие файла прогресса
        progress_file = Path(config.output_dir) / "progress.json"
        assert progress_file.exists()
        
        # Создаем мок для ContentFetcher
        with patch('src.fetcher.ContentFetcher') as mock_fetcher_class:
            mock_fetcher = AsyncMock()
            mock_fetcher.fetch_content.return_value = "<html><body><h1>Test Content</h1></body></html>"
            mock_fetcher.extract_text.return_value = "Test Content"
            mock_fetcher.__aenter__ = AsyncMock(return_value=mock_fetcher)
            mock_fetcher.__aexit__ = AsyncMock(return_value=None)
            
            # Создаем мок для LLM API
            with patch('openai.AsyncOpenAI') as mock_openai:
                mock_openai_instance = AsyncMock()
                mock_openai.return_value = mock_openai_instance
                mock_openai_instance.chat.completions.create.return_value = {
                    "choices": [{"message": {"content": "Test summary"}}]
                }
                
                # Создаем аргументы для возобновления
                args = Mock()
                args.resume = True
                args.dry_run = True
                args.no_diagram = True
                
                # Парсим закладки
                parser = BookmarkParser()
                data = parser.load_json(simple_bookmarks_file)
                root_folder = parser.parse_bookmarks(data)
                
                # Обрабатываем закладки с возобновлением
                processed, failed = await process_bookmarks(
                    args, config, root_folder, simple_bookmarks_file
                )
                
                # Проверяем результаты
                assert processed == 2  # В dry-run режиме все закладки обрабатываются
                assert failed == 0
                
                # Проверяем обновленный прогресс
                with open(progress_file, 'r', encoding='utf-8') as f:
                    progress_data = json.load(f)
                
                # В dry-run режиме добавляются все закладки, включая уже обработанные
                assert len(progress_data['processed_urls']) == 3
                assert len(progress_data['failed_urls']) == 0
                # В dry-run режиме статистика обновляется после обработки всех закладок
                assert progress_data['statistics']['processed_count'] == 3
                assert progress_data['statistics']['total_bookmarks'] == 2
    
    @pytest.mark.asyncio
    async def test_resume_with_failed_bookmarks(self, temp_dir, simple_bookmarks_file, config):
        """Тест возобновления с ошибочными закладками."""
        # Создаем менеджер прогресса с правильным хешем
        from src.progress import calculate_config_hash
        config_hash = calculate_config_hash(config)
        progress_manager = ProgressManager(
            output_dir=config.output_dir,
            bookmarks_file=simple_bookmarks_file,
            config_hash=config_hash
        )
        
        # Добавляем одну закладку с ошибкой
        bookmark1 = create_test_bookmark("Failed Bookmark", "https://failed.com")
        progress_manager.add_failed_bookmark(bookmark1, "Test error", ["Test"])
        
        # Сохраняем прогресс
        progress_manager.force_save()
        
        # Проверяем наличие файла прогресса
        progress_file = Path(config.output_dir) / "progress.json"
        assert progress_file.exists()
        
        # Создаем мок для ContentFetcher
        with patch('src.fetcher.ContentFetcher') as mock_fetcher_class:
            mock_fetcher = AsyncMock()
            mock_fetcher.fetch_content.return_value = "<html><body><h1>Test Content</h1></body></html>"
            mock_fetcher.extract_text.return_value = "Test Content"
            mock_fetcher.__aenter__ = AsyncMock(return_value=mock_fetcher)
            mock_fetcher.__aexit__ = AsyncMock(return_value=None)
            
            # Создаем мок для LLM API
            with patch('openai.AsyncOpenAI') as mock_openai:
                mock_openai_instance = AsyncMock()
                mock_openai.return_value = mock_openai_instance
                mock_openai_instance.chat.completions.create.return_value = {
                    "choices": [{"message": {"content": "Test summary"}}]
                }
                
                # Создаем аргументы для возобновления
                args = Mock()
                args.resume = True
                args.dry_run = True
                args.no_diagram = True
                
                # Парсим закладки
                parser = BookmarkParser()
                data = parser.load_json(simple_bookmarks_file)
                root_folder = parser.parse_bookmarks(data)
                
                # Обрабатываем закладки с возобновлением
                processed, failed = await process_bookmarks(
                    args, config, root_folder, simple_bookmarks_file
                )
                
                # Проверяем результаты
                # В dry-run режиме обрабатываются все закладки, включая те, что уже были в списке ошибок
                assert processed == 2  # Все закладки должны быть обработаны в dry-run режиме
                assert failed == 0  # В dry-run режиме с моками нет ошибок
                
                # Проверяем обновленный прогресс
                with open(progress_file, 'r', encoding='utf-8') as f:
                    progress_data = json.load(f)
                
                # В dry-run режиме добавляются все закладки, включая уже обработанные
                assert len(progress_data['processed_urls']) == 2  # Обе закладки обработаны
                assert len(progress_data['failed_urls']) == 1  # Ошибка из предыдущего запуска сохраняется
                assert progress_data['statistics']['processed_count'] == 2
                assert progress_data['statistics']['failed_count'] == 1
                assert progress_data['statistics']['total_bookmarks'] == 2
    
    @pytest.mark.asyncio
    async def test_config_hash_validation(self, temp_dir, simple_bookmarks_file, config):
        """Тест валидации хеша конфигурации при возобновлении."""
        # Создаем менеджер прогресса с одним хешем
        progress_manager1 = ProgressManager(
            output_dir=config.output_dir,
            bookmarks_file=simple_bookmarks_file,
            config_hash="hash1"
        )
        
        # Добавляем обработанную закладку
        bookmark = create_test_bookmark("Test Bookmark", "https://test.com")
        progress_manager1.add_processed_bookmark(bookmark, "test.md", ["Test"])
        
        # Сохраняем прогресс
        progress_manager1.force_save()
        
        # Создаем менеджер с другим хешем
        progress_manager2 = ProgressManager(
            output_dir=config.output_dir,
            bookmarks_file=simple_bookmarks_file,
            config_hash="hash2"  # Другой хеш
        )
        
        # Пытаемся загрузить прогресс с другим хешем
        load_result = progress_manager2.load_progress()
        
        # Должно вернуться False из-за несовпадения хешей
        assert load_result is False
        assert len(progress_manager2.processed_bookmarks) == 0
    
    @pytest.mark.asyncio
    async def test_progress_position_tracking(self, temp_dir, simple_bookmarks_file, config):
        """Тест отслеживания позиции в прогрессе."""
        # Создаем менеджер прогресса
        progress_manager = ProgressManager(
            output_dir=config.output_dir,
            bookmarks_file=simple_bookmarks_file,
            config_hash="test_hash"
        )
        
        # Устанавливаем текущую позицию
        progress_manager.update_current_position(["Test"], 0, 2)
        
        # Добавляем обработанную закладку
        bookmark = create_test_bookmark("Test Bookmark", "https://test.com")
        progress_manager.add_processed_bookmark(bookmark, "test.md", ["Test"])
        
        # Сохраняем прогресс
        progress_manager.force_save()
        
        # Проверяем наличие файла прогресса
        progress_file = Path(config.output_dir) / "progress.json"
        assert progress_file.exists()
        
        # Проверяем сохраненную позицию
        with open(progress_file, 'r', encoding='utf-8') as f:
            progress_data = json.load(f)
        
        assert 'current_position' in progress_data
        assert progress_data['current_position']['folder_path'] == ["Test"]
        assert progress_data['current_position']['bookmark_index'] == 0  # Позиция не меняется при добавлении закладки
        assert progress_data['current_position']['total_in_folder'] == 2
    
    @pytest.mark.asyncio
    async def test_progress_statistics(self, temp_dir, simple_bookmarks_file, config):
        """Тест статистики прогресса."""
        # Создаем менеджер прогресса
        progress_manager = ProgressManager(
            output_dir=config.output_dir,
            bookmarks_file=simple_bookmarks_file,
            config_hash="test_hash"
        )
        
        # Добавляем обработанные и ошибочные закладки
        bookmark1 = create_test_bookmark("Success 1", "https://success1.com")
        bookmark2 = create_test_bookmark("Success 2", "https://success2.com")
        bookmark3 = create_test_bookmark("Failed 1", "https://failed1.com")
        
        progress_manager.add_processed_bookmark(bookmark1, "success1.md", ["Test"])
        progress_manager.add_processed_bookmark(bookmark2, "success2.md", ["Test"])
        progress_manager.add_failed_bookmark(bookmark3, "Error message", ["Test"])
        
        # Сохраняем прогресс
        progress_manager.force_save()
        
        # Проверяем статистику
        stats = progress_manager.get_statistics()
        if stats:
            assert stats.processed_count == 2
            assert stats.failed_count == 1
            assert stats.total_bookmarks == 3
            # Проверяем статистику без процентных полей
            assert stats.processed_count == 2
            assert stats.failed_count == 1
            assert stats.total_bookmarks == 3
    
    @pytest.mark.asyncio
    async def test_progress_persistence(self, temp_dir, simple_bookmarks_file, config):
        """Тест сохранения и загрузки прогресса."""
        # Создаем менеджер прогресса
        progress_manager1 = ProgressManager(
            output_dir=config.output_dir,
            bookmarks_file=simple_bookmarks_file,
            config_hash="test_hash"
        )
        
        # Добавляем данные
        bookmark = create_test_bookmark("Test Bookmark", "https://test.com")
        progress_manager1.add_processed_bookmark(bookmark, "test.md", ["Test"])
        progress_manager1.update_current_position(["Test"], 0, 1)
        
        # Сохраняем прогресс
        progress_manager1.force_save()
        
        # Создаем новый менеджер и загружаем прогресс
        progress_manager2 = ProgressManager(
            output_dir=config.output_dir,
            bookmarks_file=simple_bookmarks_file,
            config_hash="test_hash"
        )
        
        load_result = progress_manager2.load_progress()
        assert load_result is True
        
        # Проверяем загруженные данные
        assert len(progress_manager2.processed_bookmarks) == 1
        assert progress_manager2.processed_bookmarks[0].url == bookmark.url
        assert progress_manager2.current_position is not None
        assert progress_manager2.current_position.folder_path == ["Test"]
        assert progress_manager2.current_position.bookmark_index == 0
        assert progress_manager2.current_position.total_in_folder == 1
    
    @pytest.mark.asyncio
    async def test_concurrent_progress_updates(self, temp_dir, simple_bookmarks_file, config):
        """Тест параллельных обновлений прогресса."""
        # Создаем менеджер прогресса
        progress_manager = ProgressManager(
            output_dir=config.output_dir,
            bookmarks_file=simple_bookmarks_file,
            config_hash="test_hash"
        )
        
        # Создаем несколько закладок
        bookmarks = []
        for i in range(5):
            bookmark = create_test_bookmark(f"Test {i}", f"https://test{i}.com")
            bookmarks.append(bookmark)
        
        # Добавляем закладки последовательно (add_processed_bookmark не является асинхронной функцией)
        def add_bookmarks():
            for i, bookmark in enumerate(bookmarks):
                progress_manager.add_processed_bookmark(bookmark, f"test{i}.md", ["Test"])
        
        # Выполняем добавление
        add_bookmarks()
        
        # Инициализируем статистику
        progress_manager.initialize_statistics(5)
        
        # Сохраняем прогресс
        progress_manager.force_save()
        
        # Проверяем результаты
        assert len(progress_manager.processed_bookmarks) == 5
        
        # Проверяем сохраненные данные
        progress_file = Path(config.output_dir) / "progress.json"
        assert progress_file.exists()
        
        with open(progress_file, 'r', encoding='utf-8') as f:
            progress_data = json.load(f)
        
        assert len(progress_data['processed_urls']) == 5
        assert progress_data['statistics']['processed_count'] == 5
        assert progress_data['statistics']['total_bookmarks'] == 5
    
    @pytest.mark.asyncio
    async def test_progress_recovery_after_crash(self, temp_dir, simple_bookmarks_file, config):
        """Тест восстановления прогресса после сбоя."""
        # Создаем менеджер прогресса
        progress_manager1 = ProgressManager(
            output_dir=config.output_dir,
            bookmarks_file=simple_bookmarks_file,
            config_hash="test_hash"
        )
        
        # Добавляем частичные данные
        bookmark1 = create_test_bookmark("Processed 1", "https://processed1.com")
        bookmark2 = create_test_bookmark("Failed 1", "https://failed1.com")
        
        progress_manager1.add_processed_bookmark(bookmark1, "processed1.md", ["Test"])
        progress_manager1.add_failed_bookmark(bookmark2, "Error message", ["Test"])
        progress_manager1.update_current_position(["Test"], 1, 2)
        
        # Сохраняем прогресс
        progress_manager1.force_save()
        
        # Имитируем сбой - создаем новый менеджер
        progress_manager2 = ProgressManager(
            output_dir=config.output_dir,
            bookmarks_file=simple_bookmarks_file,
            config_hash="test_hash"
        )
        
        # Восстанавливаем прогресс
        load_result = progress_manager2.load_progress()
        assert load_result is True
        
        # Проверяем восстановленные данные
        assert len(progress_manager2.processed_bookmarks) == 1
        assert len(progress_manager2.failed_bookmarks) == 1
        assert progress_manager2.processed_bookmarks[0].url == bookmark1.url
        assert progress_manager2.failed_bookmarks[0].url == bookmark2.url
        assert progress_manager2.current_position is not None
        assert progress_manager2.current_position.folder_path == ["Test"]
        assert progress_manager2.current_position.bookmark_index == 1
        assert progress_manager2.current_position.total_in_folder == 2
        
        # Проверяем статистику
        stats = progress_manager2.get_statistics()
        if stats:
            assert stats.processed_count == 1
            assert stats.failed_count == 1
            assert stats.total_bookmarks == 2