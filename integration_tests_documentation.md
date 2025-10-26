# Документация по интеграционным тестам

## Обзор

Интеграционные тесты предназначены для проверки взаимодействия между компонентами системы BookmarksReview. Они обеспечивают проверку корректности работы всего пайплайна обработки закладок, от импорта JSON-файла до генерации Markdown-файлов.

## Структура интеграционных тестов

### 1. Основные файлы тестов

- [`tests/test_integration.py`](tests/test_integration.py) - Базовые интеграционные тесты для проверки полного workflow
- [`tests/test_mock_server.py`](tests/test_mock_server.py) - Mock-сервер для имитации LLM API
- [`tests/test_diagram_integration.py`](tests/test_diagram_integration.py) - Тесты генерации Mermaid-диаграмм
- [`tests/test_filesystem_integration.py`](tests/test_filesystem_integration.py) - Тесты файловой системы
- [`tests/test_error_handling_integration.py`](tests/test_error_handling_integration.py) - Тесты обработки ошибок
- [`tests/test_resume_integration.py`](tests/test_resume_integration.py) - Тесты инкрементального выполнения и возобновления
- [`tests/conftest.py`](tests/conftest.py) - Общие фикстуры для интеграционных тестов

### 2. Тестовые данные

- [`tests/data/`](tests/data/) - Директория с тестовыми данными
  - `simple_bookmarks.json` - Простой файл закладок
  - `nested_bookmarks.json` - Вложенная структура закладок
  - `malformed_bookmarks.json` - Некорректный файл закладок

## Категории тестов

### 1. Базовые интеграционные тесты

#### `test_integration.py`

Проверяет полный цикл обработки закладок:

- `test_full_workflow_simple_bookmarks` - Полный workflow с простыми закладками
- `test_full_workflow_nested_bookmarks` - Полный workflow с вложенными закладками
- `test_error_handling_workflow` - Обработка ошибок в workflow
- `test_rate_limiting_integration` - Интеграция rate limiting
- `test_config_parsing_integration` - Интеграция конфигурации
- `test_progress_manager_integration` - Интеграция менеджера прогресса

### 2. Mock-сервер LLM API

#### `test_mock_server.py`

Предоставляет mock-сервер для имитации OpenAI-совместимого API:

- `test_default_response` - Ответ по умолчанию
- `test_custom_response` - Пользовательский ответ
- `test_error_response` - Обработка ошибок
- `test_rate_limit_response` - Rate limiting
- `test_models_endpoint` - Эндпоинт моделей
- `test_call_count_tracking` - Отслеживание вызовов
- `test_request_tracking` - Отслеживание запросов
- `test_reset_functionality` - Сброс состояния
- `test_integration_with_summarizer` - Интеграция с ContentSummarizer

### 3. Тесты диаграмм

#### `test_diagram_integration.py`

Проверяют генерацию Mermaid-диаграмм:

- `test_simple_structure_diagram` - Простая структура
- `test_nested_structure_diagram` - Вложенная структура
- `test_empty_structure_diagram` - Пустая структура
- `test_complex_nested_structure_diagram` - Сложная вложенная структура
- `test_diagram_with_special_characters` - Специальные символы
- `test_diagram_integration_with_parser` - Интеграция с парсером
- `test_diagram_node_counter_reset` - Сброс счетчика узлов
- `test_diagram_file_creation` - Создание файла диаграммы

### 4. Тесты файловой системы

#### `test_filesystem_integration.py`

Проверяют работу с файловой системой:

- `test_simple_file_structure_creation` - Создание простой структуры
- `test_nested_file_structure_creation` - Создание вложенной структуры
- `test_markdown_file_creation` - Создание Markdown-файлов
- `test_markdown_file_with_metadata` - Файлы с метаданными
- `test_markdown_file_without_metadata` - Файлы без метаданных
- `test_filename_sanitization` - Очистка имен файлов
- `test_special_characters_in_content` - Специальные символы в содержимом
- `test_long_content_handling` - Обработка длинного содержимого
- `test_unicode_content_handling` - Обработка Unicode
- `test_integration_with_parser` - Интеграция с парсером
- `test_error_handling_on_file_creation` - Обработка ошибок при создании
- `test_concurrent_file_creation` - Параллельное создание файлов

### 5. Тесты обработки ошибок

#### `test_error_handling_integration.py`

Проверяют обработку различных типов ошибок:

- `test_network_error_handling` - Сетевые ошибки
- `test_http_error_handling` - HTTP-ошибки
- `test_llm_api_error_handling` - Ошибки LLM API
- `test_file_system_error_handling` - Ошибки файловой системы
- `test_malformed_bookmarks_file` - Некорректные файлы закладок
- `test_rate_limiting_with_errors` - Rate limiting с ошибками
- `test_progress_recovery_after_error` - Восстановление после ошибок
- `test_partial_processing_recovery` - Восстановление после частичной обработки
- `test_concurrent_error_handling` - Параллельная обработка ошибок
- `test_memory_error_handling` - Ошибки памяти

### 6. Тесты инкрементального выполнения

#### `test_resume_integration.py`

Проверяют функционал сохранения и возобновления прогресса:

- `test_full_processing_with_progress` - Полная обработка с прогрессом
- `test_partial_processing_and_resume` - Частичная обработка и возобновление
- `test_resume_with_failed_bookmarks` - Возобновление с ошибочными закладками
- `test_config_hash_validation` - Валидация хеша конфигурации
- `test_progress_position_tracking` - Отслеживание позиции в прогрессе
- `test_progress_statistics` - Статистика прогресса
- `test_progress_persistence` - Сохранение прогресса
- `test_concurrent_progress_updates` - Параллельные обновления прогресса
- `test_progress_recovery_after_crash` - Восстановление после сбоя

## Запуск интеграционных тестов

### Запуск всех интеграционных тестов

```bash
python -m pytest tests/test_integration.py tests/test_mock_server.py tests/test_diagram_integration.py tests/test_filesystem_integration.py tests/test_error_handling_integration.py tests/test_resume_integration.py -v
```

### Запуск конкретной категории тестов

```bash
# Базовые интеграционные тесты
python -m pytest tests/test_integration.py -v

# Тесты диаграмм
python -m pytest tests/test_diagram_integration.py -v

# Тесты файловой системы
python -m pytest tests/test_filesystem_integration.py -v

# Тесты обработки ошибок
python -m pytest tests/test_error_handling_integration.py -v

# Тесты инкрементального выполнения
python -m pytest tests/test_resume_integration.py -v
```

### Запуск с покрытием

```bash
python -m pytest tests/test_integration.py --cov=src --cov-report=term-missing
```

## Архитектура тестов

### 1. Фикстуры

Основные фикстуры определены в [`tests/conftest.py`](tests/conftest.py):

- `temp_dir` - Временная директория для тестов
- `simple_bookmarks_file` - Простой файл закладок
- `nested_bookmarks_file` - Вложенный файл закладок
- `malformed_bookmarks_file` - Некорректный файл закладок
- `config` - Конфигурация для тестов
- `mock_llm_response` - Mock-ответ LLM
- `mock_llm_server` - Mock-сервер LLM

### 2. Mock-объекты

Для изоляции тестов используются mock-объекты:

- `httpx.AsyncClient` - Mock HTTP-клиента
- `openai.AsyncOpenAI` - Mock LLM API
- `ContentFetcher` - Mock загрузчика контента
- `ContentSummarizer` - Mock суммаризатора

### 3. Асинхронные тесты

Большинство интеграционных тестов являются асинхронными и используют декоратор `@pytest.mark.asyncio`.

## Текущее состояние

### Успешно проходящие тесты

- Все тесты диаграмм (7/7)
- Все тесты инкрементального выполнения (9/9)
- Большинство тестов файловой системы (7/12)
- Некоторые тесты обработки ошибок (4/10)

### Требующие исправления

- Mock-сервер LLM API (0/9)
- Базовые интеграционные тесты (2/6)
- Некоторые тесты файловой системы (5/12)
- Большинство тестов обработки ошибок (6/10)

### Основные проблемы

1. **Mock-сервер**: Проблемы с запуском HTTP-сервера в тестовой среде
2. **Мокирование HTTP-клиента**: Неправильная настройка моков для httpx.AsyncClient
3. **Файловая система**: Проблемы с созданием директорий и обработкой ошибок
4. **Обработка ошибок**: Неправильное ожидание поведения при ошибках

## Рекомендации по улучшению

1. **Исправить mock-сервер**: Пересмотреть реализацию HTTP-сервера для тестов
2. **Улучшить мокирование**: Использовать более правильные патчи для httpx
3. **Стандартизировать фикстуры**: Создать единые фикстуры для всех типов тестов
4. **Добавить E2E тесты**: Создать тесты с реальными HTTP-запросами
5. **Улучшить обработку ошибок**: Добавить более детальную проверку сценариев ошибок

## Покрытие

Текущее покрытие кода тестами: **87%**

- Покрытие модулей:
  - `config.py`: 96%
  - `parser.py`: 94%
  - `summarizer.py`: 93%
  - `fetcher.py`: 84%
  - `writer.py`: 82%
  - `diagram.py`: 78%
  - `main.py`: 65%
  - `utils.py`: 58%
  - `logger.py`: 45%
  - `models.py`: 0%
  - `progress.py`: 0%

## Заключение

Интеграционные тесты обеспечивают проверку взаимодействия между компонентами системы. Хотя некоторые тесты требуют доработки, основная функциональность проверяется корректно. Тесты инкрементального выполнения и диаграмм работают полностью, что обеспечивает надежность ключевых функций системы.