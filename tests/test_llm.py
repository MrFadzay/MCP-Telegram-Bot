"""
Тесты для LLM провайдеров.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from bot.llm.google import GoogleLLMClient
from bot.llm.openai import OpenAILLMClient
from bot.llm.ollama import OllamaLLMClient


class TestGoogleLLMClient:
    """Тесты Google LLM клиента."""
    
    @patch('bot.llm.google.genai')
    def test_init(self, mock_genai):
        """Тест инициализации клиента."""
        client = GoogleLLMClient("test-api-key")
        
        assert client.api_key == "test-api-key"
        assert client.model_name == "gemini-2.5-flash"
        mock_genai.configure.assert_called_once_with(api_key="test-api-key")
    
    @patch('bot.llm.google.genai')
    async def test_generate_response(self, mock_genai):
        """Тест генерации ответа."""
        # Настраиваем мок
        mock_model = AsyncMock()
        mock_response = AsyncMock()
        mock_response.text = "Test response"
        mock_model.generate_content_async.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        client = GoogleLLMClient("test-api-key")
        
        response = await client.generate_response(
            [{"role": "user", "content": "Test message"}]
        )
        
        assert response == "Test response"
        mock_model.generate_content_async.assert_called_once()
    
    @patch('bot.llm.google.genai')
    async def test_get_available_models(self, mock_genai):
        """Тест получения доступных моделей."""
        # Мокаем модели
        mock_model1 = MagicMock()
        mock_model1.name = "models/gemini-2.5-flash"
        mock_model2 = MagicMock()
        mock_model2.name = "models/gemini-2.5-pro"
        
        mock_genai.list_models.return_value = [mock_model1, mock_model2]
        
        client = GoogleLLMClient("test-api-key")
        models = await client.get_available_models()
        
        assert "models/gemini-2.5-flash" in models
        assert "models/gemini-2.5-pro" in models


class TestOpenAILLMClient:
    """Тесты OpenAI LLM клиента."""
    
    def test_init(self):
        """Тест инициализации клиента."""
        with patch('bot.llm.openai.AsyncOpenAI') as mock_openai:
            client = OpenAILLMClient("test-api-key")
            
            assert client.api_key == "test-api-key"
            assert client.model_name == "gpt-4o-mini"
            mock_openai.assert_called_once_with(api_key="test-api-key")
    
    async def test_generate_response(self):
        """Тест генерации ответа."""
        with patch('bot.llm.openai.AsyncOpenAI') as mock_openai:
            # Настраиваем мок
            mock_client = AsyncMock()
            mock_openai.return_value = mock_client
            
            mock_response = AsyncMock()
            mock_response.choices = [
                MagicMock(message=MagicMock(content="Test response"))
            ]
            mock_client.chat.completions.create.return_value = mock_response
            
            client = OpenAILLMClient("test-api-key")
            
            response = await client.generate_response(
                [{"role": "user", "content": "Test message"}]
            )
            
            assert response == "Test response"
            mock_client.chat.completions.create.assert_called_once()


class TestOllamaLLMClient:
    """Тесты Ollama LLM клиента."""
    
    def test_init(self):
        """Тест инициализации клиента."""
        client = OllamaLLMClient("http://localhost:11434")
        
        assert client.base_url == "http://localhost:11434"
        assert client.model_name == "llama3.2"
    
    @patch('bot.llm.ollama.httpx.AsyncClient')
    async def test_generate_response(self, mock_httpx):
        """Тест генерации ответа."""
        # Настраиваем мок
        mock_client = AsyncMock()
        mock_httpx.return_value.__aenter__.return_value = mock_client
        
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "message": {"content": "Test response"}
        }
        mock_client.post.return_value = mock_response
        
        client = OllamaLLMClient("http://localhost:11434")
        
        response = await client.generate_response(
            [{"role": "user", "content": "Test message"}]
        )
        
        assert response == "Test response"
        mock_client.post.assert_called_once()
    
    @patch('bot.llm.ollama.httpx.AsyncClient')
    async def test_get_available_models(self, mock_httpx):
        """Тест получения доступных моделей."""
        mock_client = AsyncMock()
        mock_httpx.return_value.__aenter__.return_value = mock_client
        
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "models": [
                {"name": "llama3.2"},
                {"name": "codellama"}
            ]
        }
        mock_client.get.return_value = mock_response
        
        client = OllamaLLMClient("http://localhost:11434")
        models = await client.get_available_models()
        
        assert "llama3.2" in models
        assert "codellama" in models