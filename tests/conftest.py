"""
Общие фикстуры для интеграционных тестов.
Содержит вспомогательные функции и фикстуры для создания тестовых данных.
"""
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock

import pytest

from src.models import BookmarkFolder, Bookmark
from src.config import ConfigManager


@pytest.fixture
def temp_dir():
    """Создает временную директорию для тестов."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_config(temp_dir):
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
def config_manager(sample_config):
    """Создает менеджер конфигурации с тестовыми параметрами."""
    return ConfigManager(sample_config)


@pytest.fixture
def config(config_manager):
    """Возвращает объект конфигурации."""
    return config_manager.get()


@pytest.fixture
def simple_bookmarks_data():
    """Возвращает простую структуру закладок для тестов."""
    return {
        "checksum": "test_checksum",
        "roots": {
            "bookmark_bar": {
                "children": [
                    {
                        "name": "Test Bookmark 1",
                        "type": "url",
                        "url": "https://example1.com",
                        "date_added": "13267383115384687"
                    },
                    {
                        "name": "Test Bookmark 2",
                        "type": "url",
                        "url": "https://example2.com",
                        "date_added": "13267383115384688"
                    }
                ]
            }
        },
        "version": 1
    }


@pytest.fixture
def nested_bookmarks_data():
    """Возвращает вложенную структуру закладок для тестов."""
    return {
        "checksum": "test_checksum_nested",
        "roots": {
            "bookmark_bar": {
                "children": [
                    {
                        "name": "Folder 1",
                        "type": "folder",
                        "children": [
                            {
                                "name": "Subfolder 1.1",
                                "type": "folder",
                                "children": [
                                    {
                                        "name": "Deep Bookmark 1",
                                        "type": "url",
                                        "url": "https://deep1.example.com",
                                        "date_added": "13267383115384689"
                                    }
                                ]
                            },
                            {
                                "name": "Bookmark 1.1",
                                "type": "url",
                                "url": "https://bookmark11.example.com",
                                "date_added": "13267383115384690"
                            }
                        ]
                    },
                    {
                        "name": "Folder 2",
                        "type": "folder",
                        "children": [
                            {
                                "name": "Bookmark 2.1",
                                "type": "url",
                                "url": "https://bookmark21.example.com",
                                "date_added": "13267383115384691"
                            }
                        ]
                    }
                ]
            }
        },
        "version": 1
    }


@pytest.fixture
def simple_bookmarks_file(temp_dir, simple_bookmarks_data):
    """Создает тестовый файл с простыми закладками."""
    bookmarks_file = temp_dir / "simple_bookmarks.json"
    with open(bookmarks_file, 'w', encoding='utf-8') as f:
        json.dump(simple_bookmarks_data, f)
    
    return str(bookmarks_file)


@pytest.fixture
def nested_bookmarks_file(temp_dir, nested_bookmarks_data):
    """Создает тестовый файл с вложенными закладками."""
    bookmarks_file = temp_dir / "nested_bookmarks.json"
    with open(bookmarks_file, 'w', encoding='utf-8') as f:
        json.dump(nested_bookmarks_data, f)
    
    return str(bookmarks_file)


@pytest.fixture
def mock_args():
    """Создает мок аргументов командной строки."""
    args = Mock()
    args.resume = False
    args.dry_run = True  # Используем dry-run для тестов
    args.no_diagram = True
    return args


@pytest.fixture
def mock_llm_response():
    """Возвращает мок-ответ от LLM API."""
    return {
        "choices": [
            {
                "message": {
                    "content": """## Основная тема

Это тестовая страница, содержащая основную информацию о теме.

## Ключевые моменты

- Первый важный момент
- Второй важный момент
- Третий важный момент

## Вывод

На основе представленной информации можно сделать вывод о значимости данной темы."""
                }
            }
        ]
    }


@pytest.fixture
def sample_html_content():
    """Возвращает пример HTML-содержимого для тестов."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Page</title>
    </head>
    <body>
        <header>
            <h1>Test Page Title</h1>
        </header>
        <main>
            <article>
                <h2>Main Content</h2>
                <p>This is a test paragraph with some important information.</p>
                <p>Another paragraph with additional details.</p>
                <ul>
                    <li>First point</li>
                    <li>Second point</li>
                    <li>Third point</li>
                </ul>
            </article>
        </main>
        <footer>
            <p>Footer information</p>
        </footer>
    </body>
    </html>
    """


@pytest.fixture
def mock_http_client(sample_html_content):
    """Создает мок HTTP-клиента с тестовыми ответами."""
    from unittest.mock import AsyncMock
    
    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.text = sample_html_content
    mock_response.status_code = 200
    mock_client.get.return_value = mock_response
    
    return mock_client


def create_test_bookmark(title="Test Bookmark", url="https://example.com"):
    """Создает тестовую закладку."""
    return Bookmark(
        title=title,
        url=url,
        date_added=datetime.now()
    )


def create_test_folder(name="Test Folder", bookmarks=None, children=None):
    """Создает тестовую папку с закладками."""
    if bookmarks is None:
        bookmarks = []
    if children is None:
        children = []
    
    return BookmarkFolder(
        name=name,
        bookmarks=bookmarks,
        children=children
    )


def create_test_processed_page(url="https://example.com", title="Test Page", summary="Test summary"):
    """Создает тестовую обработанную страницу."""
    from src.models import ProcessedPage
    
    return ProcessedPage(
        url=url,
        title=title,
        summary=summary,
        fetch_date=datetime.now(),
        status='success'
    )