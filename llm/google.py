import google.generativeai as genai
import logging
from typing import List, Optional, Dict, Any
from .api import LLMClient, LLMResponse, ToolCall
from bot.llm_utils import ToolInfo
import os
import PIL.Image
import google.generativeai.types as genai_types
import pathlib

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
    
    def _clean_schema_for_gemini(self, schema: dict) -> dict:
        """Очищает JSON схему от полей, не поддерживаемых Google Gemini API."""
        if not isinstance(schema, dict):
            return schema
        
        cleaned = {}
        for key, value in schema.items():
            if key == "properties" and isinstance(value, dict):
                # Рекурсивно очищаем свойства
                cleaned_properties = {}
                for prop_name, prop_schema in value.items():
                    if isinstance(prop_schema, dict):
                        # Удаляем неподдерживаемые поля
                        cleaned_prop = {k: v for k, v in prop_schema.items() 
                                      if k not in ["default"]}
                        cleaned_properties[prop_name] = cleaned_prop
                    else:
                        cleaned_properties[prop_name] = prop_schema
                cleaned[key] = cleaned_properties
            else:
                cleaned[key] = value
        
        return cleaned

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
        self, prompt: str, model: str, tools: List[ToolInfo],
        conversation_history: Optional[List[Dict[str, Any]]] = None
    ) -> LLMResponse:
        """Генерирует ответ от модели Google Gemini."""
        logger.info(f"Генерация ответа для запроса: {prompt[:100]}...")
        try:
            gemini_tools = []
            if tools:
                for tool_info in tools:
                    # Очищаем схему от неподдерживаемых полей (например, default)
                    cleaned_schema = self._clean_schema_for_gemini(tool_info.input_schema)
                    gemini_tools.append(
                        {
                            "function_declarations": [
                                {
                                    "name": tool_info.tool_name,
                                    "description": tool_info.description,
                                    "parameters": cleaned_schema,
                                }
                            ]
                        }
                    )
            
            # Улучшаем промпт для лучшего понимания использования инструментов
            enhanced_prompt = prompt
            if tools and any(tool.tool_name in ['brave_web_search', 'brave_local_search'] for tool in tools):
                enhanced_prompt = f"""Ты умный помощник с доступом к поисковым инструментам.

ВАЖНО: Если пользователь спрашивает о:
- Текущей погоде, новостях, курсах валют
- Актуальной информации, которая может изменяться
- Поиске в интернете
- Местных заведениях или услугах

ТО ОБЯЗАТЕЛЬНО используй доступные поисковые инструменты для получения актуальной информации.

Доступные инструменты:
- brave_web_search: параметры (query: строка поискового запроса, count: количество результатов)
- brave_local_search: параметры (query: строка поискового запроса для местного поиска, count: количество результатов)

ВНИМАНИЕ: Используй ТОЧНО параметр "query" (не "q" или другие варианты) для поисковых запросов!

Запрос пользователя: {prompt}"""
            
            logger.info(f"Using model: {model}")
            model_instance = genai.GenerativeModel(
                model_name=model, tools=gemini_tools if gemini_tools else None
            )

            # Преобразуем историю в формат Gemini
            gemini_history = []
            if conversation_history:
                for msg in conversation_history[:-1]:  # Исключаем последнее сообщение (текущий prompt)
                    role = "user" if msg["role"] == "user" else "model"
                    gemini_history.append({
                        "role": role,
                        "parts": [{"text": msg["content"]}]
                    })

            convo = model_instance.start_chat(history=gemini_history)
            logger.info("Sending message to Gemini API...")
            response = convo.send_message(enhanced_prompt)
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
                
                # Преобразуем MapComposite в обычный словарь
                try:
                    if hasattr(tool_call_data.args, '_pb'):
                        # Если это protobuf объект, преобразуем его
                        arguments = dict(tool_call_data.args)
                    else:
                        arguments = tool_call_data.args
                except Exception as e:
                    logger.warning(f"Failed to convert args, using dict(): {e}")
                    arguments = dict(tool_call_data.args)
                
                logger.info(f"Converted arguments: {arguments}")
                
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
                    arguments=arguments,
                )
            # Проверяем, есть ли текстовый ответ
            try:
                text_response = response.text
                logger.info(
                    f"Returning text response. Text: {text_response[:100]}..."
                )
                return text_response
            except ValueError as e:
                # Если не можем получить текст, возможно есть function_call
                if "function_call" in str(e):
                    logger.warning("Response contains function_call but was not processed correctly")
                    return "Извините, произошла ошибка при обработке запроса. Попробуйте переформулировать вопрос."
                else:
                    logger.error(f"Unexpected error getting response text: {e}")
                    return "Произошла ошибка при генерации ответа."
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
                
    async def generate_response_with_audio(
        self, file_path: str, model: str, user_prompt: Optional[str] = None
    ) -> str:
        """
        Генерирует ответ от модели Google Gemini с аудио.

        Аргументы:
            file_path (str): Путь к аудиофайлу.
            model (str): Имя модели для генерации ответа.
            user_prompt (str, optional): Текст, предоставленный пользователем,
            для сопровождения аудио. По умолчанию None.

        Возвращает:
            str: Сгенерированный ответ.
        """
        try:
            logger.info(f"Генерация ответа для аудио: {file_path}")
            
            # Проверяем, поддерживает ли модель аудио
            if not any(audio_model in model for audio_model in 
                      ["gemini-2.5-flash", "gemini-2.5-pro"]):
                logger.warning(f"Модель {model} может не поддерживать аудио. "
                              "Рекомендуется использовать gemini-2.5-flash или "
                              "gemini-2.5-pro с поддержкой аудио.")
            
            model_instance = genai.GenerativeModel(model_name=model)
            
            # Загружаем аудиофайл
            audio_path = pathlib.Path(file_path)
            audio_data = audio_path.read_bytes()
            
            # Определяем MIME-тип на основе расширения файла
            file_extension = os.path.splitext(file_path)[1].lower()
            mime_type = {
                '.mp3': 'audio/mp3',
                '.wav': 'audio/wav',
                '.ogg': 'audio/ogg',
                '.flac': 'audio/flac',
                '.m4a': 'audio/m4a'
            }.get(file_extension, 'audio/ogg')  # По умолчанию ogg для голосовых сообщений Telegram
            
            # Формируем запрос
            if user_prompt:
                prompt_for_model = user_prompt
            else:
                prompt_for_model = "Пожалуйста, проанализируй это аудио и расскажи, о чем в нем говорится."
            
            # Отправляем запрос с аудио
            response = model_instance.generate_content([
                prompt_for_model,
                {"mime_type": mime_type, "data": audio_data}
            ])
            
            logger.info("Получен ответ от Gemini API для аудио")
            
            if hasattr(response, "text"):
                return response.text
            else:
                result = ""
                for chunk in response:
                    result += chunk.text
                return result
                
        except Exception as e:
            logger.error(f"Ошибка при обработке аудио: {str(e)}", exc_info=True)
            raise Exception(f"Ошибка при обработке аудио: {str(e)}")
            
    async def generate_audio_from_text(
        self, text: str, model: str = "gemini-2.5-flash-preview-native-audio-dialog",
        language: str = "ru"
    ) -> bytes:
        """
        Генерирует аудио из текста с помощью Gemini TTS.
        
        Аргументы:
            text (str): Текст для преобразования в аудио.
            model (str): Модель Gemini с поддержкой TTS.
            language (str): Код языка (например, "ru", "en").
            
        Возвращает:
            bytes: Аудиоданные в формате MP3.
        """
        try:
            logger.info(f"Генерация аудио из текста: {text[:50]}...")
            
            # Проверяем, поддерживает ли модель TTS
            if not any(tts_model in model for tts_model in 
                      ["native-audio", "preview-native-audio"]):
                logger.warning(f"Модель {model} может не поддерживать TTS. "
                              "Используйте модель с 'native-audio' в названии.")
            
            model_instance = genai.GenerativeModel(model_name=model)
            
            # Формируем запрос для генерации аудио
            prompt = f"Сгенерируй аудио на {language} языке: {text}"
            
            # Указываем, что хотим получить аудио в ответе
            response = model_instance.generate_content(
                prompt,
                generation_config={"response_mime_type": "audio/mp3"}
            )
            
            # Извлекаем аудиоданные
            if hasattr(response.parts[0], "audio") and hasattr(response.parts[0].audio, "data"):
                return response.parts[0].audio.data
            else:
                raise ValueError("Не удалось получить аудиоданные от API")
                
        except Exception as e:
            logger.error(f"Ошибка при генерации аудио: {str(e)}", exc_info=True)
            raise Exception(f"Ошибка при генерации аудио: {str(e)}")
