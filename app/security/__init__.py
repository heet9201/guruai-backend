"""
Security Framework Module
Comprehensive security utilities for authentication, encryption, content filtering, and protection.
"""

from .auth_manager import AuthManager
from .crypto_manager import CryptoManager
from .audit_logger import AuditLogger, AuditEventType, AuditSeverity
from .content_filter import ContentFilter, ContentType, FilterResult, ContentCategory
from .rate_limiter import RateLimiter, RateLimitType, RateLimitResult
from .error_handler import (
    SecurityErrorHandler, 
    SecurityError, 
    AuthenticationError, 
    AuthorizationError,
    RateLimitError,
    ContentFilterError,
    ValidationError,
    SecurityViolationError,
    SecurityErrorCode,
    security_error_handler,
    raise_authentication_error,
    raise_authorization_error,
    raise_rate_limit_error,
    raise_content_filter_error,
    raise_validation_error,
    raise_security_violation
)

__all__ = [
    # Core managers
    'AuthManager',
    'CryptoManager',
    'AuditLogger',
    'ContentFilter',
    'RateLimiter',
    'SecurityErrorHandler',
    
    # Enums and types
    'AuditEventType',
    'AuditSeverity',
    'ContentType',
    'FilterResult',
    'ContentCategory',
    'RateLimitType',
    'RateLimitResult',
    'SecurityErrorCode',
    
    # Exception classes
    'SecurityError',
    'AuthenticationError',
    'AuthorizationError',
    'RateLimitError',
    'ContentFilterError',
    'ValidationError',
    'SecurityViolationError',
    
    # Global instances and utilities
    'security_error_handler',
    'raise_authentication_error',
    'raise_authorization_error',
    'raise_rate_limit_error',
    'raise_content_filter_error',
    'raise_validation_error',
    'raise_security_violation'
]

from .auth_manager import AuthManager
from .crypto_manager import CryptoManager
from .audit_logger import AuditLogger
from .content_filter import ContentFilter
from .rate_limiter import RateLimiter
from .error_handler import SecurityErrorHandler

__all__ = [
    'AuthManager',
    'CryptoManager', 
    'AuditLogger',
    'ContentFilter',
    'RateLimiter',
    'SecurityErrorHandler'
]
