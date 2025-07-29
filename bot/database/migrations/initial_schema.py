"""
Начальная миграция для создания схемы базы данных.
Создает таблицы User, Session, Message.
"""

from sqlalchemy import text
from bot.database.database import get_db_session, sync_engine
from bot.database.models import Base
import logging

logger = logging.getLogger(__name__)


def upgrade():
    """Применить миграцию - создать все таблицы."""
    try:
        logger.info("Создание таблиц базы данных...")
        
        # Создаем все таблицы
        Base.metadata.create_all(bind=sync_engine)
        
        logger.info("✅ Таблицы успешно созданы")
        
        # Проверяем, что таблицы созданы
        with get_db_session() as db:
            result = db.execute(text("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """))
            tables = [row[0] for row in result.fetchall()]
            logger.info(f"Созданные таблицы: {tables}")
            
    except Exception as e:
        logger.error(f"Ошибка при создании таблиц: {e}")
        raise


def downgrade():
    """Откатить миграцию - удалить все таблицы."""
    try:
        logger.info("Удаление таблиц базы данных...")
        
        # Удаляем все таблицы
        Base.metadata.drop_all(bind=sync_engine)
        
        logger.info("✅ Таблицы успешно удалены")
        
    except Exception as e:
        logger.error(f"Ошибка при удалении таблиц: {e}")
        raise


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Использование: python 001_initial_schema.py [upgrade|downgrade]")
        sys.exit(1)
    
    action = sys.argv[1]
    
    if action == "upgrade":
        upgrade()
        print("Миграция применена успешно!")
    elif action == "downgrade":
        downgrade()
        print("Миграция откачена успешно!")
    else:
        print("Неизвестное действие. Используйте 'upgrade' или 'downgrade'")
        sys.exit(1)