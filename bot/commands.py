from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.llm_utils import LLMSelector
from bot.services.user_service import UserService
import logging

logger = logging.getLogger(__name__)


class CommandHandlers:
    def __init__(self, llm_selector: LLMSelector):
        self.llm_selector = llm_selector

    async def start_command(
            self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        if not update.message or not update.message.from_user:
            return

        # Create or update user in database
        user = await UserService.get_or_create_user(
            update.message.from_user.id,
            update.message.from_user
        )

        welcome_text = f"""
👋 Привет, {user.first_name or 'пользователь'}!

Я бот с поддержкой различных LLM моделей и MCP инструментов.

🤖 Текущие настройки:
• Провайдер: {user.llm_provider.upper()}
• Модель: {user.llm_model}
• Стиль ответов: {user.response_style}

📋 Основные команды:
/select - Выбрать провайдера и модель
/settings - Показать все настройки
/tools - Доступные MCP инструменты
/help - Помощь

Просто напишите мне любой вопрос, и я отвечу используя ваши настройки!
        """
        await update.message.reply_text(welcome_text)

    async def help_command(
            self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        help_text = """
🤖 MCP Telegram Bot - Помощь

📋 Основные команды:
/start - Начать работу с ботом
/select - Выбрать LLM провайдера и модель
/settings - Показать текущие настройки
/tools - Список доступных MCP инструментов
/history - Статистика текущей сессии
/clear - Очистить историю диалога
/help - Показать эту справку

💬 Использование:
• Просто отправьте текстовое сообщение для получения ответа
• Отправьте фото с описанием для анализа изображения
• Отправьте голосовое сообщение для обработки аудио
• Отправьте документ для анализа содержимого

🔧 Настройки:
• Используйте /select для выбора LLM провайдера (Google, OpenAI, Ollama)
• Каждый провайдер имеет свои модели с разными возможностями
• Настройки сохраняются автоматически

🛠️ MCP инструменты:
• Бот поддерживает расширение функциональности через MCP серверы
• Используйте /tools для просмотра доступных инструментов
• Инструменты подключаются автоматически при необходимости

❓ Проблемы:
• Если бот не отвечает, проверьте выбранного провайдера командой /settings
• Для сброса настроек используйте /start
• История диалога очищается командой /clear
        """
        await update.message.reply_text(help_text)

    async def select_command(
            self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /select - выбор провайдера LLM"""
        keyboard = [
            [
                InlineKeyboardButton(
                    "🔵 Google Gemini", callback_data="provider_google"),
                InlineKeyboardButton(
                    "🟢 OpenAI GPT", callback_data="provider_openai")
            ],
            [
                InlineKeyboardButton("🟠 Ollama (Local)",
                                     callback_data="provider_ollama")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "🤖 Выберите LLM провайдера:",
            reply_markup=reply_markup
        )

    async def tools_command(
            self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /tools - показывает доступные MCP инструменты"""
        try:
            tools = await self.llm_selector.get_available_mcp_tools()

            if not tools:
                await update.message.reply_text(
                    "🔧 MCP инструменты не настроены или недоступны.\n\n"
                    "Проверьте конфигурацию MCP серверов в config/mcp_servers.json"
                )
                return

            tools_text = "🛠️ Доступные MCP инструменты:\n\n"

            for tool in tools:
                tools_text += f"🔹 **{tool.tool_name}**\n"
                tools_text += f"   {tool.description}\n\n"

            tools_text += "💡 Инструменты используются автоматически при необходимости"

            await update.message.reply_text(tools_text, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Ошибка при получении MCP инструментов: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка при получении списка инструментов."
            )

    async def settings_command(
            self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /settings - показывает настройки пользователя"""
        if not update.message or not update.message.from_user:
            return

        try:
            user_id = update.message.from_user.id
            settings = await UserService.get_user_settings(user_id)

            if not settings:
                await update.message.reply_text(
                    "❌ Не удалось получить ваши настройки. "
                    "Попробуйте выполнить команду /start для инициализации."
                )
                return

            settings_text = f"""
⚙️ Ваши настройки:

👤 Профиль:
• ID: {settings['user_id']}
• Имя: {settings['first_name'] or 'не указано'}
• Username: @{settings['username'] or 'не указан'}

🤖 LLM настройки:
• Провайдер: {settings['llm_provider'].upper()}
• Модель: {settings['llm_model']}

🎨 Персонализация:
• Стиль ответов: {settings['response_style']}

📅 Активность:
• Создан: {settings['created_at'].strftime('%d.%m.%Y %H:%M')}
• Обновлен: {settings['updated_at'].strftime('%d.%m.%Y %H:%M')}
• Последняя активность: {settings['last_activity'].strftime('%d.%m.%Y %H:%M')}

💡 Используйте /select для изменения LLM настроек
            """

            await update.message.reply_text(settings_text)

        except Exception as e:
            logger.error(f"Ошибка при получении настроек пользователя: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка при получении настроек."
            )

    async def clear_history_command(
            self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /clear - очищает историю диалога"""
        if not update.message or not update.message.from_user:
            return

        try:
            user_id = update.message.from_user.id

            # Получаем статистику перед очисткой
            stats = await self.llm_selector.history_service.get_session_stats(user_id)

            # Очищаем историю
            cleared = await self.llm_selector.history_service.clear_history(user_id)

            if cleared:
                await update.message.reply_text(
                    f"✅ История диалога очищена!\n\n"
                    f"📊 Статистика завершенной сессии:\n"
                    f"• Сообщений: {stats['messages']}\n"
                    f"• Длительность: {stats['session_duration']} мин\n\n"
                    f"🆕 Начинается новая сессия диалога."
                )
            else:
                await update.message.reply_text(
                    "ℹ️ История диалога уже пуста или не найдена активная сессия."
                )

        except Exception as e:
            logger.error(f"Ошибка при очистке истории: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка при очистке истории диалога."
            )

    async def history_command(
            self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /history - показывает статистику текущей сессии"""
        if not update.message or not update.message.from_user:
            return

        try:
            user_id = update.message.from_user.id

            # Получаем статистику сессии
            stats = await self.llm_selector.history_service.get_session_stats(user_id)

            if stats['messages'] == 0:
                await update.message.reply_text(
                    "📭 В текущей сессии пока нет сообщений.\n"
                    "Начните диалог, отправив любое сообщение!"
                )
                return

            # Получаем последние несколько сообщений для превью
            history = await self.llm_selector.history_service.get_conversation_history(
                user_id=user_id,
                limit=3
            )

            history_text = f"""
📊 Статистика текущей сессии:

💬 Сообщений: {stats['messages']}
⏱️ Длительность: {stats['session_duration']} мин
🕐 Начало сессии: {stats['session_start'][:16].replace('T', ' ')}

📝 Последние сообщения:
            """

            for msg in history[-3:]:  # Показываем последние 3 сообщения
                role_emoji = "👤" if msg["role"] == "user" else "🤖"
                content_preview = msg["content"][:50] + \
                    "..." if len(msg["content"]) > 50 else msg["content"]
                history_text += f"{role_emoji} {content_preview}\n"

            history_text += f"\n💡 Используйте /clear для очистки истории"

            await update.message.reply_text(history_text)

        except Exception as e:
            logger.error(f"Ошибка при получении истории: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка при получении истории диалога."
            )
