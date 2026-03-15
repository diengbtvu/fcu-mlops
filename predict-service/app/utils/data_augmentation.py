"""
Data Augmentation Utility
Cung cấp các phương pháp tăng cường dữ liệu cho dataset
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional
from imblearn.over_sampling import SMOTE, RandomOverSampler
from imblearn.under_sampling import RandomUnderSampler
import logging

logger = logging.getLogger(__name__)


class DataAugmenter:
    """Class để xử lý data augmentation"""
    
    def __init__(self):
        self.supported_methods = [
            'smote',
            'random_oversample',
            'random_undersample',
            'noise_injection',
            'interpolation',
            'duplication'
        ]
    
    def _clip_values(self, df: pd.DataFrame, original_df: pd.DataFrame) -> pd.DataFrame:
        """
        Giới hạn giá trị của augmented data trong range của original data
        
        Args:
            df: Augmented DataFrame
            original_df: Original DataFrame để lấy min/max bounds
            
        Returns:
            DataFrame với giá trị đã được clip
        """
        df_clipped = df.copy()
        
        # Clip từng cột số theo min/max của original data
        numeric_cols = original_df.select_dtypes(include=[np.number]).columns
        
        for col in numeric_cols:
            if col in df_clipped.columns:
                min_val = original_df[col].min()
                max_val = original_df[col].max()
                
                # Nếu cột có giá trị >= 0 (như HPR), không cho phép âm
                if min_val >= 0:
                    df_clipped[col] = df_clipped[col].clip(lower=0, upper=max_val)
                else:
                    df_clipped[col] = df_clipped[col].clip(lower=min_val, upper=max_val)
                
                logger.debug(f"Clipped column '{col}' to range [{min_val:.2f}, {max_val:.2f}]")
        
        return df_clipped
    
    def augment(
        self,
        df: pd.DataFrame,
        method: str = 'smote',
        target_column: str = 'HPR',
        **kwargs
    ) -> Tuple[pd.DataFrame, Dict]:
        """
        Thực hiện data augmentation
        
        Args:
            df: DataFrame cần augment
            method: Phương pháp augmentation
            target_column: Tên cột target (mặc định: 'HPR')
            **kwargs: Các tham số bổ sung cho từng phương pháp
            
        Returns:
            Tuple[pd.DataFrame, Dict]: (augmented_df, stats)
        """
        if method not in self.supported_methods:
            raise ValueError(f"Method '{method}' not supported. Choose from: {self.supported_methods}")
        
        original_rows = len(df)
        logger.info(f"Starting augmentation with method: {method}, original rows: {original_rows}")
        
        # Gọi phương thức tương ứng
        if method == 'smote':
            augmented_df = self._smote(df, target_column, **kwargs)
        elif method == 'random_oversample':
            augmented_df = self._random_oversample(df, target_column, **kwargs)
        elif method == 'random_undersample':
            augmented_df = self._random_undersample(df, target_column, **kwargs)
        elif method == 'noise_injection':
            augmented_df = self._noise_injection(df, **kwargs)
        elif method == 'interpolation':
            augmented_df = self._interpolation(df, **kwargs)
        elif method == 'duplication':
            augmented_df = self._duplication(df, **kwargs)
        else:
            raise ValueError(f"Unknown method: {method}")
        
        augmented_rows = len(augmented_df)
        
        stats = {
            'original_rows': original_rows,
            'augmented_rows': augmented_rows,
            'increase': augmented_rows - original_rows,
            'increase_percent': ((augmented_rows - original_rows) / original_rows) * 100
        }
        
        logger.info(f"Augmentation completed: {original_rows} -> {augmented_rows} rows")
        return augmented_df, stats
    
    def _smote(
        self,
        df: pd.DataFrame,
        target_column: str,
        sampling_strategy: str = 'auto',
        k_neighbors: int = 5,
        **kwargs
    ) -> pd.DataFrame:
        """SMOTE - Synthetic Minority Over-sampling Technique"""
        try:
            X = df.drop(columns=[target_column])
            y = df[target_column]
            
            # Chuyển target thành categorical nếu cần
            if y.dtype in ['float64', 'float32', 'int64', 'int32']:
                # Tạo bins dựa trên unique values
                n_unique = y.nunique()
                n_bins = min(5, n_unique) if n_unique > 1 else 2
                y = pd.cut(y, bins=n_bins, labels=False, duplicates='drop')
            
            # Kiểm tra số lượng samples trong mỗi class
            class_counts = y.value_counts()
            min_samples = class_counts.min()
            
            # Điều chỉnh k_neighbors dựa trên số samples ít nhất
            if min_samples <= 1:
                logger.warning(f"SMOTE requires at least 2 samples per class, found {min_samples}. Using duplication instead.")
                return self._duplication(df, duplicate_factor=2, noise_level=0.05)
            
            # k_neighbors phải nhỏ hơn min_samples
            adjusted_k_neighbors = min(k_neighbors, min_samples - 1, len(df) - 1)
            if adjusted_k_neighbors < 1:
                adjusted_k_neighbors = 1
            
            logger.info(f"SMOTE with k_neighbors={adjusted_k_neighbors} (min_samples={min_samples})")
            
            smote = SMOTE(
                sampling_strategy=sampling_strategy,
                k_neighbors=adjusted_k_neighbors,
                random_state=42
            )
            
            X_resampled, y_resampled = smote.fit_resample(X, y)
            
            # Tạo DataFrame mới
            augmented_df = pd.DataFrame(X_resampled, columns=X.columns)
            augmented_df[target_column] = y_resampled
            
            # Clip giá trị về range hợp lệ
            augmented_df = self._clip_values(augmented_df, df)
            
            return augmented_df
            
        except Exception as e:
            logger.error(f"SMOTE failed: {str(e)}")
            raise
    
    def _random_oversample(
        self,
        df: pd.DataFrame,
        target_column: str,
        sampling_strategy: str = 'auto',
        **kwargs
    ) -> pd.DataFrame:
        """Random Oversampling"""
        try:
            X = df.drop(columns=[target_column])
            y = df[target_column]
            
            # Chuyển target thành categorical nếu cần
            if y.dtype in ['float64', 'float32', 'int64', 'int32']:
                n_unique = y.nunique()
                n_bins = min(5, n_unique) if n_unique > 1 else 2
                y = pd.cut(y, bins=n_bins, labels=False, duplicates='drop')
            
            # Kiểm tra số lượng samples
            class_counts = y.value_counts()
            if class_counts.min() < 1:
                logger.warning("Not enough samples for oversampling. Using duplication instead.")
                return self._duplication(df, duplicate_factor=2, noise_level=0.05)
            
            ros = RandomOverSampler(sampling_strategy=sampling_strategy, random_state=42)
            X_resampled, y_resampled = ros.fit_resample(X, y)
            
            augmented_df = pd.DataFrame(X_resampled, columns=X.columns)
            augmented_df[target_column] = y_resampled
            
            # Clip giá trị về range hợp lệ
            augmented_df = self._clip_values(augmented_df, df)
            
            return augmented_df
            
        except Exception as e:
            logger.error(f"Random oversample failed: {str(e)}")
            raise
    
    def _random_undersample(
        self,
        df: pd.DataFrame,
        target_column: str,
        sampling_strategy: str = 'auto',
        **kwargs
    ) -> pd.DataFrame:
        """Random Undersampling"""
        try:
            X = df.drop(columns=[target_column])
            y = df[target_column]
            
            # Chuyển target thành categorical nếu cần
            if y.dtype in ['float64', 'float32', 'int64', 'int32']:
                n_unique = y.nunique()
                n_bins = min(5, n_unique) if n_unique > 1 else 2
                y = pd.cut(y, bins=n_bins, labels=False, duplicates='drop')
            
            # Kiểm tra số lượng samples
            class_counts = y.value_counts()
            if len(class_counts) < 2:
                logger.warning("Need at least 2 classes for undersampling. Returning original data.")
                return df
            
            rus = RandomUnderSampler(sampling_strategy=sampling_strategy, random_state=42)
            X_resampled, y_resampled = rus.fit_resample(X, y)
            
            augmented_df = pd.DataFrame(X_resampled, columns=X.columns)
            augmented_df[target_column] = y_resampled
            
            return augmented_df
            
        except Exception as e:
            logger.error(f"Random undersample failed: {str(e)}")
            raise
    
    def _noise_injection(
        self,
        df: pd.DataFrame,
        noise_level: float = 0.05,
        duplicate_factor: int = 2,
        **kwargs
    ) -> pd.DataFrame:
        """Thêm nhiễu Gaussian vào dữ liệu"""
        augmented_dfs = [df.copy()]
        
        for i in range(duplicate_factor - 1):
            noisy_df = df.copy()
            
            # Thêm nhiễu vào các cột số
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            for col in numeric_cols:
                noise = np.random.normal(0, df[col].std() * noise_level, size=len(df))
                noisy_df[col] = noisy_df[col] + noise
            
            augmented_dfs.append(noisy_df)
        
        result_df = pd.concat(augmented_dfs, ignore_index=True)
        
        # Clip giá trị về range hợp lệ
        result_df = self._clip_values(result_df, df)
        
        return result_df
    
    def _interpolation(
        self,
        df: pd.DataFrame,
        duplicate_factor: int = 2,
        **kwargs
    ) -> pd.DataFrame:
        """Tạo dữ liệu mới bằng interpolation"""
        augmented_dfs = [df.copy()]
        
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        
        for i in range(duplicate_factor - 1):
            interpolated_df = pd.DataFrame()
            
            for col in df.columns:
                if col in numeric_cols:
                    # Linear interpolation giữa các điểm ngẫu nhiên
                    idx1 = np.random.randint(0, len(df), size=len(df))
                    idx2 = np.random.randint(0, len(df), size=len(df))
                    alpha = np.random.random(size=len(df))
                    
                    interpolated_df[col] = df[col].iloc[idx1].values * alpha + \
                                          df[col].iloc[idx2].values * (1 - alpha)
                else:
                    # Giữ nguyên giá trị cho cột không phải số
                    interpolated_df[col] = df[col].sample(n=len(df), replace=True).values
            
            augmented_dfs.append(interpolated_df)
        
        result_df = pd.concat(augmented_dfs, ignore_index=True)
        
        # Clip giá trị về range hợp lệ
        result_df = self._clip_values(result_df, df)
        
        return result_df
    
    def _duplication(
        self,
        df: pd.DataFrame,
        duplicate_factor: int = 2,
        noise_level: float = 0.05,
        **kwargs
    ) -> pd.DataFrame:
        """Nhân đôi dữ liệu với variations nhỏ"""
        augmented_dfs = [df.copy()]
        
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        
        for i in range(duplicate_factor - 1):
            duplicated_df = df.copy()
            
            # Thêm variation nhỏ
            for col in numeric_cols:
                variation = np.random.uniform(
                    -df[col].std() * noise_level,
                    df[col].std() * noise_level,
                    size=len(df)
                )
                duplicated_df[col] = duplicated_df[col] + variation
            
            augmented_dfs.append(duplicated_df)
        
        result_df = pd.concat(augmented_dfs, ignore_index=True)
        
        # Clip giá trị về range hợp lệ
        result_df = self._clip_values(result_df, df)
        
        return result_df


def augment_dataset(
    input_path: str,
    output_path: str,
    method: str = 'smote',
    target_column: str = 'HPR',
    **kwargs
) -> Dict:
    """
    Augment dataset từ file
    
    Args:
        input_path: Đường dẫn file input
        output_path: Đường dẫn file output
        method: Phương pháp augmentation
        target_column: Tên cột target
        **kwargs: Tham số bổ sung
        
    Returns:
        Dict: Kết quả và thống kê
    """
    try:
        # Đọc dataset
        df = pd.read_csv(input_path)
        logger.info(f"Loaded dataset from {input_path}, shape: {df.shape}")
        
        # Thực hiện augmentation
        augmenter = DataAugmenter()
        augmented_df, stats = augmenter.augment(df, method, target_column, **kwargs)
        
        # Lưu kết quả
        augmented_df.to_csv(output_path, index=False)
        logger.info(f"Saved augmented dataset to {output_path}")
        
        return {
            'success': True,
            'input_path': input_path,
            'output_path': output_path,
            'method': method,
            'stats': stats
        }
        
    except Exception as e:
        logger.error(f"Augmentation failed: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }
