"""
WebSocket Chat Routes
Real-time chat features with WebSocket support.
"""

import logging
import uuid
from typing import Dict, Any, Optional
from datetime import datetime

from flask import request
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect

from app.models.websocket_models import MessageType, EventType, RoomType
from app.services.websocket_manager import WebSocketManager
from app.utils.simple_websocket_auth import SimpleWebSocketAuth, require_ws_auth, require_room_permission, rate_limit_ws

logger = logging.getLogger(__name__)

class ChatSocketHandler:
    """Handles WebSocket events for chat functionality."""
    
    def __init__(self, socketio: SocketIO, ws_manager: WebSocketManager):
        """Initialize chat socket handler."""
        self.socketio = socketio
        self.ws_manager = ws_manager
        self.ws_auth = SimpleWebSocketAuth()
        
        # Session storage for socket connections
        self.user_sessions = {}
        
        # Register event handlers
        self._register_events()
    
    def _register_events(self):
        """Register WebSocket event handlers."""
        
        @self.socketio.on('connect', namespace='/ws/chat')
        def handle_connect(auth_data):
            """Handle new WebSocket connection."""
            try:
                logger.info(f"Chat WebSocket connection attempt from {request.remote_addr}")
                
                # Validate origin
                origin = request.headers.get('Origin', '')
                if not self.ws_auth.validate_origin(origin):
                    logger.warning(f"Invalid origin for WebSocket connection: {origin}")
                    emit('error', {'message': 'Invalid origin', 'code': 'INVALID_ORIGIN'})
                    disconnect()
                    return False
                
                # Authenticate user
                success, user_data, error_msg = self.ws_auth.authenticate_socket(auth_data or {})
                if not success:
                    logger.warning(f"WebSocket authentication failed: {error_msg}")
                    emit('error', {'message': error_msg, 'code': 'AUTH_FAILED'})
                    disconnect()
                    return False
                
                # Rate limit check
                if not self.ws_auth.rate_limit_check(user_data['user_id'], 'connection'):
                    logger.warning(f"Rate limit exceeded for user {user_data['user_id']}")
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
                    'connect',
                    {'origin': origin, 'user_agent': request.headers.get('User-Agent', '')}
                )
                
                # Emit connection success
                emit('connection_established', {
                    'user_id': user_data['user_id'],
                    'socket_id': request.sid,
                    'timestamp': datetime.utcnow().isoformat(),
                    'available_rooms': self.ws_manager.get_room_list(user_data['user_id'])
                })
                
                logger.info(f"Chat WebSocket connected: user={user_data['user_id']}, socket={request.sid}")
                return True
                
            except Exception as e:
                logger.error(f"Chat WebSocket connection error: {str(e)}")
                emit('error', {'message': 'Connection failed', 'code': 'CONNECTION_ERROR'})
                disconnect()
                return False
        
        @self.socketio.on('disconnect', namespace='/ws/chat')
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
                        'disconnect'
                    )
                    
                    logger.info(f"Chat WebSocket disconnected: user={user_data['user_id']}, socket={request.sid}")
                
            except Exception as e:
                logger.error(f"Chat WebSocket disconnect error: {str(e)}")
        
        @self.socketio.on('join_room', namespace='/ws/chat')
        @require_ws_auth
        def handle_join_room(data, user_data=None):
            """Handle joining a chat room."""
            try:
                room_id = data.get('room_id')
                if not room_id:
                    emit('error', {'message': 'Room ID required', 'code': 'MISSING_ROOM_ID'})
                    return
                
                # Check room permission
                if not self.ws_auth.check_room_permission(user_data, room_id, 'read'):
                    emit('error', {'message': 'Access denied to room', 'code': 'ACCESS_DENIED'})
                    return
                
                # Create room if it doesn't exist (for chat rooms)
                room = self.ws_manager.get_room(room_id)
                if not room and room_id.startswith('chat_'):
                    room = self.ws_manager.create_room(
                        room_id=room_id,
                        name=data.get('room_name', f'Chat {room_id}'),
                        room_type=RoomType.CHAT,
                        created_by=user_data['user_id']
                    )
                
                if not room:
                    emit('error', {'message': 'Room not found', 'code': 'ROOM_NOT_FOUND'})
                    return
                
                # Join room
                success = self.ws_manager.join_room_ws(request.sid, room_id, user_data)
                if success:
                    emit('room_joined', {
                        'room_id': room_id,
                        'room_info': room.to_dict(),
                        'message_history': self.ws_manager.get_room_history(room_id),
                        'active_users': self.ws_manager.get_active_users(room_id)
                    })
                    logger.info(f"User {user_data['user_id']} joined chat room {room_id}")
                else:
                    emit('error', {'message': 'Failed to join room', 'code': 'JOIN_FAILED'})
                
            except Exception as e:
                logger.error(f"Join room error: {str(e)}")
                emit('error', {'message': 'Failed to join room', 'code': 'JOIN_ERROR'})
        
        @self.socketio.on('leave_room', namespace='/ws/chat')
        @require_ws_auth
        def handle_leave_room(data, user_data=None):
            """Handle leaving a chat room."""
            try:
                room_id = data.get('room_id')
                if not room_id:
                    emit('error', {'message': 'Room ID required', 'code': 'MISSING_ROOM_ID'})
                    return
                
                success = self.ws_manager.leave_room_ws(request.sid, room_id)
                if success:
                    emit('room_left', {'room_id': room_id})
                    logger.info(f"User {user_data['user_id']} left chat room {room_id}")
                else:
                    emit('error', {'message': 'Failed to leave room', 'code': 'LEAVE_FAILED'})
                
            except Exception as e:
                logger.error(f"Leave room error: {str(e)}")
                emit('error', {'message': 'Failed to leave room', 'code': 'LEAVE_ERROR'})
        
        @self.socketio.on('send_message', namespace='/ws/chat')
        @require_ws_auth
        @rate_limit_ws('message', limit=100, window=60)
        def handle_send_message(data, user_data=None):
            """Handle sending a chat message."""
            try:
                room_id = data.get('room_id')
                content = data.get('content', '').strip()
                message_type = data.get('message_type', 'text')
                
                if not room_id or not content:
                    emit('error', {'message': 'Room ID and content required', 'code': 'MISSING_DATA'})
                    return
                
                # Validate message type
                try:
                    msg_type = MessageType(message_type)
                except ValueError:
                    emit('error', {'message': 'Invalid message type', 'code': 'INVALID_TYPE'})
                    return
                
                # Validate content length
                if len(content) > 2000:
                    emit('error', {'message': 'Message too long (max 2000 characters)', 'code': 'MESSAGE_TOO_LONG'})
                    return
                
                # Check room access
                if not self.ws_auth.check_room_permission(user_data, room_id, 'write'):
                    emit('error', {'message': 'No write permission for room', 'code': 'NO_WRITE_PERMISSION'})
                    return
                
                # Send message
                message = self.ws_manager.send_message(
                    socket_id=request.sid,
                    room_id=room_id,
                    content=content,
                    message_type=msg_type,
                    metadata=data.get('metadata', {})
                )
                
                if message:
                    emit('message_sent', {
                        'message_id': message.id,
                        'timestamp': message.timestamp.isoformat()
                    })
                    logger.info(f"Message sent: {message.id} in room {room_id}")
                else:
                    emit('error', {'message': 'Failed to send message', 'code': 'SEND_FAILED'})
                
            except Exception as e:
                logger.error(f"Send message error: {str(e)}")
                emit('error', {'message': 'Failed to send message', 'code': 'SEND_ERROR'})
        
        @self.socketio.on('typing_start', namespace='/ws/chat')
        @require_ws_auth
        @rate_limit_ws('typing', limit=20, window=60)
        def handle_typing_start(data, user_data=None):
            """Handle typing start indicator."""
            try:
                room_id = data.get('room_id')
                if not room_id:
                    emit('error', {'message': 'Room ID required', 'code': 'MISSING_ROOM_ID'})
                    return
                
                success = self.ws_manager.handle_typing(request.sid, room_id, True)
                if not success:
                    emit('error', {'message': 'Failed to update typing status', 'code': 'TYPING_FAILED'})
                
            except Exception as e:
                logger.error(f"Typing start error: {str(e)}")
        
        @self.socketio.on('typing_stop', namespace='/ws/chat')
        @require_ws_auth
        @rate_limit_ws('typing', limit=20, window=60)
        def handle_typing_stop(data, user_data=None):
            """Handle typing stop indicator."""
            try:
                room_id = data.get('room_id')
                if not room_id:
                    emit('error', {'message': 'Room ID required', 'code': 'MISSING_ROOM_ID'})
                    return
                
                success = self.ws_manager.handle_typing(request.sid, room_id, False)
                if not success:
                    emit('error', {'message': 'Failed to update typing status', 'code': 'TYPING_FAILED'})
                
            except Exception as e:
                logger.error(f"Typing stop error: {str(e)}")
        
        @self.socketio.on('voice_processing', namespace='/ws/chat')
        @require_ws_auth
        def handle_voice_processing(data, user_data=None):
            """Handle voice message processing status."""
            try:
                room_id = data.get('room_id')
                status = data.get('status')  # 'processing', 'completed', 'error'
                
                if not room_id or not status:
                    emit('error', {'message': 'Room ID and status required', 'code': 'MISSING_DATA'})
                    return
                
                success = self.ws_manager.handle_voice_processing(
                    socket_id=request.sid,
                    room_id=room_id,
                    processing_status=status,
                    metadata=data.get('metadata', {})
                )
                
                if not success:
                    emit('error', {'message': 'Failed to update voice status', 'code': 'VOICE_STATUS_FAILED'})
                
            except Exception as e:
                logger.error(f"Voice processing error: {str(e)}")
        
        @self.socketio.on('get_room_info', namespace='/ws/chat')
        @require_ws_auth
        def handle_get_room_info(data, user_data=None):
            """Get information about a room."""
            try:
                room_id = data.get('room_id')
                if not room_id:
                    emit('error', {'message': 'Room ID required', 'code': 'MISSING_ROOM_ID'})
                    return
                
                # Check room access
                if not self.ws_auth.check_room_permission(user_data, room_id, 'read'):
                    emit('error', {'message': 'Access denied to room', 'code': 'ACCESS_DENIED'})
                    return
                
                room = self.ws_manager.get_room(room_id)
                if not room:
                    emit('error', {'message': 'Room not found', 'code': 'ROOM_NOT_FOUND'})
                    return
                
                emit('room_info', {
                    'room': room.to_dict(),
                    'active_users': self.ws_manager.get_active_users(room_id),
                    'message_history': self.ws_manager.get_room_history(room_id, 20)
                })
                
            except Exception as e:
                logger.error(f"Get room info error: {str(e)}")
                emit('error', {'message': 'Failed to get room info', 'code': 'ROOM_INFO_ERROR'})
        
        @self.socketio.on('ping', namespace='/ws/chat')
        @require_ws_auth
        def handle_ping(data, user_data=None):
            """Handle ping for connection keep-alive."""
            try:
                # Update last activity
                self.ws_manager.update_last_activity(request.sid)
                emit('pong', {'timestamp': datetime.utcnow().isoformat()})
                
            except Exception as e:
                logger.error(f"Ping error: {str(e)}")
    
    def get_handler_info(self) -> Dict[str, Any]:
        """Get information about registered handlers."""
        return {
            'namespace': '/ws/chat',
            'events': [
                'connect', 'disconnect', 'join_room', 'leave_room',
                'send_message', 'typing_start', 'typing_stop',
                'voice_processing', 'get_room_info', 'ping'
            ],
            'description': 'Real-time chat functionality with typing indicators and voice processing'
        }
