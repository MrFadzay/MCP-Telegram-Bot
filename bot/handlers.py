from telegram import Update
from telegram.ext import ContextTypes
import logging
import tempfile
from bot.llm_utils import LLMSelector
from bot.utils import download_photo, cleanup_temp_file

logger = logging.getLogger(__name__)


class MessageHandlers:
    def __init__(self, llm_selector: LLMSelector):
        self.llm_selector = llm_selector

    async def handle_message(
            self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик текстовых сообщений"""
        if update.message:
            try:
                config = self.llm_selector.get_current_config()
                if not config:
                    await update.message.reply_text(
                        "Пожалуйста, сначала выберите провайдера и "
                        "модель с помощью команды /select"
                    )
                    return

                user_message = update.message.text
                try:
                    response = await self.llm_selector.generate_response(
                        user_message
                    )
                    if response:
                        await update.message.reply_text(response)
                    else:
                        logger.error(
                            f"generate_response вернул None for message: {user_message}")
                        await update.message.reply_text(
                            "Произошла внутренняя ошибка. "
                            "Повторите попытку позже."
                        )
                except Exception as e:
                    logger.error(f"Ошибка при генерации ответа: {str(e)}")
                    await update.message.reply_text(
                        "Произошла ошибка при генерации ответа. "
                        "Попробуйте выбрать другую модель или повторить позже."
                    )

            except Exception as e:
                logger.error(f"Ошибка при обработке сообщения: {str(e)}")
                await update.message.reply_text(
                    "Произошла ошибка при обработке вашего сообщения.")
        else:
            logger.warning(f"Получено обновление без сообщения: {update}")
            return

    async def _download_photo(self, update: Update) -> str:
        """Скачивание фотографии во временный файл."""
        photo_file = await update.message.photo[-1].get_file()
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            await photo_file.download_to_drive(temp_file.name)
            return temp_file.name

    async def _process_photo(self, file_path: str, user_caption: str) -> str:
        """Отправка фотографии в LLM и получение ответа."""
        try:
            response = await self.llm_selector.generate_response_with_image(
                file_path, user_caption
            )
            if response:
                return response
            else:
                logger.error(
                    f"generate_response_with_image returned None for file: {file_path}")
                return "Произошла ошибка при обработке изображения."
        except Exception as e:
            logger.error(f"Ошибка при генерации ответа для фото: {str(e)}")
            return "Произошла ошибка при генерации ответа для фото."
        finally:
            cleanup_temp_file(file_path)

    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик входящих фотографий"""
        if update.message and update.message.photo:
            try:
                config = self.llm_selector.get_current_config()
                if not config:
                    await update.message.reply_text(
                        "Пожалуйста, сначала выберите провайдера и "
                        "модель с помощью команды /select"
                    )
                    return

                user_caption = update.message.caption
                file_path = await download_photo(update)
                response = await self._process_photo(file_path, user_caption)
                await update.message.reply_text(response)

            except Exception as e:
                logger.error(f"Ошибка при обработке фотографии: {str(e)}")
                await update.message.reply_text(
                    "Произошла ошибка при обработке вашего фото.")
        else:
            logger.warning(f"Получено обновление без фото: {update}")
            return
