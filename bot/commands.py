from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.llm_utils import LLMSelector
import logging

logger = logging.getLogger(__name__)


class CommandHandlers:
    def __init__(self, llm_selector: LLMSelector):
        self.llm_selector = llm_selector

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
            logger.warning(
                f"Получено обновление без сообщения: {update}")
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
            logger.warning(
                f"Получено обновление без сообщения: {update}")
            return

    async def select_provider_command(
            self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды выбора провайдера"""
        if update.message:
            providers = await (
                self.llm_selector.provider_manager.get_available_providers()
            )
            keyboard = []

            for provider in providers:
                keyboard.append([InlineKeyboardButton(
                    provider.upper(), callback_data=f"provider_{provider}")])

            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                'Выберите провайдера:', reply_markup=reply_markup)
        else:
            logger.warning(
                f"Получено обновление без сообщения: {update}")
            return
