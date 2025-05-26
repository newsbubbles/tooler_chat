from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.base import Session, User
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID


async def create_session(db: AsyncSession, user_id: int, expires_delta: timedelta = timedelta(days=7)) -> Session:
    """Create a new user session"""
    expires_at = datetime.utcnow() + expires_delta
    session = Session(user_id=user_id, expires_at=expires_at)
    
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def get_session(db: AsyncSession, session_id: int) -> Optional[Session]:
    """Get session by ID"""
    return await db.get(Session, session_id)


async def get_session_by_uuid(db: AsyncSession, session_uuid: UUID) -> Optional[Session]:
    """Get session by UUID"""
    query = select(Session).where(Session.uuid == session_uuid)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_active_session(db: AsyncSession, session_uuid: UUID) -> Optional[Session]:
    """Get active session by UUID"""
    now = datetime.utcnow()
    query = select(Session).where(
        (Session.uuid == session_uuid) & 
        (Session.expires_at > now)
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_user_sessions(db: AsyncSession, user_id: int) -> list[Session]:
    """Get all sessions for a user"""
    query = select(Session).where(Session.user_id == user_id)
    result = await db.execute(query)
    return result.scalars().all()


async def delete_session(db: AsyncSession, session_id: int) -> bool:
    """Delete a session"""
    session = await get_session(db, session_id)
    if not session:
        return False
    
    await db.delete(session)
    await db.commit()
    return True


async def delete_user_sessions(db: AsyncSession, user_id: int) -> int:
    """Delete all sessions for a user and return count of deleted sessions"""
    sessions = await get_user_sessions(db, user_id)
    count = 0
    
    for session in sessions:
        await db.delete(session)
        count += 1
    
    await db.commit()
    return count


async def cleanup_expired_sessions(db: AsyncSession) -> int:
    """Delete expired sessions and return count of deleted sessions"""
    now = datetime.utcnow()
    query = select(Session).where(Session.expires_at <= now)
    result = await db.execute(query)
    expired_sessions = result.scalars().all()
    count = 0
    
    for session in expired_sessions:
        await db.delete(session)
        count += 1
    
    await db.commit()
    return count
