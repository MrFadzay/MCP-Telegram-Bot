"""
SQLAlchemy models for MCP Telegram Bot.
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Integer, String, Text, Boolean, DateTime, JSON,
    ForeignKey, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base


class User(Base):
    """User model for storing user preferences and settings."""
    __tablename__ = "users"

    # Primary key
    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # User info from Telegram
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True)

    # LLM settings
    llm_provider: Mapped[str] = mapped_column(String(50), default="google")
    llm_model: Mapped[str] = mapped_column(
        String(100), default="gemini-2.5-flash")

    # Personalization settings
    language: Mapped[str] = mapped_column(String(10), default="ru")
    response_style: Mapped[str] = mapped_column(
        String(20), default="balanced")  # concise, balanced, detailed
    max_history_messages: Mapped[int] = mapped_column(Integer, default=20)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_activity: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow)

    # Relationships
    sessions: Mapped[List["Session"]] = relationship(
        "Session", back_populates="user", cascade="all, delete-orphan")
    messages: Mapped[List["Message"]] = relationship(
        "Message", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User(user_id={self.user_id}, username={self.username}, provider={self.llm_provider})>"


class Session(Base):
    """Session model for grouping conversations."""
    __tablename__ = "sessions"

    # Primary key
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)

    # Foreign key to user
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="CASCADE"))

    # Session info
    session_name: Mapped[str] = mapped_column(String(255), default="Диалог")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    ended_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="sessions")
    messages: Mapped[List["Message"]] = relationship(
        "Message", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Session(id={self.id}, user_id={self.user_id}, name={self.session_name}, active={self.is_active})>"


class Message(Base):
    """Message model for storing conversation history."""
    __tablename__ = "messages"

    # Primary key
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)

    # Foreign keys
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="CASCADE"))
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sessions.id", ondelete="CASCADE"))

    # Message content
    # 'user', 'assistant', 'system', 'tool_call', 'tool_result'
    message_type: Mapped[str] = mapped_column(String(20))
    # For OpenAI API compatibility: 'user', 'assistant', 'system'
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)

    # Metadata
    message_metadata: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True)  # Model, tokens, execution time, MCP tools used
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    processing_time_ms: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="messages")
    session: Mapped["Session"] = relationship(
        "Session", back_populates="messages")

    def __repr__(self) -> str:
        return f"<Message(id={self.id}, type={self.message_type}, role={self.role}, content={self.content[:50]}...)>"


# Indexes for better performance
Index("idx_messages_user_session", Message.user_id, Message.session_id)
Index("idx_messages_created_at", Message.created_at)
Index("idx_sessions_user_active", Session.user_id, Session.is_active)
Index("idx_users_last_activity", User.last_activity)
