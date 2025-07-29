from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.llm_utils import LLMSelector
from bot.services.user_service import UserService
import logging

logger = logging.getLogger(__name__)


class CallbackHandlers:
    def __init__(self, llm_selector: LLMSelector):
        self.llm_selector = llm_selector

    async def show_models(self, update: Update, provider: str):
        """Показать доступные модели для выбранного провайдера"""
        if update.callback_query:
            models = await self.llm_selector.provider_manager.get_available_models(provider)
            keyboard = []

            if models:
                for model in models:
                    keyboard.append([InlineKeyboardButton(
                        model, callback_data=f"model_select_{model}")])

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
            if not data:
                return
                
            if data.startswith("provider_"):
                provider = data.split("_")[1]
                user_id = query.from_user.id
                await self.llm_selector.provider_manager.set_provider(provider, user_id)
                await self.show_models(update, provider)

            elif data.startswith("model_select_"):
                model = data.split("model_select_")[1]
                user_id = query.from_user.id
                await self.llm_selector.provider_manager.set_model(model, user_id)
                config = self.llm_selector.provider_manager.get_current_config()

                if config:
                    await query.edit_message_text(
                        f"✅ Выбрано и сохранено: провайдер {config.provider_name.upper()}, "
                        f"модель {config.model_name}\n\n"
                        f"Ваши настройки автоматически сохранены и будут восстановлены "
                        f"при следующем запуске бота."
                    )
                else:
                    await query.edit_message_text(
                        "❌ Не удалось получить текущую конфигурацию модели."
                    )

        else:
            logger.warning(f"Получено обновление без callback_query: {update}")
            return
