"""
Simple migration management system for MCP Telegram Bot.
"""
import logging
from pathlib import Path
from typing import List, Dict, Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from .database import get_db_session, engine

logger = logging.getLogger(__name__)

class MigrationManager:
    """Simple migration manager for database schema changes."""
    
    def __init__(self):
        self.migrations_dir = Path(__file__).parent / "migrations"
        
    async def create_migration_table(self):
        """Create migration tracking table if it doesn't exist."""
        async with engine.begin() as conn:
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
    
    async def get_applied_migrations(self) -> List[str]:
        """Get list of applied migration versions."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT version FROM schema_migrations ORDER BY version"))
            return [row[0] for row in result.fetchall()]
    
    async def mark_migration_applied(self, version: str, name: str):
        """Mark migration as applied."""
        async with AsyncSessionLocal() as session:
            await session.execute(
                text("INSERT INTO schema_migrations (version, name) VALUES (:version, :name)"),
                {"version": version, "name": name}
            )
            await session.commit()
    
    async def get_available_migrations(self) -> List[Dict[str, Any]]:
        """Get list of available migration files."""
        migrations = []
        
        for migration_file in sorted(self.migrations_dir.glob("*.py")):
            if migration_file.name.startswith("__"):
                continue
                
            # Extract version from filename (e.g., "001_initial_schema.py" -> "001")
            version = migration_file.stem.split("_")[0]
            name = "_".join(migration_file.stem.split("_")[1:])
            
            migrations.append({
                "version": version,
                "name": name,
                "file": migration_file
            })
        
        return migrations
    
    async def run_migrations(self):
        """Run all pending migrations."""
        try:
            await self.create_migration_table()
            
            applied_migrations = await self.get_applied_migrations()
            available_migrations = await self.get_available_migrations()
            
            pending_migrations = [
                m for m in available_migrations 
                if m["version"] not in applied_migrations
            ]
            
            if not pending_migrations:
                logger.info("No pending migrations")
                return
            
            logger.info(f"Running {len(pending_migrations)} pending migrations")
            
            for migration in pending_migrations:
                logger.info(f"Applying migration {migration['version']}: {migration['name']}")
                
                # Import and run migration
                spec = importlib.util.spec_from_file_location(
                    f"migration_{migration['version']}", 
                    migration["file"]
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Run upgrade function
                async with AsyncSessionLocal() as session:
                    await module.upgrade(session)
                    await self.mark_migration_applied(migration["version"], migration["name"])
                
                logger.info(f"Migration {migration['version']} applied successfully")
            
            logger.info("All migrations completed successfully")
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            raise

# Import required for dynamic module loading
import importlib.util
from .database import AsyncSessionLocal