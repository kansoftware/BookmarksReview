# Memory Bank: BookmarksReview

Краткое описание назначения проекта
- Консольная утилита на Python для обработки экспортированных закладок Chrome: импорт JSON, загрузка HTML по URL, извлечение текста, генерация кратких описаний в Markdown через LLM-совместимый API, построение Mermaid-диаграммы, сохранение результатов в файловую структуру.

Основные компоненты/модули и взаимодействие
- Конфигурация: [`src/config.py`](src/config.py) — загрузка и валидация параметров из .env, настройка логирования.
- Модели данных: [`src/models.py`](src/models.py) — dataclass-модели Bookmark, BookmarkFolder, ProcessedPage.
- Парсер закладок: [`src/parser.py`](src/parser.py) — парсинг JSON Chrome, построение дерева папок/закладок.
- Загрузчик контента: [`src/fetcher.py`](src/fetcher.py) — асинхронная загрузка HTML (httpx), очистка и извлечение текста (BeautifulSoup), retry/timeout/лимит размера.
- Генератор описаний: [`src/summarizer.py`](src/summarizer.py) — AsyncOpenAI/OpenRouter, шаблон промпта, rate limiting для LLM.
- Генератор диаграмм: [`src/diagram.py`](src/diagram.py) — Mermaid-представление структуры закладок.
- Запись Markdown: [`src/writer.py`](src/writer.py) — создание директорий, метаданные (YAML), генерация и запись файлов.
- Вспомогательные утилиты: [`src/utils.py`](src/utils.py) — переиспользуемые функции для путей, текста, дат, валидации, ошибок, хеширования, прогресса.
- Основной workflow/CLI: [`src/main.py`](src/main.py) — оркестрация: Config → Parser → Fetcher → Summarizer → Writer (+Diagram).
- Промпт для LLM: [`prompts/summarize_prompt.txt`](prompts/summarize_prompt.txt)

Поток данных (ETL-пайплайн)
- .env → ConfigManager → JSON Bookmarks → BookmarkParser → ContentFetcher → ContentSummarizer → FileSystemWriter → Markdown
- Параллельно: BookmarkParser → DiagramGenerator → Mermaid-диаграмма

Используемый технологический стек
- Язык: Python 3.9+
- HTTP: httpx (асинхронный клиент)
- HTML-парсинг: BeautifulSoup4
- LLM: openai.AsyncOpenAI (совместим с OpenRouter)
- Конфигурация: python-dotenv
- Асинхронность: asyncio
- Файловые операции: aiofiles (план)
- Валидация: pydantic (план)
- Диаграммы: mermaid-py (план)
- Тестирование/статический анализ: pytest, pytest-asyncio, pytest-cov, pytest-mock, responses, mypy, ruff, black, isort, flake8, pylint

Архитектурные паттерны
- Монолитная CLI-утилита с модульной архитектурой.
- ETL-конвейер: парсинг → извлечение → обогащение (LLM) → запись.
- Разделение ответственности (SRP): отдельные компоненты для конфигурации, парсинга, загрузки, суммаризации, диаграмм, записи.
- Асинхронная обработка I/O с ограничением параллелизма и повторными попытками.
- Использование контекстного менеджера для HTTP-сессии (httpx.AsyncClient).
- Типизация и dataclass для моделей домена.

Ключевые зависимости (runtime)
- [`requirements.txt`](requirements.txt:1) httpx>=0.25.0
- [`requirements.txt`](requirements.txt:2) beautifulsoup4>=4.12.0
- [`requirements.txt`](requirements.txt:3) openai>=1.3.0
- [`requirements.txt`](requirements.txt:4) python-dotenv>=1.0.0
- [`requirements.txt`](requirements.txt:5) aiofiles>=23.2.0
- [`requirements.txt`](requirements.txt:6) pydantic>=2.0.0
- [`requirements.txt`](requirements.txt:7) mermaid-py>=0.4.0

Ключевые зависимости (dev/test)
- [`requirements-dev.txt`](requirements-dev.txt:1) pytest
- [`requirements-dev.txt`](requirements-dev.txt:2) pytest-asyncio
- [`requirements-dev.txt`](requirements-dev.txt:3) pytest-cov
- [`requirements-dev.txt`](requirements-dev.txt:4) pytest-mock
- [`requirements-dev.txt`](requirements-dev.txt:5) responses
- [`requirements-dev.txt`](requirements-dev.txt:6) pylint
- [`requirements-dev.txt`](requirements-dev.txt:7) flake8
- [`requirements-dev.txt`](requirements-dev.txt:8) mypy
- [`requirements-dev.txt`](requirements-dev.txt:9) black
- [`requirements-dev.txt`](requirements-dev.txt:10) isort
- [`requirements-dev.txt`](requirements-dev.txt:11) ruff

Важные замечания по текущему состоянию
- .env.example обновлен и теперь полностью соответствует техническому заданию и ожидаемым ключам из конфигурации.
- В парсере корректно преобразован Chrome timestamp (микросекунды от 1601-01-01) к Unix времени.
- Исправлена проблема с циклическим импортом между src/config.py и src/logger.py через использование TYPE_CHECKING.

Выполненные задачи (статус)
- ✅ Задача 1: Инициализация проекта и каркас директорий
- ✅ Задача 2: Подготовка зависимостей и конфигураций
- ✅ Задача 3: Реализация моделей данных ([`src/models.py`](src/models.py))
- ✅ Задача 4: Менеджер конфигурации ([`src/config.py`](src/config.py))
- ✅ Задача 5: Парсер закладок Chrome ([`src/parser.py`](src/parser.py))
- ✅ Задача 6: Асинхронный загрузчик веб-контента ([`src/fetcher.py`](src/fetcher.py))
- ✅ Задача 7: Генерация описаний через LLM ([`src/summarizer.py`](src/summarizer.py))
- ✅ Задача 8: Генерация Mermaid-диаграмм структуры ([`src/diagram.py`](src/diagram.py))
- ✅ Задача 9: Запись файловой структуры и Markdown ([`src/writer.py`](src/writer.py))
- ✅ Задача 10: Вспомогательные утилиты ([`src/utils.py`](src/utils.py))
- ✅ Задача 11: Основной workflow и CLI ([`src/main.py`](src/main.py))
- ✅ Задача 12: Логирование ([`src/logger.py`](src/logger.py))
  - Создан централизованный модуль логирования с LoggerManager
  - Внедрено логирование во все модули проекта
  - Добавлены тесты для системы логирования ([`tests/test_logger.py`](tests/test_logger.py))
  - Обновлена документация в README.md
  - Формат логов: YYYY-MM-DD HH:MM:SS - module_name - LEVEL - Сообщение на русском
  - Уровни логирования: DEBUG, INFO, WARNING, ERROR, CRITICAL
  - Ротация логов: 10 МБ, 5 резервных копий
  - Удобные функции: log_function_call(), log_performance(), log_error_with_context()
- ✅ Обновление .env.example в соответствии с ТЗ
  - Файл [.env.example](.env.example) полностью обновлен в соответствии с техническим заданием
  - Добавлены все необходимые параметры: LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_MAX_TOKENS, LLM_TEMPERATURE, LLM_RATE_LIMIT
  - Добавлены параметры загрузки контента: FETCH_TIMEOUT, FETCH_MAX_CONCURRENT, FETCH_MAX_SIZE_MB, FETCH_RETRY_ATTEMPTS, FETCH_RETRY_DELAY
  - Добавлены параметры вывода: OUTPUT_DIR, MARKDOWN_INCLUDE_METADATA, GENERATE_MERMAID_DIAGRAM
  - Добавлены параметры логирования: LOG_LEVEL, LOG_FILE
  - Добавлены примеры конфигурации для разных провайдеров (OpenRouter, OpenAI, Anthropic)
- ✅ Обновление документации в README.md
  - Расширен раздел "Настройка" с подробным описанием всех параметров
  - Добавлены примеры конфигурации для различных LLM провайдеров
  - Указаны значения по умолчанию для всех параметров
- ✅ Исправление циклического импорта в src/logger.py
  - Использован TYPE_CHECKING для разрешения циклической зависимости между src/config.py и src/logger.py
  - Обновлены аннотации типов для корректной работы с импортами

Тестовое покрытие
- [`tests/test_config.py`](tests/test_config.py) — тесты конфигурации
- [`tests/test_parser.py`](tests/test_parser.py) — тесты парсера
- [`tests/test_fetcher.py`](tests/test_fetcher.py) — тесты загрузчика (5 passed)
- [`tests/test_summarizer.py`](tests/test_summarizer.py) — тесты суммаризатора
- [`tests/test_diagram.py`](tests/test_diagram.py) — тесты диаграмм (6 passed)
- [`tests/test_writer.py`](tests/test_writer.py) — тесты файлового писателя (18 passed)
- [`tests/test_utils.py`](tests/test_utils.py) — тесты утилит (51 passed)
- [`tests/test_main.py`](tests/test_main.py) — тесты основного модуля (10 passed, 1 skipped)