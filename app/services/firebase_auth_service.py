import logging
import jwt
import uuid
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import firebase_admin
from firebase_admin import credentials, auth as firebase_auth, firestore
from flask import current_app

logger = logging.getLogger(__name__)

class FirebaseAuthService:
    """Enhanced Authentication Service with Firebase Integration."""
    
    def __init__(self):
        self.firebase_app = None
        self.db = None
        self._initialized = False
    
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
    
    def authenticate_user(self, email: str, password: str) -> Dict[str, Any]:
        """Authenticate user with Firebase."""
        try:
            self._ensure_initialized()
            
            if not self.firebase_app:
                return {
                    'success': False,
                    'message': 'Firebase not available'
                }
            
            # Note: Firebase Admin SDK doesn't support password verification directly
            # For password verification, you would typically use Firebase Client SDK
            # or implement a custom verification flow
            
            # Get user by email
            try:
                firebase_user = firebase_auth.get_user_by_email(email)
            except firebase_auth.UserNotFoundError:
                return {
                    'success': False,
                    'message': 'Invalid email or password'
                }
            
            # Get user profile from Firestore
            user_profile = {}
            if self.db:
                user_doc = self.db.collection('users').document(firebase_user.uid).get()
                if user_doc.exists:
                    user_profile = user_doc.to_dict()
            
            # Generate custom token
            custom_token = firebase_auth.create_custom_token(firebase_user.uid).decode('utf-8')
            
            # Prepare user data
            user_data = {
                'id': firebase_user.uid,
                'uid': firebase_user.uid,
                'email': firebase_user.email,
                'name': user_profile.get('name', firebase_user.display_name),
                'display_name': firebase_user.display_name,
                'email_verified': firebase_user.email_verified,
                'role': user_profile.get('role', 'user')
            }
            
            # Update last login
            if self.db:
                self.db.collection('users').document(firebase_user.uid).update({
                    'last_login': firestore.SERVER_TIMESTAMP
                })
            
            logger.info(f"User authenticated successfully: {email}")
            
            return {
                'success': True,
                'token': custom_token,
                'user': user_data
            }
            
        except Exception as e:
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

# Maintain compatibility with existing code
class AuthService(FirebaseAuthService):
    """Compatibility wrapper for the existing AuthService."""
    pass
