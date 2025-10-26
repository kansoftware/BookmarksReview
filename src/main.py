"""
Модуль main.py
Главный модуль приложения, координирующий работу всех компонентов.
Обрабатывает аргументы командной строки и запускает основной цикл обработки.
"""
import asyncio
import argparse
import sys
import json
from pathlib import Path
from typing import Optional, List, Tuple, Set, Dict, Any
from datetime import datetime
import time

from src.config import ConfigManager
from src.parser import BookmarkParser
from src.fetcher import ContentFetcher
from src.summarizer import ContentSummarizer
from src.diagram import DiagramGenerator
from src.writer import FileSystemWriter
from src.models import BookmarkFolder, Bookmark, ProcessedPage
from src.utils import ProgressTracker, ErrorUtils, DateUtils
from src.logger import get_logger, setup_logging, log_function_call, log_performance, log_error_with_context

# Настройка логера для модуля
logger = get_logger(__name__)


def parse_arguments() -> argparse.Namespace:
    """
    Парсит аргументы командной строки.
    
    Возвращает:
        argparse.Namespace: Объект с аргументами командной строки
    """
    log_function_call("parse_arguments", (), {"argv": sys.argv[1:]})
    
    parser = argparse.ArgumentParser(
        description="Утилита для экспорта и описания закладок браузера",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python -m src.main bookmarks.json
  python -m src.main bookmarks.json --output-dir ./my_export
  python -m src.main bookmarks.json --resume --verbose
  python -m src.main bookmarks.json --dry-run --no-diagram
        """
    )
    
    # Обязательные аргументы
    parser.add_argument(
        "bookmarks_file",
        help="Путь к JSON-файлу закладок Chrome"
    )
    
    # Опциональные аргументы
    parser.add_argument(
        "--config",
        dest="config_path",
        help="Путь к .env файлу (по умолчанию: .env)"
    )
    
    parser.add_argument(
        "--output-dir",
        dest="output_dir",
        help="Директория для результатов (переопределяет OUTPUT_DIR из .env)"
    )
    
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Возобновить прерванную обработку"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Только парсинг, без обработки контента"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Подробное логирование (DEBUG уровень)"
    )
    
    parser.add_argument(
        "--no-diagram",
        action="store_true",
        help="Не генерировать Mermaid-диаграмму"
    )
    
    parser.add_argument(
        "--max-concurrent",
        type=int,
        help="Максимальное количество параллельных запросов (переопределяет FETCH_MAX_CONCURRENT)"
    )
    
    args = parser.parse_args()
    logger.debug(f"Аргументы командной строки разобраны: {vars(args)}")
    
    return args


def setup_application_logging(args: argparse.Namespace, config) -> None:
    """
    Настраивает логирование приложения.
    
    Аргументы:
        args: Аргументы командной строки
        config: Объект конфигурации
    """
    log_function_call("setup_application_logging", (), {
        "verbose": args.verbose,
        "config_log_level": config.log_level
    })
    
    log_level = "DEBUG" if args.verbose else config.log_level
    
    # Используем новую систему логирования
    setup_logging(config)
    
    logger.info("Логирование приложения настроено")
    logger.debug(f"Уровень логирования: {log_level}")
    logger.debug(f"Файл лога: {config.log_file}")


def load_progress_data(output_dir: Path) -> Dict[str, Any]:
    """
    Загружает данные о прогрессе из файла.
    
    Аргументы:
        output_dir: Директория вывода
        
    Возвращает:
        Dict[str, Any]: Данные о прогрессе или пустой словарь
    """
    start_time = time.time()
    log_function_call("load_progress_data", (str(output_dir),))
    
    progress_file = output_dir / "progress.json"
    
    if not progress_file.exists():
        logger.debug(f"Файл прогресса не найден: {progress_file}")
        return {}
    
    try:
        with open(progress_file, 'r', encoding='utf-8') as f:
            progress_data = json.load(f)
        
        duration = time.time() - start_time
        log_performance("load_progress_data", duration, f"file={progress_file}")
        
        processed_count = len(progress_data.get('processed_urls', []))
        failed_count = len(progress_data.get('failed_urls', []))
        
        logger.info(f"Прогресс загружен из {progress_file}: {processed_count} обработано, {failed_count} с ошибками")
        logger.debug(f"Детали прогресса: {progress_data}")
        
        return progress_data
    except Exception as e:
        duration = time.time() - start_time
        log_performance("load_progress_data", duration, f"file={progress_file}, success=False")
        log_error_with_context(e, {"progress_file": str(progress_file), "operation": "load_progress_data"})
        return {}


def save_progress_data(output_dir: Path, processed_urls: List[str], failed_urls: List[str]) -> None:
    """
    Сохраняет данные о прогрессе в файл.
    
    Аргументы:
        output_dir: Директория вывода
        processed_urls: Список успешно обработанных URL
        failed_urls: Список URL с ошибками
    """
    start_time = time.time()
    log_function_call("save_progress_data", (str(output_dir),), {
        "processed_count": len(processed_urls),
        "failed_count": len(failed_urls)
    })
    
    progress_data = {
        'timestamp': datetime.now().isoformat(),
        'processed_urls': processed_urls,
        'failed_urls': failed_urls
    }
    
    progress_file = output_dir / "progress.json"
    
    try:
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, indent=2, ensure_ascii=False)
        
        duration = time.time() - start_time
        log_performance("save_progress_data", duration, f"file={progress_file}")
        logger.info(f"Прогресс сохранен: {len(processed_urls)} обработано, {len(failed_urls)} с ошибками")
        
    except Exception as e:
        duration = time.time() - start_time
        log_performance("save_progress_data", duration, f"file={progress_file}, success=False")
        log_error_with_context(e, {"progress_file": str(progress_file), "operation": "save_progress_data"})


async def process_single_bookmark(
    bookmark: Bookmark,
    fetcher: ContentFetcher,
    summarizer: ContentSummarizer,
    processed_urls: Set[str],
    failed_urls: Set[str]
) -> Optional[ProcessedPage]:
    """
    Обрабатывает одну закладку.
    
    Аргументы:
        bookmark: Закладка для обработки
        fetcher: Загрузчик контента
        summarizer: Генератор описаний
        processed_urls: Множество обработанных URL
        failed_urls: Множество URL с ошибками
        
    Возвращает:
        Optional[ProcessedPage]: Обработанная страница или None при ошибке
    """
    start_time = time.time()
    log_function_call("process_single_bookmark", (bookmark.title,), {"url": bookmark.url})
    
    # Пропускаем уже обработанные URL
    if bookmark.url in processed_urls:
        logger.debug(f"Пропуск уже обработанного URL: {bookmark.url}")
        return None
    
    # Пропускаем URL с предыдущими ошибками
    if bookmark.url in failed_urls:
        logger.debug(f"Пропуск URL с предыдущей ошибкой: {bookmark.url}")
        return None
    
    try:
        logger.info(f"Обработка закладки: {bookmark.title}")
        logger.debug(f"URL: {bookmark.url}")
        
        # Загрузка контента
        html = await fetcher.fetch_content(bookmark.url)
        if not html:
            logger.warning(f"Не удалось загрузить контент: {bookmark.url}")
            failed_urls.add(bookmark.url)
            return None
        
        # Извлечение текста
        text = fetcher.extract_text(html)
        if not text:
            logger.warning(f"Не удалось извлечь текст из контента: {bookmark.url}")
            failed_urls.add(bookmark.url)
            return None
        
        # Генерация описания
        summary = await summarizer.generate_summary(text, bookmark.title)
        
        # Создание объекта обработанной страницы
        page = ProcessedPage(
            url=bookmark.url,
            title=bookmark.title,
            summary=summary,
            fetch_date=datetime.now(),
            status='success'
        )
        
        processed_urls.add(bookmark.url)
        
        duration = time.time() - start_time
        log_performance("process_single_bookmark", duration, f"title={bookmark.title}, success=True")
        logger.info(f"Успешно обработана закладка: {bookmark.title} за {duration:.2f}с")
        
        return page
        
    except Exception as e:
        duration = time.time() - start_time
        log_performance("process_single_bookmark", duration, f"title={bookmark.title}, success=False")
        log_error_with_context(e, {
            "bookmark_title": bookmark.title,
            "bookmark_url": bookmark.url,
            "operation": "process_single_bookmark"
        })
        failed_urls.add(bookmark.url)
        return None


async def traverse_and_process_folder(
    folder: BookmarkFolder,
    base_path: Path,
    fetcher: ContentFetcher,
    summarizer: ContentSummarizer,
    writer: FileSystemWriter,
    processed_urls: Set[str],
    failed_urls: Set[str],
    progress_tracker: ProgressTracker,
    dry_run: bool = False
) -> Tuple[int, int]:
    """
    Рекурсивно обходит папку и обрабатывает закладки.
    
    Аргументы:
        folder: Текущая папка
        base_path: Базовый путь для сохранения файлов
        fetcher: Загрузчик контента
        summarizer: Генератор описаний
        writer: Файловый писатель
        processed_urls: Множество обработанных URL
        failed_urls: Множество URL с ошибками
        progress_tracker: Трекер прогресса
        dry_run: Флаг режима без обработки контента
        
    Возвращает:
        Tuple[int, int]: (количество обработанных, количество с ошибками)
    """
    start_time = time.time()
    log_function_call("traverse_and_process_folder", (folder.name,), {
        "base_path": str(base_path),
        "bookmarks_count": len(folder.bookmarks),
        "children_count": len(folder.children),
        "dry_run": dry_run
    })
    
    # Создаем папку в файловой системе
    folder_path = base_path / writer._sanitize_filename(folder.name)
    folder_path.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Создана папка в файловой системе: {folder_path}")
    
    processed_count = 0
    failed_count = 0
    
    # Обрабатываем закладки в текущей папке
    for i, bookmark in enumerate(folder.bookmarks):
        progress_tracker.update(0, bookmark.title)
        
        if dry_run:
            # В режиме dry-run только логируем закладки
            logger.info(f"[DRY-RUN] Закладка {i+1}/{len(folder.bookmarks)}: {bookmark.title} - {bookmark.url}")
            processed_count += 1
            progress_tracker.update(1)
            continue
        
        # Обрабатываем закладку
        page = await process_single_bookmark(
            bookmark, fetcher, summarizer, processed_urls, failed_urls
        )
        
        if page:
            # Определяем путь для сохранения файла
            file_path = folder_path / writer._sanitize_filename(bookmark.title)
            if not str(file_path).endswith('.md'):
                file_path = file_path.with_suffix('.md')
            
            # Сохраняем файл
            writer.write_markdown(page, file_path)
            processed_count += 1
        else:
            failed_count += 1
        
        progress_tracker.update(1)
    
    # Рекурсивно обрабатываем вложенные папки
    for child_folder in folder.children:
        child_processed, child_failed = await traverse_and_process_folder(
            child_folder, folder_path, fetcher, summarizer, writer,
            processed_urls, failed_urls, progress_tracker, dry_run
        )
        processed_count += child_processed
        failed_count += child_failed
    
    duration = time.time() - start_time
    log_performance("traverse_and_process_folder", duration, f"folder={folder.name}")
    logger.info(f"Папка '{folder.name}' обработана: {processed_count} успешно, {failed_count} с ошибками за {duration:.2f}с")
    
    return processed_count, failed_count


async def process_bookmarks(
    args: argparse.Namespace,
    config,
    root_folder: BookmarkFolder
) -> Tuple[int, int]:
    """
    Основная функция обработки закладок.
    
    Аргументы:
        args: Аргументы командной строки
        config: Объект конфигурации
        root_folder: Корневая папка закладок
        
    Возвращает:
        Tuple[int, int]: (количество обработанных, количество с ошибками)
    """
    start_time = time.time()
    log_function_call("process_bookmarks", (), {
        "resume": args.resume,
        "dry_run": args.dry_run,
        "no_diagram": args.no_diagram
    })
    
    output_dir = Path(config.output_dir)
    
    # Загружаем прогресс если нужно
    processed_urls: Set[str] = set()
    failed_urls: Set[str] = set()
    
    if args.resume:
        progress_data = load_progress_data(output_dir)
        processed_urls = set(progress_data.get('processed_urls', []))
        failed_urls = set(progress_data.get('failed_urls', []))
        logger.info(f"Загружен прогресс: {len(processed_urls)} обработано, {len(failed_urls)} с ошибками")
    
    # Инициализация компонентов
    writer = FileSystemWriter(config)
    
    # Создаем файловую структуру
    writer.create_folder_structure(root_folder, output_dir)
    
    # Генерируем Mermaid-диаграмму если нужно
    if not args.no_diagram and config.generate_mermaid_diagram:
        logger.info("Генерация Mermaid-диаграммы структуры закладок")
        diagram_gen = DiagramGenerator()
        diagram_code = diagram_gen.generate_structure_diagram(root_folder)
        diagram_path = output_dir / "bookmarks_structure.md"
        diagram_gen.save_diagram(diagram_code, str(diagram_path))
        logger.info(f"Mermaid-диаграмма сохранена: {diagram_path}")
    
    # Подсчитываем общее количество закладок для прогресса
    total_bookmarks = count_bookmarks(root_folder)
    progress_tracker = ProgressTracker(total_bookmarks, "Обработка закладок")
    logger.info(f"Всего закладок к обработке: {total_bookmarks}")
    
    if args.dry_run:
        logger.info("Запуск в режиме DRY-RUN (без обработки контента)")
    
    # Обрабатываем закладки
    async with ContentFetcher(config) as fetcher:
        summarizer = ContentSummarizer(config)
        
        processed_count, failed_count = await traverse_and_process_folder(
            root_folder, output_dir, fetcher, summarizer, writer,
            processed_urls, failed_urls, progress_tracker, args.dry_run
        )
    
    # Сохраняем прогресс
    save_progress_data(output_dir, list(processed_urls), list(failed_urls))
    
    duration = time.time() - start_time
    log_performance("process_bookmarks", duration, f"processed={processed_count}, failed={failed_count}")
    logger.info(f"Обработка завершена: {processed_count} успешно, {failed_count} с ошибками за {duration:.2f}с")
    
    return processed_count, failed_count


def count_bookmarks(folder: BookmarkFolder) -> int:
    """
    Рекурсивно подсчитывает количество закладок в папке.
    
    Аргументы:
        folder: Папка для подсчета
        
    Возвращает:
        int: Общее количество закладок
    """
    log_function_call("count_bookmarks", (folder.name,))
    
    count = len(folder.bookmarks)
    for child in folder.children:
        count += count_bookmarks(child)
    
    logger.debug(f"Подсчет закладок для папки '{folder.name}': {count}")
    return count


def main() -> None:
    """
    Главная функция приложения.
    """
    start_time = time.time()
    log_function_call("main", (), {"argv": sys.argv})
    
    try:
        # Парсинг аргументов командной строки
        args = parse_arguments()
        
        # Проверяем существование файла закладок
        bookmarks_file = Path(args.bookmarks_file)
        if not bookmarks_file.exists():
            log_error_with_context(
                FileNotFoundError(f"Файл закладок не найден: {bookmarks_file}"),
                {"bookmarks_file": str(bookmarks_file)}
            )
            sys.exit(1)
        
        # Загрузка конфигурации
        config_manager = ConfigManager(args.config_path)
        config = config_manager.get()
        
        # Применяем переопределения из аргументов командной строки
        if args.output_dir:
            config.output_dir = args.output_dir
            logger.debug(f"Переопределена директория вывода: {config.output_dir}")
        if args.max_concurrent:
            config.fetch_max_concurrent = args.max_concurrent
            logger.debug(f"Переопределено количество параллельных запросов: {config.fetch_max_concurrent}")
        
        # Настройка логирования
        setup_application_logging(args, config)
        
        logger.info("Запуск утилиты для экспорта и описания закладок")
        logger.info(f"Файл закладок: {bookmarks_file}")
        logger.info(f"Директория вывода: {config.output_dir}")
        logger.info(f"Режим возобновления: {args.resume}")
        logger.info(f"Режим dry-run: {args.dry_run}")
        logger.info(f"Генерация диаграммы: {not args.no_diagram}")
        
        # Парсинг закладок
        parser = BookmarkParser()
        logger.info("Загрузка и парсинг файла закладок")
        
        try:
            data = parser.load_json(str(bookmarks_file))
            root_folder = parser.parse_bookmarks(data)
            total_bookmarks = count_bookmarks(root_folder)
            logger.info(f"Загружено закладок: {total_bookmarks}")
        except Exception as e:
            log_error_with_context(e, {
                "bookmarks_file": str(bookmarks_file),
                "operation": "parse_bookmarks"
            })
            sys.exit(1)
        
        # Обработка закладок
        try:
            processed, failed = asyncio.run(process_bookmarks(args, config, root_folder))
            
            duration = time.time() - start_time
            log_performance("main", duration, f"processed={processed}, failed={failed}")
            logger.info(f"Работа завершена. Обработано: {processed}, с ошибками: {failed}")
            logger.info(f"Общее время выполнения: {duration:.2f}с")
            
        except KeyboardInterrupt:
            logger.info("Обработка прервана пользователем")
            sys.exit(1)
        except Exception as e:
            log_error_with_context(e, {"operation": "process_bookmarks"})
            logger.error(f"Критическая ошибка при обработке: {e}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Программа прервана пользователем")
        sys.exit(1)
    except Exception as e:
        log_error_with_context(e, {"operation": "main"})
        logger.error(f"Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()