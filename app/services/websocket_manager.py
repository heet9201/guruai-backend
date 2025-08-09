"""
WebSocket Manager Service
Manages WebSocket connections, rooms, and real-time communication.
"""

import logging
import uuid
import json
from typing import Dict, List, Optional, Set, Any
from datetime import datetime, timedelta
from collections import defaultdict, deque
import redis
from flask import current_app
from flask_socketio import emit, join_room, leave_room, disconnect

from app.models.websocket_models import (
    WebSocketUser, Room, ChatMessage, TypingIndicator, CursorPosition,
    PlanUpdate, WebSocketEvent, ConnectionInfo, QueuedMessage, RateLimitInfo,
    MessageType, UserStatus, RoomType, EventType
)

logger = logging.getLogger(__name__)

class WebSocketManager:
    """Manages WebSocket connections and real-time features."""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """Initialize WebSocket manager."""
        self.redis_client = redis_client
        
        # In-memory storage (consider Redis for production scaling)
        self.connections: Dict[str, ConnectionInfo] = {}  # socket_id -> connection_info
        self.user_sockets: Dict[str, Set[str]] = defaultdict(set)  # user_id -> socket_ids
        self.rooms: Dict[str, Room] = {}  # room_id -> room
        self.message_queues: Dict[str, deque] = defaultdict(deque)  # user_id -> queued_messages
        self.rate_limits: Dict[str, Dict[str, RateLimitInfo]] = defaultdict(dict)  # user_id -> event_type -> rate_limit
        
        # Rate limiting configuration
        self.rate_limit_config = {
            EventType.MESSAGE_SENT.value: {'limit': 30, 'window': 60},  # 30 messages per minute
            EventType.TYPING_START.value: {'limit': 10, 'window': 60},  # 10 typing events per minute
            EventType.CURSOR_MOVED.value: {'limit': 100, 'window': 60},  # 100 cursor moves per minute
            EventType.PLAN_UPDATED.value: {'limit': 50, 'window': 60},  # 50 plan updates per minute
        }
        
        # Message history (last 100 messages per room)
        self.message_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
    
    # Connection Management
    
    def add_connection(self, socket_id: str, user_id: str, session_id: str, 
                      ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> ConnectionInfo:
        """Add a new WebSocket connection."""
        connection = ConnectionInfo(
            socket_id=socket_id,
            user_id=user_id,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        self.connections[socket_id] = connection
        self.user_sockets[user_id].add(socket_id)
        
        logger.info(f"WebSocket connection added: user={user_id}, socket={socket_id}")
        return connection
    
    def remove_connection(self, socket_id: str) -> Optional[ConnectionInfo]:
        """Remove a WebSocket connection."""
        connection = self.connections.pop(socket_id, None)
        if connection:
            self.user_sockets[connection.user_id].discard(socket_id)
            if not self.user_sockets[connection.user_id]:
                del self.user_sockets[connection.user_id]
            
            # Remove user from all rooms
            self._remove_user_from_all_rooms(connection.user_id, socket_id)
            
            logger.info(f"WebSocket connection removed: user={connection.user_id}, socket={socket_id}")
        return connection
    
    def get_connection(self, socket_id: str) -> Optional[ConnectionInfo]:
        """Get connection information."""
        return self.connections.get(socket_id)
    
    def is_user_online(self, user_id: str) -> bool:
        """Check if user has any active connections."""
        return bool(self.user_sockets.get(user_id))
    
    def update_last_activity(self, socket_id: str) -> None:
        """Update last activity timestamp for connection."""
        connection = self.connections.get(socket_id)
        if connection:
            connection.last_activity = datetime.utcnow()
    
    # Room Management
    
    def create_room(self, room_id: str, name: str, room_type: RoomType, 
                   created_by: str, settings: Optional[Dict[str, Any]] = None) -> Room:
        """Create a new room."""
        room = Room(
            id=room_id,
            name=name,
            room_type=room_type,
            created_by=created_by,
            settings=settings or {}
        )
        
        # Set default permissions for creator
        room.permissions[created_by] = ['admin', 'read', 'write', 'invite']
        
        self.rooms[room_id] = room
        logger.info(f"Room created: {room_id} by {created_by}")
        return room
    
    def get_room(self, room_id: str) -> Optional[Room]:
        """Get room by ID."""
        return self.rooms.get(room_id)
    
    def join_room_ws(self, socket_id: str, room_id: str, user_info: Dict[str, Any]) -> bool:
        """Join user to a room."""
        connection = self.get_connection(socket_id)
        if not connection:
            return False
        
        room = self.get_room(room_id)
        if not room:
            return False
        
        # Create WebSocket user
        ws_user = WebSocketUser(
            user_id=connection.user_id,
            session_id=connection.session_id,
            socket_id=socket_id,
            name=user_info.get('name', 'Unknown'),
            email=user_info.get('email', ''),
            metadata=user_info.get('metadata', {})
        )
        
        # Add user to room
        room.add_user(ws_user)
        
        # Join SocketIO room
        join_room(room_id)
        
        # Emit user joined event
        self._emit_to_room(room_id, EventType.USER_JOINED, {
            'user': ws_user.to_dict(),
            'room': room.to_dict()
        }, exclude_user=connection.user_id)
        
        # Deliver queued messages
        self._deliver_queued_messages(connection.user_id)
        
        logger.info(f"User {connection.user_id} joined room {room_id}")
        return True
    
    def leave_room_ws(self, socket_id: str, room_id: str) -> bool:
        """Remove user from room."""
        connection = self.get_connection(socket_id)
        if not connection:
            return False
        
        room = self.get_room(room_id)
        if not room:
            return False
        
        user = room.remove_user(connection.user_id)
        if user:
            # Leave SocketIO room
            leave_room(room_id)
            
            # Emit user left event
            self._emit_to_room(room_id, EventType.USER_LEFT, {
                'user_id': connection.user_id,
                'room_id': room_id,
                'remaining_users': room.get_user_count()
            })
            
            logger.info(f"User {connection.user_id} left room {room_id}")
            return True
        return False
    
    def _remove_user_from_all_rooms(self, user_id: str, socket_id: str) -> None:
        """Remove user from all rooms."""
        for room in self.rooms.values():
            if user_id in room.active_users:
                room.remove_user(user_id)
                self._emit_to_room(room.id, EventType.USER_LEFT, {
                    'user_id': user_id,
                    'room_id': room.id,
                    'remaining_users': room.get_user_count()
                })
    
    # Chat Features
    
    def send_message(self, socket_id: str, room_id: str, content: str, 
                    message_type: MessageType = MessageType.TEXT, 
                    metadata: Optional[Dict[str, Any]] = None) -> Optional[ChatMessage]:
        """Send a chat message."""
        connection = self.get_connection(socket_id)
        if not connection:
            return None
        
        room = self.get_room(room_id)
        if not room or connection.user_id not in room.active_users:
            return None
        
        # Check rate limits
        if not self._check_rate_limit(connection.user_id, EventType.MESSAGE_SENT):
            self._emit_to_user(connection.user_id, EventType.RATE_LIMIT_EXCEEDED, {
                'event_type': EventType.MESSAGE_SENT.value,
                'message': 'Rate limit exceeded for messages'
            })
            return None
        
        # Create message
        message = ChatMessage(
            id=str(uuid.uuid4()),
            room_id=room_id,
            user_id=connection.user_id,
            content=content,
            message_type=message_type,
            metadata=metadata or {}
        )
        
        # Store in history
        self.message_history[room_id].append(message)
        
        # Emit to room
        self._emit_to_room(room_id, EventType.MESSAGE_RECEIVED, {
            'message': message.to_dict()
        })
        
        # Queue for offline users
        self._queue_message_for_offline_users(room, message)
        
        logger.info(f"Message sent: {message.id} in room {room_id}")
        return message
    
    def handle_typing(self, socket_id: str, room_id: str, is_typing: bool) -> bool:
        """Handle typing indicators."""
        connection = self.get_connection(socket_id)
        if not connection:
            return False
        
        room = self.get_room(room_id)
        if not room or connection.user_id not in room.active_users:
            return False
        
        event_type = EventType.TYPING_START if is_typing else EventType.TYPING_STOP
        
        # Check rate limits
        if not self._check_rate_limit(connection.user_id, event_type):
            return False
        
        if is_typing:
            # Add typing indicator
            room.typing_users[connection.user_id] = TypingIndicator(
                user_id=connection.user_id,
                room_id=room_id
            )
        else:
            # Remove typing indicator
            room.typing_users.pop(connection.user_id, None)
        
        # Emit typing event
        self._emit_to_room(room_id, event_type, {
            'user_id': connection.user_id,
            'room_id': room_id,
            'typing_users': [user_id for user_id in room.typing_users.keys()]
        }, exclude_user=connection.user_id)
        
        return True
    
    def handle_voice_processing(self, socket_id: str, room_id: str, 
                               processing_status: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Handle voice processing status."""
        connection = self.get_connection(socket_id)
        if not connection:
            return False
        
        room = self.get_room(room_id)
        if not room or connection.user_id not in room.active_users:
            return False
        
        # Emit voice processing status
        self._emit_to_room(room_id, EventType.VOICE_PROCESSING, {
            'user_id': connection.user_id,
            'room_id': room_id,
            'status': processing_status,
            'metadata': metadata or {}
        })
        
        return True
    
    # Collaboration Features
    
    def update_cursor_position(self, socket_id: str, room_id: str, x: float, y: float,
                              element_id: Optional[str] = None, 
                              selection_start: Optional[int] = None,
                              selection_end: Optional[int] = None) -> bool:
        """Update user cursor position."""
        connection = self.get_connection(socket_id)
        if not connection:
            return False
        
        room = self.get_room(room_id)
        if not room or connection.user_id not in room.active_users:
            return False
        
        # Check rate limits
        if not self._check_rate_limit(connection.user_id, EventType.CURSOR_MOVED):
            return False
        
        cursor_pos = CursorPosition(
            user_id=connection.user_id,
            room_id=room_id,
            x=x,
            y=y,
            element_id=element_id,
            selection_start=selection_start,
            selection_end=selection_end
        )
        
        room.cursor_positions[connection.user_id] = cursor_pos
        
        # Emit cursor position update
        self._emit_to_room(room_id, EventType.CURSOR_MOVED, {
            'cursor': cursor_pos.to_dict()
        }, exclude_user=connection.user_id)
        
        return True
    
    def handle_plan_update(self, socket_id: str, room_id: str, operation: str,
                          target_type: str, target_id: str, changes: Dict[str, Any]) -> bool:
        """Handle collaborative plan updates."""
        connection = self.get_connection(socket_id)
        if not connection:
            return False
        
        room = self.get_room(room_id)
        if not room or connection.user_id not in room.active_users:
            return False
        
        # Check permissions
        if not room.has_permission(connection.user_id, 'write'):
            self._emit_to_user(connection.user_id, EventType.ERROR_OCCURRED, {
                'message': 'Insufficient permissions for plan updates'
            })
            return False
        
        # Check rate limits
        if not self._check_rate_limit(connection.user_id, EventType.PLAN_UPDATED):
            return False
        
        plan_update = PlanUpdate(
            id=str(uuid.uuid4()),
            room_id=room_id,
            user_id=connection.user_id,
            operation=operation,
            target_type=target_type,
            target_id=target_id,
            changes=changes
        )
        
        # Emit plan update
        self._emit_to_room(room_id, EventType.PLAN_UPDATED, {
            'update': plan_update.to_dict()
        }, exclude_user=connection.user_id)
        
        logger.info(f"Plan update: {plan_update.id} in room {room_id}")
        return True
    
    def handle_activity_drag(self, socket_id: str, room_id: str, activity_id: str,
                           from_position: Dict[str, Any], to_position: Dict[str, Any]) -> bool:
        """Handle drag-and-drop operations."""
        connection = self.get_connection(socket_id)
        if not connection:
            return False
        
        room = self.get_room(room_id)
        if not room or connection.user_id not in room.active_users:
            return False
        
        # Check permissions
        if not room.has_permission(connection.user_id, 'write'):
            return False
        
        # Emit activity drag event
        self._emit_to_room(room_id, EventType.ACTIVITY_DRAGGED, {
            'user_id': connection.user_id,
            'activity_id': activity_id,
            'from_position': from_position,
            'to_position': to_position,
            'timestamp': datetime.utcnow().isoformat()
        }, exclude_user=connection.user_id)
        
        return True
    
    # Message Queuing
    
    def _queue_message_for_offline_users(self, room: Room, message: ChatMessage) -> None:
        """Queue message for offline users in the room."""
        for user_id in room.permissions.keys():
            if not self.is_user_online(user_id):
                queued_msg = QueuedMessage(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    room_id=room.id,
                    message=message
                )
                self.message_queues[user_id].append(queued_msg)
    
    def _deliver_queued_messages(self, user_id: str) -> None:
        """Deliver queued messages to user."""
        queue = self.message_queues.get(user_id, deque())
        delivered_messages = []
        
        while queue:
            queued_msg = queue.popleft()
            # Emit queued message
            self._emit_to_user(user_id, EventType.MESSAGE_RECEIVED, {
                'message': queued_msg.message.to_dict(),
                'queued': True,
                'queued_at': queued_msg.created_at.isoformat()
            })
            delivered_messages.append(queued_msg)
        
        if delivered_messages:
            logger.info(f"Delivered {len(delivered_messages)} queued messages to {user_id}")
    
    def get_queued_message_count(self, user_id: str) -> int:
        """Get number of queued messages for user."""
        return len(self.message_queues.get(user_id, deque()))
    
    # Rate Limiting
    
    def _check_rate_limit(self, user_id: str, event_type: EventType) -> bool:
        """Check if user has exceeded rate limit for event type."""
        event_name = event_type.value
        config = self.rate_limit_config.get(event_name)
        if not config:
            return True  # No rate limit configured
        
        rate_limit = self.rate_limits[user_id].get(event_name)
        if not rate_limit:
            rate_limit = RateLimitInfo(user_id=user_id, event_type=event_name)
            self.rate_limits[user_id][event_name] = rate_limit
        
        # Check if currently blocked
        if rate_limit.is_blocked():
            return False
        
        # Check window reset
        window_duration = timedelta(seconds=config['window'])
        if datetime.utcnow() - rate_limit.window_start > window_duration:
            rate_limit.reset()
        
        # Increment count
        rate_limit.increment()
        
        # Check if limit exceeded
        if rate_limit.count > config['limit']:
            # Block user for the remainder of the window
            remaining_time = window_duration - (datetime.utcnow() - rate_limit.window_start)
            rate_limit.blocked_until = datetime.utcnow() + remaining_time
            logger.warning(f"Rate limit exceeded: user={user_id}, event={event_name}")
            return False
        
        return True
    
    def reset_rate_limit(self, user_id: str, event_type: Optional[EventType] = None) -> None:
        """Reset rate limit for user."""
        if event_type:
            rate_limit = self.rate_limits[user_id].get(event_type.value)
            if rate_limit:
                rate_limit.reset()
        else:
            # Reset all rate limits for user
            for rate_limit in self.rate_limits[user_id].values():
                rate_limit.reset()
    
    # Event Emission
    
    def _emit_to_room(self, room_id: str, event_type: EventType, data: Dict[str, Any], 
                     exclude_user: Optional[str] = None) -> None:
        """Emit event to all users in room."""
        event = WebSocketEvent(
            event_type=event_type,
            room_id=room_id,
            user_id=exclude_user or 'system',
            data=data,
            event_id=str(uuid.uuid4())
        )
        
        # Use SocketIO emit to room
        emit(event_type.value, event.to_dict(), room=room_id, include_self=False)
    
    def _emit_to_user(self, user_id: str, event_type: EventType, data: Dict[str, Any]) -> None:
        """Emit event to specific user."""
        socket_ids = self.user_sockets.get(user_id, set())
        if socket_ids:
            event = WebSocketEvent(
                event_type=event_type,
                room_id='',
                user_id=user_id,
                data=data,
                event_id=str(uuid.uuid4())
            )
            
            for socket_id in socket_ids:
                emit(event_type.value, event.to_dict(), room=socket_id)
    
    # Utility Methods
    
    def get_room_list(self, user_id: str) -> List[Dict[str, Any]]:
        """Get list of rooms user has access to."""
        user_rooms = []
        for room in self.rooms.values():
            if user_id in room.permissions or room.room_type == RoomType.CHAT:
                user_rooms.append(room.to_dict())
        return user_rooms
    
    def get_room_history(self, room_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get message history for room."""
        messages = list(self.message_history.get(room_id, deque()))
        return [msg.to_dict() for msg in messages[-limit:]]
    
    def get_active_users(self, room_id: str) -> List[Dict[str, Any]]:
        """Get active users in room."""
        room = self.get_room(room_id)
        if room:
            return [user.to_dict() for user in room.active_users.values()]
        return []
    
    def cleanup_inactive_connections(self, timeout_minutes: int = 30) -> int:
        """Clean up inactive connections."""
        cutoff_time = datetime.utcnow() - timedelta(minutes=timeout_minutes)
        inactive_connections = []
        
        for socket_id, connection in self.connections.items():
            if connection.last_activity < cutoff_time:
                inactive_connections.append(socket_id)
        
        for socket_id in inactive_connections:
            self.remove_connection(socket_id)
        
        logger.info(f"Cleaned up {len(inactive_connections)} inactive connections")
        return len(inactive_connections)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get WebSocket manager statistics."""
        return {
            'total_connections': len(self.connections),
            'total_users': len(self.user_sockets),
            'total_rooms': len(self.rooms),
            'room_stats': {
                room_id: {
                    'user_count': room.get_user_count(),
                    'message_count': len(self.message_history.get(room_id, deque())),
                    'room_type': room.room_type.value
                }
                for room_id, room in self.rooms.items()
            },
            'queued_messages': {
                user_id: len(queue) 
                for user_id, queue in self.message_queues.items() 
                if queue
            }
        }
