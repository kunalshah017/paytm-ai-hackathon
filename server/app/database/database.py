import ssl as ssl_module

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.config import settings
from typing import AsyncGenerator


def _get_async_url(url: str) -> str:
    """Convert a standard postgresql:// URL to postgresql+asyncpg://"""
    # Strip query params that asyncpg doesn't understand (sslmode, channel_binding)
    base = url.split("?")[0]
    if base.startswith("postgresql://"):
        return base.replace("postgresql://", "postgresql+asyncpg://", 1)
    if base.startswith("postgres://"):
        return base.replace("postgres://", "postgresql+asyncpg://", 1)
    return base


# Neon requires SSL
_ssl_context = ssl_module.create_default_context()

engine = create_async_engine(
    _get_async_url(settings.database_url),
    echo=False,
    pool_size=10,
    max_overflow=20,
    connect_args={"ssl": _ssl_context, "timeout": 10},
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """All SQLAlchemy models inherit from this."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a DB session and closes it after the request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db():
    """Create all tables. Called on app startup."""
    import asyncio
    import logging

    for attempt in range(3):
        try:
            async with engine.begin() as conn:
                from app.models import inventory_item, order, transaction  # noqa: F401
                await conn.run_sync(Base.metadata.create_all)
            return
        except Exception as e:
            logging.warning(f"Database init attempt {attempt + 1}/3 failed: {e}")
            if attempt < 2:
                await asyncio.sleep(2 ** attempt)

    logging.error("Database initialization failed after 3 attempts. App will continue without DB init.")
    