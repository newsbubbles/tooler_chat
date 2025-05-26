from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.database import get_db
from app.core.auth import get_current_active_user
from app.models.base import User
from app.schemas.auth import UserResponse

router = APIRouter(tags=["users"])


@router.get("/users/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """Get current user information"""
    return current_user
