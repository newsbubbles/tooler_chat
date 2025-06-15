import time
from uuid import uuid4
from fastapi import Request, Response
from fastapi.routing import APIRoute
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from typing import Callable, Dict, Any, Union
import json
import asyncio

from .config import get_logger, set_request_id

logger = get_logger("app.api.middleware")

# Maximum content length to log (to avoid massive logs)
MAX_CONTENT_LENGTH = 10000  # 10KB

class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses"""

    async def dispatch(self, request: Request, call_next):
        # Generate a unique ID for this request
        request_id = str(uuid4())
        set_request_id(request_id)
        
        # Start timer
        start_time = time.time()
        
        try:
            # Read request body (we need to do this for logging but then restore it for processing)
            request_body = await self._get_request_body(request)
            
            # Collect request information
            method = request.method
            path = request.url.path
            query_params = dict(request.query_params)
            client_host = request.client.host if request.client else "unknown"
            user_agent = request.headers.get("user-agent", "unknown")
            content_type = request.headers.get("content-type", "unknown")
            authorization = "[REDACTED]" if "authorization" in request.headers else None
            
            # Get all headers (redacting sensitive ones)
            headers = {}
            for key, value in request.headers.items():
                if key.lower() in ("authorization", "cookie", "x-api-key"):
                    headers[key] = "[REDACTED]"
                else:
                    headers[key] = value
            
            # Try to parse request body if it's JSON
            parsed_body = None
            try:
                if request_body and content_type and "application/json" in content_type:
                    try:
                        parsed_body = json.loads(request_body)
                        # Redact sensitive fields
                        parsed_body = self._sanitize_data(parsed_body)
                    except Exception as e:
                        parsed_body = {"_note": f"Could not parse JSON body: {str(e)}", 
                                     "_raw": request_body[:MAX_CONTENT_LENGTH] if len(request_body) > MAX_CONTENT_LENGTH else request_body}
                elif request_body:
                    # For non-JSON bodies, include a truncated version
                    if len(request_body) > MAX_CONTENT_LENGTH:
                        parsed_body = {"_note": f"Non-JSON body (truncated, {len(request_body)} bytes total)", 
                                     "_raw": request_body[:MAX_CONTENT_LENGTH]}
                    else:
                        parsed_body = {"_note": "Non-JSON body", "_raw": request_body}
            except Exception as e:
                logger.warning(f"Error processing request body: {str(e)}")
                parsed_body = {"_note": f"Error processing body: {str(e)}"}
            
            # Log request
            if hasattr(logger, 'info_data'):
                logger.info_data(
                    f"{method} {path} - Request started",
                    {
                        "request": {
                            "method": method,
                            "path": path,
                            "query_params": query_params,
                            "client_host": client_host,
                            "user_agent": user_agent,
                            "content_type": content_type,
                            "headers": headers,
                            "body": parsed_body,
                            "has_authorization": authorization is not None
                        },
                        "request_id": request_id
                    }
                )
            else:
                # Fallback if enhanced logging isn't available
                logger.info(f"{method} {path} - Request started - client: {client_host} - id: {request_id}")
        except Exception as e:
            # Fallback if request logging fails
            logger.warning(f"Request logging error: {str(e)}")
        
        # Process the request and get response
        response = None
        try:
            response = await call_next(request)
            status_code = response.status_code
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            try:
                # Get response body for logging
                response_body = await self._get_response_body(response)
                
                # Try to parse response body if it's JSON
                parsed_response = None
                resp_content_type = response.headers.get("content-type", "")
                if response_body and resp_content_type and "application/json" in resp_content_type:
                    try:
                        parsed_response = json.loads(response_body)
                        # Redact sensitive fields
                        parsed_response = self._sanitize_data(parsed_response)
                    except Exception:
                        # Non-parseable JSON
                        parsed_response = {"_note": "Could not parse JSON response", "_raw": response_body[:MAX_CONTENT_LENGTH]}
                elif response_body:
                    # For non-JSON bodies, include a truncated version if it's text
                    if any(text_type in resp_content_type for text_type in ["text/", "application/xml", "application/html"]):
                        if len(response_body) > MAX_CONTENT_LENGTH:
                            parsed_response = {"_note": f"Text response (truncated, {len(response_body)} bytes total)",
                                             "_raw": response_body[:MAX_CONTENT_LENGTH]}
                        else:
                            parsed_response = {"_note": "Text response", "_raw": response_body}
                    else:
                        # Binary content - just note the size
                        parsed_response = {"_note": f"Binary response, {len(response_body)} bytes"}
                
                # Get response headers (redacting sensitive ones)
                resp_headers = {}
                for key, value in response.headers.items():
                    if key.lower() in ("set-cookie", "authorization"):
                        resp_headers[key] = "[REDACTED]"
                    else:
                        resp_headers[key] = value
                
                # Log response
                log_level = "warning" if status_code >= 400 else "info"
                if hasattr(logger, f"{log_level}_data"):
                    getattr(logger, f"{log_level}_data")(
                        f"{method} {path} - {status_code} - {process_time:.3f}s",
                        {
                            "response": {
                                "status_code": status_code,
                                "process_time_ms": round(process_time * 1000),
                                "headers": resp_headers,
                                "content_type": resp_content_type,
                                "body": parsed_response,
                                "size_bytes": len(response_body) if response_body else 0
                            },
                            "request": {
                                "method": method,
                                "path": path,
                                "query_params": query_params,
                            },
                            "request_id": request_id
                        }
                    )
                else:
                    # Fallback if enhanced logging isn't available
                    getattr(logger, log_level)(f"{method} {path} - {status_code} - {process_time:.3f}s - id: {request_id}")
            except Exception as e:
                # Fallback if response logging fails
                logger.warning(f"Response logging error: {str(e)}")
            
            # Add request ID to response headers
            try:
                response.headers["X-Request-ID"] = request_id
            except Exception:
                pass  # If we can't add the header, just continue
            
            return response
            
        except Exception as e:
            # Calculate processing time for error case
            process_time = time.time() - start_time
            
            # Log the error
            if hasattr(logger, 'error_data'):
                logger.error_data(
                    f"{method} {path} - Exception",
                    {
                        "error": {
                            "type": type(e).__name__,
                            "message": str(e),
                            "process_time_ms": round(process_time * 1000),
                            "traceback": self._format_traceback(e)
                        },
                        "request": {
                            "method": method,
                            "path": path,
                            "query_params": query_params,
                            "body": parsed_body if 'parsed_body' in locals() else None
                        },
                        "request_id": request_id
                    },
                    exc_info=True
                )
            else:
                # Fallback if enhanced logging isn't available
                logger.error(f"{method} {path} - Exception: {str(e)} - id: {request_id}", exc_info=True)
            
            # Re-raise the exception
            raise
    
    def _sanitize_data(self, data: Any) -> Any:
        """Sanitize data for logging to avoid sensitive information"""
        try:
            # Import the utils function if available
            try:
                from .utils import sanitize_data
                return sanitize_data(data)
            except ImportError:
                # Implement simple sanitization
                if isinstance(data, dict):
                    sanitized = {}
                    for key, value in data.items():
                        # Skip sensitive keys
                        if key.lower() in (
                            "password", "token", "secret", "authorization", 
                            "api_key", "key", "credential", "hashed_password"
                        ):
                            sanitized[key] = "[REDACTED]"
                        else:
                            sanitized[key] = self._sanitize_data(value)
                    return sanitized
                elif isinstance(data, list):
                    return [self._sanitize_data(item) for item in data]
                else:
                    return data
        except Exception as e:
            return f"[Error sanitizing data: {str(e)}]"
    
    async def _get_request_body(self, request: Request) -> str:
        """Get the request body as a string"""
        try:
            body = b""
            
            # Check if the request has a body
            if hasattr(request, "_body"):
                body = request._body
            elif request.method in ["POST", "PUT", "PATCH"]:
                try:
                    # Save original receive function
                    receive = request.receive
                    
                    async def receive_with_store():
                        nonlocal body
                        message = await receive()
                        if message["type"] == "http.request":
                            chunk = message.get("body", b"")
                            if chunk:
                                body += chunk
                        return message
                    
                    # Replace receive function
                    request.receive = receive_with_store
                    
                    # Read body
                    body_chunk = await request.body()
                    body = body_chunk
                except Exception as e:
                    logger.warning(f"Error reading request body: {str(e)}")
            
            try:
                return body.decode("utf-8")
            except UnicodeDecodeError:
                return str(body)
        except Exception as e:
            logger.warning(f"Could not get request body: {str(e)}")
            return "[Error getting request body]"
    
    async def _get_response_body(self, response: Response) -> str:
        """Get the response body as a string"""
        try:
            # We need to create a copy of the response to read the body
            # without affecting the original response
            
            original_body = b""
            
            # Only try to read body for specific content types
            content_type = response.headers.get("content-type", "").lower()
            if any(ct in content_type for ct in ["json", "text", "xml", "html"]):
                try:
                    # Some responses may have a `body` attribute directly
                    if hasattr(response, "body"):
                        original_body = response.body
                    # StreamingResponse has no body attribute
                    elif hasattr(response, "body_iterator"):
                        # For StreamingResponse we need to be careful not to consume the iterator
                        # This is a hack - we get the first chunk only
                        if asyncio.iscoroutinefunction(response.body_iterator.__anext__):
                            try:
                                # Get the first chunk only
                                chunk = await asyncio.wait_for(response.body_iterator.__anext__(), 0.1)
                                original_body = chunk[:MAX_CONTENT_LENGTH]
                                original_body += b"... [stream truncated for logging]"
                            except Exception:
                                original_body = b"[streaming content - not logged]"
                        else:
                            original_body = b"[streaming content - not logged]" 
                except Exception as e:
                    logger.warning(f"Error reading response body: {str(e)}")
                    original_body = f"[Error reading response: {str(e)}]".encode()
            else:
                original_body = b"[binary or unhandled content type - not logged]"
            
            try:
                return original_body.decode("utf-8")
            except UnicodeDecodeError:
                return str(original_body)
        except Exception as e:
            logger.warning(f"Could not get response body: {str(e)}")
            return "[Error getting response body]"
    
    def _format_traceback(self, exc: Exception) -> list:
        """Format a traceback into a structured list"""
        try:
            import traceback
            tb = traceback.extract_tb(exc.__traceback__)
            return [{
                "filename": frame.filename,
                "line": frame.lineno,
                "name": frame.name,
                "code": frame.line
            } for frame in tb]
        except Exception as e:
            return [{"error": f"Error formatting traceback: {str(e)}"}]