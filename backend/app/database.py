"""
ThermaCity — Async Database Engine & Session

Uses SQLAlchemy 2.0 async API with asyncpg driver.
GeoAlchemy2 provides PostGIS geometry column support.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings

# ── Async Engine ──────────────────────────────────────────────
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,       # Log SQL in debug mode
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,        # Reconnect on stale connections
    connect_args={"statement_cache_size": 0, "prepared_statement_name_func": lambda: ""}, # Required for Supabase transaction pooler
)

# ── Session Factory ───────────────────────────────────────────
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── Dependency Injection ──────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an async DB session.

    Usage:
        @router.get("/example")
        async def example(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
