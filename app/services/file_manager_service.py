"""
File Management Service
Main service for file operations, metadata management, and access control.
"""

import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
import json

from app.models.file_management import (
    FileMetadata, FileType, FileStatus, AccessLevel, ScanStatus,
    ShareLink, FileOperation, FileConfig
)
from app.services.file_storage_service import FileStorageService

logger = logging.getLogger(__name__)

class FileManagerService:
    """Service for comprehensive file management."""
    
    def __init__(self, storage_service: FileStorageService = None):
        """Initialize file manager service."""
        self.storage_service = storage_service or FileStorageService()
        
        # In-memory storage for development (replace with database)
        self.files_db: Dict[str, FileMetadata] = {}
        self.share_links_db: Dict[str, ShareLink] = {}
        self.operations_log: List[FileOperation] = []
        
        logger.info("File manager service initialized")
    
    async def upload_file(
        self,
        file_data: bytes,
        filename: str,
        user_id: str,
        access_level: AccessLevel = AccessLevel.PRIVATE,
        description: str = None,
        tags: List[str] = None,
        ip_address: str = None,
        user_agent: str = None
    ) -> Tuple[bool, str, Optional[FileMetadata]]:
        """Upload and manage file."""
        try:
            # Log operation
            operation = FileOperation(
                id=f"op_{datetime.utcnow().timestamp()}",
                file_id="",  # Will be updated after upload
                user_id=user_id,
                operation="upload",
                ip_address=ip_address or "unknown",
                user_agent=user_agent or "unknown",
                timestamp=datetime.utcnow(),
                success=False
            )
            
            # Upload file to storage
            success, message, metadata = await self.storage_service.upload_file(
                file_data=file_data,
                filename=filename,
                user_id=user_id,
                access_level=access_level,
                description=description,
                tags=tags
            )
            
            if success and metadata:
                # Store metadata in database
                self.files_db[metadata.id] = metadata
                
                # Update operation log
                operation.file_id = metadata.id
                operation.success = True
                operation.metadata = {
                    'filename': filename,
                    'size': metadata.size,
                    'file_type': metadata.file_type.value
                }
                
                logger.info(f"File uploaded successfully: {metadata.id}")
                
            else:
                operation.error_message = message
            
            self.operations_log.append(operation)
            return success, message, metadata
            
        except Exception as e:
            logger.error(f"File upload error: {str(e)}")
            operation.success = False
            operation.error_message = str(e)
            self.operations_log.append(operation)
            return False, f"Upload failed: {str(e)}", None
    
    async def get_file(self, file_id: str, user_id: str = None) -> Optional[FileMetadata]:
        """Get file metadata with access control."""
        try:
            metadata = self.files_db.get(file_id)
            if not metadata:
                return None
            
            # Check access permissions
            if user_id and not self._check_file_access(metadata, user_id):
                return None
            
            # Update last accessed time
            metadata.last_accessed = datetime.utcnow()
            
            return metadata
            
        except Exception as e:
            logger.error(f"Get file error: {str(e)}")
            return None
    
    async def download_file(
        self, 
        file_id: str, 
        user_id: str,
        ip_address: str = None,
        user_agent: str = None
    ) -> Tuple[bool, str, Optional[bytes], Optional[FileMetadata]]:
        """Download file with access control and logging."""
        try:
            # Get file metadata
            metadata = await self.get_file(file_id, user_id)
            if not metadata:
                return False, "File not found or access denied", None, None
            
            # Check if file is ready
            if metadata.status != FileStatus.READY:
                return False, f"File not ready for download (status: {metadata.status.value})", None, None
            
            # Check virus scan status
            if metadata.scan_status == ScanStatus.INFECTED:
                return False, "File flagged as infected and cannot be downloaded", None, None
            
            # Download from storage
            success, message, file_data = await self.storage_service.download_file(metadata)
            
            if success:
                # Update download count
                metadata.download_count += 1
                metadata.last_accessed = datetime.utcnow()
                
                # Log operation
                operation = FileOperation(
                    id=f"op_{datetime.utcnow().timestamp()}",
                    file_id=file_id,
                    user_id=user_id,
                    operation="download",
                    ip_address=ip_address or "unknown",
                    user_agent=user_agent or "unknown",
                    timestamp=datetime.utcnow(),
                    success=True,
                    metadata={'filename': metadata.original_filename, 'size': metadata.size}
                )
                self.operations_log.append(operation)
                
                logger.info(f"File downloaded: {file_id} by user {user_id}")
            
            return success, message, file_data, metadata
            
        except Exception as e:
            logger.error(f"File download error: {str(e)}")
            return False, f"Download failed: {str(e)}", None, None
    
    async def delete_file(
        self, 
        file_id: str, 
        user_id: str,
        ip_address: str = None,
        user_agent: str = None
    ) -> Tuple[bool, str]:
        """Delete file with access control."""
        try:
            # Get file metadata
            metadata = self.files_db.get(file_id)
            if not metadata:
                return False, "File not found"
            
            # Check ownership or admin rights
            if metadata.user_id != user_id:
                return False, "Access denied - not file owner"
            
            # Delete from storage
            success, message = await self.storage_service.delete_file(metadata)
            
            if success:
                # Update metadata status
                metadata.status = FileStatus.DELETED
                metadata.updated_at = datetime.utcnow()
                
                # Log operation
                operation = FileOperation(
                    id=f"op_{datetime.utcnow().timestamp()}",
                    file_id=file_id,
                    user_id=user_id,
                    operation="delete",
                    ip_address=ip_address or "unknown",
                    user_agent=user_agent or "unknown",
                    timestamp=datetime.utcnow(),
                    success=True,
                    metadata={'filename': metadata.original_filename}
                )
                self.operations_log.append(operation)
                
                logger.info(f"File deleted: {file_id} by user {user_id}")
            
            return success, message
            
        except Exception as e:
            logger.error(f"File deletion error: {str(e)}")
            return False, f"Deletion failed: {str(e)}"
    
    def list_user_files(
        self, 
        user_id: str, 
        page: int = 1, 
        per_page: int = 20,
        file_type: FileType = None,
        status: FileStatus = None,
        search: str = None
    ) -> Dict[str, Any]:
        """List user's files with pagination and filtering."""
        try:
            # Get user's files
            user_files = [
                f for f in self.files_db.values() 
                if f.user_id == user_id and f.status != FileStatus.DELETED
            ]
            
            # Apply filters
            if file_type:
                user_files = [f for f in user_files if f.file_type == file_type]
            
            if status:
                user_files = [f for f in user_files if f.status == status]
            
            if search:
                search_lower = search.lower()
                user_files = [
                    f for f in user_files 
                    if search_lower in f.original_filename.lower() 
                    or search_lower in (f.description or "").lower()
                    or any(search_lower in tag.lower() for tag in f.tags)
                ]
            
            # Sort by creation date (newest first)
            user_files.sort(key=lambda x: x.created_at, reverse=True)
            
            # Pagination
            total_files = len(user_files)
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            paginated_files = user_files[start_idx:end_idx]
            
            return {
                'files': [f.to_dict() for f in paginated_files],
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total_files,
                    'pages': (total_files + per_page - 1) // per_page,
                    'has_prev': page > 1,
                    'has_next': end_idx < total_files
                },
                'filters': {
                    'file_type': file_type.value if file_type else None,
                    'status': status.value if status else None,
                    'search': search
                }
            }
            
        except Exception as e:
            logger.error(f"List files error: {str(e)}")
            return {
                'files': [],
                'pagination': {'page': 1, 'per_page': per_page, 'total': 0, 'pages': 0},
                'error': str(e)
            }
    
    def create_share_link(
        self,
        file_id: str,
        user_id: str,
        expires_in: timedelta = None,
        max_downloads: int = None,
        password: str = None
    ) -> Tuple[bool, str, Optional[ShareLink]]:
        """Create shareable link for file."""
        try:
            # Check if file exists and user has access
            metadata = self.files_db.get(file_id)
            if not metadata:
                return False, "File not found", None
            
            if not self._check_file_access(metadata, user_id):
                return False, "Access denied", None
            
            # Generate share link
            share_link = self.storage_service.generate_share_link(
                file_id=file_id,
                created_by=user_id,
                expires_in=expires_in,
                max_downloads=max_downloads,
                password=password
            )
            
            # Store share link
            self.share_links_db[share_link.token] = share_link
            
            logger.info(f"Share link created for file {file_id} by user {user_id}")
            
            return True, "Share link created successfully", share_link
            
        except Exception as e:
            logger.error(f"Create share link error: {str(e)}")
            return False, f"Failed to create share link: {str(e)}", None
    
    def get_shared_file(self, token: str, password: str = None) -> Tuple[bool, str, Optional[FileMetadata]]:
        """Get file via shared link."""
        try:
            # Get share link
            share_link = self.share_links_db.get(token)
            if not share_link:
                return False, "Invalid share link", None
            
            # Check if link is valid
            if not share_link.is_valid():
                return False, "Share link expired or limit exceeded", None
            
            # Check password if required
            if share_link.password and share_link.password != password:
                return False, "Invalid password", None
            
            # Get file metadata
            metadata = self.files_db.get(share_link.file_id)
            if not metadata or metadata.status == FileStatus.DELETED:
                return False, "File not found", None
            
            # Increment download count for share link
            share_link.download_count += 1
            
            return True, "File accessible via share link", metadata
            
        except Exception as e:
            logger.error(f"Get shared file error: {str(e)}")
            return False, f"Failed to access shared file: {str(e)}", None
    
    def get_file_operations(self, file_id: str, user_id: str) -> List[Dict[str, Any]]:
        """Get file operation history."""
        try:
            # Check file access
            metadata = self.files_db.get(file_id)
            if not metadata or not self._check_file_access(metadata, user_id):
                return []
            
            # Get operations for this file
            file_operations = [
                op.to_dict() for op in self.operations_log 
                if op.file_id == file_id
            ]
            
            # Sort by timestamp (newest first)
            file_operations.sort(key=lambda x: x['timestamp'], reverse=True)
            
            return file_operations
            
        except Exception as e:
            logger.error(f"Get file operations error: {str(e)}")
            return []
    
    def get_file_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get user's file statistics."""
        try:
            user_files = [
                f for f in self.files_db.values() 
                if f.user_id == user_id and f.status != FileStatus.DELETED
            ]
            
            # Calculate statistics
            total_files = len(user_files)
            total_size = sum(f.size for f in user_files)
            
            # Group by file type
            type_stats = {}
            for file_type in FileType:
                type_files = [f for f in user_files if f.file_type == file_type]
                type_stats[file_type.value] = {
                    'count': len(type_files),
                    'size': sum(f.size for f in type_files)
                }
            
            # Recent activity
            recent_files = sorted(user_files, key=lambda x: x.created_at, reverse=True)[:5]
            
            return {
                'total_files': total_files,
                'total_size': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'by_type': type_stats,
                'recent_files': [f.to_dict() for f in recent_files],
                'storage_usage': {
                    'used': total_size,
                    'limit': 1024 * 1024 * 1024,  # 1GB limit for demo
                    'percentage': min(100, (total_size / (1024 * 1024 * 1024)) * 100)
                }
            }
            
        except Exception as e:
            logger.error(f"Get file statistics error: {str(e)}")
            return {'error': str(e)}
    
    def _check_file_access(self, metadata: FileMetadata, user_id: str) -> bool:
        """Check if user has access to file."""
        # Owner always has access
        if metadata.user_id == user_id:
            return True
        
        # Check access level
        if metadata.access_level == AccessLevel.PUBLIC:
            return True
        
        if metadata.access_level == AccessLevel.SHARED:
            return user_id in metadata.shared_with
        
        # Private files only accessible by owner
        return False
    
    def update_file_metadata(
        self,
        file_id: str,
        user_id: str,
        updates: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """Update file metadata."""
        try:
            metadata = self.files_db.get(file_id)
            if not metadata:
                return False, "File not found"
            
            # Check ownership
            if metadata.user_id != user_id:
                return False, "Access denied - not file owner"
            
            # Update allowed fields
            allowed_updates = ['description', 'tags', 'access_level']
            updated = False
            
            for field, value in updates.items():
                if field in allowed_updates:
                    if field == 'access_level':
                        metadata.access_level = AccessLevel(value)
                    else:
                        setattr(metadata, field, value)
                    updated = True
            
            if updated:
                metadata.updated_at = datetime.utcnow()
                logger.info(f"File metadata updated: {file_id}")
                return True, "Metadata updated successfully"
            else:
                return False, "No valid updates provided"
            
        except Exception as e:
            logger.error(f"Update file metadata error: {str(e)}")
            return False, f"Update failed: {str(e)}"
    
    def cleanup_expired_shares(self):
        """Clean up expired share links."""
        try:
            expired_tokens = [
                token for token, link in self.share_links_db.items()
                if link.is_expired()
            ]
            
            for token in expired_tokens:
                del self.share_links_db[token]
            
            if expired_tokens:
                logger.info(f"Cleaned up {len(expired_tokens)} expired share links")
                
        except Exception as e:
            logger.error(f"Cleanup expired shares error: {str(e)}")
    
    def get_system_statistics(self) -> Dict[str, Any]:
        """Get system-wide file statistics (admin only)."""
        try:
            active_files = [f for f in self.files_db.values() if f.status != FileStatus.DELETED]
            
            return {
                'total_files': len(active_files),
                'total_size': sum(f.size for f in active_files),
                'total_users': len(set(f.user_id for f in active_files)),
                'files_by_type': {
                    file_type.value: len([f for f in active_files if f.file_type == file_type])
                    for file_type in FileType
                },
                'files_by_status': {
                    status.value: len([f for f in active_files if f.status == status])
                    for status in FileStatus
                },
                'total_operations': len(self.operations_log),
                'active_share_links': len([l for l in self.share_links_db.values() if l.is_valid()])
            }
            
        except Exception as e:
            logger.error(f"Get system statistics error: {str(e)}")
            return {'error': str(e)}
