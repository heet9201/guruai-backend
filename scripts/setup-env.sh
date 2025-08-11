# Create environment variables file
cat > .env.production << EOF
# Application Configuration
FLASK_ENV=production
DEBUG=False
TESTING=False

# Server Configuration
HOST=0.0.0.0
PORT=8080

# Database Configuration (will be overridden by Secret Manager)
DATABASE_URL=postgresql://user:password@localhost/guruai

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# JWT Configuration
JWT_SECRET_KEY=your-secret-key-here
JWT_ACCESS_TOKEN_EXPIRES=3600
JWT_REFRESH_TOKEN_EXPIRES=604800

# Encryption Configuration
ENCRYPTION_KEY=your-encryption-key-here
PII_ENCRYPTION_KEY=your-pii-encryption-key-here

# AI Service Configuration
OPENAI_API_KEY=your-openai-api-key-here
AI_MODEL=gpt-4
AI_MAX_TOKENS=2048
AI_TEMPERATURE=0.7

# File Upload Configuration
MAX_CONTENT_LENGTH=16777216  # 16MB
UPLOAD_FOLDER=/tmp/uploads
ALLOWED_EXTENSIONS=txt,pdf,doc,docx,png,jpg,jpeg,gif

# Security Configuration
BCRYPT_LOG_ROUNDS=12
SESSION_TIMEOUT=3600
MAX_LOGIN_ATTEMPTS=5
LOCKOUT_DURATION=900

# Rate Limiting Configuration
RATELIMIT_STORAGE_URL=redis://localhost:6379/1
RATELIMIT_DEFAULT=100 per hour

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json

# Monitoring Configuration
ENABLE_METRICS=true
METRICS_PORT=9090

# Cache Configuration
CACHE_TYPE=RedisCache
CACHE_DEFAULT_TIMEOUT=300

# Email Configuration (if using email notifications)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password

# Webhook Configuration
WEBHOOK_SECRET=your-webhook-secret
WEBHOOK_TIMEOUT=30

# Content Moderation
ENABLE_CONTENT_MODERATION=true
TOXICITY_THRESHOLD=0.7
PROFANITY_FILTER=true

# CORS Configuration
CORS_ORIGINS=https://your-frontend-domain.com,https://app.your-domain.com

# Health Check Configuration
HEALTH_CHECK_INTERVAL=30
HEALTH_CHECK_TIMEOUT=10

# Background Tasks
CELERY_BROKER_URL=redis://localhost:6379/2
CELERY_RESULT_BACKEND=redis://localhost:6379/3

# Feature Flags
ENABLE_OFFLINE_SYNC=true
ENABLE_ACCESSIBILITY_FEATURES=true
ENABLE_ANALYTICS=true
ENABLE_A_B_TESTING=false

# Performance Configuration
GUNICORN_WORKERS=4
GUNICORN_THREADS=2
GUNICORN_TIMEOUT=120
GUNICORN_KEEPALIVE=5

# Storage Configuration
STORAGE_TYPE=gcs  # local, s3, or gcs
GCS_BUCKET_NAME=guruai-storage
GCS_PROJECT_ID=your-project-id

# Search Configuration
SEARCH_INDEX_NAME=guruai-search
ELASTICSEARCH_URL=http://localhost:9200

# Analytics Configuration
ANALYTICS_PROVIDER=google
GOOGLE_ANALYTICS_ID=GA_MEASUREMENT_ID

# Compliance Configuration
GDPR_COMPLIANCE=true
DATA_RETENTION_DAYS=365
AUDIT_LOG_RETENTION_DAYS=2555  # 7 years

# Notification Configuration
ENABLE_PUSH_NOTIFICATIONS=true
FCM_SERVER_KEY=your-fcm-server-key

# API Configuration
API_VERSION=v1
API_RATE_LIMIT=1000 per hour
API_PAGINATION_SIZE=20
API_MAX_PAGE_SIZE=100

# Development/Testing (should be false in production)
ENABLE_DEBUG_TOOLBAR=false
ENABLE_PROFILER=false
SKIP_AUTH_FOR_TESTING=false
EOF

echo "✅ Production environment template created at .env.production"
echo "📝 Please update the values with your actual configuration"
