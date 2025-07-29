"""
Database configuration and connection management for MCP Telegram Bot.
"""
import os
import logging
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy import event, create_engine
from sqlalchemy.engine import Engine
from contextlib import contextmanager, asynccontextmanager

logger = logging.getLogger(__name__)

# Base class for all models


class Base(DeclarativeBase):
    pass


# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///data/bot.db")
SYNC_DATABASE_URL = os.getenv("SYNC_DATABASE_URL", "sqlite:///data/bot.db")

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL query logging
    future=True,
    pool_pre_ping=True,
)

# Create sync engine for migrations
sync_engine = create_engine(
    SYNC_DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)

# Create session factories
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

SyncSessionLocal = sessionmaker(
    sync_engine,
    expire_on_commit=False
)

# Enable foreign keys for SQLite


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable foreign key constraints for SQLite."""
    if 'sqlite' in str(dbapi_connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


async def init_database():
    """Initialize database and create all tables."""
    try:
        # Ensure data directory exists
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)

        # Import all models to ensure they're registered
        from .models import User, Session, Message

        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info("Database initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


@asynccontextmanager
async def get_async_db_session():
    """Get async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()


@contextmanager
def get_db_session():
    """Get sync database session for migrations."""
    session = SyncSessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        session.close()


async def close_database():
    """Close database connections."""
    try:
        await engine.dispose()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database: {e}")
