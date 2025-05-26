from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.base import MCPServer, AgentMCPServer
from typing import List, Optional
from uuid import UUID


async def create_mcp_server(db: AsyncSession, user_id: int, name: str, code: str, description: Optional[str] = None) -> MCPServer:
    """Create a new MCP server"""
    mcp_server = MCPServer(
        user_id=user_id,
        name=name,
        description=description,
        code=code
    )
    
    db.add(mcp_server)
    await db.commit()
    await db.refresh(mcp_server)
    return mcp_server


async def get_mcp_server_by_id(db: AsyncSession, mcp_server_id: int) -> Optional[MCPServer]:
    """Get MCP server by ID"""
    return await db.get(MCPServer, mcp_server_id)


async def get_mcp_server_by_uuid(db: AsyncSession, mcp_server_uuid: UUID) -> Optional[MCPServer]:
    """Get MCP server by UUID"""
    query = select(MCPServer).where(MCPServer.uuid == mcp_server_uuid)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_user_mcp_servers(db: AsyncSession, user_id: int) -> List[MCPServer]:
    """Get all MCP servers for a user"""
    query = select(MCPServer).where(MCPServer.user_id == user_id)
    result = await db.execute(query)
    return result.scalars().all()


async def update_mcp_server(db: AsyncSession, mcp_server_id: int, **kwargs) -> Optional[MCPServer]:
    """Update MCP server data"""
    mcp_server = await get_mcp_server_by_id(db, mcp_server_id)
    if not mcp_server:
        return None
    
    # Update MCP server fields
    for key, value in kwargs.items():
        if hasattr(mcp_server, key):
            setattr(mcp_server, key, value)
    
    await db.commit()
    await db.refresh(mcp_server)
    return mcp_server


async def delete_mcp_server(db: AsyncSession, mcp_server_id: int) -> bool:
    """Delete an MCP server"""
    mcp_server = await get_mcp_server_by_id(db, mcp_server_id)
    if not mcp_server:
        return False
    
    await db.delete(mcp_server)
    await db.commit()
    return True


async def get_agents_using_mcp_server(db: AsyncSession, mcp_server_id: int) -> List[int]:
    """Get IDs of all agents that use a specific MCP server"""
    query = select(AgentMCPServer.agent_id).where(AgentMCPServer.mcp_server_id == mcp_server_id)
    result = await db.execute(query)
    return result.scalars().all()
