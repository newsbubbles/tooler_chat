from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import os

from app.api import auth, users, agents, mcp_servers, chat, logs
from app.db.database import create_db_and_tables
from app.core.system_init import init_system
from app.core.logging import setup_logging, get_logger
from app.core.logging.middleware import LoggingMiddleware

# Set up enhanced logging
setup_logging(
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    structured=os.getenv("STRUCTURED_LOGS", "true").lower() in ["true", "1", "yes"]
)

# Get a logger for this module
logger = get_logger("app.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup tasks
    logger.info_data("Starting up the application", {
        "app_name": "Tooler Chat API",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "version": "0.1.0"
    })
    
    # Create database tables if they don't exist
    try:
        await create_db_and_tables()
        logger.info("Database tables created or verified")
    except Exception as e:
        logger.error_data("Database initialization failed", {
            "error": str(e)
        }, exc_info=True)
        raise
    
    # Initialize the system (users and default agents)
    try:
        await init_system()
        logger.info("System initialization completed")
    except Exception as e:
        logger.error_data("System initialization failed", {
            "error": str(e)
        }, exc_info=True)
        raise
    
    # Log successful startup
    logger.info("Application startup completed successfully")
    
    yield
    
    # Shutdown tasks
    logger.info("Shutting down the application")


app = FastAPI(
    title="Tooler Chat API",
    description="API for the Tooler Chat application",
    version="0.1.0",
    lifespan=lifespan
)

# Add logging middleware
app.add_middleware(LoggingMiddleware)

# Configure CORS - make it permissive for development
origins = [
    "http://localhost:3000",           # Local React development
    "http://localhost:34140",          # Local Docker frontend
    "http://51.158.125.49:34140",      # Remote Docker frontend
    "http://51.158.125.49:34130",      # Remote Docker backend
    "http://51.158.125.49",           # Remote host
    "http://localhost",                # Local host
    "*"                               # Wildcard for development
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https?://.*",  # Allow any origin during development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Include API routers
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(agents.router, prefix="/api")
app.include_router(mcp_servers.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(logs.router, prefix="/api")  # Add logs router


@app.get("/api/health")
async def health_check():
    logger.info("Health check endpoint called")
    return {"status": "healthy", "message": "Tooler Chat API is running"}
