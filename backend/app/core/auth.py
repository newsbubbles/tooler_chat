from datetime import datetime, timedelta
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel.ext.asyncio.session import AsyncSession
from uuid import UUID
import os

from app.db.database import get_db
from app.models.base import User, Session
from app.core.security_utils import verify_password

# JWT settings
SECRET_KEY = os.getenv("SECRET_KEY", "very-secret-key-for-development-only")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 1 week

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


async def authenticate_user(db: AsyncSession, username: str, password: str) -> User | None:
    """Authenticate user by username and password"""
    from app.services.user_service import get_user_by_username
    user = await get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    """Decode JWT token and get current user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        session_uuid: str = payload.get("sub")
        if session_uuid is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    
    # Get the session with the given UUID
    from app.services.session_service import get_active_session
    session = await get_active_session(db, UUID(session_uuid))
    if session is None:
        raise credentials_exception
    
    # Get the user associated with the session
    from app.services.user_service import get_user_by_id
    user = await get_user_by_id(db, session.user_id)
    if user is None or not user.is_active:
        raise credentials_exception
        
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user
