<?php

require __DIR__.'/vendor/autoload.php';

$app = require_once __DIR__.'/bootstrap/app.php';
$app->make(\Illuminate\Contracts\Console\Kernel::class)->bootstrap();

use App\Models\User;

// Find admin user
$admin = User::where('Username', 'admin')->first();

if ($admin) {
    echo "=== ADMIN INFORMATION ===\n";
    echo "Username: " . $admin->Username . "\n";
    echo "Full Name: " . $admin->FullName . "\n";
    echo "Email: " . ($admin->email ?? 'NULL - NOT SET') . "\n";
    echo "Role ID: " . $admin->role_id . "\n";
    echo "Role: " . $admin->role->RoleName . "\n";
    echo "\n";
    
    if (empty($admin->email)) {
        echo "⚠️  WARNING: Admin does not have an email address!\n";
        echo "This is required for password reset functionality.\n";
    }
} else {
    echo "❌ Admin user not found!\n";
}
