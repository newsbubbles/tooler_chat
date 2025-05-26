from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class ChatSessionCreate(BaseModel):
    agent_id: int
    title: str = Field(..., min_length=1, max_length=100)


class ChatSessionUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=100)


class ChatSessionResponse(BaseModel):
    uuid: UUID
    title: str
    agent_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class MessageBase(BaseModel):
    role: str
    content: str
    timestamp: datetime


class MessageCreate(BaseModel):
    content: str


class MessageResponse(MessageBase):
    uuid: UUID
    
    class Config:
        from_attributes = True


class ChatSessionDetailResponse(ChatSessionResponse):
    messages: List[MessageResponse] = []
    
    class Config:
        from_attributes = True
