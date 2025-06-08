from app.db.database import get_db_context
from app.services.user_service import get_user_by_username, create_user
from app.core.agent_init import init_tooler_agent
import secrets
import logging
import os

# Configure logging
logger = logging.getLogger(__name__)

SYSTEM_USERNAME = os.getenv("SYSTEM_USERNAME", "system")
# Generate a secure random password for the system user that never needs to be known
SYSTEM_PASSWORD = os.getenv("SYSTEM_PASSWORD", secrets.token_urlsafe(32))
SYSTEM_EMAIL = os.getenv("SYSTEM_EMAIL", "system@toolerchat.internal")

async def init_system():
    """Initialize system components including system user and default agent"""
    # Create system user if it doesn't exist
    await init_system_user()
    
    # Initialize default Tooler agent
    await init_tooler_agent()

async def init_system_user():
    """Create the system user if it doesn't exist"""
    async with get_db_context() as db:
        # Check if system user already exists
        system_user = await get_user_by_username(db, SYSTEM_USERNAME)
        
        if not system_user:
            logger.info("Creating system user")
            try:
                system_user = await create_user(
                    db=db,
                    username=SYSTEM_USERNAME,
                    email=SYSTEM_EMAIL,
                    password=SYSTEM_PASSWORD
                )
                logger.info(f"System user created successfully with ID: {system_user.id}")
                return system_user
            except Exception as e:
                logger.error(f"Failed to create system user: {str(e)}")
                raise
        else:
            logger.info(f"System user already exists with ID: {system_user.id}")
            return system_user
