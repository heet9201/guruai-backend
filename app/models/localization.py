"""
Localization models for multi-language support.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import json

class LanguageCode(Enum):
    """Supported language codes."""
    ENGLISH = "en"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    HINDI = "hi"
    CHINESE = "zh"
    MARATHI = "mr"
    GUJARATI = "gu"
    TAMIL = "ta"

class TextDirection(Enum):
    """Text direction for different languages."""
    LTR = "ltr"  # Left-to-right
    RTL = "rtl"  # Right-to-left

@dataclass
class Language:
    """Language configuration model."""
    code: str
    name: str
    native_name: str
    rtl: bool = False
    region: Optional[str] = None
    dialect: Optional[str] = None
    enabled: bool = True
    completion_percentage: float = 100.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "code": self.code,
            "name": self.name,
            "nativeName": self.native_name,
            "rtl": self.rtl,
            "region": self.region,
            "dialect": self.dialect,
            "enabled": self.enabled,
            "completionPercentage": self.completion_percentage
        }

@dataclass
class LocalizedString:
    """Localized string with pluralization support."""
    key: str
    language_code: str
    value: str
    context: Optional[str] = None
    plural_forms: Optional[Dict[str, str]] = None
    variables: Optional[List[str]] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def get_plural_form(self, count: int) -> str:
        """Get appropriate plural form based on count."""
        if not self.plural_forms:
            return self.value
            
        # Simple English pluralization rules
        if self.language_code == "en":
            if count == 1:
                return self.plural_forms.get("one", self.value)
            else:
                return self.plural_forms.get("other", self.value)
        
        # Add more language-specific pluralization rules here
        return self.value
    
    def format_with_variables(self, variables: Dict[str, Any]) -> str:
        """Format string with provided variables."""
        try:
            return self.value.format(**variables)
        except (KeyError, ValueError):
            return self.value

@dataclass
class TranslationNamespace:
    """Namespace for organizing translations."""
    name: str
    description: str
    version: str
    strings: Dict[str, Dict[str, LocalizedString]] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_string(self, key: str, language_code: str) -> Optional[LocalizedString]:
        """Get localized string for specific language."""
        language_strings = self.strings.get(language_code, {})
        return language_strings.get(key)
    
    def add_string(self, localized_string: LocalizedString):
        """Add localized string to namespace."""
        if localized_string.language_code not in self.strings:
            self.strings[localized_string.language_code] = {}
        
        self.strings[localized_string.language_code][localized_string.key] = localized_string

@dataclass
class LocalizationCache:
    """Cache configuration for localized content."""
    language_code: str
    namespace: str
    version: str
    strings: Dict[str, Any]
    cached_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    
    def is_expired(self) -> bool:
        """Check if cache is expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at

@dataclass
class AITranslationRequest:
    """Request for AI-powered translation."""
    source_text: str
    source_language: str
    target_language: str
    context: Optional[str] = None
    content_type: str = "text"
    preserve_formatting: bool = True
    
@dataclass
class AITranslationResponse:
    """Response from AI translation service."""
    translated_text: str
    source_language: str
    target_language: str
    confidence_score: float
    alternatives: Optional[List[str]] = None
    detected_language: Optional[str] = None
    processing_time: Optional[float] = None

@dataclass
class PluralRule:
    """Pluralization rules for different languages."""
    language_code: str
    rule_name: str
    condition: str
    examples: List[int]
    
    @classmethod
    def get_english_rules(cls) -> List['PluralRule']:
        """Get English pluralization rules."""
        return [
            cls("en", "one", "n == 1", [1]),
            cls("en", "other", "n != 1", [0, 2, 3, 4, 5])
        ]
    
    @classmethod
    def get_hindi_rules(cls) -> List['PluralRule']:
        """Get Hindi pluralization rules."""
        return [
            cls("hi", "one", "n == 1", [1]),
            cls("hi", "other", "n != 1", [0, 2, 3, 4, 5])
        ]

# Default language configurations
DEFAULT_LANGUAGES = [
    Language("en", "English", "English", False),
    Language("es", "Spanish", "Español", False),
    Language("fr", "French", "Français", False),
    Language("de", "German", "Deutsch", False),
    Language("hi", "Hindi", "हिन्दी", False),
    Language("zh", "Chinese", "中文", False),
    Language("mr", "Marathi", "मराठी", False),
    Language("gu", "Gujarati", "ગુજરાતી", False),
    Language("ta", "Tamil", "தமிழ்", False)
]

# Common localization keys
COMMON_TRANSLATION_KEYS = {
    "common": [
        "welcome_message",
        "loading",
        "error_occurred",
        "success_message",
        "save",
        "cancel",
        "delete",
        "edit",
        "create",
        "update",
        "yes",
        "no",
        "please_wait",
        "try_again",
        "back",
        "next",
        "previous",
        "close",
        "open"
    ],
    "authentication": [
        "login",
        "logout",
        "register",
        "forgot_password",
        "reset_password",
        "email",
        "password",
        "confirm_password",
        "remember_me",
        "login_successful",
        "login_failed",
        "invalid_credentials",
        "account_created",
        "password_reset_sent"
    ],
    "chat": [
        "type_message",
        "send_message",
        "message_sent",
        "message_failed",
        "chat_history",
        "new_conversation",
        "delete_conversation",
        "typing",
        "message_count_one",
        "message_count_other"
    ],
    "files": [
        "upload_file",
        "download_file",
        "delete_file",
        "file_uploaded",
        "file_deleted",
        "file_too_large",
        "invalid_file_type",
        "upload_progress",
        "file_count_one",
        "file_count_other"
    ],
    "planning": [
        "weekly_plan",
        "daily_schedule",
        "create_plan",
        "edit_plan",
        "delete_plan",
        "plan_created",
        "plan_updated",
        "plan_deleted",
        "due_date",
        "priority",
        "completed",
        "pending"
    ]
}
