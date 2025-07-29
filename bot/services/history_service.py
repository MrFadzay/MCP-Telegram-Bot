"""
История сообщений для Telegram бота.
Управляет сохранением и получением истории диалогов пользователей.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, select

from ..database.database import get_async_db_session
from ..database.models import User, Session as ChatSession, Message


class HistoryService:
    """Сервис для управления историей сообщений пользователей."""

    def __init__(self):
        self.max_context_messages = 20  # Максимум сообщений в контексте
        self.context_window_hours = 24  # Окно контекста в часах

    async def save_message(
        self,
        user_id: int,
        message_text: str,
        message_type: str = "user",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """
        Сохранить сообщение в историю.

        Args:
            user_id: ID пользователя Telegram
            message_text: Текст сообщения
            message_type: Тип сообщения (user, assistant, system)
            metadata: Дополнительные данные (модель LLM, токены и т.д.)

        Returns:
            Созданное сообщение
        """
        async with get_async_db_session() as db:
            # Получаем или создаем пользователя
            result = await db.execute(select(User).filter(User.user_id == user_id))
            user = await result.scalar_one_or_none()
            if not user:
                user = User(user_id=user_id)
                db.add(user)
                await db.flush()

            # Получаем или создаем активную сессию
            session = await self._get_or_create_session(db, user.user_id)

            # Создаем сообщение
            message = Message(
                user_id=user_id,
                session_id=session.id,
                content=message_text,
                message_type=message_type,
                role=message_type,  # Используем message_type как role
                message_metadata=metadata or {}
            )

            db.add(message)
            await db.commit()

            return message

    async def get_conversation_history(
        self,
        user_id: int,
        limit: Optional[int] = None,
        include_system: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Получить историю диалога пользователя.

        Args:
            user_id: ID пользователя Telegram
            limit: Максимальное количество сообщений
            include_system: Включать ли системные сообщения

        Returns:
            Список сообщений в формате для LLM
        """
        async with get_async_db_session() as db:
            result = await db.execute(select(User).filter(User.user_id == user_id))
            user = await result.scalar_one_or_none()
            if not user:
                return []

            # Получаем активную сессию
            session_result = await db.execute(
                select(ChatSession).filter(
                    and_(
                        ChatSession.user_id == user.user_id,
                        ChatSession.is_active == True
                    )
                )
            )
            session = await session_result.scalar_one_or_none()

            if not session:
                return []

            # Строим запрос для сообщений
            query = select(Message).filter(Message.session_id == session.id)

            if not include_system:
                query = query.filter(Message.message_type != "system")

            # Ограничиваем по времени (контекстное окно)
            cutoff_time = datetime.now(
                timezone.utc) - timedelta(hours=self.context_window_hours)
            query = query.filter(Message.created_at >= cutoff_time)

            # Сортируем по времени и ограничиваем количество
            query = query.order_by(desc(Message.created_at))
            if limit:
                query = query.limit(limit)
            else:
                query = query.limit(self.max_context_messages)

            messages_result = await db.execute(query)
            messages = messages_result.scalars().all()

            # Преобразуем в формат для LLM (обращаем порядок)
            history = []
            for message in reversed(messages):
                role = "user" if message.message_type == "user" else "assistant"
                if message.message_type == "system":
                    role = "system"

                history.append({
                    "role": role,
                    "content": message.content,
                    "timestamp": message.created_at.isoformat(),
                    "metadata": message.message_metadata
                })

            return history

    async def clear_history(self, user_id: int) -> bool:
        """
        Очистить историю пользователя (завершить текущую сессию).

        Args:
            user_id: ID пользователя Telegram

        Returns:
            True если история была очищена
        """
        async with get_async_db_session() as db:
            result = await db.execute(select(User).filter(User.user_id == user_id))
            user = await result.scalar_one_or_none()
            if not user:
                return False

            # Завершаем активную сессию
            session_result = await db.execute(
                select(ChatSession).filter(
                    and_(
                        ChatSession.user_id == user.user_id,
                        ChatSession.is_active == True
                    )
                )
            )
            active_session = await session_result.scalar_one_or_none()

            if active_session:
                active_session.is_active = False
                active_session.ended_at = datetime.now(timezone.utc)
                await db.commit()
                return True

            return False

    async def get_session_stats(self, user_id: int) -> Dict[str, Any]:
        """
        Получить статистику текущей сессии пользователя.

        Args:
            user_id: ID пользователя Telegram

        Returns:
            Статистика сессии
        """
        async with get_async_db_session() as db:
            result = await db.execute(select(User).filter(User.user_id == user_id))
            user = await result.scalar_one_or_none()
            if not user:
                return {"messages": 0, "session_duration": 0}

            session_result = await db.execute(
                select(ChatSession).filter(
                    and_(
                        ChatSession.user_id == user.user_id,
                        ChatSession.is_active == True
                    )
                )
            )
            session = await session_result.scalar_one_or_none()

            if not session:
                return {"messages": 0, "session_duration": 0}

            # Подсчитываем сообщения
            count_result = await db.execute(
                select(Message).filter(Message.session_id == session.id)
            )
            message_count = len(await count_result.scalars().all())

            # Вычисляем длительность сессии
            duration = datetime.now(timezone.utc) - session.created_at
            duration_minutes = int(duration.total_seconds() / 60)

            return {
                "messages": message_count,
                "session_duration": duration_minutes,
                "session_start": session.created_at.isoformat()
            }

    async def _get_or_create_session(self, db, user_id: int) -> ChatSession:
        """Получить или создать активную сессию для пользователя."""
        # Ищем активную сессию
        result = await db.execute(
            select(ChatSession).filter(
                and_(
                    ChatSession.user_id == user_id,
                    ChatSession.is_active == True
                )
            )
        )
        session = await result.scalar_one_or_none()

        if session:
            return session

        # Создаем новую сессию
        session = ChatSession(user_id=user_id)
        db.add(session)
        await db.flush()

        return session

    async def set_context_limits(
        self,
        max_messages: Optional[int] = None,
        window_hours: Optional[int] = None
    ):
        """
        Настроить ограничения контекста.

        Args:
            max_messages: Максимальное количество сообщений в контексте
            window_hours: Размер временного окна в часах
        """
        if max_messages is not None:
            self.max_context_messages = max_messages
        if window_hours is not None:
            self.context_window_hours = window_hours
