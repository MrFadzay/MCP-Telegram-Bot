from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, File
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes)
from dotenv import load_dotenv
import os
import logging
import tempfile

from bot.llm_utils import LLMSelector

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')


class TelegramBot:
    def __init__(self):
        self.application = Application.builder().token(TELEGRAM_TOKEN).build()
        self.llm_selector = LLMSelector()
        self._setup_handlers()

    def _setup_handlers(self):
        """Настройка обработчиков команд и сообщений"""
        self.application.add_handler(
            CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler(
            "select", self.select_provider_command))
        self.application.add_handler(
            CallbackQueryHandler(self.button_callback))
        self.application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.application.add_handler(MessageHandler(
            filters.PHOTO, self.handle_photo))  # Added photo handler

    async def select_provider_command(
            self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды выбора провайдера"""
        if update.message:
            providers = await self.llm_selector.get_available_providers()
            keyboard = []

            for provider in providers:
                keyboard.append([InlineKeyboardButton(
                    provider.upper(), callback_data=f"provider_{provider}")])

            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                'Выберите провайдера:', reply_markup=reply_markup)
        else:
            logger.warning(f"Received update without message: {update}")
            return

    async def show_models(self, update: Update, provider: str):
        """Показать доступные модели для выбранного провайдера"""
        if update.callback_query:
            models = await self.llm_selector.get_available_models(provider)
            keyboard = []

            if models:
                for model in models:
                    keyboard.append([InlineKeyboardButton(
                        model, callback_data=f"model_{model}")])

                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.callback_query.edit_message_text(
                    f'Выберите модель для {provider.upper()}:',
                    reply_markup=reply_markup)
            else:
                await update.callback_query.edit_message_text(
                    f"Нет доступных моделей для провайдера {provider.upper()}")
        elif update.callback_query:
            logger.warning(f"Получено обновление без callback_query: {update}")
            return

    async def button_callback(
            self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатий на кнопки"""
        if update.callback_query:
            query = update.callback_query
            await query.answer()

            data = query.data
            if data.startswith("provider_"):
                provider = data.split("_")[1]
                self.llm_selector.set_provider(provider)
                await self.show_models(update, provider)

            elif data.startswith("model_"):
                model = data.split("_")[1]
                await self.llm_selector.set_model(model)
                config = self.llm_selector.get_current_config()

                await query.edit_message_text(
                    f"Выбрано: провайдер {config.provider_name.upper()}, модель {config.model_name}"
                )

        else:
            logger.warning(f"Получено обновление без callback_query: {update}")
            return

    async def help_command(
            self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        if update.message:
            help_text = """
    Доступные команды:
    /start - Начать разговор
    /help - Показать это сообщение
    /select - Выбрать провайдера и модель LLM
            """
            await update.message.reply_text(help_text)
        else:
            logger.warning(f"Получено обновление без сообщения: {update}")
            return

    async def start_command(
            self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        if update.message:
            welcome_text = """
        Привет! Я бот с поддержкой различных LLM моделей.
        Для начала работы выберите провайдера и
        модель с помощью команды /select
        Для просмотра доступных команд используйте /help
            """
            await update.message.reply_text(welcome_text)
        else:
            logger.warning(f"Получено обновление без сообщения: {update}")
            return

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

                photo_file = await update.message.photo[-1].get_file()
                user_caption = update.message.caption

                with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                    await photo_file.download_to_drive(temp_file.name)
                    file_path = temp_file.name

                try:
                    response = await self.llm_selector.generate_response_with_image(
                        file_path, user_caption
                    )
                    if response:
                        await update.message.reply_text(response)
                    else:
                        logger.error(
                            f"generate_response_with_image returned None for file: {file_path}")
                        await update.message.reply_text(
                            "Произошла внутренняя ошибка при обработке изображения. "
                            "Повторите попытку позже."
                        )
                except Exception as e:
                    logger.error(
                        f"Ошибка при генерации ответа для фото: {str(e)}")
                    await update.message.reply_text(
                        "Произошла ошибка при генерации ответа для фото. "
                        "Попробуйте выбрать другую модель или повторить позже."
                    )
                finally:
                    os.unlink(file_path)
            except Exception as e:
                logger.error(f"Ошибка при обработке фотографии: {str(e)}")
                await update.message.reply_text(
                    "Произошла ошибка при обработке вашего фото.")
        else:
            logger.warning(f"Получено обновление без фото: {update}")
            return
