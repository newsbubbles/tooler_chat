from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class MCPServerBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    code: str


class MCPServerCreate(MCPServerBase):
    pass


class MCPServerUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    code: Optional[str] = None


class MCPServerResponse(MCPServerBase):
    uuid: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class MCPServerDetailResponse(MCPServerResponse):
    agents: List["AgentResponse"] = []
    
    class Config:
        from_attributes = True


# Circular import workaround - will be defined in agent.py
from app.schemas.agent import AgentResponse
MCPServerDetailResponse.update_forward_refs()


class AgentMCPServerAdd(BaseModel):
    mcp_server_id: int


class AgentMCPServerRemove(BaseModel):
    mcp_server_id: int
