import google.generativeai as genai
import logging
from typing import List, Optional
from .api import LLMClient, LLMResponse, ToolCall
from bot.llm_utils import ToolInfo
import os
import PIL.Image
import google.generativeai.types as genai_types

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)


class GoogleClient(LLMClient):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("Google API key is required.")
        genai.configure(api_key=self.api_key)
        self._models: List[str] = []

    @property
    def provider_name(self) -> str:
        return "google"

    def get_available_models(self) -> List[str]:
        return self._models

    async def _fetch_models(self) -> None:
        """Получает список доступных моделей из Google AI API."""
        try:
            available_models: List[genai_types.Model] = genai.list_models()
            self._models = [
                model.name
                for model in available_models
                if "generateContent" in model.supported_generation_methods
            ]
            logger.info(f"Доступные модели: {self._models}")
        except Exception as e:
            logger.error(f"Ошибка при получении моделей из Google AI API: {e}")

    async def generate_response(
        self, prompt: str, model: str, tools: List[ToolInfo]
    ) -> LLMResponse:
        """Генерирует ответ от модели Google Gemini."""
        logger.info(f"Генерация ответа для запроса: {prompt[:100]}...")
        try:
            gemini_tools = []
            if tools:
                for tool_info in tools:
                    gemini_tools.append(
                        {
                            "function_declarations": [
                                {
                                    "name": tool_info.tool_name,
                                    "description": tool_info.description,
                                    "parameters": tool_info.input_schema,
                                }
                            ]
                        }
                    )
            logger.info(f"Using model: {model}")
            model_instance = genai.GenerativeModel(
                model_name=model, tools=gemini_tools if gemini_tools else None
            )

            convo = model_instance.start_chat(history=[])
            logger.info("Sending message to Gemini API...")
            response = convo.send_message(prompt)
            logger.info(
                f"Received response from Gemini API. Candidates: "
                f"{len(response.candidates) if response.candidates else 0}"
            )

            if (
                response.candidates
                and response.candidates[0].content
                and response.candidates[0].content.parts
                and response.candidates[0].content.parts[0].function_call
            ):
                tool_call_data = \
                    response.candidates[0].content.parts[0].function_call
                logger.info(
                    f"Detected tool call: {tool_call_data.name} with args: "
                    f"{tool_call_data.args}"
                )
                original_tool_info = next(
                    (
                        t
                        for t in tools
                        if t.tool_name == tool_call_data.name
                    ),
                    None,
                )
                server_name = (
                    original_tool_info.server_name
                    if original_tool_info
                    else "unknown_server"
                )

                return ToolCall(
                    server_name=server_name,
                    tool_name=tool_call_data.name,
                    arguments=tool_call_data.args,
                )
            logger.info(
                f"Returning text response. Text: {response.text[:100]}..."
            )
            return response.text
        except Exception as e:
            logger.error(
                f"Error during response generation: {str(e)}", exc_info=True
            )
            raise Exception(f"Error during response generation: {str(e)}")

    async def generate_response_with_image(
        self, file_path: str, model: str, user_prompt: Optional[str] = None
    ) -> str:
        """
        Генерирует ответ от модели Google Gemini с изображением.

        Аргументы:
            file_path (str): Путь к файлу изображения.
            model (str): Имя модели для генерации ответа.
            user_prompt (str, optional): Текст, предоставленный пользователем,
            для сопровождения изображения. По умолчанию None.

        Возвращает:
            str: Сгенерированный ответ.
        """
        try:
            model_instance = genai.GenerativeModel(model_name=model)

            try:
                img = PIL.Image.open(file_path)
            except Exception as e:
                raise ValueError(f"Invalid image file or format: {e}")

            if user_prompt:
                prompt_for_model = user_prompt
            else:
                prompt_for_model = "What is this image?"

            response = model_instance.generate_content([prompt_for_model, img])

            if hasattr(response, "text"):
                return response.text
            else:
                result = ""
                for chunk in response:
                    result += chunk.text
                return result
        except Exception as e:
            raise Exception(
                f"Error during image response generation: {str(e)}")
