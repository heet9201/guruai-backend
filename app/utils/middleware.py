import time
import logging
from flask import request, g
from functools import wraps
from app.middleware.performance_middleware import PerformanceMiddleware

logger = logging.getLogger(__name__)

def register_middleware(app):
    """Register middleware for the Flask app."""
    
    # Initialize performance middleware
    performance_middleware = PerformanceMiddleware(app)
    
    @app.before_request
    def before_request():
        """Log request details and start timing."""
        g.start_time = time.time()
        logger.info(f"Request: {request.method} {request.url}")
        logger.debug(f"Headers: {dict(request.headers)}")
        
        # Add request ID for tracking
        g.request_id = generate_request_id()
    
    @app.after_request
    def after_request(response):
        """Log response details and execution time."""
        execution_time = time.time() - g.start_time
        logger.info(f"Response: {response.status_code} - {execution_time:.3f}s")
        
        # Add custom headers
        response.headers['X-Request-ID'] = g.request_id
        response.headers['X-Execution-Time'] = f"{execution_time:.3f}s"
        
        # Add rate limit headers if available
        if hasattr(g, 'rate_limit_headers'):
            rate_limit_info = g.rate_limit_headers
            if 'remaining' in rate_limit_info:
                response.headers['X-RateLimit-Remaining'] = str(rate_limit_info['remaining'])
            if 'limit' in rate_limit_info:
                response.headers['X-RateLimit-Limit'] = str(rate_limit_info['limit'])
            if 'reset_at' in rate_limit_info:
                response.headers['X-RateLimit-Reset'] = rate_limit_info['reset_at']
        
        return response

def generate_request_id():
    """Generate a unique request ID."""
    import uuid
    return str(uuid.uuid4())[:8]

def require_json(f):
    """Decorator to ensure request contains JSON data."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.is_json:
            logger.warning("Request does not contain JSON data")
            from flask import jsonify
            return jsonify({'error': 'Content-Type must be application/json'}), 400
        return f(*args, **kwargs)
    return decorated_function

def validate_required_fields(required_fields):
    """Decorator to validate required fields in JSON payload."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            data = request.get_json()
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                logger.warning(f"Missing required fields: {missing_fields}")
                from flask import jsonify
                return jsonify({
                    'error': 'Missing required fields',
                    'missing_fields': missing_fields
                }), 400
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
