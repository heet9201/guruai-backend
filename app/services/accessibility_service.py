"""
Accessibility Service
Handles user accessibility preferences, alternative content generation,
and assistive technology integration.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import base64
import hashlib

from app.models.accessibility import (
    AccessibilitySettings, FontSize, ColorBlindMode,
    AlternativeText, VoiceCommand, AccessibilityFeature
)

logger = logging.getLogger(__name__)

class AccessibilityService:
    """Service for managing accessibility features and settings."""
    
    def __init__(self):
        """Initialize accessibility service."""
        # In-memory storage for demonstration (replace with database)
        self.user_settings: Dict[str, AccessibilitySettings] = {}
        self.alt_text_cache: Dict[str, AlternativeText] = {}
        self.voice_commands: Dict[str, VoiceCommand] = {}
        
    async def get_user_settings(self, user_id: str) -> AccessibilitySettings:
        """Get accessibility settings for a user."""
        try:
            if user_id in self.user_settings:
                return self.user_settings[user_id]
            
            # Return default settings if none exist
            default_settings = AccessibilitySettings(
                user_id=user_id,
                created_at=datetime.utcnow()
            )
            self.user_settings[user_id] = default_settings
            return default_settings
            
        except Exception as e:
            logger.error(f"Error getting accessibility settings for user {user_id}: {str(e)}")
            raise
    
    async def update_user_settings(self, user_id: str, settings_data: Dict[str, Any]) -> AccessibilitySettings:
        """Update accessibility settings for a user."""
        try:
            current_settings = await self.get_user_settings(user_id)
            
            # Update settings with new data
            if 'fontSize' in settings_data:
                current_settings.font_size = FontSize(settings_data['fontSize'])
            if 'highContrast' in settings_data:
                current_settings.high_contrast = settings_data['highContrast']
            if 'screenReader' in settings_data:
                current_settings.screen_reader = settings_data['screenReader']
            if 'voiceNavigation' in settings_data:
                current_settings.voice_navigation = settings_data['voiceNavigation']
            if 'reducedMotion' in settings_data:
                current_settings.reduced_motion = settings_data['reducedMotion']
            if 'colorBlindMode' in settings_data:
                current_settings.color_blind_mode = ColorBlindMode(settings_data['colorBlindMode'])
            
            current_settings.updated_at = datetime.utcnow()
            self.user_settings[user_id] = current_settings
            
            logger.info(f"Updated accessibility settings for user {user_id}")
            return current_settings
            
        except Exception as e:
            logger.error(f"Error updating accessibility settings for user {user_id}: {str(e)}")
            raise
    
    async def generate_alternative_text(self, content_id: str, content_type: str, 
                                      content_data: bytes, user_settings: AccessibilitySettings) -> AlternativeText:
        """Generate alternative text for visual content."""
        try:
            # Check cache first
            cache_key = f"{content_id}_{content_type}"
            if cache_key in self.alt_text_cache:
                return self.alt_text_cache[cache_key]
            
            # Generate alternative text based on content type
            alt_text = await self._generate_alt_text_content(content_type, content_data)
            detailed_description = None
            audio_description_url = None
            
            # Generate detailed description for screen readers
            if user_settings.screen_reader:
                detailed_description = await self._generate_detailed_description(content_type, content_data)
            
            # Generate audio description if needed
            if user_settings.voice_navigation:
                audio_description_url = await self._generate_audio_description(alt_text, detailed_description)
            
            alt_text_obj = AlternativeText(
                content_id=content_id,
                content_type=content_type,
                alt_text=alt_text,
                detailed_description=detailed_description,
                audio_description_url=audio_description_url,
                created_at=datetime.utcnow()
            )
            
            # Cache the result
            self.alt_text_cache[cache_key] = alt_text_obj
            
            logger.info(f"Generated alternative text for content {content_id}")
            return alt_text_obj
            
        except Exception as e:
            logger.error(f"Error generating alternative text for content {content_id}: {str(e)}")
            raise
    
    async def _generate_alt_text_content(self, content_type: str, content_data: bytes) -> str:
        """Generate alternative text based on content type."""
        if content_type == 'image':
            # In a real implementation, this would use AI vision models
            return "Image content description generated by AI vision model"
        elif content_type == 'chart':
            return "Chart showing data visualization with accessible data summary"
        elif content_type == 'diagram':
            return "Diagram illustration with structural description"
        else:
            return f"Visual content of type {content_type}"
    
    async def _generate_detailed_description(self, content_type: str, content_data: bytes) -> str:
        """Generate detailed description for screen readers."""
        if content_type == 'image':
            return "Detailed image description including objects, people, colors, and spatial relationships for screen reader users."
        elif content_type == 'chart':
            return "Comprehensive chart description including data points, trends, axes labels, and key insights."
        elif content_type == 'diagram':
            return "Structural diagram description explaining components, connections, and relationships."
        else:
            return f"Detailed description of {content_type} content for assistive technology."
    
    async def _generate_audio_description(self, alt_text: str, detailed_description: Optional[str]) -> str:
        """Generate audio description URL."""
        # In a real implementation, this would use text-to-speech services
        text_to_speak = detailed_description if detailed_description else alt_text
        audio_id = hashlib.md5(text_to_speak.encode()).hexdigest()
        return f"/api/v1/accessibility/audio/{audio_id}"
    
    async def process_voice_command(self, user_id: str, audio_data: bytes, 
                                  command_id: str) -> VoiceCommand:
        """Process voice command for navigation and interaction."""
        try:
            # Create voice command object
            voice_command = VoiceCommand(
                command_id=command_id,
                user_id=user_id,
                audio_data=audio_data,
                processed_at=datetime.utcnow()
            )
            
            # Transcribe audio (placeholder implementation)
            transcription = await self._transcribe_audio(audio_data)
            voice_command.transcription = transcription
            
            # Extract intent and entities
            intent, entities, confidence = await self._extract_intent(transcription)
            voice_command.intent = intent
            voice_command.entities = entities
            voice_command.confidence_score = confidence
            
            # Store command
            self.voice_commands[command_id] = voice_command
            
            logger.info(f"Processed voice command {command_id} for user {user_id}")
            return voice_command
            
        except Exception as e:
            logger.error(f"Error processing voice command {command_id}: {str(e)}")
            raise
    
    async def _transcribe_audio(self, audio_data: bytes) -> str:
        """Transcribe audio to text."""
        # In a real implementation, this would use Google Speech-to-Text
        # For now, return a placeholder
        return "Navigate to weekly planning section"
    
    async def _extract_intent(self, transcription: str) -> tuple:
        """Extract intent and entities from transcription."""
        # Simple intent detection (in production, use NLU services)
        transcription_lower = transcription.lower()
        
        if 'navigate' in transcription_lower:
            intent = 'navigation'
            entities = {'action': 'navigate'}
            confidence = 0.9
        elif 'read' in transcription_lower:
            intent = 'content_access'
            entities = {'action': 'read'}
            confidence = 0.85
        elif 'help' in transcription_lower:
            intent = 'assistance'
            entities = {'action': 'help'}
            confidence = 0.8
        else:
            intent = 'unknown'
            entities = {}
            confidence = 0.3
        
        return intent, entities, confidence
    
    async def adapt_content_for_accessibility(self, content: Dict[str, Any], 
                                            user_settings: AccessibilitySettings) -> Dict[str, Any]:
        """Adapt content based on user accessibility settings."""
        try:
            adapted_content = content.copy()
            
            # Apply font size adjustments
            if user_settings.font_size != FontSize.MEDIUM:
                adapted_content['fontSize'] = user_settings.font_size.value
            
            # Apply high contrast mode
            if user_settings.high_contrast:
                adapted_content['theme'] = 'high-contrast'
                adapted_content['colors'] = {
                    'background': '#000000',
                    'text': '#FFFFFF',
                    'accent': '#FFFF00'
                }
            
            # Apply color blind adaptations
            if user_settings.color_blind_mode != ColorBlindMode.NONE:
                adapted_content['colorScheme'] = self._get_colorblind_scheme(user_settings.color_blind_mode)
            
            # Apply reduced motion
            if user_settings.reduced_motion:
                adapted_content['animations'] = False
                adapted_content['transitions'] = 'none'
            
            # Add screen reader specific content
            if user_settings.screen_reader:
                adapted_content['screenReaderOptimized'] = True
                adapted_content['semanticStructure'] = True
            
            return adapted_content
            
        except Exception as e:
            logger.error(f"Error adapting content for accessibility: {str(e)}")
            return content
    
    def _get_colorblind_scheme(self, color_blind_mode: ColorBlindMode) -> Dict[str, str]:
        """Get color scheme for color blind users."""
        schemes = {
            ColorBlindMode.PROTANOPIA: {
                'primary': '#0066CC',    # Blue
                'secondary': '#FFD700',  # Gold
                'accent': '#FF6600',     # Orange
                'warning': '#663399'     # Purple
            },
            ColorBlindMode.DEUTERANOPIA: {
                'primary': '#0066CC',    # Blue
                'secondary': '#FFD700',  # Gold  
                'accent': '#FF6600',     # Orange
                'warning': '#663399'     # Purple
            },
            ColorBlindMode.TRITANOPIA: {
                'primary': '#CC0066',    # Magenta
                'secondary': '#FF6600',  # Orange
                'accent': '#FFD700',     # Gold
                'warning': '#000080'     # Navy
            }
        }
        return schemes.get(color_blind_mode, {})
    
    async def get_available_features(self) -> List[AccessibilityFeature]:
        """Get list of available accessibility features."""
        features = [
            AccessibilityFeature(
                feature_name="font_size",
                enabled=True,
                settings={'options': ['small', 'medium', 'large', 'xlarge']},
                description="Adjustable font sizes for better readability"
            ),
            AccessibilityFeature(
                feature_name="high_contrast",
                enabled=True,
                settings={'contrast_ratio': '7:1'},
                description="High contrast mode for improved visibility"
            ),
            AccessibilityFeature(
                feature_name="screen_reader",
                enabled=True,
                settings={'semantic_markup': True, 'aria_labels': True},
                description="Screen reader compatibility and optimization"
            ),
            AccessibilityFeature(
                feature_name="voice_navigation",
                enabled=True,
                settings={'language': 'en-US', 'confidence_threshold': 0.7},
                description="Voice command navigation and control"
            ),
            AccessibilityFeature(
                feature_name="color_blind_support",
                enabled=True,
                settings={'modes': ['protanopia', 'deuteranopia', 'tritanopia']},
                description="Color blindness accommodation"
            ),
            AccessibilityFeature(
                feature_name="reduced_motion",
                enabled=True,
                settings={'disable_animations': True, 'minimal_transitions': True},
                description="Reduced motion for users sensitive to movement"
            )
        ]
        return features
    
    async def validate_accessibility_compliance(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Validate content for accessibility compliance."""
        compliance_report = {
            'wcag_aa_compliant': True,
            'issues': [],
            'recommendations': [],
            'score': 100
        }
        
        # Check for alt text on images
        if 'images' in content:
            for image in content['images']:
                if not image.get('alt_text'):
                    compliance_report['issues'].append('Missing alt text for image')
                    compliance_report['wcag_aa_compliant'] = False
                    compliance_report['score'] -= 10
        
        # Check color contrast
        if 'colors' in content:
            # Simplified contrast check (in production, use proper contrast calculation)
            if content['colors'].get('contrast_ratio', 4.5) < 4.5:
                compliance_report['issues'].append('Insufficient color contrast')
                compliance_report['recommendations'].append('Increase contrast ratio to at least 4.5:1')
                compliance_report['score'] -= 15
        
        # Check for semantic markup
        if not content.get('semantic_structure'):
            compliance_report['recommendations'].append('Add semantic HTML structure for better screen reader support')
            compliance_report['score'] -= 5
        
        return compliance_report
