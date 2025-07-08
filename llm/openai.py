import os
import json
import logging
from typing import List, Optional
from llm.api import LLMClient, LLMResponse
from llm.shared_types import ToolCall, ToolInfo
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class OpenAIClient(LLMClient):
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OPENAI_API_KEY не установлен в переменных окружения."
            )
        self.client = AsyncOpenAI(api_key=self.api_key)
        self._available_models = []

    @property
    def provider_name(self) -> str:
        return "openai"

    async def _fetch_models(self):
        """
        Получает доступные модели для провайдера из OpenAI API.
        """
        try:
            models_response = await self.client.models.list()
            self._available_models = [
                model.id for model in models_response.data if "gpt" in model.id
            ]
        except Exception as e:
            logger.error(f"Ошибка при получении моделей OpenAI: {e}")
            self._available_models = ["gpt-3.5-turbo", "gpt-4o"]

    def get_available_models(self) -> List[str]:
        return self._available_models

    async def generate_response(self, prompt: str, model: str, tools: List[ToolInfo]) -> LLMResponse:
        messages = [{"role": "user", "content": prompt}]
        try:
            # Преобразование ToolInfo в формат, понятный OpenAI
            tools_schema = []
            if tools:
                for tool_info in tools:
                    tools_schema.append({
                        "type": "function",
                        "function": {
                            "name": tool_info.tool_name,
                            "description": tool_info.description,
                            "parameters": tool_info.input_schema
                        }
                    })

            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools_schema if tools_schema else None,
                tool_choice="auto",
            )

            choice = response.choices[0].message

            if choice.tool_calls:
                # Предполагаем один вызов инструмента для простоты
                tool_call = choice.tool_calls[0]
                return ToolCall(
                    # Предполагаем формат типа 'brave_search_tool_name'
                    server_name=tool_call.function.name.split('_')[0],
                    tool_name=tool_call.function.name,
                    arguments=json.loads(tool_call.function.arguments)
                )
            else:
                return choice.content
        except Exception as e:
            return f"Ошибка при генерации ответа OpenAI: {e}"

    async def generate_response_with_image(
            self, file_path: str, model: str,
            user_prompt: Optional[str] = None) -> str:
        return "Обработка изображений OpenAI пока не реализована."
