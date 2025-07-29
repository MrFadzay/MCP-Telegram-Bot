from abc import ABC, abstractmethod
from typing import List, Optional, Union, Dict, Any
from llm.shared_types import ToolCall, ToolInfo


LLMResponse = Union[str, ToolCall]


class LLMClient(ABC):
    @abstractmethod
    def get_available_models(self) -> List[str]:
        """Возвращает список доступных моделей для данного провайдера"""
        pass

    @abstractmethod
    async def generate_response(
        self, prompt: str, model: str, tools: List[ToolInfo],
        conversation_history: Optional[List[Dict[str, Any]]] = None
    ) -> LLMResponse:
        """Генерирует ответ используя выбранную модель"""
        pass

    async def generate_response_with_image(
            self, file_path: str, model: str,
            user_prompt: Optional[str] = None) -> str:
        """Генерирует ответ с изображением, может быть не реализован"""
        raise NotImplementedError(
            "Этот провайдер не реализовал ответ с изображением")

    async def _fetch_models(self):
        """
        Получает доступные модели для провайдера.
        Этот метод может быть реализован подклассами при необходимости.
        """
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Возвращает имя провайдера"""
        pass
