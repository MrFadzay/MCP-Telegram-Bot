from typing import Optional, Dict, Type, List
from dataclasses import dataclass
from llm.api import LLMClient
import asyncio


@dataclass
class ModelConfig:
    provider_name: str
    model_name: str


class LLMSelector:
    def __init__(self):
        self.current_provider: Optional[str] = None
        self.current_model: Optional[str] = None
        self._providers: Dict[str, Type[LLMClient]] = {}
        self._provider_instances: Dict[str, LLMClient] = {}
        self._is_init = False

    async def _async_init(self):
        tasks = []
        for provider in self._provider_instances.values():
            if hasattr(provider, '_fetch_models'):
                tasks.append(provider._fetch_models())
        await asyncio.gather(*tasks)
        self._is_init = True

    def register_provider(self, provider_class: Type[LLMClient]) -> None:
        """Регистрация нового провайдера"""
        provider = provider_class()
        self._providers[provider.provider_name] = provider_class
        self._provider_instances[provider.provider_name] = provider

    async def get_available_providers(self) -> List[str]:
        """Получить список доступных провайдеров"""
        if not self._is_init:
            await self._async_init()
        return list(self._providers.keys())

    async def get_available_models(self, provider: str) -> List[str]:
        """Получить список доступных моделей для провайдера"""
        if not self._is_init:
            await self._async_init()
        if provider not in self._provider_instances:
            raise ValueError(f"Неподдерживаемый провайдер: {provider}")

        provider_instance = self._provider_instances[provider]

        return provider_instance.get_available_models()

    def set_provider(self, provider: str) -> None:
        """Установить текущего провайдера"""
        if provider not in self._provider_instances:
            raise ValueError(f"Неподдерживаемый провайдер: {provider}")
        self.current_provider = provider
        self.current_model = None

    async def set_model(self, model_name: str) -> None:  # Make set_model async
        """Установить текущую модель"""
        if not self.current_provider:
            raise ValueError("Сначала необходимо выбрать провайдера")

        available_models = await self.get_available_models(self.current_provider)
        if model_name not in available_models:
            raise ValueError(
                f"Модель {model_name} недоступна для провайдера {self.current_provider}"
            )
        self.current_model = model_name

    def get_current_config(self) -> Optional[ModelConfig]:
        """Получить текущую конфигурацию"""
        if self.current_provider and self.current_model:
            return ModelConfig(self.current_provider, self.current_model)
        return None

    async def generate_response(self, prompt: str) -> str:
        """Генерировать ответ используя текущую конфигурацию"""
        if not self.current_provider or not self.current_model:
            raise ValueError("Провайдер или модель не выбраны")

        provider = self._provider_instances[self.current_provider]
        return await provider.generate_response(prompt, self.current_model)

    async def generate_response_with_image(
            self, file_path: str, user_prompt: str = None) -> str:
        """Генерировать ответ, используя текущую конфигурацию и изображение"""
        if not self.current_provider or not self.current_model:
            raise ValueError("Провайдер или модель не выбраны")

        provider = self._provider_instances[self.current_provider]
        if not hasattr(provider, 'generate_response_with_image'):
            raise NotImplementedError(
                f'Provider {self.current_provider} does not support image processing')
        return await provider.generate_response_with_image(file_path, self.current_model, user_prompt)
