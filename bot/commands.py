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
    /tools - Показать доступные MCP инструменты
            """
            await update.message.reply_text(help_text)
        else:
            logger.warning(
                f"Получено обновление без сообщения: {update}")
            return
            
    async def tools_command(
            self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /tools - показывает доступные MCP инструменты"""
        if update.message:
            try:
                tools = await self.llm_selector.get_available_mcp_tools()
                
                if not tools:
                    await update.message.reply_text(
                        "В данный момент нет доступных MCP инструментов. "
                        "Возможно, MCP серверы не запущены или не настроены."
                    )
                    return
                
                # Фильтруем мета-инструмент
                tools = [tool for tool in tools 
                         if not (tool.server_name == "meta" and 
                                 tool.tool_name == "list_mcp_tools")]
                
                if not tools:
                    await update.message.reply_text(
                        "В данный момент нет доступных MCP инструментов. "
                        "Возможно, MCP серверы не запущены или не настроены."
                    )
                    return
                
                tools_text = "Доступные MCP инструменты:\n\n"
                for tool in tools:
                    tools_text += f"📌 {tool.server_name}/{tool.tool_name}\n"
                    tools_text += f"   {tool.description}\n\n"
                
                tools_text += ("\nДля использования этих инструментов просто задайте вопрос, "
                              "и LLM автоматически выберет подходящий инструмент, если необходимо.")
                
                await update.message.reply_text(tools_text)
            except Exception as e:
                logger.error(f"Ошибка при получении списка MCP инструментов: {e}")
                await update.message.reply_text(
                    "Произошла ошибка при получении списка MCP инструментов."
                )
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
