"""
WebSocket Configuration and Initialization
Configures Flask-SocketIO and initializes WebSocket handlers.
"""

import logging
import redis
from typing import Optional, Dict, Any, List
from flask import Flask
from flask_socketio import SocketIO

from app.services.websocket_manager import WebSocketManager
from app.routes.websocket_chat import ChatSocketHandler
from app.routes.websocket_collaboration import CollaborationSocketHandler

logger = logging.getLogger(__name__)

class WebSocketConfig:
    """WebSocket configuration and initialization."""
    
    def __init__(self, app: Optional[Flask] = None, redis_client: Optional[redis.Redis] = None):
        """Initialize WebSocket configuration."""
        self.app = app
        self.socketio: Optional[SocketIO] = None
        self.ws_manager: Optional[WebSocketManager] = None
        self.chat_handler: Optional[ChatSocketHandler] = None
        self.collaboration_handler: Optional[CollaborationSocketHandler] = None
        self.redis_client = redis_client
        
        if app:
            self.init_app(app)
    
    def init_app(self, app: Flask, redis_client: Optional[redis.Redis] = None) -> SocketIO:
        """Initialize WebSocket functionality for Flask app."""
        self.app = app
        self.redis_client = redis_client or self.redis_client
        
        # Initialize Redis client if not provided
        if not self.redis_client:
            try:
                redis_url = app.config.get('REDIS_URL', 'redis://localhost:6379/0')
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                # Test connection
                self.redis_client.ping()
                logger.info("Redis connection established for WebSocket")
            except Exception as e:
                logger.warning(f"Redis connection failed, using in-memory storage: {str(e)}")
                self.redis_client = None
        
        # Configure SocketIO
        self.socketio = SocketIO(
            app,
            cors_allowed_origins=["http://localhost:5000", "http://127.0.0.1:5000", "http://localhost:3000", "http://127.0.0.1:3000"],
            async_mode='threading',  # Use threading for development
            logger=False,  # Disable SocketIO logging to avoid spam
            engineio_logger=False,
            allow_upgrades=True,
            transports=['websocket', 'polling'],  # Support fallback to polling
            ping_timeout=60,
            ping_interval=25,
            max_http_buffer_size=1e6,  # 1MB max message size
            # Add version compatibility settings
            always_connect=False,
            json=None  # Use default JSON encoder
        )
        
        # Initialize WebSocket manager
        self.ws_manager = WebSocketManager(redis_client=self.redis_client)
        
        # Initialize handlers
        self.chat_handler = ChatSocketHandler(self.socketio, self.ws_manager)
        self.collaboration_handler = CollaborationSocketHandler(self.socketio, self.ws_manager)
        
        # Register global error handlers
        self._register_global_handlers()
        
        # Schedule cleanup tasks
        self._schedule_cleanup_tasks()
        
        logger.info("WebSocket functionality initialized successfully")
        return self.socketio
    
    def _get_message_queue_url(self) -> Optional[str]:
        """Get message queue URL for scaling WebSocket across multiple instances."""
        if self.redis_client and self.app:
            redis_url = self.app.config.get('REDIS_URL')
            if redis_url:
                # Use Redis as message queue for multi-instance scaling
                return redis_url
        return None
    
    def _register_global_handlers(self):
        """Register global WebSocket event handlers."""
        
        @self.socketio.on_error_default
        def default_error_handler(e):
            """Handle WebSocket errors."""
            logger.error(f"WebSocket error: {str(e)}")
        
        @self.socketio.on('connect')
        def handle_global_connect():
            """Handle global WebSocket connection (no namespace)."""
            logger.info("Global WebSocket connection attempted - redirecting to specific namespace")
            return False  # Reject connections to global namespace
        
        @self.socketio.on('disconnect')
        def handle_global_disconnect(reason=None):
            """Handle global WebSocket disconnection."""
            logger.info(f"Global WebSocket disconnection: {reason}")
        
        @self.socketio.on('error')
        def handle_error(error_data):
            """Handle global WebSocket errors."""
            logger.error(f"Global WebSocket error: {error_data}")
    
    def _schedule_cleanup_tasks(self):
        """Schedule periodic cleanup tasks."""
        if not self.socketio or not self.ws_manager:
            return
        
        # Schedule cleanup every 5 minutes
        @self.socketio.on('connect')
        def schedule_cleanup():
            """Schedule periodic cleanup tasks."""
            import threading
            import time
            
            def cleanup_worker():
                while True:
                    try:
                        time.sleep(300)  # 5 minutes
                        if self.ws_manager:
                            self.ws_manager.cleanup_inactive_connections(timeout_minutes=30)
                    except Exception as e:
                        logger.error(f"Cleanup task error: {str(e)}")
            
            # Start cleanup thread (only once)
            if not hasattr(self, '_cleanup_thread'):
                self._cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
                self._cleanup_thread.start()
                logger.info("WebSocket cleanup task scheduled")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get WebSocket statistics."""
        stats = {
            'socketio_initialized': self.socketio is not None,
            'redis_connected': self.redis_client is not None,
            'handlers_registered': {
                'chat': self.chat_handler is not None,
                'collaboration': self.collaboration_handler is not None
            }
        }
        
        if self.ws_manager:
            stats.update(self.ws_manager.get_stats())
        
        return stats
    
    def get_handler_info(self) -> Dict[str, Any]:
        """Get information about all registered handlers."""
        info = {
            'handlers': [],
            'namespaces': [],
            'total_events': 0
        }
        
        if self.chat_handler:
            chat_info = self.chat_handler.get_handler_info()
            info['handlers'].append(chat_info)
            info['namespaces'].append(chat_info['namespace'])
            info['total_events'] += len(chat_info['events'])
        
        if self.collaboration_handler:
            collab_info = self.collaboration_handler.get_handler_info()
            info['handlers'].append(collab_info)
            info['namespaces'].append(collab_info['namespace'])
            info['total_events'] += len(collab_info['events'])
        
        return info
    
    def emit_to_user(self, user_id: str, event: str, data: Dict[str, Any], 
                    namespace: Optional[str] = None) -> bool:
        """Emit event to specific user across all their connections."""
        if not self.ws_manager:
            return False
        
        try:
            socket_ids = self.ws_manager.user_sockets.get(user_id, set())
            if not socket_ids:
                return False
            
            for socket_id in socket_ids:
                if namespace:
                    self.socketio.emit(event, data, room=socket_id, namespace=namespace)
                else:
                    self.socketio.emit(event, data, room=socket_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Error emitting to user {user_id}: {str(e)}")
            return False
    
    def emit_to_room(self, room_id: str, event: str, data: Dict[str, Any], 
                    namespace: Optional[str] = None, exclude_user: Optional[str] = None) -> bool:
        """Emit event to all users in a room."""
        try:
            emit_kwargs = {
                'event': event,
                'data': data,
                'room': room_id
            }
            
            if namespace:
                emit_kwargs['namespace'] = namespace
            
            if exclude_user and self.ws_manager:
                # Get socket IDs to exclude
                exclude_sockets = self.ws_manager.user_sockets.get(exclude_user, set())
                # Note: Flask-SocketIO doesn't have built-in exclude functionality
                # This would need custom implementation
            
            self.socketio.emit(**emit_kwargs)
            return True
            
        except Exception as e:
            logger.error(f"Error emitting to room {room_id}: {str(e)}")
            return False
    
    def create_room(self, room_id: str, name: str, room_type: str, 
                   created_by: str, settings: Optional[Dict[str, Any]] = None) -> bool:
        """Create a new WebSocket room."""
        if not self.ws_manager:
            return False
        
        try:
            from app.models.websocket_models import RoomType
            room_type_enum = RoomType(room_type)
            
            room = self.ws_manager.create_room(
                room_id=room_id,
                name=name,
                room_type=room_type_enum,
                created_by=created_by,
                settings=settings
            )
            
            return room is not None
            
        except Exception as e:
            logger.error(f"Error creating room {room_id}: {str(e)}")
            return False
    
    def get_room_users(self, room_id: str) -> List[Dict[str, Any]]:
        """Get list of users in a room."""
        if not self.ws_manager:
            return []
        
        return self.ws_manager.get_active_users(room_id)
    
    def disconnect_user(self, user_id: str, reason: str = "Disconnected by admin") -> bool:
        """Disconnect all connections for a user."""
        if not self.ws_manager:
            return False
        
        try:
            socket_ids = list(self.ws_manager.user_sockets.get(user_id, set()))
            
            for socket_id in socket_ids:
                self.socketio.disconnect(socket_id, namespace='/ws/chat')
                self.socketio.disconnect(socket_id, namespace='/ws/collaboration')
            
            logger.info(f"Disconnected user {user_id}: {reason}")
            return True
            
        except Exception as e:
            logger.error(f"Error disconnecting user {user_id}: {str(e)}")
            return False


# Global WebSocket configuration instance
websocket_config = WebSocketConfig()

def init_websockets(app: Flask, redis_client: Optional[redis.Redis] = None) -> SocketIO:
    """Initialize WebSocket functionality for the Flask app."""
    return websocket_config.init_app(app, redis_client)

def get_socketio() -> Optional[SocketIO]:
    """Get the SocketIO instance."""
    return websocket_config.socketio

def get_websocket_manager() -> Optional[WebSocketManager]:
    """Get the WebSocket manager instance."""
    return websocket_config.ws_manager

def get_websocket_stats() -> Dict[str, Any]:
    """Get WebSocket statistics."""
    return websocket_config.get_stats()

def emit_to_user(user_id: str, event: str, data: Dict[str, Any], 
                namespace: Optional[str] = None) -> bool:
    """Emit event to specific user."""
    return websocket_config.emit_to_user(user_id, event, data, namespace)

def emit_to_room(room_id: str, event: str, data: Dict[str, Any], 
                namespace: Optional[str] = None, exclude_user: Optional[str] = None) -> bool:
    """Emit event to room."""
    return websocket_config.emit_to_room(room_id, event, data, namespace, exclude_user)
