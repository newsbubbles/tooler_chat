from app.services.agent_service import get_default_agent, create_agent, update_agent
from app.services.user_service import get_user_by_username
from app.db.database import get_db_context
import os
import logging
from pathlib import Path
from datetime import datetime, timezone

# Configure logging
logger = logging.getLogger(__name__)

# System username
SYSTEM_USERNAME = os.getenv("SYSTEM_USERNAME", "system")


def load_agent_prompt(agent_path: str) -> str:
    """Loads agent prompt file and replaces time_now var with current time"""
    logger.info(f"Loading agent prompt from {agent_path}")
    time_now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(agent_path, "r") as f:
            agent_prompt = f.read()
        return agent_prompt.replace('{time_now}', time_now)
    except Exception as e:
        logger.error(f"Failed to load agent prompt: {str(e)}")
        # Return a minimal prompt if the file can't be loaded
        return "You are a helpful assistant. Today is {time_now}.".replace('{time_now}', time_now)


async def init_tooler_agent():
    """Initialize the default Tooler agent if it doesn't exist"""
    async with get_db_context() as db:
        # First check if default agent already exists
        default_agent = await get_default_agent(db)
        
        # Try to load the tooler agent prompt
        root_path = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        agent_prompt_path = root_path / "agents" / "tooler.md"
        
        if agent_prompt_path.exists():
            # Load the improved tooler agent prompt
            system_prompt = load_agent_prompt(str(agent_prompt_path))
            logger.info("Loaded tooler agent prompt from file")
        else:
            # Fallback to basic prompt
            system_prompt = "You are Tooler, an agent specialized in building custom API clients. Current time: {time_now}"
            system_prompt = system_prompt.replace('{time_now}', datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))
            logger.warning(f"Could not find tooler agent prompt at {agent_prompt_path}, using fallback")
        
        if not default_agent:
            # Get system user
            system_user = await get_user_by_username(db, SYSTEM_USERNAME)
            
            if not system_user:
                logger.error(f"Cannot create default agent - system user '{SYSTEM_USERNAME}' not found")
                return None
            
            logger.info("Creating default Tooler agent")
            await create_agent(
                db=db,
                user_id=system_user.id,
                name="Tooler",
                description="Builds custom API clients based on user requirements",
                system_prompt=system_prompt,
                is_default=True
            )
            logger.info("Default Tooler agent created successfully")
            return True
        else:
            # If agent exists but has a different name than Tooler, don't update
            if default_agent.name.lower() != "tooler":
                logger.info(f"Default agent exists with name: {default_agent.name}, not updating")
                return True
                
            # Update the system prompt for the existing Tooler agent
            logger.info("Updating existing Tooler agent prompt")
            await update_agent(
                db=db,
                agent_id=default_agent.id,
                system_prompt=system_prompt
            )
            logger.info("Default Tooler agent updated successfully")
            return True
