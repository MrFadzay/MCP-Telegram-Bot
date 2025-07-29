"""
Тесты для сервисов.
"""
import pytest
from unittest.mock import patch, AsyncMock
from bot.services.user_service import UserService
from bot.services.history_service import HistoryService
from bot.database.models import User, Session, Message


class TestUserService:
    """Тесты UserService."""

    @patch('bot.services.user_service.get_async_db_session')
    async def test_get_or_create_user_new(self, mock_session):
        """Тест создания нового пользователя."""
        # Настраиваем мок
        mock_db = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_db

        # Пользователь не найден
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        # Создаем пользователя
        user = await UserService.get_or_create_user(12345)

        # Проверяем, что пользователь был добавлен
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @patch('bot.services.user_service.get_async_db_session')
    async def test_update_llm_settings(self, mock_session):
        """Тест обновления настроек LLM."""
        mock_db = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_db

        # Мокаем результат обновления
        mock_result = AsyncMock()
        mock_result.rowcount = 1
        mock_db.execute.return_value = mock_result

        result = await UserService.update_llm_settings(
            12345,
            provider="openai",
            model="gpt-4"
        )

        assert result is True
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()


class TestHistoryService:
    """Тесты HistoryService."""

    def setup_method(self):
        """Настройка перед каждым тестом."""
        self.history_service = HistoryService()

    @patch('bot.services.history_service.get_async_db_session')
    async def test_save_message(self, mock_session):
        """Тест сохранения сообщения."""
        mock_db = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_db

        # Мокаем пользователя
        mock_user = User(user_id=12345, username="test")
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result

        # Мокаем сессию
        mock_session_obj = Session(id=1, user_id=12345)
        with patch.object(self.history_service, '_get_or_create_session',
                          return_value=mock_session_obj):

            await self.history_service.save_message(
                12345,
                "Test message",
                "user"
            )

            # Проверяем, что сообщение было добавлено
            mock_db.add.assert_called()
            mock_db.commit.assert_called_once()

    @patch('bot.services.history_service.get_async_db_session')
    async def test_get_conversation_history_empty(self, mock_session):
        """Тест получения пустой истории."""
        mock_db = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_db

        # Пользователь не найден
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        history = await self.history_service.get_conversation_history(12345)

        assert history == []

    @patch('bot.services.history_service.get_async_db_session')
    async def test_clear_history(self, mock_session):
        """Тест очистки истории."""
        mock_db = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_db

        # Мокаем пользователя
        mock_user = User(user_id=12345)
        mock_user_result = AsyncMock()
        mock_user_result.scalar_one_or_none.return_value = mock_user

        # Мокаем активную сессию
        mock_session_obj = Session(id=1, user_id=12345, is_active=True)
        mock_session_result = AsyncMock()
        mock_session_result.scalar_one_or_none.return_value = mock_session_obj

        mock_db.execute.side_effect = [mock_user_result, mock_session_result]

        result = await self.history_service.clear_history(12345)

        assert result is True
        assert mock_session_obj.is_active is False
        assert mock_session_obj.ended_at is not None
        mock_db.commit.assert_called_once()

    async def test_set_context_limits(self):
        """Тест настройки ограничений контекста."""
        self.history_service.set_context_limits(
            max_messages=50, window_hours=48)

        assert self.history_service.max_context_messages == 50
        assert self.history_service.context_window_hours == 48
