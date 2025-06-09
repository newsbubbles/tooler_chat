from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List, Dict, Any
import json
from datetime import datetime, timezone
from uuid import UUID

from app.db.database import get_db
from app.core.auth import get_current_active_user
from app.models.base import User
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
import os
import asyncio
import tempfile
from uuid import UUID

router = APIRouter(tags=["chat"])

# Configure API keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")


async def get_agent_instance(agent_uuid: str, db: AsyncSession):
    """Get a configured Agent instance with associated MCP servers"""
    # Get the agent from the database
    agent_db = await get_agent_by_uuid(db, agent_uuid)
    if not agent_db:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Get associated MCP servers
    mcp_servers_db = await get_agent_mcp_servers(db, agent_db.id)
    mcp_servers = []
    
    # Prepare environment variables for MCP servers
    # In a production system, these would be securely stored and retrieved
    env = {
        "OPENAI_API_KEY": OPENAI_API_KEY,
        "OPENROUTER_API_KEY": OPENROUTER_API_KEY,
        # Add other necessary API keys from environment or secure storage
    }
    
    # Configure MCP servers
    for mcp_server_db in mcp_servers_db:
        # Create a temporary file with the MCP server code
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as temp_file:
            temp_file.write(mcp_server_db.code)
            mcp_server_path = temp_file.name
        
        # Create MCPServerStdio instance with environment variables
        mcp_server = MCPServerStdio('python', [mcp_server_path], env=env)
        mcp_servers.append(mcp_server)
    
    # Configure the model - using OpenRouter for access to various models
    default_model = "anthropic/claude-3.7-sonnet"  # Default model, could be configurable per agent
    
    # Use OpenAI provider with OpenRouter base URL if OPENROUTER_API_KEY is available
    # Otherwise fall back to regular OpenAI
    if OPENROUTER_API_KEY:
        provider = OpenAIProvider(
            base_url='https://openrouter.ai/api/v1',
            api_key=OPENROUTER_API_KEY
        )
    else:
        provider = OpenAIProvider(api_key=OPENAI_API_KEY)
    
    # Create the model with appropriate configuration
    model = OpenAIModel(
        default_model,
        provider=provider
    )
    
    # Create the agent with the system prompt from the database
    agent_instance = Agent(
        model,
        mcp_servers=mcp_servers,
        system_prompt=agent_db.system_prompt
    )
    
    return agent_instance


@router.post("/chat/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
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
        raise HTTPException(status_code=404, detail="Agent not found")
    
    if not agent.is_default and agent.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to use this agent")
    
    # Create chat session
    chat_session = await create_chat_session(
        db=db,
        user_id=current_user.id,
        agent_id=agent.id,
        title=session_data.title
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
            raise HTTPException(status_code=404, detail="Agent not found")
        
        if not agent.is_default and agent.user_id != current_user.id:
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
async def get_chat_session(
    session_uuid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific chat session by UUID with its messages"""
    chat_session = await get_chat_session_by_uuid(db, session_uuid)
    if not chat_session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    # Verify ownership
    if chat_session.user_id != current_user.id:
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
    
    return ChatSessionDetailResponse.model_validate(session_data)


@router.put("/chat/sessions/{session_uuid}", response_model=ChatSessionResponse)
async def update_existing_chat_session(
    session_uuid: str,
    session_data: ChatSessionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update an existing chat session"""
    chat_session = await get_chat_session_by_uuid(db, session_uuid)
    if not chat_session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    # Verify ownership
    if chat_session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this chat session")
    
    # Perform the update
    update_data = session_data.model_dump(exclude_unset=True)
    updated_chat_session = await update_chat_session(db, chat_session.id, **update_data)
    
    # Get agent to get its UUID
    agent = await get_agent_by_id(db, updated_chat_session.agent_id)
    agent_uuid_str = agent.uuid if agent else None
    
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
async def delete_existing_chat_session(
    session_uuid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a chat session"""
    chat_session = await get_chat_session_by_uuid(db, session_uuid)
    if not chat_session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    # Verify ownership
    if chat_session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this chat session")
    
    result = await delete_chat_session(db, chat_session.id)
    if not result:
        raise HTTPException(status_code=500, detail="Failed to delete chat session")


@router.post("/chat/sessions/{session_uuid}/messages", response_model=MessageResponse)
async def create_chat_message(
    session_uuid: str,
    message_data: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new chat message (non-streaming)"""
    chat_session = await get_chat_session_by_uuid(db, session_uuid)
    if not chat_session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    # Verify ownership
    if chat_session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to post to this chat session")
    
    # Create user message
    user_message = await create_message(
        db=db,
        chat_session_id=chat_session.id,
        role="user",
        content=message_data.content
    )
    
    # Get agent and run it to generate a response
    agent = await get_agent_by_id(db, chat_session.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    agent_instance = await get_agent_instance(str(agent.uuid), db)
    message_history = await get_messages_as_model_messages(db, chat_session.id)
    
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
    response_data = {
        "uuid": user_message.uuid,
        "id": user_message.uuid,
        "role": user_message.role,
        "content": user_message.content,
        "timestamp": user_message.timestamp
    }
    return MessageResponse.model_validate(response_data)


@router.post("/chat/sessions/{session_uuid}/messages/stream")
async def stream_chat_message(
    session_uuid: str,
    message_data: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new chat message and stream the agent's response"""
    chat_session = await get_chat_session_by_uuid(db, session_uuid)
    if not chat_session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    # Verify ownership
    if chat_session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to post to this chat session")
    
    # Create user message
    user_message = await create_message(
        db=db,
        chat_session_id=chat_session.id,
        role="user",
        content=message_data.content
    )
    
    async def stream_response():
        # Stream the user message first for immediate display
        yield json.dumps({
            "role": "user",
            "content": message_data.content,
            "timestamp": user_message.timestamp.isoformat(),
            "id": str(user_message.uuid)  # UUID as string
        }).encode("utf-8") + b"\n"
        
        # Get agent and message history
        agent = await get_agent_by_id(db, chat_session.agent_id)
        if not agent:
            error_msg = "Agent not found"
            yield json.dumps({
                "role": "model",
                "content": error_msg,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": True,
                "id": "error"  # Special ID for errors
            }).encode("utf-8") + b"\n"
            return
            
        agent_instance = await get_agent_instance(str(agent.uuid), db)
        message_history = await get_messages_as_model_messages(db, chat_session.id)
        model_message = None
        
        try:
            async with agent_instance.run_mcp_servers():
                # Stream the agent's response
                async with agent_instance.run_stream(message_data.content, message_history=message_history) as result:
                    # Create a message record for the model's response
                    model_message = await create_message(
                        db=db,
                        chat_session_id=chat_session.id,
                        role="model",
                        content=""  # Start with empty content, will update as we stream
                    )
                    
                    # Initialize a buffer to collect the complete response
                    complete_response = ""
                    
                    # Stream chunks of the response
                    async for text in result.stream(debounce_by=0.01):
                        complete_response += text
                        # Send a response chunk with the accumulated text so far
                        yield json.dumps({
                            "role": "model",
                            "content": complete_response,
                            "timestamp": model_message.timestamp.isoformat(),
                            "id": str(model_message.uuid)  # UUID as string
                        }).encode("utf-8") + b"\n"
                    
                    # Update the model message with the complete response
                    if model_message and complete_response:
                        model_message = await update_chat_session(
                            db, 
                            model_message.id, 
                            content=complete_response
                        )
                        
                    # Add the complete interaction to the message history
                    await add_model_messages(db, chat_session.id, result.new_messages_json())
        
        except Exception as e:
            # Send error message if something goes wrong
            error_message = f"Error processing request: {str(e)}"
            
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
                "id": str(error_msg.uuid)  # UUID as string
            }).encode("utf-8") + b"\n"
    
    return StreamingResponse(stream_response(), media_type="text/plain")