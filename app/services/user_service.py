import logging
from typing import Dict, Any, Optional
from firebase_admin import firestore, auth as firebase_auth
from app.utils.auth_utils import JWTUtils

logger = logging.getLogger(__name__)

class UserService:
    """Service for user profile management."""
    
    def __init__(self, db):
        self.db = db
    
    def create_user_profile(self, firebase_user, additional_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create comprehensive user profile in Firestore."""
        try:
            user_data = {
                'uid': firebase_user.uid,
                'email': firebase_user.email,
                'name': firebase_user.display_name or additional_data.get('name', ''),
                'school': additional_data.get('school', ''),
                'subjects': additional_data.get('subjects', []),
                'grades': additional_data.get('grades', []),
                'language': additional_data.get('language', 'en'),
                'profileImage': additional_data.get('profileImage', ''),
                'role': additional_data.get('role', 'teacher'),
                'created_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP,
                'email_verified': firebase_user.email_verified,
                'profile_complete': bool(additional_data.get('school')),
                'settings': {
                    'notifications': True,
                    'theme': 'light',
                    'language': additional_data.get('language', 'en')
                },
                'stats': {
                    'login_count': 0,
                    'last_login': None,
                    'sessions_created': 0
                }
            }
            
            # Store in Firestore
            self.db.collection('users').document(firebase_user.uid).set(user_data)
            logger.info(f"User profile created for: {firebase_user.email}")
            
            return {
                'success': True,
                'user_data': user_data
            }
            
        except Exception as e:
            logger.error(f"Error creating user profile: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get user profile from Firestore."""
        try:
            user_doc = self.db.collection('users').document(user_id).get()
            
            if not user_doc.exists:
                return {
                    'success': False,
                    'error': 'User profile not found'
                }
            
            user_data = user_doc.to_dict()
            
            # Format response according to API specification
            profile = {
                'id': user_id,
                'email': user_data.get('email'),
                'name': user_data.get('name'),
                'school': user_data.get('school', ''),
                'subjects': user_data.get('subjects', []),
                'grades': user_data.get('grades', []),
                'language': user_data.get('language', 'en'),
                'profileImage': user_data.get('profileImage', ''),
                'role': user_data.get('role', 'teacher'),
                'email_verified': user_data.get('email_verified', False),
                'profile_complete': user_data.get('profile_complete', False),
                'created_at': user_data.get('created_at'),
                'updated_at': user_data.get('updated_at')
            }
            
            return {
                'success': True,
                'profile': profile
            }
            
        except Exception as e:
            logger.error(f"Error getting user profile: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def update_user_profile(self, user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update user profile in Firestore."""
        try:
            # Validate allowed fields
            allowed_fields = [
                'name', 'school', 'subjects', 'grades', 
                'language', 'profileImage', 'settings'
            ]
            
            # Filter updates to only allowed fields
            filtered_updates = {
                key: value for key, value in updates.items() 
                if key in allowed_fields
            }
            
            if not filtered_updates:
                return {
                    'success': False,
                    'error': 'No valid fields to update'
                }
            
            # Add timestamp
            filtered_updates['updated_at'] = firestore.SERVER_TIMESTAMP
            
            # Check if profile is now complete
            if 'school' in filtered_updates and filtered_updates['school']:
                filtered_updates['profile_complete'] = True
            
            # Update in Firestore
            self.db.collection('users').document(user_id).update(filtered_updates)
            
            # Get updated profile
            updated_profile = self.get_user_profile(user_id)
            
            logger.info(f"User profile updated for: {user_id}")
            
            return {
                'success': True,
                'profile': updated_profile.get('profile'),
                'message': 'Profile updated successfully'
            }
            
        except Exception as e:
            logger.error(f"Error updating user profile: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def update_login_stats(self, user_id: str) -> None:
        """Update user login statistics."""
        try:
            self.db.collection('users').document(user_id).update({
                'stats.login_count': firestore.Increment(1),
                'stats.last_login': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP
            })
            
        except Exception as e:
            logger.error(f"Error updating login stats: {str(e)}")
    
    def format_user_response(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format user data for API response."""
        return {
            'id': user_data.get('uid') or user_data.get('id'),
            'email': user_data.get('email'),
            'name': user_data.get('name'),
            'school': user_data.get('school', ''),
            'subjects': user_data.get('subjects', []),
            'grades': user_data.get('grades', []),
            'language': user_data.get('language', 'en'),
            'profileImage': user_data.get('profileImage', ''),
            'role': user_data.get('role', 'teacher'),
            'email_verified': user_data.get('email_verified', False)
        }
    
    def delete_user_data(self, user_id: str) -> Dict[str, Any]:
        """Delete all user data (GDPR compliance)."""
        try:
            # Delete user profile
            self.db.collection('users').document(user_id).delete()
            
            # Delete user devices
            devices_ref = self.db.collection('devices').where('user_id', '==', user_id)
            for device_doc in devices_ref.stream():
                device_doc.reference.delete()
            
            # Delete security events
            security_ref = self.db.collection('security_events').where('user_id', '==', user_id)
            for event_doc in security_ref.stream():
                event_doc.reference.delete()
            
            # Delete Firebase Auth user
            firebase_auth.delete_user(user_id)
            
            logger.info(f"All user data deleted for: {user_id}")
            
            return {
                'success': True,
                'message': 'All user data deleted successfully'
            }
            
        except Exception as e:
            logger.error(f"Error deleting user data: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
