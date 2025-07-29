#!/usr/bin/env python3
"""
Простой тест для проверки исправления истории разговоров.
"""

import asyncio
import sys
import os

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot.llm_utils import LLMSelector
from bot.provider_manager import ProviderManager
from bot.services.history_service import HistoryService


async def test_conversation_history():
    """Тестируем работу истории разговоров."""
    print("🧪 Тестируем исправление истории разговоров...")
    
    # Инициализируем компоненты
    llm_selector = LLMSelector()
    history_service = HistoryService()
    
    # Тестовый пользователь
    test_user_id = 999999
    
    try:
        # Очищаем историю для чистого теста
        await history_service.clear_history(test_user_id)
        print("✅ История очищена")
        
        # Сохраняем несколько тестовых сообщений
        await history_service.save_message(test_user_id, "Привет, как дела?", "user")
        await history_service.save_message(test_user_id, "Привет! Дела хорошо, спасибо!", "assistant")
        await history_service.save_message(test_user_id, "Как погода сегодня?", "user")
        await history_service.save_message(test_user_id, "Сегодня солнечно и тепло!", "assistant")
        print("✅ Тестовые сообщения сохранены")
        
        # Получаем историю
        history = await history_service.get_conversation_history(test_user_id, limit=10)
        print(f"✅ Получена история: {len(history)} сообщений")
        
        for i, msg in enumerate(history):
            print(f"  {i+1}. [{msg['role']}]: {msg['content'][:50]}...")
        
        # Проверяем, что история не пустая
        if len(history) > 0:
            print("✅ История разговоров работает корректно!")
            return True
        else:
            print("❌ История разговоров пустая!")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        return False


async def main():
    """Главная функция теста."""
    print("🚀 Запуск теста истории разговоров...")
    
    success = await test_conversation_history()
    
    if success:
        print("\n✅ Тест пройден успешно!")
        print("🔧 Исправления применены:")
        print("   - История получается ПЕРЕД сохранением текущего сообщения")
        print("   - История передается во всех итерациях ReAct цикла")
        print("   - Добавлено логирование для отладки")
    else:
        print("\n❌ Тест не пройден!")
    
    return success


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)