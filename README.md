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
- `.kilocode/` — документация проекта

## Особенности

### Асинхронная обработка
- Параллельная загрузка до 10 страниц одновременно
- Rate limiting для LLM API
- Graceful degradation при ошибках

### Управление прогрессом
- Сохранение прогресса в `bookmarks_export/progress.json`
- Возможность возобновления с `--resume`
- Периодическое сохранение прогресса во время обработки
- Отслеживание обработанных и неудачных URL
- Сохранение текущей позиции для точного возобновления
- Проверка совместимости конфигурации через хеш

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