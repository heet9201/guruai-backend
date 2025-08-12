from flask import Blueprint, request, jsonify, g
from app.services.ai_service import AIService
from app.utils.middleware import require_json, validate_required_fields
from app.utils.auth_middleware import token_required
from app.services.vertex_ai_service import QuotaExceededError, VertexAIError
from app.services.dashboard_service import DashboardService, ActivityType
import logging
import base64
import time

logger = logging.getLogger(__name__)
ai_bp = Blueprint('ai', __name__)
ai_service = AIService()
dashboard_service = DashboardService()

@ai_bp.route('/chat', methods=['POST'])
@token_required
@require_json
@validate_required_fields(['message'])
def chat():
    """Handle chat requests with AI using Vertex AI Gemini Pro."""
    start_time = time.time()
    
    try:
        data = request.get_json()
        message = data['message']
        user_id = g.current_user.get('id')
        context = data.get('context', {})
        
        # Additional parameters for Gemini Pro
        max_tokens = data.get('max_tokens', 1000)
        temperature = data.get('temperature', 0.7)
        
        logger.info(f"Chat request from user {user_id}: {message[:50]}...")
        
        response = ai_service.generate_response(
            message=message,
            user_id=user_id,
            context=context,
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        # Calculate duration and track activity
        duration_seconds = int(time.time() - start_time)
        dashboard_service.track_activity(
            user_id=user_id,
            activity_type=ActivityType.CHAT,
            title="AI Chat Session",
            description=f"Chat about: {message[:100]}...",
            metadata={
                'feature': 'ai_chat',
                'message_length': len(message),
                'response_length': len(response) if response else 0,
                'temperature': temperature,
                'max_tokens': max_tokens
            },
            duration_seconds=duration_seconds
        )
        
        return jsonify({
            'response': response,
            'status': 'success',
            'user_id': user_id
        })
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        
        if isinstance(e, QuotaExceededError):
            return jsonify({
                'error': 'Quota exceeded',
                'message': 'API quota limit reached. Please try again later.',
                'retry_after': 3600  # 1 hour
            }), 429
        
        return jsonify({
            'error': 'Failed to generate response',
            'message': str(e)
        }), 500

@ai_bp.route('/vision', methods=['POST'])
@token_required
@require_json
@validate_required_fields(['image_data'])
def vision():
    """Simple vision analysis endpoint for compatibility."""
    start_time = time.time()
    
    try:
        data = request.get_json()
        image_data = data['image_data']
        prompt = data.get('prompt', 'Analyze this image')
        user_id = g.current_user.get('id')
        
        logger.info(f"Vision analysis request from user {user_id}: {prompt[:50]}...")
        
        # Handle base64 image data
        try:
            if image_data.startswith('data:image'):
                image_data = image_data.split(',')[1]
            image_bytes = base64.b64decode(image_data)
        except Exception as e:
            return jsonify({
                'error': 'Invalid image data',
                'message': f'Could not decode image data: {str(e)}'
            }), 400
        
        response = ai_service.analyze_image(
            image_data=image_bytes,
            prompt=prompt
        )
        
        # Calculate duration and track activity
        duration_seconds = int(time.time() - start_time)
        dashboard_service.track_activity(
            user_id=user_id,
            activity_type=ActivityType.ANALYSIS,
            title="AI Vision Analysis",
            description=f"Vision analysis: {prompt[:100]}...",
            metadata={
                'feature': 'ai_vision',
                'prompt_length': len(prompt),
                'response_length': len(response) if response else 0
            },
            duration_seconds=duration_seconds
        )
        
        return jsonify({
            'success': True,
            'analysis': response,
            'prompt': prompt,
            'status': 'success'
        })
        
    except Exception as e:
        logger.error(f"Error in vision endpoint: {str(e)}")
        
        if isinstance(e, QuotaExceededError):
            return jsonify({
                'error': 'Quota exceeded',
                'message': 'Vision analysis quota limit reached. Please try again later.',
                'retry_after': 3600
            }), 429
        
        return jsonify({
            'error': 'Failed to analyze image',
            'message': str(e)
        }), 500

@ai_bp.route('/analyze-image', methods=['POST'])
@token_required
def analyze_image():
    """Analyze an image using Vertex AI Gemini Pro Vision."""
    start_time = time.time()
    
    try:
        user_id = g.current_user.get('id')
        
        # Handle both JSON and multipart/form-data
        if request.content_type.startswith('application/json'):
            data = request.get_json()
            image_url = data.get('image_url')
            image_data = data.get('image_data')  # base64 encoded
            prompt = data.get('prompt', 'Describe this image in detail')
            
            if image_data:
                # Handle base64 image data
                try:
                    # Remove data URL prefix if present
                    if image_data.startswith('data:image'):
                        image_data = image_data.split(',')[1]
                    image_bytes = base64.b64decode(image_data)
                except Exception as e:
                    return jsonify({
                        'error': 'Invalid image data',
                        'message': f'Could not decode image data: {str(e)}'
                    }), 400
            elif image_url:
                image_bytes = None  # Will be downloaded by service
            else:
                return jsonify({
                    'error': 'Missing image data',
                    'message': 'Please provide either image_url or image_data'
                }), 400
                
        elif 'multipart/form-data' in request.content_type:
            # Handle file upload
            if 'image' not in request.files:
                return jsonify({
                    'error': 'No image file provided',
                    'message': 'Please upload an image file'
                }), 400
            
            image_file = request.files['image']
            prompt = request.form.get('prompt', 'Describe this image in detail')
            image_bytes = image_file.read()
            image_url = None
        else:
            return jsonify({
                'error': 'Invalid content type',
                'message': 'Use application/json or multipart/form-data'
            }), 400
        
        logger.info(f"Image analysis request: {prompt[:50]}...")
        
        response = ai_service.analyze_image(
            image_url=image_url,
            image_data=image_bytes,
            prompt=prompt
        )
        
        # Calculate duration and track activity
        duration_seconds = int(time.time() - start_time)
        dashboard_service.track_activity(
            user_id=user_id,
            activity_type=ActivityType.ANALYSIS,
            title="Image Analysis",
            description=f"Analyzed image with prompt: {prompt[:100]}...",
            metadata={
                'feature': 'image_analysis',
                'prompt_length': len(prompt),
                'has_image_url': bool(image_url),
                'has_image_data': bool(image_bytes),
                'response_length': len(response) if response else 0
            },
            duration_seconds=duration_seconds
        )
        
        return jsonify({
            'analysis': response,
            'prompt': prompt,
            'status': 'success'
        })
        
    except Exception as e:
        logger.error(f"Error in image analysis endpoint: {str(e)}")
        
        if isinstance(e, QuotaExceededError):
            return jsonify({
                'error': 'Quota exceeded',
                'message': 'Image analysis quota limit reached. Please try again later.',
                'retry_after': 3600
            }), 429
        
        return jsonify({
            'error': 'Failed to analyze image',
            'message': str(e)
        }), 500

@ai_bp.route('/generate-summary', methods=['POST'])
@require_json
@validate_required_fields(['text'])
def generate_summary():
    """Generate a summary of the provided text using Vertex AI."""
    try:
        data = request.get_json()
        text = data['text']
        max_length = data.get('max_length', 150)
        style = data.get('style', 'concise')  # concise, detailed, bullet, executive
        
        # Validate input
        if len(text.strip()) < 50:
            return jsonify({
                'error': 'Text too short',
                'message': 'Text must be at least 50 characters long for summarization'
            }), 400
        
        if max_length < 50 or max_length > 1000:
            return jsonify({
                'error': 'Invalid max_length',
                'message': 'max_length must be between 50 and 1000 characters'
            }), 400
        
        logger.info(f"Summary generation request for text length: {len(text)}, style: {style}")
        
        summary = ai_service.generate_summary(
            text=text,
            max_length=max_length,
            style=style
        )
        
        return jsonify({
            'summary': summary,
            'original_length': len(text),
            'summary_length': len(summary),
            'compression_ratio': round(len(summary) / len(text), 2),
            'style': style,
            'status': 'success'
        })
        
    except Exception as e:
        logger.error(f"Error in summary generation endpoint: {str(e)}")
        
        if isinstance(e, QuotaExceededError):
            return jsonify({
                'error': 'Quota exceeded',
                'message': 'Summary generation quota limit reached. Please try again later.',
                'retry_after': 3600
            }), 429
        
        return jsonify({
            'error': 'Failed to generate summary',
            'message': str(e)
        }), 500

@ai_bp.route('/status', methods=['GET'])
def get_ai_status():
    """Get AI service status including quota information."""
    try:
        status = ai_service.get_service_status()
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"Error getting AI status: {str(e)}")
        return jsonify({
            'error': 'Failed to get status',
            'message': str(e)
        }), 500

@ai_bp.route('/models', methods=['GET'])
def get_available_models():
    """Get information about available AI models."""
    try:
        from flask import current_app
        
        models = {
            'text_generation': {
                'model': current_app.config.get('GEMINI_PRO_MODEL', 'gemini-1.5-pro'),
                'description': 'Gemini Pro for text generation and chat',
                'capabilities': ['text_generation', 'conversation', 'reasoning', 'summarization']
            },
            'vision_analysis': {
                'model': current_app.config.get('GEMINI_PRO_VISION_MODEL', 'gemini-1.5-pro-vision'),
                'description': 'Gemini Pro Vision for image analysis',
                'capabilities': ['image_description', 'object_detection', 'text_extraction', 'visual_reasoning']
            }
        }
        
        return jsonify({
            'models': models,
            'location': current_app.config.get('LOCATION', 'asia-south1'),
            'project': current_app.config.get('PROJECT_ID'),
            'status': 'success'
        })
        
    except Exception as e:
        logger.error(f"Error getting model information: {str(e)}")
        return jsonify({
            'error': 'Failed to get model information',
            'message': str(e)
        }), 500

@ai_bp.route('/conversation', methods=['POST'])
@require_json
@validate_required_fields(['messages'])
def conversation():
    """Handle multi-turn conversation with context."""
    try:
        data = request.get_json()
        messages = data['messages']  # List of {role: user/assistant, content: text}
        user_id = data.get('user_id')
        
        # Validate messages format
        if not isinstance(messages, list) or not messages:
            return jsonify({
                'error': 'Invalid messages format',
                'message': 'messages must be a non-empty list'
            }), 400
        
        # Build conversation context
        conversation_history = []
        current_message = ""
        
        for msg in messages:
            if msg.get('role') == 'user':
                conversation_history.append({'user': msg.get('content', '')})
                current_message = msg.get('content', '')
            elif msg.get('role') == 'assistant':
                if conversation_history:
                    conversation_history[-1]['assistant'] = msg.get('content', '')
        
        context = {
            'conversation_history': conversation_history[-5:],  # Last 5 exchanges
            'user_id': user_id
        }
        
        logger.info(f"Conversation request from user {user_id} with {len(messages)} messages")
        
        response = ai_service.generate_response(
            message=current_message,
            user_id=user_id,
            context=context
        )
        
        return jsonify({
            'response': response,
            'message_count': len(messages),
            'user_id': user_id,
            'status': 'success'
        })
        
    except Exception as e:
        logger.error(f"Error in conversation endpoint: {str(e)}")
        
        if isinstance(e, QuotaExceededError):
            return jsonify({
                'error': 'Quota exceeded',
                'message': 'Conversation quota limit reached. Please try again later.',
                'retry_after': 3600
            }), 429
        
        return jsonify({
            'error': 'Failed to process conversation',
            'message': str(e)
        }), 500
