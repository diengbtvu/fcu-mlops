<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Support\Facades\DB;

return new class extends Migration
{
    public function up(): void
    {
        DB::table('ml_models')
            ->whereIn('MLMName', [
                'Hydrogen RF Baseline',
                'Hydrogen XGBoost Baseline',
                'Hydrogen ANN Baseline',
            ])
            ->delete();
    }

    public function down(): void
    {
        // Baseline models were removed permanently.
    }
};
