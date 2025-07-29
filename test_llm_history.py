#!/usr/bin/env python3
"""
Тест для проверки работы LLM с историей разговоров.
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot.llm_utils import LLMSelector
from bot.services.history_service import HistoryService


async def test_llm_with_history():
    """Тестируем работу LLM с историей разговоров."""
    print("🧪 Тестируем работу LLM с историей разговоров...")
    
    # Инициализируем компоненты
    llm_selector = LLMSelector()
    history_service = HistoryService()
    
    # Тестовый пользователь
    test_user_id = 888888
    
    try:
        # Очищаем историю для чистого теста
        await history_service.clear_history(test_user_id)
        print("✅ История очищена")
        
        # Настраиваем провайдера (Google Gemini)
        await llm_selector.provider_manager.set_provider("google")
        await llm_selector.provider_manager.set_model("models/gemini-2.5-flash")
        print("✅ Провайдер настроен: Google Gemini")
        
        # Первый диалог - представляемся
        print("\n📝 Первое сообщение: представляемся")
        response1 = await llm_selector.generate_response(
            "Привет! Меня зовут Алексей, мне 25 лет, я программист.",
            user_id=test_user_id
        )
        print(f"🤖 Ответ LLM: {response1}")
        
        # Второй диалог - спрашиваем о погоде
        print("\n📝 Второе сообщение: спрашиваем о погоде")
        response2 = await llm_selector.generate_response(
            "Как погода в Москве?",
            user_id=test_user_id
        )
        print(f"🤖 Ответ LLM: {response2}")
        
        # Третий диалог - проверяем память
        print("\n📝 Третье сообщение: проверяем память")
        response3 = await llm_selector.generate_response(
            "Как меня зовут и сколько мне лет?",
            user_id=test_user_id
        )
        print(f"🤖 Ответ LLM: {response3}")
        
        # Проверяем, упоминает ли LLM имя и возраст
        if "Алексей" in response3 and "25" in response3:
            print("✅ LLM помнит информацию из истории!")
            return True
        else:
            print("❌ LLM не помнит информацию из истории")
            print(f"   Ожидали упоминание 'Алексей' и '25' в ответе: {response3}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Главная функция теста."""
    print("🚀 Запуск теста LLM с историей разговоров...")
    
    # Проверяем наличие API ключа
    if not os.getenv("GOOGLE_API_KEY"):
        print("❌ Не найден GOOGLE_API_KEY в переменных окружения")
        print("   Убедитесь, что файл .env содержит GOOGLE_API_KEY")
        return False
    
    success = await test_llm_with_history()
    
    if success:
        print("\n✅ Тест пройден успешно!")
        print("🎉 LLM корректно использует историю разговоров!")
    else:
        print("\n❌ Тест не пройден!")
        print("🔧 Возможные причины:")
        print("   - История не передается в LLM")
        print("   - LLM не понимает, что у него есть доступ к истории")
        print("   - Проблема с форматированием истории")
    
    return success


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)