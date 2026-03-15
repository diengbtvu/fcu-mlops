<?php

require __DIR__.'/vendor/autoload.php';

$app = require_once __DIR__.'/bootstrap/app.php';
$app->make(\Illuminate\Contracts\Console\Kernel::class)->bootstrap();

use Illuminate\Support\Facades\Mail;
use App\Mail\TrainingCompletedMail;

echo "=== EMAIL TEST SCRIPT ===\n\n";

// Check mail config
echo "MAIL_MAILER: " . config('mail.default') . "\n";
echo "MAIL_HOST: " . config('mail.mailers.smtp.host') . "\n";
echo "MAIL_PORT: " . config('mail.mailers.smtp.port') . "\n";
echo "MAIL_USERNAME: " . config('mail.mailers.smtp.username') . "\n";
echo "MAIL_ENCRYPTION: " . config('mail.mailers.smtp.encryption') . "\n";
echo "MAIL_FROM: " . config('mail.from.address') . "\n";
echo "\n";

// Test data
$trainingData = [
    'model_type' => 'XGBoost',
    'dataset_name' => 'Test Dataset',
    'model_name' => 'Test Model',
    'test_size' => 0.2,
];

$result = [
    'success' => true,
    'metrics' => [
        'r2_score' => 0.85,
        'rmse' => 10.5,
        'mae' => 8.2,
    ]
];

$recipient = 'add17022003@gmail.com';

echo "Sending test email to: {$recipient}\n";
echo "Please wait...\n\n";

try {
    Mail::to($recipient)->send(new TrainingCompletedMail($trainingData, $result));
    echo "✅ Email sent successfully!\n";
    echo "Please check your inbox/spam folder.\n";
} catch (\Exception $e) {
    echo "❌ Failed to send email!\n";
    echo "Error: " . $e->getMessage() . "\n";
}
