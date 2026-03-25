"""
MLflow Model Cache Manager

Quản lý cache cho models từ MLflow để tối ưu performance
"""

import mlflow
import mlflow.sklearn
import mlflow.keras
import mlflow.xgboost
from datetime import datetime, timedelta
import os
import joblib
from typing import Tuple, Optional, Dict, Any, List
import logging
from app.utils.mlflow_tracking import configure_mlflow_tracking_uri

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MLflowModelCache:
    """
    Cache manager cho MLflow models
    
    Features:
    - In-memory cache với TTL (Time To Live)
    - Auto-load từ MLflow khi cache miss
    - Load cả model và scaler
    - Thread-safe (basic)
    """
    
    # Class-level cache storage
    _cache: Dict[str, Dict[str, Any]] = {}
    
    # Cache TTL (Time To Live) - mặc định 1 giờ
    _cache_ttl = timedelta(hours=1)
    
    @classmethod
    def set_cache_ttl(cls, hours: int = 1):
        """Set cache TTL in hours"""
        cls._cache_ttl = timedelta(hours=hours)
        logger.info(f"Cache TTL set to {hours} hour(s)")

    @classmethod
    def _detect_model_type(cls, run: Any) -> str:
        params = run.data.params or {}
        candidates = [
            params.get("model_type"),
            params.get("best_model_type"),
            params.get("winning_model"),
            params.get("requested_model_type"),
        ]
        for candidate in candidates:
            normalized = str(candidate or "").strip().lower()
            if normalized:
                return normalized
        return "random_forest"

    @classmethod
    def _resolve_model_artifact_path(cls, client: Any, run_id: str) -> str:
        preferred_paths = ["model", "best_model", "paper_training/model"]
        for artifact_path in preferred_paths:
            try:
                local_dir = client.download_artifacts(run_id, artifact_path)
            except Exception:
                continue
            if os.path.isfile(os.path.join(local_dir, "MLmodel")):
                return artifact_path

        root_entries = client.list_artifacts(run_id)
        candidate_paths: List[str] = [entry.path for entry in root_entries if getattr(entry, "is_dir", False)]

        for artifact_path in candidate_paths:
            try:
                local_dir = client.download_artifacts(run_id, artifact_path)
            except Exception:
                continue
            if os.path.isfile(os.path.join(local_dir, "MLmodel")):
                return artifact_path

        raise FileNotFoundError(
            "No MLflow model artifact was found in this run. "
            "Expected a logged model such as 'model/'. Re-train the model or fall back to file-based prediction."
        )

    @classmethod
    def _load_scaler_artifact(cls, client: Any, run_id: str) -> Any:
        scaler_candidates = [
            ("scaler", None),
            ("paper_training", {"best_scaler_X.pkl", "scaler.pkl"}),
            ("", {"best_scaler_X.pkl", "scaler.pkl"}),
        ]

        for artifact_path, allowed_files in scaler_candidates:
            try:
                download_path = client.download_artifacts(run_id, artifact_path) if artifact_path else client.download_artifacts(run_id, "")
            except Exception:
                continue

            if os.path.isfile(download_path) and download_path.endswith(".pkl"):
                return joblib.load(download_path)

            if not os.path.isdir(download_path):
                continue

            for filename in sorted(os.listdir(download_path)):
                if not filename.endswith(".pkl"):
                    continue
                if allowed_files is not None and filename not in allowed_files:
                    continue
                return joblib.load(os.path.join(download_path, filename))

        raise FileNotFoundError("No compatible scaler artifact was found in MLflow.")
    
    @classmethod
    def get_model(cls, run_id: str, force_reload: bool = False) -> Tuple[Any, Any]:
        """
        Load model và scaler từ cache hoặc MLflow
        
        Args:
            run_id: MLflow run ID
            force_reload: Force reload từ MLflow (bỏ qua cache)
            
        Returns:
            Tuple[model, scaler]
            
        Raises:
            Exception: Nếu không load được model
        """
        
        # Check cache validity
        if run_id in cls._cache and not force_reload:
            cache_entry = cls._cache[run_id]
            cache_age = datetime.now() - cache_entry["loaded_at"]
            
            if cache_age < cls._cache_ttl:
                logger.info(f"✅ Cache HIT for run_id: {run_id} (age: {cache_age.total_seconds():.0f}s)")
                return cache_entry["model"], cache_entry["scaler"]
            else:
                logger.info(f"⏰ Cache EXPIRED for run_id: {run_id} (age: {cache_age.total_seconds():.0f}s)")
        
        # Cache miss - load from MLflow
        logger.info(f"📥 Cache MISS - Loading from MLflow: {run_id}")
        
        try:
            tracking_info = configure_mlflow_tracking_uri()
            tracking_uri = tracking_info.get("tracking_uri", "unknown")
            logger.info("Using MLflow tracking URI: %s", tracking_uri)
            
            # Get run info to determine model flavor
            client = mlflow.tracking.MlflowClient()
            run = client.get_run(run_id)
            model_type = cls._detect_model_type(run)
            
            # Load model based on type
            model_artifact_path = cls._resolve_model_artifact_path(client, run_id)
            model_uri = f"runs:/{run_id}/{model_artifact_path}"
            logger.info(f"Loading model from: {model_uri} (type: {model_type})")
            
            if model_type == 'ann':
                # Load Keras model
                model = mlflow.keras.load_model(model_uri)
            elif model_type == 'xgboost':
                model = mlflow.xgboost.load_model(model_uri)
            else:
                # Default to sklearn
                model = mlflow.sklearn.load_model(model_uri)
            
            # Load scaler artifact
            logger.info(f"Loading scaler artifact for run: {run_id}")
            client = mlflow.tracking.MlflowClient()
            
            # Download scaler artifact
            try:
                scaler = cls._load_scaler_artifact(client, run_id)
            except Exception as e:
                logger.warning(f"Failed to load scaler from MLflow: {e}")
                logger.info("Falling back to shared scaler from ml_model/scaler.pkl")
                
                # Fallback: Load shared scaler
                from app.scalers.shared_scaler import get_scaler
                scaler = get_scaler()
                
                if scaler is None:
                    raise Exception("Failed to load both MLflow scaler and shared scaler")
            
            # Update cache
            cls._cache[run_id] = {
                "model": model,
                "scaler": scaler,
                "loaded_at": datetime.now(),
                "model_uri": model_uri
            }
            
            logger.info(f"✅ Model and scaler cached successfully for run_id: {run_id}")
            logger.info(f"📊 Total cached models: {len(cls._cache)}")
            
            return model, scaler
            
        except Exception as e:
            logger.error(f"❌ Failed to load model from MLflow: {str(e)}")
            raise Exception(f"Failed to load model from MLflow run {run_id}: {str(e)}")
    
    @classmethod
    def get_cached_run_ids(cls) -> list:
        """Get list của tất cả run_ids đang được cache"""
        return list(cls._cache.keys())
    
    @classmethod
    def get_cache_info(cls, run_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get thông tin về cache
        
        Args:
            run_id: Optional - thông tin cho run_id cụ thể
            
        Returns:
            Dict với cache info
        """
        if run_id and run_id in cls._cache:
            entry = cls._cache[run_id]
            age = datetime.now() - entry["loaded_at"]
            return {
                "run_id": run_id,
                "loaded_at": entry["loaded_at"].isoformat(),
                "age_seconds": age.total_seconds(),
                "expires_in_seconds": (cls._cache_ttl - age).total_seconds(),
                "model_uri": entry["model_uri"],
                "is_expired": age >= cls._cache_ttl
            }
        
        # Return all cache info
        return {
            "total_cached_models": len(cls._cache),
            "cache_ttl_hours": cls._cache_ttl.total_seconds() / 3600,
            "cached_run_ids": cls.get_cached_run_ids(),
            "cache_entries": [
                {
                    "run_id": rid,
                    "age_seconds": (datetime.now() - entry["loaded_at"]).total_seconds(),
                    "loaded_at": entry["loaded_at"].isoformat()
                }
                for rid, entry in cls._cache.items()
            ]
        }
    
    @classmethod
    def clear_cache(cls, run_id: Optional[str] = None):
        """
        Clear cache
        
        Args:
            run_id: Optional - clear specific run_id, None = clear all
        """
        if run_id:
            if run_id in cls._cache:
                del cls._cache[run_id]
                logger.info(f"🗑️ Cleared cache for run_id: {run_id}")
            else:
                logger.warning(f"Run_id {run_id} not in cache")
        else:
            count = len(cls._cache)
            cls._cache.clear()
            logger.info(f"🗑️ Cleared all cache ({count} entries)")
    
    @classmethod
    def preload_model(cls, run_id: str):
        """
        Preload model vào cache (warm up cache)
        
        Args:
            run_id: MLflow run ID
        """
        logger.info(f"🔥 Preloading model into cache: {run_id}")
        cls.get_model(run_id, force_reload=True)
    
    @classmethod
    def cleanup_expired_cache(cls):
        """Remove tất cả expired cache entries"""
        now = datetime.now()
        expired_runs = [
            run_id for run_id, entry in cls._cache.items()
            if now - entry["loaded_at"] >= cls._cache_ttl
        ]
        
        for run_id in expired_runs:
            del cls._cache[run_id]
            logger.info(f"🗑️ Removed expired cache: {run_id}")
        
        if expired_runs:
            logger.info(f"🗑️ Cleaned up {len(expired_runs)} expired cache entries")
        
        return len(expired_runs)
