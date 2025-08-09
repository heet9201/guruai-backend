from flask import Blueprint, jsonify
import time
import logging

logger = logging.getLogger(__name__)
health_bp = Blueprint('health', __name__)

@health_bp.route('/health', methods=['GET'])
def health_check():
    """Basic health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time(),
        'service': 'sahayak-backend',
        'version': '1.0.0'
    })

@health_bp.route('/ready', methods=['GET'])
def readiness_check():
    """Comprehensive readiness check including Vertex AI services."""
    checks = {}
    overall_status = True
    
    try:
        # Database check (placeholder)
        checks['database'] = True
        
        # Redis check (optional for development)
        try:
            import redis
            from flask import current_app
            redis_url = current_app.config.get('REDIS_URL')
            if redis_url:
                redis_client = redis.from_url(redis_url)
                redis_client.ping()
                checks['redis'] = True
            else:
                # Redis is optional in development mode
                checks['redis'] = False
                logger.info("Redis not configured, continuing without it")
        except Exception as e:
            logger.warning(f"Redis check failed: {str(e)}")
            checks['redis'] = False
            # Don't fail overall status if Redis is unavailable in development
            if current_app.config.get('FLASK_ENV') == 'production':
                overall_status = False
        
        # Vertex AI service check
        try:
            from app.services.ai_service import AIService
            ai_service = AIService()
            ai_status = ai_service.get_service_status()
            checks['vertex_ai'] = ai_status.get('status') == 'healthy'
            checks['vertex_ai_available'] = ai_status.get('vertex_ai_initialized', False)
            
            # In development, don't fail if AI service has issues
            if not checks['vertex_ai'] and current_app.config.get('FLASK_ENV') == 'production':
                overall_status = False
                
        except Exception as e:
            logger.warning(f"Vertex AI check failed: {str(e)}")
            checks['vertex_ai'] = False
            checks['vertex_ai_available'] = False
            # Only fail in production
            if current_app.config.get('FLASK_ENV') == 'production':
                overall_status = False
        
        # Speech service check
        try:
            from app.services.speech_service import SpeechService
            speech_service = SpeechService()
            speech_status = speech_service.get_service_status()
            checks['speech_to_text'] = speech_status.get('speech_to_text_available', False)
            checks['text_to_speech'] = speech_status.get('text_to_speech_available', False)
            checks['storage'] = speech_status.get('storage_available', False)
            
            # In development, don't fail if speech services have issues
            if not all([checks['speech_to_text'], checks['text_to_speech'], checks['storage']]) and current_app.config.get('FLASK_ENV') == 'production':
                overall_status = False
                
        except Exception as e:
            logger.warning(f"Speech service check failed: {str(e)}")
            checks['speech_to_text'] = False
            checks['text_to_speech'] = False
            checks['storage'] = False
            # Only fail in production
            if current_app.config.get('FLASK_ENV') == 'production':
                overall_status = False
        
        # Google Cloud authentication check
        try:
            from google.auth import default
            credentials, project = default()
            checks['google_auth'] = True
            checks['project_id'] = project is not None
        except Exception as e:
            logger.warning(f"Google Cloud auth check failed: {str(e)}")
            checks['google_auth'] = False
            checks['project_id'] = False
            overall_status = False
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        overall_status = False
    
    status_code = 200 if overall_status else 503
    
    return jsonify({
        'status': 'ready' if overall_status else 'not ready',
        'checks': checks,
        'timestamp': time.time()
    }), status_code

@health_bp.route('/status/detailed', methods=['GET'])
def detailed_status():
    """Get detailed status including quota information."""
    try:
        status = {
            'service': 'sahayak-backend',
            'version': '1.0.0',
            'timestamp': time.time(),
            'uptime': time.time(),  # This would be calculated from service start time
            'services': {}
        }
        
        # AI Service Status
        try:
            from app.services.ai_service import AIService
            ai_service = AIService()
            status['services']['ai'] = ai_service.get_service_status()
        except Exception as e:
            status['services']['ai'] = {'error': str(e), 'available': False}
        
        # Speech Service Status
        try:
            from app.services.speech_service import SpeechService
            speech_service = SpeechService()
            status['services']['speech'] = speech_service.get_service_status()
        except Exception as e:
            status['services']['speech'] = {'error': str(e), 'available': False}
        
        # Configuration Status
        try:
            from flask import current_app
            status['configuration'] = {
                'environment': current_app.config.get('ENV', 'unknown'),
                'debug': current_app.config.get('DEBUG', False),
                'location': current_app.config.get('LOCATION', 'unknown'),
                'project_id_configured': bool(current_app.config.get('PROJECT_ID')),
                'credentials_configured': bool(current_app.config.get('GOOGLE_APPLICATION_CREDENTIALS')),
                'redis_configured': bool(current_app.config.get('REDIS_URL'))
            }
        except Exception as e:
            status['configuration'] = {'error': str(e)}
        
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"Detailed status check failed: {str(e)}")
        return jsonify({
            'error': 'Status check failed',
            'message': str(e),
            'timestamp': time.time()
        }), 500

@health_bp.route('/status/quotas', methods=['GET'])
def quota_status():
    """Get current API quota status."""
    try:
        quotas = {}
        
        # AI Service Quotas
        try:
            from app.services.ai_service import AIService
            ai_service = AIService()
            ai_status = ai_service.get_service_status()
            if 'quotas' in ai_status:
                quotas['ai'] = ai_status['quotas']
        except Exception as e:
            quotas['ai'] = {'error': str(e)}
        
        # Speech Service Quotas
        try:
            from app.services.speech_service import SpeechService
            speech_service = SpeechService()
            speech_status = speech_service.get_service_status()
            if 'quota' in speech_status:
                quotas['speech'] = speech_status['quota']
        except Exception as e:
            quotas['speech'] = {'error': str(e)}
        
        return jsonify({
            'quotas': quotas,
            'timestamp': time.time(),
            'status': 'success'
        })
        
    except Exception as e:
        logger.error(f"Quota status check failed: {str(e)}")
        return jsonify({
            'error': 'Quota status check failed',
            'message': str(e),
            'timestamp': time.time()
        }), 500
