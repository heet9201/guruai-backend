"""
Security Configuration
Centralized configuration for all security components.
"""

import os
from typing import Dict, Any

class SecurityConfig:
    """Security framework configuration."""
    
    # Authentication Configuration
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-super-secret-jwt-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', '900'))  # 15 minutes
    JWT_REFRESH_TOKEN_EXPIRES = int(os.getenv('JWT_REFRESH_TOKEN_EXPIRES', '604800'))  # 7 days
    JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')
    
    # Multi-Factor Authentication
    MFA_ENABLED = os.getenv('MFA_ENABLED', 'true').lower() == 'true'
    MFA_ISSUER = os.getenv('MFA_ISSUER', 'GuruAI Educational Platform')
    MFA_BACKUP_CODES_COUNT = int(os.getenv('MFA_BACKUP_CODES_COUNT', '10'))
    
    # Session Management
    SESSION_TIMEOUT = int(os.getenv('SESSION_TIMEOUT', '3600'))  # 1 hour
    MAX_SESSIONS_PER_USER = int(os.getenv('MAX_SESSIONS_PER_USER', '5'))
    REMEMBER_ME_DURATION = int(os.getenv('REMEMBER_ME_DURATION', '2592000'))  # 30 days
    
    # Redis Configuration
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
    REDIS_SESSION_DB = int(os.getenv('REDIS_SESSION_DB', '0'))
    REDIS_AUDIT_DB = int(os.getenv('REDIS_AUDIT_DB', '1'))
    REDIS_CONTENT_DB = int(os.getenv('REDIS_CONTENT_DB', '2'))
    REDIS_RATE_LIMIT_DB = int(os.getenv('REDIS_RATE_LIMIT_DB', '3'))
    REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)
    
    # Encryption Configuration
    ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')  # Must be set in production
    PII_ENCRYPTION_KEY = os.getenv('PII_ENCRYPTION_KEY')  # Must be set in production
    PASSWORD_HASH_ITERATIONS = int(os.getenv('PASSWORD_HASH_ITERATIONS', '100000'))
    PASSWORD_MIN_LENGTH = int(os.getenv('PASSWORD_MIN_LENGTH', '8'))
    
    # Rate Limiting Configuration
    RATE_LIMITING_ENABLED = os.getenv('RATE_LIMITING_ENABLED', 'true').lower() == 'true'
    
    # Default rate limits (requests per time window)
    RATE_LIMITS = {
        'api_calls': {
            'per_user': {'limit': int(os.getenv('RATE_LIMIT_USER_API', '1000')), 'window': 'hour'},
            'per_ip': {'limit': int(os.getenv('RATE_LIMIT_IP_API', '5000')), 'window': 'hour'},
            'per_endpoint': {'limit': int(os.getenv('RATE_LIMIT_ENDPOINT_API', '10000')), 'window': 'hour'}
        },
        'login_attempts': {
            'per_user': {'limit': int(os.getenv('RATE_LIMIT_USER_LOGIN', '5')), 'window': 'hour'},
            'per_ip': {'limit': int(os.getenv('RATE_LIMIT_IP_LOGIN', '20')), 'window': 'hour'}
        },
        'content_generation': {
            'per_user': {'limit': int(os.getenv('RATE_LIMIT_USER_CONTENT', '100')), 'window': 'hour'},
            'per_ip': {'limit': int(os.getenv('RATE_LIMIT_IP_CONTENT', '200')), 'window': 'hour'}
        },
        'file_uploads': {
            'per_user': {'limit': int(os.getenv('RATE_LIMIT_USER_UPLOAD', '50')), 'window': 'hour'},
            'per_ip': {'limit': int(os.getenv('RATE_LIMIT_IP_UPLOAD', '100')), 'window': 'hour'}
        }
    }
    
    # Burst protection limits
    BURST_LIMITS = {
        'api_calls': int(os.getenv('BURST_LIMIT_API', '100')),
        'content_generation': int(os.getenv('BURST_LIMIT_CONTENT', '10')),
        'search_queries': int(os.getenv('BURST_LIMIT_SEARCH', '50'))
    }
    
    # Premium user multipliers
    PREMIUM_MULTIPLIERS = {
        'basic': float(os.getenv('RATE_MULTIPLIER_BASIC', '1.0')),
        'premium': float(os.getenv('RATE_MULTIPLIER_PREMIUM', '2.0')),
        'enterprise': float(os.getenv('RATE_MULTIPLIER_ENTERPRISE', '5.0'))
    }
    
    # Content Filtering Configuration
    CONTENT_FILTERING_ENABLED = os.getenv('CONTENT_FILTERING_ENABLED', 'true').lower() == 'true'
    AI_SAFETY_ENABLED = os.getenv('AI_SAFETY_ENABLED', 'true').lower() == 'true'
    AI_SAFETY_THRESHOLD = float(os.getenv('AI_SAFETY_THRESHOLD', '0.7'))
    
    # Content filter severity thresholds
    CONTENT_FILTER_THRESHOLDS = {
        'profanity': {
            'mild': 'flagged',
            'moderate': 'flagged',
            'severe': 'blocked'
        },
        'hate_speech': 'blocked',
        'harassment': 'blocked',
        'spam': 'flagged',
        'academic_dishonesty': 'flagged',
        'child_safety': 'blocked'
    }
    
    # Audit Logging Configuration
    AUDIT_LOGGING_ENABLED = os.getenv('AUDIT_LOGGING_ENABLED', 'true').lower() == 'true'
    AUDIT_LOG_FILE = os.getenv('AUDIT_LOG_FILE', 'logs/audit.log')
    AUDIT_LOG_LEVEL = os.getenv('AUDIT_LOG_LEVEL', 'INFO')
    AUDIT_RETENTION_DAYS = int(os.getenv('AUDIT_RETENTION_DAYS', '90'))
    
    # Security Headers Configuration
    SECURITY_HEADERS_ENABLED = os.getenv('SECURITY_HEADERS_ENABLED', 'true').lower() == 'true'
    CSRF_PROTECTION_ENABLED = os.getenv('CSRF_PROTECTION_ENABLED', 'true').lower() == 'true'
    XSS_PROTECTION_ENABLED = os.getenv('XSS_PROTECTION_ENABLED', 'true').lower() == 'true'
    
    # Content Security Policy
    CSP_POLICY = {
        'default-src': ["'self'"],
        'script-src': ["'self'", "'unsafe-inline'", "'unsafe-eval'"],
        'style-src': ["'self'", "'unsafe-inline'"],
        'img-src': ["'self'", "data:", "https:"],
        'font-src': ["'self'", "https:"],
        'connect-src': ["'self'", "https:"],
        'frame-ancestors': ["'none'"],
        'base-uri': ["'self'"],
        'form-action': ["'self'"]
    }
    
    # File Upload Security
    MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', '10485760'))  # 10MB
    ALLOWED_FILE_EXTENSIONS = os.getenv(
        'ALLOWED_FILE_EXTENSIONS', 
        'txt,pdf,doc,docx,xls,xlsx,ppt,pptx,jpg,jpeg,png,gif,mp3,mp4,zip'
    ).split(',')
    
    # Blocked file types (security risk)
    BLOCKED_FILE_EXTENSIONS = [
        'exe', 'bat', 'cmd', 'scr', 'pif', 'com', 'vbs', 'js', 'jar',
        'php', 'asp', 'aspx', 'jsp', 'sh', 'py', 'rb', 'pl'
    ]
    
    # IP Blocking Configuration
    AUTO_BLOCK_ENABLED = os.getenv('AUTO_BLOCK_ENABLED', 'true').lower() == 'true'
    AUTO_BLOCK_THRESHOLD = int(os.getenv('AUTO_BLOCK_THRESHOLD', '10'))  # Failed attempts
    AUTO_BLOCK_DURATION = int(os.getenv('AUTO_BLOCK_DURATION', '3600'))  # 1 hour
    
    # Trusted IP ranges (CIDR notation)
    TRUSTED_IPS = os.getenv('TRUSTED_IPS', '').split(',') if os.getenv('TRUSTED_IPS') else []
    
    # Security Monitoring
    SECURITY_MONITORING_ENABLED = os.getenv('SECURITY_MONITORING_ENABLED', 'true').lower() == 'true'
    ALERT_EMAIL = os.getenv('SECURITY_ALERT_EMAIL', 'admin@example.com')
    HIGH_RISK_ALERT_THRESHOLD = int(os.getenv('HIGH_RISK_ALERT_THRESHOLD', '5'))
    
    # GDPR Compliance
    GDPR_ENABLED = os.getenv('GDPR_ENABLED', 'true').lower() == 'true'
    DATA_RETENTION_DAYS = int(os.getenv('DATA_RETENTION_DAYS', '2555'))  # 7 years
    COOKIE_CONSENT_REQUIRED = os.getenv('COOKIE_CONSENT_REQUIRED', 'true').lower() == 'true'
    
    # Development/Debug Settings
    DEBUG_MODE = os.getenv('FLASK_ENV', 'production') == 'development'
    SECURITY_DEBUG = os.getenv('SECURITY_DEBUG', 'false').lower() == 'true'
    
    @classmethod
    def validate_config(cls) -> Dict[str, Any]:
        """Validate security configuration and return any issues."""
        issues = []
        warnings = []
        
        # Critical security checks
        if cls.JWT_SECRET_KEY == 'your-super-secret-jwt-key-change-in-production':
            issues.append("JWT_SECRET_KEY must be changed from default value")
        
        if not cls.ENCRYPTION_KEY:
            issues.append("ENCRYPTION_KEY must be set for data encryption")
        
        if not cls.PII_ENCRYPTION_KEY:
            issues.append("PII_ENCRYPTION_KEY must be set for PII encryption")
        
        if cls.PASSWORD_HASH_ITERATIONS < 50000:
            warnings.append("PASSWORD_HASH_ITERATIONS should be at least 50,000")
        
        if cls.PASSWORD_MIN_LENGTH < 8:
            warnings.append("PASSWORD_MIN_LENGTH should be at least 8 characters")
        
        if cls.DEBUG_MODE and not cls.SECURITY_DEBUG:
            warnings.append("Consider enabling SECURITY_DEBUG in development")
        
        # Check required directories
        import os
        log_dir = os.path.dirname(cls.AUDIT_LOG_FILE)
        if not os.path.exists(log_dir):
            warnings.append(f"Audit log directory does not exist: {log_dir}")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings
        }
    
    @classmethod
    def get_redis_config(cls, db_type: str) -> Dict[str, Any]:
        """Get Redis configuration for specific database type."""
        db_mapping = {
            'session': cls.REDIS_SESSION_DB,
            'audit': cls.REDIS_AUDIT_DB,
            'content': cls.REDIS_CONTENT_DB,
            'rate_limit': cls.REDIS_RATE_LIMIT_DB
        }
        
        return {
            'host': cls.REDIS_HOST,
            'port': cls.REDIS_PORT,
            'db': db_mapping.get(db_type, 0),
            'password': cls.REDIS_PASSWORD,
            'decode_responses': True
        }
    
    @classmethod
    def get_csp_header(cls) -> str:
        """Generate Content Security Policy header string."""
        csp_parts = []
        for directive, sources in cls.CSP_POLICY.items():
            sources_str = ' '.join(sources)
            csp_parts.append(f"{directive.replace('_', '-')} {sources_str}")
        return '; '.join(csp_parts)

# Environment-specific configurations
class DevelopmentSecurityConfig(SecurityConfig):
    """Development environment security configuration."""
    
    # More lenient settings for development
    JWT_ACCESS_TOKEN_EXPIRES = 3600  # 1 hour
    RATE_LIMITING_ENABLED = False
    CONTENT_FILTERING_ENABLED = False
    CSRF_PROTECTION_ENABLED = False
    SECURITY_DEBUG = True

class ProductionSecurityConfig(SecurityConfig):
    """Production environment security configuration."""
    
    # Strict settings for production
    JWT_ACCESS_TOKEN_EXPIRES = 900  # 15 minutes
    RATE_LIMITING_ENABLED = True
    CONTENT_FILTERING_ENABLED = True
    CSRF_PROTECTION_ENABLED = True
    AUTO_BLOCK_ENABLED = True
    
    # Ensure critical settings are configured
    @classmethod
    def validate_config(cls):
        result = super().validate_config()
        
        # Additional production checks
        if cls.DEBUG_MODE:
            result['issues'].append("DEBUG_MODE must be False in production")
        
        if not cls.REDIS_PASSWORD:
            result['warnings'].append("Consider setting REDIS_PASSWORD for production")
        
        return result

class TestingSecurityConfig(SecurityConfig):
    """Testing environment security configuration."""
    
    # Fast, minimal settings for testing
    JWT_ACCESS_TOKEN_EXPIRES = 300  # 5 minutes
    PASSWORD_HASH_ITERATIONS = 1000  # Faster for tests
    RATE_LIMITING_ENABLED = False
    CONTENT_FILTERING_ENABLED = False
    AUDIT_LOGGING_ENABLED = False

# Configuration factory
def get_security_config(environment: str = None) -> SecurityConfig:
    """Get security configuration for specified environment."""
    
    if environment is None:
        environment = os.getenv('FLASK_ENV', 'production')
    
    config_mapping = {
        'development': DevelopmentSecurityConfig,
        'production': ProductionSecurityConfig,
        'testing': TestingSecurityConfig
    }
    
    config_class = config_mapping.get(environment, ProductionSecurityConfig)
    return config_class()
