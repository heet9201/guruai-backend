from flask import Blueprint, request, jsonify, g
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from app.services.firebase_auth_service import FirebaseAuthService
from app.utils.middleware import require_json, validate_required_fields
from app.utils.auth_middleware import token_required
import logging

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)
auth_service = FirebaseAuthService()

# Initialize rate limiter (will be configured in app init)
limiter = Limiter(
    default_limits=["200 per hour"],
    key_func=get_remote_address
)

@auth_bp.route('/login', methods=['POST'])
@limiter.limit("10 per minute")
@require_json
@validate_required_fields(['email', 'password', 'deviceId'])
def login():
    """Enhanced user login endpoint with security features."""
    try:
        data = request.get_json()
        email = data['email'].lower().strip()
        password = data['password']
        device_id = data['deviceId']
        
        # Validate input
        if len(email) < 3 or '@' not in email:
            return jsonify({
                'error': 'Invalid input',
                'message': 'Please provide a valid email address'
            }), 400
        
        if len(password) < 6:
            return jsonify({
                'error': 'Invalid input',
                'message': 'Password must be at least 6 characters'
            }), 400
        
        if len(device_id) < 8:
            return jsonify({
                'error': 'Invalid input',
                'message': 'Invalid device ID'
            }), 400
        
        logger.info(f"Login attempt for email: {email}")
        
        result = auth_service.authenticate_user(email, password, device_id, request)
        
        if result['success']:
            return jsonify({
                'token': result['token'],
                'refreshToken': result['refreshToken'],
                'user': result['user'],
                'status': 'success'
            })
        else:
            return jsonify({
                'error': 'Authentication failed',
                'message': result['message']
            }), 401
            
    except Exception as e:
        logger.error(f"Error in login endpoint: {str(e)}")
        return jsonify({
            'error': 'Login failed',
            'message': 'An error occurred during login'
        }), 500

@auth_bp.route('/refresh', methods=['POST'])
@limiter.limit("30 per minute")
@require_json
@validate_required_fields(['refreshToken'])
def refresh_token():
    """Refresh access token using refresh token."""
    try:
        data = request.get_json()
        refresh_token = data['refreshToken']
        
        result = auth_service.refresh_token(refresh_token)
        
        if result['success']:
            return jsonify({
                'token': result['token'],
                'refreshToken': result['refreshToken'],
                'status': 'success'
            })
        else:
            return jsonify({
                'error': 'Token refresh failed',
                'message': result['message']
            }), 401
            
    except Exception as e:
        logger.error(f"Error in refresh token endpoint: {str(e)}")
        return jsonify({
            'error': 'Token refresh failed',
            'message': 'An error occurred during token refresh'
        }), 500

@auth_bp.route('/logout', methods=['POST'])
@token_required
def logout():
    """Enhanced logout endpoint with device deactivation."""
    try:
        data = request.get_json() or {}
        device_id = data.get('deviceId')
        
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({
                'error': 'Authentication required',
                'message': 'Authorization header missing'
            }), 401
        
        # Extract token
        from app.utils.auth_utils import JWTUtils
        token = JWTUtils.extract_token_from_header(auth_header)
        
        result = auth_service.logout_user_with_token(token, device_id)
        
        if result['success']:
            return jsonify({
                'message': 'Logged out successfully',
                'status': 'success'
            })
        else:
            return jsonify({
                'error': 'Logout failed',
                'message': result['message']
            }), 400
        
    except Exception as e:
        logger.error(f"Error in logout endpoint: {str(e)}")
        return jsonify({
            'error': 'Logout failed',
            'message': 'An error occurred during logout'
        }), 500

@auth_bp.route('/register', methods=['POST'])
@limiter.limit("5 per minute")
@require_json
@validate_required_fields(['email', 'password', 'name', 'deviceId'])
def register():
    """Enhanced user registration endpoint."""
    try:
        data = request.get_json()
        email = data['email'].lower().strip()
        password = data['password']
        name = data['name'].strip()
        device_id = data['deviceId']
        
        # Validate input
        if len(email) < 3 or '@' not in email:
            return jsonify({
                'error': 'Invalid input',
                'message': 'Please provide a valid email address'
            }), 400
        
        if len(password) < 8:
            return jsonify({
                'error': 'Invalid input',
                'message': 'Password must be at least 8 characters'
            }), 400
        
        if len(name) < 2:
            return jsonify({
                'error': 'Invalid input',
                'message': 'Name must be at least 2 characters'
            }), 400
        
        # Optional fields for teacher profile
        additional_data = {
            'school': data.get('school', ''),
            'subjects': data.get('subjects', []),
            'grades': data.get('grades', []),
            'language': data.get('language', 'en'),
            'role': data.get('role', 'teacher')
        }
        
        logger.info(f"Registration attempt for email: {email}")
        
        result = auth_service.register_user_enhanced(
            email, password, name, device_id, request, additional_data
        )
        
        if result['success']:
            return jsonify({
                'token': result['token'],
                'refreshToken': result['refreshToken'],
                'user': result['user'],
                'status': 'success'
            }), 201
        else:
            return jsonify({
                'error': 'Registration failed',
                'message': result['message']
            }), 400
            
    except Exception as e:
        logger.error(f"Error in registration endpoint: {str(e)}")
        return jsonify({
            'error': 'Registration failed',
            'message': 'An error occurred during registration'
        }), 500

@auth_bp.route('/verify-token', methods=['POST'])
@require_json
@validate_required_fields(['token'])
def verify_token():
    """Verify JWT token."""
    try:
        data = request.get_json()
        token = data['token']
        
        result = auth_service.verify_jwt_token(token)
        
        if result['valid']:
            return jsonify({
                'valid': True,
                'user': result['user'],
                'deviceId': result.get('device_id'),
                'status': 'success'
            })
        else:
            return jsonify({
                'valid': False,
                'error': 'Invalid token',
                'message': result.get('error', 'Token verification failed')
            }), 401
            
    except Exception as e:
        logger.error(f"Error in token verification endpoint: {str(e)}")
        return jsonify({
            'valid': False,
            'error': 'Token verification failed',
            'message': 'An error occurred during token verification'
        }), 500
