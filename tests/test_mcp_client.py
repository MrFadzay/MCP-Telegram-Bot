"""
Тесты для MCP клиентов.
"""
import pytest
import asyncio  # Added import
from unittest.mock import AsyncMock, patch, MagicMock
from mcp_client.client import HTTPMCPClient, StdioMCPClient


class TestHTTPMCPClient:
    """Тесты HTTP MCP клиента."""

    def test_init(self):
        """Тест инициализации клиента."""
        client = HTTPMCPClient("http://localhost:8000")

        assert client.server_url == "http://localhost:8000"

    @patch('mcp_client.client.httpx.AsyncClient')
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
        mock_client.get.return_value.__aenter__.return_value = mock_response
        mock_client.get.return_value.__aexit__.return_value = None

        client = HTTPMCPClient("http://localhost:8000")
        tools = await client.list_tools()

        assert len(tools) == 1
        assert tools[0]["name"] == "test_tool"

    @patch('mcp_client.client.httpx.AsyncClient')
    async def test_execute_tool(self, mock_httpx):
        """Тест вызова инструмента."""
        mock_client = AsyncMock()
        mock_httpx.return_value.__aenter__.return_value = mock_client
        mock_httpx.return_value.__aexit__.return_value = None

        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "result": {"output": "test result"}
        }
        mock_client.post.return_value.__aenter__.return_value = mock_response
        mock_client.post.return_value.__aexit__.return_value = None

        client = HTTPMCPClient("http://localhost:8000")
        result = await client.execute_tool("test_tool", {"param": "value"})

        assert result["output"] == "test result"


class TestStdioMCPClient:
    """Тесты Stdio MCP клиента."""

    @pytest.fixture
    def mock_process(self):
        """Фикстура для мокирования asyncio.subprocess.Process."""
        mock_proc = AsyncMock()
        mock_proc.stdin = AsyncMock()
        mock_proc.stdout = AsyncMock()
        mock_proc.stderr = AsyncMock()
        mock_proc.stdout.readline.side_effect = [
            b'{"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2024-11-05"}}\n',
            b'{"jsonrpc": "2.0", "id": 2, "result": {"tools": []}}\n',
            asyncio.CancelledError  # Для завершения _read_responses
        ]
        mock_proc.wait.return_value = 0  # Процесс завершается успешно
        return mock_proc

    async def test_init(self, mock_process):
        """Тест инициализации клиента."""
        client = StdioMCPClient(mock_process)
        client.server_name = "test-server"  # Устанавливаем server_name для тестов

        assert client.process == mock_process
        assert client.server_name == "test-server"
        # _stderr_task должен быть запущен
        assert not client._stderr_task.done()
        # _reader_task должен быть запущен
        assert not client._reader_task.done()

        # Отменяем задачи, чтобы избежать RuntimeWarning
        client._reader_task.cancel()
        client._stderr_task.cancel()
        await asyncio.gather(client._reader_task, client._stderr_task, return_exceptions=True)

    @patch('mcp_client.client.asyncio.create_subprocess_exec')
    async def test_wait_until_ready(self, mock_subprocess_exec, mock_process):
        """Тест ожидания готовности сервера."""
        mock_subprocess_exec.return_value = mock_process

        client = StdioMCPClient(mock_process)
        client.server_name = "test-server"

        is_ready = await client.wait_until_ready(timeout=1)

        assert is_ready
        # Проверяем, что были отправлены запросы
        mock_process.stdin.write.assert_called()
        # Проверяем, что были прочитаны ответы
        mock_process.stdout.readline.assert_called()

        # Отменяем задачи, чтобы избежать RuntimeWarning
        client._reader_task.cancel()
        client._stderr_task.cancel()
        await asyncio.gather(client._reader_task, client._stderr_task, return_exceptions=True)

    async def test_close(self, mock_process):
        """Тест отключения от сервера."""
        client = StdioMCPClient(mock_process)
        client.server_name = "test-server"

        # Запускаем задачи, чтобы их можно было отменить
        client._reader_task = asyncio.create_task(client._read_responses())
        client._stderr_task = asyncio.create_task(client._read_stderr())

        await client.close()

        mock_process.stdin.close.assert_called_once()
        mock_process.stdin.wait_closed.assert_called_once()
        await mock_process.wait.assert_called_once()  # Добавлено await
        assert client._reader_task.done()  # Задача чтения должна быть завершена
        assert client._stderr_task.done()  # Задача stderr должна быть завершена
        mock_process.terminate.assert_called_once()  # Добавлено
        mock_process.kill.assert_called_once()  # Добавлено
