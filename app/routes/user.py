from flask import Blueprint, request, jsonify, g
from app.services.firebase_auth_service import FirebaseAuthService
from app.utils.middleware import require_json, validate_required_fields
from app.utils.auth_middleware import token_required
import logging

logger = logging.getLogger(__name__)
user_bp = Blueprint('user', __name__)
auth_service = FirebaseAuthService()

@user_bp.route('/profile', methods=['GET'])
@token_required
def get_profile():
    """Get user profile."""
    try:
        user_id = g.current_user['id']
        
        result = auth_service.user_service.get_user_profile(user_id)
        
        if result['success']:
            return jsonify({
                'user': result['profile'],
                'status': 'success'
            })
        else:
            return jsonify({
                'error': 'Profile not found',
                'message': result['error']
            }), 404
            
    except Exception as e:
        logger.error(f"Error in get profile endpoint: {str(e)}")
        return jsonify({
            'error': 'Failed to get profile',
            'message': 'An error occurred while retrieving profile'
        }), 500

@user_bp.route('/profile', methods=['PUT'])
@token_required
@require_json
def update_profile():
    """Update user profile."""
    try:
        user_id = g.current_user['id']
        data = request.get_json()
        
        # Validate allowed fields
        allowed_fields = [
            'name', 'school', 'subjects', 'grades', 
            'language', 'profileImage', 'settings'
        ]
        
        # Filter out non-allowed fields
        updates = {
            key: value for key, value in data.items() 
            if key in allowed_fields
        }
        
        if not updates:
            return jsonify({
                'error': 'Invalid input',
                'message': 'No valid fields to update',
                'allowedFields': allowed_fields
            }), 400
        
        # Validate specific fields
        if 'subjects' in updates and not isinstance(updates['subjects'], list):
            return jsonify({
                'error': 'Invalid input',
                'message': 'Subjects must be an array'
            }), 400
        
        if 'grades' in updates and not isinstance(updates['grades'], list):
            return jsonify({
                'error': 'Invalid input',
                'message': 'Grades must be an array'
            }), 400
        
        if 'language' in updates and updates['language'] not in ['en', 'hi', 'mr', 'gu']:
            return jsonify({
                'error': 'Invalid input',
                'message': 'Unsupported language code'
            }), 400
        
        result = auth_service.user_service.update_user_profile(user_id, updates)
        
        if result['success']:
            return jsonify({
                'user': result['profile'],
                'message': result['message'],
                'status': 'success'
            })
        else:
            return jsonify({
                'error': 'Update failed',
                'message': result['error']
            }), 400
            
    except Exception as e:
        logger.error(f"Error in update profile endpoint: {str(e)}")
        return jsonify({
            'error': 'Failed to update profile',
            'message': 'An error occurred while updating profile'
        }), 500

@user_bp.route('/devices', methods=['GET'])
@token_required
def get_user_devices():
    """Get all registered devices for the user."""
    try:
        user_id = g.current_user['id']
        
        devices = auth_service.device_service.get_user_devices(user_id)
        
        # Format devices for response (remove sensitive info)
        formatted_devices = []
        for device in devices:
            formatted_devices.append({
                'deviceId': device.get('device_id'),
                'lastSeen': device.get('last_seen'),
                'userAgent': device.get('user_agent', ''),
                'isActive': device.get('is_active', False),
                'loginCount': device.get('login_count', 0)
            })
        
        return jsonify({
            'devices': formatted_devices,
            'status': 'success'
        })
        
    except Exception as e:
        logger.error(f"Error in get devices endpoint: {str(e)}")
        return jsonify({
            'error': 'Failed to get devices',
            'message': 'An error occurred while retrieving devices'
        }), 500

@user_bp.route('/devices/<device_id>/deactivate', methods=['POST'])
@token_required
def deactivate_device(device_id):
    """Deactivate a specific device."""
    try:
        user_id = g.current_user['id']
        
        success = auth_service.device_service.deactivate_device(user_id, device_id)
        
        if success:
            return jsonify({
                'message': 'Device deactivated successfully',
                'status': 'success'
            })
        else:
            return jsonify({
                'error': 'Deactivation failed',
                'message': 'Failed to deactivate device'
            }), 400
            
    except Exception as e:
        logger.error(f"Error in deactivate device endpoint: {str(e)}")
        return jsonify({
            'error': 'Failed to deactivate device',
            'message': 'An error occurred while deactivating device'
        }), 500

@user_bp.route('/delete-account', methods=['DELETE'])
@token_required
@require_json
@validate_required_fields(['confirmation'])
def delete_account():
    """Delete user account and all associated data."""
    try:
        user_id = g.current_user['id']
        data = request.get_json()
        
        # Require explicit confirmation
        if data.get('confirmation') != 'DELETE_MY_ACCOUNT':
            return jsonify({
                'error': 'Invalid confirmation',
                'message': 'Account deletion requires confirmation string: DELETE_MY_ACCOUNT'
            }), 400
        
        result = auth_service.user_service.delete_user_data(user_id)
        
        if result['success']:
            return jsonify({
                'message': 'Account deleted successfully',
                'status': 'success'
            })
        else:
            return jsonify({
                'error': 'Deletion failed',
                'message': result['error']
            }), 400
            
    except Exception as e:
        logger.error(f"Error in delete account endpoint: {str(e)}")
        return jsonify({
            'error': 'Failed to delete account',
            'message': 'An error occurred while deleting account'
        }), 500
