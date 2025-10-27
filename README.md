# Утилита для экспорта и описания закладок браузера

## Описание
Консольная утилита на Python для автоматической обработки закладок из браузера Chrome. Утилита:
- Импортирует JSON-файл закладок Chrome
- Извлекает содержимое веб-страниц по сохраненным ссылкам
- Генерирует краткие описания страниц в Markdown формате с использованием OpenAI-совместимого API
- Создает Mermaid-диаграммы для визуализации структуры закладок
- Сохраняет результаты в файловую структуру, соответствующую иерархии исходных закладок

## Требования
- Python 3.9+
- Зависимости: см. `requirements.txt`

## Установка
```bash
pip install -r requirements.txt
```

## Настройка

Создайте файл `.env` на основе `.env.example` и настройте параметры:

### Обязательные параметры
- `LLM_API_KEY` — API-ключ для LLM провайдера
- `PROMPT_FILE` — путь к файлу с промптом (по умолчанию `./prompts/summarize_prompt.txt`)

### Конфигурация LLM API
- `LLM_BASE_URL` — URL API (по умолчанию `https://api.openai.com/v1`)
- `LLM_MODEL` — название модели (по умолчанию `gpt-4o-mini`)
- `LLM_MAX_TOKENS` — максимальное количество токенов в ответе (по умолчанию 1000)
- `LLM_TEMPERATURE` — температура генерации от 0.0 до 1.0 (по умолчанию 0.7)
- `LLM_RATE_LIMIT` — количество запросов в минуту (по умолчанию 3)

### Примеры конфигурации для разных провайдеров

#### OpenRouter
```env
LLM_API_KEY=sk-or-v1-your-key-here
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=openai/gpt-4o-mini
```

#### OpenAI
```env
LLM_API_KEY=sk-your-openai-key-here
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
```

#### Anthropic Claude (через OpenRouter)
```env
LLM_API_KEY=sk-or-v1-your-key-here
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=anthropic/claude-3-haiku
```

### Настройки загрузки контента
- `FETCH_TIMEOUT` — таймаут запроса в секундах (по умолчанию 30)
- `FETCH_MAX_CONCURRENT` — максимальное количество параллельных запросов (по умолчанию 10)
- `FETCH_MAX_SIZE_MB` — максимальный размер страницы в МБ (по умолчанию 5)
- `FETCH_RETRY_ATTEMPTS` — количество попыток при ошибке (по умолчанию 3)
- `FETCH_RETRY_DELAY` — задержка между попытками в секундах (по умолчанию 1.5)
- `FETCH_MAX_REDIRECTS` — максимальное количество редиректов при загрузке страницы (по умолчанию 5)

### Настройки вывода
- `OUTPUT_DIR` — директория для сохранения результатов (по умолчанию `./bookmarks_export`)
- `MARKDOWN_INCLUDE_METADATA` — включать метаданные в Markdown файлы (true/false, по умолчанию true)
- `GENERATE_MERMAID_DIAGRAM` — генерировать Mermaid-диаграмму (true/false, по умолчанию true)

### Настройки логирования
- `LOG_LEVEL` — уровень логирования (DEBUG, INFO, WARNING, ERROR, по умолчанию INFO)
- `LOG_FILE` — путь к файлу лога (по умолчанию `./bookmarks_export.log`)

## Использование

### Базовый запуск
```bash
python -m src.main path/to/bookmarks.json
```

### Дополнительные опции
```bash
# Указать кастомный .env файл
python -m src.main bookmarks.json --config custom.env

# Изменить директорию вывода
python -m src.main bookmarks.json --output-dir ./my_export

# Возобновить прерванную обработку
python -m src.main bookmarks.json --resume

# Только парсинг без обработки контента
python -m src.main bookmarks.json --dry-run

# Подробное логирование
python -m src.main bookmarks.json --verbose

# Не генерировать Mermaid-диаграмму
python -m src.main bookmarks.json --no-diagram

# Ограничить количество параллельных запросов
python -m src.main bookmarks.json --max-concurrent 5

# Перепроверить только URL с ошибками из предыдущего сеанса
python -m src.main bookmarks.json --check-error

# Перепроверить только URL с ошибками с указанием файла прогресса
python -m src.main bookmarks.json --check-error --progress-file ./custom_progress.json
```

## Структура проекта
- `src/` — исходный код
  - `main.py` — основной workflow и CLI
  - `config.py` — управление конфигурацией
  - `models.py` — модели данных
  - `parser.py` — парсер JSON закладок
  - `fetcher.py` — загрузчик веб-контента
  - `summarizer.py` — генератор описаний
  - `diagram.py` — генератор Mermaid-диаграмм
  - `writer.py` — запись Markdown-файлов
  - `logger.py` — централизованная система логирования
  - `progress.py` — менеджер прогресса для инкрементального выполнения
  - `utils.py` — вспомогательные утилиты
- `prompts/` — файлы промптов
- `tests/` — тесты
  - `data/` — тестовые данные для unit-тестов и интеграционных тестов
    - `bookmarks/` — JSON-файлы закладок Chrome
    - `html/` — HTML-файлы для тестирования парсинга
    - `responses/` — мок-ответы LLM API
- `.kilocode/` — документация проекта

## Тестирование

Проект имеет полную систему тестирования с высоким покрытием кода.

### Запуск тестов

```bash
# Запуск всех тестов
python -m pytest tests/

# Запуск с покрытием
python -m pytest tests/ --cov=src --cov-report=term-missing

# Запуск только интеграционных тестов
python -m pytest tests/ -k "integration"

# Запуск тестов конкретного модуля
python -m pytest tests/test_config.py -v
```

### Покрытие кода

- **Общее покрытие**: 90% (превышает цель 80%)
- **Unit-тесты**: 168 тестов, покрывают все основные компоненты
- **Интеграционные тесты**: 51 тест, проверяют взаимодействие компонентов

#### Покрытие по модулям:
- `config.py` — 96%
- `parser.py` — 94%
- `fetcher.py` — 84%
- `summarizer.py` — 93%
- `diagram.py` — 82%
- `writer.py` — 94%
- `utils.py` — 96%
- `main.py` — 82%
- `logger.py` — 95%
- `progress.py` — 88%

### Типы тестов

#### Unit-тесты
Изолированные тесты отдельных функций и классов с использованием моков для зависимостей.

#### Интеграционные тесты
Тесты взаимодействия между компонентами:
- **test_integration.py** — основной workflow обработки закладок
- **test_error_handling_integration.py** — обработка ошибок и восстановление
- **test_filesystem_integration.py** — создание файловой структуры
- **test_diagram_integration.py** — генерация Mermaid-диаграмм
- **test_resume_integration.py** — инкрементальное выполнение и возобновление
- **test_mock_server.py** — имитация LLM API

### Тестовые данные

В директории `tests/data/` находятся тестовые данные:
- JSON-файлы закладок различных структур (простые, вложенные, пустые)
- HTML-файлы для тестирования парсинга контента
- Мок-ответы LLM API для различных сценариев

### Качество кода

Проект использует современные инструменты статического анализа и форматирования:

#### Инструменты статического анализа
- **mypy** — строгая проверка типов с полным покрытием
- **ruff** — высокопроизводительный линтер и форматтер (замена flake8, pylint, pyupgrade)
- **black** — автоматическое форматирование кода (88 символов в строке)
- **isort** — сортировка импортов по стандартам

#### Запуск инструментов качества кода

```bash
# Проверка типов
python -m mypy src/ --config-file pyproject.toml

# Линтинг и исправление ошибок
python -m ruff check src/ --fix --config pyproject.toml

# Форматирование кода
python -m black src/ --config pyproject.toml

# Сортировка импортов
python -m isort src/ --settings-path pyproject.toml

# Запуск всех инструментов качества
python -m ruff check src/ --fix --config pyproject.toml && \
python -m black src/ --config pyproject.toml && \
python -m isort src/ --settings-path pyproject.toml && \
python -m mypy src/ --config-file pyproject.toml
```

#### Конфигурация инструментов

Все настройки инструментов находятся в `pyproject.toml`:

```toml
[tool.mypy]
python_version = "3.9"
strict = true
warn_return_any = true
warn_unused_configs = true

[tool.ruff]
line-length = 88
target-version = "py39"

[tool.ruff.lint]
select = ["E", "F", "W", "C90", "I", "N", "UP", "YTT", "S", "BLE", "FBT", "B", "A", "COM", "C4", "DTZ", "T10", "DJ", "EM", "EXE", "FA", "ISC", "ICN", "G", "INP", "PIE", "T20", "PYI", "PT", "Q", "RSE", "RET", "SLF", "SLOT", "SIM", "TID", "TCH", "INT", "ARG", "PTH", "ERA", "PD", "PGH", "PL", "TRY", "FLY", "NPY", "AIR", "PERF", "FURB", "LOG", "RUF"]
ignore = ["S101", "S104", "COM812", "ISC001"]

[tool.black]
line-length = 88
target-version = ['py39']

[tool.isort]
profile = "black"
line_length = 88
```

#### Стандарты кодирования

- **Типизация**: 100% типизированный код с использованием mypy strict mode
- **Форматирование**: Black с длиной строки 88 символов
- **Импорты**: Сортировка через isort с профилем black
- **Линтинг**: Ruff с расширенным набором правил (более 60 категорий проверок)
- **Документация**: Docstrings на русском языке для всех публичных методов

## Особенности

### Асинхронная обработка
- Параллельная загрузка до 10 страниц одновременно (настраивается через FETCH_MAX_CONCURRENT)
- Rate limiting для HTTP-запросов и LLM API
- Graceful degradation при ошибках
- Semaphore для контроля параллелизма

### Управление прогрессом
- Сохранение прогресса в `bookmarks_export/progress.json`
- Возможность возобновления с `--resume`
- Перепроверка только неудачных URL с `--check-error`
- Периодическое сохранение прогресса во время обработки
- Отслеживание обработанных и неудачных URL
- Сохранение текущей позиции для точного возобновления
- Проверка совместимости конфигурации через хеш
- Возможность указания файла прогресса с `--progress-file`

### Визуализация структуры
- Автоматическая генерация Mermaid-диаграмм
- Отображение иерархии папок и закладок
- Ограничение размера диаграммы для больших наборов

### Гибкая конфигурация
- Все параметры через .env файл
- Поддержка любого OpenAI-совместимого API
- Настраиваемые лимиты и таймауты

### Централизованное логирование
- Единая система логирования для всех модулей
- Настраиваемые уровни логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Вывод в консоль и файл с ротацией
- Поддержка русского языка в сообщениях
- Удобные функции для логирования производительности и ошибок
- Структурированное форматирование логов

#### Уровни логирования
- **DEBUG**: Детальная отладочная информация (вызовы функций, внутренние состояния)
- **INFO**: Основные операции (загрузка, сохранение, обработка)
- **WARNING**: Не критичные проблемы (пропуск закладок, ограничения)
- **ERROR**: Ошибки обработки (неудачные запросы, ошибки записи)
- **CRITICAL**: Критические системные ошибки

#### Формат логов
```
YYYY-MM-DD HH:MM:SS - module_name - LEVEL - Сообщение на русском
```

#### Настройка логирования
```env
# Уровень логирования
LOG_LEVEL=INFO

# Путь к файлу лога
LOG_FILE=./bookmarks_export.log
```

#### Использование в коде
```python
from src.logger import get_logger, log_performance, log_error_with_context

logger = get_logger(__name__)
logger.info("Информационное сообщение")
log_performance("operation_name", duration, "детали")
log_error_with_context(error, {"context": "data"})
```

### Формат файла прогресса
Файл `bookmarks_export/progress.json` содержит:
```json
{
  "version": "1.0",
  "timestamp": "2025-10-26T13:00:00",
  "bookmarks_file": "/path/to/bookmarks.json",
  "config_hash": "sha256_hash",
  "processed_urls": [
    {
      "url": "https://example.com",
      "title": "Example Page",
      "processed_at": "2025-10-26T13:00:00",
      "file_path": "Folder/Example Page.md",
      "folder_path": ["Folder"]
    }
  ],
  "failed_urls": [
    {
      "url": "https://failed.com",
      "title": "Failed Page",
      "failed_at": "2025-10-26T13:00:00",
      "error": "Connection timeout",
      "folder_path": ["Folder"]
    }
  ],
  "current_position": {
    "folder_path": ["Folder"],
    "bookmark_index": 1,
    "total_in_folder": 5
  },
  "statistics": {
    "total_bookmarks": 100,
    "processed_count": 50,
    "failed_count": 2,
    "skipped_count": 0,
    "start_time": "2025-10-26T12:00:00",
    "last_update": "2025-10-26T13:00:00"
  }
}
```

### Возобновление обработки
При использовании флага `--resume`:
1. Загружается сохраненный прогресс из `bookmarks_export/progress.json`
2. Проверяется совместимость конфигурации через хеш
3. Восстанавливается последняя позиция обработки
4. Пропускаются уже обработанные и неудачные закладки
5. Обработка продолжается с последней необработанной закладки