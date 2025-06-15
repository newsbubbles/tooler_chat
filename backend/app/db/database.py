from typing import AsyncGenerator, Optional, Dict, Any
from sqlmodel import SQLModel, create_engine, select, inspect
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import event
import os
from contextlib import asynccontextmanager
import time
import asyncio
import logging

# Import logging functionality
try:
    from app.core.logging import get_logger
    logger = get_logger("app.db.database")
except ImportError:
    logger = logging.getLogger("app.db.database")
    logger.setLevel(logging.INFO)

# Get database URL from environment variable or use a default for local development
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@db:5432/toolerchat")

# Determine if we should enable query logging
MAX_DEBUG = os.getenv("MAX_DEBUG", "false").lower() in ("true", "1", "yes")
SQL_ECHO = MAX_DEBUG or os.getenv("SQL_ECHO", "false").lower() in ("true", "1", "yes")

# Create async engine for PostgreSQL
async_engine = create_async_engine(
    DATABASE_URL,
    echo=SQL_ECHO,  # Set to True for SQL query logging
    future=True,
    pool_pre_ping=True,  # Add connection pool check
    pool_recycle=3600,  # Recycle connections after 1 hour
    pool_size=5,        # Adjust based on your needs
    max_overflow=10      # Allow 10 more connections when pool is full
)

# Add query timing logging when MAX_DEBUG is enabled
if hasattr(logger, 'debug_data') and MAX_DEBUG:
    # Set up event listeners for query timing
    @event.listens_for(async_engine.sync_engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        if not hasattr(context, 'query_start_time'):
            context.query_start_time = time.time()

    @event.listens_for(async_engine.sync_engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        if hasattr(context, 'query_start_time'):
            elapsed = time.time() - context.query_start_time
            logger.debug_data(
                "SQL Query executed",
                {
                    "query": statement,
                    "parameters": str(parameters),
                    "elapsed_ms": round(elapsed * 1000, 2),
                    "executemany": executemany
                }
            )

# Create async session factory
async_session_factory = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class LoggingAsyncSession(AsyncSession):
    """Extends AsyncSession with logging capabilities"""
    
    async def execute(self, *args, **kwargs):
        """Override execute to add timing and logging"""
        start_time = time.time()
        try:
            result = await super().execute(*args, **kwargs)
            if hasattr(logger, 'debug_data') and MAX_DEBUG:
                # Try to extract query information
                statement = args[0] if args else kwargs.get('statement', 'Unknown query')
                stmt_str = str(statement)
                elapsed = time.time() - start_time
                
                # Log the query execution
                logger.debug_data(
                    "SQLModel execute",
                    {
                        "statement": stmt_str[:1000] + "..." if len(stmt_str) > 1000 else stmt_str,
                        "elapsed_ms": round(elapsed * 1000, 2)
                    }
                )
            return result
        except Exception as e:
            if hasattr(logger, 'error_data'):
                statement = args[0] if args else kwargs.get('statement', 'Unknown query')
                stmt_str = str(statement)
                logger.error_data(
                    "Database error",
                    {
                        "statement": stmt_str[:1000] + "..." if len(stmt_str) > 1000 else stmt_str,
                        "error": str(e)
                    },
                    exc_info=True
                )
            raise


# Create enhanced async session factory if we have advanced logging
if hasattr(logger, 'debug_data'):
    enhanced_session_factory = sessionmaker(
        bind=async_engine,
        class_=LoggingAsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    async_session_factory = enhanced_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting async database sessions"""
    async with async_session_factory() as session:
        try:
            if hasattr(logger, 'debug_data'):
                logger.debug_data("Database session started")
            yield session
        except Exception as e:
            if hasattr(logger, 'error_data'):
                logger.error_data("Database session error", {"error": str(e)}, exc_info=True)
            await session.rollback()
            raise
        finally:
            await session.close()
            if hasattr(logger, 'debug_data'):
                logger.debug_data("Database session closed")


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for getting async database sessions"""
    async with async_session_factory() as session:
        try:
            if hasattr(logger, 'debug_data'):
                logger.debug_data("Database context started")
            yield session
        except Exception as e:
            if hasattr(logger, 'error_data'):
                logger.error_data("Database context error", {"error": str(e)}, exc_info=True)
            await session.rollback()
            raise
        finally:
            await session.close()
            if hasattr(logger, 'debug_data'):
                logger.debug_data("Database context closed")


async def create_db_and_tables():
    """Initialize the database tables"""
    from app.models.base import SQLModel
    
    if hasattr(logger, 'info_data'):
        logger.info_data("Creating database tables")
    else:
        logger.info("Creating database tables")
    
    start_time = time.time()
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    
    elapsed = time.time() - start_time
    if hasattr(logger, 'info_data'):
        logger.info_data(f"Database tables created in {elapsed:.2f}s")
    else:
        logger.info(f"Database tables created in {elapsed:.2f}s")


async def drop_db_and_tables():
    """Drop all database tables (use with caution)"""
    from app.models.base import SQLModel
    
    if hasattr(logger, 'warning_data'):
        logger.warning_data("Dropping all database tables")
    else:
        logger.warning("Dropping all database tables")
    
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)


async def reset_db():
    """Reset the database by dropping and recreating all tables"""
    if hasattr(logger, 'warning_data'):
        logger.warning_data("Resetting database - all data will be lost")
    else:
        logger.warning("Resetting database - all data will be lost")
    
    await drop_db_and_tables()
    await create_db_and_tables()
    
    if hasattr(logger, 'info_data'):
        logger.info_data("Database has been reset")
    else:
        logger.info("Database has been reset")


async def db_health_check() -> Dict[str, Any]:
    """Check database connectivity and return status"""
    start_time = time.time()
    try:
        async with async_session_factory() as session:
            # Execute a simple query
            result = await session.execute(select(1))
            one = result.scalar_one()
            assert one == 1
            
            # Get database statistics
            result = await session.execute("SELECT version();")
            version = result.scalar_one()
            
            elapsed = time.time() - start_time
            return {
                "status": "healthy",
                "response_time_ms": round(elapsed * 1000, 2),
                "version": version,
                "connection_pool": {
                    "size": async_engine.pool.size(),
                    "checked_out": async_engine.pool.checkedout(),
                }
            }
    except Exception as e:
        elapsed = time.time() - start_time
        error_message = str(e)
        if hasattr(logger, 'error_data'):
            logger.error_data("Database health check failed", {"error": error_message}, exc_info=True)
        else:
            logger.error(f"Database health check failed: {error_message}", exc_info=True)
        return {
            "status": "unhealthy",
            "response_time_ms": round(elapsed * 1000, 2),
            "error": error_message
        }