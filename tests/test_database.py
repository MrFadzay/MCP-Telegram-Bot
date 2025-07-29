"""
Тесты для базы данных и моделей.
"""
import pytest
from datetime import datetime
from bot.database.models import User, Session, Message


class TestUserModel:
    """Тесты модели User."""
    
    async def test_create_user(self, test_db):
        """Тест создания пользователя."""
        async with test_db() as session:
            user = User(
                user_id=123,
                username="testuser",
                first_name="Test",
                last_name="User"
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            
            assert user.user_id == 123
            assert user.username == "testuser"
            assert user.first_name == "Test"
            assert user.last_name == "User"
            assert user.llm_provider == "google"  # default
            assert user.llm_model == "gemini-2.5-flash"  # default
    
    async def test_user_relationships(self, test_db):
        """Тест связей пользователя."""
        async with test_db() as session:
            user = User(user_id=123, username="testuser")
            session.add(user)
            await session.flush()
            
            # Создаем сессию
            chat_session = Session(user_id=user.user_id, session_name="Test Session")
            session.add(chat_session)
            await session.flush()
            
            # Создаем сообщение
            message = Message(
                user_id=user.user_id,
                session_id=chat_session.id,
                message_type="user",
                role="user",
                content="Test message"
            )
            session.add(message)
            await session.commit()
            
            # Проверяем связи
            await session.refresh(user)
            assert len(user.sessions) == 1
            assert len(user.messages) == 1
            assert user.sessions[0].session_name == "Test Session"
            assert user.messages[0].content == "Test message"


class TestSessionModel:
    """Тесты модели Session."""
    
    async def test_create_session(self, test_db, test_user):
        """Тест создания сессии."""
        async with test_db() as session:
            chat_session = Session(
                user_id=test_user.user_id,
                session_name="Test Session"
            )
            session.add(chat_session)
            await session.commit()
            await session.refresh(chat_session)
            
            assert chat_session.user_id == test_user.user_id
            assert chat_session.session_name == "Test Session"
            assert chat_session.is_active is True
            assert chat_session.ended_at is None
    
    async def test_end_session(self, test_db, test_user):
        """Тест завершения сессии."""
        async with test_db() as session:
            chat_session = Session(user_id=test_user.user_id)
            session.add(chat_session)
            await session.flush()
            
            # Завершаем сессию
            chat_session.is_active = False
            chat_session.ended_at = datetime.utcnow()
            await session.commit()
            
            assert chat_session.is_active is False
            assert chat_session.ended_at is not None


class TestMessageModel:
    """Тесты модели Message."""
    
    async def test_create_message(self, test_db, test_user):
        """Тест создания сообщения."""
        async with test_db() as session:
            # Создаем сессию
            chat_session = Session(user_id=test_user.user_id)
            session.add(chat_session)
            await session.flush()
            
            # Создаем сообщение
            message = Message(
                user_id=test_user.user_id,
                session_id=chat_session.id,
                message_type="user",
                role="user",
                content="Test message",
                message_metadata={"test": "data"}
            )
            session.add(message)
            await session.commit()
            await session.refresh(message)
            
            assert message.user_id == test_user.user_id
            assert message.session_id == chat_session.id
            assert message.message_type == "user"
            assert message.role == "user"
            assert message.content == "Test message"
            assert message.message_metadata == {"test": "data"}
            assert message.tokens_used == 0  # default
            assert message.processing_time_ms == 0  # default