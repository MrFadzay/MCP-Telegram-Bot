from typing import Dict, Type, List, Optional
from llm.api import LLMClient
from dataclasses import dataclass
import asyncio
import logging
from .services.user_service import UserService

logger = logging.getLogger(__name__)


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

    async def set_provider(self, provider: str, user_id: Optional[int] = None) -> None:
        """Установить текущего провайдера и сохранить в БД"""
        if provider not in self._provider_instances:
            raise ValueError(f"Неподдерживаемый провайдер: {provider}")

        self.current_provider = provider
        self.current_model = None

        # Сохранить в БД если указан user_id
        if user_id:
            await UserService.update_llm_settings(user_id, provider=provider)
            logger.info(f"Saved provider {provider} for user {user_id}")

    async def set_model(self, model_name: str, user_id: Optional[int] = None) -> None:
        """Установить текущую модель и сохранить в БД"""
        if not self.current_provider:
            raise ValueError("Сначала необходимо выбрать провайдера")

        available_models = await self.get_available_models(self.current_provider)
        if model_name not in available_models:
            raise ValueError(f"Модель {model_name} недоступна для провайдера "
                             f"{self.current_provider}")

        self.current_model = model_name

        # Сохранить в БД если указан user_id
        if user_id:
            await UserService.update_llm_settings(user_id, model=model_name)
            logger.info(f"Saved model {model_name} for user {user_id}")

    async def load_user_settings(self, user_id: int) -> bool:
        """Загрузить настройки пользователя из БД"""
        try:
            user_settings = await UserService.get_user_settings(user_id)
            if not user_settings:
                logger.info(
                    f"No settings found for user {user_id}, using defaults")
                return False

            provider = user_settings.get("llm_provider")
            model = user_settings.get("llm_model")

            if provider and provider in self._provider_instances:
                self.current_provider = provider
                logger.info(f"Loaded provider {provider} for user {user_id}")

                if model:
                    # Проверяем, что модель доступна
                    available_models = await self.get_available_models(provider)
                    if model in available_models:
                        self.current_model = model
                        logger.info(f"Loaded model {model} for user {user_id}")
                    else:
                        logger.warning(
                            f"Model {model} not available for provider {provider}, using default")

                return True
            else:
                logger.warning(
                    f"Provider {provider} not available, using defaults")
                return False

        except Exception as e:
            logger.error(f"Failed to load user settings for {user_id}: {e}")
            return False

    def get_current_config(self) -> Optional[ModelConfig]:
        """Получить текущую конфигурацию"""
        if self.current_provider and self.current_model:
            return ModelConfig(self.current_provider, self.current_model)
        return None

    def get_provider_instance(self, provider_name: str) -> LLMClient:
        """Получить экземпляр провайдера по имени."""
        instance = self._provider_instances.get(provider_name)
        if not instance:
            raise ValueError(
                f"Провайдер '{provider_name}' не зарегистрирован.")
        return instance
