from functools import wraps
from flask import request, jsonify, g
from app.utils.auth_utils import JWTUtils
from app.services.firebase_auth_service import FirebaseAuthService
import logging

logger = logging.getLogger(__name__)

def token_required(f):
    """Decorator that requires a valid JWT token."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        
        if auth_header:
            token = JWTUtils.extract_token_from_header(auth_header)
        
        if not token:
            return jsonify({
                'error': 'Authentication required',
                'message': 'Token is missing'
            }), 401
        
        # Verify token
        auth_service = FirebaseAuthService()
        result = auth_service.verify_jwt_token(token)
        
        if not result['valid']:
            return jsonify({
                'error': 'Authentication failed',
                'message': result.get('error', 'Invalid token')
            }), 401
        
        # Store user info in Flask's g object for use in the route
        g.current_user = result['user']
        g.device_id = result.get('device_id')
        g.token_type = result.get('token_type')
        
        return f(*args, **kwargs)
    
    return decorated_function

def admin_required(f):
    """Decorator that requires admin role."""
    @wraps(f)
    @token_required
    def decorated_function(*args, **kwargs):
        if g.current_user.get('role') != 'admin':
            return jsonify({
                'error': 'Access denied',
                'message': 'Admin privileges required'
            }), 403
        
        return f(*args, **kwargs)
    
    return decorated_function

def teacher_required(f):
    """Decorator that requires teacher or admin role."""
    @wraps(f)
    @token_required
    def decorated_function(*args, **kwargs):
        allowed_roles = ['teacher', 'admin']
        if g.current_user.get('role') not in allowed_roles:
            return jsonify({
                'error': 'Access denied',
                'message': 'Teacher privileges required'
            }), 403
        
        return f(*args, **kwargs)
    
    return decorated_function
