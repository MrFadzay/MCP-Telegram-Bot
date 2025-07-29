#!/usr/bin/env python3
"""
Скрипт для управления миграциями базы данных.
"""

import sys
import os
import logging
from pathlib import Path

# Добавляем корневую директорию в путь для импорта модулей
sys.path.insert(0, str(Path(__file__).parent))

from bot.database.migrations.initial_schema import upgrade, downgrade

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Главная функция для управления миграциями."""
    if len(sys.argv) < 2:
        print("""
Использование: python migrate.py <команда>

Доступные команды:
  init     - Инициализация базы данных (создание всех таблиц)
  reset    - Сброс базы данных (удаление и пересоздание таблиц)
  status   - Показать статус базы данных
        """)
        sys.exit(1)
    
    command = sys.argv[1]
    
    try:
        if command == "init":
            logger.info("🚀 Инициализация базы данных...")
            upgrade()
            logger.info("✅ База данных успешно инициализирована!")
            
        elif command == "reset":
            logger.info("🔄 Сброс базы данных...")
            
            # Подтверждение от пользователя
            confirm = input("⚠️  Это удалит ВСЕ данные! Продолжить? (yes/no): ")
            if confirm.lower() != 'yes':
                logger.info("Операция отменена")
                return
                
            downgrade()
            upgrade()
            logger.info("✅ База данных успешно сброшена!")
            
        elif command == "status":
            logger.info("📊 Проверка статуса базы данных...")
            
            from bot.database.database import get_db_session
            from sqlalchemy import text
            
            try:
                with get_db_session() as db:
                    # Проверяем существование таблиц
                    result = db.execute(text("""
                        SELECT name FROM sqlite_master 
                        WHERE type='table' AND name NOT LIKE 'sqlite_%'
                    """))
                    tables = [row[0] for row in result.fetchall()]
                    
                    if tables:
                        logger.info(f"✅ Найдены таблицы: {', '.join(tables)}")
                        
                        # Проверяем количество записей в каждой таблице
                        for table in tables:
                            count_result = db.execute(text(f"SELECT COUNT(*) FROM {table}"))
                            count = count_result.fetchone()[0]
                            logger.info(f"   {table}: {count} записей")
                    else:
                        logger.info("❌ Таблицы не найдены. Выполните 'python migrate.py init'")
                        
            except Exception as e:
                logger.error(f"❌ Ошибка при проверке базы данных: {e}")
                logger.info("💡 Возможно, база данных не инициализирована. Выполните 'python migrate.py init'")
                
        else:
            logger.error(f"❌ Неизвестная команда: {command}")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❌ Ошибка при выполнении команды '{command}': {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()