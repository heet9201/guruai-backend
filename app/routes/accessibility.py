"""
Accessibility API Routes
RESTful endpoints for accessibility settings and features.
"""

import logging
from typing import Dict, Any
from flask import Blueprint, request, jsonify, send_file
from datetime import datetime

from app.services.accessibility_service import AccessibilityService
from app.models.accessibility import FontSize, ColorBlindMode

logger = logging.getLogger(__name__)

accessibility_bp = Blueprint('accessibility', __name__)

# Initialize service
accessibility_service = AccessibilityService()

def get_current_user():
    """Placeholder function to get current user ID."""
    # In a real implementation, this would extract user ID from JWT token
    return "placeholder-user-id"

@accessibility_bp.route('/accessibility/settings', methods=['GET'])
def get_accessibility_settings():
    """Get user accessibility preferences."""
    try:
        user_id = get_current_user()
        if not user_id:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'UNAUTHORIZED',
                    'message': 'Valid authentication required'
                }
            }), 401
        
        # Get settings (using synchronous call for Flask compatibility)
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        settings = loop.run_until_complete(
            accessibility_service.get_user_settings(user_id)
        )
        
        return jsonify({
            'success': True,
            'settings': settings.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting accessibility settings: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'GET_SETTINGS_ERROR',
                'message': str(e)
            }
        }), 500

@accessibility_bp.route('/accessibility/settings', methods=['PUT'])
def update_accessibility_settings():
    """Update user accessibility preferences."""
    try:
        user_id = get_current_user()
        if not user_id:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'UNAUTHORIZED',
                    'message': 'Valid authentication required'
                }
            }), 401
        
        # Validate request data
        if not request.is_json:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_REQUEST',
                    'message': 'Request must be JSON'
                }
            }), 400
        
        settings_data = request.get_json()
        
        # Validate settings structure
        validation_error = _validate_settings_data(settings_data)
        if validation_error:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': validation_error
                }
            }), 400
        
        # Update settings
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        updated_settings = loop.run_until_complete(
            accessibility_service.update_user_settings(user_id, settings_data)
        )
        
        return jsonify({
            'success': True,
            'message': 'Accessibility settings updated successfully',
            'settings': updated_settings.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating accessibility settings: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'UPDATE_SETTINGS_ERROR',
                'message': str(e)
            }
        }), 500

@accessibility_bp.route('/accessibility/features', methods=['GET'])
def get_accessibility_features():
    """Get available accessibility features."""
    try:
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        features = loop.run_until_complete(
            accessibility_service.get_available_features()
        )
        
        return jsonify({
            'success': True,
            'features': [feature.to_dict() for feature in features]
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting accessibility features: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'GET_FEATURES_ERROR',
                'message': str(e)
            }
        }), 500

@accessibility_bp.route('/accessibility/content/adapt', methods=['POST'])
def adapt_content_for_accessibility():
    """Adapt content based on user accessibility settings."""
    try:
        user_id = get_current_user()
        if not user_id:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'UNAUTHORIZED',
                    'message': 'Valid authentication required'
                }
            }), 401
        
        if not request.is_json:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_REQUEST',
                    'message': 'Request must be JSON'
                }
            }), 400
        
        content_data = request.get_json()
        content = content_data.get('content', {})
        
        if not content:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_CONTENT',
                    'message': 'Content data is required'
                }
            }), 400
        
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Get user settings
        user_settings = loop.run_until_complete(
            accessibility_service.get_user_settings(user_id)
        )
        
        # Adapt content
        adapted_content = loop.run_until_complete(
            accessibility_service.adapt_content_for_accessibility(content, user_settings)
        )
        
        return jsonify({
            'success': True,
            'adaptedContent': adapted_content,
            'appliedSettings': user_settings.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Error adapting content: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'CONTENT_ADAPTATION_ERROR',
                'message': str(e)
            }
        }), 500

@accessibility_bp.route('/accessibility/alt-text/generate', methods=['POST'])
def generate_alternative_text():
    """Generate alternative text for visual content."""
    try:
        user_id = get_current_user()
        if not user_id:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'UNAUTHORIZED',
                    'message': 'Valid authentication required'
                }
            }), 401
        
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'NO_FILE',
                    'message': 'File is required for alt text generation'
                }
            }), 400
        
        file_obj = request.files['file']
        content_type = request.form.get('content_type', 'image')
        content_id = request.form.get('content_id', f"content_{datetime.utcnow().timestamp()}")
        
        if file_obj.filename == '':
            return jsonify({
                'success': False,
                'error': {
                    'code': 'NO_FILE_SELECTED',
                    'message': 'No file selected'
                }
            }), 400
        
        # Read file data
        file_data = file_obj.read()
        
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Get user settings
        user_settings = loop.run_until_complete(
            accessibility_service.get_user_settings(user_id)
        )
        
        # Generate alternative text
        alt_text = loop.run_until_complete(
            accessibility_service.generate_alternative_text(
                content_id, content_type, file_data, user_settings
            )
        )
        
        return jsonify({
            'success': True,
            'alternativeText': alt_text.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Error generating alternative text: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'ALT_TEXT_GENERATION_ERROR',
                'message': str(e)
            }
        }), 500

@accessibility_bp.route('/accessibility/voice/process', methods=['POST'])
def process_voice_command():
    """Process voice command for navigation and interaction."""
    try:
        user_id = get_current_user()
        if not user_id:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'UNAUTHORIZED',
                    'message': 'Valid authentication required'
                }
            }), 401
        
        # Check if audio file is present
        if 'audio' not in request.files:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'NO_AUDIO',
                    'message': 'Audio file is required'
                }
            }), 400
        
        audio_file = request.files['audio']
        command_id = request.form.get('command_id', f"cmd_{datetime.utcnow().timestamp()}")
        
        if audio_file.filename == '':
            return jsonify({
                'success': False,
                'error': {
                    'code': 'NO_AUDIO_SELECTED',
                    'message': 'No audio file selected'
                }
            }), 400
        
        # Read audio data
        audio_data = audio_file.read()
        
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Process voice command
        voice_command = loop.run_until_complete(
            accessibility_service.process_voice_command(user_id, audio_data, command_id)
        )
        
        return jsonify({
            'success': True,
            'voiceCommand': voice_command.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Error processing voice command: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'VOICE_PROCESSING_ERROR',
                'message': str(e)
            }
        }), 500

@accessibility_bp.route('/accessibility/compliance/validate', methods=['POST'])
def validate_accessibility_compliance():
    """Validate content for accessibility compliance."""
    try:
        if not request.is_json:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_REQUEST',
                    'message': 'Request must be JSON'
                }
            }), 400
        
        content_data = request.get_json()
        content = content_data.get('content', {})
        
        if not content:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_CONTENT',
                    'message': 'Content data is required'
                }
            }), 400
        
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Validate compliance
        compliance_report = loop.run_until_complete(
            accessibility_service.validate_accessibility_compliance(content)
        )
        
        return jsonify({
            'success': True,
            'complianceReport': compliance_report
        }), 200
        
    except Exception as e:
        logger.error(f"Error validating accessibility compliance: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'COMPLIANCE_VALIDATION_ERROR',
                'message': str(e)
            }
        }), 500

@accessibility_bp.route('/accessibility/audio/<audio_id>', methods=['GET'])
def get_audio_description(audio_id: str):
    """Get audio description file."""
    try:
        # In a real implementation, this would retrieve and serve audio files
        # For now, return a placeholder response
        return jsonify({
            'success': False,
            'error': {
                'code': 'NOT_IMPLEMENTED',
                'message': 'Audio description playback not yet implemented'
            }
        }), 501
        
    except Exception as e:
        logger.error(f"Error serving audio description: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'AUDIO_SERVE_ERROR',
                'message': str(e)
            }
        }), 500

@accessibility_bp.route('/accessibility/health', methods=['GET'])
def accessibility_health_check():
    """Health check for accessibility service."""
    return jsonify({
        'success': True,
        'message': 'Accessibility service is operational',
        'timestamp': datetime.utcnow().isoformat(),
        'features': {
            'settings_management': True,
            'content_adaptation': True,
            'alt_text_generation': True,
            'voice_commands': True,
            'compliance_validation': True
        }
    }), 200

def _validate_settings_data(settings_data: Dict[str, Any]) -> str:
    """Validate accessibility settings data."""
    if not isinstance(settings_data, dict):
        return "Settings data must be an object"
    
    # Validate fontSize
    if 'fontSize' in settings_data:
        valid_font_sizes = [size.value for size in FontSize]
        if settings_data['fontSize'] not in valid_font_sizes:
            return f"Invalid fontSize. Must be one of: {', '.join(valid_font_sizes)}"
    
    # Validate boolean fields
    boolean_fields = ['highContrast', 'screenReader', 'voiceNavigation', 'reducedMotion']
    for field in boolean_fields:
        if field in settings_data and not isinstance(settings_data[field], bool):
            return f"Field '{field}' must be a boolean value"
    
    # Validate colorBlindMode
    if 'colorBlindMode' in settings_data:
        valid_modes = [mode.value for mode in ColorBlindMode]
        if settings_data['colorBlindMode'] not in valid_modes:
            return f"Invalid colorBlindMode. Must be one of: {', '.join(valid_modes)}"
    
    return None  # No validation errors
