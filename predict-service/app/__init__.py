from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file BEFORE importing other modules
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Debug: Print environment variables (optional, comment out in production)
import os
if os.getenv('DEBUG_ENV', 'false').lower() == 'true':
    print(f"✅ Environment loaded from: {env_path.absolute()}")
    print(f"   LARAVEL_API_URL: {os.getenv('LARAVEL_API_URL', 'NOT SET')}")
    print(f"   MODEL_DIR: {os.getenv('MODEL_DIR', 'NOT SET')}")
    print(f"   PREDICT_PORT: {os.getenv('PREDICT_PORT', 'NOT SET')}")

from .routes.predict import predict_bp
from .routes.train import train_bp
from .routes.augment import augment_bp
from .routes.progress import progress_bp

def create_app():
    app = Flask(__name__)
    CORS(app, origins=["*"])  # Use origins=["*"] for dev only, specify domain for production

    # Health check endpoint
    @app.route('/health', methods=['GET'])
    def health_check():
        return {
            'status': 'healthy',
            'service': 'Flask Prediction API',
            'version': '1.0.0'
        }, 200

    # Initialize Swagger UI
    try:
        from .config.swagger import init_swagger
        init_swagger(app)
    except ImportError as e:
        print(f"Warning: Could not load Swagger: {e}")

    # Import and register blueprints
    app.register_blueprint(predict_bp)
    app.register_blueprint(train_bp)
    app.register_blueprint(augment_bp)
    app.register_blueprint(progress_bp)

    return app