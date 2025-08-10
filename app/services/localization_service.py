"""
Localization service for multi-language support.
"""

import asyncio
import json
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import re

from app.models.localization import (
    Language, LocalizedString, TranslationNamespace, LocalizationCache,
    AITranslationRequest, AITranslationResponse, PluralRule,
    DEFAULT_LANGUAGES, COMMON_TRANSLATION_KEYS, LanguageCode
)

class LocalizationService:
    """Service for handling localization and internationalization."""
    
    def __init__(self, redis_client=None):
        """Initialize localization service."""
        self.redis_client = redis_client
        self.languages: Dict[str, Language] = {}
        self.namespaces: Dict[str, TranslationNamespace] = {}
        self.cache: Dict[str, LocalizationCache] = {}
        self.plural_rules: Dict[str, List[PluralRule]] = {}
        
        # Initialize with default languages
        self._initialize_default_languages()
        self._initialize_plural_rules()
    
    def _initialize_default_languages(self):
        """Initialize with default supported languages."""
        for lang in DEFAULT_LANGUAGES:
            self.languages[lang.code] = lang
    
    def _initialize_plural_rules(self):
        """Initialize pluralization rules for supported languages."""
        self.plural_rules["en"] = PluralRule.get_english_rules()
        self.plural_rules["hi"] = PluralRule.get_hindi_rules()
        # Add more language rules as needed
    
    async def get_supported_languages(self) -> List[Dict[str, Any]]:
        """Get list of supported languages."""
        languages = []
        for lang in self.languages.values():
            if lang.enabled:
                languages.append(lang.to_dict())
        return languages
    
    async def get_language_info(self, language_code: str) -> Optional[Language]:
        """Get specific language information."""
        return self.languages.get(language_code)
    
    async def add_language(self, language: Language) -> bool:
        """Add a new supported language."""
        try:
            self.languages[language.code] = language
            await self._invalidate_language_cache(language.code)
            return True
        except Exception as e:
            print(f"Error adding language {language.code}: {e}")
            return False
    
    async def get_localized_strings(
        self, 
        language_code: str, 
        namespace: str = "default",
        version: Optional[str] = None,
        keys: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Get localized strings for a specific language."""
        cache_key = f"strings:{language_code}:{namespace}:{version or 'latest'}"
        
        # Try cache first
        cached_strings = await self._get_cached_strings(cache_key)
        if cached_strings:
            if keys:
                return {k: v for k, v in cached_strings.items() if k in keys}
            return cached_strings
        
        # Load from database/storage
        strings = await self._load_strings_from_storage(language_code, namespace)
        
        # Filter by keys if specified
        if keys:
            strings = {k: v for k, v in strings.items() if k in keys}
        
        # Cache the result
        await self._cache_strings(cache_key, strings, ttl=3600)
        
        return strings
    
    async def add_localized_string(
        self, 
        key: str, 
        language_code: str, 
        value: str,
        context: Optional[str] = None,
        plural_forms: Optional[Dict[str, str]] = None,
        namespace: str = "default"
    ) -> bool:
        """Add or update a localized string."""
        try:
            localized_string = LocalizedString(
                key=key,
                language_code=language_code,
                value=value,
                context=context,
                plural_forms=plural_forms
            )
            
            # Add to namespace
            if namespace not in self.namespaces:
                self.namespaces[namespace] = TranslationNamespace(
                    name=namespace,
                    description=f"Namespace {namespace}",
                    version="1.0.0"
                )
            
            self.namespaces[namespace].add_string(localized_string)
            
            # Invalidate cache
            await self._invalidate_strings_cache(language_code, namespace)
            
            return True
        except Exception as e:
            print(f"Error adding localized string: {e}")
            return False
    
    async def translate_with_ai(
        self, 
        request: AITranslationRequest
    ) -> AITranslationResponse:
        """Translate text using AI service."""
        try:
            # Simulate AI translation (replace with actual AI service call)
            await asyncio.sleep(0.1)  # Simulate API call delay
            
            # Simple mock translation logic
            translations = {
                "en": {
                    "hello": {"es": "hola", "fr": "bonjour", "de": "hallo", "hi": "नमस्ते"},
                    "welcome": {"es": "bienvenido", "fr": "bienvenue", "de": "willkommen", "hi": "स्वागत"},
                    "goodbye": {"es": "adiós", "fr": "au revoir", "de": "auf wiedersehen", "hi": "अलविदा"}
                }
            }
            
            # Try to find translation
            source_word = request.source_text.lower().strip()
            translation_dict = translations.get(request.source_language, {})
            word_translations = translation_dict.get(source_word, {})
            translated_text = word_translations.get(request.target_language, request.source_text)
            
            response = AITranslationResponse(
                translated_text=translated_text,
                source_language=request.source_language,
                target_language=request.target_language,
                confidence_score=0.95 if translated_text != request.source_text else 0.1,
                alternatives=[],
                detected_language=request.source_language,
                processing_time=0.1
            )
            
            return response
        except Exception as e:
            print(f"Error in AI translation: {e}")
            return AITranslationResponse(
                translated_text=request.source_text,
                source_language=request.source_language,
                target_language=request.target_language,
                confidence_score=0.0
            )
    
    async def localize_content(
        self, 
        content: Dict[str, Any], 
        target_language: str,
        source_language: str = "en"
    ) -> Dict[str, Any]:
        """Localize entire content object using AI translation."""
        localized_content = content.copy()
        
        # Define fields that should be translated
        translatable_fields = ["title", "description", "content", "message", "text"]
        
        for field in translatable_fields:
            if field in content and isinstance(content[field], str):
                translation_request = AITranslationRequest(
                    source_text=content[field],
                    source_language=source_language,
                    target_language=target_language,
                    context=f"Content field: {field}"
                )
                
                translation_response = await self.translate_with_ai(translation_request)
                localized_content[field] = translation_response.translated_text
        
        # Add localization metadata
        localized_content["_localization"] = {
            "source_language": source_language,
            "target_language": target_language,
            "localized_at": datetime.utcnow().isoformat(),
            "fields_translated": [f for f in translatable_fields if f in content]
        }
        
        return localized_content
    
    async def get_pluralized_string(
        self, 
        key: str, 
        count: int, 
        language_code: str,
        namespace: str = "default",
        variables: Optional[Dict[str, Any]] = None
    ) -> str:
        """Get pluralized string based on count."""
        strings = await self.get_localized_strings(language_code, namespace)
        
        if key not in strings:
            return key  # Return key if translation not found
        
        string_data = strings[key]
        
        # If it's a simple string, return as is
        if isinstance(string_data, str):
            if variables:
                try:
                    return string_data.format(**variables)
                except (KeyError, ValueError):
                    return string_data
            return string_data
        
        # If it's a complex object with plural forms
        if isinstance(string_data, dict) and "plural_forms" in string_data:
            plural_forms = string_data["plural_forms"]
            
            # Determine plural form based on language rules
            plural_form = self._get_plural_form(count, language_code)
            
            # Get the appropriate plural form
            text = plural_forms.get(plural_form, string_data.get("value", key))
            
            # Apply variables
            if variables:
                variables["count"] = count
                try:
                    return text.format(**variables)
                except (KeyError, ValueError):
                    return text
            
            return text.replace("{count}", str(count))
        
        return str(string_data)
    
    def _get_plural_form(self, count: int, language_code: str) -> str:
        """Determine plural form based on count and language rules."""
        rules = self.plural_rules.get(language_code, self.plural_rules.get("en", []))
        
        for rule in rules:
            # Simple rule evaluation (in production, use proper expression evaluator)
            if rule.condition == "n == 1" and count == 1:
                return rule.rule_name
            elif rule.condition == "n != 1" and count != 1:
                return rule.rule_name
        
        return "other"  # Default fallback
    
    async def detect_language(self, text: str) -> Tuple[str, float]:
        """Detect language of given text."""
        # Simple language detection based on character patterns
        # In production, use proper language detection library
        
        # Check for specific scripts
        if re.search(r'[\u0900-\u097F]', text):  # Devanagari (Hindi)
            return "hi", 0.9
        elif re.search(r'[\u4e00-\u9fff]', text):  # Chinese characters
            return "zh", 0.9
        elif re.search(r'[\u0a80-\u0aff]', text):  # Gujarati
            return "gu", 0.9
        elif re.search(r'[\u0b80-\u0bff]', text):  # Tamil
            return "ta", 0.9
        
        # Simple word-based detection for Latin scripts
        spanish_words = ["el", "la", "de", "que", "y", "en", "un", "es", "se", "no"]
        french_words = ["le", "de", "et", "à", "un", "il", "être", "et", "en", "avoir"]
        german_words = ["der", "die", "und", "in", "den", "von", "zu", "das", "mit", "sich"]
        
        words = text.lower().split()
        
        spanish_count = sum(1 for word in words if word in spanish_words)
        french_count = sum(1 for word in words if word in french_words)
        german_count = sum(1 for word in words if word in german_words)
        
        if spanish_count > 0:
            return "es", min(0.8, spanish_count / len(words))
        elif french_count > 0:
            return "fr", min(0.8, french_count / len(words))
        elif german_count > 0:
            return "de", min(0.8, german_count / len(words))
        
        return "en", 0.5  # Default to English
    
    async def get_rtl_languages(self) -> List[str]:
        """Get list of RTL (right-to-left) languages."""
        rtl_languages = []
        for lang in self.languages.values():
            if lang.rtl:
                rtl_languages.append(lang.code)
        return rtl_languages
    
    async def validate_translation_completeness(
        self, 
        language_code: str,
        namespace: str = "default"
    ) -> Dict[str, Any]:
        """Validate translation completeness for a language."""
        try:
            # Get English strings as baseline
            english_strings = await self.get_localized_strings("en", namespace)
            target_strings = await self.get_localized_strings(language_code, namespace)
            
            total_keys = len(english_strings)
            translated_keys = len(target_strings)
            missing_keys = set(english_strings.keys()) - set(target_strings.keys())
            
            completion_percentage = (translated_keys / total_keys * 100) if total_keys > 0 else 0
            
            return {
                "language_code": language_code,
                "namespace": namespace,
                "total_keys": total_keys,
                "translated_keys": translated_keys,
                "missing_keys": list(missing_keys),
                "completion_percentage": completion_percentage,
                "is_complete": len(missing_keys) == 0
            }
        except Exception as e:
            print(f"Error validating translation completeness: {e}")
            return {
                "language_code": language_code,
                "namespace": namespace,
                "error": str(e)
            }
    
    async def _get_cached_strings(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get strings from cache."""
        if self.redis_client:
            try:
                cached_data = await self.redis_client.get(cache_key)
                if cached_data:
                    return json.loads(cached_data)
            except Exception as e:
                print(f"Cache read error: {e}")
        
        # Check memory cache
        if cache_key in self.cache:
            cache_entry = self.cache[cache_key]
            if isinstance(cache_entry, dict) and "strings" in cache_entry:
                return cache_entry["strings"]
            elif hasattr(cache_entry, 'strings'):
                return cache_entry.strings
        
        return None
    
    async def _cache_strings(self, cache_key: str, strings: Dict[str, Any], ttl: int = 3600):
        """Cache strings with TTL."""
        try:
            if self.redis_client:
                await self.redis_client.setex(cache_key, ttl, json.dumps(strings))
            else:
                # Fallback to memory cache
                self.cache[cache_key] = LocalizationCache(
                    language_code="",
                    namespace="",
                    version="",
                    strings=strings,
                    expires_at=datetime.utcnow() + timedelta(seconds=ttl)
                )
        except Exception as e:
            print(f"Cache write error: {e}")
    
    async def _load_strings_from_storage(
        self, 
        language_code: str, 
        namespace: str
    ) -> Dict[str, Any]:
        """Load strings from persistent storage."""
        # Mock implementation - in production, load from database
        mock_strings = {
            "en": {
                "welcome_message": "Welcome to GuruAI",
                "loading": "Loading...",
                "error_occurred": "An error occurred",
                "success_message": "Operation completed successfully",
                "save": "Save",
                "cancel": "Cancel",
                "message_count": {
                    "value": "You have {count} messages",
                    "plural_forms": {
                        "one": "You have {count} message",
                        "other": "You have {count} messages"
                    }
                }
            },
            "hi": {
                "welcome_message": "गुरुएआई में आपका स्वागत है",
                "loading": "लोड हो रहा है...",
                "error_occurred": "एक त्रुटि हुई",
                "success_message": "ऑपरेशन सफलतापूर्वक पूर्ण हुआ",
                "save": "सेव करें",
                "cancel": "रद्द करें"
            },
            "es": {
                "welcome_message": "Bienvenido a GuruAI",
                "loading": "Cargando...",
                "error_occurred": "Ocurrió un error",
                "success_message": "Operación completada exitosamente",
                "save": "Guardar",
                "cancel": "Cancelar"
            }
        }
        
        return mock_strings.get(language_code, mock_strings.get("en", {}))
    
    async def _invalidate_language_cache(self, language_code: str):
        """Invalidate cache for a specific language."""
        if self.redis_client:
            try:
                pattern = f"strings:{language_code}:*"
                keys = await self.redis_client.keys(pattern)
                if keys:
                    await self.redis_client.delete(*keys)
            except Exception as e:
                print(f"Cache invalidation error: {e}")
    
    async def _invalidate_strings_cache(self, language_code: str, namespace: str):
        """Invalidate cache for specific language and namespace."""
        if self.redis_client:
            try:
                pattern = f"strings:{language_code}:{namespace}:*"
                keys = await self.redis_client.keys(pattern)
                if keys:
                    await self.redis_client.delete(*keys)
            except Exception as e:
                print(f"Cache invalidation error: {e}")
    
    async def export_translations(
        self, 
        language_code: str, 
        namespace: str = "default",
        format_type: str = "json"
    ) -> str:
        """Export translations in specified format."""
        strings = await self.get_localized_strings(language_code, namespace)
        
        if format_type == "json":
            return json.dumps(strings, ensure_ascii=False, indent=2)
        elif format_type == "csv":
            # Simple CSV export
            lines = ["key,value"]
            for key, value in strings.items():
                if isinstance(value, str):
                    lines.append(f'"{key}","{value}"')
                else:
                    lines.append(f'"{key}","{json.dumps(value)}"')
            return "\n".join(lines)
        
        return json.dumps(strings, ensure_ascii=False, indent=2)
    
    async def import_translations(
        self, 
        language_code: str, 
        translations_data: str,
        format_type: str = "json",
        namespace: str = "default"
    ) -> bool:
        """Import translations from formatted data."""
        try:
            if format_type == "json":
                translations = json.loads(translations_data)
            else:
                # Handle other formats as needed
                translations = json.loads(translations_data)
            
            # Add each translation
            for key, value in translations.items():
                if isinstance(value, str):
                    await self.add_localized_string(key, language_code, value, namespace=namespace)
                elif isinstance(value, dict) and "value" in value:
                    await self.add_localized_string(
                        key, 
                        language_code, 
                        value["value"],
                        context=value.get("context"),
                        plural_forms=value.get("plural_forms"),
                        namespace=namespace
                    )
            
            return True
        except Exception as e:
            print(f"Error importing translations: {e}")
            return False
