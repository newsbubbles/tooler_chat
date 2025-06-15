# This is a partial update showing how to apply the logging decorators
# to the existing chat.py endpoints. Copy these decorated functions into
# the actual chat.py file.

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List, Dict, Any

from app.db.database import get_db
from app.core.auth import get_current_active_user
from app.core.logging import get_logger
from app.core.logging.decorators import log_endpoint

logger = get_logger("app.api.chat")

# Example of how to apply the log_endpoint decorator to an API endpoint
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
        logger.warning_data("Agent not found", {"agent_uuid": agent_uuid})
        raise HTTPException(status_code=404, detail="Agent not found")
    
    if not agent.is_default and agent.user_id != current_user.id:
        logger.warning_data("Unauthorized access attempt", {
            "user_id": current_user.id, 
            "agent_id": agent.id,
            "agent_owner": agent.user_id
        })
        raise HTTPException(status_code=403, detail="Not authorized to use this agent")
    
    # Create chat session
    chat_session = await create_chat_session(
        db=db,
        user_id=current_user.id,
        agent_id=agent.id,
        title=session_data.title
    )
    
    logger.info_data("Chat session created", {
        "session_id": str(chat_session.uuid),
        "user_id": current_user.id,
        "agent_id": agent.id,
        "title": chat_session.title
    })
    
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


@router.post("/chat/sessions/{session_uuid}/messages/stream")
@log_endpoint("stream_chat_message")
async def stream_chat_message(
    session_uuid: str,
    message_data: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new chat message and stream the agent's response"""
    logger.info_data("Stream chat message request", {
        "session_uuid": session_uuid,
        "user_id": current_user.id
    })
    
    chat_session = await get_chat_session_by_uuid(db, session_uuid)
    if not chat_session:
        logger.warning_data("Chat session not found", {"session_uuid": session_uuid})
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    # Verify ownership
    if chat_session.user_id != current_user.id:
        logger.warning_data("Unauthorized access to chat session", {
            "session_uuid": session_uuid,
            "session_owner": chat_session.user_id,
            "requester": current_user.id
        })
        raise HTTPException(status_code=403, detail="Not authorized to post to this chat session")
    
    # Create user message
    user_message = await create_message(
        db=db,
        chat_session_id=chat_session.id,
        role="user",
        content=message_data.content
    )
    
    logger.info_data("User message created", {
        "message_uuid": str(user_message.uuid),
        "session_uuid": session_uuid,
        "content_length": len(message_data.content)
    })
    
    async def stream_response():
        # Stream the user message first for immediate display
        yield json.dumps({
            "role": "user",
            "content": message_data.content,
            "timestamp": user_message.timestamp.isoformat(),
            "id": str(user_message.uuid)  # UUID as string
        }).encode("utf-8") + b"\n"
        
        # Get agent and message history
        agent_model = await get_agent_by_id(db, chat_session.agent_id)
        if not agent_model:
            error_msg = "Agent not found"
            logger.error_data("Agent not found for chat session", {
                "session_uuid": session_uuid,
                "agent_id": chat_session.agent_id
            })
            yield json.dumps({
                "role": "model",
                "content": error_msg,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": True,
                "id": "error"  # Special ID for errors
            }).encode("utf-8") + b"\n"
            return
        
        # Get agent instance from our agent_manager    
        agent_instance = await get_agent_instance(agent_model, db)
        if not agent_instance:
            error_msg = "Failed to initialize agent"
            logger.error_data("Failed to initialize agent", {
                "agent_id": chat_session.agent_id,
                "agent_name": agent_model.name
            })
            yield json.dumps({
                "role": "model",
                "content": error_msg,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": True,
                "id": "error"  # Special ID for errors
            }).encode("utf-8") + b"\n"
            return
            
        message_history = await get_messages_as_model_messages(db, chat_session.id)
        model_message = None
        
        try:
            with logger.catch_exceptions("Agent processing"):  # Custom error handling
                async with agent_instance.run_mcp_servers():
                    # Stream the agent's response
                    start_time = time.time()
                    logger.info_data("Starting agent processing", {
                        "agent_name": agent_model.name,
                        "session_uuid": session_uuid,
                        "history_length": len(message_history)
                    })
                    
                    async with agent_instance.run_stream(message_data.content, message_history=message_history) as result:
                        # Create a message record for the model's response
                        model_message = await create_message(
                            db=db,
                            chat_session_id=chat_session.id,
                            role="model",
                            content=""  # Start with empty content, will update as we stream
                        )
                        
                        logger.info_data("Model message created", {
                            "message_uuid": str(model_message.uuid),
                            "session_uuid": session_uuid
                        })
                        
                        # Initialize a buffer to collect the complete response
                        complete_response = ""
                        chunk_count = 0
                        
                        # Stream chunks of the response
                        async for text in result.stream(debounce_by=0.01):
                            complete_response += text
                            chunk_count += 1
                            
                            # Send a response chunk with the accumulated text so far
                            yield json.dumps({
                                "role": "model",
                                "content": complete_response,
                                "timestamp": model_message.timestamp.isoformat(),
                                "id": str(model_message.uuid)  # UUID as string
                            }).encode("utf-8") + b"\n"
                        
                        elapsed_time = time.time() - start_time
                        logger.info_data("Agent processing completed", {
                            "elapsed_seconds": round(elapsed_time, 2),
                            "chunk_count": chunk_count,
                            "response_length": len(complete_response),
                            "tokens_approx": len(complete_response) // 4  # Rough estimate
                        })
                        
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
            logger.error_data("Streaming error", {
                "error": str(e),
                "session_uuid": session_uuid
            }, exc_info=True)
            
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