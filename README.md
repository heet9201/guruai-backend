# Sahayak Backend 🚀

A powerful Flask- **🤖 AI Chat**: Vertex AI integration with Gemini Pro for intelligent conversations

- **👁️ Vision Analysis**: Gemini Pro Vision for image understanding and analysis
- **🎤 Speech-to-Text**: Enhanced Google Cloud Speech API with quota management
- **🔊 Text-to-Speech**: Multi-language audio synthesis with Neural2 voices
- **📅 Weekly Planning**: Comprehensive lesson planning system with AI-powered activity suggestions
- **📚 Content Generation**: Universal AI-powered educational content creation system
  - Stories with moral lessons and interactive elements
  - Worksheets with progressive difficulty and solutions
  - Quizzes with multiple question types and explanations
  - Lesson plans with activities and assessments
  - Visual aids with SVG diagrams and color palettes
- **🔐 Authentication**: JWT-based authentication with Redis session managementnd for the Sahayak AI assistant application, providing speech-to-text, text-to-speech, AI chat, and authentication services.

## 🏗️ Architecture

This backend follows the **Application Factory Pattern** with a modular structure:

````
# 🧠 GuruAI Backend

A comprehensive AI-powered educational assistant backend built with Flask, designed for scalability, security, and modern DevOps practices.

## 🌟 Features

### Core Functionality
- **🤖 AI-Powered Chat**: Intelligent conversational AI using OpenAI GPT models
- **📄 Content Generation**: Automated content creation with customizable templates
- **📁 File Management**: Secure file upload, processing, and storage
- **♿ Accessibility**: WCAG-compliant features and screen reader support
- **📱 Offline Sync**: Progressive Web App capabilities with offline functionality
- **📊 Dashboard Analytics**: Real-time user behavior tracking and insights

### Security & Authentication
- **🔐 JWT Authentication**: Secure token-based authentication with refresh tokens
- **🛡️ Multi-Factor Authentication**: TOTP-based 2FA support
- **🔒 End-to-End Encryption**: Data encryption at rest and in transit
- **🚨 Content Moderation**: AI-powered content filtering and safety measures
- **📋 Audit Logging**: Comprehensive security event tracking
- **⚡ Rate Limiting**: API abuse prevention and DDoS protection

### DevOps & Infrastructure
- **☁️ Google Cloud Run**: Auto-scaling containerized deployment
- **🔄 CI/CD Pipeline**: Automated testing, security scanning, and deployment
- **📈 Monitoring**: Comprehensive metrics, logging, and alerting
- **🏗️ Infrastructure as Code**: Terraform-managed cloud resources
- **🐳 Containerization**: Multi-stage Docker builds optimized for production

## 🏗️ Architecture

### Technology Stack
- **Backend**: Flask 3.0+ with Python 3.11
- **Database**: PostgreSQL 15 with connection pooling
- **Cache**: Redis for session management and caching
- **AI Service**: OpenAI GPT-4 integration
- **Storage**: Google Cloud Storage for file handling
- **Monitoring**: Prometheus, Grafana, Google Cloud Monitoring

### Infrastructure
- **Deployment**: Google Cloud Run with auto-scaling (0-1000 instances)
- **Load Balancing**: Google Cloud Load Balancer with CDN
- **Security**: VPC networking, Secret Manager, SSL termination
- **Backup**: Automated database backups with point-in-time recovery

## 🚀 Quick Start

### Development Setup

1. **Clone and setup the development environment**:
   ```bash
   git clone <repository-url>
   cd guruai-backend
   ./scripts/dev-setup.sh
````

2. **Configure environment variables**:

   ```bash
   # Edit .env file with your configuration
   nano .env
   # Add your OpenAI API key and other settings
   ```

3. **Start the development server**:
   ```bash
   source venv/bin/activate
   python app.py
   ```

The application will be available at `http://localhost:5000`

### Production Deployment

1. **Set up Google Cloud infrastructure**:

   ```bash
   # Configure project and enable APIs
   ./scripts/setup-infrastructure.sh YOUR_PROJECT_ID us-central1
   ```

2. **Deploy with Terraform**:

   ```bash
   # Copy and configure terraform variables
   cp deployment/terraform.tfvars.example deployment/terraform.tfvars
   nano deployment/terraform.tfvars

   # Deploy infrastructure
   ./scripts/terraform-deploy.sh YOUR_PROJECT_ID production
   ```

3. **Deploy application**:

   ```bash
   # Deploy via CI/CD pipeline
   git push origin main

   # Or deploy manually
   ./scripts/deploy.sh
   ```

For detailed deployment instructions, see [DEPLOYMENT.md](DEPLOYMENT.md).

## 📚 API Documentation

### Authentication Endpoints

```
POST /api/v1/auth/register     - User registration
POST /api/v1/auth/login        - User login
POST /api/v1/auth/refresh      - Token refresh
POST /api/v1/auth/logout       - User logout
POST /api/v1/auth/mfa/setup    - Setup 2FA
POST /api/v1/auth/mfa/verify   - Verify 2FA token
```

### Chat & AI Endpoints

```
POST /api/v1/chat/intelligent  - Send intelligent chat message
POST /api/v1/chat/sessions     - Create/manage chat sessions
GET  /api/v1/chat/sessions     - Get user chat sessions
POST /api/v1/chat/suggestions  - Get personalized suggestions
POST /api/v1/content/generate  - Generate content
GET  /api/v1/content/templates - Get content templates
```

### File Management

```
POST /api/v1/files/upload      - Upload file
GET  /api/v1/files/{id}        - Download file
DELETE /api/v1/files/{id}      - Delete file
GET  /api/v1/files/            - List files
```

### Health & Monitoring

```
GET  /health                   - Application health
GET  /health/ready             - Readiness probe
GET  /health/live              - Liveness probe
GET  /metrics                  - Prometheus metrics
```

## 🔧 Configuration

### Environment Variables

| Variable         | Description                  | Default      |
| ---------------- | ---------------------------- | ------------ |
| `FLASK_ENV`      | Environment mode             | `production` |
| `DATABASE_URL`   | PostgreSQL connection string | Required     |
| `REDIS_URL`      | Redis connection string      | Required     |
| `JWT_SECRET_KEY` | JWT signing key              | Required     |
| `OPENAI_API_KEY` | OpenAI API key               | Required     |
| `ENCRYPTION_KEY` | Data encryption key          | Required     |

See [scripts/setup-env.sh](scripts/setup-env.sh) for a complete list.

### Security Configuration

- **JWT Tokens**: 1-hour access tokens, 7-day refresh tokens
- **Rate Limiting**: 100 requests per hour per user
- **File Upload**: 16MB max size, restricted file types
- **Content Moderation**: Automatic toxicity detection
- **Encryption**: AES-256 encryption for sensitive data

## 📊 Monitoring & Observability

### Metrics Tracked

- **Performance**: Response times, throughput, error rates
- **Business**: User engagement, AI usage, content generation
- **Infrastructure**: CPU, memory, disk, network usage
- **Security**: Authentication attempts, rate limit violations

### Alerting

- High error rates (>1%)
- Slow response times (>2s for chat, >30s for content)
- Resource utilization (>80% memory/CPU)
- Service downtime or health check failures

### Dashboards

- **Application Dashboard**: Request metrics, user activity
- **Infrastructure Dashboard**: Resource usage, scaling metrics
- **Security Dashboard**: Authentication events, security incidents

## 🧪 Testing

### Run Tests

```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=app tests/

# Run specific test categories
python -m pytest tests/unit/
python -m pytest tests/integration/
python -m pytest tests/api/
```

### Test Categories

- **Unit Tests**: Individual component testing
- **Integration Tests**: Database and service integration
- **API Tests**: Endpoint functionality and security
- **Load Tests**: Performance and scalability validation

## 🔒 Security

### Security Features

- **Authentication**: JWT with refresh token rotation
- **Authorization**: Role-based access control (RBAC)
- **Data Protection**: Encryption at rest and in transit
- **Input Validation**: Comprehensive request validation
- **Security Headers**: CSRF, XSS, and clickjacking protection
- **Audit Logging**: Complete security event tracking

### Security Scanning

- **SAST**: Static code analysis with Bandit
- **Dependency Scanning**: Vulnerability detection with Safety
- **Secret Scanning**: Credential leak detection
- **Container Scanning**: Docker image vulnerability assessment

## 🤝 Contributing

### Development Workflow

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and add tests
4. Run tests and security checks: `python -m pytest && bandit -r app/`
5. Commit your changes: `git commit -m 'Add amazing feature'`
6. Push to the branch: `git push origin feature/amazing-feature`
7. Open a Pull Request

### Code Standards

- **Style**: Follow PEP 8 with Black formatting
- **Testing**: Maintain >90% test coverage
- **Documentation**: Document all public functions and classes
- **Security**: Follow OWASP security guidelines

## 📈 Performance & Scalability

### Performance Targets

- **Response Time**: <2s for chat, <30s for content generation
- **Throughput**: 10,000+ concurrent users
- **Availability**: 99.9% uptime SLA
- **Scalability**: Auto-scaling from 0 to 1000 instances

### Optimization Features

- **Caching**: Redis-based response caching
- **CDN**: Global content delivery network
- **Database**: Connection pooling and query optimization
- **Load Balancing**: Geographic traffic distribution

## 📋 Roadmap

### Current Version (v1.0)

- ✅ Core AI chat functionality
- ✅ Authentication and security
- ✅ File management system
- ✅ Production deployment infrastructure

### Upcoming Features (v1.1)

- 🔄 Advanced content templates
- 🔄 Real-time collaboration features
- 🔄 Enhanced analytics dashboard
- 🔄 Mobile app API support

### Future Enhancements (v2.0)

- 📅 Multi-language support
- 📅 Advanced AI model integration
- 📅 Blockchain-based authentication
- 📅 Edge computing deployment

## 📞 Support

### Documentation

- [Deployment Guide](DEPLOYMENT.md)
- [API Documentation](docs/api.md)
- [Security Guide](docs/security.md)
- [Development Setup](docs/development.md)

### Getting Help

- **Issues**: Create a GitHub issue for bugs or feature requests
- **Discussions**: Use GitHub Discussions for general questions
- **Security**: Report security issues to security@example.com
- **Commercial Support**: Contact support@example.com

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🏆 Acknowledgments

- **OpenAI**: For providing the GPT models that power our AI features
- **Google Cloud**: For the robust infrastructure platform
- **Flask Community**: For the excellent web framework and ecosystem
- **Contributors**: All the developers who have contributed to this project

---

<div align="center">
<strong>Built with ❤️ for the future of AI-powered education</strong>
</div>
├── app/
│   ├── __init__.py          # Application factory
│   ├── config.py            # Environment-based configuration
│   ├── models/              # Data models
│   │   └── __init__.py
│   ├── routes/              # API endpoints
│   │   ├── health.py        # Health check endpoints
│   │   ├── ai.py           # AI chat endpoints
│   │   ├── speech.py       # Speech processing endpoints
│   │   └── auth.py         # Authentication endpoints
│   ├── services/            # Business logic
│   │   ├── ai_service.py    # Google AI Platform integration
│   │   ├── speech_service.py # Google Speech API integration
│   │   └── auth_service.py  # Authentication & JWT handling
│   └── utils/               # Utilities and middleware
│       ├── __init__.py      # Common utilities
│       ├── error_handlers.py # Global error handling
│       └── middleware.py    # Request/response middleware
├── tests/                   # Test suite
├── requirements.txt         # Python dependencies
├── main.py                 # Application entry point
├── Procfile                # Deployment configuration
├── run.sh                  # Development run script
└── .env.example            # Environment variables template
```

## 🔧 Features

- **🤖 AI Chat**: Vertex AI integration with Gemini Pro for intelligent conversations
- **👁️ Vision Analysis**: Gemini Pro Vision for image understanding and analysis
- **🎤 Speech-to-Text**: Enhanced Google Cloud Speech API with quota management
- **🔊 Text-to-Speech**: Multi-language audio synthesis with Neural2 voices
- **� Weekly Planning**: Comprehensive lesson planning system with AI-powered activity suggestions
- **�🔐 Authentication**: JWT-based authentication with Redis session management
- **📊 Health Monitoring**: Comprehensive health checks and quota monitoring
- **🌐 CORS Support**: Configured for Flutter mobile app integration
- **📝 Request Logging**: Detailed request/response logging with execution times
- **⚡ Error Handling**: Centralized error handling with proper HTTP status codes
- **🔄 Retry Logic**: Intelligent retry mechanism with exponential backoff
- **📈 Quota Management**: Real-time API quota tracking and rate limiting
- **🔗 Connection Pooling**: Optimized connection management for better performance
- **🇮🇳 India Region**: Optimized for Asia-South1 region for better latency

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Google Cloud Account with billing enabled
- Redis server (local or cloud)
- Google Cloud CLI (`gcloud`) installed

### Automated Setup

1. **Clone and setup:**

   ```bash
   git clone <repository-url>
   cd guruai-backend

   # Run automated Vertex AI setup
   ./setup_vertex_ai.sh
   ```

2. **Start the application:**
   ```bash
   ./run.sh
   ```

### Manual Setup

1. **Clone the repository:**

   ```bash
   git clone <repository-url>
   cd guruai-backend
   ```

2. **Run the setup script:**

   ```bash
   ./run.sh
   ```

   Or manually:

   ```bash
   # Create virtual environment
   python3 -m venv venv
   source venv/bin/activate

   # Install dependencies
   pip install -r requirements.txt

   # Copy environment file
   cp .env.example .env
   ```

3. **Configure environment variables:**
   Edit `.env` file with your actual configuration:

   ```bash
   GOOGLE_CLOUD_PROJECT=your-project-id
   GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json
   FIREBASE_CREDENTIALS_PATH=path/to/firebase-credentials.json
   REDIS_URL=redis://localhost:6379/0
   SECRET_KEY=your-super-secret-key
   ```

4. **Start the application:**
   ```bash
   python main.py
   ```

The API will be available at `http://localhost:5000`

## 📡 API Endpoints

### Health Endpoints

- `GET /api/v1/health` - Basic health check
- `GET /api/v1/ready` - Readiness check with dependency status

### Authentication

- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/logout` - User logout

### AI Services

- `POST /api/v1/chat/intelligent` - Intelligent AI chat with context-awareness
- `POST /api/v1/ai/sentiment-analysis` - Sentiment analysis
- `POST /api/v1/ai/topic-extraction` - Topic extraction from conversations
- `POST /api/v1/analyze-image` - Image analysis
- `POST /api/v1/generate-summary` - Text summarization

### Speech Services

- `POST /api/v1/speech-to-text` - Convert speech to text
- `POST /api/v1/text-to-speech` - Convert text to speech
- `POST /api/v1/upload-audio` - Upload and process audio files

### Content Generation

- `POST /api/content/generate` - Universal content generation (stories, worksheets, quizzes, lesson plans, visual aids)
- `GET /api/content/history` - Get content generation history with filtering
- `GET /api/content/{id}` - Get detailed content information
- `POST /api/content/{id}/export` - Export content to PDF/DOCX/HTML/JSON
- `POST /api/content/{id}/variants` - Generate content variants (difficulty, length, style, language)
- `GET /api/content/templates` - Get available content templates
- `POST /api/content/suggestions` - Get AI-powered content suggestions
- `GET /api/content/statistics` - Get content generation statistics

### Weekly Planning

- `POST /api/weekly-planning/plans` - Create comprehensive weekly lesson plans
- `GET /api/weekly-planning/plans` - Get weekly plans with filtering
- `GET /api/weekly-planning/plans/{id}` - Get specific plan details
- `PUT /api/weekly-planning/plans/{id}` - Update weekly plan
- `DELETE /api/weekly-planning/plans/{id}` - Delete weekly plan
- `POST /api/weekly-planning/plans/{id}/activities` - Add activities to plan
- `GET /api/weekly-planning/templates` - Get activity templates
- `POST /api/weekly-planning/suggestions` - Get AI-powered activity suggestions

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_api.py

# Run with coverage
python -m pytest tests/ --cov=app
```

## 🚀 Deployment

This project uses a modern CI/CD pipeline with automated testing, security scanning, and blue-green deployment strategies.

### Production Architecture

The application is deployed on Google Cloud Platform with the following components:

- **Google Cloud Run**: Auto-scaling containerized deployment
- **Google Cloud Memorystore (Redis)**: High-performance caching and session storage
- **VPC Connector**: Secure private network connectivity
- **Artifact Registry**: Docker image storage
- **Cloud Build**: Automated CI/CD pipeline

### Quick Deployment

For detailed deployment instructions, see [DEPLOYMENT.md](DEPLOYMENT.md).

```bash
# 1. Set up Google Cloud Project
gcloud projects create your-project-id
gcloud config set project your-project-id

# 2. Run automated setup
./scripts/setup-infrastructure.sh your-project-id us-central1

# 3. Configure GitHub Secrets
# See DEPLOYMENT.md for complete secret setup

# 4. Deploy via GitHub Actions
git push origin main  # Automatically triggers deployment
```

### Environment Variables

| Variable                         | Description                  | Default       | Required |
| -------------------------------- | ---------------------------- | ------------- | -------- |
| `ENVIRONMENT`                    | Deployment environment       | `development` | Yes      |
| `REDIS_HOST`                     | Redis server hostname        | `localhost`   | Yes      |
| `REDIS_PORT`                     | Redis server port            | `6379`        | Yes      |
| `SECRET_KEY`                     | JWT secret key               | Required      | Yes      |
| `GOOGLE_CLOUD_PROJECT`           | Google Cloud project ID      | Required      | Yes      |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to service account JSON | Required      | Yes      |
| `CORS_ORIGINS`                   | Allowed CORS origins         | `*`           | No       |
| `LOG_LEVEL`                      | Logging level                | `INFO`        | No       |

### Deployment Strategies

#### Gradual Rollout (Default)

The CI/CD pipeline uses a blue-green deployment strategy with gradual traffic shifting:

- **10%** traffic to new version (5 minutes)
- **50%** traffic to new version (5 minutes)
- **100%** traffic to new version

#### Fast Deployment

For urgent fixes, skip gradual rollout by including `[skip-gradual]` in your commit message:

```bash
git commit -m "hotfix: Critical security patch [skip-gradual]"
git push origin main
```

### Health Monitoring

The application provides comprehensive health checking:

- **`/api/v1/health`** - Complete system health with Redis, memory, disk status
- **Readiness checks** - Validates all dependencies before traffic routing
- **Auto-rollback** - Automatic rollback on failed health checks

Sample health response:

```json
{
  "status": "healthy",
  "checks": {
    "redis": {
      "status": "healthy",
      "details": {
        "connected_clients": 6,
        "redis_version": "7.0.15",
        "used_memory_human": "3.88M"
      }
    },
    "memory": { "status": "healthy" },
    "disk": { "status": "healthy" }
  },
  "environment": "production",
  "uptime_seconds": 3600
}
```

## 📊 Monitoring

The application includes comprehensive logging and monitoring:

- **Request Logging**: All API requests are logged with execution time
- **Error Tracking**: Errors are logged with stack traces
- **Health Checks**: Use `/api/v1/health` for basic monitoring
- **Readiness Checks**: Use `/api/v1/ready` for dependency monitoring

## 🔧 Development

### Adding New Endpoints

1. Create a new blueprint in `app/routes/`
2. Register the blueprint in `app/__init__.py`
3. Add corresponding service logic in `app/services/`
4. Write tests in `tests/`

### Environment-Specific Configuration

The application supports multiple environments:

- `development` - Local development with debug mode
- `production` - Production deployment
- `testing` - Test environment with mocked services

## 📚 Documentation

Detailed documentation for specific features:

- **[Content Generation System](docs/CONTENT_GENERATION.md)** - AI-powered educational content creation with stories, worksheets, quizzes, lesson plans, and visual aids
- **[Weekly Planning System](docs/WEEKLY_PLANNING.md)** - Comprehensive lesson planning with AI suggestions, templates, and scheduling tools
- **[API Reference](postman_collection.json)** - Complete Postman collection with all endpoints
- **[Authentication System](docs/AUTHENTICATION.md)** - JWT-based authentication with device tracking (if applicable)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For support and questions:

- Create an issue on GitHub
- Check the documentation
- Review the test files for usage examples

---

**Built with ❤️ for the Sahayak AI Assistant**
