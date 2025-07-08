from telegram import Update
from telegram.ext import ContextTypes
import logging
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
                config = \
                    self.llm_selector.provider_manager.get_current_config()
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
                            f"generate_response вернул None для сообщения: "
                            f"{user_message}")
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
            logger.warning(
                f"Получено обновление без сообщения: {update}"
            )
            return

    async def handle_photo(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Обработчик входящих фотографий"""
        if update.message and update.message.photo:
            try:
                config = \
                    self.llm_selector.provider_manager.get_current_config()
                if not config:
                    await update.message.reply_text(
                        "Пожалуйста, сначала выберите провайдера и "
                        "модель с помощью команды /select"
                    )
                    return

                user_caption = update.message.caption
                file_path = await download_photo(update)
                response = await self.llm_selector.generate_response_with_image(
                    file_path,
                    user_caption
                )
                if response:
                    await update.message.reply_text(response)
                else:
                    logger.error(
                        f"generate_response_with_image вернул None для файла: "
                        f"{file_path}"
                    )
                    await update.message.reply_text(
                        "Произошла ошибка при обработке изображения."
                    )
                cleanup_temp_file(file_path)

            except Exception as e:
                logger.error(f"Ошибка при обработке фотографии: {str(e)}")
                await update.message.reply_text(
                    "Произошла ошибка при обработке вашего фото.")
        else:
            logger.warning(
                f"Получено обновление без фото: {update}"
            )
            return
