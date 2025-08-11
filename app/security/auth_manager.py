"""
Enhanced Authentication Manager
JWT-based authentication with refresh token rotation, device tracking, and MFA support.
"""

import os
import jwt
import redis
import hashlib
import secrets
import pyotp
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from cryptography.fernet import Fernet
from flask import request, current_app
import logging

logger = logging.getLogger(__name__)

class AuthManager:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            db=int(os.getenv('REDIS_AUTH_DB', 1)),
            decode_responses=True
        )
        self.secret_key = os.getenv('JWT_SECRET_KEY')
        self.encryption_key = os.getenv('ENCRYPTION_KEY', Fernet.generate_key())
        self.fernet = Fernet(self.encryption_key)
        
        # Token configuration
        self.access_token_expiry = timedelta(minutes=15)  # Short-lived
        self.refresh_token_expiry = timedelta(days=7)     # Longer-lived
        self.device_session_expiry = timedelta(days=30)
        
    def generate_device_fingerprint(self, user_agent: str, ip_address: str) -> str:
        """Generate unique device fingerprint."""
        fingerprint_data = f"{user_agent}:{ip_address}:{request.headers.get('Accept-Language', '')}"
        return hashlib.sha256(fingerprint_data.encode()).hexdigest()
    
    def create_tokens(self, user_id: str, device_fingerprint: str, 
                     permissions: list = None) -> Dict[str, Any]:
        """Create access and refresh tokens with device tracking."""
        now = datetime.utcnow()
        
        # Generate unique session ID
        session_id = secrets.token_urlsafe(32)
        
        # Access token payload
        access_payload = {
            'user_id': user_id,
            'session_id': session_id,
            'device_fingerprint': device_fingerprint,
            'permissions': permissions or [],
            'token_type': 'access',
            'iat': now,
            'exp': now + self.access_token_expiry,
            'jti': secrets.token_urlsafe(16)  # JWT ID
        }
        
        # Refresh token payload
        refresh_payload = {
            'user_id': user_id,
            'session_id': session_id,
            'device_fingerprint': device_fingerprint,
            'token_type': 'refresh',
            'iat': now,
            'exp': now + self.refresh_token_expiry,
            'jti': secrets.token_urlsafe(16)
        }
        
        # Generate tokens
        access_token = jwt.encode(access_payload, self.secret_key, algorithm='HS256')
        refresh_token = jwt.encode(refresh_payload, self.secret_key, algorithm='HS256')
        
        # Store session in Redis
        session_data = {
            'user_id': user_id,
            'device_fingerprint': device_fingerprint,
            'created_at': now.isoformat(),
            'last_activity': now.isoformat(),
            'permissions': ','.join(permissions or []),
            'is_active': 'true',
            'access_jti': access_payload['jti'],
            'refresh_jti': refresh_payload['jti']
        }
        
        # Store session with expiry
        self.redis_client.hset(f"session:{session_id}", mapping=session_data)
        self.redis_client.expire(f"session:{session_id}", int(self.device_session_expiry.total_seconds()))
        
        # Store refresh token mapping
        self.redis_client.setex(
            f"refresh_token:{refresh_payload['jti']}", 
            int(self.refresh_token_expiry.total_seconds()),
            session_id
        )
        
        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'session_id': session_id,
            'expires_in': int(self.access_token_expiry.total_seconds()),
            'token_type': 'Bearer'
        }
    
    def verify_token(self, token: str, token_type: str = 'access') -> Tuple[bool, Dict[str, Any], str]:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            
            # Verify token type
            if payload.get('token_type') != token_type:
                return False, {}, "Invalid token type"
            
            # Check if session exists and is active
            session_id = payload.get('session_id')
            session_data = self.redis_client.hgetall(f"session:{session_id}")
            
            if not session_data or session_data.get('is_active') != 'true':
                return False, {}, "Session invalid or expired"
            
            # Verify device fingerprint
            current_fingerprint = self.generate_device_fingerprint(
                request.headers.get('User-Agent', ''),
                request.remote_addr
            )
            
            if payload.get('device_fingerprint') != current_fingerprint:
                logger.warning(f"Device fingerprint mismatch for user {payload.get('user_id')}")
                # Don't fail completely, but log for security monitoring
            
            # Update last activity
            self.redis_client.hset(f"session:{session_id}", 'last_activity', datetime.utcnow().isoformat())
            
            return True, payload, ""
            
        except jwt.ExpiredSignatureError:
            return False, {}, "Token expired"
        except jwt.InvalidTokenError as e:
            return False, {}, f"Invalid token: {str(e)}"
        except Exception as e:
            logger.error(f"Token verification error: {str(e)}")
            return False, {}, "Token verification failed"
    
    def refresh_tokens(self, refresh_token: str) -> Tuple[bool, Dict[str, Any], str]:
        """Refresh access token using refresh token with rotation."""
        try:
            # Verify refresh token
            valid, payload, error = self.verify_token(refresh_token, 'refresh')
            if not valid:
                return False, {}, error
            
            # Get session data
            session_id = payload.get('session_id')
            session_data = self.redis_client.hgetall(f"session:{session_id}")
            
            if not session_data:
                return False, {}, "Session not found"
            
            # Verify refresh token JTI matches stored value
            if session_data.get('refresh_jti') != payload.get('jti'):
                return False, {}, "Refresh token already used"
            
            # Generate new tokens (token rotation)
            user_id = payload['user_id']
            device_fingerprint = payload['device_fingerprint']
            permissions = payload.get('permissions', [])
            
            new_tokens = self.create_tokens(user_id, device_fingerprint, permissions)
            
            # Invalidate old refresh token
            old_refresh_jti = payload.get('jti')
            self.redis_client.delete(f"refresh_token:{old_refresh_jti}")
            
            return True, new_tokens, "Tokens refreshed successfully"
            
        except Exception as e:
            logger.error(f"Token refresh error: {str(e)}")
            return False, {}, "Token refresh failed"
    
    def revoke_session(self, session_id: str, user_id: str = None) -> bool:
        """Revoke a specific session."""
        try:
            session_data = self.redis_client.hgetall(f"session:{session_id}")
            
            if not session_data:
                return False
            
            # Verify user ownership if user_id provided
            if user_id and session_data.get('user_id') != user_id:
                return False
            
            # Mark session as inactive
            self.redis_client.hset(f"session:{session_id}", 'is_active', 'false')
            
            # Remove refresh token
            refresh_jti = session_data.get('refresh_jti')
            if refresh_jti:
                self.redis_client.delete(f"refresh_token:{refresh_jti}")
            
            return True
            
        except Exception as e:
            logger.error(f"Session revocation error: {str(e)}")
            return False
    
    def revoke_all_sessions(self, user_id: str, except_session: str = None) -> int:
        """Revoke all sessions for a user except specified session."""
        try:
            revoked_count = 0
            
            # Find all sessions for user
            pattern = "session:*"
            for key in self.redis_client.scan_iter(match=pattern):
                session_data = self.redis_client.hgetall(key)
                
                if (session_data.get('user_id') == user_id and 
                    session_data.get('is_active') == 'true'):
                    
                    session_id = key.split(':')[1]
                    
                    # Skip the exception session
                    if except_session and session_id == except_session:
                        continue
                    
                    if self.revoke_session(session_id):
                        revoked_count += 1
            
            return revoked_count
            
        except Exception as e:
            logger.error(f"Bulk session revocation error: {str(e)}")
            return 0
    
    def setup_mfa(self, user_id: str) -> Dict[str, Any]:
        """Setup Multi-Factor Authentication for user."""
        try:
            # Generate secret key for TOTP
            secret = pyotp.random_base32()
            
            # Store encrypted secret in Redis
            encrypted_secret = self.fernet.encrypt(secret.encode())
            self.redis_client.setex(
                f"mfa_setup:{user_id}", 
                300,  # 5 minutes to complete setup
                encrypted_secret
            )
            
            # Generate QR code URI
            totp = pyotp.TOTP(secret)
            qr_uri = totp.provisioning_uri(
                name=user_id,
                issuer_name="GuruAI Backend"
            )
            
            return {
                'secret': secret,
                'qr_uri': qr_uri,
                'backup_codes': self._generate_backup_codes()
            }
            
        except Exception as e:
            logger.error(f"MFA setup error: {str(e)}")
            raise
    
    def verify_mfa(self, user_id: str, token: str, is_backup_code: bool = False) -> bool:
        """Verify MFA token or backup code."""
        try:
            if is_backup_code:
                return self._verify_backup_code(user_id, token)
            
            # Get user's MFA secret
            encrypted_secret = self.redis_client.get(f"mfa_secret:{user_id}")
            if not encrypted_secret:
                return False
            
            secret = self.fernet.decrypt(encrypted_secret).decode()
            totp = pyotp.TOTP(secret)
            
            # Verify token with window tolerance
            return totp.verify(token, valid_window=1)
            
        except Exception as e:
            logger.error(f"MFA verification error: {str(e)}")
            return False
    
    def enable_mfa(self, user_id: str, verification_token: str) -> bool:
        """Enable MFA after verification."""
        try:
            # Get setup secret
            encrypted_secret = self.redis_client.get(f"mfa_setup:{user_id}")
            if not encrypted_secret:
                return False
            
            secret = self.fernet.decrypt(encrypted_secret).decode()
            totp = pyotp.TOTP(secret)
            
            # Verify token
            if not totp.verify(verification_token, valid_window=1):
                return False
            
            # Move secret to permanent storage
            self.redis_client.set(f"mfa_secret:{user_id}", encrypted_secret)
            self.redis_client.delete(f"mfa_setup:{user_id}")
            
            # Mark MFA as enabled
            self.redis_client.set(f"mfa_enabled:{user_id}", "true")
            
            return True
            
        except Exception as e:
            logger.error(f"MFA enable error: {str(e)}")
            return False
    
    def is_mfa_enabled(self, user_id: str) -> bool:
        """Check if MFA is enabled for user."""
        return self.redis_client.get(f"mfa_enabled:{user_id}") == "true"
    
    def _generate_backup_codes(self) -> list:
        """Generate backup codes for MFA recovery."""
        return [secrets.token_hex(4).upper() for _ in range(10)]
    
    def _verify_backup_code(self, user_id: str, code: str) -> bool:
        """Verify MFA backup code."""
        try:
            # Get unused backup codes
            codes_key = f"mfa_backup_codes:{user_id}"
            used_codes_key = f"mfa_used_codes:{user_id}"
            
            backup_codes = self.redis_client.smembers(codes_key)
            used_codes = self.redis_client.smembers(used_codes_key)
            
            if code.upper() in backup_codes and code.upper() not in used_codes:
                # Mark code as used
                self.redis_client.sadd(used_codes_key, code.upper())
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Backup code verification error: {str(e)}")
            return False
    
    def get_active_sessions(self, user_id: str) -> list:
        """Get all active sessions for a user."""
        try:
            sessions = []
            pattern = "session:*"
            
            for key in self.redis_client.scan_iter(match=pattern):
                session_data = self.redis_client.hgetall(key)
                
                if (session_data.get('user_id') == user_id and 
                    session_data.get('is_active') == 'true'):
                    
                    sessions.append({
                        'session_id': key.split(':')[1],
                        'device_fingerprint': session_data.get('device_fingerprint'),
                        'created_at': session_data.get('created_at'),
                        'last_activity': session_data.get('last_activity')
                    })
            
            return sessions
            
        except Exception as e:
            logger.error(f"Get active sessions error: {str(e)}")
            return []
    
    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions (run periodically)."""
        try:
            cleaned = 0
            pattern = "session:*"
            
            for key in self.redis_client.scan_iter(match=pattern):
                # Redis TTL will handle automatic cleanup
                # This is for manual cleanup if needed
                if self.redis_client.ttl(key) <= 0:
                    self.redis_client.delete(key)
                    cleaned += 1
            
            return cleaned
            
        except Exception as e:
            logger.error(f"Session cleanup error: {str(e)}")
            return 0
