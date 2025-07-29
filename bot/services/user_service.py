"""
User service for managing user data and preferences.
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from telegram import User as TelegramUser

from ..database.database import get_async_db_session
from ..database.models import User

logger = logging.getLogger(__name__)


class UserService:
    """Service for managing user data and preferences."""

    @staticmethod
    async def get_or_create_user(
        user_id: int,
        telegram_user: Optional[TelegramUser] = None
    ) -> User:
        """Get existing user or create new one."""
        async with get_async_db_session() as session:
            # Try to get existing user
            result = await session.execute(
                select(User).where(User.user_id == user_id)
            )
            user = result.scalar_one_or_none()

            if user:
                # Update last activity
                user.last_activity = datetime.utcnow()

                # Update user info if provided
                if telegram_user:
                    user.username = telegram_user.username
                    user.first_name = telegram_user.first_name
                    user.last_name = telegram_user.last_name

                await session.commit()
                await session.refresh(user)
                logger.debug(f"Updated existing user {user_id}")
                return user

            # Create new user
            user_data = {
                "user_id": user_id,
                "last_activity": datetime.utcnow()
            }

            if telegram_user:
                user_data.update({
                    "username": telegram_user.username,
                    "first_name": telegram_user.first_name,
                    "last_name": telegram_user.last_name
                })

            user = User(**user_data)
            session.add(user)
            await session.commit()
            await session.refresh(user)

            logger.info(
                f"Created new user {user_id} ({telegram_user.username if telegram_user else 'unknown'})")
            return user

    @staticmethod
    async def get_user(user_id: int) -> Optional[User]:
        """Get user by ID."""
        async with get_async_db_session() as session:
            result = await session.execute(
                select(User).where(User.user_id == user_id)
            )
            return result.scalar_one_or_none()

    @staticmethod
    async def update_llm_settings(
        user_id: int,
        provider: Optional[str] = None,
        model: Optional[str] = None
    ) -> bool:
        """Update user's LLM provider and model settings."""
        try:
            async with get_async_db_session() as session:
                update_data = {"updated_at": datetime.utcnow()}

                if provider is not None:
                    update_data["llm_provider"] = provider
                if model is not None:
                    update_data["llm_model"] = model

                result = await session.execute(
                    update(User)
                    .where(User.user_id == user_id)
                    .values(**update_data)
                )

                await session.commit()

                if result.rowcount > 0:
                    logger.info(
                        f"Updated LLM settings for user {user_id}: provider={provider}, model={model}")
                    return True
                else:
                    logger.warning(
                        f"User {user_id} not found when updating LLM settings")
                    return False

        except Exception as e:
            logger.error(
                f"Failed to update LLM settings for user {user_id}: {e}")
            return False

    @staticmethod
    async def update_personalization(
        user_id: int,
        response_style: Optional[str] = None,
        max_history_messages: Optional[int] = None,
        language: Optional[str] = None
    ) -> bool:
        """Update user's personalization settings."""
        try:
            async with get_async_db_session() as session:
                update_data = {"updated_at": datetime.utcnow()}

                if response_style is not None:
                    if response_style not in ["concise", "balanced", "detailed"]:
                        raise ValueError(
                            f"Invalid response_style: {response_style}")
                    update_data["response_style"] = response_style

                if max_history_messages is not None:
                    if max_history_messages < 0 or max_history_messages > 100:
                        raise ValueError(
                            f"Invalid max_history_messages: {max_history_messages}")
                    update_data["max_history_messages"] = max_history_messages

                if language is not None:
                    update_data["language"] = language

                result = await session.execute(
                    update(User)
                    .where(User.user_id == user_id)
                    .values(**update_data)
                )

                await session.commit()

                if result.rowcount > 0:
                    logger.info(
                        f"Updated personalization for user {user_id}: {update_data}")
                    return True
                else:
                    logger.warning(
                        f"User {user_id} not found when updating personalization")
                    return False

        except Exception as e:
            logger.error(
                f"Failed to update personalization for user {user_id}: {e}")
            return False

    @staticmethod
    async def get_user_settings(user_id: int) -> Optional[Dict[str, Any]]:
        """Get user settings as dictionary."""
        user = await UserService.get_user(user_id)
        if not user:
            return None

        return {
            "user_id": user.user_id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "llm_provider": user.llm_provider,
            "llm_model": user.llm_model,
            "language": user.language,
            "response_style": user.response_style,
            "max_history_messages": user.max_history_messages,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "last_activity": user.last_activity
        }

    @staticmethod
    async def update_last_activity(user_id: int):
        """Update user's last activity timestamp."""
        try:
            async with get_async_db_session() as session:
                await session.execute(
                    update(User)
                    .where(User.user_id == user_id)
                    .values(last_activity=datetime.utcnow())
                )
                await session.commit()
        except Exception as e:
            logger.error(
                f"Failed to update last activity for user {user_id}: {e}")

    @staticmethod
    async def get_user_stats() -> Dict[str, Any]:
        """Get general user statistics."""
        try:
            async with get_async_db_session() as session:
                # Total users
                total_users_result = await session.execute(
                    select(User.user_id).count()
                )
                total_users = total_users_result.scalar()

                # Active users (last 7 days)
                week_ago = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
                week_ago = week_ago.replace(day=week_ago.day - 7)

                active_users_result = await session.execute(
                    select(User.user_id)
                    .where(User.last_activity >= week_ago)
                    .count()
                )
                active_users = active_users_result.scalar()

                # Provider distribution
                provider_stats_result = await session.execute(
                    select(User.llm_provider, User.user_id.count())
                    .group_by(User.llm_provider)
                )
                provider_stats = dict(provider_stats_result.fetchall())

                return {
                    "total_users": total_users,
                    "active_users_7d": active_users,
                    "provider_distribution": provider_stats
                }

        except Exception as e:
            logger.error(f"Failed to get user stats: {e}")
            return {
                "total_users": 0,
                "active_users_7d": 0,
                "provider_distribution": {}
            }
