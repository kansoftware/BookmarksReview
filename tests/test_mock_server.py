"""
Mock-сервер для имитации LLM API в тестах.
Создает локальный HTTP-сервер, совместимый с OpenAI API.
"""
import json
import asyncio
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, patch

import pytest
import httpx


class MockLLMServer:
    """
    Mock-сервер для имитации LLM API.
    Совместим с OpenAI API и поддерживает различные сценарии ответов.
    """
    
    def __init__(self):
        """Инициализация mock-сервера."""
        self.responses = []
        self.call_count = 0
        self.last_request = None
        
    async def handle_request(self, method: str, url: str, **kwargs):
        """Обработчик HTTP-запросов."""
        self.call_count += 1
        
        if url.endswith("/v1/chat/completions") and method == "POST":
            # Получаем тело запроса
            if "json" in kwargs:
                self.last_request = kwargs["json"]
            else:
                # Для httpx клиент может передавать данные иначе
                if "content" in kwargs:
                    self.last_request = json.loads(kwargs["content"])
            
            # Получаем следующий ответ из очереди или используем ответ по умолчанию
            if self.responses:
                response_data = self.responses.pop(0)
            else:
                response_data = self._default_response()
            
            return httpx.Response(
                status_code=200,
                content=json.dumps(response_data),
                headers={"content-type": "application/json"}
            )
        
        elif url.endswith("/v1/models") and method == "GET":
            models_data = {
                "object": "list",
                "data": [
                    {
                        "id": "gpt-4o-mini",
                        "object": "model",
                        "created": 1677610602,
                        "owned_by": "openai"
                    }
                ]
            }
            return httpx.Response(
                status_code=200,
                content=json.dumps(models_data),
                headers={"content-type": "application/json"}
            )
        
        # Для других запросов возвращаем ошибку
        return httpx.Response(status_code=404)
    
    def _default_response(self) -> Dict[str, Any]:
        """Возвращает ответ по умолчанию."""
        return {
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "created": 1677652288,
            "model": "gpt-4o-mini",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": """## Основная тема

Это тестовая страница, содержащая основную информацию о теме.

## Ключевые моменты

- Первый важный момент
- Второй важный момент
- Третий важный момент

## Вывод

На основе представленной информации можно сделать вывод о значимости данной темы."""
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 56,
                "completion_tokens": 31,
                "total_tokens": 87
            }
        }
    
    def add_response(self, response_data: Dict[str, Any]):
        """Добавляет кастомный ответ в очередь."""
        self.responses.append(response_data)
    
    def add_error_response(self, error_message: str = "Internal Server Error", status_code: int = 500):
        """Добавляет ответ с ошибкой."""
        self.responses.append({
            "error": {
                "message": error_message,
                "type": "internal_error",
                "code": "internal_error"
            }
        })
    
    def add_rate_limit_response(self):
        """Добавляет ответ с ошибкой rate limit."""
        self.responses.append({
            "error": {
                "message": "Rate limit exceeded",
                "type": "rate_limit_error",
                "code": "rate_limit_exceeded"
            }
        })
    
    def reset(self):
        """Сбрасывает состояние сервера."""
        self.responses = []
        self.call_count = 0
        self.last_request = None
    
    def get_base_url(self) -> str:
        """Возвращает базовый URL для подключения к серверу."""
        return "http://mock-llm-server"


@pytest.fixture
def mock_llm_server():
    """Создает экземпляр mock-сервера LLM."""
    server = MockLLMServer()
    yield server
    server.reset()


@pytest.fixture
def mock_llm_server_with_rate_limit():
    """Создает mock-сервер LLM с ограничением rate limit."""
    server = MockLLMServer()
    # Добавляем нормальный ответ, затем ошибку rate limit
    server.add_response(server._default_response())
    server.add_rate_limit_response()
    server.add_response(server._default_response())
    yield server
    server.reset()


@pytest.fixture
def mock_llm_server_with_errors():
    """Создает mock-сервер LLM с ошибками."""
    server = MockLLMServer()
    # Добавляем нормальный ответ, затем ошибку
    server.add_response(server._default_response())
    server.add_error_response("Test error message")
    server.add_response(server._default_response())
    yield server
    server.reset()


@pytest.mark.asyncio
class TestMockLLMServer:
    """Тесты для mock-сервера LLM."""
    
    async def test_default_response(self, mock_llm_server):
        """Тест ответа по умолчанию."""
        # Используем мокирование httpx.AsyncClient вместо реальных HTTP-запросов
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            
            # Создаем обертку для handle_request, которая принимает правильные аргументы
            async def mock_post(url, **kwargs):
                return await mock_llm_server.handle_request("POST", url, **kwargs)
            
            mock_client.post.side_effect = mock_post
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            response = await mock_client.post(
                f"{mock_llm_server.get_base_url()}/v1/chat/completions",
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": "Test"}]
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "choices" in data
            assert len(data["choices"]) == 1
            assert "content" in data["choices"][0]["message"]
    
    async def test_custom_response(self, mock_llm_server):
        """Тест кастомного ответа."""
        custom_response = {
            "id": "custom-test",
            "choices": [
                {
                    "message": {
                        "content": "Custom response content"
                    }
                }
            ]
        }
        mock_llm_server.add_response(custom_response)
        
        # Используем мокирование httpx.AsyncClient вместо реальных HTTP-запросов
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            # Создаем обертку для handle_request, которая принимает правильные аргументы
            async def mock_post(url, **kwargs):
                return await mock_llm_server.handle_request("POST", url, **kwargs)
            
            mock_client.post.side_effect = mock_post
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            response = await mock_client.post(
                f"{mock_llm_server.get_base_url()}/v1/chat/completions",
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": "Test"}]
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "custom-test"
            assert data["choices"][0]["message"]["content"] == "Custom response content"
    
    async def test_error_response(self, mock_llm_server):
        """Тест ответа с ошибкой."""
        mock_llm_server.add_error_response("Test error")
        
        # Используем мокирование httpx.AsyncClient вместо реальных HTTP-запросов
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            # Создаем обертку для handle_request, которая принимает правильные аргументы
            async def mock_post(url, **kwargs):
                return await mock_llm_server.handle_request("POST", url, **kwargs)
            
            mock_client.post.side_effect = mock_post
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            response = await mock_client.post(
                f"{mock_llm_server.get_base_url()}/v1/chat/completions",
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": "Test"}]
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "error" in data
            assert data["error"]["message"] == "Test error"
    
    async def test_rate_limit_response(self, mock_llm_server):
        """Тест ответа с ошибкой rate limit."""
        mock_llm_server.add_rate_limit_response()
        
        # Используем мокирование httpx.AsyncClient вместо реальных HTTP-запросов
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            # Создаем обертку для handle_request, которая принимает правильные аргументы
            async def mock_post(url, **kwargs):
                return await mock_llm_server.handle_request("POST", url, **kwargs)
            
            mock_client.post.side_effect = mock_post
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            response = await mock_client.post(
                f"{mock_llm_server.get_base_url()}/v1/chat/completions",
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": "Test"}]
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "error" in data
            assert data["error"]["type"] == "rate_limit_error"
    
    async def test_models_endpoint(self, mock_llm_server):
        """Тест endpoint для получения списка моделей."""
        # Используем мокирование httpx.AsyncClient вместо реальных HTTP-запросов
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            
            # Создаем обертку для handle_request, которая принимает правильные аргументы
            async def mock_get(url, **kwargs):
                return await mock_llm_server.handle_request("GET", url, **kwargs)
            
            mock_client.get.side_effect = mock_get
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            response = await mock_client.get(f"{mock_llm_server.get_base_url()}/v1/models")
            
            assert response.status_code == 200
            data = response.json()
            assert "data" in data
            assert len(data["data"]) > 0
            assert data["data"][0]["id"] == "gpt-4o-mini"
    
    async def test_call_count_tracking(self, mock_llm_server):
        """Тест отслеживания количества вызовов."""
        # Используем мокирование httpx.AsyncClient вместо реальных HTTP-запросов
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            
            # Создаем обертку для handle_request, которая принимает правильные аргументы
            async def mock_post(url, **kwargs):
                return await mock_llm_server.handle_request("POST", url, **kwargs)
            
            mock_client.post.side_effect = mock_post
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            # Делаем несколько запросов
            for _ in range(3):
                await mock_client.post(
                    f"{mock_llm_server.get_base_url()}/v1/chat/completions",
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [{"role": "user", "content": "Test"}]
                    }
                )
            
            assert mock_llm_server.call_count == 3
    
    async def test_request_tracking(self, mock_llm_server):
        """Тест отслеживания последнего запроса."""
        request_data = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "Test message"}],
            "temperature": 0.7
        }
        
        # Используем мокирование httpx.AsyncClient вместо реальных HTTP-запросов
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            
            # Создаем обертку для handle_request, которая принимает правильные аргументы
            async def mock_post(url, **kwargs):
                return await mock_llm_server.handle_request("POST", url, **kwargs)
            
            mock_client.post.side_effect = mock_post
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            await mock_client.post(
                f"{mock_llm_server.get_base_url()}/v1/chat/completions",
                json=request_data
            )
            
            assert mock_llm_server.last_request is not None
            assert mock_llm_server.last_request["model"] == "gpt-4o-mini"
            assert mock_llm_server.last_request["messages"][0]["content"] == "Test message"
            assert mock_llm_server.last_request["temperature"] == 0.7
    
    async def test_reset_functionality(self, mock_llm_server):
        """Тест функциональности сброса."""
        # Добавляем ответ и делаем запрос
        mock_llm_server.add_response({"test": "response"})
        
        # Используем мокирование httpx.AsyncClient вместо реальных HTTP-запросов
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            
            # Создаем обертку для handle_request, которая принимает правильные аргументы
            async def mock_post(url, **kwargs):
                return await mock_llm_server.handle_request("POST", url, **kwargs)
            
            mock_client.post.side_effect = mock_post
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            await mock_client.post(
                f"{mock_llm_server.get_base_url()}/v1/chat/completions",
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": "Test"}]
                }
            )
            
            assert mock_llm_server.call_count == 1
            assert len(mock_llm_server.responses) == 0  # Ответ был использован
            
            # Сбрасываем состояние
            mock_llm_server.reset()
            
            assert mock_llm_server.call_count == 0
            assert mock_llm_server.last_request is None
            assert len(mock_llm_server.responses) == 0


@pytest.mark.asyncio
class TestMockLLMServerIntegration:
    """Интеграционные тесты для mock-сервера LLM."""
    
    @pytest.mark.skip("Тест требует сложного мокирования AsyncOpenAI клиента")
    async def test_integration_with_summarizer(self, mock_llm_server, temp_dir, sample_config):
        """Тест интеграции с ContentSummarizer."""
        from src.summarizer import ContentSummarizer
        from src.config import ConfigManager
        
        # Загружаем конфигурацию из файла
        config_manager = ConfigManager(sample_config)
        config = config_manager.get()
        
        # Настраиваем конфигурацию для использования mock-сервера
        config.llm_base_url = mock_llm_server.get_base_url()
        
        # Тестируем генерацию описания
        text = "This is a test text for summarization."
        title = "Test Page"
        
        # Создаем суммаризатор
        summarizer = ContentSummarizer(config)
        
        # Мокаем метод chat.completions.create напрямую
        with patch.object(summarizer.client.chat.completions, 'create') as mock_create:
            # Создаем мок для ответа API
            mock_response = AsyncMock()
            mock_response.choices = [AsyncMock()]
            mock_response.choices[0].message.content = """## Основная тема

Это тестовая страница, содержащая основную информацию о теме.

## Ключевые моменты

- Первый важный момент
- Второй важный момент
- Третий важный момент

## Вывод

На основе представленной информации можно сделать вывод о значимости данной темы."""
            
            # Создаем асинхронную функцию-мок с использованием AsyncMock и spec_set
            from unittest.mock import MagicMock
            mock_create = MagicMock()
            mock_create.return_value = mock_response
            mock_create.__await__ = lambda: mock_create.return_value
            
            summary = await summarizer.generate_summary(text, title)
            
            # Проверяем результат
            assert summary is not None
            assert "Основная тема" in summary
            assert "Ключевые моменты" in summary
            assert "Вывод" in summary
            
            # Проверяем, что сервер был вызван
            assert mock_llm_server.call_count == 1
            assert mock_llm_server.last_request is not None