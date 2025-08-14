"""
Chat models for intelligent chat functionality.
"""
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
from enum import Enum
import json

class ChatSessionType(Enum):
    """Types of chat sessions."""
    GENERAL = "general"
    SUBJECT_SPECIFIC = "subject_specific"
    LESSON_PLANNING = "lesson_planning"
    CONTENT_CREATION = "content_creation"
    PROBLEM_SOLVING = "problem_solving"
    QUICK_HELP = "quick_help"

class MessageType(Enum):
    """Types of chat messages."""
    USER = "user"
    AI = "ai"
    SYSTEM = "system"

class SuggestionType(Enum):
    """Types of suggestions."""
    FOLLOW_UP_QUESTION = "follow_up_question"
    RELATED_TOPIC = "related_topic"
    STUDY_SUGGESTION = "study_suggestion"
    QUICK_ACTION = "quick_action"
    EXPLORATION_PROMPT = "exploration_prompt"

@dataclass
class ChatMessage:
    """Individual chat message."""
    id: str
    session_id: str
    user_id: Optional[str]
    message_type: MessageType
    content: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'user_id': self.user_id,
            'message_type': self.message_type.value,
            'content': self.content,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata or {}
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChatMessage':
        """Create from dictionary."""
        return cls(
            id=data['id'],
            session_id=data['session_id'],
            user_id=data.get('user_id'),
            message_type=MessageType(data['message_type']),
            content=data['content'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            metadata=data.get('metadata')
        )

@dataclass
class ChatSuggestion:
    """Individual chat suggestion."""
    id: str
    suggestion_type: SuggestionType
    content: str
    metadata: Optional[Dict[str, Any]] = None
    priority: int = 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'type': self.suggestion_type.value,
            'content': self.content,
            'metadata': self.metadata or {},
            'priority': self.priority
        }

@dataclass
class RelatedTopic:
    """Related educational topic."""
    id: str
    title: str
    description: str
    subject: str
    grades: List[str]
    difficulty: str
    keywords: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'subject': self.subject,
            'grades': self.grades,
            'difficulty': self.difficulty,
            'keywords': self.keywords
        }

@dataclass
class StudyRecommendation:
    """Study recommendation based on chat context."""
    id: str
    title: str
    description: str
    action_type: str  # 'create_content', 'plan_lesson', 'practice_quiz'
    action_data: Dict[str, Any]
    reasoning: str
    priority: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'action_type': self.action_type,
            'action_data': self.action_data,
            'reasoning': self.reasoning,
            'priority': self.priority
        }

@dataclass
class ChatSession:
    """Chat session with metadata."""
    id: str
    user_id: str
    title: str
    session_type: ChatSessionType
    created_at: datetime
    last_activity_at: datetime
    message_count: int = 0
    topic_tags: List[str] = None
    context: Optional[Dict[str, Any]] = None
    settings: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.topic_tags is None:
            self.topic_tags = []
        if self.context is None:
            self.context = {}
        if self.settings is None:
            self.settings = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'session_type': self.session_type.value,
            'created_at': self.created_at.isoformat(),
            'last_activity_at': self.last_activity_at.isoformat(),
            'message_count': self.message_count,
            'topic_tags': self.topic_tags,
            'context': self.context,
            'settings': self.settings
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChatSession':
        """Create from dictionary."""
        return cls(
            id=data['id'],
            user_id=data['user_id'],
            title=data['title'],
            session_type=ChatSessionType(data['session_type']),
            created_at=datetime.fromisoformat(data['created_at']),
            last_activity_at=datetime.fromisoformat(data['last_activity_at']),
            message_count=data.get('message_count', 0),
            topic_tags=data.get('topic_tags', []),
            context=data.get('context', {}),
            settings=data.get('settings', {})
        )

@dataclass
class UserContext:
    """User context for personalized chat."""
    user_id: str
    profile: Optional[Dict[str, Any]] = None
    recent_activities: List[Dict[str, Any]] = None
    current_tasks: List[Dict[str, Any]] = None
    preferences: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.recent_activities is None:
            self.recent_activities = []
        if self.current_tasks is None:
            self.current_tasks = []
        if self.preferences is None:
            self.preferences = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'user_id': self.user_id,
            'profile': self.profile,
            'recent_activities': self.recent_activities,
            'current_tasks': self.current_tasks,
            'preferences': self.preferences
        }

@dataclass
class IntelligentChatResponse:
    """Complete intelligent chat response."""
    message_id: str
    content: str
    timestamp: datetime
    suggestions: List[ChatSuggestion]
    related_topics: List[RelatedTopic]
    study_recommendations: List[StudyRecommendation]
    analytics: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'message_id': self.message_id,
            'content': self.content,
            'timestamp': self.timestamp.isoformat(),
            'suggestions': [s.to_dict() for s in self.suggestions],
            'related_topics': [t.to_dict() for t in self.related_topics],
            'study_recommendations': [r.to_dict() for r in self.study_recommendations],
            'analytics': self.analytics or {}
        }

@dataclass
class ConversationContext:
    """Context for conversation analysis."""
    session_id: str
    recent_messages: List[ChatMessage]
    user_context: UserContext
    extracted_topics: List[str] = None
    sentiment: Optional[str] = None
    intent: Optional[str] = None
    
    def __post_init__(self):
        if self.extracted_topics is None:
            self.extracted_topics = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'session_id': self.session_id,
            'recent_messages': [m.to_dict() for m in self.recent_messages],
            'user_context': self.user_context.to_dict(),
            'extracted_topics': self.extracted_topics,
            'sentiment': self.sentiment,
            'intent': self.intent
        }

@dataclass
class ChatAnalytics:
    """Analytics data for chat interactions."""
    session_id: str
    user_id: str
    total_messages: int
    session_duration: int  # in seconds
    topics_discussed: List[str]
    suggestions_used: int
    actions_taken: int
    engagement_score: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'total_messages': self.total_messages,
            'session_duration': self.session_duration,
            'topics_discussed': self.topics_discussed,
            'suggestions_used': self.suggestions_used,
            'actions_taken': self.actions_taken,
            'engagement_score': self.engagement_score
        }
