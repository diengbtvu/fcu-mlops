<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        Schema::create('email_settings', function (Blueprint $table) {
            $table->id();
            $table->string('key')->unique(); // notification_email, smtp_host, smtp_port, etc.
            $table->text('value')->nullable();
            $table->string('type')->default('text'); // text, email, number, password, select
            $table->string('group')->default('general'); // general, smtp, notification
            $table->text('description')->nullable();
            $table->boolean('is_encrypted')->default(false);
            $table->timestamps();
        });

        // Insert default settings
        DB::table('email_settings')->insert([
            [
                'key' => 'notification_email',
                'value' => config('mail.from.address'),
                'type' => 'email',
                'group' => 'notification',
                'description' => 'Email address to receive training completion notifications',
                'is_encrypted' => false,
                'created_at' => now(),
                'updated_at' => now(),
            ],
            [
                'key' => 'smtp_host',
                'value' => config('mail.mailers.smtp.host'),
                'type' => 'text',
                'group' => 'smtp',
                'description' => 'SMTP server hostname',
                'is_encrypted' => false,
                'created_at' => now(),
                'updated_at' => now(),
            ],
            [
                'key' => 'smtp_port',
                'value' => config('mail.mailers.smtp.port'),
                'type' => 'number',
                'group' => 'smtp',
                'description' => 'SMTP server port (587 for TLS, 465 for SSL)',
                'is_encrypted' => false,
                'created_at' => now(),
                'updated_at' => now(),
            ],
            [
                'key' => 'smtp_username',
                'value' => config('mail.mailers.smtp.username'),
                'type' => 'email',
                'group' => 'smtp',
                'description' => 'SMTP username (usually your email address)',
                'is_encrypted' => false,
                'created_at' => now(),
                'updated_at' => now(),
            ],
            [
                'key' => 'smtp_password',
                'value' => null, // Don't store password in migration
                'type' => 'password',
                'group' => 'smtp',
                'description' => 'SMTP password or App Password',
                'is_encrypted' => true,
                'created_at' => now(),
                'updated_at' => now(),
            ],
            [
                'key' => 'smtp_encryption',
                'value' => config('mail.mailers.smtp.encryption'),
                'type' => 'select',
                'group' => 'smtp',
                'description' => 'Encryption method (tls or ssl)',
                'is_encrypted' => false,
                'created_at' => now(),
                'updated_at' => now(),
            ],
            [
                'key' => 'mail_from_address',
                'value' => config('mail.from.address'),
                'type' => 'email',
                'group' => 'smtp',
                'description' => 'Email address shown as sender',
                'is_encrypted' => false,
                'created_at' => now(),
                'updated_at' => now(),
            ],
            [
                'key' => 'mail_from_name',
                'value' => config('mail.from.name'),
                'type' => 'text',
                'group' => 'smtp',
                'description' => 'Name shown as sender',
                'is_encrypted' => false,
                'created_at' => now(),
                'updated_at' => now(),
            ],
        ]);
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('email_settings');
    }
};
