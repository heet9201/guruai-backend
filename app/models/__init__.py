from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any

@dataclass
class User:
    """User model."""
    id: str
    email: str
    name: str
    role: str = 'user'
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    is_active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary."""
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """Create user from dictionary."""
        return cls(
            id=data['id'],
            email=data['email'],
            name=data['name'],
            role=data.get('role', 'user'),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else None,
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else None,
            is_active=data.get('is_active', True)
        )

@dataclass
class ChatMessage:
    """Chat message model."""
    id: str
    user_id: str
    message: str
    response: str
    timestamp: datetime
    context: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'message': self.message,
            'response': self.response,
            'timestamp': self.timestamp.isoformat(),
            'context': self.context
        }

@dataclass
class AudioTranscription:
    """Audio transcription model."""
    id: str
    user_id: str
    original_audio_url: str
    transcription: str
    language: str
    confidence: float
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert transcription to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'original_audio_url': self.original_audio_url,
            'transcription': self.transcription,
            'language': self.language,
            'confidence': self.confidence,
            'timestamp': self.timestamp.isoformat()
        }
