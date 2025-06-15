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
from app.core.logging import get_logger

# JWT settings
SECRET_KEY = os.getenv("SECRET_KEY", "very-secret-key-for-development-only")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 1 week

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

# Get a logger
logger = get_logger("app.core.auth")

async def authenticate_user(db: AsyncSession, username: str, password: str) -> User | None:
    """Authenticate user by username and password"""
    from app.services.user_service import get_user_by_username
    user = await get_user_by_username(db, username)
    if not user:
        logger.warning_data(f"Authentication failed: user not found", {"username": username})
        return None
    if not verify_password(password, user.hashed_password):
        logger.warning_data(f"Authentication failed: invalid password", {"username": username})
        return None
    
    logger.info_data(f"User authenticated successfully", {"username": username, "user_id": user.id})
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
            logger.warning("JWT token missing 'sub' claim")
            raise credentials_exception
    except jwt.PyJWTError as e:
        logger.warning_data("JWT token validation failed", {"error": str(e)})
        raise credentials_exception
    
    # Get the session with the given UUID
    from app.services.session_service import get_active_session
    session = await get_active_session(db, UUID(session_uuid))
    if session is None:
        logger.warning_data("Session not found or expired", {"session_uuid": session_uuid})
        raise credentials_exception
    
    # Get the user associated with the session
    from app.services.user_service import get_user_by_id
    user = await get_user_by_id(db, session.user_id)
    if user is None:
        logger.warning_data("User not found for session", 
                         {"session_uuid": session_uuid, "user_id": session.user_id})
        raise credentials_exception
        
    if not user.is_active:
        logger.warning_data("Inactive user attempted to access API", 
                         {"user_id": user.id, "username": user.username})
        raise credentials_exception
        
    logger.debug_data("User authenticated via token", 
                   {"user_id": user.id, "username": user.username})
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user"""
    if not current_user.is_active:
        logger.warning_data("Inactive user attempted to access API", 
                         {"user_id": current_user.id, "username": current_user.username})
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_current_superuser(current_user: User = Depends(get_current_active_user)) -> User:
    """Get current superuser/admin user
    
    For now, this just checks if username is 'admin' since we don't have a proper admin role.
    In a production environment, you'd want to check a proper is_admin or roles field.
    """
    # For now, only the 'admin' user has admin privileges
    # You should expand this to use proper role-based controls
    if current_user.username != "admin":
        logger.warning_data("Non-admin user attempted to access admin-only endpoint", 
                         {"user_id": current_user.id, "username": current_user.username})
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    logger.debug_data("Admin access granted", 
                   {"user_id": current_user.id, "username": current_user.username})
    return current_user
