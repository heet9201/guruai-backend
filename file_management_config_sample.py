"""
File Management Configuration Sample
Copy these settings to your main config.py or environment variables.
"""

# File Management Settings
FILE_MANAGEMENT_CONFIG = {
    # Storage Settings
    'GOOGLE_CLOUD_STORAGE_BUCKET': 'your-bucket-name',
    'LOCAL_STORAGE_PATH': 'uploads',
    'CDN_BASE_URL': 'https://your-cdn-domain.com',
    'ENABLE_CDN': False,
    
    # File Upload Limits
    'MAX_FILE_SIZE': 100 * 1024 * 1024,  # 100MB
    'ALLOWED_EXTENSIONS': {
        'images': ['jpg', 'jpeg', 'png', 'gif', 'webp'],
        'documents': ['pdf', 'txt', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'],
        'audio': ['mp3', 'wav', 'ogg', 'flac'],
        'archives': ['zip', 'rar', '7z', 'tar', 'gz']
    },
    
    # Security Settings
    'ENABLE_VIRUS_SCANNING': False,
    'VIRUSTOTAL_API_KEY': 'your-api-key',
    'QUARANTINE_INFECTED_FILES': True,
    
    # Performance Settings
    'THUMBNAIL_SIZES': [(150, 150), (300, 300), (800, 600)],
    'ENABLE_COMPRESSION': True,
    'COMPRESSION_QUALITY': 85,
    
    # Access Control
    'DEFAULT_ACCESS_LEVEL': 'private',
    'ENABLE_SHARE_LINKS': True,
    'SHARE_LINK_EXPIRY_DAYS': 30,
    
    # Monitoring
    'ENABLE_AUDIT_LOGGING': True,
    'LOG_FILE_OPERATIONS': True,
    'METRICS_COLLECTION': True
}
