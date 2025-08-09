import jwt
import uuid
import bcrypt
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from flask import current_app
import logging

logger = logging.getLogger(__name__)

class JWTUtils:
    """JWT token management utilities."""
    
    @staticmethod
    def generate_access_token(user_id: str, device_id: str) -> str:
        """Generate JWT access token with 1 hour expiry."""
        payload = {
            'user_id': user_id,
            'device_id': device_id,
            'type': 'access',
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(hours=1),
            'jti': str(uuid.uuid4())  # JWT ID for token revocation
        }
        
        secret_key = current_app.config.get('SECRET_KEY', 'fallback-secret-key')
        return jwt.encode(payload, secret_key, algorithm='HS256')
    
    @staticmethod
    def generate_refresh_token(user_id: str, device_id: str) -> str:
        """Generate JWT refresh token with 30 days expiry."""
        payload = {
            'user_id': user_id,
            'device_id': device_id,
            'type': 'refresh',
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(days=30),
            'jti': str(uuid.uuid4())
        }
        
        secret_key = current_app.config.get('SECRET_KEY', 'fallback-secret-key')
        return jwt.encode(payload, secret_key, algorithm='HS256')
    
    @staticmethod
    def verify_token(token: str) -> Dict[str, Any]:
        """Verify and decode JWT token."""
        try:
            secret_key = current_app.config.get('SECRET_KEY', 'fallback-secret-key')
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            
            return {
                'valid': True,
                'payload': payload,
                'user_id': payload.get('user_id'),
                'device_id': payload.get('device_id'),
                'type': payload.get('type'),
                'jti': payload.get('jti')
            }
            
        except jwt.ExpiredSignatureError:
            return {
                'valid': False,
                'error': 'Token has expired'
            }
        except jwt.InvalidTokenError:
            return {
                'valid': False,
                'error': 'Invalid token'
            }
        except Exception as e:
            logger.error(f"Token verification error: {str(e)}")
            return {
                'valid': False,
                'error': 'Token verification failed'
            }
    
    @staticmethod
    def extract_token_from_header(auth_header: str) -> Optional[str]:
        """Extract token from Authorization header."""
        if not auth_header:
            return None
        
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return None
        
        return parts[1]

class PasswordUtils:
    """Password hashing utilities using bcrypt."""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using bcrypt."""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        """Verify password against bcrypt hash."""
        try:
            return bcrypt.checkpw(
                password.encode('utf-8'), 
                hashed_password.encode('utf-8')
            )
        except Exception as e:
            logger.error(f"Password verification error: {str(e)}")
            return False

class DeviceUtils:
    """Device fingerprinting utilities."""
    
    @staticmethod
    def generate_device_fingerprint(request) -> str:
        """Generate device fingerprint from request data."""
        # Combine various request headers to create a fingerprint
        user_agent = request.headers.get('User-Agent', '')
        accept_language = request.headers.get('Accept-Language', '')
        accept_encoding = request.headers.get('Accept-Encoding', '')
        
        # Create a simple fingerprint (in production, use more sophisticated methods)
        fingerprint_data = f"{user_agent}|{accept_language}|{accept_encoding}"
        
        # Hash the fingerprint data
        import hashlib
        return hashlib.sha256(fingerprint_data.encode()).hexdigest()[:16]
    
    @staticmethod
    def get_client_ip(request) -> str:
        """Get client IP address from request."""
        # Check for forwarded headers (proxy/load balancer)
        if request.headers.get('X-Forwarded-For'):
            return request.headers.get('X-Forwarded-For').split(',')[0].strip()
        elif request.headers.get('X-Real-IP'):
            return request.headers.get('X-Real-IP')
        else:
            return request.remote_addr or 'unknown'
