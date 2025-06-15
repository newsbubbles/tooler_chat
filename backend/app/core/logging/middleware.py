import time
from uuid import uuid4
from fastapi import Request, Response
from fastapi.routing import APIRoute
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from typing import Callable, Dict, Any, Union
import json

from .config import get_logger, set_request_id

logger = get_logger("app.api.middleware")

class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses"""

    async def dispatch(self, request: Request, call_next):
        # Generate a unique ID for this request
        request_id = str(uuid4())
        set_request_id(request_id)
        
        # Start timer
        start_time = time.time()
        
        # Collect request information
        method = request.method
        path = request.url.path
        query_params = dict(request.query_params)
        client_host = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Log request
        logger.info_data(
            f"{method} {path} - Request started",
            {
                "request": {
                    "method": method,
                    "path": path,
                    "query_params": query_params,
                    "client_host": client_host,
                    "user_agent": user_agent
                },
                "request_id": request_id
            }
        )
        
        # Process the request and get response
        try:
            response = await call_next(request)
            status_code = response.status_code
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log response
            logger.info_data(
                f"{method} {path} - {status_code} - {process_time:.3f}s",
                {
                    "response": {
                        "status_code": status_code,
                        "process_time_ms": round(process_time * 1000)
                    },
                    "request": {
                        "method": method,
                        "path": path
                    },
                    "request_id": request_id
                }
            )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            # Calculate processing time for error case
            process_time = time.time() - start_time
            
            # Log the error
            logger.error_data(
                f"{method} {path} - Exception",
                {
                    "error": {
                        "type": type(e).__name__,
                        "message": str(e),
                        "process_time_ms": round(process_time * 1000)
                    },
                    "request": {
                        "method": method,
                        "path": path
                    },
                    "request_id": request_id
                },
                exc_info=True
            )
            
            # Re-raise the exception
            raise