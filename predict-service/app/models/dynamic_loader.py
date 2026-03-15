"""
Dynamic Model Loader
Support loading different types of models from filepath
"""
import os
import pickle
import joblib

class ModelLoader:
    """Class to load models from filepath with different libraries"""
    
    @staticmethod
    def load_model(model_path, model_type=None):
        """
        Load model from filepath
        
        Args:
            model_path (str): Path to model file
            model_type (str): Library type (keras, pytorch, sklearn, xgboost, pickle, joblib)
                            If None, will auto-detect from extension
        
        Returns:
            model: Loaded model object
        """
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")
        
        # Auto-detect model type from extension if not provided
        if model_type is None or model_type == 'auto':
            model_type = ModelLoader._detect_model_type(model_path)
        
        try:
            if model_type == 'keras':
                return ModelLoader._load_keras_model(model_path)
            elif model_type == 'pytorch':
                return ModelLoader._load_pytorch_model(model_path)
            elif model_type == 'sklearn':
                return ModelLoader._load_sklearn_model(model_path)
            elif model_type == 'xgboost':
                return ModelLoader._load_xgboost_model(model_path)
            elif model_type == 'pickle':
                return ModelLoader._load_sklearn_model(model_path)
            elif model_type == 'joblib':
                return ModelLoader._load_sklearn_model(model_path)
            else:
                raise ValueError(f"Unsupported model type: {model_type}")
                
        except Exception as e:
            raise Exception(f"Failed to load model from {model_path}: {str(e)}")
    
    @staticmethod
    def _detect_model_type(model_path):
        """Auto-detect model type from file extension"""
        _, ext = os.path.splitext(model_path.lower())
        
        # Keras/TensorFlow models
        if ext in ['.keras', '.h5', '.hdf5']:
            return 'keras'
        # PyTorch models
        elif ext in ['.pt', '.pth']:
            return 'pytorch'
        # Pickle files (could be any ML model)
        elif ext in ['.pkl', '.pickle']:
            return 'pickle'
        # Joblib files (usually sklearn)
        elif ext in ['.joblib']:
            return 'joblib'
        # XGBoost specific formats
        elif ext in ['.json', '.model', '.xgb']:
            return 'xgboost'
        else:
            # Default fallback to pickle for unknown extensions
            return 'pickle'
    
    @staticmethod
    def _load_keras_model(model_path):
        """Load Keras/TensorFlow model"""
        try:
            from tensorflow import keras
            return keras.models.load_model(model_path)
        except ImportError:
            raise ImportError("TensorFlow/Keras not available. Install: pip install tensorflow")
    
    @staticmethod
    def _load_pytorch_model(model_path):
        """Load PyTorch model"""
        try:
            import torch
            # Load the model (assumes model was saved with torch.save)
            model = torch.load(model_path, map_location='cpu')
            # Set to evaluation mode
            if hasattr(model, 'eval'):
                model.eval()
            return model
        except ImportError:
            raise ImportError("PyTorch not available. Install: pip install torch")
    
    @staticmethod
    def _load_sklearn_model(model_path):
        """Load scikit-learn model"""
        try:
            import sklearn
            return joblib.load(model_path)
        except ImportError:
            raise ImportError("scikit-learn not available. Install: pip install scikit-learn")
    
    @staticmethod
    def _load_xgboost_model(model_path):
        """Load XGBoost model"""
        try:
            import xgboost as xgb
            model = xgb.Booster()
            model.load_model(model_path)
            return model
        except ImportError:
            raise ImportError("XGBoost not available. Install: pip install xgboost")
    
    @staticmethod
    def _load_pickle_model(model_path):
        """Load model from pickle file"""
        with open(model_path, 'rb') as f:
            return pickle.load(f)
    
    @staticmethod
    def _load_joblib_model(model_path):
        """Load model from joblib file"""
        return joblib.load(model_path)


class ModelPredictor:
    """Class to perform predictions with different model types"""
    
    @staticmethod
    def predict(model, inputs, model_type=None):
        """
        Perform prediction
        
        Args:
            model: Loaded model object
            inputs: Input data (numpy array or pandas DataFrame)
            model_type (str): Model type for appropriate prediction handling
            
        Returns:
            prediction result
        """
        try:
            # Determine model type if not provided
            if model_type is None:
                model_type = ModelPredictor._infer_model_type(model)
            
            # Keras/TensorFlow models
            if model_type == 'keras' or ('tensorflow' in str(type(model)) and hasattr(model, 'predict')):
                result = model.predict(inputs)
                # Keras usually returns 2D array, get first value
                if hasattr(result, 'flatten'):
                    raw_result = float(result.flatten()[0])
                elif hasattr(result, '__getitem__'):
                    raw_result = float(result[0][0] if hasattr(result[0], '__getitem__') else result[0])
                else:
                    raw_result = float(result)
                
                # Normalize output for Hydrogen Production Rate (HPR)
                return ModelPredictor._normalize_hpr_output(raw_result, model_type)
            
            # PyTorch models
            elif model_type == 'pytorch' or 'torch' in str(type(model)):
                import torch
                # Convert inputs to tensor if needed
                if not isinstance(inputs, torch.Tensor):
                    if hasattr(inputs, 'values'):
                        # Pandas DataFrame
                        inputs_tensor = torch.FloatTensor(inputs.values)
                    else:
                        # Numpy array or list
                        inputs_tensor = torch.FloatTensor(inputs)
                else:
                    inputs_tensor = inputs
                
                # Make prediction
                with torch.no_grad():
                    result = model(inputs_tensor)
                
                # Convert result to float
                if hasattr(result, 'item'):
                    raw_result = float(result.item())
                elif hasattr(result, 'detach'):
                    raw_result = float(result.detach().numpy().flatten()[0])
                else:
                    raw_result = float(result[0])
                
                # Normalize output for Hydrogen Production Rate (HPR)
                return ModelPredictor._normalize_hpr_output(raw_result, model_type)
            
            # XGBoost models
            elif model_type == 'xgboost' or 'xgboost' in str(type(model)):
                import xgboost as xgb
                if hasattr(inputs, 'values'):
                    # Pandas DataFrame
                    dmatrix = xgb.DMatrix(
                        inputs.values,
                        feature_names=list(inputs.columns),
                    )
                else:
                    # Numpy array
                    dmatrix = xgb.DMatrix(inputs)
                result = model.predict(dmatrix)
                raw_result = float(result[0])
                
                # Normalize output for Hydrogen Production Rate (HPR)
                return ModelPredictor._normalize_hpr_output(raw_result, model_type)
            
            # Scikit-learn and other models with predict method
            elif hasattr(model, 'predict'):
                result = model.predict(inputs)
                if hasattr(result, '__iter__') and not isinstance(result, str):
                    raw_result = float(result[0])
                else:
                    raw_result = float(result)
                
                return ModelPredictor._normalize_hpr_output(raw_result, model_type)
            
            else:
                raise ValueError(f"Unsupported model type for prediction: {type(model)}")
                
        except Exception as e:
            raise Exception(f"Prediction failed: {str(e)}")
    
    @staticmethod
    def _infer_model_type(model):
        """Infer model type from model object"""
        model_type_str = str(type(model)).lower()
        
        if 'tensorflow' in model_type_str or 'keras' in model_type_str:
            return 'keras'
        elif 'torch' in model_type_str:
            return 'pytorch'
        elif 'xgboost' in model_type_str:
            return 'xgboost'
        elif hasattr(model, 'predict'):
            return 'sklearn'  # Assume sklearn for models with predict method
        else:
            return 'unknown'

    @staticmethod
    def _normalize_hpr_output(raw_result, model_type):
        """
        Normalize model output for Hydrogen Production Rate (HPR).
        """
        _ = model_type  # model_type kept for compatibility with existing call sites

        # HPR is a non-negative regression target measured directly in L/h/L.
        return round(max(float(raw_result), 0.0), 4)
