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

```
guruai-backend/
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

- `POST /api/v1/chat` - AI chat conversation
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

### Using Gunicorn (Production)

```bash
gunicorn main:app --bind 0.0.0.0:8000 --workers 4
```

### Using Docker

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:5000"]
```

### Environment Variables

| Variable                         | Description                  | Default                    |
| -------------------------------- | ---------------------------- | -------------------------- |
| `FLASK_ENV`                      | Environment mode             | `development`              |
| `SECRET_KEY`                     | JWT secret key               | Required                   |
| `GOOGLE_CLOUD_PROJECT`           | Google Cloud project ID      | Required                   |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to service account JSON | Required                   |
| `REDIS_URL`                      | Redis connection URL         | `redis://localhost:6379/0` |
| `CORS_ORIGINS`                   | Allowed CORS origins         | `*`                        |
| `LOG_LEVEL`                      | Logging level                | `INFO`                     |

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
