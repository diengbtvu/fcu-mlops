from flask import Blueprint, request, jsonify, send_from_directory, abort
from app.middlewares.auth import token_required
import os
from datetime import datetime
import traceback
from app.utils.database_utils import DatabaseUtils
from app.utils.progress_tracker import TrainingProgressTracker
from app.utils.mlflow_tracking import configure_mlflow_tracking_uri
from app.utils.training_report import generate_training_report
import sys
import mlflow
import mlflow.sklearn
import mlflow.xgboost

# Append the base directory to the path for module imports
current_file_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file_path)))
sys.path.append(project_root)
REPORTS_ROOT = os.path.join(project_root, "app", "reports")

# Import training helper functions
from app.routes.train_helpers import (
    train_random_forest,
    train_xgboost,
    train_svm,
    train_knn,
    train_decision_tree,
    run_gra_analysis,
    prepare_data,
    evaluate_model,
    save_model_files
)

train_bp = Blueprint('train', __name__, url_prefix='/train')

# Try to import swagger decorator
try:
    from flasgger import swag_from
    HAS_SWAGGER = True
except ImportError:
    def swag_from(spec):
        def decorator(f):
            return f
        return decorator
    HAS_SWAGGER = False


@train_bp.route('/model', methods=['POST'])
# @token_required  # Temporarily disabled for development
@swag_from({
    'tags': ['Training'],
    'summary': 'Train a new ML model',
    'description': 'Train one paper model: SVM, Decision Tree, Random Forest, KNN, or XGBoost',
    'security': [{'Bearer': []}],
    'parameters': [
        {
            'in': 'body',
            'name': 'body',
            'description': 'Training parameters',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['dataset_path'],
                'properties': {
                    'dataset_path': {
                        'type': 'string',
                        'description': 'Absolute path to the dataset file (.csv or .xlsx)'
                    },
                    'model_name': {
                        'type': 'string',
                        'description': 'Custom name for the trained model (optional)'
                    },
                    'training_scope': {
                        'type': 'string',
                        'default': 'all_models_compare',
                        'description': 'single_model (no benchmark comparison) or all_models_compare'
                    },
                    'n_estimators': {
                        'type': 'integer',
                        'default': 100,
                        'description': 'Number of trees in the forest'
                    },
                    'max_depth': {
                        'type': 'integer',
                        'default': None,
                        'description': 'Maximum depth of trees'
                    },
                    'test_size': {
                        'type': 'number',
                        'default': 0.2,
                        'minimum': 0.1,
                        'maximum': 0.5,
                        'description': 'Proportion of dataset for testing'
                    },
                    'random_state': {
                        'type': 'integer',
                        'default': 42,
                        'description': 'Random state for reproducibility'
                    },
                    'dataset_id': {
                        'type': 'integer',
                        'description': 'Optional dataset ID for database reference'
                    }
                }
            }
        }
    ],
    'responses': {
        '200': {
            'description': 'Training completed successfully',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'},
                    'model_path': {'type': 'string'},
                    'metrics': {
                        'type': 'object',
                        'properties': {
                            'r2_score': {'type': 'number'},
                            'rmse': {'type': 'number'},
                            'mae': {'type': 'number'}
                        }
                    },
                    'training_info': {
                        'type': 'object',
                        'properties': {
                            'train_samples': {'type': 'integer'},
                            'test_samples': {'type': 'integer'},
                            'n_features': {'type': 'integer'},
                            'trained_by': {'type': 'string'},
                            'trained_at': {'type': 'string'},
                            'saved_to_database': {'type': 'boolean'}
                        }
                    },
                    'database_id': {'type': 'integer', 'description': 'Database ID of saved model'},
                    'scaler_path': {'type': 'string', 'description': 'Path to saved scaler file'},
                    'model_name': {'type': 'string', 'description': 'Name of the trained model'}
                }
            }
        },
        '400': {'description': 'Bad request - invalid parameters'},
        '401': {'description': 'Unauthorized'},
        '404': {'description': 'Dataset file not found'},
        '500': {'description': 'Training failed'}
    }
})
def train_model():
    """
    Train a new ML model (SVM, Decision Tree, Random Forest, KNN, or XGBoost)
    """
    try:
        data = request.get_json()
        
        # Get user info and dataset ID from request
        trained_by = data.get('trained_by', 1)
        dataset_id = data.get('dataset_id', None)
        session_id = data.get('session_id', None)  # Get session_id for progress tracking
        
        # Validate required fields
        if 'dataset_path' not in data:
            return jsonify({'error': 'Missing required field: dataset_path'}), 400
        
        dataset_path = data['dataset_path']
        
        # Check if dataset file exists
        if not os.path.exists(dataset_path):
            return jsonify({'error': f'Dataset file not found: {dataset_path}'}), 404

        if not str(dataset_path).lower().endswith(('.csv', '.xlsx')):
            return jsonify({
                'error': 'Unsupported dataset format. Only .csv and .xlsx are allowed.'
            }), 400
        
        # Get model type and parameters
        model_type = data.get('model_type', 'random_forest')
        training_scope = str(data.get('training_scope', 'all_models_compare')).lower().strip()
        test_size = float(data.get('test_size', 0.2))
        random_state = int(data.get('random_state', 42))
        model_name = data.get('model_name', f'{model_type.upper()}_Model_{datetime.now().strftime("%Y%m%d_%H%M%S")}')

        if training_scope not in {'single_model', 'all_models_compare'}:
            return jsonify({
                'error': 'training_scope must be one of: single_model, all_models_compare'
            }), 400
        include_comparison = training_scope == 'all_models_compare'
        
        # Validate common parameters
        if not (0.1 <= test_size <= 0.5):
            return jsonify({'error': 'test_size must be between 0.1 and 0.5'}), 400
        
        # ========== MLFLOW TRACKING START ==========
        tracking_info = configure_mlflow_tracking_uri()
        if tracking_info.get('used_fallback'):
            print(
                f"⚠️ MLflow default directory is not writable, using fallback: "
                f"{tracking_info.get('tracking_dir')}"
            )
        experiment_name = "hydrogen_production_training"
        mlflow.set_experiment(experiment_name)
        
        # Start MLflow run
        with mlflow.start_run(run_name=model_name):
            # Log common parameters
            mlflow.log_param("model_type", model_type)
            mlflow.log_param("test_size", test_size)
            mlflow.log_param("random_state", random_state)
            mlflow.log_param("training_scope", training_scope)
            mlflow.log_param("trained_by", trained_by)
            mlflow.log_param("dataset_path", dataset_path)
            if dataset_id:
                mlflow.log_param("dataset_id", dataset_id)
            
            # ========== TRAIN BASED ON MODEL TYPE ==========
            model_type_lower = str(model_type).lower()

            # Optional: run GRA before training
            gra_result = None
            if data.get('use_gra', False):
                try:
                    X_train_tmp, X_test_tmp, y_train_tmp, y_test_tmp, _sc = prepare_data(
                        dataset_path, data, None
                    )
                    gra_result = run_gra_analysis(X_train_tmp, y_train_tmp)
                    print(f"GRA ranking computed. Top feature: {gra_result['ranking'][0]['feature']}")
                except Exception as gra_err:
                    print(f"Warning: GRA failed: {gra_err}")

            if model_type_lower == 'random_forest':
                model, scaler, metrics, save_paths = train_random_forest(
                    data, dataset_path, model_name, trained_by, dataset_id, session_id
                )
            elif model_type_lower == 'xgboost':
                model, scaler, metrics, save_paths = train_xgboost(
                    data, dataset_path, model_name, trained_by, dataset_id, session_id
                )
            elif model_type_lower == 'svm':
                model, scaler, metrics, save_paths = train_svm(
                    data, dataset_path, model_name, trained_by, dataset_id, session_id
                )
            elif model_type_lower == 'knn':
                model, scaler, metrics, save_paths = train_knn(
                    data, dataset_path, model_name, trained_by, dataset_id, session_id
                )
            elif model_type_lower in ('decision_tree', 'dt'):
                model, scaler, metrics, save_paths = train_decision_tree(
                    data, dataset_path, model_name, trained_by, dataset_id, session_id
                )
            else:
                return jsonify({'error': f'Unsupported model_type: {model_type}. '
                                         f'Supported: random_forest, svm, knn, decision_tree (or dt), xgboost'}), 400
            
            # Get MLflow run info
            mlflow_run_id = mlflow.active_run().info.run_id
            mlflow_experiment_id = mlflow.active_run().info.experiment_id
            
            print(f"\n🔗 MLflow Tracking:")
            print(f"   Experiment: {experiment_name}")
            print(f"   Run ID: {mlflow_run_id}")

            # Generate chart/report artifacts (best-effort, non-blocking)
            report_info = None
            try:
                X_train_report, X_test_report, y_train_report, y_test_report, _ = prepare_data(
                    dataset_path, data, None, log_to_mlflow=False
                )
                report_info = generate_training_report(
                    model_name=model_name,
                    model_type=model_type_lower,
                    trained_model=model,
                    X_train=X_train_report,
                    X_test=X_test_report,
                    y_train=y_train_report,
                    y_test=y_test_report,
                    selected_metrics=metrics,
                    gra_ranking=(gra_result or {}).get("ranking") if isinstance(gra_result, dict) else None,
                    include_comparison=include_comparison,
                )
                if isinstance(report_info, dict):
                    report_info['training_scope'] = training_scope
                print(f"📊 Training report generated: {report_info.get('route_prefix')}")
            except Exception as report_error:
                print(f"⚠️ Report generation failed: {report_error}")
            
            # Save model information to Laravel database
            try:
                db_utils = DatabaseUtils()
                
                if not db_utils.test_connection():
                    print("⚠️ Cannot connect to Laravel API - skipping database save")
                    model_db_id = None
                else:
                    # Prepare model information
                    model_info = {
                        'MLMName': model_name,
                        'FilePath': f'models/{save_paths["model_filename"]}',
                        'LibType': save_paths['lib_type'],
                        'IsActive': True,
                        'MSEValue': round(metrics['mse'], 6),
                        'MAEValue': round(metrics['mae'], 6),
                        'R2Value': round(metrics['r2_score'], 6),
                        'RMSEValue': round(metrics['rmse'], 6),
                        'TrainedBy': trained_by,
                        'DatasetId': dataset_id,
                        'mlflow_run_id': mlflow_run_id,
                        'mlflow_experiment_id': mlflow_experiment_id,
                        'gra_ranking': (gra_result or {}).get("ranking") if isinstance(gra_result, dict) else None,
                        'training_report': report_info,
                        'auth_token': request.headers.get('Authorization', '').replace('Bearer ', '') if hasattr(request, 'headers') else None
                    }
                    
                    db_result = db_utils.save_ml_model_to_db(model_info)
                    
                    if db_result:
                        print("✅ Model information saved to database!")
                        model_db_id = db_result.get('data', {}).get('id')
                    else:
                        print("⚠️ Failed to save to database")
                        model_db_id = None
                
            except Exception as db_error:
                print(f"⚠️ Database save error: {str(db_error)}")
                model_db_id = None
            
            # Return success response
            response_data = {
                'success': True,
                'message': f'{model_type.upper()} model trained successfully',
                'model_path': save_paths['model_path'],
                'scaler_path': save_paths['scaler_path'],
                'model_name': model_name,
                'model_type': model_type,
                'database_id': model_db_id,
                'mlflow_run_id': mlflow_run_id,
                'mlflow_experiment_id': mlflow_experiment_id,
                'metrics': metrics,
                'gra_ranking': gra_result,
                'report_info': report_info,
                'training_info': {
                    'model_type': model_type,
                    'training_scope': training_scope,
                    'lib_type': save_paths['lib_type'],
                    'trained_by': trained_by,
                    'trained_at': datetime.now().isoformat(),
                    'saved_to_database': model_db_id is not None,
                    'report_generated': report_info is not None
                }
            }
            
            # Mark training as complete
            if session_id:
                tracker = TrainingProgressTracker()
                tracker.complete_training(
                    session_id,
                    result=response_data,
                    message=f"Training completed! {model_type.upper()} achieved R²={metrics['r2_score']:.4f}"
                )
            
            return jsonify(response_data), 200
        
    except Exception as e:
        print(f"\n❌ Training Error: {str(e)}")
        traceback.print_exc()
        
        # Mark training as failed
        if 'session_id' in locals() and session_id:
            tracker = TrainingProgressTracker()
            tracker.fail_training(session_id, error=str(e))
        
        return jsonify({
            'success': False,
            'error': f'Training failed: {str(e)}'
        }), 500


@train_bp.route('/reports/<report_id>/<path:filename>', methods=['GET'])
def get_training_report_asset(report_id, filename):
    """Serve generated training report assets."""
    reports_root = os.path.abspath(REPORTS_ROOT)
    report_dir = os.path.abspath(os.path.join(reports_root, report_id))

    # Block path traversal
    if not report_dir.startswith(reports_root + os.sep):
        abort(400)
    if not os.path.exists(report_dir):
        abort(404)

    return send_from_directory(report_dir, filename)


@train_bp.route('/status', methods=['GET'])
@swag_from({
    'tags': ['Training'],
    'summary': 'Get training service status',
    'description': 'Check if training service is available',
    'responses': {
        '200': {
            'description': 'Service status',
            'schema': {
                'type': 'object',
                'properties': {
                    'status': {'type': 'string'},
                    'available_models_dir': {'type': 'string'}
                }
            }
        }
    }
})
def training_status():
    """Check training service status"""
    model_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ml_model')
    return jsonify({
        'status': 'available',
        'models_directory': model_dir,
        'models_count': len([f for f in os.listdir(model_dir) if f.endswith('.pkl')]) if os.path.exists(model_dir) else 0
    }), 200


@train_bp.route('/models', methods=['GET'])
@token_required
@swag_from({
    'tags': ['Training'],
    'summary': 'List all trained models',
    'description': 'Get list of all trained models in ml_model directory',
    'security': [{'Bearer': []}],
    'responses': {
        '200': {
            'description': 'List of models',
            'schema': {
                'type': 'object',
                'properties': {
                    'models': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'name': {'type': 'string'},
                                'path': {'type': 'string'},
                                'size': {'type': 'integer'},
                                'created_at': {'type': 'string'}
                            }
                        }
                    }
                }
            }
        }
    }
})
def list_models():
    """List all trained models"""
    try:
        model_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ml_model')
        
        if not os.path.exists(model_dir):
            return jsonify({'models': []}), 200
        
        models = []
        for filename in os.listdir(model_dir):
            if filename.endswith('.pkl') and not filename.endswith('_scaler.pkl'):
                filepath = os.path.join(model_dir, filename)
                stat = os.stat(filepath)
                models.append({
                    'name': filename,
                    'path': filepath,
                    'size': stat.st_size,
                    'created_at': datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
        
        return jsonify({'models': models}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@train_bp.route('/mlflow/experiments', methods=['GET'])
@swag_from({
    'tags': ['MLflow Tracking'],
    'summary': 'Get MLflow experiments',
    'description': 'List all MLflow experiments',
    'responses': {
        '200': {
            'description': 'List of experiments',
            'schema': {
                'type': 'object',
                'properties': {
                    'experiments': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'experiment_id': {'type': 'string'},
                                'name': {'type': 'string'},
                                'artifact_location': {'type': 'string'}
                            }
                        }
                    }
                }
            }
        }
    }
})
def get_mlflow_experiments():
    """Get all MLflow experiments"""
    try:
        configure_mlflow_tracking_uri()
        
        client = mlflow.tracking.MlflowClient()
        experiments = client.search_experiments()
        
        exp_list = []
        for exp in experiments:
            exp_list.append({
                'experiment_id': exp.experiment_id,
                'name': exp.name,
                'artifact_location': exp.artifact_location,
                'lifecycle_stage': exp.lifecycle_stage
            })
        
        return jsonify({'experiments': exp_list}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@train_bp.route('/mlflow/runs', methods=['GET'])
@swag_from({
    'tags': ['MLflow Tracking'],
    'summary': 'Get MLflow runs',
    'description': 'List all MLflow runs for an experiment',
    'parameters': [
        {
            'name': 'experiment_name',
            'in': 'query',
            'type': 'string',
            'required': False,
            'default': 'hydrogen_production_training',
            'description': 'Experiment name to filter runs'
        },
        {
            'name': 'limit',
            'in': 'query',
            'type': 'integer',
            'required': False,
            'default': 10,
            'description': 'Maximum number of runs to return'
        }
    ],
    'responses': {
        '200': {
            'description': 'List of runs',
            'schema': {
                'type': 'object',
                'properties': {
                    'runs': {
                        'type': 'array',
                        'items': {
                            'type': 'object'
                        }
                    }
                }
            }
        }
    }
})
def get_mlflow_runs():
    """Get MLflow runs for an experiment"""
    try:
        # Get query parameters
        experiment_name = request.args.get('experiment_name', 'hydrogen_production_training')
        limit = int(request.args.get('limit', 10))
        
        configure_mlflow_tracking_uri()
        
        # Get experiment
        client = mlflow.tracking.MlflowClient()
        experiment = client.get_experiment_by_name(experiment_name)
        
        if not experiment:
            return jsonify({'error': f'Experiment {experiment_name} not found'}), 404
        
        # Search runs
        runs = client.search_runs(
            experiment_ids=[experiment.experiment_id],
            max_results=limit,
            order_by=["start_time DESC"]
        )
        
        runs_list = []
        for run in runs:
            runs_list.append({
                'run_id': run.info.run_id,
                'run_name': run.data.tags.get('mlflow.runName', 'N/A'),
                'status': run.info.status,
                'start_time': datetime.fromtimestamp(run.info.start_time / 1000).isoformat(),
                'end_time': datetime.fromtimestamp(run.info.end_time / 1000).isoformat() if run.info.end_time else None,
                'metrics': run.data.metrics,
                'params': run.data.params,
                'artifact_uri': run.info.artifact_uri
            })
        
        return jsonify({
            'experiment': experiment_name,
            'total_runs': len(runs_list),
            'runs': runs_list
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
