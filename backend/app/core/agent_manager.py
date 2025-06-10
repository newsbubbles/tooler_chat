import asyncio
import logging
import os
from pathlib import Path
from typing import Dict, Optional

from pydantic_ai import Agent
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.app.agents.tooler_agent import create_tooler_agent
from backend.app.models.base import Agent as AgentModel
from backend.app.models.base import MCPServer

# Configure logging
logger = logging.getLogger(__name__)

# Global cache for agent instances
_agent_cache: Dict[str, Agent] = {}


async def get_or_create_tooler_agent() -> Agent:
    """Get the tooler agent from the cache or create a new one"""
    if 'tooler' in _agent_cache:
        return _agent_cache['tooler']
    
    # Determine the project tools path
    # In development, it might be in a different location than in production
    project_tools_path = "project_tools"
    
    for candidate_path in ["project_tools", "../project_tools", "../../project_tools"]:
        if Path(candidate_path).exists():
            project_tools_path = candidate_path
            break
    
    # Create the agent
    agent = create_tooler_agent(project_tools_path=project_tools_path)
    
    # Cache the agent
    _agent_cache['tooler'] = agent
    
    return agent


async def get_agent_instance(agent_model: AgentModel, db: AsyncSession) -> Optional[Agent]:
    """Get an agent instance based on its database model
    
    Args:
        agent_model: The database model of the agent
        db: Database session for loading MCP servers
    
    Returns:
        Configured Agent instance or None if not found/supported
    """
    # Special case for the tooler agent
    if agent_model.name.lower() == "tooler":
        return await get_or_create_tooler_agent()
    
    # For other agents, we would need to implement their creation here
    logger.warning(f"Agent type {agent_model.name} not implemented")
    return None


async def cleanup_agents():
    """Clean up all cached agents"""
    for agent_name, agent in _agent_cache.items():
        logger.info(f"Cleaning up agent: {agent_name}")
        try:
            # Stop any running MCP servers
            if hasattr(agent, '_mcp_server_tasks') and agent._mcp_server_tasks:
                for task in agent._mcp_server_tasks:
                    if not task.done():
                        task.cancel()
                        try:
                            await task
                        except asyncio.CancelledError:
                            pass
        except Exception as e:
            logger.error(f"Error cleaning up agent {agent_name}: {e}")
    
    # Clear the cache
    _agent_cache.clear()