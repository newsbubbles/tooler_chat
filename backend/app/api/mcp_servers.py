from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List

from app.db.database import get_db
from app.core.auth import get_current_active_user
from app.models.base import User
from app.schemas.mcp_server import MCPServerCreate, MCPServerUpdate, MCPServerResponse, MCPServerDetailResponse
from app.schemas.agent import AgentResponse
from app.services.mcp_server_service import (
    create_mcp_server, get_user_mcp_servers, get_mcp_server_by_id, get_mcp_server_by_uuid,
    update_mcp_server, delete_mcp_server, get_agents_using_mcp_server
)
from app.services.agent_service import get_agent_by_id

router = APIRouter(tags=["mcp_servers"])


@router.post("/mcp-servers", response_model=MCPServerResponse, status_code=status.HTTP_201_CREATED)
async def create_new_mcp_server(
    mcp_server_data: MCPServerCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new MCP server"""
    mcp_server = await create_mcp_server(
        db=db,
        user_id=current_user.id,
        name=mcp_server_data.name,
        code=mcp_server_data.code,
        description=mcp_server_data.description
    )
    return mcp_server


@router.get("/mcp-servers", response_model=List[MCPServerResponse])
async def get_mcp_servers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all MCP servers for the current user"""
    mcp_servers = await get_user_mcp_servers(db, current_user.id)
    return mcp_servers


@router.get("/mcp-servers/{mcp_server_uuid}", response_model=MCPServerDetailResponse)
async def get_mcp_server(
    mcp_server_uuid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific MCP server by UUID"""
    mcp_server = await get_mcp_server_by_uuid(db, mcp_server_uuid)
    if not mcp_server:
        raise HTTPException(status_code=404, detail="MCP server not found")
    
    # Check if user has access to this MCP server
    if mcp_server.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this MCP server")
    
    # Get agents associated with this MCP server
    agent_ids = await get_agents_using_mcp_server(db, mcp_server.id)
    agents = []
    
    for agent_id in agent_ids:
        agent = await get_agent_by_id(db, agent_id)
        if agent and (agent.is_default or agent.user_id == current_user.id):
            agents.append(agent)
    
    # Create response with MCP server and its associated agents
    response = MCPServerDetailResponse.model_validate(mcp_server)
    response.agents = [AgentResponse.model_validate(a) for a in agents]
    
    return response


@router.put("/mcp-servers/{mcp_server_uuid}", response_model=MCPServerResponse)
async def update_existing_mcp_server(
    mcp_server_uuid: str,
    mcp_server_data: MCPServerUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update an existing MCP server"""
    mcp_server = await get_mcp_server_by_uuid(db, mcp_server_uuid)
    if not mcp_server:
        raise HTTPException(status_code=404, detail="MCP server not found")
    
    # Verify ownership
    if mcp_server.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this MCP server")
    
    # Perform the update
    update_data = mcp_server_data.model_dump(exclude_unset=True)
    updated_mcp_server = await update_mcp_server(db, mcp_server.id, **update_data)
    
    return updated_mcp_server


@router.delete("/mcp-servers/{mcp_server_uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_mcp_server(
    mcp_server_uuid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete an MCP server"""
    mcp_server = await get_mcp_server_by_uuid(db, mcp_server_uuid)
    if not mcp_server:
        raise HTTPException(status_code=404, detail="MCP server not found")
    
    # Verify ownership
    if mcp_server.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this MCP server")
    
    result = await delete_mcp_server(db, mcp_server.id)
    if not result:
        raise HTTPException(status_code=500, detail="Failed to delete MCP server")
