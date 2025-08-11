"""
Enhanced Health Check Endpoint
Comprehensive health monitoring with dependency checks.
"""

import os
import time
import redis
import logging
from flask import Blueprint, jsonify, current_app
from datetime import datetime, timezone

health_bp = Blueprint('health', __name__)
logger = logging.getLogger(__name__)

class HealthChecker:
    def __init__(self):
        self.checks = {
            'database': self._check_database,
            'redis': self._check_redis,
            'ai_service': self._check_ai_service,
            'storage': self._check_storage,
            'memory': self._check_memory,
            'disk': self._check_disk
        }
    
    def run_all_checks(self):
        """Run all health checks and return comprehensive status."""
        start_time = time.time()
        results = {}
        overall_status = 'healthy'
        
        for check_name, check_func in self.checks.items():
            try:
                check_start = time.time()
                result = check_func()
                check_duration = time.time() - check_start
                
                results[check_name] = {
                    'status': result['status'],
                    'message': result.get('message', ''),
                    'details': result.get('details', {}),
                    'response_time_ms': round(check_duration * 1000, 2)
                }
                
                if result['status'] != 'healthy':
                    overall_status = 'unhealthy'
                    
            except Exception as e:
                logger.error(f"Health check {check_name} failed: {str(e)}")
                results[check_name] = {
                    'status': 'unhealthy',
                    'message': f"Check failed: {str(e)}",
                    'details': {},
                    'response_time_ms': 0
                }
                overall_status = 'unhealthy'
        
        total_duration = time.time() - start_time
        
        return {
            'status': overall_status,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'version': os.getenv('APP_VERSION', '1.0.0'),
            'environment': os.getenv('FLASK_ENV', 'production'),
            'uptime_seconds': self._get_uptime(),
            'checks': results,
            'total_check_time_ms': round(total_duration * 1000, 2)
        }
    
    def _check_database(self):
        """Check database connectivity."""
        try:
            # For now, just check if DATABASE_URL is configured
            database_url = os.getenv('DATABASE_URL')
            if not database_url:
                return {
                    'status': 'degraded',
                    'message': 'Database URL not configured'
                }
            
            return {
                'status': 'healthy',
                'message': 'Database configured'
            }
                
        except Exception as e:
            return {
                'status': 'unhealthy',
                'message': f'Database check failed: {str(e)}'
            }
    
    def _check_redis(self):
        """Check Redis connectivity."""
        try:
            redis_host = os.getenv('REDIS_HOST', 'localhost')
            redis_port = int(os.getenv('REDIS_PORT', 6379))
            
            r = redis.Redis(host=redis_host, port=redis_port, decode_responses=True, socket_timeout=5)
            
            # Test basic operations
            test_key = 'health_check_test'
            r.set(test_key, 'test_value', ex=10)
            value = r.get(test_key)
            r.delete(test_key)
            
            if value == 'test_value':
                # Get Redis info
                info = r.info()
                return {
                    'status': 'healthy',
                    'message': 'Redis connection successful',
                    'details': {
                        'connected_clients': info.get('connected_clients', 0),
                        'used_memory_human': info.get('used_memory_human', 'unknown'),
                        'redis_version': info.get('redis_version', 'unknown')
                    }
                }
            else:
                return {
                    'status': 'unhealthy',
                    'message': 'Redis read/write test failed'
                }
                
        except Exception as e:
            return {
                'status': 'unhealthy',
                'message': f'Redis connection failed: {str(e)}'
            }
    
    def _check_ai_service(self):
        """Check AI service availability."""
        try:
            # Check if OpenAI API key is configured
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                return {
                    'status': 'degraded',
                    'message': 'OpenAI API key not configured'
                }
            
            # For now, just return healthy if key is configured
            # In production, you might want to make a test API call
            return {
                'status': 'healthy',
                'message': 'AI service configured',
                'details': {
                    'api_key_configured': True
                }
            }
                
        except Exception as e:
            return {
                'status': 'unhealthy',
                'message': f'AI service check failed: {str(e)}'
            }
    
    def _check_storage(self):
        """Check file storage accessibility."""
        try:
            # Check if upload directory exists and is writable
            upload_dir = os.getenv('UPLOAD_FOLDER', 'uploads')
            
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir, exist_ok=True)
            
            # Test write/read/delete
            test_file = os.path.join(upload_dir, 'health_check.txt')
            test_content = 'health check test'
            
            with open(test_file, 'w') as f:
                f.write(test_content)
            
            with open(test_file, 'r') as f:
                read_content = f.read()
            
            os.remove(test_file)
            
            if read_content == test_content:
                # Get storage stats
                stat = os.statvfs(upload_dir)
                free_space = stat.f_frsize * stat.f_bavail
                total_space = stat.f_frsize * stat.f_blocks
                used_percent = ((total_space - free_space) / total_space) * 100
                
                return {
                    'status': 'healthy',
                    'message': 'Storage accessible',
                    'details': {
                        'free_space_gb': round(free_space / (1024**3), 2),
                        'used_percent': round(used_percent, 2),
                        'upload_dir': upload_dir
                    }
                }
            else:
                return {
                    'status': 'unhealthy',
                    'message': 'Storage read/write test failed'
                }
                
        except Exception as e:
            return {
                'status': 'unhealthy',
                'message': f'Storage check failed: {str(e)}'
            }
    
    def _check_memory(self):
        """Check memory usage."""
        try:
            import psutil
            
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            available_gb = memory.available / (1024**3)
            
            if memory_percent > 90:
                status = 'unhealthy'
                message = f'Critical memory usage: {memory_percent}%'
            elif memory_percent > 80:
                status = 'degraded'
                message = f'High memory usage: {memory_percent}%'
            else:
                status = 'healthy'
                message = f'Memory usage normal: {memory_percent}%'
            
            return {
                'status': status,
                'message': message,
                'details': {
                    'memory_percent': round(memory_percent, 2),
                    'available_gb': round(available_gb, 2),
                    'total_gb': round(memory.total / (1024**3), 2)
                }
            }
            
        except ImportError:
            return {
                'status': 'degraded',
                'message': 'psutil not available for memory monitoring'
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'message': f'Memory check failed: {str(e)}'
            }
    
    def _check_disk(self):
        """Check disk space."""
        try:
            import shutil
            
            total, used, free = shutil.disk_usage('/')
            used_percent = (used / total) * 100
            
            if used_percent > 95:
                status = 'unhealthy'
                message = f'Critical disk usage: {used_percent:.1f}%'
            elif used_percent > 85:
                status = 'degraded'
                message = f'High disk usage: {used_percent:.1f}%'
            else:
                status = 'healthy'
                message = f'Disk usage normal: {used_percent:.1f}%'
            
            return {
                'status': status,
                'message': message,
                'details': {
                    'used_percent': round(used_percent, 2),
                    'free_gb': round(free / (1024**3), 2),
                    'total_gb': round(total / (1024**3), 2)
                }
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'message': f'Disk check failed: {str(e)}'
            }
    
    def _get_uptime(self):
        """Get application uptime in seconds."""
        try:
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            return time.time() - process.create_time()
        except:
            return 0

# Global health checker instance
health_checker = HealthChecker()

@health_bp.route('/health', methods=['GET'])
def health_check():
    """Comprehensive health check endpoint."""
    try:
        result = health_checker.run_all_checks()
        
        # Determine HTTP status code
        if result['status'] == 'healthy':
            status_code = 200
        elif result['status'] == 'degraded':
            status_code = 200  # Still operational but with issues
        else:
            status_code = 503  # Service unavailable
        
        return jsonify(result), status_code
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'message': f'Health check system failure: {str(e)}',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 503

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
