from flask import Blueprint, request, jsonify
from app.middlewares.auth import token_required
import pandas as pd
import os

from app.models.dynamic_loader import ModelLoader, ModelPredictor
from app.scalers.shared_scaler import get_scaler
from app.utils.mlflow_cache import MLflowModelCache
from app.utils.mlflow_tracking import configure_mlflow_tracking_uri
from app.utils.database_utils import DatabaseUtils
from steps.config import HydrogenExperimentConfig
import traceback

predict_bp = Blueprint('predict', __name__, url_prefix='/predict')

EXPERIMENT_CONFIG = HydrogenExperimentConfig()
FEATURE_FIELD_MAP = {
    'ph': 'pH',
    'vss': 'VSS',
    'ethanol': 'Ethanol',
    'acetate': 'Acetate',
    'propionate': 'Propionate',
    'butyrate': 'Butyrate',
    'sucrose_degradation': 'Sucrose_Degradation',
    'orp_mid': 'ORP_Mid',
    'orp_low': 'ORP_Low',
    'vfa': 'VFA',
    'cod_o': 'COD-O',
}
FEATURE_DESCRIPTIONS = {
    'ph': 'System pH',
    'vss': 'Volatile Suspended Solids (mg/L)',
    'ethanol': 'Ethanol concentration (mM)',
    'acetate': 'Acetate concentration (mM)',
    'propionate': 'Propionate concentration (mM)',
    'butyrate': 'Butyrate concentration (mM)',
    'sucrose_degradation': 'Sucrose degradation (%)',
    'orp_mid': 'ORP Mid (mV)',
    'orp_low': 'ORP Low (mV)',
    'vfa': 'VFA concentration (mM)',
    'cod_o': 'COD-O (mg/L)',
}
FEATURE_EXAMPLES = {
    'ph': 5.8,
    'vss': 2.36,
    'ethanol': 1739.25,
    'acetate': 925.5,
    'propionate': 1100.0,
    'butyrate': 10.6,
    'sucrose_degradation': 91.68,
    'orp_mid': -226.67,
    'orp_low': -481.0,
    'vfa': 3723.5,
    'cod_o': 11.52,
}
SUPPORTED_MODEL_TYPES = ['keras', 'pytorch', 'sklearn', 'xgboost', 'pickle', 'joblib']
SWAGGER_FEATURE_PROPERTIES = {
    request_key: {
        'type': 'number',
        'minimum': EXPERIMENT_CONFIG.feature_ranges[feature_name]['min'],
        'maximum': EXPERIMENT_CONFIG.feature_ranges[feature_name]['max'],
        'description': FEATURE_DESCRIPTIONS[request_key],
        'example': FEATURE_EXAMPLES[request_key],
    }
    for request_key, feature_name in FEATURE_FIELD_MAP.items()
}

# Try to import swagger decorator, but continue without it if not available
try:
    from flasgger import swag_from
    HAS_SWAGGER = True
except ImportError:
    def swag_from(spec):
        def decorator(f):
            return f
        return decorator
    HAS_SWAGGER = False


def _scale_with_feature_names(scaler, input_df: pd.DataFrame) -> pd.DataFrame:
    """
    Scale input data and preserve feature names for downstream model prediction.
    Some sklearn models are trained with DataFrame columns and will reject
    unnamed ndarray inputs at predict time.
    """
    scaled_values = scaler.transform(input_df)
    return pd.DataFrame(scaled_values, columns=input_df.columns, index=input_df.index)


def _validate_prediction_features(payload: dict) -> dict:
    """
    Validate and normalize incoming feature values against the Hydrogen
    experiment ranges derived from the current dataset.
    """
    normalized = {}

    for request_key, feature_name in FEATURE_FIELD_MAP.items():
        if request_key not in payload:
            raise ValueError(f'Missing required field: {request_key}')

        try:
            value = float(payload[request_key])
        except (TypeError, ValueError):
            raise ValueError(f'{request_key} must be numeric') from None

        bounds = EXPERIMENT_CONFIG.feature_ranges[feature_name]
        if value < bounds['min'] or value > bounds['max']:
            raise ValueError(
                f'{request_key} must be between {bounds["min"]} and {bounds["max"]}'
            )

        normalized[request_key] = value

    return normalized


def _build_input_dataframe(features: dict) -> pd.DataFrame:
    return pd.DataFrame({
        feature_name: [features[request_key]]
        for request_key, feature_name in FEATURE_FIELD_MAP.items()
    })

@predict_bp.route('/model', methods=['POST'])
@token_required  
@swag_from({
    'tags': ['Prediction'],
    'summary': 'Predict using dynamic model loading',
    'description': 'Make predictions using any supported ML model type (Keras, PyTorch, XGBoost, Sklearn, etc.)',
    'security': [{'Bearer': []}],
    'parameters': [
        {
            'in': 'body',
            'name': 'body',
            'description': 'Prediction parameters with model information',
            'required': True,
            'schema': {
                'type': 'object',
                'required': [
                    'ph', 'vss', 'ethanol', 'acetate', 'propionate', 'butyrate',
                    'sucrose_degradation', 'orp_mid', 'orp_low', 'vfa', 'cod_o',
                    'model_path', 'model_type'
                ],
                'properties': {
                    **SWAGGER_FEATURE_PROPERTIES,
                    'model_path': {
                        'type': 'string',
                        'description': 'Absolute path to the model file'
                    },
                    'model_type': {
                        'type': 'string',
                        'enum': ['keras', 'pytorch', 'sklearn', 'xgboost', 'pickle', 'joblib'],
                        'description': 'Type of machine learning model'
                    }
                }
            }
        }
    ],
    'responses': {
        '200': {
            'description': 'Successful prediction',
            'schema': {
                'type': 'object',
                'properties': {
                    'prediction': {
                        'type': 'number',
                        'description': 'Predicted Hydrogen Production Rate'
                    },
                    'model_used': {
                        'type': 'string',
                        'description': 'Name/path of the model used'
                    },
                    'model_type': {
                        'type': 'string', 
                        'description': 'Type of the model used'
                    },
                    'input_parameters': {
                        'type': 'object',
                        'description': 'Input parameters used for prediction'
                    }
                }
            }
        },
        '400': {
            'description': 'Bad request - invalid input parameters'
        },
        '401': {
            'description': 'Unauthorized - invalid or missing token'
        },
        '404': {
            'description': 'Model file not found'
        },
        '500': {
            'description': 'Internal server error - model loading or prediction failed'
        }
    }
})
def predict_with_dynamic_model():
    """
    Universal prediction endpoint supporting multiple ML model types
    """
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = [
            'ph', 'vss', 'ethanol', 'acetate', 'propionate', 'butyrate',
            'sucrose_degradation', 'orp_mid', 'orp_low', 'vfa', 'cod_o',
            'model_path', 'model_type'
        ]
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        features = _validate_prediction_features(data)
        model_path = data['model_path']
        model_type = data['model_type'].lower()

        # Validate model type
        if model_type not in SUPPORTED_MODEL_TYPES:
            return jsonify({'error': f'Unsupported model_type: {model_type}. Supported types: {SUPPORTED_MODEL_TYPES}'}), 400

        # Check if model file exists
        if not os.path.exists(model_path):
            return jsonify({'error': f'Model file not found: {model_path}'}), 404

        # Load model
        model = ModelLoader.load_model(model_path, model_type)
        if model is None:
            return jsonify({'error': f'Failed to load model from {model_path}'}), 500

        # Prepare input DataFrame with correct column names (match training feature names)
        input_data = _build_input_dataframe(features)

        # Get shared scaler (MinMaxScaler)
        scaler = get_scaler()
        if scaler is None:
            return jsonify({'error': 'Failed to load scaler'}), 500

        scaled_data = _scale_with_feature_names(scaler, input_data)
        prediction = ModelPredictor.predict(model, scaled_data, model_type)

        if prediction is None:
            return jsonify({'error': 'Prediction failed'}), 500

        return jsonify({
            'prediction': prediction,
            'unit': 'L/h/L',
            'description': 'Hydrogen Production Rate',
            'user': request.user["username"],
            'model_used': os.path.basename(model_path),
            'model_type': model_type,
            'input_parameters': features
        })

    except ValueError as ve:
        return jsonify({'error': f'Invalid parameter value: {str(ve)}'}), 400
    except Exception as e:
        return jsonify({'error': f'Prediction error: {str(e)}'}), 500

@predict_bp.route('/health', methods=['GET'])
@swag_from({
    'tags': ['Health'],
    'summary': 'Health check endpoint',
    'description': 'Check if the predict service is running and healthy',
    'responses': {
        200: {
            'description': 'Service is healthy',
            'schema': {
                'type': 'object',
                'properties': {
                    'status': {'type': 'string', 'description': 'Health status'},
                    'message': {'type': 'string', 'description': 'Status message'}
                }
            }
        }
    }
})
def health_check():
    """Health check endpoint for the predict service"""
    return jsonify({
        "status": "healthy",
        "message": "Predict service is running"
    }), 200

# Prediction with active model from database
@predict_bp.route('/model/active', methods=['POST'])
# @token_required  # Temporarily disabled for testing  
@swag_from({
    'tags': ['Prediction'],
    'summary': 'Predict using active model from database',
    'description': 'Make predictions using the currently active model stored in database',
    'security': [{'Bearer': []}],
    'parameters': [
        {
            'in': 'body',
            'name': 'body',
            'description': 'Prediction parameters (model info automatically retrieved from database)',
            'required': True,
            'schema': {
                'type': 'object',
                'required': [
                    'ph', 'vss', 'ethanol', 'acetate', 'propionate', 'butyrate',
                    'sucrose_degradation', 'orp_mid', 'orp_low', 'vfa', 'cod_o'
                ],
                'properties': {
                    **SWAGGER_FEATURE_PROPERTIES
                }
            }
        }
    ],
    'responses': {
        '200': {
            'description': 'Successful prediction',
            'schema': {
                'type': 'object',
                'properties': {
                    'prediction': {'type': 'number'},
                    'model_used': {'type': 'string'},
                    'model_id': {'type': 'integer'},
                    'model_type': {'type': 'string'},
                    'input_parameters': {'type': 'object'}
                }
            }
        },
        '404': {'description': 'No active model found'},
        '500': {'description': 'Prediction failed'}
    }
})
def predict_with_active_model():
    """
    Prediction using the currently active model from database (Hydrogen HPR)
    """
    try:
        from app.utils.database_utils import DatabaseUtils

        data = request.get_json()

        required_fields = [
            'ph', 'vss', 'ethanol', 'acetate', 'propionate', 'butyrate',
            'sucrose_degradation', 'orp_mid', 'orp_low', 'vfa', 'cod_o'
        ]
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        features = _validate_prediction_features(data)

        # Get active model from database
        db_utils = DatabaseUtils()
        active_model_info = db_utils.get_active_model()
        if not active_model_info:
            return jsonify({'error': 'No active model found in database'}), 404

        model_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ml_model')
        raw_file_path = (active_model_info.get('FilePath') or '').strip()
        file_basename = os.path.basename(raw_file_path) if raw_file_path else ''

        possible_paths = [
            os.path.join(model_dir, 'latest_model.pkl'),
            os.path.join(model_dir, active_model_info.get('MLMName', '') + '.pkl'),
        ]

        # Resolve DB FilePath for both absolute and relative forms.
        if raw_file_path:
            if os.path.isabs(raw_file_path):
                possible_paths.append(raw_file_path)
            else:
                possible_paths.extend([
                    os.path.join('/var/www/html/public', raw_file_path.lstrip('/')),
                    os.path.join(model_dir, raw_file_path.lstrip('/')),
                    os.path.join('/app', raw_file_path.lstrip('/')),
                ])

        if file_basename:
            possible_paths.append(os.path.join(model_dir, file_basename))

        model_path = next((p for p in possible_paths if p and os.path.exists(p)), None)
        if not model_path:
            return jsonify({'error': 'Model file not found for active model'}), 404

        model_type = active_model_info.get('LibType', 'sklearn').lower()
        model = ModelLoader.load_model(model_path, model_type)
        if model is None:
            return jsonify({'error': f'Failed to load model from {model_path}'}), 500

        input_data = _build_input_dataframe(features)

        scaler = get_scaler()
        if scaler is None:
            return jsonify({'error': 'Failed to load scaler'}), 500

        scaled_data = _scale_with_feature_names(scaler, input_data)
        prediction = ModelPredictor.predict(model, scaled_data, model_type)
        if prediction is None:
            return jsonify({'error': 'Prediction failed'}), 500

        return jsonify({
            'prediction': prediction,
            'unit': 'L/h/L',
            'description': 'Hydrogen Production Rate',
            'user': getattr(request, 'user', {}).get('username', 'test_user'),
            'model_used': active_model_info.get('MLMName', 'unknown'),
            'model_id': active_model_info.get('id'),
            'model_type': model_type,
            'model_path': model_path,
            'input_parameters': features
        })

    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        return jsonify({'error': f'Prediction error: {str(e)}'}), 500


# ========== MLFLOW PREDICTION ENDPOINTS ==========

@predict_bp.route('/mlflow', methods=['POST'])
@swag_from({
    'tags': ['MLflow Prediction'],
    'summary': 'Predict using MLflow model (with cache)',
    'description': 'Make predictions using model from MLflow tracking with intelligent caching',
    'security': [{'Bearer': []}],
    'parameters': [
        {
            'in': 'body',
            'name': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['features'],
                'properties': {
                    'run_id': {
                        'type': 'string',
                        'description': 'MLflow run ID (option 1)'
                    },
                    'use_active': {
                        'type': 'boolean',
                        'description': 'Use active model from database (option 2)'
                    },
                    'model_name': {
                        'type': 'string',
                        'description': 'Model name to search in MLflow (option 3)'
                    },
                    'features': {
                        'type': 'object',
                        'required': [
                            'ph', 'vss', 'ethanol', 'acetate', 'propionate', 'butyrate',
                            'sucrose_degradation', 'orp_mid', 'orp_low', 'vfa', 'cod_o'
                        ],
                        'properties': SWAGGER_FEATURE_PROPERTIES
                    },
                    'force_reload': {
                        'type': 'boolean',
                        'default': False,
                        'description': 'Force reload model from MLflow (bypass cache)'
                    }
                }
            }
        }
    ],
    'responses': {
        '200': {
            'description': 'Successful prediction',
            'schema': {
                'type': 'object',
                'properties': {
                    'prediction': {'type': 'number'},
                    'unit': {'type': 'string'},
                    'mlflow_run_id': {'type': 'string'},
                    'cached': {'type': 'boolean'},
                    'model_source': {'type': 'string'},
                    'input_parameters': {'type': 'object'}
                }
            }
        }
    }
})
def predict_with_mlflow():
    """
    Predict sử dụng model từ MLflow với intelligent caching
    
    3 cách để chỉ định model:
    1. Cung cấp run_id trực tiếp
    2. Set use_active=true để dùng active model từ database
    3. Cung cấp model_name để search latest run
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        # Validate features
        if 'features' not in data:
            return jsonify({'error': 'Missing required field: features'}), 400
        
        features = data['features']
        required_features = [
            'ph', 'vss', 'ethanol', 'acetate', 'propionate', 'butyrate',
            'sucrose_degradation', 'orp_mid', 'orp_low', 'vfa', 'cod_o'
        ]
        
        for field in required_features:
            if field not in features:
                return jsonify({'error': f'Missing required feature: {field}'}), 400

        features = _validate_prediction_features(features)
        
        # Determine run_id từ các options
        run_id = None
        model_source = None
        
        # Option 1: User cung cấp run_id trực tiếp
        if 'run_id' in data and data['run_id']:
            run_id = data['run_id']
            model_source = 'run_id_provided'
            print(f"📌 Using provided run_id: {run_id}")
        
        # Option 2: Lấy từ active model trong database
        elif 'use_active' in data and data['use_active']:
            try:
                db_utils = DatabaseUtils()
                active_model = db_utils.get_active_model()
                
                if not active_model:
                    return jsonify({'error': 'No active model found in database'}), 404
                
                # Kiểm tra xem có mlflow_run_id không
                if 'mlflow_run_id' in active_model and active_model['mlflow_run_id']:
                    run_id = active_model['mlflow_run_id']
                    model_source = f"active_model_db (id={active_model.get('id')})"
                    print(f"📌 Using active model from database: {active_model.get('MLMName')}")
                else:
                    return jsonify({
                        'error': 'Active model does not have mlflow_run_id',
                        'suggestion': 'Train a new model or use run_id parameter'
                    }), 400
                    
            except Exception as db_error:
                return jsonify({'error': f'Database error: {str(db_error)}'}), 500
        
        # Option 3: Search by model_name trong MLflow
        elif 'model_name' in data and data['model_name']:
            try:
                import mlflow
                
                tracking_info = configure_mlflow_tracking_uri()
                if tracking_info.get('used_fallback'):
                    print(
                        f"⚠️ MLflow default directory is not writable, using fallback: "
                        f"{tracking_info.get('tracking_dir')}"
                    )
                
                # Search for latest run với model_name
                experiment_name = "hydrogen_production_training"
                experiment = mlflow.get_experiment_by_name(experiment_name)
                
                if not experiment:
                    return jsonify({'error': f'Experiment {experiment_name} not found'}), 404
                
                # Search runs
                client = mlflow.tracking.MlflowClient()
                runs = client.search_runs(
                    experiment_ids=[experiment.experiment_id],
                    filter_string=f"tags.mlflow.runName = '{data['model_name']}'",
                    max_results=1,
                    order_by=["start_time DESC"]
                )
                
                if not runs:
                    return jsonify({'error': f'No runs found for model_name: {data["model_name"]}'}), 404
                
                run_id = runs[0].info.run_id
                model_source = f"mlflow_search (name={data['model_name']})"
                print(f"📌 Found run via search: {run_id}")
                
            except Exception as search_error:
                return jsonify({'error': f'MLflow search error: {str(search_error)}'}), 500
        
        else:
            return jsonify({
                'error': 'Must provide one of: run_id, use_active=true, or model_name'
            }), 400
        
        # Validate run_id
        if not run_id:
            return jsonify({'error': 'Could not determine run_id'}), 400
        
        # Get force_reload flag
        force_reload = data.get('force_reload', False)
        
        # Load model + scaler từ MLflow cache
        print(f"🔄 Loading model for run_id: {run_id} (force_reload={force_reload})")
        
        try:
            model, scaler = MLflowModelCache.get_model(run_id, force_reload=force_reload)
            was_cached = run_id in MLflowModelCache.get_cached_run_ids() and not force_reload
            
        except Exception as load_error:
            return jsonify({
                'error': f'Failed to load model from MLflow: {str(load_error)}',
                'run_id': run_id
            }), 500
        
        # Prepare input data
        input_data = _build_input_dataframe(features)
        
        # Scale features
        scaled_data = _scale_with_feature_names(scaler, input_data)

        # Make prediction
        prediction = model.predict(scaled_data)[0]
        
        # Get user info
        user = getattr(request, 'user', {}).get('username', 'anonymous')
        
        # Return response
        return jsonify({
            'success': True,
            'prediction': float(prediction),
            'unit': 'L/h/L',
            'mlflow_run_id': run_id,
            'model_source': model_source,
            'cached': was_cached,
            'user': user,
            'input_parameters': {
                'ph': features['ph'],
                'vss': features['vss'],
                'ethanol': features['ethanol'],
                'acetate': features['acetate'],
                'propionate': features['propionate'],
                'butyrate': features['butyrate'],
                'sucrose_degradation': features['sucrose_degradation'],
                'orp_mid': features['orp_mid'],
                'orp_low': features['orp_low'],
                'vfa': features['vfa'],
                'cod_o': features['cod_o'],
            },
            'cache_info': {
                'total_cached_models': len(MLflowModelCache.get_cached_run_ids()),
                'cached_run_ids': MLflowModelCache.get_cached_run_ids()
            }
        }), 200
        
    except ValueError as ve:
        return jsonify({
            'success': False,
            'error': str(ve)
        }), 400
    except Exception as e:
        print(f"❌ Prediction error: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Prediction failed: {str(e)}'
        }), 500


@predict_bp.route('/mlflow/cache/info', methods=['GET'])
@swag_from({
    'tags': ['MLflow Cache'],
    'summary': 'Get MLflow cache information',
    'description': 'View current cache status and statistics',
    'parameters': [
        {
            'name': 'run_id',
            'in': 'query',
            'type': 'string',
            'required': False,
            'description': 'Specific run_id to get info (optional)'
        }
    ],
    'responses': {
        '200': {'description': 'Cache information'}
    }
})
def get_cache_info():
    """Get thông tin về MLflow model cache"""
    try:
        run_id = request.args.get('run_id')
        cache_info = MLflowModelCache.get_cache_info(run_id)
        
        return jsonify({
            'success': True,
            'cache_info': cache_info
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@predict_bp.route('/mlflow/cache/clear', methods=['POST'])
@swag_from({
    'tags': ['MLflow Cache'],
    'summary': 'Clear MLflow cache',
    'description': 'Clear all or specific model cache',
    'parameters': [
        {
            'in': 'body',
            'name': 'body',
            'schema': {
                'type': 'object',
                'properties': {
                    'run_id': {
                        'type': 'string',
                        'description': 'Specific run_id to clear (omit to clear all)'
                    }
                }
            }
        }
    ],
    'responses': {
        '200': {'description': 'Cache cleared successfully'}
    }
})
def clear_cache():
    """Clear MLflow model cache"""
    try:
        data = request.get_json() or {}
        run_id = data.get('run_id')
        
        MLflowModelCache.clear_cache(run_id)
        
        return jsonify({
            'success': True,
            'message': f'Cache cleared for run_id: {run_id}' if run_id else 'All cache cleared',
            'remaining_cached': len(MLflowModelCache.get_cached_run_ids())
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@predict_bp.route('/mlflow/cache/preload', methods=['POST'])
@swag_from({
    'tags': ['MLflow Cache'],
    'summary': 'Preload model into cache',
    'description': 'Warm up cache by preloading model',
    'parameters': [
        {
            'in': 'body',
            'name': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['run_id'],
                'properties': {
                    'run_id': {
                        'type': 'string',
                        'description': 'MLflow run_id to preload'
                    }
                }
            }
        }
    ],
    'responses': {
        '200': {'description': 'Model preloaded successfully'}
    }
})
def preload_cache():
    """Preload model vào cache (warm up)"""
    try:
        data = request.get_json()
        
        if not data or 'run_id' not in data:
            return jsonify({'error': 'Missing required field: run_id'}), 400
        
        run_id = data['run_id']
        
        # Preload model
        MLflowModelCache.preload_model(run_id)
        
        return jsonify({
            'success': True,
            'message': f'Model preloaded successfully for run_id: {run_id}',
            'cached_run_ids': MLflowModelCache.get_cached_run_ids()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# In the future, you can add routes for other models like /cnn, /xgboost ...
