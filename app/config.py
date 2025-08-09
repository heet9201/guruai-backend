import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration class."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database
    DATABASE_URL = os.environ.get('DATABASE_URL')
    
    # Google Cloud & Vertex AI
    GOOGLE_CLOUD_PROJECT = os.environ.get('GOOGLE_CLOUD_PROJECT')
    PROJECT_ID = os.environ.get('PROJECT_ID') or os.environ.get('GOOGLE_CLOUD_PROJECT')
    GOOGLE_APPLICATION_CREDENTIALS = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    LOCATION = os.environ.get('LOCATION') or 'asia-south1'  # India region
    
    # Vertex AI Models
    GEMINI_PRO_MODEL = os.environ.get('GEMINI_PRO_MODEL') or 'gemini-1.5-pro'
    GEMINI_PRO_VISION_MODEL = os.environ.get('GEMINI_PRO_VISION_MODEL') or 'gemini-1.5-pro-vision'
    
    # API Quotas and Rate Limiting
    TEXT_GENERATION_QUOTA = int(os.environ.get('TEXT_GENERATION_QUOTA', '1000'))  # requests per hour
    VISION_ANALYSIS_QUOTA = int(os.environ.get('VISION_ANALYSIS_QUOTA', '500'))   # requests per hour
    SPEECH_TO_TEXT_QUOTA = int(os.environ.get('SPEECH_TO_TEXT_QUOTA', '2000'))    # requests per hour
    
    # Connection Pool Settings
    MAX_POOL_SIZE = int(os.environ.get('MAX_POOL_SIZE', '10'))
    CONNECTION_TIMEOUT = int(os.environ.get('CONNECTION_TIMEOUT', '30'))
    READ_TIMEOUT = int(os.environ.get('READ_TIMEOUT', '60'))
    
    # Retry Settings
    MAX_RETRIES = int(os.environ.get('MAX_RETRIES', '3'))
    RETRY_DELAY = float(os.environ.get('RETRY_DELAY', '1.0'))
    RETRY_BACKOFF = float(os.environ.get('RETRY_BACKOFF', '2.0'))
    
    # Firebase
    FIREBASE_CREDENTIALS_PATH = os.environ.get('FIREBASE_CREDENTIALS_PATH')
    
    # Redis
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'
    
    # AI Platform (legacy support)
    AI_PLATFORM_LOCATION = os.environ.get('AI_PLATFORM_LOCATION') or 'asia-south1'
    
    # CORS
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL') or 'INFO'

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    ENV = 'development'

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    ENV = 'production'

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    ENV = 'testing'

# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
