from abc import ABC, abstractmethod
from typing import List


class LLMClient(ABC):
    @abstractmethod
    def get_available_models(self) -> List[str]:
        """Возвращает список доступных моделей для данного провайдера"""
        pass

    @abstractmethod
    async def generate_response(self, prompt: str, model: str) -> str:
        """Генерирует ответ используя выбранную модель"""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Возвращает имя провайдера"""
        pass
