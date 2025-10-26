"""
Интеграционные тесты для функционала инкрементального выполнения и возобновления.
Проверяют полный цикл обработки с сохранением и восстановлением прогресса.
"""
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

import pytest

from src.main import process_bookmarks, create_progress_manager
from src.models import BookmarkFolder, Bookmark
from src.config import ConfigManager


class TestIntegrationProgress:
    """Интеграционные тесты для функционала прогресса."""
    
    @pytest.fixture
    def temp_dir(self):
        """Создает временную директорию для тестов."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def sample_bookmarks_file(self, temp_dir):
        """Создает тестовый файл закладок."""
        bookmarks_data = {
            "checksum": "test_checksum",
            "roots": {
                "bookmark_bar": {
                    "children": [
                        {
                            "name": "Folder 1",
                            "type": "folder",
                            "children": [
                                {
                                    "name": "Bookmark 1",
                                    "type": "url",
                                    "url": "https://example1.com"
                                },
                                {
                                    "name": "Bookmark 2",
                                    "type": "url",
                                    "url": "https://example2.com"
                                }
                            ]
                        },
                        {
                            "name": "Folder 2",
                            "type": "folder",
                            "children": [
                                {
                                    "name": "Bookmark 3",
                                    "type": "url",
                                    "url": "https://example3.com"
                                }
                            ]
                        }
                    ]
                }
            },
            "version": 1
        }
        
        bookmarks_file = temp_dir / "test_bookmarks.json"
        with open(bookmarks_file, 'w', encoding='utf-8') as f:
            json.dump(bookmarks_data, f)
        
        return str(bookmarks_file)
    
    @pytest.fixture
    def sample_config(self, temp_dir):
        """Создает тестовую конфигурацию."""
        config_file = temp_dir / ".env"
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(f"""
LLM_API_KEY=test_key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
LLM_MAX_TOKENS=1000
LLM_TEMPERATURE=0.7
LLM_RATE_LIMIT=3
FETCH_TIMEOUT=30
FETCH_MAX_CONCURRENT=10
FETCH_MAX_SIZE_MB=5
FETCH_RETRY_ATTEMPTS=3
FETCH_RETRY_DELAY=1.5
OUTPUT_DIR={temp_dir}/output
MARKDOWN_INCLUDE_METADATA=true
GENERATE_MERMAID_DIAGRAM=true
PROMPT_FILE=./prompts/summarize_prompt.txt
LOG_LEVEL=INFO
LOG_FILE={temp_dir}/test.log
""")
        
        return str(config_file)
    
    @pytest.fixture
    def mock_args(self):
        """Создает мок аргументов командной строки."""
        args = Mock()
        args.resume = False
        args.dry_run = True  # Используем dry-run для тестов
        args.no_diagram = True
        return args
    
    @pytest.mark.asyncio
    async def test_full_processing_with_progress(self, temp_dir, sample_bookmarks_file, sample_config, mock_args):
        """Тест полной обработки с сохранением прогресса."""
        # Загружаем конфигурацию
        config_manager = ConfigManager(sample_config)
        config = config_manager.get()
        
        # Вычисляем правильный хеш для теста
        from src.progress import calculate_config_hash
        correct_hash = calculate_config_hash(config)
        
        # Парсим закладки
        from src.parser import BookmarkParser
        parser = BookmarkParser()
        data = parser.load_json(sample_bookmarks_file)
        root_folder = parser.parse_bookmarks(data)
        
        # Обрабатываем закладки
        processed, failed = await process_bookmarks(
            mock_args, config, root_folder, sample_bookmarks_file
        )
        
        # Проверяем результаты
        assert processed == 3  # Все закладки должны быть обработаны в dry-run
        assert failed == 0
        
        # Проверяем наличие файла прогресса
        progress_file = Path(config.output_dir) / "progress.json"
        assert progress_file.exists()
        
        # Проверяем содержимое файла прогресса
        with open(progress_file, 'r', encoding='utf-8') as f:
            progress_data = json.load(f)
        
        assert progress_data['version'] == '1.0'
        assert progress_data['bookmarks_file'] == sample_bookmarks_file
        assert progress_data['config_hash'] == correct_hash
        assert len(progress_data['processed_urls']) == 3
        assert len(progress_data['failed_urls']) == 0
        assert progress_data['statistics']['total_bookmarks'] == 3
        assert progress_data['statistics']['processed_count'] == 3
    
    @pytest.mark.asyncio
    async def test_resume_processing(self, temp_dir, sample_bookmarks_file, sample_config, mock_args):
        """Тест возобновления обработки."""
        # Загружаем конфигурацию
        config_manager = ConfigManager(sample_config)
        config = config_manager.get()
        
        # Вычисляем правильный хеш для теста
        from src.progress import calculate_config_hash
        correct_hash = calculate_config_hash(config)
        
        # Парсим закладки
        from src.parser import BookmarkParser
        parser = BookmarkParser()
        data = parser.load_json(sample_bookmarks_file)
        root_folder = parser.parse_bookmarks(data)
        
        # Создаем частичный прогресс (имитируем прерванную обработку)
        progress_file = Path(config.output_dir) / "progress.json"
        progress_file.parent.mkdir(parents=True, exist_ok=True)
        
        partial_progress = {
            "version": "1.0",
            "timestamp": datetime.now().isoformat(),
            "bookmarks_file": sample_bookmarks_file,
            "config_hash": correct_hash,
            "processed_urls": [
                {
                    "url": "https://example1.com",
                    "title": "Bookmark 1",
                    "processed_at": datetime.now().isoformat(),
                    "file_path": "Folder 1/Bookmark 1.md",
                    "folder_path": ["Folder 1"]
                }
            ],
            "failed_urls": [
                {
                    "url": "https://example2.com",
                    "title": "Bookmark 2",
                    "failed_at": datetime.now().isoformat(),
                    "error": "Test error",
                    "folder_path": ["Folder 1"]
                }
            ],
            "current_position": {
                "folder_path": ["Folder 1"],
                "bookmark_index": 1,
                "total_in_folder": 2
            },
            "statistics": {
                "total_bookmarks": 3,
                "processed_count": 1,
                "failed_count": 1,
                "skipped_count": 0,
                "start_time": datetime.now().isoformat(),
                "last_update": datetime.now().isoformat()
            }
        }
        
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(partial_progress, f)
        
        # Устанавливаем флаг возобновления
        mock_args.resume = True
        
        # Обрабатываем закладки с возобновлением
        processed, failed = await process_bookmarks(
            mock_args, config, root_folder, sample_bookmarks_file
        )
        
        # Проверяем результаты
        assert processed == 1  # Только новая закладка должна быть обработана
        assert failed == 1  # Одна закладка уже была с ошибкой
        
        # Проверяем обновленный прогресс
        with open(progress_file, 'r', encoding='utf-8') as f:
            updated_progress = json.load(f)
        
        # Должна быть обработана только новая закладка
        assert len(updated_progress['processed_urls']) == 2
        assert len(updated_progress['failed_urls']) == 1
        
        # Проверяем, что новая закладка добавлена
        processed_urls = [item['url'] for item in updated_progress['processed_urls']]
        assert "https://example3.com" in processed_urls
    
    @pytest.mark.asyncio
    async def test_progress_manager_integration(self, temp_dir, sample_config, sample_bookmarks_file):
        """Тест интеграции ProgressManager с основным кодом."""
        # Создаем аргументы
        args = Mock()
        args.resume = False
        
        # Загружаем конфигурацию
        config_manager = ConfigManager(sample_config)
        config = config_manager.get()
        
        # Создаем менеджер прогресса
        progress_manager = create_progress_manager(args, config, sample_bookmarks_file)
        
        # Проверяем инициализацию
        assert progress_manager is not None
        assert progress_manager.output_dir == Path(config.output_dir)
        assert progress_manager.bookmarks_file == sample_bookmarks_file
        
        # Добавляем тестовые данные
        bookmark = Bookmark(
            title="Test Bookmark",
            url="https://test.com",
            date_added=datetime.now()
        )
        
        folder_path = ["Test", "Subfolder"]
        progress_manager.add_processed_bookmark(bookmark, "test.md", folder_path)
        
        # Проверяем, что данные добавлены
        assert len(progress_manager.processed_bookmarks) == 1
        assert progress_manager.processed_bookmarks[0].url == bookmark.url
        
        # Сохраняем прогресс
        result = progress_manager.force_save()
        assert result is True
        
        # Проверяем наличие файла
        progress_file = Path(config.output_dir) / "progress.json"
        assert progress_file.exists()
        
        # Создаем новый менеджер и загружаем прогресс
        new_args = Mock()
        new_args.resume = True
        
        new_manager = create_progress_manager(new_args, config, sample_bookmarks_file)
        load_result = new_manager.load_progress()
        
        assert load_result is True
        assert len(new_manager.processed_bookmarks) == 1
        assert new_manager.processed_bookmarks[0].url == bookmark.url
    
    def test_config_hash_consistency(self, temp_dir, sample_config):
        """Тест консистентности хеша конфигурации."""
        # Загружаем конфигурацию
        config_manager = ConfigManager(sample_config)
        config = config_manager.get()
        
        # Вычисляем хеш
        from src.progress import calculate_config_hash
        hash1 = calculate_config_hash(config)
        
        # Создаем новую конфигурацию с теми же параметрами
        config_manager2 = ConfigManager(sample_config)
        config2 = config_manager2.get()
        
        hash2 = calculate_config_hash(config2)
        
        # Хеши должны быть одинаковыми
        assert hash1 == hash2
        
        # Изменяем параметр
        config2.llm_temperature = 0.8
        hash3 = calculate_config_hash(config2)
        
        # Хеш должен измениться
        assert hash1 != hash3