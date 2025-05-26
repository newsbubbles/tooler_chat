from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from uuid import UUID


class Token(BaseModel):
    access_token: str
    token_type: str
    session_uuid: UUID


class TokenData(BaseModel):
    session_uuid: Optional[str] = None


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    uuid: UUID
    username: str
    email: EmailStr
    is_active: bool
    
    class Config:
        from_attributes = True
