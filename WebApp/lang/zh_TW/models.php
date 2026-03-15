<?php

return [
    'title' => '模型管理',
    'list' => '模型列表',
    'create' => '建立模型',
    'edit' => '編輯模型',
    'delete' => '刪除模型',
    'details' => '模型詳情',
    'comparison' => '模型比較',
    
    // Fields
    'name' => '模型名稱',
    'library_type' => '函式庫類型',
    'mse' => 'MSE',
    'mae' => 'MAE',
    'r2' => 'R² 分數',
    'rmse' => 'RMSE',
    'created_date' => '建立日期',
    'algorithm' => '演算法',
    'parameters' => '參數',
    'training_time' => '訓練時間',
    'dataset_used' => '使用的資料集',
    
    // Library Types
    'libraries' => [
        'ann' => '人工神經網路',
        'xgboost' => 'XGBoost',
        'random_forest' => '隨機森林',
        'linear_regression' => '線性迴歸',
    ],
    
    // Comparison
    'compare_models' => '比較模型',
    'select_models' => '選擇要比較的模型',
    'comparison_chart' => '比較圖表',
    'winner' => '優勝者',
    'best_model' => '最佳模型',
    'metrics_comparison' => '指標比較',
    'performance_summary' => '效能摘要',
    
    // Warnings
    'incomplete_metrics' => '部分模型的指標資料不完整。請重新訓練這些模型以取得完整的評估指標。',
    'no_r2_value' => 'R² 值無法取得',
    'no_rmse_value' => 'RMSE 值無法取得',
    
    // Actions
    'train_model' => '訓練模型',
    'retrain' => '重新訓練',
    'evaluate' => '評估',
    'deploy' => '部署',
    'download_model' => '下載模型',
    'view_logs' => '檢視日誌',
    
    // Messages
    'training_started' => '模型訓練已成功開始！',
    'training_completed' => '模型訓練已完成！',
    'training_failed' => '模型訓練失敗。請檢查日誌。',
    'model_deleted' => '模型已成功刪除！',
    'no_models' => '找不到模型。請先訓練模型。',
];
