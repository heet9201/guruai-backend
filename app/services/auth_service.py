import logging
import jwt
import hashlib
import redis
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, auth
import json

logger = logging.getLogger(__name__)

class AuthService:
    """Service for authentication and authorization operations."""
    
    def __init__(self):
        self.redis_client = None
        self.firebase_app = None
        self._initialize_services()
    
    def _initialize_services(self):
        """Initialize Redis and Firebase services."""
        try:
            from flask import current_app
            
            # Initialize Redis with fallback to in-memory storage
            try:
                redis_url = current_app.config.get('REDIS_URL', 'redis://localhost:6379/0')
                self.redis_client = redis.from_url(redis_url)
                # Test Redis connection
                self.redis_client.ping()
                logger.info("Redis connected successfully")
            except Exception as redis_error:
                logger.warning(f"Redis connection failed: {redis_error}. Using in-memory storage.")
                self.redis_client = None
            
            # Initialize Firebase using Application Default Credentials
            try:
                if not firebase_admin._apps:
                    # Use Application Default Credentials when running on Cloud Run
                    self.firebase_app = firebase_admin.initialize_app()
                    logger.info("Firebase initialized with Application Default Credentials")
                else:
                    self.firebase_app = firebase_admin.get_app()
                    logger.info("Firebase app already initialized")
            except Exception as firebase_error:
                logger.error(f"Firebase initialization failed: {firebase_error}")
                self.firebase_app = None
            
            logger.info("Auth services initialization completed")
            
        except Exception as e:
            logger.error(f"Failed to initialize auth services: {str(e)}")
    
    def authenticate_user(self, email, password):
        """Authenticate user with email and password."""
        try:
            # This is a placeholder implementation
            # In a real app, you would verify against a database
            
            # Hash the password for comparison
            password_hash = self._hash_password(password)
            
            # Mock user data - replace with database lookup
            if email == "test@example.com" and password == "password":
                user_data = {
                    'id': '12345',
                    'email': email,
                    'name': 'Test User',
                    'role': 'user'
                }
                
                # Generate JWT token
                token = self._generate_jwt_token(user_data)
                
                # Store session in Redis
                self._store_session(user_data['id'], token)
                
                return {
                    'success': True,
                    'token': token,
                    'user': user_data
                }
            else:
                return {
                    'success': False,
                    'message': 'Invalid email or password'
                }
                
        except Exception as e:
            logger.error(f"Error authenticating user: {str(e)}")
            return {
                'success': False,
                'message': str(e)
            }
    
    def register_user(self, email, password, name):
        """Register a new user."""
        try:
            # Check if user already exists (mock implementation)
            if email == "existing@example.com":
                return {
                    'success': False,
                    'message': 'User already exists'
                }
            
            # Create user data
            user_data = {
                'id': self._generate_user_id(),
                'email': email,
                'name': name,
                'role': 'user',
                'created_at': datetime.utcnow().isoformat()
            }
            
            # Hash password
            password_hash = self._hash_password(password)
            
            # In a real app, save user to database here
            
            # Generate JWT token
            token = self._generate_jwt_token(user_data)
            
            # Store session in Redis
            self._store_session(user_data['id'], token)
            
            logger.info(f"User registered successfully: {email}")
            
            return {
                'success': True,
                'token': token,
                'user': user_data
            }
            
        except Exception as e:
            logger.error(f"Error registering user: {str(e)}")
            return {
                'success': False,
                'message': str(e)
            }
    
    def verify_token(self, token):
        """Verify JWT token and return user data."""
        try:
            from flask import current_app
            
            # Decode JWT token
            payload = jwt.decode(
                token,
                current_app.config['SECRET_KEY'],
                algorithms=['HS256']
            )
            
            user_id = payload.get('user_id')
            
            # Check if session exists in Redis
            session_data = self.redis_client.get(f"session:{user_id}")
            if not session_data:
                return {
                    'valid': False,
                    'message': 'Session expired'
                }
            
            session_info = json.loads(session_data)
            
            return {
                'valid': True,
                'user': payload.get('user_data'),
                'session': session_info
            }
            
        except jwt.ExpiredSignatureError:
            return {
                'valid': False,
                'message': 'Token expired'
            }
        except jwt.InvalidTokenError:
            return {
                'valid': False,
                'message': 'Invalid token'
            }
        except Exception as e:
            logger.error(f"Error verifying token: {str(e)}")
            return {
                'valid': False,
                'message': str(e)
            }
    
    def logout_user(self, token):
        """Logout user by invalidating the session."""
        try:
            # Verify token to get user ID
            token_data = self.verify_token(token)
            
            if token_data['valid']:
                user_id = token_data['user']['id']
                
                # Remove session from Redis
                self.redis_client.delete(f"session:{user_id}")
                
                logger.info(f"User logged out successfully: {user_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error logging out user: {str(e)}")
            return False
    
    def _generate_jwt_token(self, user_data):
        """Generate JWT token for user."""
        try:
            from flask import current_app
            
            payload = {
                'user_id': user_data['id'],
                'user_data': user_data,
                'exp': datetime.utcnow() + timedelta(days=7),  # 7 days expiry
                'iat': datetime.utcnow()
            }
            
            token = jwt.encode(
                payload,
                current_app.config['SECRET_KEY'],
                algorithm='HS256'
            )
            
            return token
            
        except Exception as e:
            logger.error(f"Error generating JWT token: {str(e)}")
            raise
    
    def _hash_password(self, password):
        """Hash password using SHA-256."""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def _generate_user_id(self):
        """Generate a unique user ID."""
        import uuid
        return str(uuid.uuid4())
    
    def _store_session(self, user_id, token):
        """Store session data in Redis."""
        try:
            session_data = {
                'token': token,
                'created_at': datetime.utcnow().isoformat(),
                'last_activity': datetime.utcnow().isoformat()
            }
            
            # Store with 7 days expiry
            self.redis_client.setex(
                f"session:{user_id}",
                timedelta(days=7),
                json.dumps(session_data)
            )
            
        except Exception as e:
            logger.error(f"Error storing session: {str(e)}")
            # Continue without storing session if Redis fails
