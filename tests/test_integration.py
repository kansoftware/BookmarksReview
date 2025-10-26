"""
Интеграционные тесты для проверки взаимодействия между компонентами системы.
Тестируют полный цикл обработки закладок от парсинга до сохранения результатов.
"""
import json
import asyncio
from pathlib import Path
from unittest.mock import patch, AsyncMock, Mock

import pytest

from src.parser import BookmarkParser
from src.fetcher import ContentFetcher
from src.summarizer import ContentSummarizer
from src.diagram import DiagramGenerator
from src.writer import FileSystemWriter
from src.main import process_bookmarks, create_progress_manager
from tests.conftest import create_test_bookmark, create_test_folder


class TestIntegrationWorkflow:
    """Интеграционные тесты для основного workflow."""
    
    @pytest.mark.asyncio
    async def test_full_workflow_simple_bookmarks(self, temp_dir, simple_bookmarks_file, config, mock_llm_response):
        """Тест полного цикла обработки простых закладок."""
        # Создаем мок для HTTP-клиента
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.aclose = AsyncMock()
            mock_response = AsyncMock()
            mock_response.text = "<html><body><h1>Test Content</h1><p>Test paragraph</p></body></html>"
            mock_response.status_code = 200
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client_class.return_value.__aexit__ = AsyncMock()
            
            # Создаем мок для LLM API
            with patch('openai.AsyncOpenAI') as mock_openai:
                mock_openai_instance = AsyncMock()
                mock_openai.return_value = mock_openai_instance
                mock_openai_instance.chat.completions.create.return_value = mock_llm_response
                
                # Инициализируем компоненты
                parser = BookmarkParser()
                fetcher = ContentFetcher(config)
                summarizer = ContentSummarizer(config)
                writer = FileSystemWriter(config)
                diagram_gen = DiagramGenerator()
                
                # Парсим закладки
                data = parser.load_json(simple_bookmarks_file)
                root_folder = parser.parse_bookmarks(data)
                
                # Генерируем диаграмму
                diagram_code = diagram_gen.generate_structure_diagram(root_folder)
                diagram_path = Path(config.output_dir) / "bookmarks_structure.md"
                diagram_path.parent.mkdir(parents=True, exist_ok=True)
                diagram_gen.save_diagram(diagram_code, str(diagram_path))
                
                # Создаем структуру папок
                writer.create_folder_structure(root_folder, config.output_dir)
                
                # Инициализируем сессию напрямую, минуя контекстный менеджер
                fetcher.session = mock_client
                
                processed_count = 0

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

                        # Генерируем описание
                        summary = await summarizer.generate_summary(text, bookmark.title)

                        # Создаем объект обработанной страницы
                        from src.models import ProcessedPage
                        from datetime import datetime

                        page = ProcessedPage(
                            url=bookmark.url,
                            title=bookmark.title,
                            summary=summary,
                            fetch_date=datetime.now(),
                            status='success'
                        )

                        # Определяем путь к файлу
                        file_path = Path(config.output_dir) / f"{bookmark.title}.md"

                        # Сохраняем результат
                        writer.write_markdown(page, file_path)
                        processed_count += 1
                
                # Проверяем результаты
                assert processed_count == 2
                assert diagram_path.exists()
                
                # Проверяем содержимое диаграммы
                with open(diagram_path, 'r', encoding='utf-8') as f:
                    diagram_content = f.read()
                    assert "```mermaid" in diagram_content
                    assert "graph TD" in diagram_content
                
                # Проверяем созданные файлы
                output_dir = Path(config.output_dir)
                markdown_files = list(output_dir.glob("*.md"))
                assert len(markdown_files) >= 2  # Хотя бы 2 файла для закладок + диаграмма
    
    @pytest.mark.asyncio
    async def test_full_workflow_nested_bookmarks(self, temp_dir, nested_bookmarks_file, config, mock_llm_response):
        """Тест полного цикла обработки вложенных закладок."""
        # Создаем мок для HTTP-клиента
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.aclose = AsyncMock()
            mock_response = AsyncMock()
            mock_response.text = "<html><body><h1>Nested Test Content</h1><p>Nested test paragraph</p></body></html>"
            mock_response.status_code = 200
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client_class.return_value.__aexit__ = AsyncMock()
            
            # Создаем мок для LLM API
            with patch('src.summarizer.AsyncOpenAI') as mock_openai:
                mock_openai_instance = AsyncMock()
                mock_openai.return_value = mock_openai_instance
                mock_openai_instance.chat.completions.create.return_value = mock_llm_response
                
                # Инициализируем компоненты
                parser = BookmarkParser()
                writer = FileSystemWriter(config)
                
                # Парсим закладки
                data = parser.load_json(nested_bookmarks_file)
                root_folder = parser.parse_bookmarks(data)
                
                # Создаем структуру папок
                writer.create_folder_structure(root_folder, config.output_dir)
                
                # Проверяем создание вложенной структуры папок
                output_dir = Path(config.output_dir)
                root_folder = output_dir / "Root"
                bookmark_bar = root_folder / "Bookmark Bar"
                folder1 = bookmark_bar / "Folder 1"
                subfolder1_1 = folder1 / "Subfolder 1.1"
                folder2 = bookmark_bar / "Folder 2"

                assert root_folder.exists()
                assert bookmark_bar.exists()
                assert folder1.exists()
                assert subfolder1_1.exists()
                assert folder2.exists()
    
    @pytest.mark.asyncio
    async def test_error_handling_workflow(self, temp_dir, simple_bookmarks_file, config):
        """Тест обработки ошибок в workflow."""
        # Создаем мок для HTTP-клиента, который вызывает ошибку
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.aclose = AsyncMock()
            mock_client.get.side_effect = Exception("Network error")
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
            
            processed_count = 0
            error_count = 0

            def traverse_bookmarks(folder):
                """Рекурсивно обходит все закладки в папке."""
                for bookmark in folder.bookmarks:
                    yield bookmark
                for child_folder in folder.children:
                    yield from traverse_bookmarks(child_folder)

            for bookmark in traverse_bookmarks(root_folder):
                # Пытаемся загрузить контент
                html = await fetcher.fetch_content(bookmark.url)
                if html:
                    processed_count += 1
                else:
                    error_count += 1

            # Проверяем, что ошибки обработаны корректно
            assert error_count == 2  # Обе закладки должны вызвать ошибку
            assert processed_count == 0
    
    @pytest.mark.asyncio
    async def test_rate_limiting_integration(self, temp_dir, simple_bookmarks_file, config, mock_llm_response):
        """Тест интеграции rate limiting."""
        # Изменяем конфигурацию для теста rate limiting
        config.llm_rate_limit = 2  # Устанавливаем низкий лимит
        
        # Создаем мок для HTTP-клиента
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.aclose = AsyncMock()
            mock_response = AsyncMock()
            mock_response.text = "<html><body><h1>Rate Limit Test</h1></body></html>"
            mock_response.status_code = 200
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client_class.return_value.__aexit__ = AsyncMock()
            
            # Создаем мок для LLM API с отслеживанием вызовов
            with patch('src.summarizer.AsyncOpenAI') as mock_openai:
                mock_openai_instance = AsyncMock()
                mock_openai.return_value = mock_openai_instance
                mock_openai_instance.chat.completions.create.return_value = mock_llm_response
                
                # Инициализируем компоненты
                parser = BookmarkParser()
                fetcher = ContentFetcher(config)
                summarizer = ContentSummarizer(config)
                
                # Парсим закладки
                data = parser.load_json(simple_bookmarks_file)
                root_folder = parser.parse_bookmarks(data)
                
                # Инициализируем сессию напрямую, минуя контекстный менеджер
                fetcher.session = mock_client
                
                # Обрабатываем закладки

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

                        # Генерируем описание
                        await summarizer.generate_summary(text, bookmark.title)

                # Проверяем, что LLM API был вызван правильное количество раз
                assert mock_openai_instance.chat.completions.create.call_count == 2
    
    def test_config_parsing_integration(self, temp_dir, sample_config):
        """Тест интеграции парсинга конфигурации."""
        from src.config import ConfigManager
        
        # Загружаем конфигурацию
        config_manager = ConfigManager(sample_config)
        config = config_manager.get()
        
        # Проверяем, что все параметры загружены корректно
        assert config.llm_api_key == "test_key"
        assert config.llm_base_url == "https://api.openai.com/v1"
        assert config.llm_model == "gpt-4o-mini"
        assert config.llm_max_tokens == 1000
        assert config.llm_temperature == 0.7
        assert config.llm_rate_limit == 3
        assert config.fetch_timeout == 30
        assert config.fetch_max_concurrent == 10
        assert config.fetch_max_size_mb == 5
        assert config.fetch_retry_attempts == 3
        assert config.fetch_retry_delay == 1.5
        assert config.markdown_include_metadata is True
        assert config.generate_mermaid_diagram is True
        assert config.log_level == "INFO"
    
    @pytest.mark.asyncio
    async def test_progress_manager_integration(self, temp_dir, simple_bookmarks_file, config):
        """Тест интеграции менеджера прогресса."""
        from src.progress import ProgressManager
        from src.models import ProcessedPage
        from datetime import datetime
        
        # Создаем менеджер прогресса
        progress_manager = ProgressManager(
            output_dir=config.output_dir,
            bookmarks_file=simple_bookmarks_file,
            config_hash="test_hash"
        )
        
        # Добавляем тестовые закладки
        bookmark1 = create_test_bookmark("Test 1", "https://test1.com")
        bookmark2 = create_test_bookmark("Test 2", "https://test2.com")
        
        # Добавляем обработанные закладки
        page1 = ProcessedPage(
            url=bookmark1.url,
            title=bookmark1.title,
            summary="Test summary 1",
            fetch_date=datetime.now(),
            status='success'
        )
        
        page2 = ProcessedPage(
            url=bookmark2.url,
            title=bookmark2.title,
            summary="Test summary 2",
            fetch_date=datetime.now(),
            status='success'
        )
        
        progress_manager.add_processed_bookmark(bookmark1, "test1.md", ["Test"])
        progress_manager.add_processed_bookmark(bookmark2, "test2.md", ["Test"])
        
        # Сохраняем прогресс
        result = progress_manager.force_save()
        assert result is True
        
        # Проверяем наличие файла прогресса
        progress_file = Path(config.output_dir) / "progress.json"
        assert progress_file.exists()
        
        # Загружаем и проверяем прогресс
        with open(progress_file, 'r', encoding='utf-8') as f:
            progress_data = json.load(f)
        
        assert len(progress_data['processed_urls']) == 2
        assert progress_data['processed_urls'][0]['url'] == bookmark1.url
        assert progress_data['processed_urls'][1]['url'] == bookmark2.url