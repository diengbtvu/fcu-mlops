<?php

namespace Database\Seeders;

use Illuminate\Database\Console\Seeds\WithoutModelEvents;
use Illuminate\Database\Seeder;
use App\Models\Permission;
use App\Models\Role;

class PermissionSeeder extends Seeder
{
    /**
     * Run the database seeds.
     */
    public function run(): void
    {
        // Define all permissions
        $permissions = [
            [
                'name' => 'training_model',
                'description' => 'Can train machine learning models'
            ],
            [
                'name' => 'manage_dataset',
                'description' => 'Can upload, edit, delete datasets'
            ],
            [
                'name' => 'manage_users',
                'description' => 'Can manage user accounts'
            ],
            [
                'name' => 'manage_models',
                'description' => 'Can manage ML models'
            ],
            [
                'name' => 'view_predictions',
                'description' => 'Can view prediction results'
            ],
            [
                'name' => 'make_predictions',
                'description' => 'Can make predictions using models'
            ],
            [
                'name' => 'view_history',
                'description' => 'Can view prediction history'
            ],
            [
                'name' => 'manage_roles',
                'description' => 'Can manage roles and permissions'
            ],
        ];

        // Create permissions
        foreach ($permissions as $permission) {
            Permission::firstOrCreate(
                ['name' => $permission['name']],
                ['description' => $permission['description']]
            );
        }

        // Get roles
        $adminRole = Role::where('id', 1)->first(); // Admin
        $userRole = Role::where('id', 2)->first();  // Default User
        $predictionUserRole = Role::where('RoleCode', 'prediction_user')->first(); // Group 1
        $datasetManagerRole = Role::where('RoleCode', 'dataset_manager')->first(); // Group 2
        $modelTrainerRole = Role::where('RoleCode', 'model_trainer')->first(); // Group 3

        // Get all permissions
        $allPermissions = Permission::all();

        // Admin has all permissions
        if ($adminRole) {
            $adminRole->permissions()->sync($allPermissions->pluck('id'));
        }

        // Default User has limited permissions (backward compatibility)
        if ($userRole) {
            $userPermissions = Permission::whereIn('name', [
                'view_predictions',
                'make_predictions',
                'view_history'
            ])->pluck('id');
            
            $userRole->permissions()->sync($userPermissions);
        }

        // Group 1: Prediction User
        // Permissions: Make Predictions, View Predictions, View History
        if ($predictionUserRole) {
            $group1Permissions = Permission::whereIn('name', [
                'make_predictions',
                'view_predictions',
                'view_history'
            ])->pluck('id');
            
            $predictionUserRole->permissions()->sync($group1Permissions);
        }

        // Group 2: Dataset Manager
        // Permissions: Manage Datasets
        if ($datasetManagerRole) {
            $group2Permissions = Permission::whereIn('name', [
                'manage_dataset'
            ])->pluck('id');
            
            $datasetManagerRole->permissions()->sync($group2Permissions);
        }

        // Group 3: Model Trainer
        // Permissions: Manage Datasets, Train Models, Manage Models
        if ($modelTrainerRole) {
            $group3Permissions = Permission::whereIn('name', [
                'manage_dataset',
                'training_model',
                'manage_models'
            ])->pluck('id');
            
            $modelTrainerRole->permissions()->sync($group3Permissions);
        }
    }
}
