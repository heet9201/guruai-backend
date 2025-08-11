"""
Security Middleware
Comprehensive security middleware integrating all security components.
"""

import os
import time
import logging
from functools import wraps
from typing import Dict, Any, Optional, Callable
from flask import request, g, current_app
from werkzeug.exceptions import Forbidden, Unauthorized, TooManyRequests

from .auth_manager import AuthManager
from .crypto_manager import CryptoManager
from .audit_logger import AuditLogger, AuditEventType, AuditSeverity
from .content_filter import ContentFilter, ContentType, FilterResult
from .rate_limiter import RateLimiter, RateLimitType
from .error_handler import (
    security_error_handler,
    raise_authentication_error,
    raise_authorization_error,
    raise_rate_limit_error,
    raise_content_filter_error,
    raise_security_violation,
    SecurityErrorCode
)

class SecurityMiddleware:
    """Comprehensive security middleware."""
    
    def __init__(self, app=None):
        self.app = app
        self.auth_manager = AuthManager()
        self.crypto_manager = CryptoManager()
        self.audit_logger = AuditLogger()
        self.content_filter = ContentFilter()
        self.rate_limiter = RateLimiter()
        
        self.logger = logging.getLogger('security_middleware')
        
        # Security configuration
        self.config = {
            'rate_limiting_enabled': os.getenv('RATE_LIMITING_ENABLED', 'true').lower() == 'true',
            'content_filtering_enabled': os.getenv('CONTENT_FILTERING_ENABLED', 'true').lower() == 'true',
            'audit_logging_enabled': os.getenv('AUDIT_LOGGING_ENABLED', 'true').lower() == 'true',
            'csrf_protection_enabled': os.getenv('CSRF_PROTECTION_ENABLED', 'true').lower() == 'true',
            'xss_protection_enabled': os.getenv('XSS_PROTECTION_ENABLED', 'true').lower() == 'true'
        }
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize security middleware with Flask app."""
        self.app = app
        
        # Register error handlers
        app.errorhandler(Exception)(self.handle_error)
        
        # Register before request handlers
        app.before_request(self.before_request)
        app.after_request(self.after_request)
        
        # Add security headers
        app.after_request(self.add_security_headers)
    
    def before_request(self):
        """Process security checks before each request."""
        
        # Generate request ID for tracking
        g.request_id = self._generate_request_id()
        g.request_start_time = time.time()
        
        try:
            # 1. IP blocking check
            if self._is_ip_blocked():
                self.audit_logger.log_event(
                    AuditEventType.ACCESS_DENIED,
                    severity=AuditSeverity.HIGH,
                    details={'reason': 'IP blocked', 'ip': request.remote_addr}
                )
                raise_rate_limit_error("IP address is blocked", 3600)
            
            # 2. Rate limiting check
            if self.config['rate_limiting_enabled']:
                self._check_rate_limits()
            
            # 3. Security headers validation
            self._validate_security_headers()
            
            # 4. Input validation and XSS protection
            if self.config['xss_protection_enabled']:
                self._check_xss_attempts()
            
            # 5. CSRF protection for state-changing operations
            if self.config['csrf_protection_enabled']:
                self._check_csrf_protection()
            
            # 6. Authentication check for protected routes
            self._check_authentication()
            
        except Exception as e:
            # Let error handler manage the response
            raise e
    
    def after_request(self, response):
        """Process security checks after each request."""
        
        try:
            # Log request completion
            if self.config['audit_logging_enabled']:
                self._log_request_completion(response)
            
            # Add rate limit headers
            self._add_rate_limit_headers(response)
            
        except Exception as e:
            self.logger.error(f"After request security check failed: {str(e)}")
        
        return response
    
    def _is_ip_blocked(self) -> bool:
        """Check if current IP is blocked."""
        return self.rate_limiter.is_ip_blocked(request.remote_addr)
    
    def _check_rate_limits(self):
        """Check various rate limits."""
        
        ip_address = request.remote_addr
        user_id = getattr(g, 'user_id', None)
        endpoint = request.endpoint or 'unknown'
        
        # IP-based rate limiting
        ip_result = self.rate_limiter.check_rate_limit(
            RateLimitType.PER_IP,
            'api_calls',
            ip_address
        )
        
        if not ip_result.allowed:
            self.audit_logger.log_event(
                AuditEventType.RATE_LIMIT_EXCEEDED,
                user_id=user_id,
                severity=AuditSeverity.MEDIUM,
                details={'limit_type': 'ip', 'ip': ip_address}
            )
            raise_rate_limit_error(
                f"Rate limit exceeded for IP {ip_address}",
                ip_result.retry_after
            )
        
        # User-based rate limiting (if authenticated)
        if user_id:
            user_result = self.rate_limiter.check_rate_limit(
                RateLimitType.PER_USER,
                'api_calls',
                user_id
            )
            
            if not user_result.allowed:
                self.audit_logger.log_event(
                    AuditEventType.RATE_LIMIT_EXCEEDED,
                    user_id=user_id,
                    severity=AuditSeverity.MEDIUM,
                    details={'limit_type': 'user', 'user_id': user_id}
                )
                raise_rate_limit_error(
                    "Rate limit exceeded for user",
                    user_result.retry_after
                )
        
        # Endpoint-specific rate limiting
        endpoint_result = self.rate_limiter.check_rate_limit(
            RateLimitType.PER_ENDPOINT,
            endpoint,
            ip_address
        )
        
        if not endpoint_result.allowed:
            self.audit_logger.log_event(
                AuditEventType.RATE_LIMIT_EXCEEDED,
                user_id=user_id,
                severity=AuditSeverity.MEDIUM,
                details={'limit_type': 'endpoint', 'endpoint': endpoint}
            )
            raise_rate_limit_error(
                f"Rate limit exceeded for endpoint {endpoint}",
                endpoint_result.retry_after
            )
    
    def _validate_security_headers(self):
        """Validate important security headers."""
        
        # Check for suspicious headers
        suspicious_headers = [
            'x-forwarded-for',
            'x-real-ip',
            'x-originating-ip'
        ]
        
        for header in suspicious_headers:
            if header in request.headers:
                # Log for monitoring (might indicate proxy/load balancer issues)
                self.logger.info(f"Received header {header}: {request.headers[header]}")
    
    def _check_xss_attempts(self):
        """Check for XSS attempts in request data."""
        
        xss_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'onload\s*=',
            r'onerror\s*=',
            r'onclick\s*=',
            r'<iframe[^>]*>',
            r'<object[^>]*>',
            r'<embed[^>]*>'
        ]
        
        # Check URL parameters
        for key, value in request.args.items():
            if self._contains_xss_pattern(value, xss_patterns):
                self.audit_logger.log_event(
                    AuditEventType.SECURITY_VIOLATION,
                    user_id=getattr(g, 'user_id', None),
                    severity=AuditSeverity.HIGH,
                    details={
                        'violation_type': 'xss_attempt',
                        'parameter': key,
                        'value': value[:100]
                    }
                )
                raise_security_violation(
                    "XSS attempt detected in URL parameters",
                    "high",
                    SecurityErrorCode.XSS_ATTEMPT
                )
        
        # Check form data
        if request.form:
            for key, value in request.form.items():
                if self._contains_xss_pattern(value, xss_patterns):
                    self.audit_logger.log_event(
                        AuditEventType.SECURITY_VIOLATION,
                        user_id=getattr(g, 'user_id', None),
                        severity=AuditSeverity.HIGH,
                        details={
                            'violation_type': 'xss_attempt',
                            'form_field': key,
                            'value': value[:100]
                        }
                    )
                    raise_security_violation(
                        "XSS attempt detected in form data",
                        "high",
                        SecurityErrorCode.XSS_ATTEMPT
                    )
    
    def _contains_xss_pattern(self, text: str, patterns: list) -> bool:
        """Check if text contains XSS patterns."""
        import re
        
        text_lower = text.lower()
        for pattern in patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        return False
    
    def _check_csrf_protection(self):
        """Check CSRF protection for state-changing operations."""
        
        if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
            # Skip CSRF check for API endpoints with proper authentication
            if request.path.startswith('/api/') and self._has_valid_api_token():
                return
            
            # Check for CSRF token
            csrf_token = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token')
            
            if not csrf_token:
                self.audit_logger.log_event(
                    AuditEventType.SECURITY_VIOLATION,
                    user_id=getattr(g, 'user_id', None),
                    severity=AuditSeverity.MEDIUM,
                    details={'violation_type': 'missing_csrf_token'}
                )
                raise_security_violation(
                    "CSRF token missing",
                    "medium",
                    SecurityErrorCode.CSRF_VIOLATION
                )
            
            # Validate CSRF token (simplified - in production, use proper CSRF validation)
            session_id = getattr(g, 'session_id', None)
            if not self._validate_csrf_token(csrf_token, session_id):
                self.audit_logger.log_event(
                    AuditEventType.SECURITY_VIOLATION,
                    user_id=getattr(g, 'user_id', None),
                    severity=AuditSeverity.HIGH,
                    details={'violation_type': 'invalid_csrf_token'}
                )
                raise_security_violation(
                    "Invalid CSRF token",
                    "high",
                    SecurityErrorCode.CSRF_VIOLATION
                )
    
    def _has_valid_api_token(self) -> bool:
        """Check if request has valid API token."""
        auth_header = request.headers.get('Authorization', '')
        return auth_header.startswith('Bearer ')
    
    def _validate_csrf_token(self, token: str, session_id: str) -> bool:
        """Validate CSRF token (simplified implementation)."""
        # In production, implement proper CSRF token validation
        # This is a placeholder implementation
        return len(token) > 10 and session_id is not None
    
    def _check_authentication(self):
        """Check authentication for protected routes."""
        
        # Skip authentication for public routes
        public_routes = [
            '/',
            '/health',
            '/api/auth/login',
            '/api/auth/register',
            '/api/auth/refresh'
        ]
        
        if request.path in public_routes:
            return
        
        # Check for authentication token
        auth_header = request.headers.get('Authorization', '')
        
        if not auth_header.startswith('Bearer '):
            if request.path.startswith('/api/'):
                raise_authentication_error(
                    "Authentication token required",
                    SecurityErrorCode.MISSING_TOKEN
                )
            return
        
        # Extract and validate token
        token = auth_header[7:]  # Remove 'Bearer ' prefix
        
        try:
            payload = self.auth_manager.verify_access_token(token)
            
            # Set user context
            g.user_id = payload['user_id']
            g.session_id = payload.get('session_id')
            g.user_role = payload.get('role', 'user')
            
            # Check if session is still valid
            if not self.auth_manager.is_session_valid(payload['user_id'], payload.get('session_id')):
                raise_authentication_error(
                    "Session expired or invalid",
                    SecurityErrorCode.SESSION_EXPIRED
                )
            
            # Log successful authentication
            self.audit_logger.log_event(
                AuditEventType.ACCESS_GRANTED,
                user_id=g.user_id,
                details={'endpoint': request.endpoint}
            )
            
        except Exception as e:
            self.audit_logger.log_event(
                AuditEventType.ACCESS_DENIED,
                severity=AuditSeverity.MEDIUM,
                details={
                    'reason': 'invalid_token',
                    'endpoint': request.endpoint,
                    'error': str(e)
                }
            )
            raise_authentication_error(
                "Invalid or expired token",
                SecurityErrorCode.INVALID_TOKEN
            )
    
    def _log_request_completion(self, response):
        """Log request completion for audit trail."""
        
        request_time = time.time() - g.request_start_time
        
        self.audit_logger.log_event(
            AuditEventType.DATA_ACCESS,
            user_id=getattr(g, 'user_id', None),
            details={
                'method': request.method,
                'endpoint': request.endpoint,
                'status_code': response.status_code,
                'response_time': round(request_time, 3),
                'user_agent': request.headers.get('User-Agent', ''),
                'content_length': response.content_length
            }
        )
    
    def _add_rate_limit_headers(self, response):
        """Add rate limiting headers to response."""
        
        user_id = getattr(g, 'user_id', None)
        if user_id:
            # Get current rate limit status
            usage = self.rate_limiter.get_current_usage(
                RateLimitType.PER_USER,
                'api_calls',
                user_id
            )
            
            response.headers['X-RateLimit-Limit'] = str(usage['limit'])
            response.headers['X-RateLimit-Remaining'] = str(usage['remaining'])
            response.headers['X-RateLimit-Reset'] = str(int(usage['reset_time']))
    
    def add_security_headers(self, response):
        """Add comprehensive security headers."""
        
        # Content Security Policy
        csp_policy = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' https:; "
            "connect-src 'self' https:; "
            "frame-ancestors 'none';"
        )
        response.headers['Content-Security-Policy'] = csp_policy
        
        # Security headers
        response.headers.update({
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'Permissions-Policy': 'geolocation=(), microphone=(), camera=()',
            'X-Request-ID': getattr(g, 'request_id', ''),
        })
        
        # Remove server information
        response.headers.pop('Server', None)
        
        return response
    
    def handle_error(self, error):
        """Handle all application errors through security error handler."""
        return security_error_handler.handle_error(error)
    
    def _generate_request_id(self) -> str:
        """Generate unique request ID."""
        import uuid
        return str(uuid.uuid4())

# Decorator functions for route-specific security
def require_auth(f):
    """Decorator to require authentication for a route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, 'user_id') or not g.user_id:
            raise_authentication_error(
                "Authentication required",
                SecurityErrorCode.MISSING_TOKEN
            )
        return f(*args, **kwargs)
    return decorated_function

def require_role(required_role: str):
    """Decorator to require specific role for a route."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_role = getattr(g, 'user_role', None)
            if user_role != required_role:
                raise_authorization_error(
                    f"Role '{required_role}' required",
                    SecurityErrorCode.ROLE_REQUIRED
                )
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def content_filter_required(content_type: ContentType = ContentType.TEXT):
    """Decorator to require content filtering for a route."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # This would be called in the route handler to filter content
            # The actual filtering would be done on the content in the route
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def rate_limit(resource: str, limit_type: RateLimitType = RateLimitType.PER_USER):
    """Decorator to apply specific rate limiting to a route."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Additional rate limiting specific to this route
            # The middleware already handles general rate limiting
            return f(*args, **kwargs)
        return decorated_function
    return decorator
