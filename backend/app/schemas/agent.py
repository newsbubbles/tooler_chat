from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class AgentBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    system_prompt: str


class AgentCreate(AgentBase):
    pass


class AgentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    system_prompt: Optional[str] = None


class AgentResponse(AgentBase):
    uuid: UUID
    is_default: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class AgentDetailResponse(AgentResponse):
    mcp_servers: List["MCPServerResponse"] = []
    
    class Config:
        from_attributes = True


# Circular import workaround - will be defined in mcp_server.py
from app.schemas.mcp_server import MCPServerResponse
AgentDetailResponse.update_forward_refs()