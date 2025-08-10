"""
File Storage Service
Handles file upload, storage, and retrieval with Google Cloud Storage.
"""

import os
import hashlib
import uuid
import logging
from typing import Optional, Dict, Any, List, Tuple, BinaryIO
from datetime import datetime, timedelta
from io import BytesIO
import magic
from PIL import Image, ImageOps
import requests

# Google Cloud Storage
try:
    from google.cloud import storage
    from google.cloud.storage import Blob
    GCS_AVAILABLE = True
except ImportError:
    GCS_AVAILABLE = False
    storage = None
    Blob = None

from app.models.file_management import (
    FileMetadata, FileType, FileStatus, AccessLevel, ScanStatus,
    ShareLink, FileOperation, FileConfig
)

logger = logging.getLogger(__name__)

class FileStorageService:
    """Service for file storage and management."""
    
    def __init__(self, bucket_name: str = None, cdn_base_url: str = None):
        """Initialize file storage service."""
        self.bucket_name = bucket_name or os.getenv('GCS_BUCKET_NAME', 'guruai-files')
        self.cdn_base_url = cdn_base_url or FileConfig.CDN_BASE_URL
        
        # Initialize Google Cloud Storage client
        if GCS_AVAILABLE:
            try:
                self.gcs_client = storage.Client()
                self.bucket = self.gcs_client.bucket(self.bucket_name)
                logger.info(f"Initialized GCS client with bucket: {self.bucket_name}")
            except Exception as e:
                logger.error(f"Failed to initialize GCS client: {str(e)}")
                self.gcs_client = None
                self.bucket = None
        else:
            logger.warning("Google Cloud Storage not available, using local storage fallback")
            self.gcs_client = None
            self.bucket = None
        
        # Local storage fallback
        self.local_storage_path = os.getenv('LOCAL_STORAGE_PATH', './uploads')
        os.makedirs(self.local_storage_path, exist_ok=True)
    
    def generate_file_id(self) -> str:
        """Generate unique file ID."""
        return str(uuid.uuid4())
    
    def generate_filename(self, original_filename: str, file_id: str) -> str:
        """Generate secure filename."""
        # Extract extension
        ext = os.path.splitext(original_filename)[1].lower()
        # Use file ID as base name for security
        return f"{file_id}{ext}"
    
    def calculate_checksum(self, file_data: bytes) -> str:
        """Calculate file checksum."""
        return hashlib.sha256(file_data).hexdigest()
    
    def detect_mime_type(self, file_data: bytes, filename: str) -> str:
        """Detect MIME type from file data."""
        try:
            mime = magic.from_buffer(file_data, mime=True)
            return mime
        except Exception as e:
            logger.warning(f"Failed to detect MIME type: {str(e)}")
            # Fallback to extension-based detection
            ext = os.path.splitext(filename)[1].lower()
            mime_map = {
                '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
                '.png': 'image/png', '.gif': 'image/gif',
                '.mp3': 'audio/mpeg', '.wav': 'audio/wav',
                '.pdf': 'application/pdf', '.txt': 'text/plain',
                '.zip': 'application/zip'
            }
            return mime_map.get(ext, 'application/octet-stream')
    
    def validate_file(self, file_data: bytes, filename: str, user_id: str) -> Tuple[bool, str, Dict[str, Any]]:
        """Validate uploaded file."""
        try:
            # Detect MIME type
            mime_type = self.detect_mime_type(file_data, filename)
            file_size = len(file_data)
            
            # Check if file is allowed
            is_allowed, message = FileConfig.is_allowed_file(filename, mime_type, file_size)
            if not is_allowed:
                return False, message, {}
            
            # Additional security checks
            if file_size == 0:
                return False, "Empty file not allowed", {}
            
            # Check for malicious patterns (basic)
            if self._contains_malicious_patterns(file_data):
                return False, "File contains potentially malicious content", {}
            
            # Prepare metadata
            metadata = {
                'mime_type': mime_type,
                'size': file_size,
                'file_type': FileConfig.get_file_type(filename, mime_type).value
            }
            
            return True, "File validation passed", metadata
            
        except Exception as e:
            logger.error(f"File validation error: {str(e)}")
            return False, f"Validation error: {str(e)}", {}
    
    def _contains_malicious_patterns(self, file_data: bytes) -> bool:
        """Basic malicious pattern detection."""
        # Check for common malicious patterns
        malicious_patterns = [
            b'<script', b'javascript:', b'vbscript:', 
            b'<?php', b'<%', b'#!/bin/sh'
        ]
        
        # Check first 1KB for patterns
        sample = file_data[:1024].lower()
        return any(pattern in sample for pattern in malicious_patterns)
    
    async def upload_file(
        self, 
        file_data: bytes, 
        filename: str, 
        user_id: str,
        access_level: AccessLevel = AccessLevel.PRIVATE,
        description: str = None,
        tags: List[str] = None
    ) -> Tuple[bool, str, Optional[FileMetadata]]:
        """Upload file to storage."""
        try:
            # Validate file
            is_valid, message, validation_metadata = self.validate_file(file_data, filename, user_id)
            if not is_valid:
                return False, message, None
            
            # Generate file metadata
            file_id = self.generate_file_id()
            secure_filename = self.generate_filename(filename, file_id)
            checksum = self.calculate_checksum(file_data)
            file_type = FileType(validation_metadata['file_type'])
            
            # Create file metadata
            metadata = FileMetadata(
                id=file_id,
                filename=secure_filename,
                original_filename=filename,
                file_type=file_type,
                mime_type=validation_metadata['mime_type'],
                size=validation_metadata['size'],
                checksum=checksum,
                user_id=user_id,
                status=FileStatus.UPLOADING,
                access_level=access_level,
                scan_status=ScanStatus.PENDING,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                description=description,
                tags=tags or []
            )
            
            # Upload to storage
            storage_path = f"files/{user_id}/{file_id[:2]}/{secure_filename}"
            
            if self.bucket:
                # Upload to Google Cloud Storage
                success = await self._upload_to_gcs(file_data, storage_path, metadata.mime_type)
            else:
                # Fallback to local storage
                success = await self._upload_to_local(file_data, storage_path)
            
            if not success:
                return False, "Failed to upload file to storage", None
            
            # Update metadata with storage info
            metadata.storage_path = storage_path
            metadata.storage_provider = "gcs" if self.bucket else "local"
            metadata.status = FileStatus.PROCESSING
            
            # Generate CDN URL if using GCS
            if self.bucket:
                metadata.cdn_url = f"{self.cdn_base_url}/{storage_path}"
            
            # Start background processing
            await self._process_file_async(metadata, file_data)
            
            return True, "File uploaded successfully", metadata
            
        except Exception as e:
            logger.error(f"File upload error: {str(e)}")
            return False, f"Upload failed: {str(e)}", None
    
    async def _upload_to_gcs(self, file_data: bytes, storage_path: str, mime_type: str) -> bool:
        """Upload file to Google Cloud Storage."""
        try:
            blob = self.bucket.blob(storage_path)
            blob.upload_from_string(
                file_data,
                content_type=mime_type
            )
            
            # Set cache control for CDN
            blob.cache_control = "public, max-age=86400"  # 24 hours
            blob.patch()
            
            logger.info(f"Uploaded file to GCS: {storage_path}")
            return True
            
        except Exception as e:
            logger.error(f"GCS upload error: {str(e)}")
            return False
    
    async def _upload_to_local(self, file_data: bytes, storage_path: str) -> bool:
        """Upload file to local storage."""
        try:
            full_path = os.path.join(self.local_storage_path, storage_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            with open(full_path, 'wb') as f:
                f.write(file_data)
            
            logger.info(f"Uploaded file to local storage: {full_path}")
            return True
            
        except Exception as e:
            logger.error(f"Local upload error: {str(e)}")
            return False
    
    async def _process_file_async(self, metadata: FileMetadata, file_data: bytes):
        """Process file in background (thumbnails, metadata extraction, etc.)."""
        try:
            # Process based on file type
            if metadata.file_type == FileType.IMAGE:
                await self._process_image(metadata, file_data)
            elif metadata.file_type == FileType.AUDIO:
                await self._process_audio(metadata, file_data)
            elif metadata.file_type == FileType.DOCUMENT:
                await self._process_document(metadata, file_data)
            
            # Update status
            metadata.status = FileStatus.READY
            metadata.updated_at = datetime.utcnow()
            
            # Scan for viruses (placeholder - integrate with actual service)
            metadata.scan_status = await self._scan_file(file_data)
            
            logger.info(f"File processing completed: {metadata.id}")
            
        except Exception as e:
            logger.error(f"File processing error: {str(e)}")
            metadata.status = FileStatus.ERROR
            metadata.updated_at = datetime.utcnow()
    
    async def _process_image(self, metadata: FileMetadata, file_data: bytes):
        """Process image file (generate thumbnails, extract metadata)."""
        try:
            image = Image.open(BytesIO(file_data))
            
            # Extract dimensions
            metadata.width, metadata.height = image.size
            
            # Generate thumbnails
            for size_name, (width, height) in FileConfig.THUMBNAIL_SIZES.items():
                thumbnail = self._generate_thumbnail(image, width, height)
                if thumbnail:
                    # Upload thumbnail
                    thumb_path = f"thumbnails/{metadata.user_id}/{metadata.id}_{size_name}.jpg"
                    
                    if self.bucket:
                        success = await self._upload_thumbnail_to_gcs(thumbnail, thumb_path)
                    else:
                        success = await self._upload_thumbnail_to_local(thumbnail, thumb_path)
                    
                    if success:
                        metadata.thumbnails[size_name] = f"{self.cdn_base_url}/{thumb_path}"
            
        except Exception as e:
            logger.error(f"Image processing error: {str(e)}")
    
    def _generate_thumbnail(self, image: Image.Image, width: int, height: int) -> Optional[bytes]:
        """Generate thumbnail from image."""
        try:
            # Use ImageOps.fit for better thumbnails
            thumbnail = ImageOps.fit(image, (width, height), Image.Resampling.LANCZOS)
            
            # Convert to RGB if necessary
            if thumbnail.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', thumbnail.size, (255, 255, 255))
                if thumbnail.mode == 'P':
                    thumbnail = thumbnail.convert('RGBA')
                background.paste(thumbnail, mask=thumbnail.split()[-1] if thumbnail.mode == 'RGBA' else None)
                thumbnail = background
            
            # Save to bytes
            output = BytesIO()
            thumbnail.save(output, format='JPEG', quality=85, optimize=True)
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Thumbnail generation error: {str(e)}")
            return None
    
    async def _upload_thumbnail_to_gcs(self, thumbnail_data: bytes, path: str) -> bool:
        """Upload thumbnail to GCS."""
        try:
            blob = self.bucket.blob(path)
            blob.upload_from_string(thumbnail_data, content_type='image/jpeg')
            blob.cache_control = "public, max-age=31536000"  # 1 year
            blob.patch()
            return True
        except Exception as e:
            logger.error(f"Thumbnail GCS upload error: {str(e)}")
            return False
    
    async def _upload_thumbnail_to_local(self, thumbnail_data: bytes, path: str) -> bool:
        """Upload thumbnail to local storage."""
        try:
            full_path = os.path.join(self.local_storage_path, path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            with open(full_path, 'wb') as f:
                f.write(thumbnail_data)
            return True
        except Exception as e:
            logger.error(f"Thumbnail local upload error: {str(e)}")
            return False
    
    async def _process_audio(self, metadata: FileMetadata, file_data: bytes):
        """Process audio file (extract metadata, generate waveform)."""
        try:
            # Placeholder for audio processing
            # You could use libraries like librosa, pydub, or wave
            # to extract duration, generate waveforms, etc.
            
            # For now, just set a placeholder duration
            metadata.duration = 0.0
            
            # Generate waveform data (placeholder)
            metadata.waveform_data = "[]"  # JSON array of waveform points
            
        except Exception as e:
            logger.error(f"Audio processing error: {str(e)}")
    
    async def _process_document(self, metadata: FileMetadata, file_data: bytes):
        """Process document file (extract text, count pages)."""
        try:
            # Placeholder for document processing
            # You could use libraries like PyPDF2, python-docx, etc.
            # to extract text and metadata
            
            # For now, just set placeholder values
            metadata.page_count = 1
            metadata.extracted_text = ""
            
        except Exception as e:
            logger.error(f"Document processing error: {str(e)}")
    
    async def _scan_file(self, file_data: bytes) -> ScanStatus:
        """Scan file for viruses (placeholder)."""
        try:
            # Placeholder for virus scanning
            # You could integrate with services like VirusTotal, ClamAV, etc.
            
            # For now, assume all files are clean
            return ScanStatus.CLEAN
            
        except Exception as e:
            logger.error(f"File scanning error: {str(e)}")
            return ScanStatus.ERROR
    
    async def download_file(self, metadata: FileMetadata) -> Tuple[bool, str, Optional[bytes]]:
        """Download file from storage."""
        try:
            if self.bucket:
                return await self._download_from_gcs(metadata.storage_path)
            else:
                return await self._download_from_local(metadata.storage_path)
                
        except Exception as e:
            logger.error(f"File download error: {str(e)}")
            return False, f"Download failed: {str(e)}", None
    
    async def _download_from_gcs(self, storage_path: str) -> Tuple[bool, str, Optional[bytes]]:
        """Download file from Google Cloud Storage."""
        try:
            blob = self.bucket.blob(storage_path)
            if not blob.exists():
                return False, "File not found in storage", None
            
            file_data = blob.download_as_bytes()
            return True, "File downloaded successfully", file_data
            
        except Exception as e:
            logger.error(f"GCS download error: {str(e)}")
            return False, f"GCS download failed: {str(e)}", None
    
    async def _download_from_local(self, storage_path: str) -> Tuple[bool, str, Optional[bytes]]:
        """Download file from local storage."""
        try:
            full_path = os.path.join(self.local_storage_path, storage_path)
            
            if not os.path.exists(full_path):
                return False, "File not found in storage", None
            
            with open(full_path, 'rb') as f:
                file_data = f.read()
            
            return True, "File downloaded successfully", file_data
            
        except Exception as e:
            logger.error(f"Local download error: {str(e)}")
            return False, f"Local download failed: {str(e)}", None
    
    async def delete_file(self, metadata: FileMetadata) -> Tuple[bool, str]:
        """Delete file from storage."""
        try:
            if self.bucket:
                success, message = await self._delete_from_gcs(metadata.storage_path)
            else:
                success, message = await self._delete_from_local(metadata.storage_path)
            
            if success:
                # Also delete thumbnails
                await self._delete_thumbnails(metadata)
            
            return success, message
            
        except Exception as e:
            logger.error(f"File deletion error: {str(e)}")
            return False, f"Deletion failed: {str(e)}"
    
    async def _delete_from_gcs(self, storage_path: str) -> Tuple[bool, str]:
        """Delete file from Google Cloud Storage."""
        try:
            blob = self.bucket.blob(storage_path)
            if blob.exists():
                blob.delete()
            return True, "File deleted from GCS"
        except Exception as e:
            logger.error(f"GCS deletion error: {str(e)}")
            return False, f"GCS deletion failed: {str(e)}"
    
    async def _delete_from_local(self, storage_path: str) -> Tuple[bool, str]:
        """Delete file from local storage."""
        try:
            full_path = os.path.join(self.local_storage_path, storage_path)
            if os.path.exists(full_path):
                os.remove(full_path)
            return True, "File deleted from local storage"
        except Exception as e:
            logger.error(f"Local deletion error: {str(e)}")
            return False, f"Local deletion failed: {str(e)}"
    
    async def _delete_thumbnails(self, metadata: FileMetadata):
        """Delete associated thumbnails."""
        for size_name in metadata.thumbnails.keys():
            thumb_path = f"thumbnails/{metadata.user_id}/{metadata.id}_{size_name}.jpg"
            try:
                if self.bucket:
                    blob = self.bucket.blob(thumb_path)
                    if blob.exists():
                        blob.delete()
                else:
                    full_path = os.path.join(self.local_storage_path, thumb_path)
                    if os.path.exists(full_path):
                        os.remove(full_path)
            except Exception as e:
                logger.error(f"Thumbnail deletion error: {str(e)}")
    
    def generate_share_link(
        self, 
        file_id: str, 
        created_by: str,
        expires_in: timedelta = None,
        max_downloads: int = None,
        password: str = None
    ) -> ShareLink:
        """Generate shareable link for file."""
        if expires_in is None:
            expires_in = FileConfig.DEFAULT_SHARE_EXPIRATION
        
        share_link = ShareLink(
            id=str(uuid.uuid4()),
            file_id=file_id,
            token=str(uuid.uuid4()),
            created_by=created_by,
            expires_at=datetime.utcnow() + expires_in,
            max_downloads=max_downloads,
            password=password
        )
        
        return share_link
