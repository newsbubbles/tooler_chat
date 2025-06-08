from typing import AsyncGenerator
from sqlmodel import SQLModel, create_engine
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.orm import sessionmaker
import os
from contextlib import asynccontextmanager

# Get database URL from environment variable or use a default for local development
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@db:5432/toolerchat")

# Create async engine for PostgreSQL
async_engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL query logging
    future=True
)

# Create async session factory
async_session_factory = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting async database sessions"""
    async with async_session_factory() as session:
        yield session
        await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for getting async database sessions"""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def create_db_and_tables():
    """Initialize the database tables"""
    from app.models.base import SQLModel
    
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def drop_db_and_tables():
    """Drop all database tables (use with caution)"""
    from app.models.base import SQLModel
    
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)


async def reset_db():
    """Reset the database by dropping and recreating all tables"""
    await drop_db_and_tables()
    await create_db_and_tables()