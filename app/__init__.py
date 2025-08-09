import logging
from flask import Flask
from flask_cors import CORS
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
    
    # Setup logging
    setup_logging(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Register middleware
    register_middleware(app)
    
    # Register blueprints
    register_blueprints(app)
    
    return app

def setup_logging(app):
    """Setup application logging."""
    logging.basicConfig(
        level=getattr(logging, app.config['LOG_LEVEL']),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create logger for the app
    app.logger.setLevel(getattr(logging, app.config['LOG_LEVEL']))

def register_blueprints(app):
    """Register all blueprints."""
    from app.routes.health import health_bp
    from app.routes.ai import ai_bp
    from app.routes.speech import speech_bp
    from app.routes.auth import auth_bp
    
    app.register_blueprint(health_bp, url_prefix='/api/v1')
    app.register_blueprint(ai_bp, url_prefix='/api/v1')
    app.register_blueprint(speech_bp, url_prefix='/api/v1')
    app.register_blueprint(auth_bp, url_prefix='/api/v1')
