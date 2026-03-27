<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Support\Facades\DB;

return new class extends Migration
{
    public function up(): void
    {
        $baselineModelIds = DB::table('ml_models')
            ->whereIn('MLMName', [
                'Hydrogen RF Baseline',
                'Hydrogen XGBoost Baseline',
                'Hydrogen ANN Baseline',
            ])
            ->pluck('id');

        if ($baselineModelIds->isEmpty()) {
            return;
        }

        DB::table('predictions')
            ->whereIn('ml_model_id', $baselineModelIds)
            ->delete();

        DB::table('ml_models')
            ->whereIn('id', $baselineModelIds)
            ->delete();
    }

    public function down(): void
    {
        // Baseline models were removed permanently.
    }
};
