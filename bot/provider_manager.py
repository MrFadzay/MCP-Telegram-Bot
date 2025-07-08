from typing import Dict, Type, List, Optional
from llm.api import LLMClient
from dataclasses import dataclass
import asyncio

@dataclass
class ModelConfig:
    provider_name: str
    model_name: str

class ProviderManager:
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

    async def set_model(self, model_name: str) -> None:
        """Установить текущую модель"""
        if not self.current_provider:
            raise ValueError("Сначала необходимо выбрать провайдера")

        available_models = await self.get_available_models(self.current_provider)
        if model_name not in available_models:
            raise ValueError(f"Модель {model_name} недоступна для провайдера "
                             f"{self.current_provider}")
        self.current_model = model_name

    def get_current_config(self) -> Optional[ModelConfig]:
        """Получить текущую конфигурацию"""
        if self.current_provider and self.current_model:
            return ModelConfig(self.current_provider, self.current_model)
        return None

    def get_provider_instance(self, provider_name: str) -> LLMClient:
        """Получить экземпляр провайдера по имени."""
        instance = self._provider_instances.get(provider_name)
        if not instance:
            raise ValueError(f"Провайдер '{provider_name}' не зарегистрирован.")
        return instance
