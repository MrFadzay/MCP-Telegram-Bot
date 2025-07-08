import httpx
import asyncio
import json
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

import jsonrpyc
from httpx_sse import ServerSentEvent, EventSource


class BaseMCPClient(ABC):
    @abstractmethod
    async def list_tools(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def list_resources(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def execute_tool(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def access_resource(self, uri: str) -> Any:
        pass

    @abstractmethod
    async def close(self):
        pass

    @abstractmethod
    async def get_stderr_messages(self) -> List[str]:
        pass

    @abstractmethod
    async def wait_until_ready(self, timeout: int = 60) -> bool:
        """
        Waits until the MCP server is ready to accept requests.
        Returns True if ready within timeout, False otherwise.
        """
        pass


class HTTPMCPClient(BaseMCPClient):
    def __init__(self, server_url: str):
        self.server_url = server_url
        self.client = httpx.AsyncClient()

    async def wait_until_ready(self, timeout: int = 60) -> bool:
        """
        Checks if the HTTP MCP server is ready by attempting to list tools.
        """
        start_time = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_time < timeout:
            try:
                # Attempt to list tools as a health check
                await self.list_tools()
                print(f"HTTP MCP server at {self.server_url} is ready.")
                return True
            except (httpx.RequestError, httpx.HTTPStatusError):
                print(f"HTTP MCP server at {self.server_url} not ready yet, "
                      "retrying...")
                await asyncio.sleep(1)  # Wait for 1 second before retrying
        print(f"HTTP MCP server at {self.server_url} did not become ready "
              f"within {timeout} seconds.")
        return False

    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        Lists all available tools on the MCP server.
        """
        try:
            response = await self.client.get(f"{self.server_url}/tools")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"HTTP error listing tools: {e}")
            return []
        except httpx.RequestError as e:
            print(f"Request error listing tools: {e}")
            return []

    async def list_resources(self) -> List[Dict[str, Any]]:
        """
        Lists all available resources on the MCP server.
        """
        try:
            response = await self.client.get(f"{self.server_url}/resources")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"HTTP error listing resources: {e}")
            return []
        except httpx.RequestError as e:
            print(f"Request error listing resources: {e}")
            return []

    async def execute_tool(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Executes a specific tool on the MCP server.
        """
        try:
            response = await self.client.post(
                f"{self.server_url}/tools/{tool_name}/execute",
                json=arguments
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"HTTP error executing tool {tool_name}: {e}")
            return {"error": str(e), "details": response.text}
        except httpx.RequestError as e:
            print(f"Request error executing tool {tool_name}: {e}")
            return {"error": str(e)}

    async def access_resource(self, uri: str) -> Any:
        """
        Accesses a specific resource on the MCP server.
        """
        try:
            response = await self.client.get(
                f"{self.server_url}/resources/{uri}"
            )
            response.raise_for_status()
            # Assuming resources return JSON, adjust if needed
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"HTTP error accessing resource {uri}: {e}")
            return {"error": str(e), "details": response.text}
        except httpx.RequestError as e:
            print(f"Request error accessing resource {uri}: {e}")
            return {"error": str(e)}

    async def close(self):
        """
        Closes the HTTP client session.
        """
        await self.client.aclose()

    async def get_stderr_messages(self) -> List[str]:
        """
        HTTP clients do not have stderr, so return an empty list.
        """
        return []


class StdioMCPClient(BaseMCPClient):
    def __init__(self, process: asyncio.subprocess.Process):
        self.process = process
        self._stderr_queue: asyncio.Queue = asyncio.Queue()
        self.server_name: Optional[str] = None
        self._client = jsonrpyc.RPC(
            self.process.stdout, self.process.stdin,
            is_server=False,
            loop=asyncio.get_event_loop()
        )
        # jsonrpyc does not have a start_io method, it starts on first call
        # or when the event loop is running.

    async def wait_until_ready(self, timeout: int = 60) -> bool:
        """
        Checks if the Stdio MCP server is ready by attempting to list tools.
        """
        start_time = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_time < timeout:
            try:
                # Attempt to list tools as a health check
                # jsonrpyc calls are awaited directly on the client object
                await self._client.list_tools()
                print(f"Stdio MCP server '{self.server_name}' is ready.")
                return True
            except Exception as e:
                print(f"Stdio MCP server '{self.server_name}' not ready yet, "
                      f"retrying... Error: {e}")
                await asyncio.sleep(1)  # Wait for 1 second before retrying
        print(f"Stdio MCP server '{self.server_name}' did not become ready "
              f"within {timeout} seconds.")
        return False

    async def add_stderr_message(self, message: str) -> None:
        """Добавляет сообщение из stderr в очередь."""
        await self._stderr_queue.put(message)

    async def get_stderr_messages(self) -> List[str]:
        """Возвращает все сообщения из stderr и очищает очередь."""
        messages = []
        while not self._stderr_queue.empty():
            messages.append(await self._stderr_queue.get())
        return messages

    async def list_tools(self) -> List[Dict[str, Any]]:
        print("DEBUG: Calling list_tools for StdioMCPClient via jsonrpyc")
        try:
            # jsonrpyc allows direct method calls
            response = await self._client.list_tools()
            print(f"DEBUG: Received response for list_tools: {response}")
            return response.get("tools", [])
        except Exception as e:
            print(f"ERROR: Failed to list tools via jsonrpyc: {e}")
            return []

    async def list_resources(self) -> List[Dict[str, Any]]:
        print("DEBUG: Calling list_resources for StdioMCPClient via jsonrpyc")
        try:
            response = await self._client.list_resources()
            print(f"DEBUG: Received response for list_resources: {response}")
            return response.get("resources", [])
        except Exception as e:
            print(f"ERROR: Failed to list resources via jsonrpyc: {e}")
            return []

    async def execute_tool(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        print(f"DEBUG: Calling execute_tool '{tool_name}' for StdioMCPClient "
              f"via jsonrpyc with args: {arguments}")
        try:
            response = await self._client.execute_tool(tool_name, arguments)
            print(f"DEBUG: Received response for execute_tool: {response}")
            return response.get("result", {})
        except Exception as e:
            print(
                f"ERROR: Failed to execute tool '{tool_name}' via jsonrpyc: {e}")
            return {"error": str(e)}

    async def access_resource(self, uri: str) -> Any:
        print(f"DEBUG: Calling access_resource '{uri}' for StdioMCPClient "
              "via jsonrpyc")
        try:
            response = await self._client.access_resource(uri)
            print(f"DEBUG: Received response for access_resource: {response}")
            return response.get("resource", {})
        except Exception as e:
            print(
                f"ERROR: Failed to access resource '{uri}' via jsonrpyc: {e}")
            return {"error": str(e)}

    async def close(self):
        print("DEBUG: Closing StdioMCPClient (jsonrpyc)")
        if self._client:
            # jsonrpyc does not have a specific stop method for client side
            # but closing the process will terminate the communication
            pass
        if self.process:
            try:
                # Give the process a moment to shut down gracefully
                await asyncio.wait_for(self.process.wait(), timeout=5)
            except asyncio.TimeoutError:
                print(f"WARNING: StdioMCPClient process for '{self.server_name}' "
                      "did not terminate in time, killing it.")
                self.process.kill()
                await self.process.wait()
        print("DEBUG: StdioMCPClient (jsonrpyc) closed.")


class SSE_MCP_Client(BaseMCPClient):
    def __init__(self, server_url: str):
        self.server_url = server_url
        self.client = httpx.AsyncClient(timeout=None)
        self._stderr_queue: asyncio.Queue = asyncio.Queue()
        self._event_source: Optional[EventSource] = None
        self._sse_task: Optional[asyncio.Task] = None

    async def wait_until_ready(self, timeout: int = 60) -> bool:
        """
        Checks if the SSE MCP server is ready by attempting to list tools.
        """
        start_time = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_time < timeout:
            try:
                await self.list_tools()
                print(f"SSE MCP server at {self.server_url} is ready.")
                return True
            except (httpx.RequestError, httpx.HTTPStatusError, asyncio.TimeoutError) as e:
                print(f"SSE MCP server at {self.server_url} not ready yet, "
                      f"retrying... Error: {e}")
                await asyncio.sleep(1)  # Wait for 1 second before retrying
            except Exception as e:
                print(f"Unexpected error during SSE MCP server health check: "
                      f"{e}")
                await asyncio.sleep(1)
        print(f"SSE MCP server at {self.server_url} did not become ready "
              f"within {timeout} seconds.")
        return False

    async def _get_event_source(self) -> EventSource:
        if self._event_source is None or self._event_source.closed:
            self._event_source = EventSource(
                self.server_url, client=self.client)
            # Start the SSE listener task if not already running
            if self._sse_task is None or self._sse_task.done():
                self._sse_task = asyncio.create_task(self._listen_for_events())
        return self._event_source

    async def _listen_for_events(self):
        """
        Прослушивает SSE-поток и обрабатывает события.
        """
        try:
            async with await self._get_event_source() as event_source:
                async for sse in event_source.aiter_sse():
                    if sse.data:
                        try:
                            data = json.loads(sse.data)
                            # Assuming SSE events are JSON-RPC responses/notifications
                            if "jsonrpc" in data and data["jsonrpc"] == "2.0":
                                # For simplicity, we'll just print for now.
                                # A more robust solution would involve a queue
                                # for responses based on request ID, similar to
                                # the original implementation.
                                print(
                                    f"DEBUG: Received SSE JSON-RPC event: {data}")
                            else:
                                print(f"DEBUG: Received SSE data: {data}")
                        except json.JSONDecodeError:
                            print(
                                f"DEBUG: Received non-JSON SSE data: {sse.data}")
                        except Exception as e:
                            print(f"DEBUG: Error processing SSE event: {sse.data}, "
                                  f"Error: {e}")
        except httpx.RequestError as e:
            print(f"ERROR: SSE connection failed: {e}")
        except Exception as e:
            print(f"ERROR: Unexpected error in SSE listener: {e}")
        finally:
            self._sse_task = None
            if self._event_source and not self._event_source.closed:
                await self._event_source.aclose()
            self._event_source = None

    async def _send_request_and_wait_for_sse_response(
        self, method: str, path: str, json_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Отправляет HTTP-запрос и ожидает соответствующий ответ из SSE-потока.
        """
        # В текущей реализации предполагается, что ответы на запросы (list_tools,
        # execute_tool и т.д.) приходят по обычному HTTP, а SSE используется
        # для асинхронных уведомлений или прогресса.
        # Если MCP-сервер на SSE отправляет ответы на вызовы инструментов
        # через SSE, то потребуется более сложная логика корреляции запросов
        # с SSE-ответами (например, по ID запроса).
        try:
            if method == "GET":
                response = await self.client.get(f"{self.server_url}/{path}")
            elif method == "POST":
                response = await self.client.post(
                    f"{self.server_url}/{path}", json=json_data
                )
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"HTTP error sending request to {path}: {e}")
            return {"error": str(e), "details": e.response.text}
        except httpx.RequestError as e:
            print(f"Request error sending request to {path}: {e}")
            return {"error": str(e)}

    async def list_tools(self) -> List[Dict[str, Any]]:
        response = await self._send_request_and_wait_for_sse_response(
            "GET", "tools"
        )
        return response.get("tools", [])

    async def list_resources(self) -> List[Dict[str, Any]]:
        response = await self._send_request_and_wait_for_sse_response(
            "GET", "resources"
        )
        return response.get("resources", [])

    async def execute_tool(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        response = await self._send_request_and_wait_for_sse_response(
            "POST", f"tools/{tool_name}/execute",
            {"tool_name": tool_name, "arguments": arguments}
        )
        return response.get("result", {})

    async def access_resource(self, uri: str) -> Any:
        response = await self._send_request_and_wait_for_sse_response(
            "GET", f"resources/{uri}"
        )
        return response.get("resource", {})

    async def close(self):
        if self._sse_task and not self._sse_task.done():
            self._sse_task.cancel()
            try:
                await self._sse_task
            except asyncio.CancelledError:
                pass
        if self._event_source and not self._event_source.closed:
            await self._event_source.aclose()
        await self.client.aclose()

    async def get_stderr_messages(self) -> List[str]:
        messages = []
        while not self._stderr_queue.empty():
            messages.append(await self._stderr_queue.get())
        return messages


def create_mcp_client(
    server_name: str,
    server_config: Dict[str, Any],
    process: Optional[asyncio.subprocess.Process] = None
) -> BaseMCPClient:
    server_type = server_config.get("type")
    server_url = server_config.get("url")

    if server_type == "stdio" and process:
        client = StdioMCPClient(process)
        client.server_name = server_name
        return client
    elif server_type == "sse" and server_url:
        return SSE_MCP_Client(server_url)
    elif server_url:
        return HTTPMCPClient(server_url)
    else:
        raise ValueError(
            "Invalid MCP server configuration: 'type' or 'url'/'process' "
            "missing."
        )
