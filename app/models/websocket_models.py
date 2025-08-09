"""
WebSocket Models
Data models for real-time communication and collaboration.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum
import json

class MessageType(Enum):
    """Types of real-time messages."""
    TEXT = "text"
    VOICE = "voice"
    IMAGE = "image"
    SYSTEM = "system"
    TYPING = "typing"
    ERROR = "error"

class UserStatus(Enum):
    """User connection status."""
    ONLINE = "online"
    OFFLINE = "offline"
    TYPING = "typing"
    AWAY = "away"

class RoomType(Enum):
    """Types of collaboration rooms."""
    CHAT = "chat"
    PLANNING = "planning"
    CONTENT_GENERATION = "content_generation"
    PRIVATE = "private"

class EventType(Enum):
    """WebSocket event types."""
    # Chat events
    TYPING_START = "typing_start"
    TYPING_STOP = "typing_stop"
    MESSAGE_SENT = "message_sent"
    MESSAGE_RECEIVED = "message_received"
    VOICE_PROCESSING = "voice_processing"
    
    # Collaboration events
    PLAN_UPDATED = "plan_updated"
    USER_JOINED = "user_joined"
    USER_LEFT = "user_left"
    CURSOR_MOVED = "cursor_moved"
    ACTIVITY_DRAGGED = "activity_dragged"
    
    # System events
    CONNECTION_ESTABLISHED = "connection_established"
    AUTHENTICATION_SUCCESS = "authentication_success"
    AUTHENTICATION_FAILED = "authentication_failed"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    ERROR_OCCURRED = "error_occurred"

@dataclass
class WebSocketUser:
    """Represents a connected WebSocket user."""
    user_id: str
    session_id: str
    socket_id: str
    name: str
    email: str
    status: UserStatus = UserStatus.ONLINE
    connected_at: datetime = field(default_factory=datetime.utcnow)
    last_seen: datetime = field(default_factory=datetime.utcnow)
    rooms: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'user_id': self.user_id,
            'session_id': self.session_id,
            'socket_id': self.socket_id,
            'name': self.name,
            'email': self.email,
            'status': self.status.value,
            'connected_at': self.connected_at.isoformat(),
            'last_seen': self.last_seen.isoformat(),
            'rooms': self.rooms,
            'metadata': self.metadata
        }

@dataclass
class ChatMessage:
    """Represents a chat message."""
    id: str
    room_id: str
    user_id: str
    content: str
    message_type: MessageType = MessageType.TEXT
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    edited: bool = False
    edited_at: Optional[datetime] = None
    reply_to: Optional[str] = None
    reactions: Dict[str, List[str]] = field(default_factory=dict)  # emoji -> user_ids
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'room_id': self.room_id,
            'user_id': self.user_id,
            'content': self.content,
            'message_type': self.message_type.value,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata,
            'edited': self.edited,
            'edited_at': self.edited_at.isoformat() if self.edited_at else None,
            'reply_to': self.reply_to,
            'reactions': self.reactions
        }

@dataclass
class TypingIndicator:
    """Represents typing indicator state."""
    user_id: str
    room_id: str
    started_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'user_id': self.user_id,
            'room_id': self.room_id,
            'started_at': self.started_at.isoformat()
        }

@dataclass
class CursorPosition:
    """Represents user cursor position in collaborative editing."""
    user_id: str
    room_id: str
    x: float
    y: float
    element_id: Optional[str] = None
    selection_start: Optional[int] = None
    selection_end: Optional[int] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'user_id': self.user_id,
            'room_id': self.room_id,
            'x': self.x,
            'y': self.y,
            'element_id': self.element_id,
            'selection_start': self.selection_start,
            'selection_end': self.selection_end,
            'timestamp': self.timestamp.isoformat()
        }

@dataclass
class PlanUpdate:
    """Represents a plan update in collaborative planning."""
    id: str
    room_id: str
    user_id: str
    operation: str  # 'create', 'update', 'delete', 'move'
    target_type: str  # 'plan', 'activity', 'lesson'
    target_id: str
    changes: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'room_id': self.room_id,
            'user_id': self.user_id,
            'operation': self.operation,
            'target_type': self.target_type,
            'target_id': self.target_id,
            'changes': self.changes,
            'timestamp': self.timestamp.isoformat()
        }

@dataclass
class Room:
    """Represents a collaboration room."""
    id: str
    name: str
    room_type: RoomType
    created_by: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    active_users: Dict[str, WebSocketUser] = field(default_factory=dict)
    typing_users: Dict[str, TypingIndicator] = field(default_factory=dict)
    cursor_positions: Dict[str, CursorPosition] = field(default_factory=dict)
    settings: Dict[str, Any] = field(default_factory=dict)
    permissions: Dict[str, List[str]] = field(default_factory=dict)  # user_id -> permissions
    
    def add_user(self, user: WebSocketUser) -> None:
        """Add user to room."""
        self.active_users[user.user_id] = user
        if self.id not in user.rooms:
            user.rooms.append(self.id)
    
    def remove_user(self, user_id: str) -> Optional[WebSocketUser]:
        """Remove user from room."""
        user = self.active_users.pop(user_id, None)
        if user and self.id in user.rooms:
            user.rooms.remove(self.id)
        # Clean up user-specific data
        self.typing_users.pop(user_id, None)
        self.cursor_positions.pop(user_id, None)
        return user
    
    def get_user_count(self) -> int:
        """Get number of active users."""
        return len(self.active_users)
    
    def has_permission(self, user_id: str, permission: str) -> bool:
        """Check if user has specific permission."""
        user_permissions = self.permissions.get(user_id, [])
        return permission in user_permissions or 'admin' in user_permissions
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'room_type': self.room_type.value,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat(),
            'active_users': {uid: user.to_dict() for uid, user in self.active_users.items()},
            'user_count': self.get_user_count(),
            'settings': self.settings
        }

@dataclass
class WebSocketEvent:
    """Represents a WebSocket event."""
    event_type: EventType
    room_id: str
    user_id: str
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    event_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'event_type': self.event_type.value,
            'room_id': self.room_id,
            'user_id': self.user_id,
            'data': self.data,
            'timestamp': self.timestamp.isoformat(),
            'event_id': self.event_id
        }

@dataclass
class ConnectionInfo:
    """Stores connection information."""
    socket_id: str
    user_id: str
    session_id: str
    connected_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'socket_id': self.socket_id,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'connected_at': self.connected_at.isoformat(),
            'last_activity': self.last_activity.isoformat(),
            'ip_address': self.ip_address,
            'user_agent': self.user_agent
        }

@dataclass
class QueuedMessage:
    """Represents a queued message for offline users."""
    id: str
    user_id: str
    room_id: str
    message: ChatMessage
    created_at: datetime = field(default_factory=datetime.utcnow)
    delivered: bool = False
    delivered_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'room_id': self.room_id,
            'message': self.message.to_dict(),
            'created_at': self.created_at.isoformat(),
            'delivered': self.delivered,
            'delivered_at': self.delivered_at.isoformat() if self.delivered_at else None
        }

@dataclass
class RateLimitInfo:
    """Rate limiting information."""
    user_id: str
    event_type: str
    count: int = 0
    window_start: datetime = field(default_factory=datetime.utcnow)
    blocked_until: Optional[datetime] = None
    
    def increment(self) -> None:
        """Increment the count."""
        self.count += 1
    
    def reset(self) -> None:
        """Reset the counter."""
        self.count = 0
        self.window_start = datetime.utcnow()
        self.blocked_until = None
    
    def is_blocked(self) -> bool:
        """Check if currently blocked."""
        if self.blocked_until is None:
            return False
        return datetime.utcnow() < self.blocked_until
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'user_id': self.user_id,
            'event_type': self.event_type,
            'count': self.count,
            'window_start': self.window_start.isoformat(),
            'blocked_until': self.blocked_until.isoformat() if self.blocked_until else None
        }
