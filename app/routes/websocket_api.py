"""
WebSocket API Routes
HTTP endpoints for managing WebSocket functionality and real-time features.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from flask import Blueprint, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from app.websocket_config import get_websocket_manager, get_websocket_stats, websocket_config
from app.models.websocket_models import RoomType, MessageType, UserStatus
from app.utils.simple_websocket_auth import SimpleWebSocketAuth

logger = logging.getLogger(__name__)

# Create blueprint
websocket_api_bp = Blueprint('websocket_api', __name__, url_prefix='/api/ws')

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)
ws_auth = SimpleWebSocketAuth()

@websocket_api_bp.route('/stats', methods=['GET'])
@limiter.limit("10 per minute")
def get_websocket_statistics():
    """Get WebSocket connection and usage statistics."""
    try:
        stats = get_websocket_stats()
        
        return jsonify({
            'success': True,
            'stats': stats,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting WebSocket stats: {str(e)}")
        return jsonify({
            'error': 'Failed to get WebSocket statistics',
            'message': str(e)
        }), 500

@websocket_api_bp.route('/rooms', methods=['GET'])
@limiter.limit("20 per minute")
def get_rooms():
    """Get list of active WebSocket rooms."""
    try:
        ws_manager = get_websocket_manager()
        if not ws_manager:
            return jsonify({
                'error': 'WebSocket manager not initialized'
            }), 503
        
        # Get query parameters
        room_type = request.args.get('room_type')
        user_id = request.args.get('user_id')
        
        rooms = []
        for room_id, room in ws_manager.rooms.items():
            # Filter by room type if specified
            if room_type and room.room_type.value != room_type:
                continue
            
            # Filter by user access if specified
            if user_id and not ws_auth.check_room_permission({'user_id': user_id}, room_id, 'read'):
                continue
            
            room_data = room.to_dict()
            room_data['message_count'] = len(ws_manager.message_history.get(room_id, []))
            rooms.append(room_data)
        
        return jsonify({
            'success': True,
            'rooms': rooms,
            'total_rooms': len(rooms),
            'filters': {
                'room_type': room_type,
                'user_id': user_id
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting rooms: {str(e)}")
        return jsonify({
            'error': 'Failed to get rooms',
            'message': str(e)
        }), 500

@websocket_api_bp.route('/rooms', methods=['POST'])
@limiter.limit("5 per minute")
def create_room():
    """Create a new WebSocket room."""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['room_id', 'name', 'room_type', 'created_by']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({
                'error': 'Missing required fields',
                'missing_fields': missing_fields
            }), 400
        
        # Validate room type
        try:
            room_type = RoomType(data['room_type'])
        except ValueError:
            return jsonify({
                'error': 'Invalid room type',
                'valid_types': [rt.value for rt in RoomType]
            }), 400
        
        # Create room
        success = websocket_config.create_room(
            room_id=data['room_id'],
            name=data['name'],
            room_type=data['room_type'],
            created_by=data['created_by'],
            settings=data.get('settings', {})
        )
        
        if success:
            return jsonify({
                'success': True,
                'room_id': data['room_id'],
                'message': 'Room created successfully'
            }), 201
        else:
            return jsonify({
                'error': 'Failed to create room'
            }), 500
        
    except Exception as e:
        logger.error(f"Error creating room: {str(e)}")
        return jsonify({
            'error': 'Failed to create room',
            'message': str(e)
        }), 500

@websocket_api_bp.route('/rooms/<room_id>', methods=['GET'])
@limiter.limit("30 per minute")
def get_room_details(room_id: str):
    """Get detailed information about a specific room."""
    try:
        ws_manager = get_websocket_manager()
        if not ws_manager:
            return jsonify({
                'error': 'WebSocket manager not initialized'
            }), 503
        
        room = ws_manager.get_room(room_id)
        if not room:
            return jsonify({
                'error': 'Room not found',
                'room_id': room_id
            }), 404
        
        # Get additional room information
        room_data = room.to_dict()
        room_data['message_history'] = ws_manager.get_room_history(room_id, limit=50)
        room_data['active_users'] = ws_manager.get_active_users(room_id)
        room_data['typing_users'] = [
            typing.to_dict() for typing in room.typing_users.values()
        ]
        room_data['cursor_positions'] = [
            cursor.to_dict() for cursor in room.cursor_positions.values()
        ]
        
        return jsonify({
            'success': True,
            'room': room_data
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting room details: {str(e)}")
        return jsonify({
            'error': 'Failed to get room details',
            'message': str(e)
        }), 500

@websocket_api_bp.route('/rooms/<room_id>/users', methods=['GET'])
@limiter.limit("30 per minute")
def get_room_users(room_id: str):
    """Get users currently active in a room."""
    try:
        users = websocket_config.get_room_users(room_id)
        
        return jsonify({
            'success': True,
            'room_id': room_id,
            'users': users,
            'user_count': len(users)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting room users: {str(e)}")
        return jsonify({
            'error': 'Failed to get room users',
            'message': str(e)
        }), 500

@websocket_api_bp.route('/rooms/<room_id>/messages', methods=['GET'])
@limiter.limit("30 per minute")
def get_room_messages(room_id: str):
    """Get message history for a room."""
    try:
        ws_manager = get_websocket_manager()
        if not ws_manager:
            return jsonify({
                'error': 'WebSocket manager not initialized'
            }), 503
        
        # Get query parameters
        limit = min(int(request.args.get('limit', 50)), 100)  # Max 100 messages
        
        messages = ws_manager.get_room_history(room_id, limit=limit)
        
        return jsonify({
            'success': True,
            'room_id': room_id,
            'messages': messages,
            'message_count': len(messages),
            'limit': limit
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting room messages: {str(e)}")
        return jsonify({
            'error': 'Failed to get room messages',
            'message': str(e)
        }), 500

@websocket_api_bp.route('/users/<user_id>/status', methods=['GET'])
@limiter.limit("30 per minute")
def get_user_status(user_id: str):
    """Get user's WebSocket connection status."""
    try:
        ws_manager = get_websocket_manager()
        if not ws_manager:
            return jsonify({
                'error': 'WebSocket manager not initialized'
            }), 503
        
        is_online = ws_manager.is_user_online(user_id)
        socket_ids = list(ws_manager.user_sockets.get(user_id, set()))
        
        # Get user's rooms
        user_rooms = []
        for room in ws_manager.rooms.values():
            if user_id in room.active_users:
                user_rooms.append({
                    'room_id': room.id,
                    'room_name': room.name,
                    'room_type': room.room_type.value,
                    'joined_at': room.active_users[user_id].connected_at.isoformat()
                })
        
        # Get queued messages
        queued_count = ws_manager.get_queued_message_count(user_id)
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'is_online': is_online,
            'connection_count': len(socket_ids),
            'socket_ids': socket_ids,
            'active_rooms': user_rooms,
            'queued_messages': queued_count
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting user status: {str(e)}")
        return jsonify({
            'error': 'Failed to get user status',
            'message': str(e)
        }), 500

@websocket_api_bp.route('/users/<user_id>/disconnect', methods=['POST'])
@limiter.limit("5 per minute")
def disconnect_user(user_id: str):
    """Disconnect all WebSocket connections for a user."""
    try:
        data = request.get_json() or {}
        reason = data.get('reason', 'Disconnected by admin')
        
        success = websocket_config.disconnect_user(user_id, reason)
        
        if success:
            return jsonify({
                'success': True,
                'user_id': user_id,
                'message': f'User disconnected: {reason}'
            }), 200
        else:
            return jsonify({
                'error': 'Failed to disconnect user',
                'user_id': user_id
            }), 500
        
    except Exception as e:
        logger.error(f"Error disconnecting user: {str(e)}")
        return jsonify({
            'error': 'Failed to disconnect user',
            'message': str(e)
        }), 500

@websocket_api_bp.route('/broadcast', methods=['POST'])
@limiter.limit("5 per minute")
def broadcast_message():
    """Broadcast a message to all connected users or specific room."""
    try:
        data = request.get_json()
        
        message = data.get('message')
        room_id = data.get('room_id')
        namespace = data.get('namespace')
        event_type = data.get('event_type', 'broadcast')
        
        if not message:
            return jsonify({
                'error': 'Message content required'
            }), 400
        
        broadcast_data = {
            'message': message,
            'timestamp': datetime.utcnow().isoformat(),
            'type': 'system_broadcast'
        }
        
        if room_id:
            # Broadcast to specific room
            success = websocket_config.emit_to_room(
                room_id=room_id,
                event=event_type,
                data=broadcast_data,
                namespace=namespace
            )
            target = f"room {room_id}"
        else:
            # Broadcast to all connections (implementation would need enhancement)
            # For now, we'll indicate this isn't supported
            return jsonify({
                'error': 'Global broadcast not implemented',
                'suggestion': 'Use room_id to broadcast to specific room'
            }), 501
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Message broadcasted to {target}',
                'event_type': event_type
            }), 200
        else:
            return jsonify({
                'error': 'Failed to broadcast message'
            }), 500
        
    except Exception as e:
        logger.error(f"Error broadcasting message: {str(e)}")
        return jsonify({
            'error': 'Failed to broadcast message',
            'message': str(e)
        }), 500

@websocket_api_bp.route('/health', methods=['GET'])
def websocket_health():
    """WebSocket health check endpoint."""
    try:
        ws_manager = get_websocket_manager()
        socketio = websocket_config.socketio
        
        health_data = {
            'websocket_enabled': socketio is not None,
            'manager_initialized': ws_manager is not None,
            'redis_connected': websocket_config.redis_client is not None,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if ws_manager:
            stats = ws_manager.get_stats()
            health_data.update({
                'total_connections': stats.get('total_connections', 0),
                'total_rooms': stats.get('total_rooms', 0),
                'total_users': stats.get('total_users', 0)
            })
        
        # Test Redis connection if available
        if websocket_config.redis_client:
            try:
                websocket_config.redis_client.ping()
                health_data['redis_status'] = 'connected'
            except Exception:
                health_data['redis_status'] = 'disconnected'
        
        status_code = 200 if health_data['websocket_enabled'] else 503
        
        return jsonify({
            'success': True,
            'service': 'WebSocket',
            'health': health_data
        }), status_code
        
    except Exception as e:
        logger.error(f"WebSocket health check error: {str(e)}")
        return jsonify({
            'success': False,
            'service': 'WebSocket',
            'error': str(e)
        }), 500

@websocket_api_bp.route('/handlers', methods=['GET'])
def get_websocket_handlers():
    """Get information about registered WebSocket handlers."""
    try:
        handler_info = websocket_config.get_handler_info()
        
        return jsonify({
            'success': True,
            'handlers': handler_info
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting handler info: {str(e)}")
        return jsonify({
            'error': 'Failed to get handler information',
            'message': str(e)
        }), 500

# Error handlers
@websocket_api_bp.errorhandler(429)
def rate_limit_exceeded(error):
    """Handle rate limit exceeded."""
    return jsonify({
        'error': 'Rate limit exceeded',
        'message': 'Too many requests. Please try again later.'
    }), 429

@websocket_api_bp.errorhandler(500)
def internal_error(error):
    """Handle internal server errors."""
    return jsonify({
        'error': 'Internal server error',
        'message': 'An unexpected error occurred'
    }), 500
