"""
Тесты для LLM провайдеров.
"""
import os
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from llm.google import GoogleClient
from llm.openai import OpenAIClient
from llm.ollama import OllamaClient
from llm.shared_types import ToolCall, ToolInfo


class TestGoogleClient:
    """Тесты Google LLM клиента."""

    @patch('llm.google.genai')
    def test_init(self, mock_genai):
        """Тест инициализации клиента."""
        client = GoogleClient("test-api-key")

        assert client.api_key == "test-api-key"
        mock_genai.configure.assert_called_once_with(api_key="test-api-key")

    @patch('llm.google.genai')
    async def test_generate_response(self, mock_genai):
        """Тест генерации ответа."""
        # Настраиваем мок
        mock_model = AsyncMock()
        mock_response = AsyncMock()
        mock_response.text = "Test response"
        mock_model.generate_content_async.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        client = GoogleClient("test-api-key")

        response = await client.generate_response(
            prompt="Test message", model="gemini-2.5-flash", tools=[]
        )

        assert response == "Test response"
        mock_model.generate_content_async.assert_called_once()

    @patch('llm.google.genai')
    async def test_get_available_models(self, mock_genai):
        """Тест получения доступных моделей."""
        # Мокаем модели
        mock_model1 = MagicMock()
        mock_model1.name = "models/gemini-2.5-flash"
        mock_model2 = MagicMock()
        mock_model2.name = "models/gemini-2.5-pro"

        mock_genai.list_models.return_value = [mock_model1, mock_model2]

        client = GoogleClient("test-api-key")
        models = client.get_available_models()

        assert "models/gemini-2.5-flash" in models
        assert "models/gemini-2.5-pro" in models


class TestOpenAIClient:
    """Тесты OpenAI LLM клиента."""

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-api-key"})
    def test_init(self):
        """Тест инициализации клиента."""
        with patch('llm.openai.AsyncOpenAI') as mock_openai:
            client = OpenAIClient()
            assert client.api_key == "test-api-key"
            mock_openai.assert_called_once_with(api_key="test-api-key")

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-api-key"})
    async def test_generate_response(self):
        """Тест генерации ответа."""
        with patch('llm.openai.AsyncOpenAI') as mock_openai:
            # Настраиваем мок
            mock_client = AsyncMock()
            mock_openai.return_value = mock_client

            mock_response = AsyncMock()
            mock_response.choices = [
                MagicMock(message=MagicMock(
                    content="Test response",
                    tool_calls=None  # Ensure no tool calls for this test
                ))
            ]
            mock_client.chat.completions.create.return_value = mock_response

            client = OpenAIClient()

            response = await client.generate_response(
                prompt="Test message", model="gpt-4o-mini", tools=[]
            )

            assert response == "Test response"
            mock_client.chat.completions.create.assert_called_once()

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-api-key"})
    async def test_generate_response_with_tool_call(self):
        """Тест генерации ответа с вызовом инструмента."""
        with patch('llm.openai.AsyncOpenAI') as mock_openai:
            mock_client = AsyncMock()
            mock_openai.return_value = mock_client

            mock_tool_call = MagicMock()
            mock_tool_call.function.name = "brave_web_search"
            mock_tool_call.function.arguments = '{"query": "test query"}'

            mock_response = AsyncMock()
            mock_response.choices = [
                MagicMock(message=MagicMock(
                    content=None,
                    tool_calls=[mock_tool_call]
                ))
            ]
            mock_client.chat.completions.create.return_value = mock_response

            client = OpenAIClient()

            tools = [
                ToolInfo(
                    server_name="brave-search",
                    tool_name="brave_web_search",
                    description="Performs a web search",
                    input_schema={"type": "object", "properties": {
                        "query": {"type": "string"}}}
                )
            ]

            response = await client.generate_response(
                prompt="Test message", model="gpt-4o-mini", tools=tools
            )

            assert isinstance(response, ToolCall)
            assert response.server_name == "brave"
            assert response.tool_name == "brave_web_search"
            assert response.arguments == {"query": "test query"}
            mock_client.chat.completions.create.assert_called_once()


class TestOllamaClient:
    """Тесты Ollama LLM клиента."""

    def test_init(self):
        """Тест инициализации клиента."""
        client = OllamaClient("http://localhost:11434")

        assert client.base_url == "http://localhost:11434"

    @patch('llm.ollama.aiohttp.ClientSession')
    async def test_generate_response(self, mock_client_session):
        """Тест генерации ответа."""
        # Настраиваем мок
        mock_session_instance = AsyncMock()
        mock_client_session.return_value.__aenter__.return_value = mock_session_instance

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "response": "Test response"
        }
        mock_session_instance.post.return_value.__aenter__.return_value = mock_response

        client = OllamaClient("http://localhost:11434")

        response = await client.generate_response(
            prompt="Test message", model="llama3.2", tools=[]
        )

        assert response == "Test response"
        mock_session_instance.post.assert_called_once()

    @patch('llm.ollama.aiohttp.ClientSession')
    async def test_get_available_models(self, mock_client_session):
        """Тест получения доступных моделей."""
        mock_session_instance = AsyncMock()
        mock_client_session.return_value.__aenter__.return_value = mock_session_instance

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "llama3.2"},
                {"name": "codellama"}
            ]
        }
        mock_session_instance.get.return_value.__aenter__.return_value = mock_response

        client = OllamaClient("http://localhost:11434")
        models = await client._fetch_models()  # Call the async method to fetch models

        assert "llama3.2" in models
        assert "codellama" in models
