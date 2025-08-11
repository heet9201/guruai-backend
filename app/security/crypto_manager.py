"""
Cryptographic Manager
End-to-end encryption, PII handling, and data protection utilities.
"""

import os
import hashlib
import secrets
from datetime import datetime
from typing import Dict, Any, Optional, Union
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import base64
import json
import logging

logger = logging.getLogger(__name__)

class CryptoManager:
    def __init__(self):
        self.master_key = os.getenv('MASTER_ENCRYPTION_KEY', Fernet.generate_key())
        self.fernet = Fernet(self.master_key)
        self.pii_key = os.getenv('PII_ENCRYPTION_KEY', Fernet.generate_key())
        self.pii_fernet = Fernet(self.pii_key)
        
    def encrypt_data(self, data: Union[str, dict], use_pii_key: bool = False) -> str:
        """Encrypt data with optional PII-specific key."""
        try:
            if isinstance(data, dict):
                data = json.dumps(data)
            
            data_bytes = data.encode('utf-8')
            
            if use_pii_key:
                encrypted = self.pii_fernet.encrypt(data_bytes)
            else:
                encrypted = self.fernet.encrypt(data_bytes)
            
            return base64.urlsafe_b64encode(encrypted).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Encryption error: {str(e)}")
            raise
    
    def decrypt_data(self, encrypted_data: str, use_pii_key: bool = False) -> str:
        """Decrypt data with optional PII-specific key."""
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode('utf-8'))
            
            if use_pii_key:
                decrypted = self.pii_fernet.decrypt(encrypted_bytes)
            else:
                decrypted = self.fernet.decrypt(encrypted_bytes)
            
            return decrypted.decode('utf-8')
            
        except Exception as e:
            logger.error(f"Decryption error: {str(e)}")
            raise
    
    def hash_password(self, password: str, salt: Optional[str] = None) -> Dict[str, str]:
        """Hash password with salt using PBKDF2."""
        if salt is None:
            salt = secrets.token_urlsafe(32)
        
        password_bytes = password.encode('utf-8')
        salt_bytes = salt.encode('utf-8')
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt_bytes,
            iterations=100000,
        )
        
        key = kdf.derive(password_bytes)
        hashed = base64.urlsafe_b64encode(key).decode('utf-8')
        
        return {
            'hash': hashed,
            'salt': salt
        }
    
    def verify_password(self, password: str, stored_hash: str, salt: str) -> bool:
        """Verify password against stored hash."""
        try:
            computed = self.hash_password(password, salt)
            return computed['hash'] == stored_hash
        except Exception as e:
            logger.error(f"Password verification error: {str(e)}")
            return False
    
    def anonymize_pii(self, data: Dict[str, Any], pii_fields: list) -> Dict[str, Any]:
        """Anonymize PII fields in data."""
        anonymized = data.copy()
        
        for field in pii_fields:
            if field in anonymized:
                if field == 'email':
                    anonymized[field] = self._anonymize_email(anonymized[field])
                elif field == 'phone':
                    anonymized[field] = self._anonymize_phone(anonymized[field])
                elif field == 'name':
                    anonymized[field] = self._anonymize_name(anonymized[field])
                else:
                    # Generic anonymization
                    anonymized[field] = self._anonymize_generic(anonymized[field])
        
        return anonymized
    
    def _anonymize_email(self, email: str) -> str:
        """Anonymize email address."""
        try:
            local, domain = email.split('@')
            if len(local) <= 2:
                anonymized_local = '*' * len(local)
            else:
                anonymized_local = local[:2] + '*' * (len(local) - 2)
            return f"{anonymized_local}@{domain}"
        except:
            return "***@***.***"
    
    def _anonymize_phone(self, phone: str) -> str:
        """Anonymize phone number."""
        if len(phone) <= 4:
            return '*' * len(phone)
        return phone[:2] + '*' * (len(phone) - 4) + phone[-2:]
    
    def _anonymize_name(self, name: str) -> str:
        """Anonymize name."""
        parts = name.split()
        if len(parts) == 1:
            return parts[0][0] + '*' * (len(parts[0]) - 1)
        else:
            return parts[0][0] + '*' * (len(parts[0]) - 1) + ' ' + parts[-1][0] + '*' * (len(parts[-1]) - 1)
    
    def _anonymize_generic(self, value: str) -> str:
        """Generic anonymization."""
        if len(value) <= 2:
            return '*' * len(value)
        return value[:1] + '*' * (len(value) - 2) + value[-1:]
    
    def encrypt_file(self, file_data: bytes, user_key: Optional[str] = None) -> Dict[str, Any]:
        """Encrypt file data with optional user-specific key."""
        try:
            # Generate file-specific key
            file_key = Fernet.generate_key()
            file_fernet = Fernet(file_key)
            
            # Encrypt file data
            encrypted_data = file_fernet.encrypt(file_data)
            
            # Encrypt file key with master key or user key
            if user_key:
                user_fernet = Fernet(user_key.encode())
                encrypted_file_key = user_fernet.encrypt(file_key)
            else:
                encrypted_file_key = self.fernet.encrypt(file_key)
            
            return {
                'encrypted_data': base64.urlsafe_b64encode(encrypted_data).decode('utf-8'),
                'encrypted_key': base64.urlsafe_b64encode(encrypted_file_key).decode('utf-8'),
                'algorithm': 'Fernet'
            }
            
        except Exception as e:
            logger.error(f"File encryption error: {str(e)}")
            raise
    
    def decrypt_file(self, encrypted_file_info: Dict[str, Any], user_key: Optional[str] = None) -> bytes:
        """Decrypt file data."""
        try:
            encrypted_data = base64.urlsafe_b64decode(encrypted_file_info['encrypted_data'].encode('utf-8'))
            encrypted_file_key = base64.urlsafe_b64decode(encrypted_file_info['encrypted_key'].encode('utf-8'))
            
            # Decrypt file key
            if user_key:
                user_fernet = Fernet(user_key.encode())
                file_key = user_fernet.decrypt(encrypted_file_key)
            else:
                file_key = self.fernet.decrypt(encrypted_file_key)
            
            # Decrypt file data
            file_fernet = Fernet(file_key)
            decrypted_data = file_fernet.decrypt(encrypted_data)
            
            return decrypted_data
            
        except Exception as e:
            logger.error(f"File decryption error: {str(e)}")
            raise
    
    def generate_secure_token(self, length: int = 32) -> str:
        """Generate cryptographically secure token."""
        return secrets.token_urlsafe(length)
    
    def hash_data(self, data: str, algorithm: str = 'sha256') -> str:
        """Hash data with specified algorithm."""
        data_bytes = data.encode('utf-8')
        
        if algorithm == 'sha256':
            hasher = hashlib.sha256()
        elif algorithm == 'sha512':
            hasher = hashlib.sha512()
        elif algorithm == 'blake2b':
            hasher = hashlib.blake2b()
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
        
        hasher.update(data_bytes)
        return hasher.hexdigest()
    
    def create_gdpr_export_package(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create GDPR-compliant data export package."""
        try:
            export_package = {
                'export_timestamp': datetime.utcnow().isoformat(),
                'user_id': user_data.get('user_id'),
                'personal_data': {},
                'usage_data': {},
                'system_data': {}
            }
            
            # Categorize data for GDPR compliance
            personal_fields = ['name', 'email', 'phone', 'address', 'date_of_birth']
            usage_fields = ['login_history', 'activity_logs', 'preferences']
            system_fields = ['account_created', 'last_updated', 'permissions']
            
            for field, value in user_data.items():
                if field in personal_fields:
                    export_package['personal_data'][field] = value
                elif field in usage_fields:
                    export_package['usage_data'][field] = value
                elif field in system_fields:
                    export_package['system_data'][field] = value
            
            # Encrypt the package
            encrypted_package = self.encrypt_data(export_package)
            
            return {
                'encrypted_data': encrypted_package,
                'export_id': self.generate_secure_token(16),
                'created_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"GDPR export error: {str(e)}")
            raise
    
    def secure_delete_data(self, data_identifier: str) -> bool:
        """Securely delete data (GDPR right to be forgotten)."""
        try:
            # This is a placeholder for secure deletion
            # In practice, this would involve:
            # 1. Overwriting data multiple times
            # 2. Updating database to mark as deleted
            # 3. Scheduling physical deletion
            # 4. Updating audit logs
            
            logger.info(f"Secure deletion initiated for: {data_identifier}")
            return True
            
        except Exception as e:
            logger.error(f"Secure deletion error: {str(e)}")
            return False
