import aiohttp
from typing import List, Optional
from .api import LLMClient, LLMResponse, ToolCall
from bot.llm_utils import ToolInfo
import base64
import json
import re
import logging

logger = logging.getLogger(__name__)


class OllamaClient(LLMClient):
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self._models: List[str] = []

    @property
    def provider_name(self) -> str:
        return "ollama"

    def get_available_models(self) -> List[str]:
        return self._models if self._models else ["llama2", "mistral", "gemma"]

    async def _fetch_models(self) -> List[str]:
        """Получение списка доступных моделей с Ollama сервера"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/tags"
                ) as response:
                    if response.status != 200:
                        return ["llama2", "mistral", "gemma"]
                    data = await response.json()
                    self._models = [
                        model['name'] for model in data['models']
                    ]
                    return self._models

        except Exception as e:
            logger.error(f"Ошибка при получении списка моделей: {e}")
            return ["llama2", "mistral", "gemma"]

    async def generate_response(
        self, prompt: str, model: str, tools: List[ToolInfo]
    ) -> LLMResponse:
        """Генерация ответа от модели"""
        try:
            async with aiohttp.ClientSession() as session:
                tool_prompt = ""
                if tools:
                    tool_prompt = "\n\nДоступные инструменты:\n"
                    for tool in tools:
                        tool_prompt += (
                            f"- Сервер: {tool.server_name}, "
                            f"Инструмент: {tool.tool_name}\n"
                            f"  Описание: {tool.description}\n"
                            f"  Схема ввода: {json.dumps(tool.input_schema)}\n"
                        )
                    tool_prompt += (
                        "\nЕсли вам нужно использовать инструмент, ответьте JSON-объектом "
                        "в формате: "
                        '{"tool_call": {"server_name": "...", "tool_name": "...", '
                        '"arguments": {...}}}'
                        "\nВ противном случае, ответьте обычной строкой."
                    )

                full_prompt = f"{prompt}{tool_prompt}"

                payload = {
                    "model": model,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.0,
                    },
                }

                async with session.post(
                    f"{self.base_url}/api/generate", json=payload
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Ошибка API: {error_text}")
                    data = await response.json()
                    response_text = data.get("response", "")

                    # Попытка разобрать вызов инструмента из ответа
                    try:
                        tool_call_match = re.search(
                            r'\{"tool_call":\s*\{.*?\}\}', response_text, re.DOTALL
                        )
                        if tool_call_match:
                            tool_call_json = json.loads(
                                tool_call_match.group(0))
                            tool_call_data = tool_call_json.get("tool_call")
                            if tool_call_data:
                                return ToolCall(
                                    server_name=tool_call_data.get(
                                        "server_name", ""),
                                    tool_name=tool_call_data.get(
                                        "tool_name", ""),
                                    arguments=tool_call_data.get(
                                        "arguments", {}),
                                )
                    except json.JSONDecodeError:
                        pass  # Недействительный JSON, продолжаем как текст

                    return response_text

        except Exception as e:
            raise Exception(f"Ошибка при генерации ответа: {str(e)}")

    async def generate_response_with_image(
        self, file_path: str, model: str, user_prompt: Optional[str] = None
    ) -> str:
        """Генерирует ответ от модели Ollama с изображением."""
        try:
            async with aiohttp.ClientSession() as session:

                with open(file_path, "rb") as image_file:
                    encoded_string = base64.b64encode(
                        image_file.read()).decode('utf-8')

                # Используем user_prompt, если предоставлен, иначе используем запрос по умолчанию
                prompt_for_model = (
                    user_prompt if user_prompt else "Что на этом изображении?"
                )

                payload = {
                    "model": model,
                    "prompt": prompt_for_model,
                    "images": [encoded_string],
                    "stream": False
                }

                async with session.post(
                        f"{self.base_url}/api/generate",
                        json=payload
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"API error: {error_text}")

                    try:
                        data = await response.json()
                        if 'error' in data:
                            raise Exception(f"Ollama error: {data['error']}")
                        return data.get('response', '')
                    except json.JSONDecodeError:
                        raise Exception(
                            f"Failed to decode Ollama response as JSON: {await response.text()}"
                        )

        except Exception as e:
            raise Exception(f"Error generating response with image: {str(e)}")
