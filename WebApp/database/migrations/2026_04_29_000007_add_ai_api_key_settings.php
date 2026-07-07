<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Support\Facades\DB;

return new class extends Migration
{
    public function up(): void
    {
        DB::table('email_settings')->updateOrInsert(
            ['key' => 'groq_api_keys'],
            [
                'value' => null,
                'type' => 'textarea',
                'group' => 'ai',
                'description' => 'Groq API key pool used by report explanations and benchmark evaluation',
                'is_encrypted' => true,
                'updated_at' => now(),
                'created_at' => now(),
            ]
        );
    }

    public function down(): void
    {
        DB::table('email_settings')->where('key', 'groq_api_keys')->delete();
    }
};
