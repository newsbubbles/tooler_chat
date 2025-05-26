from sqlmodel import select, or_, and_
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.base import Agent, AgentMCPServer, MCPServer, User
from typing import List, Optional
from uuid import UUID


async def create_agent(db: AsyncSession, user_id: int, name: str, system_prompt: str, description: Optional[str] = None, is_default: bool = False) -> Agent:
    """Create a new agent"""
    agent = Agent(
        user_id=user_id,
        name=name,
        description=description,
        system_prompt=system_prompt,
        is_default=is_default
    )
    
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent


async def get_agent_by_id(db: AsyncSession, agent_id: int) -> Optional[Agent]:
    """Get agent by ID"""
    return await db.get(Agent, agent_id)


async def get_agent_by_uuid(db: AsyncSession, agent_uuid: UUID) -> Optional[Agent]:
    """Get agent by UUID"""
    query = select(Agent).where(Agent.uuid == agent_uuid)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_default_agent(db: AsyncSession) -> Optional[Agent]:
    """Get the default Tooler agent"""
    query = select(Agent).where(Agent.is_default == True)  # noqa: E712
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_user_agents(db: AsyncSession, user_id: int) -> List[Agent]:
    """Get all agents for a user"""
    # Get both user-created agents and the default Tooler agent
    query = select(Agent).where(
        or_(
            Agent.user_id == user_id,
            Agent.is_default == True  # noqa: E712
        )
    )
    result = await db.execute(query)
    return result.scalars().all()


async def update_agent(db: AsyncSession, agent_id: int, **kwargs) -> Optional[Agent]:
    """Update agent data"""
    agent = await get_agent_by_id(db, agent_id)
    if not agent:
        return None
    
    # Update agent fields
    for key, value in kwargs.items():
        if hasattr(agent, key):
            setattr(agent, key, value)
    
    await db.commit()
    await db.refresh(agent)
    return agent


async def delete_agent(db: AsyncSession, agent_id: int) -> bool:
    """Delete an agent"""
    agent = await get_agent_by_id(db, agent_id)
    if not agent or agent.is_default:  # Prevent deletion of default agent
        return False
    
    await db.delete(agent)
    await db.commit()
    return True


async def get_agent_mcp_servers(db: AsyncSession, agent_id: int) -> List[MCPServer]:
    """Get all MCP servers associated with an agent"""
    query = select(MCPServer).join(AgentMCPServer).where(AgentMCPServer.agent_id == agent_id)
    result = await db.execute(query)
    return result.scalars().all()


async def add_mcp_server_to_agent(db: AsyncSession, agent_id: int, mcp_server_id: int) -> AgentMCPServer:
    """Associate an MCP server with an agent"""
    agent_mcp_server = AgentMCPServer(agent_id=agent_id, mcp_server_id=mcp_server_id)
    
    db.add(agent_mcp_server)
    await db.commit()
    await db.refresh(agent_mcp_server)
    return agent_mcp_server


async def remove_mcp_server_from_agent(db: AsyncSession, agent_id: int, mcp_server_id: int) -> bool:
    """Remove an MCP server association from an agent"""
    query = select(AgentMCPServer).where(
        and_(
            AgentMCPServer.agent_id == agent_id,
            AgentMCPServer.mcp_server_id == mcp_server_id
        )
    )
    result = await db.execute(query)
    agent_mcp_server = result.scalar_one_or_none()
    
    if not agent_mcp_server:
        return False
    
    await db.delete(agent_mcp_server)
    await db.commit()
    return True
