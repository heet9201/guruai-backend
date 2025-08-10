"""
File Management API Routes
RESTful endpoints for file upload, download, sharing, and management.
"""

import os
import logging
import asyncio
from functools import wraps
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple, Optional
from werkzeug.utils import secure_filename
from flask import Blueprint, request, jsonify, send_file, Response
from flask_limiter import Limiter

from app.auth.jwt_auth import jwt_required, get_current_user
from app.models.file_management import FileType, AccessLevel, FileStatus
from app.services.file_manager_service import FileManagerService
from app.services.file_storage_service import FileStorageService

logger = logging.getLogger(__name__)

file_management_bp = Blueprint('file_management', __name__)

# Initialize services
file_manager = FileManagerService()
storage_service = FileStorageService()

def async_route(f):
    """Decorator to handle async functions in Flask routes."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            # Get or create event loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    raise RuntimeError("Event loop is closed")
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Run the async function
            return loop.run_until_complete(f(*args, **kwargs))
        except Exception as e:
            logger.error(f"Async route error: {str(e)}")
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INTERNAL_ERROR',
                    'message': str(e)
                }
            }), 500
    return wrapper

import logging
import os
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from flask import Blueprint, request, jsonify, send_file, current_app
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from app.models.file_management import (
    FileType, FileStatus, AccessLevel, ScanStatus, FileConfig
)
from app.services.file_manager_service import FileManagerService
from app.services.file_storage_service import FileStorageService
from app.utils.auth_middleware import require_auth, get_current_user

logger = logging.getLogger(__name__)

# Create blueprint
files_bp = Blueprint('files', __name__, url_prefix='/api/v1/files')

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Initialize services
storage_service = FileStorageService()
file_manager = FileManagerService(storage_service)

@files_bp.route('/upload', methods=['POST'])
@require_auth
@limiter.limit("10 per minute")
def upload_file():
    """Upload file with comprehensive validation and processing."""
    try:
        user_data = get_current_user()
        user_id = user_data['user_id']
        
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({
                'error': 'No file provided',
                'code': 'FILE_REQUIRED'
            }), 400
        
        file_obj: FileStorage = request.files['file']
        
        # Check if filename is present
        if file_obj.filename == '':
            return jsonify({
                'error': 'No file selected',
                'code': 'FILE_REQUIRED'
            }), 400
        
        # Get additional parameters
        description = request.form.get('description', '').strip()
        tags = request.form.get('tags', '').split(',') if request.form.get('tags') else []
        tags = [tag.strip() for tag in tags if tag.strip()]
        
        access_level_str = request.form.get('access_level', 'private').lower()
        try:
            access_level = AccessLevel(access_level_str)
        except ValueError:
            access_level = AccessLevel.PRIVATE
        
        # Read file data
        file_data = file_obj.read()
        
        if not file_data:
            return jsonify({
                'error': 'Empty file not allowed',
                'code': 'EMPTY_FILE'
            }), 400
        
        # Upload file
        try:
            # Create event loop if not exists
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Run async upload function
            success, message, metadata = loop.run_until_complete(
                file_manager.upload_file(
                    file_data=file_data,
                    filename=secure_filename(file_obj.filename),
                    user_id=user_id,
                    access_level=access_level,
                    description=description if description else None,
                    tags=tags,
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent', '')
                )
            )
        
        if success and metadata:
            return jsonify({
                'success': True,
                'message': message,
                'file': metadata.to_dict()
            }), 201
        else:
            return jsonify({
                'error': message,
                'code': 'UPLOAD_FAILED'
            }), 400
            
    except Exception as e:
        logger.error(f"File upload error: {str(e)}")
        return jsonify({
            'error': 'Upload failed',
            'message': str(e),
            'code': 'UPLOAD_ERROR'
        }), 500

@files_bp.route('/<file_id>', methods=['GET'])
@require_auth
@limiter.limit("100 per minute")
def download_file(file_id: str):
    """Download file with access control."""
    try:
        user_data = get_current_user()
        user_id = user_data['user_id']
        
        # Check if this is a metadata request
        if request.args.get('metadata') == 'true':
            metadata = await file_manager.get_file(file_id, user_id)
            if not metadata:
                return jsonify({
                    'error': 'File not found or access denied',
                    'code': 'FILE_NOT_FOUND'
                }), 404
            
            return jsonify({
                'success': True,
                'file': metadata.to_dict()
            }), 200
        
        # Download file
        success, message, file_data, metadata = await file_manager.download_file(
            file_id=file_id,
            user_id=user_id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')
        )
        
        if not success:
            return jsonify({
                'error': message,
                'code': 'DOWNLOAD_FAILED'
            }), 404 if 'not found' in message.lower() else 400
        
        # Create response with proper headers
        response = send_file(
            io.BytesIO(file_data),
            mimetype=metadata.mime_type,
            as_attachment=True,
            download_name=metadata.original_filename
        )
        
        # Add custom headers
        response.headers['X-File-ID'] = file_id
        response.headers['X-File-Size'] = str(metadata.size)
        response.headers['X-File-Type'] = metadata.file_type.value
        
        return response
        
    except Exception as e:
        logger.error(f"File download error: {str(e)}")
        return jsonify({
            'error': 'Download failed',
            'message': str(e),
            'code': 'DOWNLOAD_ERROR'
        }), 500

@files_bp.route('/<file_id>', methods=['DELETE'])
@require_auth
@limiter.limit("20 per minute")
def delete_file(file_id: str):
    """Delete file securely."""
    try:
        user_data = get_current_user()
        user_id = user_data['user_id']
        
        success, message = await file_manager.delete_file(
            file_id=file_id,
            user_id=user_id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': message
            }), 200
        else:
            return jsonify({
                'error': message,
                'code': 'DELETE_FAILED'
            }), 404 if 'not found' in message.lower() else 403
            
    except Exception as e:
        logger.error(f"File deletion error: {str(e)}")
        return jsonify({
            'error': 'Deletion failed',
            'message': str(e),
            'code': 'DELETE_ERROR'
        }), 500

@files_bp.route('', methods=['GET'])
@require_auth
@limiter.limit("60 per minute")
def list_files():
    """List user files with pagination and filtering."""
    try:
        user_data = get_current_user()
        user_id = user_data['user_id']
        
        # Get query parameters
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 20)), 100)  # Max 100 per page
        
        # Filters
        file_type_str = request.args.get('type')
        status_str = request.args.get('status')
        search = request.args.get('search', '').strip()
        
        file_type = None
        if file_type_str:
            try:
                file_type = FileType(file_type_str.lower())
            except ValueError:
                pass
        
        status = None
        if status_str:
            try:
                status = FileStatus(status_str.lower())
            except ValueError:
                pass
        
        # Get files
        result = file_manager.list_user_files(
            user_id=user_id,
            page=page,
            per_page=per_page,
            file_type=file_type,
            status=status,
            search=search if search else None
        )
        
        return jsonify({
            'success': True,
            'data': result
        }), 200
        
    except Exception as e:
        logger.error(f"List files error: {str(e)}")
        return jsonify({
            'error': 'Failed to list files',
            'message': str(e),
            'code': 'LIST_ERROR'
        }), 500

@files_bp.route('/<file_id>/share', methods=['POST'])
@require_auth
@limiter.limit("10 per minute")
def create_share_link(file_id: str):
    """Generate shareable link for file."""
    try:
        user_data = get_current_user()
        user_id = user_data['user_id']
        
        data = request.get_json() or {}
        
        # Parse expiration
        expires_in_hours = data.get('expires_in_hours', 24)
        expires_in = timedelta(hours=min(expires_in_hours, 168))  # Max 1 week
        
        # Parse other options
        max_downloads = data.get('max_downloads')
        if max_downloads is not None:
            max_downloads = min(max_downloads, 100)  # Max 100 downloads
        
        password = data.get('password', '').strip()
        password = password if password else None
        
        # Create share link
        success, message, share_link = file_manager.create_share_link(
            file_id=file_id,
            user_id=user_id,
            expires_in=expires_in,
            max_downloads=max_downloads,
            password=password
        )
        
        if success and share_link:
            # Generate public URL
            share_url = f"{request.host_url}api/v1/files/shared/{share_link.token}"
            
            response_data = share_link.to_dict()
            response_data['share_url'] = share_url
            
            return jsonify({
                'success': True,
                'message': message,
                'share_link': response_data
            }), 201
        else:
            return jsonify({
                'error': message,
                'code': 'SHARE_FAILED'
            }), 400
            
    except Exception as e:
        logger.error(f"Create share link error: {str(e)}")
        return jsonify({
            'error': 'Failed to create share link',
            'message': str(e),
            'code': 'SHARE_ERROR'
        }), 500

@files_bp.route('/shared/<token>', methods=['GET'])
@limiter.limit("50 per minute")
def access_shared_file(token: str):
    """Access file via shared link."""
    try:
        # Get password if provided
        password = request.args.get('password')
        
        # Check if this is a metadata request
        if request.args.get('metadata') == 'true':
            success, message, metadata = file_manager.get_shared_file(token, password)
            if not success:
                return jsonify({
                    'error': message,
                    'code': 'SHARE_ACCESS_DENIED'
                }), 403 if 'password' in message.lower() else 404
            
            return jsonify({
                'success': True,
                'file': metadata.to_dict()
            }), 200
        
        # Get file for download
        success, message, metadata = file_manager.get_shared_file(token, password)
        if not success:
            return jsonify({
                'error': message,
                'code': 'SHARE_ACCESS_DENIED'
            }), 403 if 'password' in message.lower() else 404
        
        # Download file
        download_success, download_message, file_data = await storage_service.download_file(metadata)
        
        if not download_success:
            return jsonify({
                'error': download_message,
                'code': 'DOWNLOAD_FAILED'
            }), 500
        
        # Create response
        response = send_file(
            io.BytesIO(file_data),
            mimetype=metadata.mime_type,
            as_attachment=True,
            download_name=metadata.original_filename
        )
        
        response.headers['X-Shared-File'] = 'true'
        response.headers['X-File-ID'] = metadata.id
        
        return response
        
    except Exception as e:
        logger.error(f"Shared file access error: {str(e)}")
        return jsonify({
            'error': 'Failed to access shared file',
            'message': str(e),
            'code': 'SHARE_ACCESS_ERROR'
        }), 500

@files_bp.route('/<file_id>/metadata', methods=['PUT'])
@require_auth
@limiter.limit("30 per minute")
def update_file_metadata(file_id: str):
    """Update file metadata."""
    try:
        user_data = get_current_user()
        user_id = user_data['user_id']
        
        data = request.get_json()
        if not data:
            return jsonify({
                'error': 'No update data provided',
                'code': 'NO_DATA'
            }), 400
        
        success, message = file_manager.update_file_metadata(
            file_id=file_id,
            user_id=user_id,
            updates=data
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': message
            }), 200
        else:
            return jsonify({
                'error': message,
                'code': 'UPDATE_FAILED'
            }), 400
            
    except Exception as e:
        logger.error(f"Update metadata error: {str(e)}")
        return jsonify({
            'error': 'Failed to update metadata',
            'message': str(e),
            'code': 'UPDATE_ERROR'
        }), 500

@files_bp.route('/<file_id>/operations', methods=['GET'])
@require_auth
@limiter.limit("30 per minute")
def get_file_operations(file_id: str):
    """Get file operation history."""
    try:
        user_data = get_current_user()
        user_id = user_data['user_id']
        
        operations = file_manager.get_file_operations(file_id, user_id)
        
        return jsonify({
            'success': True,
            'operations': operations
        }), 200
        
    except Exception as e:
        logger.error(f"Get file operations error: {str(e)}")
        return jsonify({
            'error': 'Failed to get file operations',
            'message': str(e),
            'code': 'OPERATIONS_ERROR'
        }), 500

@files_bp.route('/statistics', methods=['GET'])
@require_auth
@limiter.limit("20 per minute")
def get_file_statistics():
    """Get user's file statistics."""
    try:
        user_data = get_current_user()
        user_id = user_data['user_id']
        
        stats = file_manager.get_file_statistics(user_id)
        
        return jsonify({
            'success': True,
            'statistics': stats
        }), 200
        
    except Exception as e:
        logger.error(f"Get file statistics error: {str(e)}")
        return jsonify({
            'error': 'Failed to get file statistics',
            'message': str(e),
            'code': 'STATISTICS_ERROR'
        }), 500

@files_bp.route('/config', methods=['GET'])
@limiter.limit("10 per minute")
def get_file_config():
    """Get file upload configuration and limits."""
    try:
        config = {
            'size_limits': {
                file_type.value: limit for file_type, limit in FileConfig.SIZE_LIMITS.items()
            },
            'allowed_types': {
                file_type.value: mime_types for file_type, mime_types in FileConfig.ALLOWED_MIME_TYPES.items()
            },
            'thumbnail_sizes': FileConfig.THUMBNAIL_SIZES,
            'max_files_per_upload': 5,
            'supported_formats': {
                'images': ['PNG', 'JPG', 'JPEG', 'GIF', 'WEBP', 'BMP', 'SVG'],
                'audio': ['MP3', 'WAV', 'OGG', 'FLAC', 'AAC'],
                'documents': ['PDF', 'DOC', 'DOCX', 'XLS', 'XLSX', 'PPT', 'PPTX', 'TXT', 'CSV', 'RTF'],
                'archives': ['ZIP', 'RAR', '7Z', 'TAR', 'GZ']
            }
        }
        
        return jsonify({
            'success': True,
            'config': config
        }), 200
        
    except Exception as e:
        logger.error(f"Get file config error: {str(e)}")
        return jsonify({
            'error': 'Failed to get file configuration',
            'message': str(e),
            'code': 'CONFIG_ERROR'
        }), 500

# Admin endpoints
@files_bp.route('/admin/statistics', methods=['GET'])
@require_auth
@limiter.limit("10 per minute")
def get_system_statistics():
    """Get system-wide file statistics (admin only)."""
    try:
        user_data = get_current_user()
        
        # Check if user is admin (implement proper admin check)
        if not user_data.get('is_admin', False):
            return jsonify({
                'error': 'Admin access required',
                'code': 'ADMIN_REQUIRED'
            }), 403
        
        stats = file_manager.get_system_statistics()
        
        return jsonify({
            'success': True,
            'statistics': stats
        }), 200
        
    except Exception as e:
        logger.error(f"Get system statistics error: {str(e)}")
        return jsonify({
            'error': 'Failed to get system statistics',
            'message': str(e),
            'code': 'ADMIN_STATISTICS_ERROR'
        }), 500

@files_bp.route('/admin/cleanup', methods=['POST'])
@require_auth
@limiter.limit("5 per minute")
def cleanup_expired_shares():
    """Clean up expired share links (admin only)."""
    try:
        user_data = get_current_user()
        
        # Check if user is admin
        if not user_data.get('is_admin', False):
            return jsonify({
                'error': 'Admin access required',
                'code': 'ADMIN_REQUIRED'
            }), 403
        
        file_manager.cleanup_expired_shares()
        
        return jsonify({
            'success': True,
            'message': 'Cleanup completed successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Cleanup error: {str(e)}")
        return jsonify({
            'error': 'Cleanup failed',
            'message': str(e),
            'code': 'CLEANUP_ERROR'
        }), 500

# Error handlers
@files_bp.errorhandler(413)
def file_too_large(error):
    """Handle file too large errors."""
    return jsonify({
        'error': 'File too large',
        'message': 'The uploaded file exceeds the size limit',
        'code': 'FILE_TOO_LARGE'
    }), 413

@files_bp.errorhandler(429)
def rate_limit_exceeded(error):
    """Handle rate limit exceeded."""
    return jsonify({
        'error': 'Rate limit exceeded',
        'message': 'Too many requests. Please try again later.',
        'code': 'RATE_LIMIT'
    }), 429

# Import necessary modules at the top
import io
