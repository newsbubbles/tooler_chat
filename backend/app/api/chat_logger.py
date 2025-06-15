# This file contains logging enhancement functions for chat.py
# Import these at the top of chat.py

import time
from typing import Dict, Any, Optional
from uuid import UUID
from contextlib import asynccontextmanager

from app.core.logging import get_logger

# Create a dedicated logger for chat operations
chat_logger = get_logger("app.api.chat")


def log_chat_session_operation(operation: str, session_uuid: str, user_id: int, **kwargs):
    """Log a chat session operation with contextual information"""
    chat_logger.info_data(f"Chat session {operation}", {
        "operation": operation,
        "session_uuid": session_uuid,
        "user_id": user_id,
        **kwargs
    })


def log_message_operation(operation: str, session_uuid: str, message_uuid: str, role: str, **kwargs):
    """Log a message operation with contextual information"""
    chat_logger.info_data(f"Message {operation}", {
        "operation": operation,
        "session_uuid": session_uuid,
        "message_uuid": message_uuid,
        "role": role,
        **kwargs
    })


def log_agent_operation(operation: str, agent_uuid: str, agent_name: str, session_uuid: str, **kwargs):
    """Log an agent operation with contextual information"""
    chat_logger.info_data(f"Agent {operation}", {
        "operation": operation,
        "agent_uuid": agent_uuid,
        "agent_name": agent_name,
        "session_uuid": session_uuid,
        **kwargs
    })


def log_chat_error(error_type: str, error_message: str, debug_step: str, session_uuid: Optional[str] = None, **kwargs):
    """Log a chat error with detailed context"""
    chat_logger.error_data(f"Chat error: {error_type}", {
        "error_type": error_type,
        "error_message": error_message,
        "debug_step": debug_step,
        "session_uuid": session_uuid,
        **kwargs
    }, exc_info=True) # Include stack trace


@asynccontextmanager
async def timed_operation(operation_name: str, session_uuid: Optional[str] = None, **context):
    """Context manager to time and log operations"""
    start_time = time.time()
    chat_logger.info_data(f"Starting: {operation_name}", {
        "operation": operation_name,
        "session_uuid": session_uuid,
        **context
    })
    
    try:
        yield
        
        elapsed_time = time.time() - start_time
        chat_logger.info_data(f"Completed: {operation_name}", {
            "operation": operation_name,
            "session_uuid": session_uuid,
            "elapsed_seconds": round(elapsed_time, 3),
            **context
        })
        
    except Exception as e:
        elapsed_time = time.time() - start_time
        chat_logger.error_data(f"Failed: {operation_name}", {
            "operation": operation_name,
            "session_uuid": session_uuid,
            "elapsed_seconds": round(elapsed_time, 3),
            "error": str(e),
            "error_type": type(e).__name__,
            **context
        }, exc_info=True)
        raise


def log_message_batch(operation: str, session_uuid: str, message_count: int, **kwargs):
    """Log information about batch message operations"""
    chat_logger.info_data(f"Message batch {operation}", {
        "operation": operation,
        "session_uuid": session_uuid,
        "message_count": message_count,
        **kwargs
    })


def log_streaming_progress(session_uuid: str, message_uuid: str, chunk_number: int, total_length: int, **kwargs):
    """Log progress of streaming operations at debug level"""
    if chunk_number % 10 == 0 or chunk_number <= 5:  # Log every 10th chunk to avoid excessive logs
        chat_logger.debug_data(f"Streaming chunk {chunk_number}", {
            "session_uuid": session_uuid,
            "message_uuid": message_uuid,
            "chunk_number": chunk_number,
            "total_content_length": total_length,
            **kwargs
        })