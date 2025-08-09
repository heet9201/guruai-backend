import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from firebase_admin import firestore
from app.utils.auth_utils import DeviceUtils

logger = logging.getLogger(__name__)

class DeviceService:
    """Service for managing user devices and security."""
    
    def __init__(self, db):
        self.db = db
    
    def register_device(self, user_id: str, device_id: str, request) -> Dict[str, Any]:
        """Register or update a device for a user."""
        try:
            device_fingerprint = DeviceUtils.generate_device_fingerprint(request)
            client_ip = DeviceUtils.get_client_ip(request)
            
            device_data = {
                'device_id': device_id,
                'user_id': user_id,
                'fingerprint': device_fingerprint,
                'ip_address': client_ip,
                'user_agent': request.headers.get('User-Agent', ''),
                'last_seen': firestore.SERVER_TIMESTAMP,
                'created_at': firestore.SERVER_TIMESTAMP,
                'is_active': True,
                'login_count': 1
            }
            
            # Check if device already exists
            device_ref = self.db.collection('devices').document(f"{user_id}_{device_id}")
            existing_device = device_ref.get()
            
            if existing_device.exists:
                # Update existing device
                update_data = {
                    'fingerprint': device_fingerprint,
                    'ip_address': client_ip,
                    'user_agent': request.headers.get('User-Agent', ''),
                    'last_seen': firestore.SERVER_TIMESTAMP,
                    'login_count': firestore.Increment(1)
                }
                device_ref.update(update_data)
                logger.info(f"Updated device {device_id} for user {user_id}")
            else:
                # Create new device
                device_ref.set(device_data)
                logger.info(f"Registered new device {device_id} for user {user_id}")
            
            return {
                'success': True,
                'device_fingerprint': device_fingerprint
            }
            
        except Exception as e:
            logger.error(f"Error registering device: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_user_devices(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all devices for a user."""
        try:
            devices_ref = self.db.collection('devices').where('user_id', '==', user_id)
            devices = []
            
            for doc in devices_ref.stream():
                device_data = doc.to_dict()
                device_data['id'] = doc.id
                devices.append(device_data)
            
            return devices
            
        except Exception as e:
            logger.error(f"Error getting user devices: {str(e)}")
            return []
    
    def deactivate_device(self, user_id: str, device_id: str) -> bool:
        """Deactivate a specific device."""
        try:
            device_ref = self.db.collection('devices').document(f"{user_id}_{device_id}")
            device_ref.update({
                'is_active': False,
                'deactivated_at': firestore.SERVER_TIMESTAMP
            })
            
            logger.info(f"Deactivated device {device_id} for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deactivating device: {str(e)}")
            return False
    
    def verify_device(self, user_id: str, device_id: str, request) -> Dict[str, Any]:
        """Verify if device is valid and trusted."""
        try:
            device_ref = self.db.collection('devices').document(f"{user_id}_{device_id}")
            device_doc = device_ref.get()
            
            if not device_doc.exists:
                return {
                    'valid': False,
                    'reason': 'Device not registered'
                }
            
            device_data = device_doc.to_dict()
            
            if not device_data.get('is_active', False):
                return {
                    'valid': False,
                    'reason': 'Device is deactivated'
                }
            
            # Check device fingerprint (optional security check)
            current_fingerprint = DeviceUtils.generate_device_fingerprint(request)
            stored_fingerprint = device_data.get('fingerprint')
            
            fingerprint_match = current_fingerprint == stored_fingerprint
            
            return {
                'valid': True,
                'fingerprint_match': fingerprint_match,
                'device_data': device_data
            }
            
        except Exception as e:
            logger.error(f"Error verifying device: {str(e)}")
            return {
                'valid': False,
                'reason': 'Device verification failed'
            }

class SecurityService:
    """Service for tracking failed login attempts and security events."""
    
    def __init__(self, db):
        self.db = db
    
    def track_failed_login(self, email: str, ip_address: str, device_id: str = None) -> None:
        """Track failed login attempt."""
        try:
            failed_attempt = {
                'email': email,
                'ip_address': ip_address,
                'device_id': device_id,
                'timestamp': firestore.SERVER_TIMESTAMP,
                'type': 'failed_login'
            }
            
            self.db.collection('security_events').add(failed_attempt)
            logger.warning(f"Failed login attempt tracked for {email} from {ip_address}")
            
        except Exception as e:
            logger.error(f"Error tracking failed login: {str(e)}")
    
    def get_failed_login_count(self, email: str, time_window_minutes: int = 15) -> int:
        """Get count of failed login attempts for email within time window."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(minutes=time_window_minutes)
            
            failed_attempts_ref = (
                self.db.collection('security_events')
                .where('email', '==', email)
                .where('type', '==', 'failed_login')
                .where('timestamp', '>=', cutoff_time)
            )
            
            return len(list(failed_attempts_ref.stream()))
            
        except Exception as e:
            logger.error(f"Error getting failed login count: {str(e)}")
            return 0
    
    def is_account_locked(self, email: str, max_attempts: int = 5) -> bool:
        """Check if account is locked due to too many failed attempts."""
        failed_count = self.get_failed_login_count(email)
        return failed_count >= max_attempts
    
    def clear_failed_attempts(self, email: str) -> None:
        """Clear failed login attempts for successful login."""
        try:
            # Delete recent failed attempts for this email
            cutoff_time = datetime.utcnow() - timedelta(hours=1)
            
            failed_attempts_ref = (
                self.db.collection('security_events')
                .where('email', '==', email)
                .where('type', '==', 'failed_login')
                .where('timestamp', '>=', cutoff_time)
            )
            
            for doc in failed_attempts_ref.stream():
                doc.reference.delete()
            
            logger.info(f"Cleared failed login attempts for {email}")
            
        except Exception as e:
            logger.error(f"Error clearing failed attempts: {str(e)}")
    
    def track_token_invalidation(self, user_id: str, token_jti: str, reason: str) -> None:
        """Track token invalidation for security audit."""
        try:
            invalidation_event = {
                'user_id': user_id,
                'token_jti': token_jti,
                'reason': reason,
                'timestamp': firestore.SERVER_TIMESTAMP,
                'type': 'token_invalidation'
            }
            
            self.db.collection('security_events').add(invalidation_event)
            
            # Also store in invalidated tokens collection for quick lookup
            self.db.collection('invalidated_tokens').document(token_jti).set({
                'user_id': user_id,
                'invalidated_at': firestore.SERVER_TIMESTAMP,
                'reason': reason
            })
            
            logger.info(f"Token invalidation tracked for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error tracking token invalidation: {str(e)}")
    
    def is_token_invalidated(self, token_jti: str) -> bool:
        """Check if token has been invalidated."""
        try:
            token_doc = self.db.collection('invalidated_tokens').document(token_jti).get()
            return token_doc.exists
            
        except Exception as e:
            logger.error(f"Error checking token invalidation: {str(e)}")
            return False
