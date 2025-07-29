from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters)
from telegram import BotCommand
from dotenv import load_dotenv
import os
import logging
from bot.llm_utils import LLMSelector
from bot import CommandHandlers, MessageHandlers, CallbackHandlers

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

        self.command_handlers = CommandHandlers(self.llm_selector)
        self.message_handlers = MessageHandlers(self.llm_selector)
        self.callback_handlers = CallbackHandlers(self.llm_selector)

        self._setup_handlers()

    def _setup_handlers(self):
        """Настройка обработчиков команд и сообщений"""
        self.application.add_handler(CommandHandler(
            "start", self.command_handlers.start_command))
        self.application.add_handler(CommandHandler(
            "help", self.command_handlers.help_command))
        self.application.add_handler(CommandHandler(
            "select", self.command_handlers.select_command))
        self.application.add_handler(CommandHandler(
            "settings", self.command_handlers.settings_command))
        self.application.add_handler(CommandHandler(
            "tools", self.command_handlers.tools_command))
        self.application.add_handler(CommandHandler(
            "history", self.command_handlers.history_command))
        self.application.add_handler(CommandHandler(
            "clear", self.command_handlers.clear_history_command))
        self.application.add_handler(CallbackQueryHandler(
            self.callback_handlers.button_callback))
        self.application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, self.message_handlers.handle_message))
        self.application.add_handler(MessageHandler(
            filters.PHOTO, self.message_handlers.handle_photo))
        self.application.add_handler(MessageHandler(
            filters.VOICE, self.message_handlers.handle_voice))
        self.application.add_handler(MessageHandler(
            filters.Document, self.message_handlers.handle_document))

    async def _setup_commands(self):
        """Установка команд в меню Telegram"""
        commands = [
            BotCommand("start", "🚀 Начать работу с ботом"),
            BotCommand("help", "📚 Показать справку по командам"),
            BotCommand("select", "⚙️ Выбрать LLM провайдера и модель"),
            BotCommand("settings", "🔧 Показать настройки пользователя"),
            BotCommand("tools", "🛠️ Показать доступные MCP инструменты"),
            BotCommand("history", "📊 Статистика текущей сессии"),
            BotCommand("clear", "🗑️ Очистить историю диалога"),
        ]

        try:
            await self.application.bot.set_my_commands(commands)
            logger.info("✅ Команды успешно установлены в меню Telegram")
        except Exception as e:
            logger.error(f"❌ Ошибка при установке команд: {e}")

    async def start(self):
        """Запуск бота"""
        try:
            # Инициализируем приложение
            await self.application.initialize()

            # Устанавливаем команды
            await self._setup_commands()

            # Запускаем бота
            await self.application.start()
            await self.application.updater.start_polling()

            logger.info("🤖 Бот запущен и готов к работе!")

        except Exception as e:
            logger.error(f"❌ Ошибка при запуске бота: {e}")
            raise

    async def stop(self):
        """Остановка бота"""
        try:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
            logger.info("🛑 Бот остановлен")
        except Exception as e:
            logger.error(f"❌ Ошибка при остановке бота: {e}")
