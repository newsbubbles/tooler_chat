from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List

from app.db.database import get_db
from app.core.auth import get_current_active_user
from app.models.base import User
from app.schemas.agent import AgentCreate, AgentUpdate, AgentResponse, AgentDetailResponse
from app.schemas.mcp_server import AgentMCPServerAdd, AgentMCPServerRemove, MCPServerResponse
from app.services.agent_service import (
    create_agent, get_user_agents, get_agent_by_id, get_agent_by_uuid,
    update_agent, delete_agent, get_agent_mcp_servers,
    add_mcp_server_to_agent, remove_mcp_server_from_agent
)
from app.services.mcp_server_service import get_mcp_server_by_id

router = APIRouter(tags=["agents"])


@router.post("/agents", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_new_agent(
    agent_data: AgentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new agent"""
    agent = await create_agent(
        db=db,
        user_id=current_user.id,
        name=agent_data.name,
        system_prompt=agent_data.system_prompt,
        description=agent_data.description,
        is_default=False  # User-created agents are never default
    )
    return agent


@router.get("/agents", response_model=List[AgentResponse])
async def get_agents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all agents for the current user, including the default Tooler agent"""
    agents = await get_user_agents(db, current_user.id)
    return agents


@router.get("/agents/{agent_uuid}", response_model=AgentDetailResponse)
async def get_agent(
    agent_uuid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific agent by UUID"""
    agent = await get_agent_by_uuid(db, agent_uuid)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Check if user has access to this agent
    if not agent.is_default and agent.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this agent")
    
    # Get MCP servers associated with this agent
    mcp_servers = await get_agent_mcp_servers(db, agent.id)
    
    # Create response with agent and its MCP servers
    response = AgentDetailResponse.model_validate(agent)
    response.mcp_servers = [MCPServerResponse.model_validate(s) for s in mcp_servers]
    
    return response


@router.put("/agents/{agent_uuid}", response_model=AgentResponse)
async def update_existing_agent(
    agent_uuid: str,
    agent_data: AgentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update an existing agent"""
    agent = await get_agent_by_uuid(db, agent_uuid)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Verify ownership (except for default agent which just uses system prompt editing)
    if not agent.is_default and agent.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this agent")
    
    # For default agent, only allow system_prompt updates
    if agent.is_default and (agent_data.name is not None or agent_data.description is not None):
        raise HTTPException(status_code=400, detail="Cannot change the name or description of the default agent")
    
    # Perform the update
    update_data = agent_data.model_dump(exclude_unset=True)
    updated_agent = await update_agent(db, agent.id, **update_data)
    
    return updated_agent


@router.delete("/agents/{agent_uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_agent(
    agent_uuid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete an agent"""
    agent = await get_agent_by_uuid(db, agent_uuid)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Cannot delete the default agent
    if agent.is_default:
        raise HTTPException(status_code=400, detail="Cannot delete the default agent")
    
    # Verify ownership
    if agent.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this agent")
    
    result = await delete_agent(db, agent.id)
    if not result:
        raise HTTPException(status_code=500, detail="Failed to delete agent")


@router.post("/agents/{agent_uuid}/mcp-servers", response_model=AgentResponse)
async def add_mcp_server(
    agent_uuid: str,
    data: AgentMCPServerAdd,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Add an MCP server to an agent"""
    agent = await get_agent_by_uuid(db, agent_uuid)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Verify agent ownership/access
    if not agent.is_default and agent.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this agent")
    
    # Check if MCP server exists and belongs to the user
    mcp_server = await get_mcp_server_by_id(db, data.mcp_server_id)
    if not mcp_server:
        raise HTTPException(status_code=404, detail="MCP server not found")
    
    if mcp_server.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to use this MCP server")
    
    # Add MCP server to agent
    await add_mcp_server_to_agent(db, agent.id, mcp_server.id)
    
    return agent


@router.delete("/agents/{agent_uuid}/mcp-servers", response_model=AgentResponse)
async def remove_mcp_server(
    agent_uuid: str,
    data: AgentMCPServerRemove,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Remove an MCP server from an agent"""
    agent = await get_agent_by_uuid(db, agent_uuid)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Verify agent ownership/access
    if not agent.is_default and agent.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this agent")
    
    # Remove MCP server from agent
    result = await remove_mcp_server_from_agent(db, agent.id, data.mcp_server_id)
    if not result:
        raise HTTPException(status_code=404, detail="MCP server not associated with this agent")
    
    return agent
