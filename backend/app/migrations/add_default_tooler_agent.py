#!/usr/bin/env python

"""
Migration script to add default Tooler agent to the database

This script adds the Tooler agent as a default agent in the database if it doesn't already exist.
It reads the system prompt from the tooler.md file and creates a new agent record.

Usage:
    python -m backend.app.migrations.add_default_tooler_agent
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add the project root to the sys.path
root_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_path))

from sqlmodel import select
from backend.app.db.database import engine, AsyncSession
from backend.app.models.base import Agent
from backend.app.agents.tooler_agent import load_agent_prompt

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def add_default_tooler_agent():
    """Add default Tooler agent to the database if it doesn't exist"""
    async with AsyncSession(engine) as session:
        # Check if default agent already exists
        query = select(Agent).where(Agent.is_default == True)  # noqa: E712
        result = await session.execute(query)
        default_agent = result.scalar_one_or_none()
        
        if default_agent:
            logger.info(f"Default agent already exists: {default_agent.name}")
            # If it's already the Tooler agent, update the system prompt
            if default_agent.name.lower() == "tooler":
                agent_prompt_path = root_path / "backend" / "app" / "agents" / "tooler.md"
                if agent_prompt_path.exists():
                    system_prompt = load_agent_prompt(str(agent_prompt_path))
                    default_agent.system_prompt = system_prompt
                    session.add(default_agent)
                    await session.commit()
                    logger.info("Updated Tooler agent system prompt")
            return
        
        # Load the Tooler agent system prompt
        agent_prompt_path = root_path / "backend" / "app" / "agents" / "tooler.md"
        if not agent_prompt_path.exists():
            logger.error(f"Tooler agent prompt not found at {agent_prompt_path}")
            return
        
        system_prompt = load_agent_prompt(str(agent_prompt_path))
        
        # Create the default Tooler agent
        tooler_agent = Agent(
            name="Tooler",
            description="Builds custom API clients based on user requirements",
            system_prompt=system_prompt,
            is_default=True,
            # No user_id because it's a system agent
        )
        
        session.add(tooler_agent)
        await session.commit()
        logger.info("Added default Tooler agent to the database")


if __name__ == "__main__":
    asyncio.run(add_default_tooler_agent())
