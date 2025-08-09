import os
from app import create_app

# Determine the configuration environment
config_name = os.environ.get('FLASK_ENV', 'development')

# Create the Flask application
app = create_app(config_name)

if __name__ == '__main__':
    # Get port from environment variable (useful for deployment)
    port = int(os.environ.get('PORT', 5000))
    
    # Get host from environment variable
    host = os.environ.get('HOST', '0.0.0.0')
    
    # Get debug mode from environment
    debug = os.environ.get('DEBUG', 'True').lower() == 'true'
    
    print(f"Starting Sahayak Backend on {host}:{port}")
    print(f"Environment: {config_name}")
    print(f"Debug mode: {debug}")
    
    app.run(
        host=host,
        port=port,
        debug=debug
    )
