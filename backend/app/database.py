"""
BillAgent Pro - Database Configuration
=======================================
Async SQLAlchemy 2.0 setup with PostgreSQL.
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from .config import settings


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


# -----------------------------------------------------------------------------
# Engine Configuration
# -----------------------------------------------------------------------------
engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=settings.debug,  # Log SQL queries in debug mode
    future=True,
    pool_pre_ping=True,  # Verify connections before use
    # Use NullPool for better async behavior
    # In production, consider using connection pooling
    poolclass=NullPool if settings.environment == "development" else None,
)

# -----------------------------------------------------------------------------
# Session Factory
# -----------------------------------------------------------------------------
async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# -----------------------------------------------------------------------------
# Dependency Injection
# -----------------------------------------------------------------------------
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that provides a database session.
    
    Usage in FastAPI:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# -----------------------------------------------------------------------------
# Database Lifecycle
# -----------------------------------------------------------------------------
async def init_db() -> None:
    """
    Initialize database tables.
    Called during application startup.
    
    Note: In production, use Alembic migrations instead.
    """
    async with engine.begin() as conn:
        # Import all models to register them with Base
        from .models import vendor, bill, line_item, audit_log, gl_code  # noqa: F401
        
        # Create all tables (development only)
        if settings.environment == "development":
            await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """
    Close database connections.
    Called during application shutdown.
    """
    await engine.dispose()
