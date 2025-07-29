#!/usr/bin/env python3
"""
Скрипт для сброса базы данных.
ВНИМАНИЕ: Удаляет все данные!
"""
import os
import asyncio
from pathlib import Path
from bot.database.database import init_database, engine, Base

async def reset_database():
    """Сбросить базу данных."""
    try:
        # Удаляем файл базы данных
        db_path = Path("data/bot.db")
        if db_path.exists():
            db_path.unlink()
            print("✅ Старая база данных удалена")
        
        # Создаем новую базу данных
        await init_database()
        print("✅ Новая база данных создана")
        
        # Закрываем соединения
        await engine.dispose()
        print("✅ Соединения закрыты")
        
    except Exception as e:
        print(f"❌ Ошибка при сбросе базы данных: {e}")
        raise

if __name__ == "__main__":
    print("🔄 Сброс базы данных...")
    print("⚠️  ВНИМАНИЕ: Все данные будут удалены!")
    
    confirm = input("Продолжить? (y/N): ")
    if confirm.lower() != 'y':
        print("❌ Отменено")
        exit(1)
    
    asyncio.run(reset_database())
    print("✅ База данных успешно сброшена")