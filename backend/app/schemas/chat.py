from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class ChatSessionCreate(BaseModel):
    agent_id: UUID  # Changed from int to UUID
    title: str = Field(..., min_length=1, max_length=100)


class ChatSessionUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=100)


class ChatSessionResponse(BaseModel):
    uuid: UUID
    id: UUID = Field(None)  # Added id field for UUID consistency
    title: str
    agent_id: UUID  # Changed from int to UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        
    def model_post_init(self, __context):
        # Ensure id is set to the uuid value
        self.id = self.uuid


class MessageBase(BaseModel):
    role: str
    content: str
    timestamp: datetime


class MessageCreate(BaseModel):
    content: str


class MessageResponse(MessageBase):
    uuid: UUID
    id: UUID = Field(None)  # Added id field for UUID consistency
    
    class Config:
        from_attributes = True
        
    def model_post_init(self, __context):
        # Ensure id is set to the uuid value
        self.id = self.uuid


class ChatSessionDetailResponse(ChatSessionResponse):
    messages: List[MessageResponse] = []
    
    class Config:
        from_attributes = True
