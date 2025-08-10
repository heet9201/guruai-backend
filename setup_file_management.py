#!/usr/bin/env python3
"""
File Management Setup Script
Initialize directories and configure file management system.
"""

import os
import sys
from pathlib import Path

def create_directories():
    """Create necessary directories for file management."""
    base_dir = Path(__file__).parent
    
    directories = [
        'uploads',
        'uploads/images',
        'uploads/documents',
        'uploads/audio',
        'uploads/archives',
        'uploads/temp',
        'uploads/thumbnails',
        'logs',
        'app/utils'
    ]
    
    print("Creating file management directories...")
    
    for directory in directories:
        dir_path = base_dir / directory
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"✓ Created directory: {dir_path}")
    
    # Create .gitkeep files to ensure directories are tracked
    for directory in directories:
        if directory.startswith('uploads'):
            gitkeep_path = base_dir / directory / '.gitkeep'
            gitkeep_path.touch()
            print(f"✓ Created .gitkeep: {gitkeep_path}")

def create_gitignore_entries():
    """Add file management entries to .gitignore."""
    gitignore_path = Path(__file__).parent / '.gitignore'
    
    file_management_entries = [
        "# File Management",
        "uploads/*",
        "!uploads/.gitkeep",
        "!uploads/*/.gitkeep",
        "*.tmp",
        "*.temp",
        "virus_scan_results/",
        ""
    ]
    
    # Read existing .gitignore
    existing_content = ""
    if gitignore_path.exists():
        with open(gitignore_path, 'r') as f:
            existing_content = f.read()
    
    # Check if file management entries already exist
    if "# File Management" not in existing_content:
        print("Adding file management entries to .gitignore...")
        
        with open(gitignore_path, 'a') as f:
            f.write('\n'.join(file_management_entries))
        
        print("✓ Updated .gitignore with file management entries")
    else:
        print("✓ File management entries already present in .gitignore")

def check_dependencies():
    """Check if required dependencies are available."""
    print("\nChecking dependencies...")
    
    required_packages = [
        ('PIL', 'Pillow'),
        ('magic', 'python-magic'),
        ('google.cloud.storage', 'google-cloud-storage')
    ]
    
    missing_packages = []
    
    for import_name, package_name in required_packages:
        try:
            __import__(import_name)
            print(f"✓ {package_name} is available")
        except ImportError:
            print(f"✗ {package_name} is missing")
            missing_packages.append(package_name)
    
    if missing_packages:
        print(f"\nMissing packages: {', '.join(missing_packages)}")
        print("Install them using: pip install " + " ".join(missing_packages))
        return False
    
    return True

def create_sample_config():
    """Create a sample configuration file for file management."""
    config_content = '''"""
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
'''
    
    config_path = Path(__file__).parent / 'file_management_config_sample.py'
    
    with open(config_path, 'w') as f:
        f.write(config_content)
    
    print(f"✓ Created sample configuration: {config_path}")

def main():
    """Main setup function."""
    print("GuruAI File Management Setup")
    print("=" * 40)
    
    try:
        # Create directories
        create_directories()
        
        # Update .gitignore
        create_gitignore_entries()
        
        # Check dependencies
        deps_ok = check_dependencies()
        
        # Create sample config
        create_sample_config()
        
        print("\n" + "=" * 40)
        print("Setup completed!")
        
        if not deps_ok:
            print("\n⚠️  Some dependencies are missing. Please install them before using file management features.")
            sys.exit(1)
        
        print("\nNext steps:")
        print("1. Configure your Google Cloud Storage bucket in .env")
        print("2. Set up virus scanning (optional)")
        print("3. Test file upload functionality")
        print("4. Configure CDN settings if needed")
        
    except Exception as e:
        print(f"\n❌ Setup failed: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
