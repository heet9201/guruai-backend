import logging
from flask import Flask
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from app.config import config
from app.utils.error_handlers import register_error_handlers
from app.utils.middleware import register_middleware

def create_app(config_name=None):
    """Application factory pattern for Flask app creation."""
    
    # Determine configuration
    if config_name is None:
        config_name = 'development'
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize CORS
    CORS(app, origins=app.config['CORS_ORIGINS'])
    
    # Initialize rate limiter
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["1000 per hour", "100 per minute"]
    )
    
    # Setup logging
    setup_logging(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Register middleware
    register_middleware(app)
    
    # Initialize WebSocket functionality
    socketio = initialize_websockets(app)
    
    # Register blueprints
    register_blueprints(app)
    
    return app, socketio

def setup_logging(app):
    """Setup application logging."""
    logging.basicConfig(
        level=getattr(logging, app.config['LOG_LEVEL']),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create logger for the app
    app.logger.setLevel(getattr(logging, app.config['LOG_LEVEL']))

def initialize_websockets(app):
    """Initialize WebSocket functionality."""
    try:
        from app.websocket_config import websocket_config
        
        # Initialize WebSocket configuration with the Flask app
        socketio = websocket_config.init_app(app)
        
        app.logger.info("WebSocket functionality initialized successfully")
        return socketio
        
    except Exception as e:
        app.logger.error(f"Failed to initialize WebSocket functionality: {str(e)}")
        # Return None if WebSocket initialization fails
        return None

def register_blueprints(app):
    """Register all blueprints."""
    from app.routes.health import health_bp
    from app.routes.ai import ai_bp
    from app.routes.speech import speech_bp
    from app.routes.auth import auth_bp
    from app.routes.user import user_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.weekly_planning import weekly_planning_bp
    from app.routes.content_generation import content_generation_bp
    from app.routes.websocket_api import websocket_api_bp
    from app.routes.file_management_simple import file_management_bp
    from app.routes.accessibility import accessibility_bp
    from app.routes.offline_sync import sync_bp
    from app.routes.localization import localization_bp
    from app.routes.performance import performance_bp
    from app.routes.intelligent_chat import intelligent_chat_bp
    
    app.register_blueprint(health_bp, url_prefix='/api/v1')
    app.register_blueprint(ai_bp, url_prefix='/api/v1')
    app.register_blueprint(speech_bp, url_prefix='/api/v1')
    app.register_blueprint(auth_bp, url_prefix='/api/v1/auth')
    app.register_blueprint(user_bp, url_prefix='/api/v1/user')
    app.register_blueprint(dashboard_bp, url_prefix='/api/v1/dashboard')
    app.register_blueprint(weekly_planning_bp)  # Already has /api/v1/weekly-planning prefix
    app.register_blueprint(content_generation_bp)  # Already has /api/content prefix
    app.register_blueprint(websocket_api_bp)
    app.register_blueprint(file_management_bp, url_prefix='/api/v1')
    app.register_blueprint(accessibility_bp, url_prefix='/api/v1/accessibility')
    app.register_blueprint(sync_bp, url_prefix='/api/v1/offline-sync')
    app.register_blueprint(localization_bp, url_prefix='/api/v1/localization')
    app.register_blueprint(performance_bp, url_prefix='/api/v1/performance')
    app.register_blueprint(intelligent_chat_bp)  # No prefix as routes already include full path
