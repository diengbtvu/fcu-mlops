<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        Schema::table('ml_models', function (Blueprint $table) {
            $table->json('training_report')
                ->nullable()
                ->after('gra_ranking')
                ->comment('Training report metadata from predict-service: report_id, route_prefix, files, generated_at');
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::table('ml_models', function (Blueprint $table) {
            $table->dropColumn('training_report');
        });
    }
};

