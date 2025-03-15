import aiohttp
from typing import List
from .api import LLMClient
import os
import base64
import json


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
                async with session.get(f"{self.base_url}/api/tags") as response:
                    if response.status != 200:
                        return ["llama2", "mistral", "gemma"]
                    data = await response.json()
                    self._models = [
                        model['name'] for model in data['models']
                    ]
                    return self._models

        except Exception as e:
            print(f"Ошибка при получении списка моделей: {e}")
            return ["llama2", "mistral", "gemma"]

    async def generate_response(self, prompt: str, model: str) -> str:
        """Генерация ответа от модели"""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": model,
                    "prompt": prompt,
                    "stream": False
                }

                async with session.post(
                    f"{self.base_url}/api/generate",
                    json=payload
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Ошибка API: {error_text}")
                    data = await response.json()
                    return data.get('response', '')

        except Exception as e:
            raise Exception(f"Ошибка при генерации ответа: {str(e)}")

    async def generate_response_with_image(
            self, file_path: str, model: str, user_prompt: str = None) -> str:
        """Generate a response from the Ollama model with an image."""
        try:
            async with aiohttp.ClientSession() as session:

                with open(file_path, "rb") as image_file:
                    encoded_string = base64.b64encode(
                        image_file.read()).decode('utf-8')

                # Use user_prompt if provided, otherwise use a default prompt
                prompt_for_model = user_prompt if user_prompt else "What is in this picture?"

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
                        raise Exception(f"Failed to decode Ollama response as JSON: {await response.text()}")

        except Exception as e:
            raise Exception(f"Error generating response with image: {str(e)}")
