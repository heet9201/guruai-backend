#!/bin/bash

# Local development setup script
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

function print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

function print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

function print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

function print_error() {
    echo -e "${RED}❌ $1${NC}"
}

function check_prerequisites() {
    print_header "Checking Prerequisites"
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed"
        exit 1
    fi
    print_success "Python 3 is installed"
    
    # Check pip
    if ! command -v pip3 &> /dev/null; then
        print_error "pip3 is not installed"
        exit 1
    fi
    print_success "pip3 is installed"
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        exit 1
    fi
    print_success "Docker is installed"
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed"
        exit 1
    fi
    print_success "Docker Compose is installed"
}

function setup_python_environment() {
    print_header "Setting up Python Environment"
    
    # Create virtual environment
    if [ ! -d "venv" ]; then
        print_warning "Creating virtual environment..."
        python3 -m venv venv
        print_success "Virtual environment created"
    else
        print_success "Virtual environment already exists"
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    print_success "Virtual environment activated"
    
    # Upgrade pip
    pip install --upgrade pip
    print_success "pip upgraded"
    
    # Install requirements
    if [ -f "requirements.txt" ]; then
        print_warning "Installing Python dependencies..."
        pip install -r requirements.txt
        print_success "Python dependencies installed"
    else
        print_warning "requirements.txt not found, skipping dependency installation"
    fi
    
    # Install development requirements
    if [ -f "requirements-dev.txt" ]; then
        print_warning "Installing development dependencies..."
        pip install -r requirements-dev.txt
        print_success "Development dependencies installed"
    fi
}

function setup_environment_file() {
    print_header "Setting up Environment File"
    
    if [ ! -f ".env" ]; then
        print_warning "Creating .env file from template..."
        cat > .env << EOF
# Development Environment Configuration
FLASK_ENV=development
DEBUG=True
TESTING=False

# Server Configuration
HOST=127.0.0.1
PORT=5000

# Database Configuration
DATABASE_URL=postgresql://guruai:password@localhost:5432/guruai_dev

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# JWT Configuration
JWT_SECRET_KEY=dev-secret-key-change-in-production
JWT_ACCESS_TOKEN_EXPIRES=3600
JWT_REFRESH_TOKEN_EXPIRES=604800

# Encryption Configuration
ENCRYPTION_KEY=dev-encryption-key-32-bytes-long
PII_ENCRYPTION_KEY=dev-pii-key-32-bytes-long-too

# AI Service Configuration (add your API key)
OPENAI_API_KEY=your-openai-api-key-here
AI_MODEL=gpt-3.5-turbo
AI_MAX_TOKENS=2048
AI_TEMPERATURE=0.7

# File Upload Configuration
MAX_CONTENT_LENGTH=16777216
UPLOAD_FOLDER=uploads
ALLOWED_EXTENSIONS=txt,pdf,doc,docx,png,jpg,jpeg,gif

# Security Configuration
BCRYPT_LOG_ROUNDS=4
SESSION_TIMEOUT=3600
MAX_LOGIN_ATTEMPTS=5
LOCKOUT_DURATION=900

# Rate Limiting Configuration
RATELIMIT_STORAGE_URL=redis://localhost:6379/1
RATELIMIT_DEFAULT=1000 per hour

# Logging Configuration
LOG_LEVEL=DEBUG
LOG_FORMAT=text

# Monitoring Configuration
ENABLE_METRICS=true
METRICS_PORT=9090

# Cache Configuration
CACHE_TYPE=RedisCache
CACHE_DEFAULT_TIMEOUT=300

# CORS Configuration
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Development Features
ENABLE_DEBUG_TOOLBAR=true
ENABLE_PROFILER=false
SKIP_AUTH_FOR_TESTING=false

# Background Tasks
CELERY_BROKER_URL=redis://localhost:6379/2
CELERY_RESULT_BACKEND=redis://localhost:6379/3

# Feature Flags
ENABLE_OFFLINE_SYNC=true
ENABLE_ACCESSIBILITY_FEATURES=true
ENABLE_ANALYTICS=false
ENABLE_A_B_TESTING=false
EOF
        print_success ".env file created"
        print_warning "Please update the OPENAI_API_KEY in .env file"
    else
        print_success ".env file already exists"
    fi
}

function start_services() {
    print_header "Starting Development Services"
    
    # Start Docker services
    print_warning "Starting PostgreSQL and Redis with Docker Compose..."
    docker-compose up -d postgres redis
    
    # Wait for services to be ready
    print_warning "Waiting for services to be ready..."
    sleep 10
    
    # Check if PostgreSQL is ready
    max_attempts=30
    attempt=0
    while [ $attempt -lt $max_attempts ]; do
        if docker-compose exec -T postgres pg_isready -U guruai -d guruai_dev > /dev/null 2>&1; then
            print_success "PostgreSQL is ready"
            break
        fi
        attempt=$((attempt + 1))
        sleep 2
    done
    
    if [ $attempt -eq $max_attempts ]; then
        print_error "PostgreSQL failed to start within timeout"
        exit 1
    fi
    
    # Check if Redis is ready
    if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
        print_success "Redis is ready"
    else
        print_error "Redis is not responding"
        exit 1
    fi
}

function setup_database() {
    print_header "Setting up Database"
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Run database migrations
    print_warning "Running database migrations..."
    if [ -f "migrate.py" ]; then
        python migrate.py
        print_success "Database migrations completed"
    elif [ -f "app/__init__.py" ]; then
        # Try Flask-Migrate
        export FLASK_APP=app
        if command -v flask &> /dev/null; then
            flask db upgrade 2>/dev/null || print_warning "No migrations found or migration failed"
        fi
    else
        print_warning "No migration script found, skipping database setup"
    fi
}

function run_tests() {
    print_header "Running Tests"
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Run tests
    if [ -f "pytest.ini" ] || [ -d "tests" ]; then
        print_warning "Running pytest..."
        python -m pytest tests/ -v --tb=short
        print_success "Tests completed"
    elif [ -f "test.py" ]; then
        print_warning "Running test.py..."
        python test.py
        print_success "Tests completed"
    else
        print_warning "No tests found, skipping test execution"
    fi
}

function start_application() {
    print_header "Starting Application"
    
    # Activate virtual environment
    source venv/bin/activate
    
    print_success "Development environment is ready!"
    echo ""
    echo -e "${BLUE}To start the application:${NC}"
    echo "1. Activate virtual environment: source venv/bin/activate"
    echo "2. Start the Flask app: python app.py"
    echo ""
    echo -e "${BLUE}Services running:${NC}"
    echo "• PostgreSQL: localhost:5432"
    echo "• Redis: localhost:6379"
    echo "• Application will run on: http://localhost:5000"
    echo ""
    echo -e "${BLUE}Useful commands:${NC}"
    echo "• View logs: docker-compose logs"
    echo "• Stop services: docker-compose down"
    echo "• Run tests: python -m pytest"
    echo "• Database shell: docker-compose exec postgres psql -U guruai -d guruai_dev"
    echo "• Redis CLI: docker-compose exec redis redis-cli"
}

function cleanup_on_exit() {
    if [ "$1" = "SIGINT" ]; then
        print_warning "Shutting down services..."
        docker-compose down
        exit 0
    fi
}

# Help function
show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --skip-tests    Skip running tests"
    echo "  --no-services   Don't start Docker services"
    echo "  -h, --help      Show this help message"
    echo ""
    echo "This script will:"
    echo "1. Check prerequisites (Python, Docker, etc.)"
    echo "2. Set up Python virtual environment"
    echo "3. Install dependencies"
    echo "4. Create .env file if it doesn't exist"
    echo "5. Start PostgreSQL and Redis services"
    echo "6. Set up database"
    echo "7. Run tests (optional)"
    echo "8. Provide instructions to start the application"
}

# Parse command line arguments
SKIP_TESTS=false
NO_SERVICES=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        --no-services)
            NO_SERVICES=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Main execution
main() {
    trap 'cleanup_on_exit SIGINT' SIGINT
    
    print_header "GuruAI Backend Development Setup"
    
    check_prerequisites
    setup_python_environment
    setup_environment_file
    
    if [ "$NO_SERVICES" = false ]; then
        start_services
        setup_database
    fi
    
    if [ "$SKIP_TESTS" = false ]; then
        run_tests
    fi
    
    start_application
}

# Run main function
main
