<?php

return [
    'title' => 'Email Settings',
    'description' => 'Configure email notifications and SMTP settings',
    
    // Sections
    'notification_settings' => 'Notification Settings',
    'smtp_configuration' => 'SMTP Configuration',
    'sender_information' => 'Sender Information',
    
    // Fields
    'notification_email' => 'Notification Email',
    'notification_email_help' => 'Email address to receive training completion notifications',
    'smtp_host' => 'SMTP Host',
    'smtp_host_help' => 'Your email provider\'s SMTP server (e.g., smtp.gmail.com)',
    'smtp_port' => 'SMTP Port',
    'smtp_port_help' => 'Usually 587 for TLS or 465 for SSL',
    'smtp_username' => 'SMTP Username',
    'smtp_username_help' => 'Your email address',
    'smtp_password' => 'SMTP Password',
    'smtp_password_help' => 'Your email password or app-specific password',
    'smtp_encryption' => 'SMTP Encryption',
    'smtp_encryption_help' => 'Security protocol (TLS recommended)',
    'mail_from_address' => 'From Email Address',
    'mail_from_address_help' => 'Email address that appears in "From" field',
    'mail_from_name' => 'From Name',
    'mail_from_name_help' => 'Name that appears in "From" field',
    
    // Encryption options
    'encryption' => [
        'tls' => 'TLS (Recommended)',
        'ssl' => 'SSL',
        'none' => 'None',
    ],
    
    // Actions
    'save_settings' => 'Save Settings',
    'test_email' => 'Send Test Email',
    'show_password' => 'Show Password',
    'hide_password' => 'Hide Password',
    
    // Gmail Instructions
    'gmail_setup' => 'Gmail Setup Instructions',
    'gmail_step1' => 'Enable 2-Step Verification in your Google Account',
    'gmail_step2' => 'Generate an App Password',
    'gmail_step3' => 'Use the 16-character app password in the SMTP Password field',
    'gmail_link' => 'Create App Password',
    
    // Messages
    'settings_saved' => 'Email settings saved successfully!',
    'test_email_sent' => 'Test email sent successfully! Please check your inbox.',
    'test_email_failed' => 'Failed to send test email. Please check your SMTP settings.',
    'smtp_error' => 'SMTP configuration error. Please verify your settings.',
    
    // Training Notification Email
    'training_notification' => [
        'subject' => 'Model Training Completed',
        'greeting' => 'Hello!',
        'body' => 'Your model training has been completed successfully.',
        'model_name' => 'Model Name',
        'library_type' => 'Library Type',
        'metrics' => 'Performance Metrics',
        'view_model' => 'View Model',
        'footer' => 'Thank you for using our platform!',
    ],
];
