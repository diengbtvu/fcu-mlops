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
            $table->string('mlflow_run_id', 255)->nullable()->after('MAEValue');
            $table->string('mlflow_experiment_id', 255)->nullable()->after('mlflow_run_id');
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::table('ml_models', function (Blueprint $table) {
            $table->dropColumn(['mlflow_run_id', 'mlflow_experiment_id']);
        });
    }
};
