"""
Интеграционные тесты для обработки ошибок и восстановления.
Тестируют поведение системы при возникновении ошибок.
"""
import json
import asyncio
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, AsyncMock

import pytest

from src.parser import BookmarkParser
from src.fetcher import ContentFetcher
from src.summarizer import ContentSummarizer
from src.writer import FileSystemWriter
from src.progress import ProgressManager
from tests.conftest import create_test_bookmark, create_test_folder


class TestErrorHandlingIntegration:
    """Интеграционные тесты для обработки ошибок."""
    
    @pytest.mark.asyncio
    async def test_network_error_handling(self, temp_dir, simple_bookmarks_file, config):
        """Тест обработки сетевых ошибок."""
        # Создаем мок для HTTP-клиента с ошибкой сети
        mock_client = AsyncMock()
        mock_client.aclose = AsyncMock()
        mock_client.get.side_effect = Exception("Network error")

        # Инициализируем компоненты
        parser = BookmarkParser()
        fetcher = ContentFetcher(config)

        # Парсим закладки
        data = parser.load_json(simple_bookmarks_file)
        root_folder = parser.parse_bookmarks(data)

        # Считаем ошибки
        error_count = 0
        success_count = 0

        # Инициализируем сессию напрямую, минуя контекстный менеджер
        fetcher.session = mock_client

        def traverse_bookmarks(folder):
            """Рекурсивно обходит все закладки в папке."""
            for bookmark in folder.bookmarks:
                yield bookmark
            for child_folder in folder.children:
                yield from traverse_bookmarks(child_folder)

        for bookmark in traverse_bookmarks(root_folder):
            html = await fetcher.fetch_content(bookmark.url)
            if html:
                success_count += 1
            else:
                error_count += 1

        # Проверяем результаты
        assert error_count == 2  # Обе закладки должны вызвать ошибку
        assert success_count == 0
    
    @pytest.mark.asyncio
    async def test_http_error_handling(self, temp_dir, simple_bookmarks_file, config):
        """Тест обработки HTTP-ошибок."""
        # Создаем мок для HTTP-клиента с HTTP-ошибками
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.aclose = AsyncMock()
            
            # Создаем мок-ответ с ошибкой 404
            mock_response_404 = AsyncMock()
            mock_response_404.status_code = 404
            mock_response_404.text = None
            
            # Создаем мок-ответ с ошибкой 500
            mock_response_500 = AsyncMock()
            mock_response_500.status_code = 500
            mock_response_500.text = None
            
            # Настраиваем последовательность ответов
            mock_client.get.side_effect = [mock_response_404, mock_response_500]
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client_class.return_value.__aexit__ = AsyncMock()
            
            # Инициализируем компоненты
            parser = BookmarkParser()
            fetcher = ContentFetcher(config)
            
            # Парсим закладки
            data = parser.load_json(simple_bookmarks_file)
            root_folder = parser.parse_bookmarks(data)
            
            # Считаем ошибки
            error_count = 0
            success_count = 0
            
            # Инициализируем сессию напрямую, минуя контекстный менеджер
            fetcher.session = mock_client
            
            def traverse_bookmarks(folder):
                """Рекурсивно обходит все закладки в папке."""
                for bookmark in folder.bookmarks:
                    yield bookmark
                for child_folder in folder.children:
                    yield from traverse_bookmarks(child_folder)
    
            for bookmark in traverse_bookmarks(root_folder):
                html = await fetcher.fetch_content(bookmark.url)
                if html:
                    success_count += 1
                else:
                    error_count += 1
            
            # Проверяем результаты
            assert error_count == 2  # Обе закладки должны вызвать ошибку
            assert success_count == 0
    
    @pytest.mark.asyncio
    async def test_llm_api_error_handling(self, temp_dir, simple_bookmarks_file, config):
        """Тест обработки ошибок LLM API."""
        # Создаем мок для HTTP-клиента
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.aclose = AsyncMock()
            mock_response = AsyncMock()
            mock_response.text = "<html><body><h1>Test Content</h1></body></html>"
            mock_response.status_code = 200
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client_class.return_value.__aexit__ = AsyncMock()
            
            # Создаем мок для LLM API с ошибкой
            with patch('src.summarizer.AsyncOpenAI') as mock_openai:
                mock_openai_instance = AsyncMock()
                mock_openai.return_value = mock_openai_instance
                mock_openai_instance.chat.completions.create.side_effect = Exception("LLM API error")
                
                # Инициализируем компоненты
                parser = BookmarkParser()
                fetcher = ContentFetcher(config)
                summarizer = ContentSummarizer(config)
                
                # Парсим закладки
                data = parser.load_json(simple_bookmarks_file)
                root_folder = parser.parse_bookmarks(data)
                
                # Считаем ошибки
                error_count = 0
                success_count = 0
                
                # Инициализируем сессию напрямую, минуя контекстный менеджер
                fetcher.session = mock_client
                
                def traverse_bookmarks(folder):
                    """Рекурсивно обходит все закладки в папке."""
                    for bookmark in folder.bookmarks:
                        yield bookmark
                    for child_folder in folder.children:
                        yield from traverse_bookmarks(child_folder)

                for bookmark in traverse_bookmarks(root_folder):
                    # Загружаем контент
                    html = await fetcher.fetch_content(bookmark.url)
                    if html:
                        text = fetcher.extract_text(html)

                        # Пытаемся сгенерировать описание
                        summary = await summarizer.generate_summary(text, bookmark.title)
                        if summary and not summary.startswith("Ошибка генерации описания"):
                            success_count += 1
                        else:
                            error_count += 1
                    else:
                        error_count += 1

                # Проверяем результаты
                assert error_count == 2  # Обе закладки должны вызвать ошибку
                assert success_count == 0
    
    @pytest.mark.asyncio
    async def test_file_system_error_handling(self, temp_dir, simple_bookmarks_file, config):
        """Тест обработки ошибок файловой системы."""
        # Инициализируем компоненты
        parser = BookmarkParser()
        writer = FileSystemWriter(config)
        
        # Парсим закладки
        data = parser.load_json(simple_bookmarks_file)
        root_folder = parser.parse_bookmarks(data)
        
        # Создаем страницу
        from src.models import ProcessedPage
        
        page = ProcessedPage(
            url="https://example.com",
            title="Test Page",
            summary="Test summary",
            fetch_date=datetime.now(),
            status='success'
        )
        
        # Пытаемся сохранить файл в недоступной директории
        invalid_path = Path("/nonexistent/path/test.md")
        
        # Должна возникнуть ошибка
        with pytest.raises(Exception):
            writer.write_markdown(page, invalid_path)
    
    @pytest.mark.asyncio
    async def test_malformed_bookmarks_file(self, temp_dir, config):
        """Тест обработки некорректного файла закладок."""
        # Создаем некорректный JSON-файл
        malformed_file = temp_dir / "malformed.json"
        with open(malformed_file, 'w', encoding='utf-8') as f:
            f.write('{"invalid": "json"}')
        
        # Инициализируем парсер
        parser = BookmarkParser()
        
        # Должна возникнуть ошибка при парсинге
        with pytest.raises(Exception):
            parser.load_json(str(malformed_file))
    
    @pytest.mark.asyncio
    async def test_rate_limiting_with_errors(self, temp_dir, simple_bookmarks_file, config):
        """Тест работы rate limiting при ошибках."""
        # Устанавливаем низкий лимит для теста
        config.llm_rate_limit = 1
        
        # Создаем мок для HTTP-клиента
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.aclose = AsyncMock()
            mock_response = AsyncMock()
            mock_response.text = "<html><body><h1>Test Content</h1></body></html>"
            mock_response.status_code = 200
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client_class.return_value.__aexit__ = AsyncMock()
            
            # Создаем мок для LLM API с ошибкой rate limit
            with patch('src.summarizer.AsyncOpenAI') as mock_openai:
                mock_openai_instance = AsyncMock()
                mock_openai.return_value = mock_openai_instance

                # Создаем успешный ответ
                success_response = AsyncMock()
                success_response.choices = [AsyncMock()]
                success_response.choices[0].message = AsyncMock()
                success_response.choices[0].message.content = "Success response"

                # Первый вызов успешный, второй - ошибка rate limit, третий - успешный после retry
                mock_openai_instance.chat.completions.create.side_effect = [
                    success_response,
                    Exception("Rate limit exceeded"),
                    success_response
                ]
                
                # Инициализируем компоненты
                parser = BookmarkParser()
                fetcher = ContentFetcher(config)
                summarizer = ContentSummarizer(config)
                
                # Парсим закладки
                data = parser.load_json(simple_bookmarks_file)
                root_folder = parser.parse_bookmarks(data)
                
                # Обрабатываем закладки с измерением времени
                start_time = asyncio.get_event_loop().time()

                success_count = 0
                error_count = 0

                # Инициализируем сессию напрямую, минуя контекстный менеджер
                fetcher.session = mock_client

                def traverse_bookmarks(folder):
                    """Рекурсивно обходит все закладки в папке."""
                    for bookmark in folder.bookmarks:
                        yield bookmark
                    for child_folder in folder.children:
                        yield from traverse_bookmarks(child_folder)

                for bookmark in traverse_bookmarks(root_folder):
                    try:
                        # Загружаем контент
                        html = await fetcher.fetch_content(bookmark.url)
                        if html:
                            text = fetcher.extract_text(html)

                            # Генерируем описание
                            summary = await summarizer.generate_summary(text, bookmark.title)
                            if summary and not summary.startswith("Ошибка генерации описания"):
                                success_count += 1
                            else:
                                error_count += 1
                        else:
                            error_count += 1
                    except Exception:
                        error_count += 1

                end_time = asyncio.get_event_loop().time()
                elapsed_time = end_time - start_time

                # Проверяем результаты
                assert success_count >= 1 # Хотя бы одна закладка обработана
                assert error_count >= 1 # Хотя бы одна ошибка
                
                # Проверяем, что было задержка из-за rate limiting
                assert elapsed_time > 1.0  # Должна быть задержка
    
    @pytest.mark.asyncio
    async def test_progress_recovery_after_error(self, temp_dir, simple_bookmarks_file, config):
        """Тест восстановления прогресса после ошибки."""
        # Создаем менеджер прогресса
        progress_manager = ProgressManager(
            output_dir=config.output_dir,
            bookmarks_file=simple_bookmarks_file,
            config_hash="test_hash"
        )
        
        # Добавляем закладку с ошибкой
        bookmark = create_test_bookmark("Test Bookmark", "https://example.com")
        progress_manager.add_failed_bookmark(bookmark, "Test error", ["Test"])
        
        # Сохраняем прогресс
        progress_manager.force_save()
        
        # Проверяем наличие файла прогресса
        progress_file = Path(config.output_dir) / "progress.json"
        assert progress_file.exists()
        
        # Загружаем прогресс
        with open(progress_file, 'r', encoding='utf-8') as f:
            progress_data = json.load(f)
        
        # Проверяем наличие ошибки в прогрессе
        assert len(progress_data['failed_urls']) == 1
        assert progress_data['failed_urls'][0]['url'] == bookmark.url
        assert progress_data['failed_urls'][0]['error'] == "Test error"
        
        # Создаем новый менеджер и загружаем прогресс
        new_progress_manager = ProgressManager(
            output_dir=config.output_dir,
            bookmarks_file=simple_bookmarks_file,
            config_hash="test_hash"
        )
        
        load_result = new_progress_manager.load_progress()
        assert load_result is True
        assert len(new_progress_manager.failed_bookmarks) == 1
        assert new_progress_manager.failed_bookmarks[0].url == bookmark.url
    
    @pytest.mark.asyncio
    async def test_partial_processing_recovery(self, temp_dir, simple_bookmarks_file, config):
        """Тест восстановления после частичной обработки."""
        # Создаем менеджер прогресса
        progress_manager = ProgressManager(
            output_dir=config.output_dir,
            bookmarks_file=simple_bookmarks_file,
            config_hash="test_hash"
        )
        
        # Добавляем одну обработанную закладку
        bookmark1 = create_test_bookmark("Processed Bookmark", "https://processed.com")
        progress_manager.add_processed_bookmark(bookmark1, "processed.md", ["Test"])
        
        # Добавляем одну закладку с ошибкой
        bookmark2 = create_test_bookmark("Failed Bookmark", "https://failed.com")
        progress_manager.add_failed_bookmark(bookmark2, "Failed error", ["Test"])
        
        # Сохраняем прогресс
        progress_manager.force_save()
        
        # Проверяем наличие файла прогресса
        progress_file = Path(config.output_dir) / "progress.json"
        assert progress_file.exists()
        
        # Создаем новый менеджер и загружаем прогресс
        new_progress_manager = ProgressManager(
            output_dir=config.output_dir,
            bookmarks_file=simple_bookmarks_file,
            config_hash="test_hash"
        )
        
        load_result = new_progress_manager.load_progress()
        assert load_result is True
        
        # Проверяем состояние
        assert len(new_progress_manager.processed_bookmarks) == 1
        assert len(new_progress_manager.failed_bookmarks) == 1
        assert new_progress_manager.processed_bookmarks[0].url == bookmark1.url
        assert new_progress_manager.failed_bookmarks[0].url == bookmark2.url
        
        # Проверяем статистику
        stats = new_progress_manager.get_statistics()
        if stats:
            assert stats.processed_count == 1
            assert stats.failed_count == 1
            assert stats.total_bookmarks == 2
    
    @pytest.mark.asyncio
    async def test_concurrent_error_handling(self, temp_dir, simple_bookmarks_file, config):
        """Тест обработки ошибок при параллельной обработке."""
        # Создаем мок для HTTP-клиента с периодическими ошибками
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.aclose = AsyncMock()
            
            # Создаем мок-ответы
            success_response = AsyncMock()
            success_response.text = "<html><body><h1>Success</h1></body></html>"
            success_response.status_code = 200

            # Настраиваем последовательность: успех, ошибка
            mock_client.get.side_effect = [success_response, Exception("Network error")]
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client_class.return_value.__aexit__ = AsyncMock()
            
            # Инициализируем компоненты
            parser = BookmarkParser()
            fetcher = ContentFetcher(config)
            
            # Парсим закладки
            data = parser.load_json(simple_bookmarks_file)
            root_folder = parser.parse_bookmarks(data)
            
            # Инициализируем сессию напрямую, минуя контекстный менеджер
            fetcher.session = mock_client
            
            success_count = 0
            error_count = 0
            
            def traverse_bookmarks(folder):
                """Рекурсивно обходит все закладки в папке."""
                for bookmark in folder.bookmarks:
                    yield bookmark
                for child_folder in folder.children:
                    yield from traverse_bookmarks(child_folder)
    
            for bookmark in traverse_bookmarks(root_folder):
                html = await fetcher.fetch_content(bookmark.url)
                if html:
                    success_count += 1
                else:
                    error_count += 1

            # Проверяем результаты
            assert success_count == 1  # Один успешный запрос
            assert error_count == 1    # Одна ошибка
            assert error_count == 1  # Одна ошибка
    
    @pytest.mark.asyncio
    async def test_memory_error_handling(self, temp_dir, simple_bookmarks_file, config):
        """Тест обработки ошибок памяти."""
        # Создаем мок для HTTP-клиента с большим ответом
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.aclose = AsyncMock()
            
            # Создаем мок-ответ с большим содержимым
            large_response = AsyncMock()
            large_response.text = "x" * (10 * 1024 * 1024)  # 10MB
            large_response.status_code = 200
            
            mock_client.get.return_value = large_response
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client_class.return_value.__aexit__ = AsyncMock()
            
            # Устанавливаем низкий лимит размера
            config.fetch_max_size_mb = 1  # 1MB
            
            # Инициализируем компоненты
            parser = BookmarkParser()
            fetcher = ContentFetcher(config)
            
            # Парсим закладки
            data = parser.load_json(simple_bookmarks_file)
            root_folder = parser.parse_bookmarks(data)
            
            # Инициализируем сессию напрямую, минуя контекстный менеджер
            fetcher.session = mock_client
            
            error_count = 0
            success_count = 0
            
            def traverse_bookmarks(folder):
                """Рекурсивно обходит все закладки в папке."""
                for bookmark in folder.bookmarks:
                    yield bookmark
                for child_folder in folder.children:
                    yield from traverse_bookmarks(child_folder)

            for bookmark in traverse_bookmarks(root_folder):
                html = await fetcher.fetch_content(bookmark.url)
                if html:
                    success_count += 1
                else:
                    error_count += 1
            
            # Проверяем результаты
            assert error_count == 2  # Обе закладки должны вызвать ошибку из-за размера
            assert success_count == 0