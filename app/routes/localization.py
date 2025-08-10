"""
Localization API routes for multi-language support.
"""

from flask import Blueprint, request, jsonify, current_app
from typing import Dict, Any, Optional
import asyncio
from functools import wraps

from app.services.localization_service import LocalizationService
from app.models.localization import AITranslationRequest

# Create blueprint
localization_bp = Blueprint('localization', __name__, url_prefix='/api/v1/localization')

# Initialize service (would be injected in production)
localization_service = LocalizationService()

def async_route(f):
    """Decorator to handle async routes in Flask."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapper

@localization_bp.route('/strings', methods=['GET'])
@async_route
async def get_localized_strings():
    """
    Get localized strings for a specific language.
    
    Query Parameters:
    - language: Language code (en, es, fr, de, hi, zh, mr, gu, ta)
    - version: Version string for cache busting (optional)
    - namespace: Translation namespace (optional, default: 'default')
    - keys: Comma-separated list of specific keys to retrieve (optional)
    """
    try:
        # Get query parameters
        language = request.args.get('language', 'en')
        version = request.args.get('version')
        namespace = request.args.get('namespace', 'default')
        keys_param = request.args.get('keys')
        
        # Validate language
        supported_languages = await localization_service.get_supported_languages()
        language_codes = [lang['code'] for lang in supported_languages]
        
        if language not in language_codes:
            return jsonify({
                "success": False,
                "error": {
                    "code": "UNSUPPORTED_LANGUAGE",
                    "message": f"Language '{language}' is not supported",
                    "supported_languages": language_codes
                }
            }), 400
        
        # Parse keys if provided
        keys = None
        if keys_param:
            keys = [key.strip() for key in keys_param.split(',') if key.strip()]
        
        # Get localized strings
        strings = await localization_service.get_localized_strings(
            language_code=language,
            namespace=namespace,
            version=version,
            keys=keys
        )
        
        # Get language info
        language_info = await localization_service.get_language_info(language)
        
        response_data = {
            "success": True,
            "language": language,
            "namespace": namespace,
            "version": version or "latest",
            "strings": strings,
            "count": len(strings),
            "language_info": language_info.to_dict() if language_info else None
        }
        
        # Add cache headers for better performance
        response = jsonify(response_data)
        response.headers['Cache-Control'] = 'public, max-age=3600'
        response.headers['ETag'] = f'"{language}-{namespace}-{version or "latest"}"'
        
        return response
        
    except Exception as e:
        current_app.logger.error(f"Error getting localized strings: {e}")
        return jsonify({
            "success": False,
            "error": {
                "code": "LOCALIZATION_ERROR",
                "message": "Failed to retrieve localized strings",
                "details": str(e)
            }
        }), 500

@localization_bp.route('/languages', methods=['GET'])
@async_route
async def get_supported_languages():
    """
    Get list of supported languages with their metadata.
    """
    try:
        languages = await localization_service.get_supported_languages()
        
        response_data = {
            "success": True,
            "languages": languages,
            "count": len(languages)
        }
        
        # Add cache headers
        response = jsonify(response_data)
        response.headers['Cache-Control'] = 'public, max-age=7200'  # 2 hours
        
        return response
        
    except Exception as e:
        current_app.logger.error(f"Error getting supported languages: {e}")
        return jsonify({
            "success": False,
            "error": {
                "code": "LANGUAGES_ERROR",
                "message": "Failed to retrieve supported languages",
                "details": str(e)
            }
        }), 500

@localization_bp.route('/translate', methods=['POST'])
@async_route
async def translate_content():
    """
    Translate content using AI translation service.
    
    Request Body:
    {
        "text": "Text to translate",
        "sourceLanguage": "en",
        "targetLanguage": "es",
        "context": "Optional context",
        "contentType": "text|html|markdown"
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'text' not in data:
            return jsonify({
                "success": False,
                "error": {
                    "code": "MISSING_TEXT",
                    "message": "Text to translate is required"
                }
            }), 400
        
        # Validate required fields
        text = data.get('text', '').strip()
        source_language = data.get('sourceLanguage', 'en')
        target_language = data.get('targetLanguage')
        
        if not text:
            return jsonify({
                "success": False,
                "error": {
                    "code": "EMPTY_TEXT",
                    "message": "Text cannot be empty"
                }
            }), 400
        
        if not target_language:
            return jsonify({
                "success": False,
                "error": {
                    "code": "MISSING_TARGET_LANGUAGE",
                    "message": "Target language is required"
                }
            }), 400
        
        # Validate languages
        supported_languages = await localization_service.get_supported_languages()
        language_codes = [lang['code'] for lang in supported_languages]
        
        if source_language not in language_codes:
            return jsonify({
                "success": False,
                "error": {
                    "code": "UNSUPPORTED_SOURCE_LANGUAGE",
                    "message": f"Source language '{source_language}' is not supported"
                }
            }), 400
        
        if target_language not in language_codes:
            return jsonify({
                "success": False,
                "error": {
                    "code": "UNSUPPORTED_TARGET_LANGUAGE",
                    "message": f"Target language '{target_language}' is not supported"
                }
            }), 400
        
        # Create translation request
        translation_request = AITranslationRequest(
            source_text=text,
            source_language=source_language,
            target_language=target_language,
            context=data.get('context'),
            content_type=data.get('contentType', 'text'),
            preserve_formatting=data.get('preserveFormatting', True)
        )
        
        # Perform translation
        translation_response = await localization_service.translate_with_ai(translation_request)
        
        return jsonify({
            "success": True,
            "translation": {
                "originalText": text,
                "translatedText": translation_response.translated_text,
                "sourceLanguage": translation_response.source_language,
                "targetLanguage": translation_response.target_language,
                "confidenceScore": translation_response.confidence_score,
                "alternatives": translation_response.alternatives,
                "detectedLanguage": translation_response.detected_language,
                "processingTime": translation_response.processing_time
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error translating content: {e}")
        return jsonify({
            "success": False,
            "error": {
                "code": "TRANSLATION_ERROR",
                "message": "Failed to translate content",
                "details": str(e)
            }
        }), 500

@localization_bp.route('/content/localize', methods=['POST'])
@async_route
async def localize_content():
    """
    Localize entire content object with multiple fields.
    
    Request Body:
    {
        "content": {
            "title": "Content title",
            "description": "Content description",
            "body": "Main content"
        },
        "targetLanguage": "es",
        "sourceLanguage": "en"
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'content' not in data:
            return jsonify({
                "success": False,
                "error": {
                    "code": "MISSING_CONTENT",
                    "message": "Content object is required"
                }
            }), 400
        
        content = data.get('content')
        target_language = data.get('targetLanguage')
        source_language = data.get('sourceLanguage', 'en')
        
        if not target_language:
            return jsonify({
                "success": False,
                "error": {
                    "code": "MISSING_TARGET_LANGUAGE",
                    "message": "Target language is required"
                }
            }), 400
        
        # Validate languages
        supported_languages = await localization_service.get_supported_languages()
        language_codes = [lang['code'] for lang in supported_languages]
        
        if target_language not in language_codes:
            return jsonify({
                "success": False,
                "error": {
                    "code": "UNSUPPORTED_TARGET_LANGUAGE",
                    "message": f"Target language '{target_language}' is not supported"
                }
            }), 400
        
        # Localize content
        localized_content = await localization_service.localize_content(
            content=content,
            target_language=target_language,
            source_language=source_language
        )
        
        return jsonify({
            "success": True,
            "localizedContent": localized_content
        })
        
    except Exception as e:
        current_app.logger.error(f"Error localizing content: {e}")
        return jsonify({
            "success": False,
            "error": {
                "code": "LOCALIZATION_ERROR",
                "message": "Failed to localize content",
                "details": str(e)
            }
        }), 500

@localization_bp.route('/detect', methods=['POST'])
@async_route
async def detect_language():
    """
    Detect language of provided text.
    
    Request Body:
    {
        "text": "Text to analyze"
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'text' not in data:
            return jsonify({
                "success": False,
                "error": {
                    "code": "MISSING_TEXT",
                    "message": "Text is required for language detection"
                }
            }), 400
        
        text = data.get('text', '').strip()
        
        if not text:
            return jsonify({
                "success": False,
                "error": {
                    "code": "EMPTY_TEXT",
                    "message": "Text cannot be empty"
                }
            }), 400
        
        # Detect language
        detected_language, confidence = await localization_service.detect_language(text)
        
        # Get language info
        language_info = await localization_service.get_language_info(detected_language)
        
        return jsonify({
            "success": True,
            "detection": {
                "text": text,
                "detectedLanguage": detected_language,
                "confidence": confidence,
                "languageInfo": language_info.to_dict() if language_info else None
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error detecting language: {e}")
        return jsonify({
            "success": False,
            "error": {
                "code": "DETECTION_ERROR",
                "message": "Failed to detect language",
                "details": str(e)
            }
        }), 500

@localization_bp.route('/pluralize', methods=['POST'])
@async_route
async def get_pluralized_string():
    """
    Get pluralized string based on count.
    
    Request Body:
    {
        "key": "message_count",
        "count": 5,
        "language": "en",
        "variables": {"user": "John"}
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'key' not in data or 'count' not in data:
            return jsonify({
                "success": False,
                "error": {
                    "code": "MISSING_PARAMETERS",
                    "message": "Key and count are required"
                }
            }), 400
        
        key = data.get('key')
        count = data.get('count')
        language = data.get('language', 'en')
        variables = data.get('variables', {})
        namespace = data.get('namespace', 'default')
        
        # Validate count is integer
        try:
            count = int(count)
        except (ValueError, TypeError):
            return jsonify({
                "success": False,
                "error": {
                    "code": "INVALID_COUNT",
                    "message": "Count must be a valid integer"
                }
            }), 400
        
        # Get pluralized string
        pluralized_string = await localization_service.get_pluralized_string(
            key=key,
            count=count,
            language_code=language,
            namespace=namespace,
            variables=variables
        )
        
        return jsonify({
            "success": True,
            "result": {
                "key": key,
                "count": count,
                "language": language,
                "pluralizedString": pluralized_string,
                "variables": variables
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting pluralized string: {e}")
        return jsonify({
            "success": False,
            "error": {
                "code": "PLURALIZATION_ERROR",
                "message": "Failed to get pluralized string",
                "details": str(e)
            }
        }), 500

@localization_bp.route('/rtl', methods=['GET'])
@async_route
async def get_rtl_languages():
    """Get list of right-to-left languages."""
    try:
        rtl_languages = await localization_service.get_rtl_languages()
        
        return jsonify({
            "success": True,
            "rtlLanguages": rtl_languages,
            "count": len(rtl_languages)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting RTL languages: {e}")
        return jsonify({
            "success": False,
            "error": {
                "code": "RTL_ERROR",
                "message": "Failed to get RTL languages",
                "details": str(e)
            }
        }), 500

@localization_bp.route('/validation/<language_code>', methods=['GET'])
@async_route
async def validate_translation_completeness(language_code):
    """
    Validate translation completeness for a language.
    
    Path Parameters:
    - language_code: Language to validate
    
    Query Parameters:
    - namespace: Translation namespace (optional, default: 'default')
    """
    try:
        namespace = request.args.get('namespace', 'default')
        
        # Validate translation completeness
        validation_result = await localization_service.validate_translation_completeness(
            language_code=language_code,
            namespace=namespace
        )
        
        return jsonify({
            "success": True,
            "validation": validation_result
        })
        
    except Exception as e:
        current_app.logger.error(f"Error validating translations: {e}")
        return jsonify({
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Failed to validate translation completeness",
                "details": str(e)
            }
        }), 500

@localization_bp.route('/export/<language_code>', methods=['GET'])
@async_route
async def export_translations(language_code):
    """
    Export translations for a language.
    
    Path Parameters:
    - language_code: Language to export
    
    Query Parameters:
    - namespace: Translation namespace (optional, default: 'default')
    - format: Export format (json|csv, default: json)
    """
    try:
        namespace = request.args.get('namespace', 'default')
        format_type = request.args.get('format', 'json')
        
        if format_type not in ['json', 'csv']:
            return jsonify({
                "success": False,
                "error": {
                    "code": "INVALID_FORMAT",
                    "message": "Format must be 'json' or 'csv'"
                }
            }), 400
        
        # Export translations
        exported_data = await localization_service.export_translations(
            language_code=language_code,
            namespace=namespace,
            format_type=format_type
        )
        
        # Set appropriate content type
        if format_type == 'csv':
            response = current_app.response_class(
                exported_data,
                mimetype='text/csv',
                headers={'Content-Disposition': f'attachment; filename=translations_{language_code}_{namespace}.csv'}
            )
        else:
            response = current_app.response_class(
                exported_data,
                mimetype='application/json',
                headers={'Content-Disposition': f'attachment; filename=translations_{language_code}_{namespace}.json'}
            )
        
        return response
        
    except Exception as e:
        current_app.logger.error(f"Error exporting translations: {e}")
        return jsonify({
            "success": False,
            "error": {
                "code": "EXPORT_ERROR",
                "message": "Failed to export translations",
                "details": str(e)
            }
        }), 500

@localization_bp.route('/import/<language_code>', methods=['POST'])
@async_route
async def import_translations(language_code):
    """
    Import translations for a language.
    
    Path Parameters:
    - language_code: Target language
    
    Request Body:
    {
        "translations": "JSON string or object with translations",
        "format": "json|csv",
        "namespace": "default"
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'translations' not in data:
            return jsonify({
                "success": False,
                "error": {
                    "code": "MISSING_TRANSLATIONS",
                    "message": "Translations data is required"
                }
            }), 400
        
        translations_data = data.get('translations')
        format_type = data.get('format', 'json')
        namespace = data.get('namespace', 'default')
        
        # Convert translations to string if it's an object
        if isinstance(translations_data, dict):
            import json
            translations_data = json.dumps(translations_data)
        
        # Import translations
        success = await localization_service.import_translations(
            language_code=language_code,
            translations_data=translations_data,
            format_type=format_type,
            namespace=namespace
        )
        
        if success:
            return jsonify({
                "success": True,
                "message": f"Translations imported successfully for {language_code}",
                "language": language_code,
                "namespace": namespace
            })
        else:
            return jsonify({
                "success": False,
                "error": {
                    "code": "IMPORT_FAILED",
                    "message": "Failed to import translations"
                }
            }), 500
        
    except Exception as e:
        current_app.logger.error(f"Error importing translations: {e}")
        return jsonify({
            "success": False,
            "error": {
                "code": "IMPORT_ERROR",
                "message": "Failed to import translations",
                "details": str(e)
            }
        }), 500

# Error handlers
@localization_bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({
        "success": False,
        "error": {
            "code": "ENDPOINT_NOT_FOUND",
            "message": "Localization endpoint not found",
            "available_endpoints": [
                "/strings",
                "/languages", 
                "/translate",
                "/content/localize",
                "/detect",
                "/pluralize",
                "/rtl",
                "/validation/<language_code>",
                "/export/<language_code>",
                "/import/<language_code>"
            ]
        }
    }), 404

@localization_bp.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({
        "success": False,
        "error": {
            "code": "INTERNAL_SERVER_ERROR",
            "message": "Internal server error in localization service"
        }
    }), 500
