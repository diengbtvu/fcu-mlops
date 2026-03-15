<?php

return [
    'title' => 'Email 設定',
    'description' => '設定 Email 通知和 SMTP 設定',
    
    // Sections
    'notification_settings' => '通知設定',
    'smtp_configuration' => 'SMTP 設定',
    'sender_information' => '寄件者資訊',
    
    // Fields
    'notification_email' => '通知 Email',
    'notification_email_help' => '接收訓練完成通知的 Email 地址',
    'smtp_host' => 'SMTP 主機',
    'smtp_host_help' => '您的電子郵件提供者的 SMTP 伺服器（例如：smtp.gmail.com）',
    'smtp_port' => 'SMTP 埠',
    'smtp_port_help' => 'TLS 通常使用 587，SSL 使用 465',
    'smtp_username' => 'SMTP 使用者名稱',
    'smtp_username_help' => '您的 Email 地址',
    'smtp_password' => 'SMTP 密碼',
    'smtp_password_help' => '您的 Email 密碼或應用程式專用密碼',
    'smtp_encryption' => 'SMTP 加密',
    'smtp_encryption_help' => '安全協定（建議使用 TLS）',
    'mail_from_address' => '寄件者 Email',
    'mail_from_address_help' => '顯示在「寄件者」欄位的 Email 地址',
    'mail_from_name' => '寄件者名稱',
    'mail_from_name_help' => '顯示在「寄件者」欄位的名稱',
    
    // Encryption options
    'encryption' => [
        'tls' => 'TLS（建議）',
        'ssl' => 'SSL',
        'none' => '無',
    ],
    
    // Actions
    'save_settings' => '儲存設定',
    'test_email' => '傳送測試 Email',
    'show_password' => '顯示密碼',
    'hide_password' => '隱藏密碼',
    
    // Gmail Instructions
    'gmail_setup' => 'Gmail 設定說明',
    'gmail_step1' => '在您的 Google 帳戶中啟用兩步驟驗證',
    'gmail_step2' => '產生應用程式密碼',
    'gmail_step3' => '在 SMTP 密碼欄位中使用 16 字元的應用程式密碼',
    'gmail_link' => '建立應用程式密碼',
    
    // Messages
    'settings_saved' => 'Email 設定儲存成功！',
    'test_email_sent' => '測試 Email 傳送成功！請檢查您的收件匣。',
    'test_email_failed' => '傳送測試 Email 失敗。請檢查您的 SMTP 設定。',
    'smtp_error' => 'SMTP 設定錯誤。請驗證您的設定。',
    
    // Training Notification Email
    'training_notification' => [
        'subject' => '模型訓練已完成',
        'greeting' => '您好！',
        'body' => '您的模型訓練已成功完成。',
        'model_name' => '模型名稱',
        'library_type' => '函式庫類型',
        'metrics' => '效能指標',
        'view_model' => '檢視模型',
        'footer' => '感謝您使用我們的平台！',
    ],
];
