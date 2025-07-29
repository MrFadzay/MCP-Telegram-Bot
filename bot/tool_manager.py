from typing import Dict, Any, List, Optional
from mcp_client.client import BaseMCPClient, create_mcp_client
from llm.shared_types import ToolInfo
import asyncio
import json
import logging

logger = logging.getLogger(__name__)


class ToolManager:
    def __init__(self):
        self._mcp_clients: Dict[str, BaseMCPClient] = {}
        self._mcp_stderr_tasks: Dict[str, asyncio.Task] = {}

    def register_mcp_server(
        self,
        server_name: str,
        server_config: Dict[str, Any],
        process: Optional[asyncio.subprocess.Process] = None
    ) -> BaseMCPClient:
        """Регистрирует новый MCP сервер."""
        if server_name in self._mcp_clients:
            logger.info(
                f"MCP сервер '{server_name}' уже зарегистрирован. Перезаписываем.")

        client = create_mcp_client(server_name, server_config, process)
        self._mcp_clients[server_name] = client
        logger.info(f"MCP сервер '{server_name}' зарегистрирован.")
        return client

    def register_stderr_task(self, server_name: str, task: asyncio.Task) -> None:
        """Регистрирует задачу чтения stderr для MCP сервера."""
        self._mcp_stderr_tasks[server_name] = task

    async def close_mcp_clients(self) -> None:
        """Закрывает все MCP клиенты и отменяет связанные задачи stderr."""
        for server_name, client in self._mcp_clients.items():
            try:
                await client.close()
                logger.info(f"MCP клиент '{server_name}' закрыт.")
            except Exception as e:
                logger.error(
                    f"Ошибка при закрытии MCP клиента '{server_name}': {e}")

        for server_name, task in self._mcp_stderr_tasks.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    logger.info(f"Задача stderr для MCP сервера '{server_name}' "
                                "отменена.")
                except Exception as e:
                    logger.error(f"Ошибка при отмене задачи stderr для MCP сервера "
                                 f"'{server_name}': {e}")

    def _get_meta_tool_info(self) -> ToolInfo:
        """Возвращает информацию о мета-инструменте list_mcp_tools."""
        return ToolInfo(
            server_name="meta",
            tool_name="list_mcp_tools",
            description="Перечисляет все доступные инструменты MCP.",
            input_schema={}
        )

    async def get_available_mcp_tools(self) -> List[ToolInfo]:
        """
        Получает список всех доступных инструментов
        от зарегистрированных MCP серверов,
        включая мета-инструмент для перечисления инструментов.
        """
        all_tools: List[ToolInfo] = [self._get_meta_tool_info()]
        tasks = []
        for server_name, client in self._mcp_clients.items():
            tasks.append(self._fetch_server_tools(server_name, client))

        results = await asyncio.gather(*tasks)
        for tools_list in results:
            all_tools.extend(tools_list)
        return all_tools

    async def _fetch_server_tools(
        self,
        server_name: str,
        client: BaseMCPClient
    ) -> List[ToolInfo]:
        try:
            tools_data = await client.list_tools()
            server_tools: List[ToolInfo] = []
            for tool in tools_data:
                server_tools.append(
                    ToolInfo(
                        server_name=server_name,
                        tool_name=tool.get("name", "unknown"),
                        description=tool.get("description", ""),
                        input_schema=tool.get("input_schema", {})
                    )
                )
            return server_tools
        except Exception as e:
            logger.error(f"Ошибка при получении инструментов от MCP сервера "
                         f"'{server_name}': {e}")
            return []

    async def execute_mcp_tool(
        self, server_name: str, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Выполняет определенный инструмент на MCP сервере или мета-инструмент.
        """
        logger.info(f"Executing tool '{tool_name}' on server '{server_name}' with args: {arguments}")
        
        if server_name == "meta" and tool_name == "list_mcp_tools":
            # Обработка вызова мета-инструмента
            all_tools = await self.get_available_mcp_tools()
            # Отфильтровываем сам мета-инструмент из списка
            filtered_tools = [
                tool for tool in all_tools
                if not (tool.server_name == "meta" and tool.tool_name == "list_mcp_tools")
            ]
            formatted_tools = []
            for tool in filtered_tools:
                formatted_tools.append(
                    f"- Сервер: {tool.server_name}, Инструмент: {tool.tool_name}\n"
                    f"  Описание: {tool.description}\n"
                    f"  Схема ввода: {json.dumps(tool.input_schema)}"
                )
            return {"result": "\n".join(formatted_tools) if formatted_tools else "Нет доступных инструментов."}

        mcp_client = self._mcp_clients.get(server_name)
        if not mcp_client:
            raise ValueError(f"MCP server '{server_name}' not registered.")

        # Проверяем и преобразуем аргументы если необходимо
        if not isinstance(arguments, dict):
            logger.warning(f"Arguments are not dict, type: {type(arguments)}, converting...")
            try:
                if hasattr(arguments, '_pb'):
                    # Protobuf объект
                    arguments = dict(arguments)
                else:
                    arguments = dict(arguments)
            except Exception as e:
                logger.error(f"Failed to convert arguments: {e}")
                return {"error": f"Invalid arguments format: {type(arguments)}"}

        # Исправляем распространенные ошибки в аргументах для brave_web_search
        if tool_name == "brave_web_search":
            # Если LLM использует 'q' вместо 'query', исправляем
            if 'q' in arguments and 'query' not in arguments:
                arguments['query'] = arguments.pop('q')
                logger.info(f"Fixed argument: changed 'q' to 'query' for brave_web_search")
            
            # Убеждаемся, что есть обязательный параметр query
            if 'query' not in arguments:
                logger.error(f"Missing required 'query' parameter for brave_web_search")
                return {"error": "Missing required 'query' parameter"}

        result = await mcp_client.execute_tool(tool_name, arguments)
        logger.info(f"Tool execution result: {result}")
        
        # Обрабатываем результат в зависимости от структуры ответа MCP
        if isinstance(result, dict):
            if "content" in result:
                # MCP возвращает результат в поле content
                content = result["content"]
                if isinstance(content, list) and len(content) > 0:
                    # Если content - это список, извлекаем текст из первого элемента
                    if isinstance(content[0], dict) and "text" in content[0]:
                        return {"result": content[0]["text"]}
                    else:
                        return {"result": str(content[0])}
                elif isinstance(content, str):
                    return {"result": content}
                else:
                    return {"result": str(content)}
            elif "result" in result:
                return result
            else:
                return {"result": result}
        else:
            return {"result": result}

    async def get_mcp_stderr_messages(self, server_name: str) -> List[str]:
        """
        Получает сообщения stderr от определенного MCP сервера.
        """
        mcp_client = self._mcp_clients.get(server_name)
        if not mcp_client:
            return []
        return await mcp_client.get_stderr_messages()
