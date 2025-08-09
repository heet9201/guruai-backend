from flask import Blueprint, request, jsonify
from app.services.firebase_auth_service import FirebaseAuthService
from app.utils.middleware import require_json, validate_required_fields
import logging

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)
auth_service = FirebaseAuthService()

@auth_bp.route('/login', methods=['POST'])
@require_json
@validate_required_fields(['email', 'password'])
def login():
    """User login endpoint."""
    try:
        data = request.get_json()
        email = data['email']
        password = data['password']
        
        logger.info(f"Login attempt for email: {email}")
        
        result = auth_service.authenticate_user(email, password)
        
        if result['success']:
            return jsonify({
                'token': result['token'],
                'user': result['user'],
                'status': 'success'
            })
        else:
            return jsonify({
                'error': 'Invalid credentials',
                'message': result['message']
            }), 401
            
    except Exception as e:
        logger.error(f"Error in login endpoint: {str(e)}")
        return jsonify({
            'error': 'Login failed',
            'message': str(e)
        }), 500

@auth_bp.route('/register', methods=['POST'])
@require_json
@validate_required_fields(['email', 'password', 'name'])
def register():
    """User registration endpoint."""
    try:
        data = request.get_json()
        email = data['email']
        password = data['password']
        name = data['name']
        
        logger.info(f"Registration attempt for email: {email}")
        
        result = auth_service.register_user(email, password, name)
        
        if result['success']:
            return jsonify({
                'token': result['token'],
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
            'message': str(e)
        }), 500

@auth_bp.route('/verify-token', methods=['POST'])
@require_json
@validate_required_fields(['token'])
def verify_token():
    """Verify JWT token."""
    try:
        data = request.get_json()
        token = data['token']
        
        result = auth_service.verify_token(token)
        
        if result['valid']:
            return jsonify({
                'valid': True,
                'user': result['user'],
                'status': 'success'
            })
        else:
            return jsonify({
                'valid': False,
                'error': 'Invalid token',
                'message': result['message']
            }), 401
            
    except Exception as e:
        logger.error(f"Error in token verification endpoint: {str(e)}")
        return jsonify({
            'valid': False,
            'error': 'Token verification failed',
            'message': str(e)
        }), 500

@auth_bp.route('/logout', methods=['POST'])
@require_json
@validate_required_fields(['token'])
def logout():
    """User logout endpoint."""
    try:
        data = request.get_json()
        token = data['token']
        
        # First verify the token to get user ID
        verify_result = auth_service.verify_token(token)
        
        if not verify_result['valid']:
            return jsonify({
                'error': 'Invalid token',
                'message': verify_result['message']
            }), 401
        
        # Logout using user ID
        uid = verify_result['user']['uid']
        result = auth_service.logout_user(uid)
        
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
            'message': str(e)
        }), 500
