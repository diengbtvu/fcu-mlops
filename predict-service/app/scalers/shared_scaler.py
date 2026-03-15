import os
import joblib
from app.config.env import Config_env

# Scaler file path (keeping original filename for compatibility)
SCALER_PATH = os.path.join(Config_env.MODEL_DIR, 'scaler.pkl')

_shared_scaler = None

def get_scaler():
    """
    Get the shared scaler used for all model predictions.
    This scaler is trained on the standard input features and used consistently
    across all model types (Keras, PyTorch, sklearn, XGBoost, etc.)
    """
    global _shared_scaler
    if _shared_scaler is None:
        with open(SCALER_PATH, 'rb') as f:
            _shared_scaler = joblib.load(f)
    return _shared_scaler