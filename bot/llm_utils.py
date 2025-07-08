import logging
from typing import Optional, Dict, List, Any
from llm.api import LLMResponse
from llm.shared_types import ToolCall, ToolInfo
import asyncio
import json
from bot.provider_manager import ProviderManager
from bot.tool_manager import ToolManager

logger = logging.getLogger(__name__)

# Максимальная длина результата инструмента для передачи LLM
MAX_TOOL_OUTPUT_LENGTH = 2000


class LLMSelector:
    def __init__(self):
        self.provider_manager = ProviderManager()
        self.tool_manager = ToolManager()

    async def get_available_mcp_tools(self) -> List[ToolInfo]:
        """
        Получает список всех доступных инструментов
        от зарегистрированных MCP серверов.
        """
        if not self.provider_manager._is_init:
            await self.provider_manager._async_init()

        return await self.tool_manager.get_available_mcp_tools()

    def register_mcp_server(
        self,
        server_name: str,
        server_config: Dict[str, Any],
        process: Optional[asyncio.subprocess.Process] = None
    ) -> Any:
        """Регистрирует новый MCP сервер."""
        return self.tool_manager.register_mcp_server(server_name, server_config, process)

    def register_stderr_task(self, server_name: str, task: asyncio.Task) -> None:
        """Регистрирует задачу чтения stderr для MCP сервера."""
        self.tool_manager.register_stderr_task(server_name, task)

    async def close_mcp_clients(self) -> None:
        """Закрывает все MCP клиенты и отменяет связанные задачи stderr."""
        await self.tool_manager.close_mcp_clients()

    async def generate_response(self, prompt: str) -> LLMResponse:
        """Генерировать ответ используя текущую конфигурацию"""
        if not self.provider_manager.current_provider or not self.provider_manager.current_model:
            raise ValueError("Провайдер или модель не выбраны")

        provider = self.provider_manager.get_provider_instance(self.provider_manager.current_provider)

        
        available_tools = await self.get_available_mcp_tools()

        # --- Start of multi-step tool call logic ---
        MAX_TOOL_CALL_ITERATIONS = 3
        current_prompt = prompt
        tool_output_history = []

        for i in range(MAX_TOOL_CALL_ITERATIONS):
            # Всегда передаем available_tools провайдеру.generate_response
            # Ожидается, что LLM поймет, как их использовать.
            response = await provider.generate_response(
                current_prompt, self.provider_manager.current_model, available_tools
            )

            if isinstance(response, ToolCall):
                # Execute the tool
                try:
                    tool_result = await self.tool_manager.execute_mcp_tool(
                        response.server_name, response.tool_name, response.arguments
                    )
                    # Проверяем сообщения stderr после выполнения инструмента
                    stderr_messages = await self.tool_manager.get_mcp_stderr_messages(response.server_name)
                    if stderr_messages:
                        logger.debug(f"Сообщения stderr от MCP сервера "
                                     f"'{response.server_name}': {stderr_messages}")
                        # Добавляем stderr сообщения к результату инструмента
                        if isinstance(tool_result, dict):
                            tool_result["stderr_output"] = stderr_messages
                        else:
                            tool_result = {"result": tool_result,
                                           "stderr_output": stderr_messages}

                    tool_output_str = json.dumps(tool_result, ensure_ascii=False)
                    if len(tool_output_str) > MAX_TOOL_OUTPUT_LENGTH:
                        tool_output_str = (
                            tool_output_str[:MAX_TOOL_OUTPUT_LENGTH] +
                            f"... [результат сокращен до {MAX_TOOL_OUTPUT_LENGTH} "
                            "символов]"
                        )

                    tool_output = (f"Вызов инструмента '{response.tool_name}' "
                                   f"с аргументами {response.arguments} "
                                   f"вернул: {tool_output_str}")
                    tool_output_history.append(tool_output)
                    current_prompt = (
                        f"Основываясь на следующем выводе инструмента, "
                        "пожалуйста, продолжите или дайте окончательный ответ:\n"
                        f"{tool_output}"
                    )

                except Exception as e:
                    stderr_messages = await self.tool_manager.get_mcp_stderr_messages(response.server_name)

                    error_message = (
                        f"Ошибка при выполнении инструмента MCP "
                        f"'{response.server_name}/{response.tool_name}': {e}"
                    )
                    if stderr_messages:
                        error_message += (
                            f"\nStderr: {json.dumps(stderr_messages, ensure_ascii=False)}"
                        )
                    print(error_message)
                    tool_output_history.append(
                        f"Вызов инструмента завершился с ошибкой: {error_message}"
                    )
                    current_prompt = (
                        f"Предыдущий вызов инструмента завершился с ошибкой: "
                        f"{error_message}\nПожалуйста, попробуйте снова или "
                        "дайте окончательный ответ."
                    )
                    continue
            else:
                # Если LLM не запросил инструмент, это окончательный ответ
                return response

        # Если мы достигли этой точки, это означает, что было достигнуто
        # максимальное количество итераций вызова инструментов, и LLM
        # все еще не предоставил окончательный ответ.
        return LLMResponse(
            text="Я достиг максимального количества итераций для вызова "
                 "инструментов и не смог сформировать окончательный ответ. "
                 "Пожалуйста, переформулируйте ваш запрос или попробуйте позже."
        )
        # --- Конец логики многошагового вызова инструмента ---

    async def generate_response_with_image(
            self, file_path: str, user_prompt: Optional[str] = None) -> str:
        """Генерировать ответ, используя текущую конфигурацию и изображение"""
        if not self.provider_manager.current_provider or not self.provider_manager.current_model:
            raise ValueError("Провайдер или модель не выбраны")

        provider = self.provider_manager.get_provider_instance(self.provider_manager.current_provider)
        if not hasattr(provider, 'generate_response_with_image'):
            raise NotImplementedError(
                f'Провайдер {self.provider_manager.current_provider} не поддерживает '
                'обработку изображений')
        return await provider.generate_response_with_image(
            file_path, self.provider_manager.current_model, user_prompt)
