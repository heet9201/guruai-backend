# Test configuration file
import os

# Test environment configuration
TEST_DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:test_password@localhost:5432/test_db')
TEST_REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
TEST_JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'test-secret-key')
TEST_ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', 'test-encryption-key')
TEST_PII_ENCRYPTION_KEY = os.getenv('PII_ENCRYPTION_KEY', 'test-pii-key')

# Test user credentials
TEST_USER_EMAIL = 'test@example.com'
TEST_USER_PASSWORD = 'testpassword123'
TEST_USER_USERNAME = 'testuser'

# API endpoints
API_BASE_URL = '/api/v1'
HEALTH_ENDPOINT = '/health'
AUTH_REGISTER_ENDPOINT = f'{API_BASE_URL}/auth/register'
AUTH_LOGIN_ENDPOINT = f'{API_BASE_URL}/auth/login'
AUTH_REFRESH_ENDPOINT = f'{API_BASE_URL}/auth/refresh'
AUTH_LOGOUT_ENDPOINT = f'{API_BASE_URL}/auth/logout'

CHAT_MESSAGE_ENDPOINT = f'{API_BASE_URL}/chat/message'
CHAT_HISTORY_ENDPOINT = f'{API_BASE_URL}/chat/history'

CONTENT_GENERATE_ENDPOINT = f'{API_BASE_URL}/content/generate'
CONTENT_TEMPLATES_ENDPOINT = f'{API_BASE_URL}/content/templates'

FILES_UPLOAD_ENDPOINT = f'{API_BASE_URL}/files/upload'
FILES_LIST_ENDPOINT = f'{API_BASE_URL}/files'

# Test timeouts
DEFAULT_TIMEOUT = 30
LONG_TIMEOUT = 60

# Mock data
MOCK_USER_DATA = {
    'email': TEST_USER_EMAIL,
    'password': TEST_USER_PASSWORD,
    'username': TEST_USER_USERNAME,
    'first_name': 'Test',
    'last_name': 'User'
}

MOCK_CHAT_MESSAGE = {
    'message': 'Hello, can you help me with my studies?',
    'context': 'general'
}

MOCK_CONTENT_REQUEST = {
    'type': 'essay',
    'topic': 'Artificial Intelligence',
    'length': 'medium',
    'style': 'academic'
}

# Test file data
TEST_FILE_CONTENT = b'This is test file content for upload testing.'
TEST_FILE_NAME = 'test_document.txt'
TEST_FILE_TYPE = 'text/plain'
