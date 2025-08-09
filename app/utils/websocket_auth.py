"""
WebSocket Authentication Middleware
Handles JWT authentication for WebSocket connections.
"""

import logging
import jwt
from typing import Optional, Dict, Any, Tuple
from functools import wraps
from flask import current_app
from flask_socketio import disconnect, emit
import redis

logger = logging.getLogger(__name__)

class WebSocketAuth:
    """WebSocket authentication handler."""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """Initialize WebSocket authentication."""
        self.redis_client = redis_client
    
    def authenticate_socket(self, auth_data: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Authenticate WebSocket connection.
        
        Args:
            auth_data: Authentication data containing token
            
        Returns:
            Tuple of (success, user_data, error_message)
        """
        try:
            token = auth_data.get('token')
            if not token:
                return False, None, "No authentication token provided"
            
            # Remove 'Bearer ' prefix if present
            if token.startswith('Bearer '):
                token = token[7:]
            
            # Validate JWT token
            try:
                payload = jwt.decode(
                    token,
                    current_app.config['SECRET_KEY'],
                    algorithms=['HS256']
                )
            except jwt.ExpiredSignatureError:
                return False, None, "Token has expired"
            except jwt.InvalidTokenError:
                return False, None, "Invalid token"
            
            user_id = payload.get('user_id')
            if not user_id:
                return False, None, "Invalid token payload"
            
            # Check if session is still valid in Redis
            if self.redis_client:
                session_key = f"session:{user_id}"
                session_data = self.redis_client.get(session_key)
                if not session_data:
                    return False, None, "Session expired"
            
            # Extract user information
            user_data = {
                'user_id': user_id,
                'email': payload.get('email'),
                'name': payload.get('name'),
                'role': payload.get('role', 'user'),
                'permissions': payload.get('permissions', []),
                'session_id': payload.get('session_id')
            }
            
            return True, user_data, None
            
        except Exception as e:
            logger.error(f"WebSocket authentication error: {str(e)}")
            return False, None, "Authentication failed"
    
    def check_room_permission(self, user_data: Dict[str, Any], room_id: str, 
                             permission: str = 'read') -> bool:
        """
        Check if user has permission to access room.
        
        Args:
            user_data: User information from authentication
            room_id: Room identifier
            permission: Required permission ('read', 'write', 'admin')
            
        Returns:
            True if user has permission
        """
        try:
            # System admin has access to all rooms
            if user_data.get('role') == 'admin':
                return True
            
            # Check user permissions
            user_permissions = user_data.get('permissions', [])
            if f"room:{room_id}:{permission}" in user_permissions:
                return True
            
            # Check if user has general permission
            if permission in user_permissions:
                return True
            
            # For public chat rooms, allow read access
            if room_id.startswith('chat_') and permission == 'read':
                return True
            
            # For user's own rooms (room_id contains user_id)
            if user_data.get('user_id') in room_id:
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Permission check error: {str(e)}")
            return False
    
    def validate_origin(self, origin: str) -> bool:
        """
        Validate WebSocket connection origin.
        
        Args:
            origin: Connection origin
            
        Returns:
            True if origin is allowed
        """
        try:
            allowed_origins = current_app.config.get('CORS_ORIGINS', ['*'])
            
            # Allow all origins if '*' is configured
            if '*' in allowed_origins:
                return True
            
            # Check if origin is in allowed list
            return origin in allowed_origins
            
        except Exception as e:
            logger.error(f"Origin validation error: {str(e)}")
            return False
    
    def rate_limit_check(self, user_id: str, event_type: str) -> bool:
        """
        Check rate limits for WebSocket events.
        
        Args:
            user_id: User identifier
            event_type: Type of event
            
        Returns:
            True if within rate limits
        """
        if not self.redis_client:
            return True  # No rate limiting without Redis
        
        try:
            # Rate limit configuration
            rate_limits = {
                'connection': {'limit': 10, 'window': 60},  # 10 connections per minute
                'message': {'limit': 100, 'window': 60},    # 100 messages per minute
                'typing': {'limit': 20, 'window': 60},      # 20 typing events per minute
            }
            
            config = rate_limits.get(event_type, {'limit': 50, 'window': 60})
            
            key = f"rate_limit:{user_id}:{event_type}"
            current_count = self.redis_client.get(key)
            
            if current_count is None:
                # First request in window
                self.redis_client.setex(key, config['window'], 1)
                return True
            
            current_count = int(current_count)
            if current_count >= config['limit']:
                return False
            
            # Increment counter
            self.redis_client.incr(key)
            return True
            
        except Exception as e:
            logger.error(f"Rate limit check error: {str(e)}")
            return True  # Allow on error
    
    def log_connection(self, user_id: str, socket_id: str, event: str, 
                      metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Log WebSocket connection events.
        
        Args:
            user_id: User identifier
            socket_id: Socket identifier
            event: Event type
            metadata: Additional metadata
        """
        try:
            log_data = {
                'user_id': user_id,
                'socket_id': socket_id,
                'event': event,
                'timestamp': str(logger.handlers[0].formatter.formatTime(logger.makeRecord(
                    'websocket', logging.INFO, '', 0, '', (), None
                ))),
                'metadata': metadata or {}
            }
            
            logger.info(f"WebSocket {event}: {log_data}")
            
            # Store in Redis for audit trail if available
            if self.redis_client:
                log_key = f"ws_log:{user_id}:{socket_id}"
                self.redis_client.lpush(log_key, str(log_data))
                self.redis_client.ltrim(log_key, 0, 99)  # Keep last 100 entries
                self.redis_client.expire(log_key, 86400)  # Expire after 24 hours
                
        except Exception as e:
            logger.error(f"Connection logging error: {str(e)}")

def require_ws_auth(f):
    """
    Decorator to require authentication for WebSocket events.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # The decorated function should have access to socket session
            from flask_socketio import session as socket_session
            
            user_data = socket_session.get('user_data')
            if not user_data:
                emit('error', {
                    'message': 'Authentication required',
                    'code': 'AUTH_REQUIRED'
                })
                disconnect()
                return
            
            # Add user_data to kwargs for the handler
            kwargs['user_data'] = user_data
            return f(*args, **kwargs)
            
        except Exception as e:
            logger.error(f"WebSocket auth decorator error: {str(e)}")
            emit('error', {
                'message': 'Authentication error',
                'code': 'AUTH_ERROR'
            })
            disconnect()
    
    return decorated_function

def require_room_permission(permission: str = 'read'):
    """
    Decorator to require specific room permission.
    
    Args:
        permission: Required permission level
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                from flask_socketio import session as socket_session
                
                user_data = socket_session.get('user_data')
                room_id = kwargs.get('room_id') or (args[0] if args else None)
                
                if not user_data or not room_id:
                    emit('error', {
                        'message': 'Invalid request',
                        'code': 'INVALID_REQUEST'
                    })
                    return
                
                # Check permission
                ws_auth = WebSocketAuth()
                if not ws_auth.check_room_permission(user_data, room_id, permission):
                    emit('error', {
                        'message': f'Insufficient permissions for {permission} access',
                        'code': 'INSUFFICIENT_PERMISSIONS'
                    })
                    return
                
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"Room permission decorator error: {str(e)}")
                emit('error', {
                    'message': 'Permission check failed',
                    'code': 'PERMISSION_ERROR'
                })
        
        return decorated_function
    return decorator

def rate_limit_ws(event_type: str, limit: int = 50, window: int = 60):
    """
    Decorator to apply rate limiting to WebSocket events.
    
    Args:
        event_type: Type of event for rate limiting
        limit: Maximum number of events
        window: Time window in seconds
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                from flask_socketio import session as socket_session
                
                user_data = socket_session.get('user_data')
                if not user_data:
                    return f(*args, **kwargs)  # Let auth decorator handle
                
                user_id = user_data.get('user_id')
                ws_auth = WebSocketAuth()
                
                if not ws_auth.rate_limit_check(user_id, event_type):
                    emit('error', {
                        'message': f'Rate limit exceeded for {event_type}',
                        'code': 'RATE_LIMIT_EXCEEDED',
                        'retry_after': window
                    })
                    return
                
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"Rate limit decorator error: {str(e)}")
                return f(*args, **kwargs)  # Continue on error
        
        return decorated_function
    return decorator
