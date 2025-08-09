"""
WebSocket Collaboration Routes
Real-time collaborative planning and resource management.
"""

import logging
import uuid
import json
from typing import Dict, Any, Optional, List
from datetime import datetime

from flask import request
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect

from app.models.websocket_models import EventType, RoomType
from app.services.websocket_manager import WebSocketManager
from app.utils.simple_websocket_auth import SimpleWebSocketAuth, require_ws_auth, require_room_permission, rate_limit_ws

logger = logging.getLogger(__name__)

import logging
import uuid
from typing import Dict, Any, Optional
from datetime import datetime

from flask import request
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect

from app.models.websocket_models import EventType, RoomType
from app.services.websocket_manager import WebSocketManager
from app.utils.websocket_auth import WebSocketAuth, require_ws_auth, require_room_permission, rate_limit_ws

import logging
import uuid
import json
from typing import Dict, Any, Optional, List
from datetime import datetime

from flask import request
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect

from app.models.websocket_models import EventType, RoomType
from app.services.websocket_manager import WebSocketManager
from app.utils.websocket_auth import WebSocketAuth, require_ws_auth, require_room_permission, rate_limit_ws

logger = logging.getLogger(__name__)

class CollaborationSocketHandler:
    """Handles WebSocket events for collaborative planning functionality."""
    
    def __init__(self, socketio: SocketIO, ws_manager: WebSocketManager):
        """Initialize collaboration socket handler."""
        self.socketio = socketio
        self.ws_manager = ws_manager
        self.ws_auth = SimpleWebSocketAuth()
        
        # Session storage for socket connections
        self.user_sessions = {}
        
        # Register event handlers
        self._register_events()
    
    def _register_events(self):
        """Register WebSocket event handlers."""
        
        @self.socketio.on('connect', namespace='/ws/collaboration')
        def handle_connect(auth_data):
            """Handle new WebSocket connection for collaboration."""
            try:
                logger.info(f"Collaboration WebSocket connection attempt from {request.remote_addr}")
                
                # Validate origin
                origin = request.headers.get('Origin', '')
                if not self.ws_auth.validate_origin(origin):
                    logger.warning(f"Invalid origin for collaboration WebSocket: {origin}")
                    emit('error', {'message': 'Invalid origin', 'code': 'INVALID_ORIGIN'})
                    disconnect()
                    return False
                
                # Authenticate user
                success, user_data, error_msg = self.ws_auth.authenticate_socket(auth_data or {})
                if not success:
                    logger.warning(f"Collaboration WebSocket auth failed: {error_msg}")
                    emit('error', {'message': error_msg, 'code': 'AUTH_FAILED'})
                    disconnect()
                    return False
                
                # Rate limit check
                if not self.ws_auth.rate_limit_check(user_data['user_id'], 'connection'):
                    logger.warning(f"Rate limit exceeded for collaboration user {user_data['user_id']}")
                    emit('error', {'message': 'Rate limit exceeded', 'code': 'RATE_LIMIT'})
                    disconnect()
                    return False
                
                # Store user data in session
                self.user_sessions[request.sid] = user_data
                
                # Add connection to manager
                connection = self.ws_manager.add_connection(
                    socket_id=request.sid,
                    user_id=user_data['user_id'],
                    session_id=user_data.get('session_id', ''),
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent', '')
                )
                
                # Log connection
                self.ws_auth.log_connection(
                    user_data['user_id'],
                    request.sid,
                    'collaboration_connect',
                    {'origin': origin}
                )
                
                # Emit connection success
                emit('collaboration_connected', {
                    'user_id': user_data['user_id'],
                    'socket_id': request.sid,
                    'timestamp': datetime.utcnow().isoformat(),
                    'available_rooms': self.ws_manager.get_room_list(user_data['user_id'])
                })
                
                logger.info(f"Collaboration WebSocket connected: user={user_data['user_id']}, socket={request.sid}")
                return True
                
            except Exception as e:
                logger.error(f"Collaboration WebSocket connection error: {str(e)}")
                emit('error', {'message': 'Connection failed', 'code': 'CONNECTION_ERROR'})
                disconnect()
                return False
        
        @self.socketio.on('disconnect', namespace='/ws/collaboration')
        def handle_disconnect():
            """Handle WebSocket disconnection."""
            try:
                user_data = self.user_sessions.get(request.sid)
                if user_data:
                    # Remove connection from manager
                    self.ws_manager.remove_connection(request.sid)
                    
                    # Log disconnection
                    self.ws_auth.log_connection(
                        user_data['user_id'],
                        request.sid,
                        'collaboration_disconnect'
                    )
                    
                    logger.info(f"Collaboration WebSocket disconnected: user={user_data['user_id']}, socket={request.sid}")
                
            except Exception as e:
                logger.error(f"Collaboration WebSocket disconnect error: {str(e)}")
        
        @self.socketio.on('join_planning_session', namespace='/ws/collaboration')
        @require_ws_auth
        def handle_join_planning_session(data, user_data=None):
            """Handle joining a collaborative planning session."""
            try:
                session_id = data.get('session_id')
                plan_id = data.get('plan_id')
                
                if not session_id:
                    emit('error', {'message': 'Session ID required', 'code': 'MISSING_SESSION_ID'})
                    return
                
                # Create room ID for planning session
                room_id = f"planning_{session_id}"
                
                # Check permission to access the plan
                if not self.ws_auth.check_room_permission(user_data, room_id, 'read'):
                    emit('error', {'message': 'Access denied to planning session', 'code': 'ACCESS_DENIED'})
                    return
                
                # Create room if it doesn't exist
                room = self.ws_manager.get_room(room_id)
                if not room:
                    room = self.ws_manager.create_room(
                        room_id=room_id,
                        name=data.get('session_name', f'Planning Session {session_id}'),
                        room_type=RoomType.PLANNING,
                        created_by=user_data['user_id'],
                        settings={
                            'plan_id': plan_id,
                            'session_id': session_id,
                            'auto_save': data.get('auto_save', True),
                            'conflict_resolution': data.get('conflict_resolution', 'merge')
                        }
                    )
                
                # Join room
                success = self.ws_manager.join_room_ws(request.sid, room_id, user_data)
                if success:
                    emit('planning_session_joined', {
                        'session_id': session_id,
                        'room_id': room_id,
                        'plan_id': plan_id,
                        'room_info': room.to_dict(),
                        'active_users': self.ws_manager.get_active_users(room_id),
                        'settings': room.settings
                    })
                    logger.info(f"User {user_data['user_id']} joined planning session {session_id}")
                else:
                    emit('error', {'message': 'Failed to join planning session', 'code': 'JOIN_FAILED'})
                
            except Exception as e:
                logger.error(f"Join planning session error: {str(e)}")
                emit('error', {'message': 'Failed to join planning session', 'code': 'JOIN_ERROR'})
        
        @self.socketio.on('leave_planning_session', namespace='/ws/collaboration')
        @require_ws_auth
        def handle_leave_planning_session(data, user_data=None):
            """Handle leaving a collaborative planning session."""
            try:
                session_id = data.get('session_id')
                if not session_id:
                    emit('error', {'message': 'Session ID required', 'code': 'MISSING_SESSION_ID'})
                    return
                
                room_id = f"planning_{session_id}"
                success = self.ws_manager.leave_room_ws(request.sid, room_id)
                if success:
                    emit('planning_session_left', {'session_id': session_id, 'room_id': room_id})
                    logger.info(f"User {user_data['user_id']} left planning session {session_id}")
                else:
                    emit('error', {'message': 'Failed to leave planning session', 'code': 'LEAVE_FAILED'})
                
            except Exception as e:
                logger.error(f"Leave planning session error: {str(e)}")
                emit('error', {'message': 'Failed to leave planning session', 'code': 'LEAVE_ERROR'})
        
        @self.socketio.on('plan_updated', namespace='/ws/collaboration')
        @require_ws_auth
        @rate_limit_ws('plan_update', limit=50, window=60)
        def handle_plan_update(data, user_data=None):
            """Handle real-time plan updates."""
            try:
                session_id = data.get('session_id')
                operation = data.get('operation')  # 'create', 'update', 'delete', 'move'
                target_type = data.get('target_type')  # 'plan', 'activity', 'lesson'
                target_id = data.get('target_id')
                changes = data.get('changes', {})
                
                if not all([session_id, operation, target_type, target_id]):
                    emit('error', {'message': 'Missing required fields for plan update', 'code': 'MISSING_DATA'})
                    return
                
                room_id = f"planning_{session_id}"
                
                # Check write permission
                if not self.ws_auth.check_room_permission(user_data, room_id, 'write'):
                    emit('error', {'message': 'No write permission for planning session', 'code': 'NO_WRITE_PERMISSION'})
                    return
                
                # Validate operation
                valid_operations = ['create', 'update', 'delete', 'move', 'reorder']
                if operation not in valid_operations:
                    emit('error', {'message': 'Invalid operation', 'code': 'INVALID_OPERATION'})
                    return
                
                # Handle the plan update
                success = self.ws_manager.handle_plan_update(
                    socket_id=request.sid,
                    room_id=room_id,
                    operation=operation,
                    target_type=target_type,
                    target_id=target_id,
                    changes=changes
                )
                
                if success:
                    emit('plan_update_processed', {
                        'session_id': session_id,
                        'operation': operation,
                        'target_type': target_type,
                        'target_id': target_id,
                        'timestamp': datetime.utcnow().isoformat()
                    })
                    logger.info(f"Plan update processed: {operation} on {target_type} {target_id}")
                else:
                    emit('error', {'message': 'Failed to process plan update', 'code': 'UPDATE_FAILED'})
                
            except Exception as e:
                logger.error(f"Plan update error: {str(e)}")
                emit('error', {'message': 'Failed to update plan', 'code': 'UPDATE_ERROR'})
        
        @self.socketio.on('cursor_moved', namespace='/ws/collaboration')
        @require_ws_auth
        @rate_limit_ws('cursor_move', limit=100, window=60)
        def handle_cursor_moved(data, user_data=None):
            """Handle real-time cursor position updates."""
            try:
                session_id = data.get('session_id')
                x = data.get('x')
                y = data.get('y')
                element_id = data.get('element_id')
                selection_start = data.get('selection_start')
                selection_end = data.get('selection_end')
                
                if not session_id or x is None or y is None:
                    emit('error', {'message': 'Session ID and coordinates required', 'code': 'MISSING_DATA'})
                    return
                
                room_id = f"planning_{session_id}"
                
                # Update cursor position
                success = self.ws_manager.update_cursor_position(
                    socket_id=request.sid,
                    room_id=room_id,
                    x=float(x),
                    y=float(y),
                    element_id=element_id,
                    selection_start=selection_start,
                    selection_end=selection_end
                )
                
                if not success:
                    emit('error', {'message': 'Failed to update cursor position', 'code': 'CURSOR_UPDATE_FAILED'})
                
            except Exception as e:
                logger.error(f"Cursor move error: {str(e)}")
        
        @self.socketio.on('activity_dragged', namespace='/ws/collaboration')
        @require_ws_auth
        @rate_limit_ws('activity_drag', limit=30, window=60)
        def handle_activity_dragged(data, user_data=None):
            """Handle drag-and-drop operations for activities."""
            try:
                session_id = data.get('session_id')
                activity_id = data.get('activity_id')
                from_position = data.get('from_position', {})
                to_position = data.get('to_position', {})
                
                if not all([session_id, activity_id, from_position, to_position]):
                    emit('error', {'message': 'Missing required data for activity drag', 'code': 'MISSING_DATA'})
                    return
                
                room_id = f"planning_{session_id}"
                
                # Check write permission
                if not self.ws_auth.check_room_permission(user_data, room_id, 'write'):
                    emit('error', {'message': 'No write permission for activity drag', 'code': 'NO_WRITE_PERMISSION'})
                    return
                
                # Handle activity drag
                success = self.ws_manager.handle_activity_drag(
                    socket_id=request.sid,
                    room_id=room_id,
                    activity_id=activity_id,
                    from_position=from_position,
                    to_position=to_position
                )
                
                if success:
                    emit('activity_drag_processed', {
                        'session_id': session_id,
                        'activity_id': activity_id,
                        'from_position': from_position,
                        'to_position': to_position,
                        'timestamp': datetime.utcnow().isoformat()
                    })
                    logger.info(f"Activity drag processed: {activity_id} in session {session_id}")
                else:
                    emit('error', {'message': 'Failed to process activity drag', 'code': 'DRAG_FAILED'})
                
            except Exception as e:
                logger.error(f"Activity drag error: {str(e)}")
                emit('error', {'message': 'Failed to process activity drag', 'code': 'DRAG_ERROR'})
        
        @self.socketio.on('lock_resource', namespace='/ws/collaboration')
        @require_ws_auth
        def handle_lock_resource(data, user_data=None):
            """Handle locking a resource for exclusive editing."""
            try:
                session_id = data.get('session_id')
                resource_type = data.get('resource_type')  # 'activity', 'lesson', 'plan'
                resource_id = data.get('resource_id')
                
                if not all([session_id, resource_type, resource_id]):
                    emit('error', {'message': 'Missing required data for resource lock', 'code': 'MISSING_DATA'})
                    return
                
                room_id = f"planning_{session_id}"
                room = self.ws_manager.get_room(room_id)
                
                if not room or user_data['user_id'] not in room.active_users:
                    emit('error', {'message': 'Not in planning session', 'code': 'NOT_IN_SESSION'})
                    return
                
                # Check if resource is already locked
                locks = room.settings.get('resource_locks', {})
                lock_key = f"{resource_type}:{resource_id}"
                
                if lock_key in locks:
                    locked_by = locks[lock_key]['user_id']
                    if locked_by != user_data['user_id']:
                        emit('resource_lock_failed', {
                            'resource_type': resource_type,
                            'resource_id': resource_id,
                            'locked_by': locked_by,
                            'message': 'Resource is already locked by another user'
                        })
                        return
                
                # Lock the resource
                locks[lock_key] = {
                    'user_id': user_data['user_id'],
                    'user_name': user_data.get('name', 'Unknown'),
                    'locked_at': datetime.utcnow().isoformat()
                }
                room.settings['resource_locks'] = locks
                
                # Emit lock event to all users in the room
                self.ws_manager._emit_to_room(room_id, EventType.PLAN_UPDATED, {
                    'type': 'resource_locked',
                    'resource_type': resource_type,
                    'resource_id': resource_id,
                    'locked_by': user_data['user_id'],
                    'locked_by_name': user_data.get('name', 'Unknown')
                })
                
                emit('resource_locked', {
                    'resource_type': resource_type,
                    'resource_id': resource_id,
                    'locked_at': locks[lock_key]['locked_at']
                })
                
                logger.info(f"Resource locked: {lock_key} by {user_data['user_id']}")
                
            except Exception as e:
                logger.error(f"Lock resource error: {str(e)}")
                emit('error', {'message': 'Failed to lock resource', 'code': 'LOCK_ERROR'})
        
        @self.socketio.on('unlock_resource', namespace='/ws/collaboration')
        @require_ws_auth
        def handle_unlock_resource(data, user_data=None):
            """Handle unlocking a resource."""
            try:
                session_id = data.get('session_id')
                resource_type = data.get('resource_type')
                resource_id = data.get('resource_id')
                
                if not all([session_id, resource_type, resource_id]):
                    emit('error', {'message': 'Missing required data for resource unlock', 'code': 'MISSING_DATA'})
                    return
                
                room_id = f"planning_{session_id}"
                room = self.ws_manager.get_room(room_id)
                
                if not room or user_data['user_id'] not in room.active_users:
                    emit('error', {'message': 'Not in planning session', 'code': 'NOT_IN_SESSION'})
                    return
                
                # Check if user owns the lock
                locks = room.settings.get('resource_locks', {})
                lock_key = f"{resource_type}:{resource_id}"
                
                if lock_key not in locks:
                    emit('error', {'message': 'Resource is not locked', 'code': 'NOT_LOCKED'})
                    return
                
                locked_by = locks[lock_key]['user_id']
                if locked_by != user_data['user_id'] and user_data.get('role') != 'admin':
                    emit('error', {'message': 'Cannot unlock resource locked by another user', 'code': 'UNLOCK_DENIED'})
                    return
                
                # Unlock the resource
                del locks[lock_key]
                room.settings['resource_locks'] = locks
                
                # Emit unlock event to all users in the room
                self.ws_manager._emit_to_room(room_id, EventType.PLAN_UPDATED, {
                    'type': 'resource_unlocked',
                    'resource_type': resource_type,
                    'resource_id': resource_id,
                    'unlocked_by': user_data['user_id']
                })
                
                emit('resource_unlocked', {
                    'resource_type': resource_type,
                    'resource_id': resource_id
                })
                
                logger.info(f"Resource unlocked: {lock_key} by {user_data['user_id']}")
                
            except Exception as e:
                logger.error(f"Unlock resource error: {str(e)}")
                emit('error', {'message': 'Failed to unlock resource', 'code': 'UNLOCK_ERROR'})
        
        @self.socketio.on('get_session_state', namespace='/ws/collaboration')
        @require_ws_auth
        def handle_get_session_state(data, user_data=None):
            """Get current state of planning session."""
            try:
                session_id = data.get('session_id')
                if not session_id:
                    emit('error', {'message': 'Session ID required', 'code': 'MISSING_SESSION_ID'})
                    return
                
                room_id = f"planning_{session_id}"
                room = self.ws_manager.get_room(room_id)
                
                if not room:
                    emit('error', {'message': 'Planning session not found', 'code': 'SESSION_NOT_FOUND'})
                    return
                
                # Check read permission
                if not self.ws_auth.check_room_permission(user_data, room_id, 'read'):
                    emit('error', {'message': 'Access denied to planning session', 'code': 'ACCESS_DENIED'})
                    return
                
                emit('session_state', {
                    'session_id': session_id,
                    'room_info': room.to_dict(),
                    'active_users': self.ws_manager.get_active_users(room_id),
                    'cursor_positions': {uid: pos.to_dict() for uid, pos in room.cursor_positions.items()},
                    'resource_locks': room.settings.get('resource_locks', {}),
                    'settings': room.settings
                })
                
            except Exception as e:
                logger.error(f"Get session state error: {str(e)}")
                emit('error', {'message': 'Failed to get session state', 'code': 'STATE_ERROR'})
        
        @self.socketio.on('ping', namespace='/ws/collaboration')
        @require_ws_auth
        def handle_ping(data, user_data=None):
            """Handle ping for connection keep-alive."""
            try:
                # Update last activity
                self.ws_manager.update_last_activity(request.sid)
                emit('pong', {'timestamp': datetime.utcnow().isoformat()})
                
            except Exception as e:
                logger.error(f"Collaboration ping error: {str(e)}")
    
    def get_handler_info(self) -> Dict[str, Any]:
        """Get information about registered handlers."""
        return {
            'namespace': '/ws/collaboration',
            'events': [
                'connect', 'disconnect', 'join_planning_session', 'leave_planning_session',
                'plan_updated', 'cursor_moved', 'activity_dragged', 'lock_resource',
                'unlock_resource', 'get_session_state', 'ping'
            ],
            'description': 'Real-time collaborative planning with cursor tracking and resource locking'
        }
