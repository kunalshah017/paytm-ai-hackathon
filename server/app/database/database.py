import ssl as ssl_module

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.config import settings
from typing import AsyncGenerator


def _get_async_url(url: str) -> str:
    """Convert a standard postgresql:// URL to postgresql+asyncpg://"""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


# Supabase requires SSL
_ssl_context = ssl_module.create_default_context()
_ssl_context.check_hostname = False
_ssl_context.verify_mode = ssl_module.CERT_NONE

engine = create_async_engine(
    _get_async_url(settings.database_url),
    echo=False,
    pool_size=10,
    max_overflow=20,
    connect_args={"ssl": _ssl_context},
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
    async with engine.begin() as conn:
        from app.models import inventory_item, order, transaction  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)
    