"""
Offline Synchronization API Routes
RESTful endpoints for offline sync, conflict resolution, and incremental updates.
"""

import logging
import json
from typing import Dict, Any, List
from flask import Blueprint, request, jsonify
from datetime import datetime

from app.services.offline_sync_service import OfflineSyncService
from app.models.offline_sync import ConflictResolution

logger = logging.getLogger(__name__)

sync_bp = Blueprint('sync', __name__)

# Initialize service
sync_service = OfflineSyncService()

def get_current_user():
    """Placeholder function to get current user ID."""
    # In a real implementation, this would extract user ID from JWT token
    return "placeholder-user-id"

def get_device_id():
    """Get device ID from request headers."""
    return request.headers.get('X-Device-ID', 'default-device')

@sync_bp.route('/sync/upload', methods=['POST'])
def upload_offline_changes():
    """Upload offline changes from client to server."""
    try:
        user_id = get_current_user()
        if not user_id:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'UNAUTHORIZED',
                    'message': 'Valid authentication required'
                }
            }), 401
        
        device_id = get_device_id()
        
        # Validate request data
        if not request.is_json:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_REQUEST',
                    'message': 'Request must be JSON'
                }
            }), 400
        
        request_data = request.get_json()
        changes_data = request_data.get('changes', [])
        
        if not isinstance(changes_data, list):
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_CHANGES',
                    'message': 'Changes must be an array'
                }
            }), 400
        
        # Validate changes structure
        validation_error = _validate_changes_data(changes_data)
        if validation_error:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': validation_error
                }
            }), 400
        
        # Process offline changes
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        sync_response = loop.run_until_complete(
            sync_service.upload_offline_changes(user_id, device_id, changes_data)
        )
        
        return jsonify({
            'success': sync_response.success,
            'message': sync_response.message,
            'syncResponse': sync_response.to_dict()
        }), 200 if sync_response.success else 409  # 409 for conflicts
        
    except Exception as e:
        logger.error(f"Error uploading offline changes: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'UPLOAD_ERROR',
                'message': str(e)
            }
        }), 500

@sync_bp.route('/sync/download', methods=['GET'])
def download_server_changes():
    """Download incremental server changes."""
    try:
        user_id = get_current_user()
        if not user_id:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'UNAUTHORIZED',
                    'message': 'Valid authentication required'
                }
            }), 401
        
        device_id = get_device_id()
        
        # Get query parameters
        last_sync_time_str = request.args.get('lastSyncTime')
        last_sync_time = None
        
        if last_sync_time_str:
            try:
                last_sync_time = datetime.fromisoformat(last_sync_time_str.replace('Z', '+00:00'))
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 'INVALID_TIMESTAMP',
                        'message': 'Invalid lastSyncTime format. Use ISO format.'
                    }
                }), 400
        
        # Download server changes
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        sync_response = loop.run_until_complete(
            sync_service.download_server_changes(user_id, device_id, last_sync_time)
        )
        
        response_data = {
            'success': sync_response.success,
            'message': sync_response.message,
            'syncResponse': sync_response.to_dict()
        }
        
        # Add compression header if data was compressed
        response = jsonify(response_data)
        if sync_response.compression_used:
            response.headers['Content-Encoding'] = 'gzip'
        
        return response, 200
        
    except Exception as e:
        logger.error(f"Error downloading server changes: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'DOWNLOAD_ERROR',
                'message': str(e)
            }
        }), 500

@sync_bp.route('/sync/conflicts', methods=['GET'])
def get_pending_conflicts():
    """Get pending sync conflicts for resolution."""
    try:
        user_id = get_current_user()
        if not user_id:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'UNAUTHORIZED',
                    'message': 'Valid authentication required'
                }
            }), 401
        
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        pending_conflicts = loop.run_until_complete(
            sync_service._get_pending_conflicts(user_id)
        )
        
        return jsonify({
            'success': True,
            'conflicts': [conflict.to_dict() for conflict in pending_conflicts],
            'count': len(pending_conflicts)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting pending conflicts: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'GET_CONFLICTS_ERROR',
                'message': str(e)
            }
        }), 500

@sync_bp.route('/sync/conflicts/<conflict_id>/resolve', methods=['POST'])
def resolve_sync_conflict(conflict_id: str):
    """Resolve a specific sync conflict."""
    try:
        user_id = get_current_user()
        if not user_id:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'UNAUTHORIZED',
                    'message': 'Valid authentication required'
                }
            }), 401
        
        if not request.is_json:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_REQUEST',
                    'message': 'Request must be JSON'
                }
            }), 400
        
        request_data = request.get_json()
        resolution_strategy_str = request_data.get('resolutionStrategy')
        resolved_data = request_data.get('resolvedData')
        
        if not resolution_strategy_str:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'MISSING_STRATEGY',
                    'message': 'Resolution strategy is required'
                }
            }), 400
        
        # Validate resolution strategy
        try:
            resolution_strategy = ConflictResolution(resolution_strategy_str)
        except ValueError:
            valid_strategies = [strategy.value for strategy in ConflictResolution]
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_STRATEGY',
                    'message': f'Invalid resolution strategy. Must be one of: {", ".join(valid_strategies)}'
                }
            }), 400
        
        # Validate resolved data for user choice strategy
        if resolution_strategy == ConflictResolution.USER_CHOICE and not resolved_data:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'MISSING_RESOLVED_DATA',
                    'message': 'Resolved data is required for user choice resolution'
                }
            }), 400
        
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Resolve conflict
        success = loop.run_until_complete(
            sync_service.resolve_conflict(
                conflict_id, resolution_strategy, resolved_data, user_id
            )
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Conflict {conflict_id} resolved successfully',
                'resolutionStrategy': resolution_strategy.value
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'RESOLUTION_FAILED',
                    'message': f'Failed to resolve conflict {conflict_id}'
                }
            }), 400
        
    except Exception as e:
        logger.error(f"Error resolving conflict {conflict_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'CONFLICT_RESOLUTION_ERROR',
                'message': str(e)
            }
        }), 500

@sync_bp.route('/sync/statistics', methods=['GET'])
def get_sync_statistics():
    """Get synchronization statistics for the user."""
    try:
        user_id = get_current_user()
        if not user_id:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'UNAUTHORIZED',
                    'message': 'Valid authentication required'
                }
            }), 401
        
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        statistics = loop.run_until_complete(
            sync_service.get_sync_statistics(user_id)
        )
        
        return jsonify({
            'success': True,
            'statistics': statistics
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting sync statistics: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'STATISTICS_ERROR',
                'message': str(e)
            }
        }), 500

@sync_bp.route('/sync/compress', methods=['POST'])
def compress_sync_data():
    """Compress sync data for mobile networks."""
    try:
        if not request.is_json:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_REQUEST',
                    'message': 'Request must be JSON'
                }
            }), 400
        
        data = request.get_json()
        
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        compressed_data = loop.run_until_complete(
            sync_service.compress_sync_data(data)
        )
        
        # Return base64 encoded compressed data
        import base64
        encoded_data = base64.b64encode(compressed_data).decode('utf-8')
        
        return jsonify({
            'success': True,
            'compressedData': encoded_data,
            'originalSize': len(json.dumps(data)),
            'compressedSize': len(compressed_data),
            'compressionRatio': len(compressed_data) / len(json.dumps(data))
        }), 200
        
    except Exception as e:
        logger.error(f"Error compressing sync data: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'COMPRESSION_ERROR',
                'message': str(e)
            }
        }), 500

@sync_bp.route('/sync/health', methods=['GET'])
def sync_health_check():
    """Health check for offline sync service."""
    return jsonify({
        'success': True,
        'message': 'Offline sync service is operational',
        'timestamp': datetime.utcnow().isoformat(),
        'features': {
            'upload_changes': True,
            'download_changes': True,
            'conflict_resolution': True,
            'incremental_sync': True,
            'data_compression': True,
            'statistics': True
        }
    }), 200

def _validate_changes_data(changes_data: List[Dict[str, Any]]) -> str:
    """Validate sync changes data structure."""
    required_fields = ['entityType', 'entityId', 'action', 'data', 'timestamp']
    valid_entity_types = ['chat', 'weekly_plan', 'activity', 'content', 'file', 'settings']
    valid_actions = ['create', 'update', 'delete', 'restore']
    
    for i, change in enumerate(changes_data):
        if not isinstance(change, dict):
            return f"Change at index {i} must be an object"
        
        # Check required fields
        for field in required_fields:
            if field not in change:
                return f"Change at index {i} missing required field: {field}"
        
        # Validate entity type
        if change['entityType'] not in valid_entity_types:
            return f"Invalid entityType at index {i}. Must be one of: {', '.join(valid_entity_types)}"
        
        # Validate action
        if change['action'] not in valid_actions:
            return f"Invalid action at index {i}. Must be one of: {', '.join(valid_actions)}"
        
        # Validate timestamp format
        try:
            datetime.fromisoformat(change['timestamp'].replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return f"Invalid timestamp format at index {i}. Use ISO format."
        
        # Validate data field
        if not isinstance(change['data'], dict):
            return f"Data field at index {i} must be an object"
    
    return None  # No validation errors
