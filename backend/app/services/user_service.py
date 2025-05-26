from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.base import User
from app.core.auth import get_password_hash
from typing import List, Optional
from uuid import UUID


async def create_user(db: AsyncSession, username: str, email: str, password: str) -> User:
    """Create a new user"""
    hashed_password = get_password_hash(password)
    user = User(
        username=username,
        email=email,
        hashed_password=hashed_password
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    """Get user by ID"""
    return await db.get(User, user_id)


async def get_user_by_uuid(db: AsyncSession, user_uuid: UUID) -> Optional[User]:
    """Get user by UUID"""
    query = select(User).where(User.uuid == user_uuid)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    """Get user by username"""
    query = select(User).where(User.username == username)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Get user by email"""
    query = select(User).where(User.email == email)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_users(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[User]:
    """Get a list of users"""
    query = select(User).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


async def update_user(db: AsyncSession, user_id: int, **kwargs) -> Optional[User]:
    """Update user data"""
    user = await get_user_by_id(db, user_id)
    if not user:
        return None
    
    # If password is being updated, hash it
    if 'password' in kwargs:
        kwargs['hashed_password'] = get_password_hash(kwargs.pop('password'))
    
    # Update user fields
    for key, value in kwargs.items():
        if hasattr(user, key):
            setattr(user, key, value)
    
    await db.commit()
    await db.refresh(user)
    return user


async def delete_user(db: AsyncSession, user_id: int) -> bool:
    """Delete a user"""
    user = await get_user_by_id(db, user_id)
    if not user:
        return False
    
    await db.delete(user)
    await db.commit()
    return True
