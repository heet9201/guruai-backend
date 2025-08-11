# Comprehensive Security Framework Documentation

## Overview

This security framework provides enterprise-grade security measures for the GuruAI educational platform, including JWT authentication, encryption, content filtering, rate limiting, audit logging, and comprehensive error handling.

## Security Components

### 1. Authentication Manager (`auth_manager.py`)

- **JWT-based authentication** with short-lived access tokens (15 minutes) and refresh tokens (7 days)
- **Multi-Factor Authentication (MFA)** with TOTP and backup codes
- **Device fingerprinting** for enhanced security
- **Session management** with Redis backend
- **Token rotation** and secure revocation

### 2. Cryptographic Manager (`crypto_manager.py`)

- **End-to-end encryption** for sensitive data using Fernet
- **PII data handling** and anonymization
- **GDPR compliance** features including data export and deletion
- **Secure file encryption** with user-specific keys
- **Password hashing** with PBKDF2 (100,000 iterations)

### 3. Audit Logger (`audit_logger.py`)

- **Comprehensive event logging** for all user actions
- **Security incident tracking** with real-time alerts
- **Redis-backed storage** for fast queries
- **Structured JSON logging** for analysis
- **Automatic security pattern detection**

### 4. Content Filter (`content_filter.py`)

- **AI safety filters** for generated content
- **Inappropriate content detection** (profanity, hate speech, harassment)
- **Child safety measures** with enhanced protection
- **Academic dishonesty detection**
- **Spam and malicious content filtering**

### 5. Rate Limiter (`rate_limiter.py`)

- **Configurable rate limiting** per user, IP, and endpoint
- **Sliding window algorithm** for accurate limiting
- **Burst protection** with short-term limits
- **Premium user tiers** with multipliers
- **Automatic IP blocking** for violations

### 6. Error Handler (`error_handler.py`)

- **Standardized error responses** with proper HTTP status codes
- **Security-aware error handling** that doesn't leak sensitive information
- **Comprehensive error tracking** and pattern detection
- **User-friendly error messages** with help information

### 7. Security Middleware (`middleware.py`)

- **Comprehensive request/response processing**
- **Integrated security checks** (XSS, CSRF, rate limiting)
- **Security headers** injection
- **Request tracking** and monitoring

### 8. Security Configuration (`config.py`)

- **Environment-specific configurations** (development, production, testing)
- **Centralized security settings**
- **Configuration validation**
- **Redis connection management**

## Installation and Setup

### 1. Install Dependencies

```bash
pip install -r app/security/requirements.txt
```

### 2. Environment Variables

Set these critical environment variables:

```bash
# Authentication
export JWT_SECRET_KEY="your-super-secret-jwt-key-change-in-production"
export ENCRYPTION_KEY="your-32-byte-encryption-key"
export PII_ENCRYPTION_KEY="your-32-byte-pii-encryption-key"

# Redis Configuration
export REDIS_HOST="localhost"
export REDIS_PORT="6379"
export REDIS_PASSWORD="your-redis-password"

# Security Settings
export RATE_LIMITING_ENABLED="true"
export CONTENT_FILTERING_ENABLED="true"
export AUDIT_LOGGING_ENABLED="true"
export MFA_ENABLED="true"
```

### 3. Initialize Security Middleware

```python
from flask import Flask
from app.security.middleware import SecurityMiddleware

app = Flask(__name__)
security = SecurityMiddleware(app)
```

## Usage Examples

### 1. Authentication

```python
from app.security import AuthManager

auth_manager = AuthManager()

# Register user
user_data = auth_manager.register_user(
    username="student123",
    email="student@example.com",
    password="SecurePassword123!",
    role="student"
)

# Login
login_result = auth_manager.authenticate_user(
    "student123",
    "SecurePassword123!",
    device_info={"browser": "Chrome", "os": "Windows"}
)

# Setup MFA
mfa_secret = auth_manager.setup_mfa("user_id_123")
```

### 2. Content Filtering

```python
from app.security import ContentFilter, ContentType

content_filter = ContentFilter()

# Filter user content
result = content_filter.filter_content(
    "User's message here",
    content_type=ContentType.TEXT,
    user_age=16
)

if result['result'] == FilterResult.BLOCKED:
    # Handle blocked content
    return {"error": "Content violates community guidelines"}
```

### 3. Rate Limiting

```python
from app.security import RateLimiter, RateLimitType

rate_limiter = RateLimiter()

# Check rate limit
result = rate_limiter.check_rate_limit(
    RateLimitType.PER_USER,
    "content_generation",
    user_id,
    user_tier="premium"
)

if not result.allowed:
    # Handle rate limit exceeded
    return {"error": "Rate limit exceeded", "retry_after": result.retry_after}
```

### 4. Audit Logging

```python
from app.security import AuditLogger, AuditEventType, AuditSeverity

audit_logger = AuditLogger()

# Log security event
audit_logger.log_event(
    AuditEventType.LOGIN_SUCCESS,
    user_id="user_123",
    severity=AuditSeverity.LOW,
    details={"login_method": "password"}
)
```

### 5. Route Protection Decorators

```python
from app.security.middleware import require_auth, require_role, content_filter_required

@app.route('/api/admin/users')
@require_auth
@require_role('admin')
def get_users():
    return {"users": []}

@app.route('/api/content/generate')
@require_auth
@content_filter_required(ContentType.TEXT)
def generate_content():
    # Content will be automatically filtered
    return {"content": "Generated content"}
```

## Security Features

### Authentication & Authorization

- ✅ JWT-based authentication with short-lived tokens
- ✅ Refresh token rotation
- ✅ Multi-factor authentication (TOTP)
- ✅ Device fingerprinting
- ✅ Session management with Redis
- ✅ Role-based access control

### Data Protection

- ✅ End-to-end encryption for sensitive data
- ✅ PII data handling and anonymization
- ✅ GDPR compliance features
- ✅ Secure file storage with encryption
- ✅ Password hashing with PBKDF2

### Content Security

- ✅ AI safety filters for generated content
- ✅ Inappropriate content detection
- ✅ Child safety measures
- ✅ Academic dishonesty prevention
- ✅ Spam and malicious content filtering

### API Security

- ✅ Rate limiting per user/IP/endpoint
- ✅ Input validation and sanitization
- ✅ XSS protection
- ✅ CSRF protection
- ✅ Security headers (CSP, HSTS, etc.)

### Monitoring & Logging

- ✅ Comprehensive audit logging
- ✅ Security incident tracking
- ✅ Real-time alert system
- ✅ Error tracking and pattern detection
- ✅ Performance monitoring

### Error Handling

- ✅ Standardized error response format
- ✅ Proper HTTP status codes
- ✅ Security-aware error handling
- ✅ User-friendly error messages

## Configuration Options

### Rate Limiting

```python
# Customize rate limits
RATE_LIMITS = {
    'api_calls': {
        'per_user': {'limit': 1000, 'window': 'hour'},
        'per_ip': {'limit': 5000, 'window': 'hour'}
    },
    'content_generation': {
        'per_user': {'limit': 100, 'window': 'hour'}
    }
}
```

### Content Filtering

```python
# Configure content filter thresholds
CONTENT_FILTER_THRESHOLDS = {
    'profanity': {
        'mild': 'flagged',
        'moderate': 'flagged',
        'severe': 'blocked'
    },
    'hate_speech': 'blocked',
    'child_safety': 'blocked'
}
```

### Security Headers

```python
# Customize Content Security Policy
CSP_POLICY = {
    'default-src': ["'self'"],
    'script-src': ["'self'", "'unsafe-inline'"],
    'style-src': ["'self'", "'unsafe-inline'"],
    'img-src': ["'self'", "data:", "https:"]
}
```

## Monitoring and Alerts

The security framework includes comprehensive monitoring:

1. **Real-time Security Alerts**: Automatic detection of suspicious activities
2. **Audit Trail**: Complete logging of all user actions and system events
3. **Rate Limit Monitoring**: Track and alert on rate limit violations
4. **Content Filter Statistics**: Monitor content filtering effectiveness
5. **Error Pattern Detection**: Identify and alert on unusual error patterns

## Production Deployment

### 1. Environment Configuration

```bash
export FLASK_ENV="production"
export JWT_SECRET_KEY="$(openssl rand -base64 32)"
export ENCRYPTION_KEY="$(openssl rand -base64 32)"
export PII_ENCRYPTION_KEY="$(openssl rand -base64 32)"
```

### 2. Redis Setup

Ensure Redis is properly configured with:

- Password protection
- SSL/TLS encryption
- Proper network security
- Regular backups

### 3. Monitoring Setup

Configure monitoring for:

- Security alerts
- Rate limit violations
- Authentication failures
- Content filter triggers
- System errors

### 4. Regular Security Reviews

- Review audit logs weekly
- Update content filter rules monthly
- Review and update rate limits quarterly
- Security penetration testing annually

## Security Best Practices

1. **Keep Dependencies Updated**: Regularly update security-related packages
2. **Monitor Security Alerts**: Set up automated monitoring for security events
3. **Regular Security Audits**: Conduct periodic security reviews
4. **Backup Security Data**: Ensure audit logs and security configurations are backed up
5. **Train Your Team**: Ensure developers understand security best practices

## Support and Maintenance

This security framework is designed to be:

- **Modular**: Each component can be used independently
- **Extensible**: Easy to add new security features
- **Configurable**: Adaptable to different environments and requirements
- **Maintainable**: Clear separation of concerns and comprehensive documentation

For additional support or custom security requirements, refer to the individual component documentation or security configuration options.
