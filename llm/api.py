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

    async def generate_response_with_image(self, file_path:str, model: str) -> str:
      """Generate response with image, may not be implemented"""
      raise NotImplementedError("This provider not implemented response with image")

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Возвращает имя провайдера"""
        pass
