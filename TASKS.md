# План задач: Утилита для экспорта и описания закладок

Провайдер LLM по умолчанию: OpenRouter; источник закладок: экспортированный JSON-файл Chrome.

## Нумерованный список задач

1. Инициализация проекта и каркас директорий [COMPLETED]
   - Создать структуру: [`src/`](src), [`prompts/`](prompts), [`tests/`](tests)
   - Базовые файлы: [`src/__init__.py`](src/__init__.py), [`.gitignore`](.gitignore), [`README.md`](README.md), [`setup.py`](setup.py)

2. Подготовка зависимостей и конфигураций [COMPLETED]
   - Runtime: создать [`requirements.txt`](requirements.txt)
   - Dev/Test: создать [`requirements-dev.txt`](requirements-dev.txt) или описать в [`README.md`](README.md)
   - .env шаблон: [`.env.example`](.env.example); добавить исключение .env в [`.gitignore`](.gitignore)

3. Реализация моделей данных [COMPLETED]
   - [`src/models.py`](src/models.py)

4. Менеджер конфигурации [COMPLETED]
   - [`src/config.py`](src/config.py)

5. Парсер закладок Chrome (JSON) [COMPLETED]
    - [`src/parser.py`](src/parser.py)

6. Асинхронный загрузчик веб-контента [COMPLETED]
    - [`src/fetcher.py`](src/fetcher.py)

7. Генерация описаний через LLM (OpenRouter по умолчанию) [COMPLETED]
    - [`src/summarizer.py`](src/summarizer.py), файл промпта: [`prompts/summarize_prompt.txt`](prompts/summarize_prompt.txt)

8. Генерация Mermaid-диаграмм структуры [COMPLETED]
   - [`src/diagram.py`](src/diagram.py)

9. Запись файловой структуры и Markdown [COMPLETED]
   - [`src/writer.py`](src/writer.py)

10. Вспомогательные утилиты [COMPLETED]
    - [`src/utils.py`](src/utils.py)

11. Основной workflow и CLI [COMPLETED]
    - [`src/main.py`](src/main.py)

12. Логирование [COMPLETED]
    - Внедрить логирование в: [`src/config.py`](src/config.py), [`src/parser.py`](src/parser.py), [`src/fetcher.py`](src/fetcher.py), [`src/summarizer.py`](src/summarizer.py), [`src/diagram.py`](src/diagram.py), [`src/writer.py`](src/writer.py), [`src/main.py`](src/main.py)
    - Создан централизованный модуль [`src/logger.py`](src/logger.py) с системой логирования
    - Добавлены тесты для системы логирования: [`tests/test_logger.py`](tests/test_logger.py)
    - Обновлена документация в [`README.md`](README.md)

13. Инкрементальное выполнение и возобновление
    - Чекпоинты: [`bookmarks_export/progress.json`](bookmarks_export/progress.json)

14. Ограничение параллелизма и rate limit
    - Реализовать Semaphore и rate limiting в: [`src/fetcher.py`](src/fetcher.py), [`src/summarizer.py`](src/summarizer.py)

15. Подготовка тестовых данных
    - [`tests/data/`](tests/data)

16. Unit-тесты
    - [`tests/test_config.py`](tests/test_config.py), [`tests/test_parser.py`](tests/test_parser.py), [`tests/test_fetcher.py`](tests/test_fetcher.py), [`tests/test_summarizer.py`](tests/test_summarizer.py), [`tests/test_diagram.py`](tests/test_diagram.py), [`tests/test_writer.py`](tests/test_writer.py)
    - Статус: [`tests/test_fetcher.py`](tests/test_fetcher.py) — [COMPLETED] (5 passed)

17. Интеграционные тесты
    - [`tests/conftest.py`](tests/conftest.py) при необходимости

18. E2E-тест
    - Прогон реального набора из ~50 ссылок

19. Статический анализ и типизация
    - Описать конфиги и/или добавить [`pyproject.toml`](pyproject.toml); документация в [`README.md`](README.md)

20. Документация
    - Обновить [`README.md`](README.md)

## Зависимости

Runtime (requirements.txt):
- httpx>=0.25.0
- beautifulsoup4>=4.12.0
- openai>=1.3.0
- python-dotenv>=1.0.0
- aiofiles>=23.2.0
- pydantic>=2.0.0
- mermaid-py>=0.4.0

Dev/Test (requirements-dev.txt или README):
- pytest
- pytest-asyncio
- pytest-cov
- pytest-mock
- responses
- pylint
- flake8
- mypy
- black
- isort