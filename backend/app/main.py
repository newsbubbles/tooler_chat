from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.api import auth, users, agents, mcp_servers, chat
from app.db.database import create_db_and_tables
from app.core.system_init import init_system

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup tasks
    logger.info("Starting up the application")
    
    # Create database tables if they don't exist
    await create_db_and_tables()
    
    # Initialize the system (users and default agents)
    await init_system()
    
    yield
    
    # Shutdown tasks
    logger.info("Shutting down the application")


app = FastAPI(
    title="Tooler Chat API",
    description="API for the Tooler Chat application",
    version="0.1.0",
    lifespan=lifespan
)

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


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "message": "Tooler Chat API is running"}
