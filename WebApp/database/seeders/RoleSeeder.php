<?php

namespace Database\Seeders;

use Illuminate\Database\Console\Seeds\WithoutModelEvents;
use Illuminate\Database\Seeder;
use App\Models\Role;

class RoleSeeder extends Seeder
{
    /**
     * Run the database seeds.
     */
    public function run(): void
    {
        // Role 1: Admin (unchanged)
        Role::firstOrCreate(
            ['RoleCode' => 'admin'],
            ['RoleName' => 'Administrator']
        );

        // Role 2: Default User (unchanged for backward compatibility)
        Role::firstOrCreate(
            ['RoleCode' => 'user'],
            ['RoleName' => 'User']
        );

        // Role 3: Permission Group 1 - Prediction User
        // Can: Make Predictions, View Predictions, View History
        Role::firstOrCreate(
            ['RoleCode' => 'prediction_user'],
            ['RoleName' => 'Prediction User']
        );

        // Role 4: Permission Group 2 - Dataset Manager
        // Can: Manage Datasets
        Role::firstOrCreate(
            ['RoleCode' => 'dataset_manager'],
            ['RoleName' => 'Dataset Manager']
        );

        // Role 5: Permission Group 3 - Model Trainer
        // Can: Manage Datasets, Train Models, Manage Models
        Role::firstOrCreate(
            ['RoleCode' => 'model_trainer'],
            ['RoleName' => 'Model Trainer']
        );
    }
}
