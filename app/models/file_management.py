"""
File Management Models
Data models for file storage, metadata, and access control.
"""

from enum import Enum
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
import uuid

class FileType(Enum):
    """Supported file types."""
    IMAGE = "image"
    AUDIO = "audio"
    DOCUMENT = "document"
    ARCHIVE = "archive"
    OTHER = "other"

class FileStatus(Enum):
    """File processing status."""
    UPLOADING = "uploading"
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"
    DELETED = "deleted"

class AccessLevel(Enum):
    """File access levels."""
    PRIVATE = "private"
    SHARED = "shared"
    PUBLIC = "public"

class ScanStatus(Enum):
    """Virus scan status."""
    PENDING = "pending"
    CLEAN = "clean"
    INFECTED = "infected"
    ERROR = "error"

@dataclass
class FileMetadata:
    """File metadata information."""
    id: str
    filename: str
    original_filename: str
    file_type: FileType
    mime_type: str
    size: int
    checksum: str
    user_id: str
    status: FileStatus
    access_level: AccessLevel
    scan_status: ScanStatus
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None
    
    # Storage information
    storage_provider: str = "gcs"
    storage_path: str = ""
    cdn_url: Optional[str] = None
    
    # Processing information
    thumbnails: Dict[str, str] = None  # size -> url mapping
    waveform_data: Optional[str] = None  # For audio files
    extracted_text: Optional[str] = None  # For documents
    
    # Metadata
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[float] = None  # For audio/video
    page_count: Optional[int] = None  # For documents
    
    # Access control
    shared_with: List[str] = None  # User IDs with access
    download_count: int = 0
    last_accessed: Optional[datetime] = None
    
    # Tags and categorization
    tags: List[str] = None
    description: Optional[str] = None
    
    def __post_init__(self):
        """Initialize default values."""
        if self.thumbnails is None:
            self.thumbnails = {}
        if self.shared_with is None:
            self.shared_with = []
        if self.tags is None:
            self.tags = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        
        # Convert enums to values
        data['file_type'] = self.file_type.value
        data['status'] = self.status.value
        data['access_level'] = self.access_level.value
        data['scan_status'] = self.scan_status.value
        
        # Convert datetime objects
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        
        if self.expires_at:
            data['expires_at'] = self.expires_at.isoformat()
        if self.last_accessed:
            data['last_accessed'] = self.last_accessed.isoformat()
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FileMetadata':
        """Create from dictionary."""
        # Convert enum strings back to enums
        data['file_type'] = FileType(data['file_type'])
        data['status'] = FileStatus(data['status'])
        data['access_level'] = AccessLevel(data['access_level'])
        data['scan_status'] = ScanStatus(data['scan_status'])
        
        # Convert datetime strings back to datetime objects
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        
        if data.get('expires_at'):
            data['expires_at'] = datetime.fromisoformat(data['expires_at'])
        if data.get('last_accessed'):
            data['last_accessed'] = datetime.fromisoformat(data['last_accessed'])
        
        return cls(**data)

@dataclass
class ShareLink:
    """Shareable file link."""
    id: str
    file_id: str
    token: str
    created_by: str
    expires_at: datetime
    max_downloads: Optional[int] = None
    download_count: int = 0
    password: Optional[str] = None
    created_at: datetime = None
    
    def __post_init__(self):
        """Initialize default values."""
        if self.created_at is None:
            self.created_at = datetime.utcnow()
    
    def is_expired(self) -> bool:
        """Check if link is expired."""
        return datetime.utcnow() > self.expires_at
    
    def is_download_limit_exceeded(self) -> bool:
        """Check if download limit is exceeded."""
        if self.max_downloads is None:
            return False
        return self.download_count >= self.max_downloads
    
    def is_valid(self) -> bool:
        """Check if link is valid for use."""
        return not self.is_expired() and not self.is_download_limit_exceeded()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'file_id': self.file_id,
            'token': self.token,
            'created_by': self.created_by,
            'expires_at': self.expires_at.isoformat(),
            'max_downloads': self.max_downloads,
            'download_count': self.download_count,
            'password': self.password,
            'created_at': self.created_at.isoformat(),
            'is_expired': self.is_expired(),
            'is_valid': self.is_valid()
        }

@dataclass
class FileOperation:
    """File operation audit log."""
    id: str
    file_id: str
    user_id: str
    operation: str  # upload, download, delete, share, etc.
    ip_address: str
    user_agent: str
    timestamp: datetime
    success: bool
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        """Initialize default values."""
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'file_id': self.file_id,
            'user_id': self.user_id,
            'operation': self.operation,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'timestamp': self.timestamp.isoformat(),
            'success': self.success,
            'error_message': self.error_message,
            'metadata': self.metadata
        }

class FileConfig:
    """File management configuration."""
    
    # File size limits (in bytes)
    SIZE_LIMITS = {
        FileType.IMAGE: 10 * 1024 * 1024,    # 10MB
        FileType.AUDIO: 50 * 1024 * 1024,    # 50MB
        FileType.DOCUMENT: 25 * 1024 * 1024, # 25MB
        FileType.ARCHIVE: 100 * 1024 * 1024, # 100MB
        FileType.OTHER: 5 * 1024 * 1024      # 5MB
    }
    
    # Supported MIME types
    ALLOWED_MIME_TYPES = {
        FileType.IMAGE: [
            'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 
            'image/webp', 'image/bmp', 'image/svg+xml'
        ],
        FileType.AUDIO: [
            'audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/wave',
            'audio/x-wav', 'audio/ogg', 'audio/flac', 'audio/aac'
        ],
        FileType.DOCUMENT: [
            'application/pdf', 'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.ms-powerpoint',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'text/plain', 'text/csv', 'text/rtf'
        ],
        FileType.ARCHIVE: [
            'application/zip', 'application/x-zip-compressed',
            'application/x-rar-compressed', 'application/x-7z-compressed',
            'application/gzip', 'application/x-tar'
        ]
    }
    
    # File extensions mapping
    FILE_EXTENSIONS = {
        '.jpg': FileType.IMAGE, '.jpeg': FileType.IMAGE, '.png': FileType.IMAGE,
        '.gif': FileType.IMAGE, '.webp': FileType.IMAGE, '.bmp': FileType.IMAGE,
        '.svg': FileType.IMAGE,
        
        '.mp3': FileType.AUDIO, '.wav': FileType.AUDIO, '.ogg': FileType.AUDIO,
        '.flac': FileType.AUDIO, '.aac': FileType.AUDIO,
        
        '.pdf': FileType.DOCUMENT, '.doc': FileType.DOCUMENT, '.docx': FileType.DOCUMENT,
        '.xls': FileType.DOCUMENT, '.xlsx': FileType.DOCUMENT,
        '.ppt': FileType.DOCUMENT, '.pptx': FileType.DOCUMENT,
        '.txt': FileType.DOCUMENT, '.csv': FileType.DOCUMENT, '.rtf': FileType.DOCUMENT,
        
        '.zip': FileType.ARCHIVE, '.rar': FileType.ARCHIVE, '.7z': FileType.ARCHIVE,
        '.tar': FileType.ARCHIVE, '.gz': FileType.ARCHIVE
    }
    
    # Thumbnail sizes for images
    THUMBNAIL_SIZES = {
        'small': (150, 150),
        'medium': (300, 300),
        'large': (800, 600)
    }
    
    # CDN settings
    CDN_BASE_URL = "https://cdn.guruai.app"
    
    # Default share link expiration (24 hours)
    DEFAULT_SHARE_EXPIRATION = timedelta(hours=24)
    
    @classmethod
    def get_file_type(cls, filename: str, mime_type: str) -> FileType:
        """Determine file type from filename and MIME type."""
        # Try to determine from file extension first
        ext = '.' + filename.split('.')[-1].lower() if '.' in filename else ''
        if ext in cls.FILE_EXTENSIONS:
            return cls.FILE_EXTENSIONS[ext]
        
        # Fallback to MIME type checking
        for file_type, mime_types in cls.ALLOWED_MIME_TYPES.items():
            if mime_type in mime_types:
                return file_type
        
        return FileType.OTHER
    
    @classmethod
    def is_allowed_file(cls, filename: str, mime_type: str, size: int) -> tuple[bool, str]:
        """Check if file is allowed for upload."""
        file_type = cls.get_file_type(filename, mime_type)
        
        # Check MIME type
        if file_type != FileType.OTHER:
            if mime_type not in cls.ALLOWED_MIME_TYPES[file_type]:
                return False, f"MIME type {mime_type} not allowed for {file_type.value} files"
        
        # Check size limit
        size_limit = cls.SIZE_LIMITS.get(file_type, cls.SIZE_LIMITS[FileType.OTHER])
        if size > size_limit:
            return False, f"File size {size} exceeds limit {size_limit} for {file_type.value} files"
        
        return True, "File is allowed"
