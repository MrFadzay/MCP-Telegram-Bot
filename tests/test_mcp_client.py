"""
Тесты для MCP клиентов.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from bot.mcp_client.client import HTTPMCPClient, StdioMCPClient


class TestHTTPMCPClient:
    """Тесты HTTP MCP клиента."""
    
    def test_init(self):
        """Тест инициализации клиента."""
        client = HTTPMCPClient("test-server", "http://localhost:8000")
        
        assert client.server_name == "test-server"
        assert client.url == "http://localhost:8000"
    
    @patch('bot.mcp_client.client.httpx.AsyncClient')
    async def test_list_tools(self, mock_httpx):
        """Тест получения списка инструментов."""
        # Настраиваем мок
        mock_client = AsyncMock()
        mock_httpx.return_value.__aenter__.return_value = mock_client
        
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "tools": [
                {
                    "name": "test_tool",
                    "description": "Test tool",
                    "inputSchema": {"type": "object"}
                }
            ]
        }
        mock_client.post.return_value = mock_response
        
        client = HTTPMCPClient("test-server", "http://localhost:8000")
        tools = await client.list_tools()
        
        assert "tools" in tools
        assert len(tools["tools"]) == 1
        assert tools["tools"][0]["name"] == "test_tool"
    
    @patch('bot.mcp_client.client.httpx.AsyncClient')
    async def test_call_tool(self, mock_httpx):
        """Тест вызова инструмента."""
        mock_client = AsyncMock()
        mock_httpx.return_value.__aenter__.return_value = mock_client
        
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "result": {"output": "test result"}
        }
        mock_client.post.return_value = mock_response
        
        client = HTTPMCPClient("test-server", "http://localhost:8000")
        result = await client.call_tool("test_tool", {"param": "value"})
        
        assert result["result"]["output"] == "test result"


class TestStdioMCPClient:
    """Тесты Stdio MCP клиента."""
    
    def test_init(self):
        """Тест инициализации клиента."""
        client = StdioMCPClient(
            "test-server", 
            "python", 
            ["-m", "test_server"]
        )
        
        assert client.server_name == "test-server"
        assert client.command == "python"
        assert client.args == ["-m", "test_server"]
    
    @patch('bot.mcp_client.client.asyncio.create_subprocess_exec')
    async def test_connect(self, mock_subprocess):
        """Тест подключения к серверу."""
        # Мокаем процесс
        mock_process = AsyncMock()
        mock_process.stdin = AsyncMock()
        mock_process.stdout = AsyncMock()
        mock_process.stderr = AsyncMock()
        mock_subprocess.return_value = mock_process
        
        client = StdioMCPClient("test-server", "python", ["-m", "test_server"])
        
        await client.connect()
        
        assert client.process == mock_process
        mock_subprocess.assert_called_once()
    
    async def test_disconnect(self):
        """Тест отключения от сервера."""
        client = StdioMCPClient("test-server", "python", ["-m", "test_server"])
        
        # Мокаем процесс
        mock_process = AsyncMock()
        client.process = mock_process
        
        await client.disconnect()
        
        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called_once()
        assert client.process is None