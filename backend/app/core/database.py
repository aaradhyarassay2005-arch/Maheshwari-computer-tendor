from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings

# Create engine configurations dynamically based on the DB type
engine_args = {
    "echo": False,
    "future": True
}

if settings.DATABASE_URL.startswith("postgresql"):
    engine_args["pool_size"] = 20
    engine_args["max_overflow"] = 10

# Create asynchronous engine
engine = create_async_engine(
    settings.DATABASE_URL,
    **engine_args
)

# Async session maker
async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency injection helper to yield an active async database session."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
