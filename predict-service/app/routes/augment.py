from flask import Blueprint, request, jsonify
import os
import pandas as pd
from datetime import datetime
import logging

from app.utils.data_augmentation import DataAugmenter

logger = logging.getLogger(__name__)

augment_bp = Blueprint('augment', __name__)


@augment_bp.route('/augment', methods=['POST'])
def augment_dataset():
    """
    API endpoint để thực hiện data augmentation
    
    Request JSON:
    {
        "dataset_path": "path/to/dataset.csv",
        "augmentation_method": "smote|random_oversample|random_undersample|noise_injection|interpolation|duplication",
        "sampling_strategy": "auto|minority|not majority|not minority|all",
        "k_neighbors": 5,
        "noise_level": 0.05,
        "duplicate_factor": 2,
        "output_name": "custom_name" (optional)
    }
    """
    try:
        data = request.get_json()
        
        # Validate input
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
        
        dataset_path = data.get('dataset_path')
        if not dataset_path or not os.path.exists(dataset_path):
            return jsonify({
                'success': False,
                'error': f'Dataset file not found: {dataset_path}'
            }), 400
        
        # Get augmentation parameters
        method = data.get('augmentation_method', 'smote')
        sampling_strategy = data.get('sampling_strategy', 'auto')
        k_neighbors = int(data.get('k_neighbors', 5))
        noise_level = float(data.get('noise_level', 0.05))
        duplicate_factor = int(data.get('duplicate_factor', 2))
        output_name = data.get('output_name')
        
        # Validate method
        augmenter = DataAugmenter()
        if method not in augmenter.supported_methods:
            return jsonify({
                'success': False,
                'error': f'Unsupported method: {method}',
                'supported_methods': augmenter.supported_methods
            }), 400
        
        logger.info(f"Starting data augmentation: {method} on {dataset_path}")
        
        # Load dataset
        df = pd.read_csv(dataset_path)
        original_rows = len(df)
        
        logger.info(f"Loaded dataset with {original_rows} rows, {df.shape[1]} columns")
        
        # Auto-detect target column (prefer HPR-like names, fallback to last column)
        target_column = None
        for col in df.columns:
            col_lower = col.lower()
            if col_lower in {'hpr', 'hydrogen_production_rate'} or 'hydrogen production rate' in col_lower:
                target_column = col
                break
        
        if target_column is None:
            target_column = df.columns[-1]  # Use last column as fallback
        
        logger.info(f"Using target column: {target_column}")
        
        # Perform augmentation
        augmented_df, stats = augmenter.augment(
            df,
            method=method,
            target_column=target_column,
            sampling_strategy=sampling_strategy,
            k_neighbors=k_neighbors,
            noise_level=noise_level,
            duplicate_factor=duplicate_factor
        )
        
        # Generate output filename
        if output_name:
            output_filename = output_name if output_name.endswith('.csv') else f'{output_name}.csv'
        else:
            base_name = os.path.splitext(os.path.basename(dataset_path))[0]
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_filename = f'{base_name}_augmented_{method}_{timestamp}.csv'
        
        # Save to data directory in predict-service
        output_dir = os.path.join(os.path.dirname(dataset_path))
        output_path = os.path.join(output_dir, output_filename)
        
        augmented_df.to_csv(output_path, index=False)
        
        logger.info(f"Augmentation completed. Saved to: {output_path}")
        
        return jsonify({
            'success': True,
            'message': f'Data augmentation completed successfully using {method}',
            'original_rows': stats['original_rows'],
            'augmented_rows': stats['augmented_rows'],
            'increase': stats['increase'],
            'increase_percent': round(stats['increase_percent'], 2),
            'method': method,
            'augmented_file_path': output_path,
            'augmented_filename': output_filename
        }), 200
        
    except Exception as e:
        logger.error(f"Augmentation failed: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@augment_bp.route('/augment/methods', methods=['GET'])
def get_augmentation_methods():
    """
    API để lấy danh sách các phương pháp augmentation có sẵn
    """
    augmenter = DataAugmenter()
    
    methods_info = {
        'smote': {
            'name': 'SMOTE',
            'description': 'Synthetic Minority Over-sampling Technique',
            'parameters': ['sampling_strategy', 'k_neighbors']
        },
        'random_oversample': {
            'name': 'Random Oversampling',
            'description': 'Random oversampling of minority class',
            'parameters': ['sampling_strategy']
        },
        'random_undersample': {
            'name': 'Random Undersampling',
            'description': 'Random undersampling of majority class',
            'parameters': ['sampling_strategy']
        },
        'noise_injection': {
            'name': 'Noise Injection',
            'description': 'Add Gaussian noise to features',
            'parameters': ['noise_level', 'duplicate_factor']
        },
        'interpolation': {
            'name': 'Linear Interpolation',
            'description': 'Create synthetic samples using interpolation',
            'parameters': ['duplicate_factor']
        },
        'duplication': {
            'name': 'Duplication with Variation',
            'description': 'Duplicate data with small variations',
            'parameters': ['duplicate_factor', 'noise_level']
        }
    }
    
    return jsonify({
        'success': True,
        'methods': methods_info,
        'supported_methods': augmenter.supported_methods
    }), 200
