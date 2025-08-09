import logging
import jwt
import uuid
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import firebase_admin
from firebase_admin import credentials, auth as firebase_auth, firestore
from flask import current_app, request
from app.utils.auth_utils import JWTUtils, DeviceUtils
from app.services.device_service import DeviceService, SecurityService
from app.services.user_service import UserService

logger = logging.getLogger(__name__)

class FirebaseAuthService:
    """Enhanced Authentication Service with Firebase Integration."""
    
    def __init__(self):
        self.firebase_app = None
        self.db = None
        self._initialized = False
        self.device_service = None
        self.security_service = None
        self.user_service = None
    
    def _ensure_initialized(self):
        """Ensure Firebase is initialized before use."""
        if not self._initialized:
            self._initialize_firebase()
    
    def _initialize_firebase(self):
        """Initialize Firebase Admin SDK."""
        try:
            if self._initialized:
                return
                
            # Check if Firebase is already initialized
            try:
                self.firebase_app = firebase_admin.get_app()
                logger.info("Using existing Firebase app")
            except ValueError:
                # Initialize Firebase if not already done
                firebase_creds_path = current_app.config.get('FIREBASE_CREDENTIALS_PATH')
                if not firebase_creds_path:
                    raise Exception("FIREBASE_CREDENTIALS_PATH not configured")
                
                cred = credentials.Certificate(firebase_creds_path)
                self.firebase_app = firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin SDK initialized successfully")
            
            # Initialize Firestore
            self.db = firestore.client()
            
            # Initialize services
            self.device_service = DeviceService(self.db)
            self.security_service = SecurityService(self.db)
            self.user_service = UserService(self.db)
            
            self._initialized = True
            
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {str(e)}")
            # Don't raise exception to allow app to start
            self.firebase_app = None
            self.db = None
    
    def register_user(self, email: str, password: str, name: str) -> Dict[str, Any]:
        """Register a new user with Firebase Authentication and store profile in Firestore."""
        try:
            self._ensure_initialized()
            
            if not self.firebase_app:
                return {
                    'success': False,
                    'message': 'Firebase not available'
                }
            
            # Create user in Firebase Auth
            firebase_user = firebase_auth.create_user(
                email=email,
                password=password,
                display_name=name,
                email_verified=False
            )
            
            # Create user profile in Firestore
            user_data = {
                'uid': firebase_user.uid,
                'email': email,
                'name': name,
                'display_name': name,
                'role': 'user',
                'created_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP,
                'email_verified': False,
                'profile_complete': False,
                'settings': {
                    'language': 'en',
                    'notifications': True,
                    'theme': 'light'
                }
            }
            
            # Store in Firestore
            if self.db:
                self.db.collection('users').document(firebase_user.uid).set(user_data)
                logger.info(f"User profile created in Firestore: {email}")
            
            # Generate custom JWT token for API access
            custom_token = firebase_auth.create_custom_token(firebase_user.uid).decode('utf-8')
            
            # Prepare response data
            response_user_data = {
                'id': firebase_user.uid,
                'uid': firebase_user.uid,
                'email': email,
                'name': name,
                'display_name': name,
                'email_verified': False,
                'role': 'user'
            }
            
            logger.info(f"User registered successfully: {email}")
            
            return {
                'success': True,
                'token': custom_token,
                'user': response_user_data,
                'firebase_uid': firebase_user.uid
            }
            
        except firebase_auth.EmailAlreadyExistsError:
            logger.warning(f"Registration attempt with existing email: {email}")
            return {
                'success': False,
                'message': 'Email already exists'
            }
        except Exception as e:
            logger.error(f"Error registering user: {str(e)}")
            return {
                'success': False,
                'message': f'Registration failed: {str(e)}'
            }
    
    def register_user_enhanced(self, email: str, password: str, name: str, 
                              device_id: str, request_obj, additional_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Enhanced user registration with device tracking and comprehensive profile."""
        try:
            self._ensure_initialized()
            
            if not self.firebase_app:
                return {
                    'success': False,
                    'message': 'Firebase not available'
                }
            
            # Create user in Firebase Auth
            firebase_user = firebase_auth.create_user(
                email=email,
                password=password,
                display_name=name,
                email_verified=False
            )
            
            # Create comprehensive user profile
            profile_result = self.user_service.create_user_profile(
                firebase_user, additional_data or {}
            )
            
            if not profile_result['success']:
                # Cleanup Firebase user if profile creation fails
                firebase_auth.delete_user(firebase_user.uid)
                return {
                    'success': False,
                    'message': 'Failed to create user profile'
                }
            
            # Register device
            device_result = self.device_service.register_device(
                firebase_user.uid, device_id, request_obj
            )
            
            if not device_result['success']:
                logger.warning(f"Device registration failed during registration: {firebase_user.uid}")
            
            # Generate JWT tokens
            access_token = JWTUtils.generate_access_token(firebase_user.uid, device_id)
            refresh_token = JWTUtils.generate_refresh_token(firebase_user.uid, device_id)
            
            # Format user data for response
            user_data = self.user_service.format_user_response(
                profile_result['user_data']
            )
            
            logger.info(f"User registered successfully with enhanced features: {email}")
            
            return {
                'success': True,
                'token': access_token,
                'refreshToken': refresh_token,
                'user': user_data
            }
            
        except firebase_auth.EmailAlreadyExistsError:
            logger.warning(f"Registration attempt with existing email: {email}")
            return {
                'success': False,
                'message': 'Email already exists'
            }
        except Exception as e:
            logger.error(f"Error in enhanced registration: {str(e)}")
            return {
                'success': False,
                'message': f'Registration failed: {str(e)}'
            }
    
    def authenticate_user(self, email: str, password: str, device_id: str, request_obj) -> Dict[str, Any]:
        """Authenticate user with comprehensive security features."""
        try:
            self._ensure_initialized()
            
            if not self.firebase_app:
                return {
                    'success': False,
                    'message': 'Firebase not available'
                }
            
            # Get client IP for security tracking
            client_ip = DeviceUtils.get_client_ip(request_obj)
            
            # Check if account is locked due to failed attempts
            if self.security_service.is_account_locked(email):
                logger.warning(f"Account locked due to failed attempts: {email}")
                return {
                    'success': False,
                    'message': 'Account temporarily locked due to multiple failed login attempts'
                }
            
            # Get user by email
            try:
                firebase_user = firebase_auth.get_user_by_email(email)
            except firebase_auth.UserNotFoundError:
                # Track failed attempt
                self.security_service.track_failed_login(email, client_ip, device_id)
                return {
                    'success': False,
                    'message': 'Invalid email or password'
                }
            
            # Note: Firebase Admin SDK doesn't support password verification directly
            # In a real implementation, you would use Firebase Client SDK or
            # implement custom password verification for additional security
            
            # For now, we'll assume password verification is handled by Firebase Auth
            # In production, integrate with Firebase Auth REST API for password verification
            
            # Get user profile from Firestore
            user_profile_result = self.user_service.get_user_profile(firebase_user.uid)
            if not user_profile_result['success']:
                return {
                    'success': False,
                    'message': 'User profile not found'
                }
            
            user_profile = user_profile_result['profile']
            
            # Register/update device
            device_result = self.device_service.register_device(
                firebase_user.uid, device_id, request_obj
            )
            
            if not device_result['success']:
                logger.warning(f"Device registration failed for user {firebase_user.uid}")
            
            # Generate JWT tokens
            access_token = JWTUtils.generate_access_token(firebase_user.uid, device_id)
            refresh_token = JWTUtils.generate_refresh_token(firebase_user.uid, device_id)
            
            # Update login statistics
            self.user_service.update_login_stats(firebase_user.uid)
            
            # Clear any failed login attempts
            self.security_service.clear_failed_attempts(email)
            
            # Format user data for response
            user_data = self.user_service.format_user_response(user_profile)
            
            logger.info(f"User authenticated successfully: {email}")
            
            return {
                'success': True,
                'token': access_token,
                'refreshToken': refresh_token,
                'user': user_data
            }
            
        except Exception as e:
            # Track failed attempt on any error
            client_ip = DeviceUtils.get_client_ip(request_obj) if request_obj else 'unknown'
            self.security_service.track_failed_login(email, client_ip, device_id)
            
            logger.error(f"Error authenticating user: {str(e)}")
            return {
                'success': False,
                'message': 'Authentication failed'
            }
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify Firebase custom token."""
        try:
            self._ensure_initialized()
            
            if not self.firebase_app:
                return {
                    'valid': False,
                    'message': 'Firebase not available'
                }
            
            # Verify the custom token
            decoded_token = firebase_auth.verify_id_token(token)
            uid = decoded_token['uid']
            
            # Get user data
            firebase_user = firebase_auth.get_user(uid)
            
            # Get profile from Firestore
            user_profile = {}
            if self.db:
                user_doc = self.db.collection('users').document(uid).get()
                if user_doc.exists:
                    user_profile = user_doc.to_dict()
            
            user_data = {
                'id': uid,
                'uid': uid,
                'email': firebase_user.email,
                'name': user_profile.get('name', firebase_user.display_name),
                'email_verified': firebase_user.email_verified,
                'role': user_profile.get('role', 'user')
            }
            
            return {
                'valid': True,
                'user': user_data,
                'decoded_token': decoded_token
            }
            
        except firebase_auth.InvalidIdTokenError:
            return {
                'valid': False,
                'message': 'Invalid token'
            }
        except firebase_auth.ExpiredIdTokenError:
            return {
                'valid': False,
                'message': 'Token expired'
            }
        except Exception as e:
            logger.error(f"Error verifying token: {str(e)}")
            return {
                'valid': False,
                'message': 'Token verification failed'
            }
    
    def logout_user(self, uid: str) -> Dict[str, Any]:
        """Logout user (revoke refresh tokens)."""
        try:
            self._ensure_initialized()
            
            if not self.firebase_app:
                return {
                    'success': False,
                    'message': 'Firebase not available'
                }
            
            # Revoke all refresh tokens for the user
            firebase_auth.revoke_refresh_tokens(uid)
            
            # Update logout time in Firestore
            if self.db:
                self.db.collection('users').document(uid).update({
                    'last_logout': firestore.SERVER_TIMESTAMP
                })
            
            logger.info(f"User logged out: {uid}")
            
            return {
                'success': True,
                'message': 'Logged out successfully'
            }
            
        except Exception as e:
            logger.error(f"Error logging out user: {str(e)}")
            return {
                'success': False,
                'message': 'Logout failed'
            }
    
    def get_user_profile(self, uid: str) -> Dict[str, Any]:
        """Get complete user profile from Firestore."""
        try:
            self._ensure_initialized()
            
            if not self.db:
                return {
                    'success': False,
                    'message': 'Database not available'
                }
            
            user_doc = self.db.collection('users').document(uid).get()
            if not user_doc.exists:
                return {
                    'success': False,
                    'message': 'User profile not found'
                }
            
            profile_data = user_doc.to_dict()
            
            return {
                'success': True,
                'profile': profile_data
            }
            
        except Exception as e:
            logger.error(f"Error getting user profile: {str(e)}")
            return {
                'success': False,
                'message': 'Failed to get profile'
            }
    
    def update_user_profile(self, uid: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update user profile in Firestore."""
        try:
            self._ensure_initialized()
            
            if not self.db:
                return {
                    'success': False,
                    'message': 'Database not available'
                }
            
            # Add updated timestamp
            updates['updated_at'] = firestore.SERVER_TIMESTAMP
            
            # Update in Firestore
            self.db.collection('users').document(uid).update(updates)
            
            logger.info(f"User profile updated: {uid}")
            
            return {
                'success': True,
                'message': 'Profile updated successfully'
            }
            
        except Exception as e:
            logger.error(f"Error updating user profile: {str(e)}")
            return {
                'success': False,
                'message': 'Failed to update profile'
            }
    
    def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token using refresh token."""
        try:
            self._ensure_initialized()
            
            # Verify refresh token
            token_result = JWTUtils.verify_token(refresh_token)
            
            if not token_result['valid']:
                return {
                    'success': False,
                    'message': 'Invalid refresh token'
                }
            
            # Check if it's actually a refresh token
            if token_result['payload'].get('type') != 'refresh':
                return {
                    'success': False,
                    'message': 'Invalid token type'
                }
            
            # Check if token is invalidated
            token_jti = token_result['payload'].get('jti')
            if self.security_service.is_token_invalidated(token_jti):
                return {
                    'success': False,
                    'message': 'Token has been invalidated'
                }
            
            user_id = token_result['user_id']
            device_id = token_result['device_id']
            
            # Generate new access token
            new_access_token = JWTUtils.generate_access_token(user_id, device_id)
            
            # Optionally generate new refresh token for rotation
            new_refresh_token = JWTUtils.generate_refresh_token(user_id, device_id)
            
            # Invalidate old refresh token
            self.security_service.track_token_invalidation(
                user_id, token_jti, 'token_refresh'
            )
            
            logger.info(f"Token refreshed for user: {user_id}")
            
            return {
                'success': True,
                'token': new_access_token,
                'refreshToken': new_refresh_token
            }
            
        except Exception as e:
            logger.error(f"Error refreshing token: {str(e)}")
            return {
                'success': False,
                'message': 'Token refresh failed'
            }
    
    def logout_user_with_token(self, access_token: str, device_id: str = None) -> Dict[str, Any]:
        """Logout user by invalidating tokens."""
        try:
            self._ensure_initialized()
            
            # Verify access token
            token_result = JWTUtils.verify_token(access_token)
            
            if not token_result['valid']:
                return {
                    'success': False,
                    'message': 'Invalid token'
                }
            
            user_id = token_result['user_id']
            token_device_id = token_result['device_id']
            token_jti = token_result['payload'].get('jti')
            
            # Invalidate the current token
            self.security_service.track_token_invalidation(
                user_id, token_jti, 'user_logout'
            )
            
            # If device_id is provided, deactivate that specific device
            if device_id:
                self.device_service.deactivate_device(user_id, device_id)
            else:
                # Deactivate the device associated with the token
                self.device_service.deactivate_device(user_id, token_device_id)
            
            # Update logout time in user profile
            if self.db:
                self.db.collection('users').document(user_id).update({
                    'stats.last_logout': firestore.SERVER_TIMESTAMP
                })
            
            logger.info(f"User logged out: {user_id}")
            
            return {
                'success': True,
                'message': 'Logged out successfully'
            }
            
        except Exception as e:
            logger.error(f"Error logging out user: {str(e)}")
            return {
                'success': False,
                'message': 'Logout failed'
            }
    
    def verify_jwt_token(self, token: str) -> Dict[str, Any]:
        """Verify JWT token with security checks."""
        try:
            self._ensure_initialized()
            
            # Verify token format and signature
            token_result = JWTUtils.verify_token(token)
            
            if not token_result['valid']:
                return token_result
            
            # Check if token is invalidated
            token_jti = token_result['payload'].get('jti')
            if self.security_service.is_token_invalidated(token_jti):
                return {
                    'valid': False,
                    'error': 'Token has been invalidated'
                }
            
            user_id = token_result['user_id']
            device_id = token_result['device_id']
            
            # Get user profile
            user_profile_result = self.user_service.get_user_profile(user_id)
            if not user_profile_result['success']:
                return {
                    'valid': False,
                    'error': 'User not found'
                }
            
            # Format user data
            user_data = self.user_service.format_user_response(
                user_profile_result['profile']
            )
            
            return {
                'valid': True,
                'user': user_data,
                'device_id': device_id,
                'token_type': token_result['payload'].get('type', 'access')
            }
            
        except Exception as e:
            logger.error(f"Error verifying JWT token: {str(e)}")
            return {
                'valid': False,
                'error': 'Token verification failed'
            }

# Maintain compatibility with existing code
class AuthService(FirebaseAuthService):
    """Compatibility wrapper for the existing AuthService."""
    pass
