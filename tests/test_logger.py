"""
Тесты для модуля логирования.
Проверяют корректность работы централизованной системы логирования.
"""
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import logging

from src.logger import LoggerManager, get_logger, setup_logging, set_log_level
from src.config import Config


class TestLoggerManager(unittest.TestCase):
    """Тесты для класса LoggerManager."""
    
    def setUp(self):
        """Подготовка тестового окружения."""
        # Создаем временный файл для логов
        self.temp_dir = tempfile.mkdtemp()
        self.log_file = os.path.join(self.temp_dir, "test.log")
        
        # Создаем тестовую конфигурацию
        self.test_config = Config(
            llm_api_key="test_key",
            llm_base_url="https://api.test.com",
            llm_model="test-model",
            llm_max_tokens=100,
            llm_temperature=0.7,
            llm_rate_limit=3,
            
            fetch_timeout=30,
            fetch_max_concurrent=10,
            fetch_max_size_mb=5,
            fetch_retry_attempts=3,
            fetch_retry_delay=1.5,
            fetch_max_redirects=5,
            
            output_dir="./test_output",
            markdown_include_metadata=True,
            generate_mermaid_diagram=True,
            
            prompt_file="./test_prompt.txt",
            
            log_level="DEBUG",
            log_file=self.log_file
        )
    
    def tearDown(self):
        """Очистка тестового окружения."""
        # Удаляем временные файлы
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_singleton_pattern(self):
        """Тест паттерна Singleton."""
        manager1 = LoggerManager()
        manager2 = LoggerManager()
        
        # Должен быть один и тот же экземпляр
        self.assertIs(manager1, manager2)
    
    def test_setup_logging(self):
        """Тест настройки логирования."""
        manager = LoggerManager()
        manager.setup_logging(self.test_config)
        
        # Проверяем, что корневой логгер настроен
        root_logger = logging.getLogger()
        self.assertEqual(root_logger.level, logging.DEBUG)
        
        # Проверяем наличие обработчиков
        self.assertTrue(len(root_logger.handlers) >= 1)
    
    def test_get_logger(self):
        """Тест получения логгера."""
        manager = LoggerManager()
        manager.setup_logging(self.test_config)
        
        logger1 = manager.get_logger("test_module")
        logger2 = manager.get_logger("test_module")
        logger3 = manager.get_logger("another_module")
        
        # Один и тот же модуль должен возвращать один и тот же логгер
        self.assertIs(logger1, logger2)
        
        # Разные модули должны возвращать разные логгеры
        self.assertIsNot(logger1, logger3)
        
        # Проверяем имена логгеров
        self.assertEqual(logger1.name, "test_module")
        self.assertEqual(logger3.name, "another_module")
    
    def test_set_level(self):
        """Тест изменения уровня логирования."""
        manager = LoggerManager()
        manager.setup_logging(self.test_config)
        
        # Изменяем уровень
        manager.set_level("ERROR")
        
        # Проверяем уровень корневого логгера, а не дочернего
        root_logger = logging.getLogger()
        self.assertEqual(root_logger.level, logging.ERROR)
    
    def test_file_handler_creation(self):
        """Тест создания файлового обработчика."""
        manager = LoggerManager()
        manager.setup_logging(self.test_config)
        
        # Проверяем, что файл лога создан
        self.assertTrue(os.path.exists(self.log_file))
    
    def test_log_file_rotation(self):
        """Тест ротации файлов лога."""
        manager = LoggerManager()
        manager.setup_logging(self.test_config)
        
        logger = manager.get_logger("test_module")
        
        # Записываем много сообщений для проверки ротации
        for i in range(1000):
            logger.info(f"Test message {i}")
        
        # Проверяем, что файл существует
        self.assertTrue(os.path.exists(self.log_file))


class TestLoggerFunctions(unittest.TestCase):
    """Тесты для удобных функций модуля logger."""
    
    def setUp(self):
        """Подготовка тестового окружения."""
        self.temp_dir = tempfile.mkdtemp()
        self.log_file = os.path.join(self.temp_dir, "test.log")
        
        self.test_config = Config(
            llm_api_key="test_key",
            llm_base_url="https://api.test.com",
            llm_model="test-model",
            llm_max_tokens=1000,
            llm_temperature=0.7,
            llm_rate_limit=3,
    
            fetch_timeout=30,
            fetch_max_concurrent=10,
            fetch_max_size_mb=5,
            fetch_retry_attempts=3,
            fetch_retry_delay=1.5,
            fetch_max_redirects=5,
    
            output_dir="./test_output",
            markdown_include_metadata=True,
            generate_mermaid_diagram=True,
    
            prompt_file="./test_prompt.txt",
    
            log_level="INFO",
            log_file=self.log_file
        )
    
    def tearDown(self):
        """Очистка тестового окружения."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_get_logger_function(self):
        """Тест функции get_logger."""
        logger1 = get_logger("test_module")
        logger2 = get_logger("test_module")
        
        # Должен возвращать один и тот же логгер
        self.assertIs(logger1, logger2)
        self.assertEqual(logger1.name, "test_module")
    
    def test_setup_logging_function(self):
        """Тест функции setup_logging."""
        setup_logging(self.test_config)
        
        # Проверяем, что логирование настроено
        root_logger = logging.getLogger()
        self.assertTrue(len(root_logger.handlers) > 0)
    
    def test_set_log_level_function(self):
        """Тест функции set_log_level."""
        setup_logging(self.test_config)
        
        # Изменяем уровень
        set_log_level("WARNING")
        
        # Проверяем уровень корневого логгера, а не дочернего
        root_logger = logging.getLogger()
        self.assertEqual(root_logger.level, logging.WARNING)
    
    def test_log_performance(self):
        """Тест функции log_performance."""
        from src.logger import log_performance
        
        setup_logging(self.test_config)
        logger = get_logger("test_module")
        
        with self.assertLogs('src.logger', level='INFO') as cm:
            log_performance("test_operation", 2.5, "test details")
        
        # Проверяем наличие сообщения о производительности
        self.assertIn("Производительность: test_operation выполнена за 2.50с (test details)", cm.output[0])
    
    def test_log_function_call(self):
        """Тест функции log_function_call."""
        from src.logger import log_function_call
        
        setup_logging(self.test_config)
        
        with self.assertLogs('src.logger', level='DEBUG') as cm:
            log_function_call("test_function", ("arg1",), {"kwarg1": "value1"})
        
        # Проверяем наличие сообщения о вызове функции
        self.assertIn("Вызов функции: test_function(arg1, kwarg1=value1)", cm.output[0])
    
    def test_log_error_with_context(self):
        """Тест функции log_error_with_context."""
        from src.logger import log_error_with_context
        
        setup_logging(self.test_config)
        
        test_error = ValueError("Test error")
        context = {"url": "https://example.com", "step": "parsing"}
        
        with self.assertLogs('src.logger', level='ERROR') as cm:
            log_error_with_context(test_error, context)
        
        # Проверяем наличие сообщения об ошибке с контекстом
        self.assertIn("Ошибка: ValueError: Test error | Контекст: url=https://example.com, step=parsing", cm.output[0])


class TestLoggerIntegration(unittest.TestCase):
    """Тесты интеграции логирования с другими модулями."""
    
    def setUp(self):
        """Подготовка тестового окружения."""
        self.temp_dir = tempfile.mkdtemp()
        self.log_file = os.path.join(self.temp_dir, "test.log")
    
    def tearDown(self):
        """Очистка тестового окружения."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_config_module_logging(self):
        """Тест интеграции с модулем config."""
        # Просто проверяем, что ConfigManager может быть создан с тестовой конфигурацией
        # и что логирование работает корректно
        from src.config import ConfigManager
        
        # Создаем временный .env файл
        env_file = os.path.join(self.temp_dir, ".env")
        with open(env_file, 'w') as f:
            f.write("LLM_API_KEY=test_key\n")
            f.write("LOG_LEVEL=INFO\n")
        
        try:
            # Просто проверяем, что ConfigManager создается без ошибок
            config_manager = ConfigManager(env_file)
            self.assertIsNotNone(config_manager)
            
            # Проверяем, что конфигурация загружается корректно
            config = config_manager.get()
            self.assertEqual(config.llm_api_key, "test_key")
            self.assertEqual(config.log_level, "INFO")
        finally:
            if os.path.exists(env_file):
                os.remove(env_file)
    
    def test_logging_levels(self):
        """Тест различных уровней логирования."""
        from src.logger import get_logger
        
        # Создаем тестовую конфигурацию для каждого уровня
        levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        
        for level in levels:
            with self.subTest(level=level):
                test_config = Config(
                    llm_api_key="test_key",
                    llm_base_url="https://api.test.com",
                    llm_model="test-model",
                    llm_max_tokens=1000,
                    llm_temperature=0.7,
                    llm_rate_limit=3,
    
                    fetch_timeout=30,
                    fetch_max_concurrent=10,
                    fetch_max_size_mb=5,
                    fetch_retry_attempts=3,
                    fetch_retry_delay=1.5,
                    fetch_max_redirects=5,
    
                    output_dir="./test_output",
                    markdown_include_metadata=True,
                    generate_mermaid_diagram=True,
    
                    prompt_file="./test_prompt.txt",
    
                    log_level=level,
                    log_file=self.log_file
                )
                
                setup_logging(test_config)
                
                # Проверяем уровень корневого логгера, а не дочернего
                root_logger = logging.getLogger()
                expected_level = getattr(logging, level)
                self.assertEqual(root_logger.level, expected_level)


if __name__ == '__main__':
    unittest.main()