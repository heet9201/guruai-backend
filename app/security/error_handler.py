"""
Security Error Handler
Standardized error response format with proper HTTP status codes.
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from flask import jsonify, request, g
from werkzeug.exceptions import HTTPException

class SecurityErrorCode:
    # Authentication errors (4xx)
    INVALID_TOKEN = "AUTH_001"
    EXPIRED_TOKEN = "AUTH_002"
    MISSING_TOKEN = "AUTH_003"
    INVALID_CREDENTIALS = "AUTH_004"
    ACCOUNT_LOCKED = "AUTH_005"
    MFA_REQUIRED = "AUTH_006"
    INVALID_MFA_CODE = "AUTH_007"
    SESSION_EXPIRED = "AUTH_008"
    DEVICE_NOT_RECOGNIZED = "AUTH_009"
    
    # Authorization errors (4xx)
    INSUFFICIENT_PERMISSIONS = "AUTHZ_001"
    ACCESS_DENIED = "AUTHZ_002"
    RESOURCE_FORBIDDEN = "AUTHZ_003"
    ROLE_REQUIRED = "AUTHZ_004"
    
    # Rate limiting errors (4xx)
    RATE_LIMIT_EXCEEDED = "RATE_001"
    TOO_MANY_REQUESTS = "RATE_002"
    IP_BLOCKED = "RATE_003"
    BURST_LIMIT_EXCEEDED = "RATE_004"
    
    # Content filtering errors (4xx)
    CONTENT_BLOCKED = "CONTENT_001"
    INAPPROPRIATE_CONTENT = "CONTENT_002"
    SPAM_DETECTED = "CONTENT_003"
    CONTENT_FLAGGED = "CONTENT_004"
    
    # Input validation errors (4xx)
    INVALID_INPUT = "INPUT_001"
    MISSING_REQUIRED_FIELD = "INPUT_002"
    INVALID_FORMAT = "INPUT_003"
    INVALID_FILE_TYPE = "INPUT_004"
    FILE_TOO_LARGE = "INPUT_005"
    
    # Security violation errors (4xx/5xx)
    SECURITY_VIOLATION = "SEC_001"
    SUSPICIOUS_ACTIVITY = "SEC_002"
    INJECTION_ATTEMPT = "SEC_003"
    XSS_ATTEMPT = "SEC_004"
    CSRF_VIOLATION = "SEC_005"
    
    # System errors (5xx)
    INTERNAL_ERROR = "SYS_001"
    SERVICE_UNAVAILABLE = "SYS_002"
    DATABASE_ERROR = "SYS_003"
    EXTERNAL_SERVICE_ERROR = "SYS_004"
    CONFIGURATION_ERROR = "SYS_005"

class SecurityError(Exception):
    """Base security exception class."""
    
    def __init__(self, 
                 message: str, 
                 error_code: str, 
                 status_code: int = 400,
                 details: Optional[Dict[str, Any]] = None,
                 user_message: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        self.user_message = user_message or self._get_user_friendly_message(error_code)
    
    def _get_user_friendly_message(self, error_code: str) -> str:
        """Get user-friendly error message."""
        messages = {
            SecurityErrorCode.INVALID_TOKEN: "Your session has expired. Please log in again.",
            SecurityErrorCode.EXPIRED_TOKEN: "Your session has expired. Please log in again.",
            SecurityErrorCode.MISSING_TOKEN: "Authentication required. Please log in.",
            SecurityErrorCode.INVALID_CREDENTIALS: "Invalid username or password.",
            SecurityErrorCode.ACCOUNT_LOCKED: "Your account has been temporarily locked. Please try again later.",
            SecurityErrorCode.MFA_REQUIRED: "Multi-factor authentication is required.",
            SecurityErrorCode.INVALID_MFA_CODE: "Invalid authentication code. Please try again.",
            SecurityErrorCode.RATE_LIMIT_EXCEEDED: "Too many requests. Please slow down and try again later.",
            SecurityErrorCode.CONTENT_BLOCKED: "Your content violates our community guidelines.",
            SecurityErrorCode.INVALID_INPUT: "Invalid input provided. Please check your data.",
            SecurityErrorCode.SECURITY_VIOLATION: "Security violation detected. This incident has been logged.",
            SecurityErrorCode.INTERNAL_ERROR: "An internal error occurred. Please try again later."
        }
        return messages.get(error_code, "An error occurred. Please try again.")

class AuthenticationError(SecurityError):
    """Authentication-related errors."""
    
    def __init__(self, message: str, error_code: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code, 401, details)

class AuthorizationError(SecurityError):
    """Authorization-related errors."""
    
    def __init__(self, message: str, error_code: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code, 403, details)

class RateLimitError(SecurityError):
    """Rate limiting errors."""
    
    def __init__(self, message: str, error_code: str, retry_after: int = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code, 429, details)
        self.retry_after = retry_after

class ContentFilterError(SecurityError):
    """Content filtering errors."""
    
    def __init__(self, message: str, error_code: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code, 400, details)

class ValidationError(SecurityError):
    """Input validation errors."""
    
    def __init__(self, message: str, error_code: str, field: str = None, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        if field:
            details['field'] = field
        super().__init__(message, error_code, 400, details)

class SecurityViolationError(SecurityError):
    """Security violation errors."""
    
    def __init__(self, message: str, error_code: str, severity: str = "medium", details: Optional[Dict[str, Any]] = None):
        status_code = 403 if severity in ["low", "medium"] else 500
        details = details or {}
        details['severity'] = severity
        super().__init__(message, error_code, status_code, details)

class SecurityErrorHandler:
    """Centralized security error handling."""
    
    def __init__(self):
        self.logger = logging.getLogger('security_error_handler')
        self.error_tracking = {}
    
    def handle_error(self, error: Exception) -> tuple:
        """
        Handle security error and return appropriate response.
        
        Returns:
            tuple: (response_dict, status_code, headers)
        """
        
        # Generate error ID for tracking
        error_id = self._generate_error_id()
        
        # Extract error information
        if isinstance(error, SecurityError):
            error_info = self._handle_security_error(error, error_id)
        elif isinstance(error, HTTPException):
            error_info = self._handle_http_error(error, error_id)
        else:
            error_info = self._handle_generic_error(error, error_id)
        
        # Log the error
        self._log_error(error_info, error)
        
        # Track error patterns
        self._track_error_pattern(error_info)
        
        # Build response
        response = self._build_error_response(error_info)
        headers = self._build_error_headers(error_info)
        
        return response, error_info['status_code'], headers
    
    def _handle_security_error(self, error: SecurityError, error_id: str) -> Dict[str, Any]:
        """Handle SecurityError instances."""
        
        return {
            'error_id': error_id,
            'error_code': error.error_code,
            'message': error.message,
            'user_message': error.user_message,
            'status_code': error.status_code,
            'details': error.details,
            'timestamp': datetime.utcnow().isoformat(),
            'type': 'security_error',
            'retry_after': getattr(error, 'retry_after', None)
        }
    
    def _handle_http_error(self, error: HTTPException, error_id: str) -> Dict[str, Any]:
        """Handle HTTP exceptions."""
        
        # Map HTTP status codes to security error codes
        status_to_error_code = {
            400: SecurityErrorCode.INVALID_INPUT,
            401: SecurityErrorCode.INVALID_TOKEN,
            403: SecurityErrorCode.ACCESS_DENIED,
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            413: SecurityErrorCode.FILE_TOO_LARGE,
            429: SecurityErrorCode.RATE_LIMIT_EXCEEDED,
            500: SecurityErrorCode.INTERNAL_ERROR,
            502: SecurityErrorCode.SERVICE_UNAVAILABLE,
            503: SecurityErrorCode.SERVICE_UNAVAILABLE
        }
        
        error_code = status_to_error_code.get(error.code, "HTTP_ERROR")
        
        return {
            'error_id': error_id,
            'error_code': error_code,
            'message': error.description or str(error),
            'user_message': self._get_user_friendly_message(error.code),
            'status_code': error.code,
            'details': {},
            'timestamp': datetime.utcnow().isoformat(),
            'type': 'http_error'
        }
    
    def _handle_generic_error(self, error: Exception, error_id: str) -> Dict[str, Any]:
        """Handle generic exceptions."""
        
        return {
            'error_id': error_id,
            'error_code': SecurityErrorCode.INTERNAL_ERROR,
            'message': "Internal server error",
            'user_message': "An unexpected error occurred. Please try again later.",
            'status_code': 500,
            'details': {
                'error_type': type(error).__name__
            },
            'timestamp': datetime.utcnow().isoformat(),
            'type': 'internal_error'
        }
    
    def _get_user_friendly_message(self, status_code: int) -> str:
        """Get user-friendly message for HTTP status codes."""
        
        messages = {
            400: "Bad request. Please check your input.",
            401: "Authentication required. Please log in.",
            403: "Access denied. You don't have permission to access this resource.",
            404: "The requested resource was not found.",
            405: "Method not allowed for this endpoint.",
            413: "File too large. Please reduce the file size.",
            429: "Too many requests. Please slow down.",
            500: "Internal server error. Please try again later.",
            502: "Service temporarily unavailable.",
            503: "Service temporarily unavailable."
        }
        
        return messages.get(status_code, "An error occurred.")
    
    def _build_error_response(self, error_info: Dict[str, Any]) -> Dict[str, Any]:
        """Build standardized error response."""
        
        # Determine if we should show detailed error information
        show_details = self._should_show_details(error_info)
        
        response = {
            'success': False,
            'error': {
                'code': error_info['error_code'],
                'message': error_info['user_message'],
                'timestamp': error_info['timestamp'],
                'request_id': getattr(g, 'request_id', None)
            }
        }
        
        # Add error ID for tracking (always include)
        response['error']['error_id'] = error_info['error_id']
        
        # Add details in development or for certain error types
        if show_details and error_info.get('details'):
            response['error']['details'] = error_info['details']
        
        # Add retry information for rate limiting
        if error_info.get('retry_after'):
            response['error']['retry_after'] = error_info['retry_after']
        
        # Add help information
        response['error']['help'] = self._get_help_information(error_info['error_code'])
        
        return response
    
    def _build_error_headers(self, error_info: Dict[str, Any]) -> Dict[str, str]:
        """Build error-specific headers."""
        
        headers = {
            'Content-Type': 'application/json',
            'X-Error-Code': error_info['error_code'],
            'X-Error-ID': error_info['error_id']
        }
        
        # Add retry-after header for rate limiting
        if error_info.get('retry_after'):
            headers['Retry-After'] = str(error_info['retry_after'])
        
        # Add security headers
        headers.update({
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block'
        })
        
        return headers
    
    def _should_show_details(self, error_info: Dict[str, Any]) -> bool:
        """Determine if detailed error information should be shown."""
        
        # Show details in development environment
        if os.getenv('FLASK_ENV') == 'development':
            return True
        
        # Show details for client errors (4xx) but not server errors (5xx)
        status_code = error_info['status_code']
        if 400 <= status_code < 500:
            return True
        
        # Never show details for security violations
        if error_info['error_code'].startswith('SEC_'):
            return False
        
        return False
    
    def _get_help_information(self, error_code: str) -> Dict[str, Any]:
        """Get help information for error code."""
        
        help_info = {
            SecurityErrorCode.INVALID_TOKEN: {
                'suggestion': 'Please log in again to get a new authentication token.',
                'docs_url': '/docs/authentication'
            },
            SecurityErrorCode.RATE_LIMIT_EXCEEDED: {
                'suggestion': 'Please wait before making more requests. Consider upgrading for higher limits.',
                'docs_url': '/docs/rate-limits'
            },
            SecurityErrorCode.CONTENT_BLOCKED: {
                'suggestion': 'Please review our community guidelines and modify your content.',
                'docs_url': '/docs/community-guidelines'
            },
            SecurityErrorCode.INVALID_INPUT: {
                'suggestion': 'Please check the format and content of your request.',
                'docs_url': '/docs/api-reference'
            }
        }
        
        return help_info.get(error_code, {
            'suggestion': 'Please contact support if this issue persists.',
            'support_url': '/support'
        })
    
    def _log_error(self, error_info: Dict[str, Any], original_error: Exception):
        """Log error with appropriate level and context."""
        
        # Gather request context
        context = self._gather_request_context()
        
        log_data = {
            'error_info': error_info,
            'context': context,
            'user_id': getattr(g, 'user_id', None),
            'session_id': getattr(g, 'session_id', None)
        }
        
        # Determine log level based on error type and status code
        status_code = error_info['status_code']
        
        if status_code >= 500:
            self.logger.error(f"Server error: {json.dumps(log_data)}", exc_info=original_error)
        elif status_code == 429:
            self.logger.warning(f"Rate limit exceeded: {json.dumps(log_data)}")
        elif error_info['error_code'].startswith('SEC_'):
            self.logger.warning(f"Security violation: {json.dumps(log_data)}")
        else:
            self.logger.info(f"Client error: {json.dumps(log_data)}")
    
    def _gather_request_context(self) -> Dict[str, Any]:
        """Gather request context for logging."""
        
        context = {}
        
        try:
            if request:
                context.update({
                    'method': request.method,
                    'url': request.url,
                    'endpoint': request.endpoint,
                    'ip_address': request.remote_addr,
                    'user_agent': request.headers.get('User-Agent', ''),
                    'referrer': request.headers.get('Referer', ''),
                    'content_type': request.content_type,
                    'content_length': request.content_length
                })
        except RuntimeError:
            # Outside request context
            pass
        
        return context
    
    def _track_error_pattern(self, error_info: Dict[str, Any]):
        """Track error patterns for monitoring."""
        
        try:
            # Simple in-memory tracking (in production, use proper monitoring)
            error_code = error_info['error_code']
            current_hour = datetime.utcnow().strftime('%Y-%m-%d:%H')
            
            key = f"{error_code}:{current_hour}"
            
            if key not in self.error_tracking:
                self.error_tracking[key] = 0
            
            self.error_tracking[key] += 1
            
            # Alert on high error rates
            if self.error_tracking[key] > 100:  # More than 100 errors per hour
                self.logger.critical(f"High error rate detected: {key} - {self.error_tracking[key]} errors")
        
        except Exception as e:
            self.logger.error(f"Failed to track error pattern: {str(e)}")
    
    def _generate_error_id(self) -> str:
        """Generate unique error ID for tracking."""
        import uuid
        return str(uuid.uuid4())
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics."""
        
        stats = {
            'error_counts': dict(self.error_tracking),
            'total_errors': sum(self.error_tracking.values())
        }
        
        return stats

# Global error handler instance
security_error_handler = SecurityErrorHandler()

# Convenience functions for raising common errors
def raise_authentication_error(message: str, error_code: str = SecurityErrorCode.INVALID_TOKEN, details: Dict[str, Any] = None):
    """Raise authentication error."""
    raise AuthenticationError(message, error_code, details)

def raise_authorization_error(message: str, error_code: str = SecurityErrorCode.ACCESS_DENIED, details: Dict[str, Any] = None):
    """Raise authorization error."""
    raise AuthorizationError(message, error_code, details)

def raise_rate_limit_error(message: str, retry_after: int = None, details: Dict[str, Any] = None):
    """Raise rate limit error."""
    raise RateLimitError(message, SecurityErrorCode.RATE_LIMIT_EXCEEDED, retry_after, details)

def raise_content_filter_error(message: str, error_code: str = SecurityErrorCode.CONTENT_BLOCKED, details: Dict[str, Any] = None):
    """Raise content filter error."""
    raise ContentFilterError(message, error_code, details)

def raise_validation_error(message: str, field: str = None, error_code: str = SecurityErrorCode.INVALID_INPUT, details: Dict[str, Any] = None):
    """Raise validation error."""
    raise ValidationError(message, error_code, field, details)

def raise_security_violation(message: str, severity: str = "medium", error_code: str = SecurityErrorCode.SECURITY_VIOLATION, details: Dict[str, Any] = None):
    """Raise security violation error."""
    raise SecurityViolationError(message, error_code, severity, details)
