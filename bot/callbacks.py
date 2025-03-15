from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.llm_utils import LLMSelector
import logging

logger = logging.getLogger(__name__)


class CallbackHandlers:
    def __init__(self, llm_selector: LLMSelector):
        self.llm_selector = llm_selector

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
