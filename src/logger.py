"""
Модуль logger.py
Централизованная система логирования для всех модулей проекта.
Обеспечивает единообразное форматирование и конфигурацию логирования.
"""
import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from .config import Config


class LoggerManager:
    """
    Менеджер логирования приложения.
    
    Обеспечивает централизованную настройку логирования для всех модулей.
    Поддерживает вывод в консоль и файл с ротацией.
    """
    
    _instance: Optional['LoggerManager'] = None
    _initialized: bool = False
    
    def __new__(cls) -> 'LoggerManager':
        """
        Реализация паттерна Singleton для менеджера логирования.
        
        Возвращает:
            LoggerManager: Единственный экземпляр менеджера
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self) -> None:
        """
        Инициализация менеджера логирования.
        """
        if not self._initialized:
            self._loggers: Dict[str, logging.Logger] = {}
            self._config: Optional[Config] = None
            self._root_logger: Optional[logging.Logger] = None
            LoggerManager._initialized = True
    
    def setup_logging(self, config: Config) -> None:
        """
        Настраивает логирование на основе конфигурации.
        
        Аргументы:
            config: Объект конфигурации приложения
        """
        self._config = config
        
        # Получаем корневой логгер
        self._root_logger = logging.getLogger()
        self._root_logger.setLevel(getattr(logging, config.log_level.upper(), logging.INFO))
        
        # Очищаем существующие обработчики
        self._root_logger.handlers.clear()
        
        # Создаем форматтер
        formatter = self._create_formatter()
        
        # Добавляем обработчик для консоли
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self._root_logger.addHandler(console_handler)
        
        # Добавляем обработчик для файла с ротацией
        if config.log_file:
            file_handler = self._create_file_handler(config.log_file)
            file_handler.setFormatter(formatter)
            self._root_logger.addHandler(file_handler)
        
        # Логируем информацию о настройке
        logger = self.get_logger(__name__)
        logger.info(f"Логирование настроено с уровнем: {config.log_level}")
        logger.debug(f"Файл лога: {config.log_file}")
    
    def _create_formatter(self) -> logging.Formatter:
        """
        Создает форматтер для логов.
        
        Возвращает:
            logging.Formatter: Настроенный форматтер
        """
        # Формат с поддержкой русского языка
        format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        # Настройка локали для корректного отображения русского языка
        formatter = logging.Formatter(
            fmt=format_string,
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        return formatter
    
    def _create_file_handler(self, log_file: str) -> logging.Handler:
        """
        Создает файловый обработчик с ротацией.
        
        Аргументы:
            log_file: Путь к файлу лога
            
        Возвращает:
            logging.Handler: Файловый обработчик с ротацией
        """
        log_path = Path(log_file)
        
        # Создаем директорию для лога, если она не существует
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Используем ротацию по размеру (10 МБ) с сохранением 5 резервных копий
        handler = logging.handlers.RotatingFileHandler(
            filename=log_path,
            maxBytes=10 * 1024 * 1024,  # 10 МБ
            backupCount=5,
            encoding='utf-8'
        )
        
        return handler
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        Получает логгер для указанного модуля.
        
        Аргументы:
            name: Имя модуля (обычно __name__)
            
        Возвращает:
            logging.Logger: Настроенный логгер
        """
        if name not in self._loggers:
            logger = logging.getLogger(name)
            self._loggers[name] = logger
        
        return self._loggers[name]
    
    def set_level(self, level: str) -> None:
        """
        Изменяет уровень логирования для всех логгеров.
        
        Аргументы:
            level: Новый уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        if self._root_logger:
            self._root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
            
            # Логируем изменение уровня
            logger = self.get_logger(__name__)
            logger.info(f"Уровень логирования изменен на: {level}")
    
    def add_custom_handler(self, handler: logging.Handler) -> None:
        """
        Добавляет пользовательский обработчик к корневому логгеру.
        
        Аргументы:
            handler: Пользовательский обработчик логирования
        """
        if self._root_logger:
            self._root_logger.addHandler(handler)
            
            # Логируем добавление обработчика
            logger = self.get_logger(__name__)
            logger.debug(f"Добавлен пользовательский обработчик: {type(handler).__name__}")


# Глобальный экземпляр менеджера логирования
_logger_manager: Optional[LoggerManager] = None


def get_logger(name: str) -> logging.Logger:
    """
    Получает логгер для указанного модуля.
    
    Это удобная функция для получения логгера без необходимости
    напрямую работать с LoggerManager.
    
    Аргументы:
        name: Имя модуля (обычно __name__)
        
    Возвращает:
        logging.Logger: Настроенный логгер
        
    Пример:
        >>> from src.logger import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.info("Сообщение на русском языке")
    """
    global _logger_manager
    
    if _logger_manager is None:
        _logger_manager = LoggerManager()
    
    return _logger_manager.get_logger(name)


def setup_logging(config: Config) -> None:
    """
    Настраивает логирование приложения.
    
    Эта функция должна вызываться один раз при запуске приложения
    для инициализации системы логирования.
    
    Аргументы:
        config: Объект конфигурации приложения
        
    Пример:
        >>> from src.config import ConfigManager
        >>> from src.logger import setup_logging
        >>> 
        >>> config_manager = ConfigManager()
        >>> config = config_manager.get()
        >>> setup_logging(config)
    """
    global _logger_manager
    
    if _logger_manager is None:
        _logger_manager = LoggerManager()
    
    _logger_manager.setup_logging(config)


def set_log_level(level: str) -> None:
    """
    Изменяет уровень логирования для всего приложения.
    
    Аргументы:
        level: Новый уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Пример:
        >>> from src.logger import set_log_level
        >>> set_log_level("DEBUG")
    """
    global _logger_manager
    
    if _logger_manager is not None:
        _logger_manager.set_level(level)


def log_function_call(func_name: str, args: tuple = (), kwargs: Optional[dict] = None) -> None:
    """
    Логирует вызов функции с аргументами.
    
    Удобная функция для логирования вызовов функций в DEBUG режиме.
    
    Аргументы:
        func_name: Имя функции
        args: Позиционные аргументы
        kwargs: Именованные аргументы
        
    Пример:
        >>> from src.logger import log_function_call
        >>> log_function_call("process_bookmark", ("url",), {"title": "Заголовок"})
    """
    logger = get_logger(__name__)
    
    if logger.isEnabledFor(logging.DEBUG):
        args_str = ", ".join(str(arg) for arg in args)
        kwargs_str = ", ".join(f"{k}={v}" for k, v in (kwargs or {}).items())
        
        all_args = []
        if args_str:
            all_args.append(args_str)
        if kwargs_str:
            all_args.append(kwargs_str)
        
        args_full = ", ".join(all_args)
        logger.debug(f"Вызов функции: {func_name}({args_full})")


def log_performance(func_name: str, duration: float, details: str = "") -> None:
    """
    Логирует производительность операции.
    
    Аргументы:
        func_name: Имя операции или функции
        duration: Длительность в секундах
        details: Дополнительные детали
        
    Пример:
        >>> from src.logger import log_performance
        >>> import time
        >>> start = time.time()
        >>> # ... операция ...
        >>> duration = time.time() - start
        >>> log_performance("fetch_content", duration, "url=https://example.com")
    """
    logger = get_logger(__name__)
    
    details_str = f" ({details})" if details else ""
    logger.info(f"Производительность: {func_name} выполнена за {duration:.2f}с{details_str}")


def log_error_with_context(error: Exception, context: Dict[str, Any]) -> None:
    """
    Логирует ошибку с контекстной информацией.
    
    Аргументы:
        error: Исключение
        context: Контекстная информация (URL, файл и т.д.)
        
    Пример:
        >>> from src.logger import log_error_with_context
        >>> try:
        ...     # ... операция ...
        ... except Exception as e:
        ...     log_error_with_context(e, {"url": "https://example.com", "step": "parsing"})
    """
    logger = get_logger(__name__)
    
    context_str = ", ".join(f"{k}={v}" for k, v in context.items())
    logger.error(f"Ошибка: {type(error).__name__}: {error} | Контекст: {context_str}")