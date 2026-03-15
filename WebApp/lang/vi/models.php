<?php

return [
    'title' => 'Quản Lý Mô Hình',
    'list' => 'Danh Sách Mô Hình',
    'create' => 'Tạo Mô Hình',
    'edit' => 'Chỉnh Sửa Mô Hình',
    'delete' => 'Xóa Mô Hình',
    'details' => 'Chi Tiết Mô Hình',
    'comparison' => 'So Sánh Mô Hình',
    
    // Fields
    'name' => 'Tên Mô Hình',
    'library_type' => 'Loại Thư Viện',
    'mse' => 'MSE',
    'mae' => 'MAE',
    'r2' => 'Chỉ Số R²',
    'rmse' => 'RMSE',
    'created_date' => 'Ngày Tạo',
    'algorithm' => 'Thuật Toán',
    'parameters' => 'Tham Số',
    'training_time' => 'Thời Gian Huấn Luyện',
    'dataset_used' => 'Tập Dữ Liệu Sử Dụng',
    
    // Library Types
    'libraries' => [
        'ann' => 'Mạng Nơ-ron Nhân Tạo',
        'xgboost' => 'XGBoost',
        'random_forest' => 'Rừng Ngẫu Nhiên',
        'linear_regression' => 'Hồi Quy Tuyến Tính',
    ],
    
    // Comparison
    'compare_models' => 'So Sánh Mô Hình',
    'select_models' => 'Chọn mô hình để so sánh',
    'comparison_chart' => 'Biểu Đồ So Sánh',
    'winner' => 'Chiến Thắng',
    'best_model' => 'Mô Hình Tốt Nhất',
    'metrics_comparison' => 'So Sánh Chỉ Số',
    'performance_summary' => 'Tóm Tắt Hiệu Suất',
    
    // Warnings
    'incomplete_metrics' => 'Một số mô hình có dữ liệu chỉ số không đầy đủ. Vui lòng huấn luyện lại các mô hình này để có đầy đủ các chỉ số đánh giá.',
    'no_r2_value' => 'Chỉ số R² không có sẵn',
    'no_rmse_value' => 'Giá trị RMSE không có sẵn',
    
    // Actions
    'train_model' => 'Huấn Luyện Mô Hình',
    'retrain' => 'Huấn Luyện Lại',
    'evaluate' => 'Đánh Giá',
    'deploy' => 'Triển Khai',
    'download_model' => 'Tải Xuống Mô Hình',
    'view_logs' => 'Xem Nhật Ký',
    
    // Messages
    'training_started' => 'Bắt đầu huấn luyện mô hình thành công!',
    'training_completed' => 'Hoàn thành huấn luyện mô hình!',
    'training_failed' => 'Huấn luyện mô hình thất bại. Vui lòng kiểm tra nhật ký.',
    'model_deleted' => 'Xóa mô hình thành công!',
    'no_models' => 'Không tìm thấy mô hình nào. Vui lòng huấn luyện mô hình trước.',
];
