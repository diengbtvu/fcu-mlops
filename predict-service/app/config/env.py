import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env file from project root
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

class Config_env:
    SECRET_KEY = os.environ.get("JWT_SECRET", "jwt_secret")
    MODEL_DIR = os.environ.get("MODEL_DIR", "ml_model")
    PORT = int(os.environ.get("PREDICT_PORT", 5000))
    LARAVEL_API_URL = os.environ.get("LARAVEL_API_URL", "http://127.0.0.1:8000/api")

config = Config_env()