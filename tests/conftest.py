"""
Конфигурация pytest для тестов MCP Telegram Bot.
"""
from bot.database.models import User, Session, Message
from bot.database.database import Base
import sys
import os
import pytest
import asyncio
import tempfile
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from unittest.mock import AsyncMock, MagicMock

# Добавляем корневую директорию проекта в sys.path
# Это позволяет pytest находить модули bot, llm, mcp_client и т.д.
sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..')))


@pytest.fixture(scope="session")
def event_loop():
    """Создает event loop для всей сессии тестов."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_db():
    """Создает временную тестовую базу данных."""
    # Создаем временный файл для базы данных
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db.close()

    # Создаем движок для тестовой базы
    test_engine = create_async_engine(
        f"sqlite+aiosqlite:///{temp_db.name}",
        echo=False
    )

    # Создаем таблицы
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Создаем фабрику сессий
    TestSessionLocal = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    yield TestSessionLocal

    # Очистка
    await test_engine.dispose()
    os.unlink(temp_db.name)


@pytest.fixture
async def test_user(test_db):
    """Создает тестового пользователя."""
    async with test_db() as session:
        user = User(
            user_id=12345,
            username="testuser",
            first_name="Test",
            last_name="User"
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest.fixture
def mock_telegram_update():
    """Мок объекта Update от Telegram."""
    update = MagicMock()
    update.effective_user.id = 12345
    update.effective_user.username = "testuser"
    update.effective_user.first_name = "Test"
    update.effective_user.last_name = "User"
    update.message.text = "Test message"
    return update


@pytest.fixture
def mock_telegram_context():
    """Мок объекта CallbackContext от Telegram."""
    context = MagicMock()
    context.bot.send_message = AsyncMock()
    return context


@pytest.fixture
def mock_llm_client():
    """Мок LLM клиента."""
    client = AsyncMock()
    client.generate_response.return_value = "Test response"
    client.get_available_models.return_value = ["test-model"]
    return client


@pytest.fixture
def mock_mcp_client():
    """Мок MCP клиента."""
    client = AsyncMock()
    client.list_tools.return_value = {
        "tools": [
            {
                "name": "test_tool",
                "description": "Test tool",
                "inputSchema": {"type": "object", "properties": {}}
            }
        ]
    }
    client.call_tool.return_value = {"result": "test result"}
    return client
