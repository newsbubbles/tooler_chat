from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy import update
from typing import List, Dict, Any, Optional
import json
import time
from datetime import datetime, timezone
from uuid import UUID
import os
import asyncio
import tempfile

from app.db.database import get_db
from app.core.auth import get_current_active_user
from app.core.agent_manager import get_agent_instance  # Use our new agent_manager
from app.models.base import User, Message
from app.schemas.chat import (
    ChatSessionCreate, ChatSessionUpdate, ChatSessionResponse,
    ChatSessionDetailResponse, MessageCreate, MessageResponse
)
from app.services.chat_service import (
    create_chat_session, get_user_chat_sessions, get_user_agent_chat_sessions,
    get_chat_session_by_id, get_chat_session_by_uuid, update_chat_session,
    delete_chat_session, create_message, get_chat_session_messages,
    get_messages_as_model_messages, add_model_messages
)
from app.services.agent_service import get_agent_by_id, get_agent_mcp_servers, get_agent_by_uuid
from app.services.mcp_server_service import get_mcp_server_by_id

from pydantic_ai import Agent, RunContext
from pydantic_ai.mcp import MCPServerStdio
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.agent import AgentRunResult

# Import enhanced logging
from app.core.logging import get_logger
from app.core.logging.decorators import log_endpoint
# Import the chat logging utilities
from app.api.chat_logger import (
    log_chat_session_operation,
    log_message_operation,
    log_agent_operation,
    log_chat_error,
    timed_operation,
    log_message_batch,
    log_streaming_progress
)

# Configure logging
logger = get_logger(__name__)

router = APIRouter(tags=["chat"])

# Configure API keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Add function to reset agent cache for debugging
async def reset_agent_cache(agent_uuid: Optional[str] = None):
    """Reset the agent cache for a specific agent or all agents
    
    This is useful for debugging issues where agent state might be causing problems
    """
    from app.core.agent_manager import _agent_cache
    
    if agent_uuid:
        # Clear specific agent
        agent_key = f"agent_{agent_uuid}"
        if "tooler" in _agent_cache: 
            logger.info_data(f"Clearing tooler agent cache", {"agent_uuid": agent_uuid})
            del _agent_cache["tooler"]
        if agent_key in _agent_cache:
            logger.info_data(f"Clearing agent cache", {"agent_uuid": agent_uuid})
            del _agent_cache[agent_key]
    else:
        # Clear all agents
        logger.info_data("Clearing all agent caches", {"cache_size": len(_agent_cache)})
        _agent_cache.clear()
    
    return True

# Add function to update message content
async def update_message(db: AsyncSession, message_id: int, content: str) -> Optional[Message]:
    """Update a message's content"""
    stmt = (
        update(Message)
        .where(Message.id == message_id)
        .values(content=content)
        .returning(Message)
    )
    result = await db.execute(stmt)
    await db.commit()
    return result.scalar_one_or_none()

@router.post("/chat/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
@log_endpoint("create_chat_session")
async def create_new_chat_session(
    session_data: ChatSessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new chat session"""
    # Extract UUID string and convert to UUID object
    agent_uuid = session_data.agent_id
    
    # Verify agent exists and user has access to it
    agent = await get_agent_by_uuid(db, agent_uuid)
    if not agent:
        log_chat_error("not_found", "Agent not found", "verifying_agent", 
                     agent_uuid=agent_uuid)
        raise HTTPException(status_code=404, detail="Agent not found")
    
    if not agent.is_default and agent.user_id != current_user.id:
        log_chat_error("unauthorized", "Not authorized to use this agent", "checking_authorization",
                     agent_uuid=agent_uuid, user_id=current_user.id)
        raise HTTPException(status_code=403, detail="Not authorized to use this agent")
    
    # Create chat session
    chat_session = await create_chat_session(
        db=db,
        user_id=current_user.id,
        agent_id=agent.id,
        title=session_data.title
    )
    
    # Log the creation
    log_chat_session_operation(
        "created",
        str(chat_session.uuid),
        current_user.id,
        title=session_data.title,
        agent_uuid=agent_uuid,
        agent_name=agent.name
    )
    
    # Create a response dictionary with the proper UUIDs
    response = {
        "uuid": chat_session.uuid,
        "id": chat_session.uuid,  # Use UUID for id as well
        "title": chat_session.title,
        "agent_id": agent.uuid,  # Use agent's UUID rather than database ID
        "created_at": chat_session.created_at,
        "updated_at": chat_session.updated_at
    }
    
    # Now validate the response
    return ChatSessionResponse.model_validate(response)


@router.get("/chat/sessions", response_model=List[ChatSessionResponse])
@log_endpoint("get_chat_sessions")
async def get_chat_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    agent_uuid: str = None
):
    """Get all chat sessions for the current user, optionally filtered by agent"""
    if agent_uuid:
        # Verify agent exists and user has access to it
        agent = await get_agent_by_uuid(db, agent_uuid)
        if not agent:
            log_chat_error("not_found", "Agent not found", "get_chat_sessions", 
                         agent_uuid=agent_uuid) 
            raise HTTPException(status_code=404, detail="Agent not found")
        
        if not agent.is_default and agent.user_id != current_user.id:
            log_chat_error("unauthorized", "Not authorized to access sessions", "get_chat_sessions",
                         agent_uuid=agent_uuid, user_id=current_user.id)
            raise HTTPException(status_code=403, detail="Not authorized to access this agent's sessions")
        
        sessions = await get_user_agent_chat_sessions(db, current_user.id, agent.id)
    else:
        sessions = await get_user_chat_sessions(db, current_user.id)
    
    # Process each session to use UUIDs instead of integer IDs
    result = []
    for session in sessions:
        # Get agent to get its UUID
        agent = await get_agent_by_id(db, session.agent_id)
        agent_uuid_str = agent.uuid if agent else None
        
        # Create response dictionary with proper UUID conversion
        session_data = {
            "uuid": session.uuid,
            "id": session.uuid,  # Use UUID for id as well
            "title": session.title,
            "agent_id": agent_uuid_str,
            "created_at": session.created_at,
            "updated_at": session.updated_at
        }
        
        result.append(ChatSessionResponse.model_validate(session_data))
    
    return result


@router.get("/chat/sessions/{session_uuid}", response_model=ChatSessionDetailResponse)
@log_endpoint("get_chat_session")
async def get_chat_session(
    session_uuid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific chat session by UUID with its messages"""
    chat_session = await get_chat_session_by_uuid(db, session_uuid)
    if not chat_session:
        log_chat_error("not_found", "Chat session not found", "get_chat_session", 
                     session_uuid=session_uuid)
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    # Verify ownership
    if chat_session.user_id != current_user.id:
        log_chat_error("unauthorized", "Not authorized to access this chat session", "get_chat_session",
                    session_uuid=session_uuid, user_id=current_user.id, session_owner=chat_session.user_id)
        raise HTTPException(status_code=403, detail="Not authorized to access this chat session")
    
    # Get messages for this chat session
    messages = await get_chat_session_messages(db, chat_session.id)
    
    # Get agent to get its UUID
    agent = await get_agent_by_id(db, chat_session.agent_id)
    agent_uuid_str = agent.uuid if agent else None
    
    # Create response dictionary with proper UUID conversion
    session_data = {
        "uuid": chat_session.uuid,
        "id": chat_session.uuid,  # Use UUID for id as well
        "title": chat_session.title,
        "agent_id": agent_uuid_str,
        "created_at": chat_session.created_at,
        "updated_at": chat_session.updated_at,
        "messages": []
    }
    
    # Process messages
    for message in messages:
        msg_data = {
            "uuid": message.uuid,
            "id": message.uuid,  # Use UUID for id as well
            "role": message.role,
            "content": message.content,
            "timestamp": message.timestamp
        }
        session_data["messages"].append(MessageResponse.model_validate(msg_data))
    
    log_message_batch("retrieved", session_uuid, len(messages), 
                    agent_name=agent.name if agent else "unknown")
    
    return ChatSessionDetailResponse.model_validate(session_data)


@router.put("/chat/sessions/{session_uuid}", response_model=ChatSessionResponse)
@log_endpoint("update_chat_session")
async def update_existing_chat_session(
    session_uuid: str,
    session_data: ChatSessionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update an existing chat session"""
    chat_session = await get_chat_session_by_uuid(db, session_uuid)
    if not chat_session:
        log_chat_error("not_found", "Chat session not found", "update_chat_session", 
                     session_uuid=session_uuid)
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    # Verify ownership
    if chat_session.user_id != current_user.id:
        log_chat_error("unauthorized", "Not authorized to update this chat session", "update_chat_session",
                    session_uuid=session_uuid, user_id=current_user.id, session_owner=chat_session.user_id)
        raise HTTPException(status_code=403, detail="Not authorized to update this chat session")
    
    # Perform the update
    update_data = session_data.model_dump(exclude_unset=True)
    updated_chat_session = await update_chat_session(db, chat_session.id, **update_data)
    
    # Get agent to get its UUID
    agent = await get_agent_by_id(db, updated_chat_session.agent_id)
    agent_uuid_str = agent.uuid if agent else None
    
    log_chat_session_operation("updated", session_uuid, current_user.id,
                              title=updated_chat_session.title,
                              agent_uuid=agent_uuid_str)
    
    # Create response dictionary with proper UUID conversion
    response_data = {
        "uuid": updated_chat_session.uuid,
        "id": updated_chat_session.uuid,  # Use UUID for id as well
        "title": updated_chat_session.title,
        "agent_id": agent_uuid_str,
        "created_at": updated_chat_session.created_at,
        "updated_at": updated_chat_session.updated_at
    }
    
    return ChatSessionResponse.model_validate(response_data)


@router.delete("/chat/sessions/{session_uuid}", status_code=status.HTTP_204_NO_CONTENT)
@log_endpoint("delete_chat_session")
async def delete_existing_chat_session(
    session_uuid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a chat session"""
    chat_session = await get_chat_session_by_uuid(db, session_uuid)
    if not chat_session:
        log_chat_error("not_found", "Chat session not found", "delete_chat_session", 
                     session_uuid=session_uuid)
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    # Verify ownership
    if chat_session.user_id != current_user.id:
        log_chat_error("unauthorized", "Not authorized to delete this chat session", "delete_chat_session",
                    session_uuid=session_uuid, user_id=current_user.id, session_owner=chat_session.user_id)
        raise HTTPException(status_code=403, detail="Not authorized to delete this chat session")
    
    log_chat_session_operation("deleted", session_uuid, current_user.id)
    
    result = await delete_chat_session(db, chat_session.id)
    if not result:
        log_chat_error("delete_failed", "Failed to delete chat session", "delete_chat_session",
                     session_uuid=session_uuid)
        raise HTTPException(status_code=500, detail="Failed to delete chat session")


@router.post("/chat/sessions/{session_uuid}/messages", response_model=MessageResponse)
@log_endpoint("create_chat_message")
async def create_chat_message(
    session_uuid: str,
    message_data: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new chat message (non-streaming)"""
    chat_session = await get_chat_session_by_uuid(db, session_uuid)
    if not chat_session:
        log_chat_error("not_found", "Chat session not found", "create_chat_message", 
                     session_uuid=session_uuid)
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    # Verify ownership
    if chat_session.user_id != current_user.id:
        log_chat_error("unauthorized", "Not authorized to post to this chat session", "create_chat_message",
                    session_uuid=session_uuid, user_id=current_user.id, session_owner=chat_session.user_id)
        raise HTTPException(status_code=403, detail="Not authorized to post to this chat session")
    
    # Create user message
    user_message = await create_message(
        db=db,
        chat_session_id=chat_session.id,
        role="user",
        content=message_data.content
    )
    
    log_message_operation("created", session_uuid, str(user_message.uuid), "user",
                        content_length=len(message_data.content))
    
    # Get agent and run it to generate a response
    agent_model = await get_agent_by_id(db, chat_session.agent_id)
    if not agent_model:
        log_chat_error("agent_not_found", "Agent not found", "create_chat_message",
                     session_uuid=session_uuid, agent_id=chat_session.agent_id)
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Log agent access
    log_agent_operation("accessing", str(agent_model.uuid), agent_model.name, session_uuid,
                      is_default=agent_model.is_default)
    
    # Get agent instance from our agent_manager
    agent_instance = await get_agent_instance(agent_model, db)
    if not agent_instance:
        log_chat_error("agent_init_failed", "Failed to initialize agent", "create_chat_message",
                     session_uuid=session_uuid, agent_name=agent_model.name)
        raise HTTPException(status_code=500, detail="Failed to initialize agent")
        
    message_history = await get_messages_as_model_messages(db, chat_session.id)
    log_message_batch("history_loaded", session_uuid, len(message_history))
    
    # Timed operation context manager for agent processing
    async with timed_operation("agent_processing", session_uuid, 
                              agent_name=agent_model.name,
                              message_history_length=len(message_history)):
        async with agent_instance.run_mcp_servers():
            # Run the agent with the user prompt and chat history
            result = await agent_instance.run(
                message_data.content,
                message_history=message_history
            )
            
            # Add the new messages to the database
            await add_model_messages(db, chat_session.id, result.new_messages_json())
    
    # Get the last message which should be the model's response
    messages = await get_chat_session_messages(db, chat_session.id)
    if messages and messages[-1].role == "model":
        # Log the model's response
        log_message_operation("created", session_uuid, str(messages[-1].uuid), "model",
                            content_length=len(messages[-1].content))
        
        # Convert to proper response model with UUID
        response_data = {
            "uuid": messages[-1].uuid,
            "id": messages[-1].uuid,
            "role": messages[-1].role,
            "content": messages[-1].content,
            "timestamp": messages[-1].timestamp
        }
        return MessageResponse.model_validate(response_data)
    
    # Fallback to user message if something went wrong
    log_chat_error("no_model_response", "No model response generated", "create_chat_message",
                 session_uuid=session_uuid, message_uuid=str(user_message.uuid))
    
    response_data = {
        "uuid": user_message.uuid,
        "id": user_message.uuid,
        "role": user_message.role,
        "content": user_message.content,
        "timestamp": user_message.timestamp
    }
    return MessageResponse.model_validate(response_data)


@router.post("/chat/sessions/{session_uuid}/messages/stream")
@log_endpoint("stream_chat_message")
async def stream_chat_message(
    session_uuid: str,
    message_data: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new chat message and stream the agent's response"""
    # Get current request ID for correlation
    from app.core.logging import get_request_id
    request_id = get_request_id()
    logger.info_data("Stream chat message request started", {
        "session_uuid": session_uuid,
        "user_id": current_user.id,
        "content_length": len(message_data.content),
        "request_id": request_id
    })
    
    # Special debugging condition - clear agent cache if MAX_DEBUG is enabled
    # This ensures the agent is fresh for each request when debugging
    if os.getenv("MAX_DEBUG", "false").lower() in ("true", "1", "yes"):
        logger.info_data("MAX_DEBUG enabled: Resetting agent cache", {"session_uuid": session_uuid})
        await reset_agent_cache()
    
    async def stream_response():
        # This function handles the actual streaming and will be called by FastAPI
        # We need comprehensive error handling here
        user_message = None
        model_message = None
        agent_model = None
        chat_session = None
        debug_step = "initializing"  # Track the step we're on for detailed error reporting
        
        try:
            # Step 1: Get the chat session - DB Operation
            debug_step = "getting chat session"
            chat_session = await get_chat_session_by_uuid(db, session_uuid)
            if not chat_session:
                logger.warning_data("Chat session not found", {
                    "session_uuid": session_uuid,
                    "request_id": request_id
                })
                yield json.dumps({
                    "role": "model",
                    "content": "Error: Chat session not found",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "error": True,
                    "id": "error"
                }).encode("utf-8") + b"\n"
                return
            
            # Step 2: Verify ownership - Authorization Check
            debug_step = "verifying authorization"
            if chat_session.user_id != current_user.id:
                logger.warning_data("Unauthorized access to chat session", {
                    "session_uuid": session_uuid,
                    "session_owner": chat_session.user_id,
                    "requester": current_user.id,
                    "request_id": request_id
                })
                yield json.dumps({
                    "role": "model",
                    "content": "Error: Not authorized to access this chat session",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "error": True,
                    "id": "error"
                }).encode("utf-8") + b"\n"
                return
            
            # Step 3: Create user message - DB Operation
            debug_step = "creating user message"
            user_message = await create_message(
                db=db,
                chat_session_id=chat_session.id,
                role="user",
                content=message_data.content
            )
            
            logger.info_data("User message created", {
                "message_uuid": str(user_message.uuid),
                "session_uuid": session_uuid,
                "content_length": len(message_data.content),
                "request_id": request_id
            })
            
            # Stream the user message first for immediate display
            yield json.dumps({
                "role": "user",
                "content": message_data.content,
                "timestamp": user_message.timestamp.isoformat(),
                "id": str(user_message.uuid)
            }).encode("utf-8") + b"\n"
            
            # Step 4: Get the agent - DB Operation
            debug_step = "retrieving agent model"
            agent_model = await get_agent_by_id(db, chat_session.agent_id)
            if not agent_model:
                error_msg = "Agent not found for this chat session"
                logger.error_data("Agent not found", {
                    "session_uuid": session_uuid,
                    "agent_id": chat_session.agent_id,
                    "request_id": request_id
                })
                yield json.dumps({
                    "role": "model",
                    "content": f"Error: {error_msg}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "error": True,
                    "id": "error"
                }).encode("utf-8") + b"\n"
                return
            
            # Step 5: Get agent instance - Agent Operation
            debug_step = "initializing agent instance"
            agent_instance = await get_agent_instance(agent_model, db)
            if not agent_instance:
                error_msg = "Failed to initialize agent"
                logger.error_data("Failed to initialize agent", {
                    "agent_id": chat_session.agent_id,
                    "agent_name": agent_model.name,
                    "request_id": request_id
                })
                yield json.dumps({
                    "role": "model",
                    "content": f"Error: {error_msg}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "error": True,
                    "id": "error"  
                }).encode("utf-8") + b"\n"
                return
            
            # Step 6: Get message history - DB Operation
            debug_step = "retrieving message history"
            message_history = await get_messages_as_model_messages(db, chat_session.id)
            
            # Debug: Log message history details to help identify issues
            if os.getenv("MAX_DEBUG", "false").lower() in ("true", "1", "yes"):
                msg_info = []
                for idx, msg in enumerate(message_history):
                    msg_content = getattr(msg, 'content', '[No content attribute]')
                    if isinstance(msg_content, str) and len(msg_content) > 50:
                        msg_content = msg_content[:50] + "..."
                    msg_info.append({
                        "index": idx,
                        "role": getattr(msg, 'role', 'unknown'),
                        "content_preview": msg_content
                    })
                
                logger.info_data("Message history details", {
                    "session_uuid": session_uuid,
                    "history_count": len(message_history),
                    "message_details": msg_info,
                    "request_id": request_id
                })
            else:
                logger.info_data("Retrieved message history", {
                    "session_uuid": session_uuid,
                    "message_count": len(message_history),
                    "request_id": request_id
                })
            
            # Step 7: Create model message record (empty initially)
            debug_step = "creating model message"
            model_message = await create_message(
                db=db,
                chat_session_id=chat_session.id,
                role="model",
                content=""  # Start with empty content, will update as we stream
            )
            
            logger.info_data("Empty model message created", {
                "message_uuid": str(model_message.uuid),
                "session_uuid": session_uuid,
                "request_id": request_id
            })

            # Step 8: Process with agent - Primary Agent Operation
            debug_step = "running agent processing"
            complete_response = ""
            chunk_count = 0
            
            try:
                # Start the MCP servers
                debug_step = "starting MCP servers"
                async with agent_instance.run_mcp_servers():
                    # Log the start of agent processing
                    logger.info_data("Starting agent processing", {
                        "agent_name": agent_model.name,
                        "session_uuid": session_uuid,
                        "history_length": len(message_history),
                        "request_id": request_id
                    })
                    
                    # Stream the agent's response
                    debug_step = "streaming agent response"
                    start_time = time.time()
                    
                    async with agent_instance.run_stream(message_data.content, message_history=message_history) as result:
                        # Stream chunks of the response
                        async for text in result.stream(debounce_by=0.01):
                            debug_step = "processing response chunk"
                            complete_response += text
                            chunk_count += 1
                            
                            # Log streaming progress (at debug level to avoid too many logs)
                            log_streaming_progress(session_uuid, str(model_message.uuid), 
                                              chunk_count, len(complete_response))
                            
                            # Send a response chunk with the accumulated text so far
                            yield json.dumps({
                                "role": "model",
                                "content": complete_response,
                                "timestamp": model_message.timestamp.isoformat(),
                                "id": str(model_message.uuid)
                            }).encode("utf-8") + b"\n"
                    
                    # Step 9: Update the model message with the complete content
                    debug_step = "updating model message"
                    if model_message and complete_response:
                        try:
                            updated_message = await update_message(
                                db, 
                                model_message.id, 
                                content=complete_response
                            )
                            if not updated_message:
                                logger.warning_data("Failed to update message, not found", {
                                    "message_id": model_message.id,
                                    "session_uuid": session_uuid
                                })
                        except Exception as update_error:
                            # If updating fails, log but continue
                            logger.error_data("Error updating message content", {
                                "error": str(update_error),
                                "message_id": model_message.id,
                                "session_uuid": session_uuid
                            }, exc_info=True)
                        
                        elapsed_time = time.time() - start_time
                        logger.info_data("Agent processing completed", {
                            "elapsed_seconds": round(elapsed_time, 2),
                            "chunk_count": chunk_count,
                            "response_length": len(complete_response),
                            "message_uuid": str(model_message.uuid),
                            "session_uuid": session_uuid,
                            "request_id": request_id
                        })
                    
                    # Step 10: Add messages to history - DB Operation
                    debug_step = "saving messages to history"
                    await add_model_messages(db, chat_session.id, result.new_messages_json())
                    
            except Exception as e:
                # Detailed logging of MCP/agent error
                logger.error_data("Error during agent processing", {
                    "debug_step": debug_step,
                    "agent_name": agent_model.name if agent_model else "unknown",
                    "error_type": type(e).__name__,
                    "error": str(e),
                    "session_uuid": session_uuid, 
                    "request_id": request_id
                }, exc_info=True)
                
                # Return error to frontend
                error_message = f"Error during agent processing: {str(e)}"
                
                # Create an error message in the database
                error_msg = await create_message(
                    db=db,
                    chat_session_id=chat_session.id,
                    role="model",
                    content=error_message
                )
                
                # Stream the error to the client
                yield json.dumps({
                    "role": "model",
                    "content": error_message,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "error": True,
                    "id": str(error_msg.uuid)
                }).encode("utf-8") + b"\n"
                
        except Exception as e:
            # This is the top-level exception handler for any unexpected errors
            error_message = f"Error processing request: {str(e)}"
            logger.error_data("Unhandled exception in stream_chat_message", {
                "debug_step": debug_step,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "session_uuid": session_uuid,
                "user_id": current_user.id,
                "request_id": request_id
            }, exc_info=True)
            
            # Try to create an error message in the database if we have a chat session
            try:
                if chat_session:
                    error_msg = await create_message(
                        db=db,
                        chat_session_id=chat_session.id,
                        role="model",
                        content=error_message
                    )
                    error_id = str(error_msg.uuid)
                else:
                    error_id = "system-error"
            except Exception:
                error_id = "system-error"
                
            # Always try to return something useful to the client
            yield json.dumps({
                "role": "model",
                "content": f"Error: {error_message}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": True,
                "debug_step": debug_step,  # Include the step where failure occurred
                "id": error_id
            }).encode("utf-8") + b"\n"
    
    return StreamingResponse(stream_response(), media_type="text/plain")


# Add a debug endpoint to reset agent cache
@router.post("/chat/reset-agent-cache")
@log_endpoint("reset_agent_cache")
async def api_reset_agent_cache(
    agent_uuid: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Reset the agent cache for a specific agent or all agents"""
    await reset_agent_cache(agent_uuid)
    return {"success": True, "message": "Agent cache reset successfully"}
