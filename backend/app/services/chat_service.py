from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.base import ChatSession, Message, Agent
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter
import json


async def create_chat_session(db: AsyncSession, user_id: int, agent_id: int, title: str) -> ChatSession:
    """Create a new chat session"""
    chat_session = ChatSession(
        user_id=user_id,
        agent_id=agent_id,
        title=title
    )
    
    db.add(chat_session)
    await db.commit()
    await db.refresh(chat_session)
    return chat_session


async def get_chat_session_by_id(db: AsyncSession, chat_session_id: int) -> Optional[ChatSession]:
    """Get chat session by ID"""
    return await db.get(ChatSession, chat_session_id)


async def get_chat_session_by_uuid(db: AsyncSession, session_uuid: UUID) -> Optional[ChatSession]:
    """Get chat session by UUID"""
    query = select(ChatSession).where(ChatSession.uuid == session_uuid)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_user_chat_sessions(db: AsyncSession, user_id: int) -> List[ChatSession]:
    """Get all chat sessions for a user"""
    query = select(ChatSession).where(ChatSession.user_id == user_id)
    result = await db.execute(query)
    return result.scalars().all()


async def get_user_agent_chat_sessions(db: AsyncSession, user_id: int, agent_id: int) -> List[ChatSession]:
    """Get all chat sessions for a user with a specific agent"""
    query = select(ChatSession).where(
        (ChatSession.user_id == user_id) & 
        (ChatSession.agent_id == agent_id)
    )
    result = await db.execute(query)
    return result.scalars().all()


async def update_chat_session(db: AsyncSession, chat_session_id: int, **kwargs) -> Optional[ChatSession]:
    """Update chat session data"""
    chat_session = await get_chat_session_by_id(db, chat_session_id)
    if not chat_session:
        return None
    
    # Update chat session fields
    for key, value in kwargs.items():
        if hasattr(chat_session, key):
            setattr(chat_session, key, value)
    
    chat_session.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(chat_session)
    return chat_session


async def delete_chat_session(db: AsyncSession, chat_session_id: int) -> bool:
    """Delete a chat session"""
    chat_session = await get_chat_session_by_id(db, chat_session_id)
    if not chat_session:
        return False
    
    await db.delete(chat_session)
    await db.commit()
    return True


async def create_message(db: AsyncSession, chat_session_id: int, role: str, content: str) -> Message:
    """Create a new message"""
    message = Message(
        chat_session_id=chat_session_id,
        role=role,
        content=content
    )
    
    db.add(message)
    await db.commit()
    await db.refresh(message)
    
    # Update the chat session's updated_at timestamp
    chat_session = await get_chat_session_by_id(db, chat_session_id)
    if chat_session:
        chat_session.updated_at = datetime.utcnow()
        await db.commit()
    
    return message


async def get_chat_session_messages(db: AsyncSession, chat_session_id: int) -> List[Message]:
    """Get all messages for a chat session ordered by timestamp"""
    query = select(Message).where(Message.chat_session_id == chat_session_id).order_by(Message.timestamp)
    result = await db.execute(query)
    return result.scalars().all()


async def get_messages_as_model_messages(db: AsyncSession, chat_session_id: int) -> List[ModelMessage]:
    """Get chat session messages in a format suitable for the agent"""
    messages = await get_chat_session_messages(db, chat_session_id)
    model_messages_json = []
    
    for msg in messages:
        timestamp = msg.timestamp.isoformat()
        
        if msg.role == "user":
            # User messages use ModelRequest format with parts
            message_json = {
                "kind": "request",
                "request": {
                    "user_prompt": msg.content,
                    # Add parts array which appears to be required
                    "parts": [
                        {
                            "type": "user_prompt",
                            "content": msg.content,
                            "timestamp": timestamp
                        }
                    ]
                },
                "timestamp": timestamp
            }
        else:
            # Model messages use ModelResponse format with parts
            message_json = {
                "kind": "response",
                "response": {
                    "text": msg.content,
                    # Add parts array which appears to be required
                    "parts": [
                        {
                            "type": "text",
                            "content": msg.content,
                            "timestamp": timestamp
                        }
                    ]
                },
                "timestamp": timestamp
            }
        model_messages_json.append(json.dumps(message_json))
    
    # If there are no messages, return an empty list
    if not model_messages_json:
        return []
    
    return ModelMessagesTypeAdapter.validate_json('[' + ','.join(model_messages_json) + ']')


async def add_model_messages(db: AsyncSession, chat_session_id: int, model_messages_json: str) -> List[Message]:
    """Add messages from agent response to the database"""
    model_messages = ModelMessagesTypeAdapter.validate_json(model_messages_json)
    created_messages = []
    
    for msg in model_messages:
        try:
            if msg.kind == "request":
                role = "user"
                # Try to get content from parts or directly from user_prompt
                if hasattr(msg.request, "parts") and msg.request.parts:
                    content = msg.request.parts[0].content
                else:
                    content = msg.request.user_prompt
            else:  # response
                role = "model"
                # Try to get content from parts or directly from text
                if hasattr(msg.response, "parts") and msg.response.parts:
                    content = msg.response.parts[0].content
                else:
                    content = msg.response.text
                    
            message = await create_message(
                db=db,
                chat_session_id=chat_session_id,
                role=role,
                content=content
            )
            created_messages.append(message)
        except Exception as e:
            # Log the error but continue processing other messages
            print(f"Error processing message: {str(e)}")
            continue
    
    return created_messages
