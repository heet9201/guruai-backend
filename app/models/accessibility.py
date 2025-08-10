"""
Accessibility Settings Models
Data structures for user accessibility preferences and features.
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional
from enum import Enum
from datetime import datetime

class FontSize(Enum):
    """Font size options for accessibility."""
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    XLARGE = "xlarge"

class ColorBlindMode(Enum):
    """Color blindness accommodation modes."""
    NONE = "none"
    PROTANOPIA = "protanopia"      # Red-blind
    DEUTERANOPIA = "deuteranopia"  # Green-blind
    TRITANOPIA = "tritanopia"      # Blue-blind

@dataclass
class AccessibilitySettings:
    """User accessibility preferences."""
    user_id: str
    font_size: FontSize = FontSize.MEDIUM
    high_contrast: bool = False
    screen_reader: bool = False
    voice_navigation: bool = False
    reduced_motion: bool = False
    color_blind_mode: ColorBlindMode = ColorBlindMode.NONE
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            'user_id': self.user_id,
            'fontSize': self.font_size.value,
            'highContrast': self.high_contrast,
            'screenReader': self.screen_reader,
            'voiceNavigation': self.voice_navigation,
            'reducedMotion': self.reduced_motion,
            'colorBlindMode': self.color_blind_mode.value,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AccessibilitySettings':
        """Create from dictionary data."""
        return cls(
            user_id=data['user_id'],
            font_size=FontSize(data.get('fontSize', 'medium')),
            high_contrast=data.get('highContrast', False),
            screen_reader=data.get('screenReader', False),
            voice_navigation=data.get('voiceNavigation', False),
            reduced_motion=data.get('reducedMotion', False),
            color_blind_mode=ColorBlindMode(data.get('colorBlindMode', 'none')),
            created_at=datetime.fromisoformat(data['createdAt']) if data.get('createdAt') else None,
            updated_at=datetime.fromisoformat(data['updatedAt']) if data.get('updatedAt') else None
        )

@dataclass
class AlternativeText:
    """Alternative text for images and visual content."""
    content_id: str
    content_type: str  # 'image', 'chart', 'diagram', etc.
    alt_text: str
    detailed_description: Optional[str] = None
    audio_description_url: Optional[str] = None
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            'contentId': self.content_id,
            'contentType': self.content_type,
            'altText': self.alt_text,
            'detailedDescription': self.detailed_description,
            'audioDescriptionUrl': self.audio_description_url,
            'createdAt': self.created_at.isoformat() if self.created_at else None
        }

@dataclass
class VoiceCommand:
    """Voice command processing data."""
    command_id: str
    user_id: str
    audio_data: bytes
    transcription: Optional[str] = None
    intent: Optional[str] = None
    entities: Optional[Dict[str, Any]] = None
    confidence_score: Optional[float] = None
    processed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            'commandId': self.command_id,
            'userId': self.user_id,
            'transcription': self.transcription,
            'intent': self.intent,
            'entities': self.entities,
            'confidenceScore': self.confidence_score,
            'processedAt': self.processed_at.isoformat() if self.processed_at else None
        }

@dataclass
class AccessibilityFeature:
    """Accessibility feature configuration."""
    feature_name: str
    enabled: bool
    settings: Dict[str, Any]
    description: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            'featureName': self.feature_name,
            'enabled': self.enabled,
            'settings': self.settings,
            'description': self.description
        }
