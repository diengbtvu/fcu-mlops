"""
Model Training Helper Functions
Contains training logic for paper models: RF, XGBoost, SVM, KNN, DT
"""

import pandas as pd
import os
import joblib
from sklearn.metrics import mean_absolute_error
import mlflow
import mlflow.sklearn
import mlflow.xgboost
import shutil

from steps.ingest_data import IngestData
from src.data_cleaning import DataCleaning, DataPreprocessStrategy, DataDivideStrategy
from src.model_dev import (
    RandomForestModel, SVMModel, KNNModel, DecisionTreeModel, XGBoostModel
)
from src.evaluation import R2Score, RMSE
from src.gra import run_gra
from app.utils.progress_tracker import TrainingProgressTracker

def train_random_forest(data, dataset_path, model_name, trained_by, dataset_id, session_id=None):
    """Train Random Forest model"""
    tracker = TrainingProgressTracker()
    
    # Initialize progress tracking
    if session_id:
        tracker.start_training(session_id)
        tracker.update_progress(session_id, progress=5, message="Initializing Random Forest training...")
    
    # Get parameters
    n_estimators = int(data.get('n_estimators', 100))
    max_depth_value = data.get('max_depth', None)
    max_depth = int(max_depth_value) if max_depth_value not in [None, ''] else None
    random_state = int(data.get('random_state', 42))
    
    print("🌲 Training Random Forest Model...")
    
    # Ingest and preprocess data
    if session_id:
        tracker.update_progress(session_id, progress=15, message="Loading and preprocessing dataset...")
    X_train, X_test, y_train, y_test, scaler = prepare_data(dataset_path, data, session_id)
    
    # Train model
    if session_id:
        tracker.update_progress(session_id, progress=50, message="Training Random Forest model...")
    model_instance = RandomForestModel()
    hyperparams = {
        'n_estimators': n_estimators,
        'max_depth': max_depth,
        'random_state': random_state,
        'n_jobs': -1
    }
    model = model_instance.train(X_train, y_train, **hyperparams)
    
    # Log parameters (don't log model_type again - already logged in main function)
    mlflow.log_param("n_estimators", n_estimators)
    mlflow.log_param("max_depth", max_depth if max_depth is not None else "None")
    
    # Evaluate
    if session_id:
        tracker.update_progress(session_id, progress=75, message="Evaluating model performance...")
    metrics = evaluate_model(model, X_test, y_test, "RandomForest")
    
    # Log model to MLflow
    if session_id:
        tracker.update_progress(session_id, progress=85, message="Logging model to MLflow...")
    mlflow.sklearn.log_model(model, "model", registered_model_name=f"RandomForest_{model_name}")
    
    # Save model
    if session_id:
        tracker.update_progress(session_id, progress=95, message="Saving model and scaler files...")
    save_paths = save_model_files(model, scaler, model_name, 'sklearn', '.pkl')
    
    return model, scaler, metrics, save_paths


def train_xgboost(data, dataset_path, model_name, trained_by, dataset_id, session_id=None):
    """Train XGBoost model"""
    tracker = TrainingProgressTracker()
    
    # Initialize progress tracking
    if session_id:
        tracker.start_training(session_id)
        tracker.update_progress(session_id, progress=5, message="Initializing XGBoost training...")
    
    # Get parameters
    n_estimators = int(data.get('n_estimators', 100))
    max_depth_value = data.get('max_depth', None)
    max_depth = int(max_depth_value) if max_depth_value not in [None, ''] else None
    learning_rate = float(data.get('learning_rate', 0.1))
    random_state = int(data.get('random_state', 42))
    
    print("🚀 Training XGBoost Model...")
    
    # Ingest and preprocess data
    if session_id:
        tracker.update_progress(session_id, progress=15, message="Loading and preprocessing dataset...")
    X_train, X_test, y_train, y_test, scaler = prepare_data(dataset_path, data, session_id)
    
    # Train model
    if session_id:
        tracker.update_progress(session_id, progress=45, message="Training XGBoost model...")
    model_instance = XGBoostModel()
    hyperparams = {
        'n_estimators': n_estimators,
        'learning_rate': learning_rate,
        'random_state': random_state,
    }
    # Match paper defaults: do not force max_depth unless explicitly provided.
    if max_depth is not None:
        hyperparams['max_depth'] = max_depth
    model = model_instance.train(X_train, y_train, **hyperparams)

    # Log parameters (don't log model_type again)
    mlflow.log_param("n_estimators", n_estimators)
    mlflow.log_param("max_depth", max_depth if max_depth is not None else "default")
    mlflow.log_param("learning_rate", learning_rate)
    
    # Evaluate
    if session_id:
        tracker.update_progress(session_id, progress=75, message="Evaluating model performance...")
    metrics = evaluate_model(model, X_test, y_test, "XGBoost")
    
    # Log model to MLflow with sklearn flavor (since we use XGBRegressor)
    if session_id:
        tracker.update_progress(session_id, progress=85, message="Logging model to MLflow...")
    mlflow.sklearn.log_model(model, "model", registered_model_name=f"XGBoost_{model_name}")
    
    # Save model
    if session_id:
        tracker.update_progress(session_id, progress=95, message="Saving model and scaler files...")
    save_paths = save_model_files(model, scaler, model_name, 'xgboost', '.json')
    
    return model, scaler, metrics, save_paths


def prepare_data(dataset_path, data, session_id=None, log_to_mlflow=True):
    """Prepare data for training using MinMaxScaler (Equation 1 of Wang et al. 2024)"""
    tracker = TrainingProgressTracker()
    test_size = float(data.get('test_size', 0.2))
    random_state = int(data.get('random_state', 42))

    # Step 1: Ingest
    if session_id:
        tracker.update_progress(session_id, progress=18, message="Loading dataset...")
    print(f"📂 Loading data from: {dataset_path}")
    ingest_data = IngestData(dataset_path)
    df = ingest_data.get_data()
    print(f"✅ Dataset loaded: {len(df)} rows, {len(df.columns)} columns")

    # Step 2a: Preprocess
    if session_id:
        tracker.update_progress(session_id, progress=25, message="Preprocessing data...")
    preprocess_strategy = DataPreprocessStrategy()
    data_cleaning = DataCleaning(df, preprocess_strategy)
    preprocessed_data = data_cleaning.handle_data()

    # Step 2b: Split + MinMax normalise (handled inside DataDivideStrategy)
    if session_id:
        tracker.update_progress(session_id, progress=32, message="Splitting and normalising data...")
    divide_strategy = DataDivideStrategy(test_size=test_size, random_state=random_state)
    data_cleaning2 = DataCleaning(preprocessed_data, divide_strategy)
    X_train, X_test, y_train, y_test = data_cleaning2.handle_data()

    # The scaler is already fitted inside DataDivideStrategy;
    # expose it for saving alongside the model.
    scaler = divide_strategy.scaler_X

    if log_to_mlflow:
        mlflow.log_param("train_samples", len(X_train))
        mlflow.log_param("test_samples", len(X_test))
        mlflow.log_param("n_features", X_train.shape[1])

    return X_train, X_test, y_train, y_test, scaler



def evaluate_model(model, X_test, y_test, model_type):
    """Evaluate model and log metrics"""
    print("📊 Evaluating model...")
    
    # Predict
    if hasattr(model, 'predict'):
        y_pred = model.predict(X_test)
        if len(y_pred.shape) > 1:
            y_pred = y_pred.flatten()
    else:
        raise ValueError("Model does not have predict method")
    
    # Calculate metrics
    r2_calc = R2Score()
    r2 = r2_calc.calculate_score(y_test, y_pred)
    
    rmse_calc = RMSE()
    rmse = rmse_calc.calculate_score(y_test, y_pred)
    
    mae = mean_absolute_error(y_test, y_pred)
    mse = rmse ** 2
    
    # Log to MLflow
    mlflow.log_metric("r2_score", r2)
    mlflow.log_metric("rmse", rmse)
    mlflow.log_metric("mae", mae)
    mlflow.log_metric("mse", mse)
    
    print(f"\n📈 {model_type} Performance:")
    print(f"   R² Score: {r2:.4f}")
    print(f"   RMSE: {rmse:.4f}")
    print(f"   MAE: {mae:.4f}")
    
    return {
        'r2_score': float(r2),
        'rmse': float(rmse),
        'mae': float(mae),
        'mse': float(mse)
    }


def run_gra_analysis(X_train: pd.DataFrame, y_train: pd.Series) -> dict:
    """
    Run Grey Relational Analysis on training data.
    Logs GRA ranking as MLflow params.

    Returns serialisable ranking dict.
    """
    feature_names = list(X_train.columns)
    result = run_gra(
        X_train.values,
        y_train.values,
        feature_names=feature_names,
    )
    # Log top features to MLflow
    for item in result["ranking"]:
        mlflow.log_param(
            f"gra_rank_{item['rank']}_{item['feature']}",
            round(item["score"], 4),
        )
    return result


# ---------------------------------------------------------------------------
# SVM
# ---------------------------------------------------------------------------
def train_svm(data, dataset_path, model_name, trained_by, dataset_id, session_id=None):
    """Train SVM (SVR) model."""
    tracker = TrainingProgressTracker()
    if session_id:
        tracker.start_training(session_id)
        tracker.update_progress(session_id, progress=5, message="Initialising SVM training...")

    C = float(data.get('C', 1.0))
    gamma = data.get('gamma', 'scale')
    kernel = data.get('kernel', 'rbf')

    print("🔷 Training SVM Model...")
    if session_id:
        tracker.update_progress(session_id, progress=15, message="Loading and preprocessing dataset...")
    X_train, X_test, y_train, y_test, scaler = prepare_data(dataset_path, data, session_id)

    if session_id:
        tracker.update_progress(session_id, progress=50, message="Training SVM model...")
    model = SVMModel().train(X_train, y_train, C=C, gamma=gamma, kernel=kernel)

    mlflow.log_param("C", C)
    mlflow.log_param("gamma", gamma)
    mlflow.log_param("kernel", kernel)

    if session_id:
        tracker.update_progress(session_id, progress=75, message="Evaluating...")
    metrics = evaluate_model(model, X_test, y_test, "SVM")

    if session_id:
        tracker.update_progress(session_id, progress=85, message="Logging to MLflow...")
    mlflow.sklearn.log_model(model, "model", registered_model_name=f"SVM_{model_name}")

    if session_id:
        tracker.update_progress(session_id, progress=95, message="Saving files...")
    save_paths = save_model_files(model, scaler, model_name, 'sklearn', '.pkl')
    return model, scaler, metrics, save_paths


# ---------------------------------------------------------------------------
# KNN
# ---------------------------------------------------------------------------
def train_knn(data, dataset_path, model_name, trained_by, dataset_id, session_id=None):
    """Train KNN regressor."""
    tracker = TrainingProgressTracker()
    if session_id:
        tracker.start_training(session_id)
        tracker.update_progress(session_id, progress=5, message="Initialising KNN training...")

    n_neighbors = int(data.get('n_neighbors', 5))

    print("🔶 Training KNN Model...")
    if session_id:
        tracker.update_progress(session_id, progress=15, message="Loading and preprocessing dataset...")
    X_train, X_test, y_train, y_test, scaler = prepare_data(dataset_path, data, session_id)

    if session_id:
        tracker.update_progress(session_id, progress=50, message="Training KNN model...")
    model = KNNModel().train(X_train, y_train, n_neighbors=n_neighbors)

    mlflow.log_param("n_neighbors", n_neighbors)

    if session_id:
        tracker.update_progress(session_id, progress=75, message="Evaluating...")
    metrics = evaluate_model(model, X_test, y_test, "KNN")

    if session_id:
        tracker.update_progress(session_id, progress=85, message="Logging to MLflow...")
    mlflow.sklearn.log_model(model, "model", registered_model_name=f"KNN_{model_name}")

    if session_id:
        tracker.update_progress(session_id, progress=95, message="Saving files...")
    save_paths = save_model_files(model, scaler, model_name, 'sklearn', '.pkl')
    return model, scaler, metrics, save_paths


# ---------------------------------------------------------------------------
# Decision Tree
# ---------------------------------------------------------------------------
def train_decision_tree(data, dataset_path, model_name, trained_by, dataset_id, session_id=None):
    """Train Decision Tree regressor."""
    tracker = TrainingProgressTracker()
    if session_id:
        tracker.start_training(session_id)
        tracker.update_progress(session_id, progress=5, message="Initialising Decision Tree training...")

    max_depth_val = data.get('max_depth', None)
    max_depth = int(max_depth_val) if max_depth_val not in [None, ''] else None
    random_state = int(data.get('random_state', 42))

    print("🌿 Training Decision Tree Model...")
    if session_id:
        tracker.update_progress(session_id, progress=15, message="Loading and preprocessing dataset...")
    X_train, X_test, y_train, y_test, scaler = prepare_data(dataset_path, data, session_id)

    if session_id:
        tracker.update_progress(session_id, progress=50, message="Training Decision Tree model...")
    model = DecisionTreeModel().train(X_train, y_train, max_depth=max_depth, random_state=random_state)

    mlflow.log_param("max_depth", max_depth)
    mlflow.log_param("random_state", random_state)

    if session_id:
        tracker.update_progress(session_id, progress=75, message="Evaluating...")
    metrics = evaluate_model(model, X_test, y_test, "DecisionTree")

    if session_id:
        tracker.update_progress(session_id, progress=85, message="Logging to MLflow...")
    mlflow.sklearn.log_model(model, "model", registered_model_name=f"DT_{model_name}")

    if session_id:
        tracker.update_progress(session_id, progress=95, message="Saving files...")
    save_paths = save_model_files(model, scaler, model_name, 'sklearn', '.pkl')
    return model, scaler, metrics, save_paths


def save_model_files(model, scaler, model_name, lib_type, extension):
    """Save model and scaler files"""
    # Determine directories
    current_file = os.path.abspath(__file__)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
    model_dir = os.path.join(project_root, 'app', 'ml_model')
    os.makedirs(model_dir, exist_ok=True)
    
    # Save model
    model_filename = f"{model_name}{extension}"
    model_path = os.path.join(model_dir, model_filename)
    
    if lib_type == 'keras':
        model.save(model_path)
    elif lib_type == 'xgboost':
        model.save_model(model_path)
    else:  # sklearn
        joblib.dump(model, model_path)
    
    print(f"💾 Model saved: {model_path}")
    
    # Save scaler
    scaler_filename = f"{model_name}_scaler.pkl"
    scaler_path = os.path.join(model_dir, scaler_filename)
    joblib.dump(scaler, scaler_path)
    print(f"💾 Scaler saved: {scaler_path}")
    
    # Save shared scaler in the main model directory.
    shared_scaler_path = os.path.join(model_dir, 'scaler.pkl')
    joblib.dump(scaler, shared_scaler_path)

    # Backward-compatible shared scaler path used by older envs (MODEL_DIR=ml_model).
    legacy_model_dir = os.path.join(project_root, 'ml_model')
    os.makedirs(legacy_model_dir, exist_ok=True)
    legacy_shared_scaler_path = os.path.join(legacy_model_dir, 'scaler.pkl')
    joblib.dump(scaler, legacy_shared_scaler_path)
    
    # Log scaler to MLflow
    mlflow.log_artifact(scaler_path, "scaler")
    
    # Copy to Laravel public directory
    try:
        laravel_public_models = os.path.join('/var/www/html', 'public', 'models')
        os.makedirs(laravel_public_models, exist_ok=True)
        
        laravel_model_path = os.path.join(laravel_public_models, model_filename)
        laravel_scaler_path = os.path.join(laravel_public_models, scaler_filename)
        
        if os.path.isdir(model_path):
            if os.path.exists(laravel_model_path):
                shutil.rmtree(laravel_model_path)
            shutil.copytree(model_path, laravel_model_path)
        else:
            shutil.copy2(model_path, laravel_model_path)
        
        shutil.copy2(scaler_path, laravel_scaler_path)
        print(f"📋 Files copied to Laravel: {laravel_public_models}")
        
    except Exception as e:
        print(f"⚠️ Warning: Could not copy to Laravel: {str(e)}")
    
    return {
        'model_path': model_path,
        'scaler_path': scaler_path,
        'model_filename': model_filename,
        'lib_type': lib_type
    }
