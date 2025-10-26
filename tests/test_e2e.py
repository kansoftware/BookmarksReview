"""
E2E-тесты для полного цикла обработки закладок.
Проверяет весь workflow от загрузки JSON до создания Markdown-файлов.
"""
import asyncio
import json
import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from src.config import ConfigManager
from src.main import main
from src.progress import ProgressManager, calculate_config_hash


@pytest.fixture
def e2e_test_env():
    """Временная директория для E2E тестов."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_llm_responses():
    """Мок-ответы для LLM API."""
    return {
        "choices": [
            {
                "message": {
                    "content": """# Тестовая страница

## Основная тема
Это тестовое описание для веб-страницы.

## Ключевые моменты
- Тестовый пункт 1
- Тестовый пункт 2
- Тестовый пункт 3

## Вывод
Это сгенерированное описание для тестовой закладки."""
                }
            }
        ]
    }


@pytest.fixture
def mock_html_content():
    """Мок-HTML контент для веб-страниц."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Тестовая страница</title>
    </head>
    <body>
        <main>
            <h1>Тестовая страница</h1>
            <p>Это тестовый контент для проверки парсинга HTML.</p>
            <article>
                <h2>Основной контент</h2>
                <p>Здесь находится основная информация страницы.</p>
                <ul>
                    <li>Тестовый пункт 1</li>
                    <li>Тестовый пункт 2</li>
                    <li>Тестовый пункт 3</li>
                </ul>
            </article>
        </main>
    </body>
    </html>
    """


class TestE2E:
    """E2E тесты для полного цикла обработки."""

    @pytest.mark.asyncio
    async def test_full_workflow_with_mock_server(self, e2e_test_env, mock_llm_responses, mock_html_content):
        """Тест полного workflow с мок-сервером."""
        # Подготовка тестовых данных
        bookmarks_file = Path(e2e_test_env) / "test_bookmarks.json"
        output_dir = Path(e2e_test_env) / "output"
        
        # Копируем тестовый файл закладок
        shutil.copy("tests/data/bookmarks/e2e_test_bookmarks.json", bookmarks_file)
        
        # Создаем .env файл для теста
        env_file = Path(e2e_test_env) / ".env"
        with open(env_file, "w") as f:
            f.write(f"""
LLM_API_KEY=test-key
LLM_BASE_URL=http://localhost:8888/v1
LLM_MODEL=gpt-4o-mini
LLM_MAX_TOKENS=1000
LLM_TEMPERATURE=0.7
LLM_RATE_LIMIT=3
FETCH_TIMEOUT=30
FETCH_MAX_CONCURRENT=10
FETCH_MAX_SIZE_MB=5
FETCH_RETRY_ATTEMPTS=3
FETCH_RETRY_DELAY=1.5
OUTPUT_DIR={output_dir}
MARKDOWN_INCLUDE_METADATA=true
GENERATE_MERMAID_DIAGRAM=true
PROMPT_FILE=./prompts/summarize_prompt.txt
LOG_LEVEL=INFO
LOG_FILE={Path(e2e_test_env) / "test.log"}
""")
        
        # Мокаем HTTP запросы для загрузки контента
        with patch('httpx.AsyncClient.get') as mock_get, \
             patch('asyncio.sleep') as mock_sleep, \
             patch('src.summarizer.ContentSummarizer.generate_summary') as mock_generate_summary:

            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.text = mock_html_content
            mock_response.headers = {"content-type": "text/html"}
            mock_response.request = AsyncMock()  # Для httpx.HTTPStatusError
            mock_get.return_value = mock_response

            # Мокаем генерацию описаний
            mock_generate_summary.return_value = mock_llm_responses["choices"][0]["message"]["content"]

            # Запускаем основной workflow
            try:
                # Мокаем sys.argv для передачи аргументов
                with patch('sys.argv', ['main.py', str(bookmarks_file)]):
                    # Вызываем process_bookmarks напрямую, избегая asyncio.run()
                    from src.main import process_bookmarks, parse_arguments
                    args = parse_arguments()
                    config_manager = ConfigManager(env_path=str(env_file))
                    config = config_manager.get()
                    from src.parser import BookmarkParser
                    parser = BookmarkParser()
                    data = parser.load_json(str(bookmarks_file))
                    root_folder = parser.parse_bookmarks(data)
                    await process_bookmarks(args, config, root_folder, str(bookmarks_file))
            except SystemExit:
                # main() вызывает sys.exit(0) при успешном завершении
                pass
        
        # Проверяем результаты
        assert output_dir.exists(), "Директория вывода должна быть создана"
        
        # Проверяем наличие Mermaid диаграммы
        diagram_file = output_dir / "bookmarks_structure.md"
        assert diagram_file.exists(), "Mermaid диаграмма должна быть создана"
        
        # Проверяем наличие файлов прогресса
        progress_file = output_dir / "progress.json"
        assert progress_file.exists(), "Файл прогресса должен быть создан"
        
        # Проверяем созданную структуру папок
        bookmark_bar_dir = output_dir / "Root" / "Bookmark Bar"
        web_frameworks_dir = bookmark_bar_dir / "Web Frameworks"
        assert web_frameworks_dir.exists(), "Папка 'Web Frameworks' должна быть создана"
        
        # Проверяем наличие Markdown файлов
        markdown_files = list(output_dir.rglob("*.md"))
        assert len(markdown_files) > 0, "Должны быть созданы Markdown файлы"
        
        # Проверяем содержимое одного из Markdown файлов
        fastapi_file = web_frameworks_dir / "FastAPI.md"
        if fastapi_file.exists():
            with open(fastapi_file, "r", encoding="utf-8") as f:
                content = f.read()
                assert "# FastAPI" in content, "Заголовок закладки должен быть в содержимом"
                assert "# Тестовая страница" in content, "Описание должно быть в содержимом"
                assert "## Основная тема" in content, "Структура описания должна быть сохранена"
        
        # Проверяем прогресс
        with open(progress_file, "r", encoding="utf-8") as f:
            progress_data = json.load(f)
            assert "processed_urls" in progress_data, "Прогресс должен содержать обработанные закладки"
            assert "config_hash" in progress_data, "Прогресс должен содержать хеш конфигурации"

    @pytest.mark.asyncio
    async def test_resume_functionality(self, e2e_test_env, mock_llm_responses, mock_html_content):
        """Тест функциональности возобновления обработки."""
        # Подготовка тестовых данных
        bookmarks_file = Path(e2e_test_env) / "test_bookmarks.json"
        output_dir = Path(e2e_test_env) / "output"
        
        # Копируем тестовый файл закладок
        import os
        source_file = os.path.join(os.path.dirname(__file__), "data", "bookmarks", "e2e_test_bookmarks.json")
        shutil.copy(source_file, bookmarks_file)
        
        # Создаем .env файл для теста
        env_file = Path(e2e_test_env) / ".env"
        with open(env_file, "w") as f:
            f.write(f"""
LLM_API_KEY=test-key
LLM_BASE_URL=http://localhost:8888/v1
LLM_MODEL=gpt-4o-mini
LLM_MAX_TOKENS=1000
LLM_TEMPERATURE=0.7
LLM_RATE_LIMIT=3
FETCH_TIMEOUT=30
FETCH_MAX_CONCURRENT=10
FETCH_MAX_SIZE_MB=5
FETCH_RETRY_ATTEMPTS=3
FETCH_RETRY_DELAY=1.5
OUTPUT_DIR={output_dir}
MARKDOWN_INCLUDE_METADATA=true
GENERATE_MERMAID_DIAGRAM=true
PROMPT_FILE=./prompts/summarize_prompt.txt
LOG_LEVEL=INFO
LOG_FILE={Path(e2e_test_env) / "test.log"}
""")
        
        # Создаем частичный прогресс
        output_dir.mkdir(parents=True, exist_ok=True)
        progress_file = output_dir / "progress.json"

        # Создаем ConfigManager для получения хеша конфигурации
        # Не меняем рабочую директорию, используем абсолютные пути
        config_manager = ConfigManager(env_path=str(env_file))
        config = config_manager.get()
        
        config_hash = calculate_config_hash(config)
        progress_manager = ProgressManager(
            output_dir=str(output_dir),
            bookmarks_file=str(bookmarks_file),
            config_hash=config_hash
        )
        
        # Создаем частичный прогресс с несколькими обработанными закладками
        partial_progress = {
            "version": "1.0",
            "timestamp": "2023-01-01T00:05:00",
            "bookmarks_file": str(bookmarks_file),
            "config_hash": config_hash,
            "processed_urls": [
                {
                    "url": "https://docs.python.org/3/",
                    "title": "Python Documentation",
                    "processed_at": "2023-01-01T00:01:00",
                    "file_path": str(output_dir / "Python_Documentation.md"),
                    "folder_path": ["Root", "Bookmark Bar"]
                },
                {
                    "url": "https://github.com",
                    "title": "GitHub",
                    "processed_at": "2023-01-01T00:02:00",
                    "file_path": str(output_dir / "GitHub.md"),
                    "folder_path": ["Root", "Bookmark Bar"]
                }
            ],
            "failed_urls": [],
            "current_position": {
                "folder_path": ["Root", "Bookmark Bar"],
                "bookmark_index": 2,
                "total_in_folder": 10
            },
            "statistics": {
                "total_bookmarks": 50,
                "processed_count": 2,
                "failed_count": 0,
                "skipped_count": 0,
                "start_time": "2023-01-01T00:00:00",
                "last_update": "2023-01-01T00:05:00"
            }
        }
        
        with open(progress_file, "w", encoding="utf-8") as f:
            json.dump(partial_progress, f, indent=2)
        
        # Мокаем HTTP запросы
        with patch('httpx.AsyncClient.get') as mock_get, \
             patch('asyncio.sleep') as mock_sleep, \
             patch('src.summarizer.ContentSummarizer.generate_summary') as mock_generate_summary:

            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.text = mock_html_content
            mock_response.headers = {"content-type": "text/html"}
            mock_response.request = AsyncMock()
            mock_get.return_value = mock_response

            mock_generate_summary.return_value = mock_llm_responses["choices"][0]["message"]["content"]

            # Запускаем с флагом --resume
            try:
                # Мокаем sys.argv для передачи аргументов
                with patch('sys.argv', ['main.py', str(bookmarks_file), '--resume']):
                    # Вызываем process_bookmarks напрямую, избегая asyncio.run()
                    from src.main import process_bookmarks, parse_arguments
                    args = parse_arguments()
                    config_manager = ConfigManager(env_path=str(env_file))
                    config = config_manager.get()
                    from src.parser import BookmarkParser
                    parser = BookmarkParser()
                    data = parser.load_json(str(bookmarks_file))
                    root_folder = parser.parse_bookmarks(data)
                    await process_bookmarks(args, config, root_folder, str(bookmarks_file))
            except SystemExit:
                pass
        
        # Проверяем, что обработка продолжилась с учетом прогресса
        with open(progress_file, "r", encoding="utf-8") as f:
            final_progress = json.load(f)
            
        # Должно быть обработано больше закладок, чем в частичном прогрессе
        assert len(final_progress["processed_urls"]) > len(partial_progress["processed_urls"]), \
            "При возобновлении должны быть обработаны новые закладки"

        # Проверяем, что ранее обработанные закладки не были обработаны повторно
        processed_urls = {item["url"] for item in final_progress["processed_urls"]}
        assert "https://docs.python.org/3/" in processed_urls, "Ранее обработанная закладка должна остаться в прогрессе"
        assert "https://github.com" in processed_urls, "Ранее обработанная закладка должна остаться в прогрессе"

    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, e2e_test_env):
        """Тест обработки ошибок и восстановления."""
        # Подготовка тестовых данных
        bookmarks_file = Path(e2e_test_env) / "test_bookmarks.json"
        output_dir = Path(e2e_test_env) / "output"
        
        # Копируем тестовый файл закладок
        shutil.copy("tests/data/bookmarks/e2e_test_bookmarks.json", bookmarks_file)
        
        # Создаем .env файл для теста
        env_file = Path(e2e_test_env) / ".env"
        with open(env_file, "w") as f:
            f.write(f"""
LLM_API_KEY=test-key
LLM_BASE_URL=http://localhost:8888/v1
LLM_MODEL=gpt-4o-mini
LLM_MAX_TOKENS=1000
LLM_TEMPERATURE=0.7
LLM_RATE_LIMIT=3
FETCH_TIMEOUT=30
FETCH_MAX_CONCURRENT=10
FETCH_MAX_SIZE_MB=5
FETCH_RETRY_ATTEMPTS=3
FETCH_RETRY_DELAY=1.5
OUTPUT_DIR={output_dir}
MARKDOWN_INCLUDE_METADATA=true
GENERATE_MERMAID_DIAGRAM=true
PROMPT_FILE=./prompts/summarize_prompt.txt
LOG_LEVEL=INFO
LOG_FILE={Path(e2e_test_env) / "test.log"}
""")
        
        # Мокаем HTTP запросы с ошибками для некоторых URL
        async def mock_get(url, **kwargs):
            mock_response = AsyncMock()
            if "github.com" in str(url):
                mock_response.status_code = 404
                mock_response.text = "Not Found"
            else:
                mock_response.status_code = 200
                mock_response.text = "<html><body><h1>Test</h1></body></html>"
                mock_response.headers = {"content-type": "text/html"}
            return mock_response
        
        # Мокаем LLM API
        async def mock_llm_create(**kwargs):
            mock_completion = AsyncMock()
            mock_completion.choices = [
                {
                    "message": {
                        "content": "Test summary"
                    }
                }
            ]
            return mock_completion
        
        # Запускаем с моками
        async def run_test():
            with patch('httpx.AsyncClient.get', side_effect=mock_get), \
                 patch('asyncio.sleep') as mock_sleep, \
                 patch('src.summarizer.ContentSummarizer.generate_summary') as mock_generate_summary:

                mock_generate_summary.return_value = "Test summary"

                try:
                    # Мокаем sys.argv для передачи аргументов
                    with patch('sys.argv', ['main.py', str(bookmarks_file)]):
                        # Вызываем process_bookmarks напрямую, избегая asyncio.run()
                        from src.main import process_bookmarks, parse_arguments
                        args = parse_arguments()
                        config_manager = ConfigManager(env_path=str(env_file))
                        config = config_manager.get()
                        from src.parser import BookmarkParser
                        parser = BookmarkParser()
                        data = parser.load_json(str(bookmarks_file))
                        root_folder = parser.parse_bookmarks(data)
                        await process_bookmarks(args, config, root_folder, str(bookmarks_file))
                except SystemExit:
                    pass
        
        await run_test()
        
        # Проверяем, что обработка продолжилась несмотря на ошибки
        assert output_dir.exists(), "Директория вывода должна быть создана"
        
        # Проверяем прогресс
        progress_file = output_dir / "progress.json"
        if progress_file.exists():
            with open(progress_file, "r", encoding="utf-8") as f:
                progress_data = json.load(f)
                
            # Должны быть как успешные, так и неуспешные обработки
            processed_urls = progress_data.get("processed_urls", [])
            failed_urls = progress_data.get("failed_urls", [])
            assert len(processed_urls) > 0, "Должны быть обработаны некоторые закладки"
            assert len(failed_urls) > 0, "Должны быть зафиксированы ошибки обработки"