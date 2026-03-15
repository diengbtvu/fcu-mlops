from flask import Blueprint, request, jsonify
from app.middlewares.auth import token_required
import pandas as pd
import os

from app.models.dynamic_loader import ModelLoader, ModelPredictor
from app.scalers.shared_scaler import get_scaler
from app.utils.mlflow_cache import MLflowModelCache
from app.utils.mlflow_tracking import configure_mlflow_tracking_uri
from app.utils.database_utils import DatabaseUtils
import traceback

predict_bp = Blueprint('predict', __name__, url_prefix='/predict')

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
                    'ph': {'type': 'number', 'minimum': 3, 'maximum': 8, 'description': 'System pH'},
                    'vss': {'type': 'number', 'minimum': 0, 'maximum': 10000, 'description': 'Volatile Suspended Solids (mg/L)'},
                    'ethanol': {'type': 'number', 'minimum': 0, 'maximum': 100, 'description': 'Ethanol concentration'},
                    'acetate': {'type': 'number', 'minimum': 0, 'maximum': 200, 'description': 'Acetate concentration'},
                    'propionate': {'type': 'number', 'minimum': 0, 'maximum': 100, 'description': 'Propionate concentration'},
                    'butyrate': {'type': 'number', 'minimum': 0, 'maximum': 200, 'description': 'Butyrate concentration'},
                    'sucrose_degradation': {'type': 'number', 'minimum': 0, 'maximum': 100, 'description': 'Sucrose degradation (%)'},
                    'orp_mid': {'type': 'number', 'minimum': -500, 'maximum': 100, 'description': 'ORP Mid (mV)'},
                    'orp_low': {'type': 'number', 'minimum': -500, 'maximum': 100, 'description': 'ORP Low (mV)'},
                    'vfa': {'type': 'number', 'minimum': 0, 'maximum': 500, 'description': 'VFA concentration'},
                    'cod_o': {'type': 'number', 'minimum': 0, 'maximum': 50000, 'description': 'COD-O (mg/L)'},
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

        # Extract parameters
        ph                  = float(data['ph'])
        vss                 = float(data['vss'])
        ethanol             = float(data['ethanol'])
        acetate             = float(data['acetate'])
        propionate          = float(data['propionate'])
        butyrate            = float(data['butyrate'])
        sucrose_degradation = float(data['sucrose_degradation'])
        orp_mid             = float(data['orp_mid'])
        orp_low             = float(data['orp_low'])
        vfa                 = float(data['vfa'])
        cod_o               = float(data['cod_o'])
        model_path          = data['model_path']
        model_type          = data['model_type'].lower()

        # Validate ranges
        if not (3.0 <= ph <= 8.0):
            return jsonify({'error': 'ph must be between 3.0 and 8.0'}), 400
        if not (0 <= vss <= 10000):
            return jsonify({'error': 'vss must be between 0 and 10000'}), 400
        if not (0 <= ethanol <= 100):
            return jsonify({'error': 'ethanol must be between 0 and 100'}), 400
        if not (0 <= acetate <= 200):
            return jsonify({'error': 'acetate must be between 0 and 200'}), 400
        if not (0 <= propionate <= 100):
            return jsonify({'error': 'propionate must be between 0 and 100'}), 400
        if not (0 <= butyrate <= 200):
            return jsonify({'error': 'butyrate must be between 0 and 200'}), 400
        if not (0 <= sucrose_degradation <= 100):
            return jsonify({'error': 'sucrose_degradation must be between 0 and 100'}), 400
        if not (-500 <= orp_mid <= 100):
            return jsonify({'error': 'orp_mid must be between -500 and 100'}), 400
        if not (-500 <= orp_low <= 100):
            return jsonify({'error': 'orp_low must be between -500 and 100'}), 400
        if not (0 <= vfa <= 500):
            return jsonify({'error': 'vfa must be between 0 and 500'}), 400
        if not (0 <= cod_o <= 50000):
            return jsonify({'error': 'cod_o must be between 0 and 50000'}), 400

        # Validate model type
        supported_types = ['keras', 'pytorch', 'sklearn', 'xgboost', 'pickle', 'joblib']
        if model_type not in supported_types:
            return jsonify({'error': f'Unsupported model_type: {model_type}. Supported types: {supported_types}'}), 400

        # Check if model file exists
        if not os.path.exists(model_path):
            return jsonify({'error': f'Model file not found: {model_path}'}), 404

        # Load model
        model = ModelLoader.load_model(model_path, model_type)
        if model is None:
            return jsonify({'error': f'Failed to load model from {model_path}'}), 500

        # Prepare input DataFrame with correct column names (match training feature names)
        input_data = pd.DataFrame({
            'pH':                  [ph],
            'VSS':                 [vss],
            'Ethanol':             [ethanol],
            'Acetate':             [acetate],
            'Propionate':          [propionate],
            'Butyrate':            [butyrate],
            'Sucrose_Degradation': [sucrose_degradation],
            'ORP_Mid':             [orp_mid],
            'ORP_Low':             [orp_low],
            'VFA':                 [vfa],
            'COD-O':               [cod_o],
        })

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
            'input_parameters': {
                'ph': ph, 'vss': vss, 'ethanol': ethanol,
                'acetate': acetate, 'propionate': propionate,
                'butyrate': butyrate, 'sucrose_degradation': sucrose_degradation,
                'orp_mid': orp_mid, 'orp_low': orp_low,
                'vfa': vfa, 'cod_o': cod_o,
            }
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
                    'ph': {'type': 'number', 'minimum': 3, 'maximum': 8},
                    'vss': {'type': 'number', 'minimum': 0, 'maximum': 10000},
                    'ethanol': {'type': 'number', 'minimum': 0, 'maximum': 100},
                    'acetate': {'type': 'number', 'minimum': 0, 'maximum': 200},
                    'propionate': {'type': 'number', 'minimum': 0, 'maximum': 100},
                    'butyrate': {'type': 'number', 'minimum': 0, 'maximum': 200},
                    'sucrose_degradation': {'type': 'number', 'minimum': 0, 'maximum': 100},
                    'orp_mid': {'type': 'number', 'minimum': -500, 'maximum': 100},
                    'orp_low': {'type': 'number', 'minimum': -500, 'maximum': 100},
                    'vfa': {'type': 'number', 'minimum': 0, 'maximum': 500},
                    'cod_o': {'type': 'number', 'minimum': 0, 'maximum': 50000}
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

        input_data = pd.DataFrame({
            'pH':                  [float(data['ph'])],
            'VSS':                 [float(data['vss'])],
            'Ethanol':             [float(data['ethanol'])],
            'Acetate':             [float(data['acetate'])],
            'Propionate':          [float(data['propionate'])],
            'Butyrate':            [float(data['butyrate'])],
            'Sucrose_Degradation': [float(data['sucrose_degradation'])],
            'ORP_Mid':             [float(data['orp_mid'])],
            'ORP_Low':             [float(data['orp_low'])],
            'VFA':                 [float(data['vfa'])],
            'COD-O':               [float(data['cod_o'])],
        })

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
            'input_parameters': {k: float(data[k]) for k in required_fields}
        })

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
                        'properties': {
                            'ph': {'type': 'number', 'minimum': 3, 'maximum': 8},
                            'vss': {'type': 'number', 'minimum': 0, 'maximum': 10000},
                            'ethanol': {'type': 'number', 'minimum': 0, 'maximum': 100},
                            'acetate': {'type': 'number', 'minimum': 0, 'maximum': 200},
                            'propionate': {'type': 'number', 'minimum': 0, 'maximum': 100},
                            'butyrate': {'type': 'number', 'minimum': 0, 'maximum': 200},
                            'sucrose_degradation': {'type': 'number', 'minimum': 0, 'maximum': 100},
                            'orp_mid': {'type': 'number', 'minimum': -500, 'maximum': 100},
                            'orp_low': {'type': 'number', 'minimum': -500, 'maximum': 100},
                            'vfa': {'type': 'number', 'minimum': 0, 'maximum': 500},
                            'cod_o': {'type': 'number', 'minimum': 0, 'maximum': 50000}
                        }
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
        input_data = pd.DataFrame({
            'pH': [features['ph']],
            'VSS': [features['vss']],
            'Ethanol': [features['ethanol']],
            'Acetate': [features['acetate']],
            'Propionate': [features['propionate']],
            'Butyrate': [features['butyrate']],
            'Sucrose_Degradation': [features['sucrose_degradation']],
            'ORP_Mid': [features['orp_mid']],
            'ORP_Low': [features['orp_low']],
            'VFA': [features['vfa']],
            'COD-O': [features['cod_o']],
        })
        
        # Validate ranges
        if not (3.0 <= features['ph'] <= 8.0):
            return jsonify({'error': 'ph must be between 3.0 and 8.0'}), 400
        if not (0 <= features['vss'] <= 10000):
            return jsonify({'error': 'vss must be between 0 and 10000'}), 400
        if not (0 <= features['ethanol'] <= 100):
            return jsonify({'error': 'ethanol must be between 0 and 100'}), 400
        if not (0 <= features['acetate'] <= 200):
            return jsonify({'error': 'acetate must be between 0 and 200'}), 400
        if not (0 <= features['propionate'] <= 100):
            return jsonify({'error': 'propionate must be between 0 and 100'}), 400
        if not (0 <= features['butyrate'] <= 200):
            return jsonify({'error': 'butyrate must be between 0 and 200'}), 400
        if not (0 <= features['sucrose_degradation'] <= 100):
            return jsonify({'error': 'sucrose_degradation must be between 0 and 100'}), 400
        if not (-500 <= features['orp_mid'] <= 100):
            return jsonify({'error': 'orp_mid must be between -500 and 100'}), 400
        if not (-500 <= features['orp_low'] <= 100):
            return jsonify({'error': 'orp_low must be between -500 and 100'}), 400
        if not (0 <= features['vfa'] <= 500):
            return jsonify({'error': 'vfa must be between 0 and 500'}), 400
        if not (0 <= features['cod_o'] <= 50000):
            return jsonify({'error': 'cod_o must be between 0 and 50000'}), 400
        
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
