# Copy this code into your chat.py file, replacing the existing stream_chat_message function

@router.post("/chat/sessions/{session_uuid}/messages/stream")
@log_endpoint("stream_chat_message")
async def stream_chat_message(
    session_uuid: str,
    message_data: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new chat message and stream the agent's response"""
    request_id = None
    if hasattr(logger, 'info_data'):
        # Get current request ID for correlation
        from app.core.logging import get_request_id
        request_id = get_request_id()
        logger.info_data("Stream chat message request started", {
            "session_uuid": session_uuid,
            "user_id": current_user.id,
            "content_length": len(message_data.content),
            "request_id": request_id
        })
    else:
        logger.info(f"Chat message streaming started for session {session_uuid}")
    
    async def stream_response():
        # This function handles the actual streaming and will be called by FastAPI
        # We need comprehensive error handling here
        user_message = None
        model_message = None
        agent_model = None
        chat_session = None
        
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
                        updated_message = await update_message(
                            db, 
                            model_message.id, 
                            content=complete_response
                        )
                        
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


# Make sure to add this helper function to update message content:
async def update_message(db: AsyncSession, message_id: int, content: str):
    """Update a message's content"""
    stmt = (
        update(Message)
        .where(Message.id == message_id)
        .values(content=content)
        .returning(Message)
    )
    result = await db.execute(stmt)
    await db.commit()
    return result.scalar_one()
