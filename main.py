from telegram import Update
from bot.bot import TelegramBot
from llm.ollama import OllamaClient
from llm.google import GoogleClient


def main():
    bot = TelegramBot()

    bot.llm_selector.register_provider(OllamaClient)
    bot.llm_selector.register_provider(GoogleClient)

    print("Бот запущен...")
    bot.application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
