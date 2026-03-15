<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

/**
 * Add GRA (Grey Relational Analysis) ranking column to ml_models table.
 * Stores the feature importance ranking computed by GRA before training.
 */
return new class extends Migration
{
    public function up(): void
    {
        Schema::table('ml_models', function (Blueprint $table) {
            $table->json('gra_ranking')->nullable()
                ->comment('GRA feature ranking: [{"rank":1,"feature":"Sucrose_Degradation","score":0.9492}, ...]')
                ->after('mlflow_experiment_id');
        });
    }

    public function down(): void
    {
        Schema::table('ml_models', function (Blueprint $table) {
            $table->dropColumn('gra_ranking');
        });
    }
};
