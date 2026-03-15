<?php

namespace Database\Seeders;

use Illuminate\Database\Console\Seeds\WithoutModelEvents;
use Illuminate\Database\Seeder;
use App\Models\MLModel;

class MLModelSeeder extends Seeder
{
    /**
     * Run the database seeds.
     */
    public function run(): void
    {
        // Seed baseline Hydrogen models only when table is empty.
        if (MLModel::count() == 0) {
            MLModel::create([
                'MLMName' => 'Hydrogen RF Baseline',
                'FilePath' => 'models/hydrogen_rf_baseline.pkl',
                'LibType' => 'sklearn',
                'IsActive' => true,
                'MSEValue' => 0.007804,
                'MAEValue' => 0.065474,
                'R2Value' => 0.865292,
                'RMSEValue' => 0.088340,
            ]);

            MLModel::create([
                'MLMName' => 'Hydrogen XGBoost Baseline',
                'FilePath' => 'models/hydrogen_xgb_baseline.json',
                'LibType' => 'xgboost',
                'IsActive' => true,
                'MSEValue' => 0.010000,
                'MAEValue' => 0.067809,
                'R2Value' => 0.827382,
                'RMSEValue' => 0.100000,
            ]);

            MLModel::create([
                'MLMName' => 'Hydrogen ANN Baseline',
                'FilePath' => 'models/hydrogen_ann_baseline.keras',
                'LibType' => 'keras',
                'IsActive' => true,
                'MSEValue' => 0.012309,
                'MAEValue' => 0.080522,
                'R2Value' => 0.787520,
                'RMSEValue' => 0.110948,
            ]);
        }
    }
}
