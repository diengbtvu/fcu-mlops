<?php

return [
    'title' => 'Cài Đặt Email',
    'description' => 'Cấu hình thông báo email và cài đặt SMTP',
    
    // Sections
    'notification_settings' => 'Cài Đặt Thông Báo',
    'smtp_configuration' => 'Cấu Hình SMTP',
    'sender_information' => 'Thông Tin Người Gửi',
    
    // Fields
    'notification_email' => 'Email Nhận Thông Báo',
    'notification_email_help' => 'Địa chỉ email nhận thông báo khi hoàn thành huấn luyện',
    'smtp_host' => 'Máy Chủ SMTP',
    'smtp_host_help' => 'Máy chủ SMTP của nhà cung cấp email (ví dụ: smtp.gmail.com)',
    'smtp_port' => 'Cổng SMTP',
    'smtp_port_help' => 'Thường là 587 cho TLS hoặc 465 cho SSL',
    'smtp_username' => 'Tên Đăng Nhập SMTP',
    'smtp_username_help' => 'Địa chỉ email của bạn',
    'smtp_password' => 'Mật Khẩu SMTP',
    'smtp_password_help' => 'Mật khẩu email hoặc mật khẩu ứng dụng',
    'smtp_encryption' => 'Mã Hóa SMTP',
    'smtp_encryption_help' => 'Giao thức bảo mật (khuyến nghị TLS)',
    'mail_from_address' => 'Địa Chỉ Email Gửi',
    'mail_from_address_help' => 'Địa chỉ email xuất hiện trong trường "Từ"',
    'mail_from_name' => 'Tên Người Gửi',
    'mail_from_name_help' => 'Tên xuất hiện trong trường "Từ"',
    
    // Encryption options
    'encryption' => [
        'tls' => 'TLS (Khuyến nghị)',
        'ssl' => 'SSL',
        'none' => 'Không',
    ],
    
    // Actions
    'save_settings' => 'Lưu Cài Đặt',
    'test_email' => 'Gửi Email Thử',
    'show_password' => 'Hiện Mật Khẩu',
    'hide_password' => 'Ẩn Mật Khẩu',
    
    // Gmail Instructions
    'gmail_setup' => 'Hướng Dẫn Cài Đặt Gmail',
    'gmail_step1' => 'Bật Xác minh 2 bước trong Tài khoản Google của bạn',
    'gmail_step2' => 'Tạo Mật khẩu ứng dụng',
    'gmail_step3' => 'Sử dụng mật khẩu ứng dụng 16 ký tự trong trường Mật khẩu SMTP',
    'gmail_link' => 'Tạo Mật Khẩu Ứng Dụng',
    
    // Messages
    'settings_saved' => 'Lưu cài đặt email thành công!',
    'test_email_sent' => 'Gửi email thử thành công! Vui lòng kiểm tra hộp thư của bạn.',
    'test_email_failed' => 'Gửi email thử thất bại. Vui lòng kiểm tra cài đặt SMTP.',
    'smtp_error' => 'Lỗi cấu hình SMTP. Vui lòng kiểm tra lại cài đặt.',
    
    // Training Notification Email
    'training_notification' => [
        'subject' => 'Hoàn Thành Huấn Luyện Mô Hình',
        'greeting' => 'Xin chào!',
        'body' => 'Quá trình huấn luyện mô hình của bạn đã hoàn thành thành công.',
        'model_name' => 'Tên Mô Hình',
        'library_type' => 'Loại Thư Viện',
        'metrics' => 'Chỉ Số Hiệu Suất',
        'view_model' => 'Xem Mô Hình',
        'footer' => 'Cảm ơn bạn đã sử dụng nền tảng của chúng tôi!',
    ],
];
