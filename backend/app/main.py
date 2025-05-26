from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.api import auth, users, agents, mcp_servers, chat
from app.db.database import create_db_and_tables
from app.core.agent_init import init_tooler_agent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup tasks
    logger.info("Starting up the application")
    
    # Create database tables if they don't exist
    await create_db_and_tables()
    
    # Initialize the default Tooler agent if it doesn't exist
    await init_tooler_agent()
    
    yield
    
    # Shutdown tasks
    logger.info("Shutting down the application")


app = FastAPI(
    title="Tooler Chat API",
    description="API for the Tooler Chat application",
    version="0.1.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, specify the actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(agents.router, prefix="/api")
app.include_router(mcp_servers.router, prefix="/api")
app.include_router(chat.router, prefix="/api")


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "message": "Tooler Chat API is running"}
