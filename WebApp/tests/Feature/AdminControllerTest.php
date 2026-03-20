<?php

namespace Tests\Feature;

use Tests\TestCase;
use App\Models\User;
use App\Models\Role;
use App\Models\MLModel;
use App\Models\Prediction;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\UploadedFile;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Facades\Http;

class AdminControllerTest extends TestCase
{
    use RefreshDatabase;

    protected $admin;
    protected $user;

    protected function setUp(): void
    {
        parent::setUp();
        
        // Create roles
        Role::create(['RoleCode' => 'admin', 'RoleName' => 'Administrator']);
        Role::create(['RoleCode' => 'user', 'RoleName' => 'User']);
        
        // Create users
        $this->admin = User::factory()->create(['role_id' => 1]);
        $this->user = User::factory()->create(['role_id' => 2]);
    }

    private function validPredictionData(int $modelId, array $overrides = []): array
    {
        return array_merge([
            'ph' => 5.8,
            'vss' => 2.36,
            'ethanol' => 1739.25,
            'acetate' => 925.5,
            'propionate' => 1100.0,
            'butyrate' => 10.6,
            'sucrose_degradation' => 91.68,
            'orp_mid' => -226.67,
            'orp_low' => -481.0,
            'vfa' => 3723.5,
            'cod_o' => 11.52,
            'ml_model_id' => $modelId,
        ], $overrides);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function admin_can_access_dashboard()
    {
        $response = $this->actingAs($this->admin)->get(route('admin.dashboard'));

        $response->assertStatus(200);
        $response->assertViewIs('admin.dashboard');
        $response->assertViewHas(['totalUsers', 'totalModels', 'activeModels', 'adminPredictions']);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function non_admin_cannot_access_admin_dashboard()
    {
        $response = $this->actingAs($this->user)->get(route('admin.dashboard'));

        $response->assertStatus(403);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function guest_cannot_access_admin_dashboard()
    {
        $response = $this->get(route('admin.dashboard'));

        $response->assertRedirect(route('login'));
    }

    // User Management Tests
    #[\PHPUnit\Framework\Attributes\Test]
    public function admin_can_view_users_list()
    {
        User::factory()->count(3)->create(['role_id' => 2]);

        $response = $this->actingAs($this->admin)->get(route('admin.users'));

        $response->assertStatus(200);
        $response->assertViewIs('admin.users.index');
        $response->assertViewHas('users');
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function admin_can_view_create_user_form()
    {
        $response = $this->actingAs($this->admin)->get(route('admin.users.create'));

        $response->assertStatus(200);
        $response->assertViewIs('admin.users.create');
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function admin_can_create_new_user()
    {
        $userData = [
            'FullName' => 'Test User',
            'Gender' => 'Male',
            'BirthDate' => '1990-01-01',
            'Address' => 'Test Address',
            'Username' => 'testuser123',
            'Password' => 'password123'
        ];

        $response = $this->actingAs($this->admin)->post(route('admin.users.store'), $userData);

        $response->assertRedirect(route('admin.users'));
        $response->assertSessionHas('success');
        $this->assertDatabaseHas('users', [
            'FullName' => 'Test User',
            'Username' => 'testuser123',
            'role_id' => 2
        ]);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function admin_cannot_create_user_with_duplicate_username()
    {
        User::factory()->create(['Username' => 'existinguser']);

        $userData = [
            'FullName' => 'Test User',
            'Gender' => 'Male',
            'BirthDate' => '1990-01-01',
            'Address' => 'Test Address',
            'Username' => 'existinguser',
            'Password' => 'password123'
        ];

        $response = $this->actingAs($this->admin)->post(route('admin.users.store'), $userData);

        $response->assertSessionHasErrors(['Username']);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function admin_can_view_edit_user_form()
    {
        $user = User::factory()->create(['role_id' => 2]);

        $response = $this->actingAs($this->admin)->get(route('admin.users.edit', $user));

        $response->assertStatus(200);
        $response->assertViewIs('admin.users.edit');
        $response->assertViewHas('user', $user);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function admin_can_view_edit_form_for_admin_user()
    {
        $anotherAdmin = User::factory()->create(['role_id' => 1]);

        $response = $this->actingAs($this->admin)->get(route('admin.users.edit', $anotherAdmin));

        $response->assertStatus(200);
        $response->assertViewIs('admin.users.edit');
        $response->assertViewHas('user', $anotherAdmin);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function admin_can_update_user()
    {
        $user = User::factory()->create(['role_id' => 2]);
        
        $updateData = [
            'FullName' => 'Updated Name',
            'Gender' => 'Female',
            'BirthDate' => '1995-05-05',
            'Address' => 'Updated Address',
            'Username' => 'updatedusername',
            'role_id' => 2,
        ];

        $response = $this->actingAs($this->admin)->put(route('admin.users.update', $user), $updateData);

        $response->assertRedirect(route('admin.users'));
        $response->assertSessionHas('success');
        $this->assertDatabaseHas('users', [
            'id' => $user->id,
            'FullName' => 'Updated Name',
            'Gender' => 'Female',
            'Address' => 'Updated Address',
            'Username' => 'updatedusername',
            'role_id' => 2,
        ]);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function admin_can_reset_user_password()
    {
        $user = User::factory()->create(['role_id' => 2]);
        $originalPassword = $user->Password;

        $response = $this->actingAs($this->admin)->post(route('admin.users.reset-password', $user));

        $response->assertRedirect(route('admin.users'));
        $response->assertSessionHas('success');
        $user->refresh();
        $this->assertNotEquals($originalPassword, $user->Password);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function admin_can_delete_user_without_predictions()
    {
        $user = User::factory()->create(['role_id' => 2]);

        $response = $this->actingAs($this->admin)->delete(route('admin.users.delete', $user));

        $response->assertRedirect(route('admin.users'));
        $response->assertSessionHas('success');
        $this->assertDatabaseMissing('users', ['id' => $user->id]);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function admin_cannot_delete_user_with_predictions()
    {
        $user = User::factory()->create(['role_id' => 2]);
        $model = MLModel::factory()->create();
        Prediction::factory()->create(['user_id' => $user->id, 'ml_model_id' => $model->id]);

        $response = $this->actingAs($this->admin)->delete(route('admin.users.delete', $user));

        $response->assertRedirect(route('admin.users'));
        $response->assertSessionHas('error');
        $this->assertDatabaseHas('users', ['id' => $user->id]);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function admin_can_force_delete_user_with_predictions()
    {
        $user = User::factory()->create(['role_id' => 2]);
        $model = MLModel::factory()->create();
        Prediction::factory()->create(['user_id' => $user->id, 'ml_model_id' => $model->id]);

        $response = $this->actingAs($this->admin)->delete(route('admin.users.force-delete', $user));

        $response->assertRedirect(route('admin.users'));
        $response->assertSessionHas('success');
        $this->assertDatabaseMissing('users', ['id' => $user->id]);
        $this->assertDatabaseMissing('predictions', ['user_id' => $user->id]);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function admin_can_anonymize_user()
    {
        $user = User::factory()->create(['role_id' => 2, 'FullName' => 'Original Name']);
        
        $response = $this->actingAs($this->admin)->post(route('admin.users.anonymize', $user));

        $response->assertRedirect(route('admin.users'));
        $response->assertSessionHas('success');
        $user->refresh();
        $this->assertEquals('Anonymous User', $user->FullName);
        $this->assertStringStartsWith('anon_', $user->Username);
    }

    // ML Model Management Tests
    #[\PHPUnit\Framework\Attributes\Test]
    public function admin_can_view_models_list()
    {
        MLModel::factory()->count(3)->create();

        $response = $this->actingAs($this->admin)->get(route('admin.models'));

        $response->assertStatus(200);
        $response->assertViewIs('admin.models.index');
        $response->assertViewHas('models');
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function admin_can_view_model_training_report_page()
    {
        Http::fake([
            '*/train/reports/*/summary.json' => Http::response([
                'selected_model_metrics' => [
                    'r2_score' => 0.91,
                    'rmse' => 0.05,
                    'mse' => 0.0025,
                    'mae' => 0.03,
                ],
                'files' => [
                    'summary' => 'summary.json',
                    'model_comparison_bars' => 'fig_model_comparison_bars.png',
                ],
                'benchmark_models' => [
                    ['model' => 'RF', 'r2_score' => 0.91, 'rmse' => 0.05, 'mse' => 0.0025, 'mae' => 0.03],
                ],
            ], 200),
        ]);

        $model = MLModel::factory()->create([
            'training_report' => [
                'report_id' => 'rf_test_20260314',
                'route_prefix' => '/train/reports/rf_test_20260314',
                'files' => [
                    'summary' => 'summary.json',
                    'model_comparison_bars' => 'fig_model_comparison_bars.png',
                ],
            ],
        ]);

        $response = $this->actingAs($this->admin)->get(route('admin.models.report', $model));

        $response->assertStatus(200);
        $response->assertViewIs('admin.models.report');
        $response->assertViewHas('model', $model);
        $response->assertViewHas('reportAssets');
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function admin_can_view_create_model_form()
    {
        $response = $this->actingAs($this->admin)->get(route('admin.models.create'));

        $response->assertStatus(200);
        $response->assertViewIs('admin.models.create');
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function admin_can_create_model_with_valid_file()
    {
        Storage::fake('public');
        
        $file = UploadedFile::fake()->create('test_model.h5', 100, 'application/octet-stream');
        
        $modelData = [
            'MLMName' => 'Test Model',
            'model_file' => $file,
            'LibType' => 'keras',
            'IsActive' => '1',
            'MSEValue' => 0.11,
            'MAEValue' => 0.07,
        ];

        $response = $this->actingAs($this->admin)->post(route('admin.models.store'), $modelData);

        $response->assertRedirect(route('admin.models'));
        $response->assertSessionHas('success');
        $this->assertDatabaseHas('ml_models', [
            'MLMName' => 'Test Model',
            'LibType' => 'keras',
            'IsActive' => true
        ]);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function admin_cannot_create_model_without_file()
    {
        $modelData = [
            'MLMName' => 'Test Model',
            'LibType' => 'keras'
        ];

        $response = $this->actingAs($this->admin)->post(route('admin.models.store'), $modelData);

        $response->assertSessionHasErrors(['model_file']);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function admin_can_view_edit_model_form()
    {
        $model = MLModel::factory()->create();

        $response = $this->actingAs($this->admin)->get(route('admin.models.edit', $model));

        $response->assertStatus(200);
        $response->assertViewIs('admin.models.edit');
        $response->assertViewHas('model', $model);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function admin_can_update_model()
    {
        $model = MLModel::factory()->create();
        
        $updateData = [
            'MLMName' => 'Updated Model Name',
            'LibType' => 'pytorch',
            'IsActive' => '1',
            'MSEValue' => 0.12,
            'MAEValue' => 0.08,
        ];

        $response = $this->actingAs($this->admin)->put(route('admin.models.update', $model), $updateData);

        $response->assertRedirect(route('admin.models'));
        $response->assertSessionHas('success');
        $this->assertDatabaseHas('ml_models', [
            'id' => $model->id,
            'MLMName' => 'Updated Model Name',
            'LibType' => 'pytorch'
        ]);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function admin_can_delete_model_without_predictions()
    {
        MLModel::factory()->create([
            'MLMName' => 'Hydrogen RF Baseline',
            'FilePath' => 'models/hydrogen_rf_baseline.pkl',
            'IsActive' => true,
        ]);

        $model = MLModel::factory()->create(['MLMName' => 'Test Model']);

        $response = $this->actingAs($this->admin)->delete(route('admin.models.delete', $model));

        $response->assertRedirect(route('admin.models'));
        $response->assertSessionHas('success');
        $this->assertDatabaseMissing('ml_models', ['id' => $model->id]);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function admin_cannot_delete_model_with_predictions()
    {
        $model = MLModel::factory()->create();
        Prediction::factory()->create(['ml_model_id' => $model->id]);

        $response = $this->actingAs($this->admin)->delete(route('admin.models.delete', $model));

        $response->assertRedirect(route('admin.models'));
        $response->assertSessionHas('error');
        $this->assertDatabaseHas('ml_models', ['id' => $model->id]);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function admin_can_view_prediction_form()
    {
        MLModel::factory()->create(['IsActive' => true]);

        $response = $this->actingAs($this->admin)->get(route('admin.predict'));

        $response->assertStatus(200);
        $response->assertViewIs('admin.predict');
        $response->assertViewHas('models');
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function admin_can_make_prediction_with_valid_data()
    {
        Http::fake([
            '*/predict/health' => Http::response(['status' => 'healthy'], 200),
            '*/predict/mlflow' => Http::response(['prediction' => 0.855, 'unit' => 'L/h/L'], 200),
        ]);

        $model = MLModel::factory()->create([
            'IsActive' => true,
            'mlflow_run_id' => 'run_admin_test_001',
        ]);
        $predictionData = $this->validPredictionData($model->id);

        $response = $this->actingAs($this->admin)->postJson(route('admin.predict.make'), $predictionData);

        $response->assertStatus(200);
        $response->assertJson(['success' => true]);
        $this->assertDatabaseHas('predictions', [
            'user_id' => $this->admin->id,
            'ml_model_id' => $model->id,
            'pH' => 5.8,
            'HPR' => 0.855,
        ]);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function admin_can_view_prediction_history()
    {
        $model = MLModel::factory()->create();
        Prediction::factory()->count(3)->create([
            'user_id' => $this->admin->id,
            'ml_model_id' => $model->id
        ]);

        $response = $this->actingAs($this->admin)->get(route('admin.history'));

        $response->assertStatus(200);
        $response->assertViewIs('admin.history');
        $response->assertViewHas('predictions');
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function admin_prediction_validation_fails_with_invalid_data()
    {
        $invalidData = $this->validPredictionData(999, [
            'ph' => -0.1,
            'vss' => -10,
            'cod_o' => 999999,
        ]);

        $response = $this->actingAs($this->admin)->postJson(route('admin.predict.make'), $invalidData);

        $response->assertStatus(422);
        $response->assertJsonValidationErrors([
            'ph',
            'vss',
            'cod_o',
            'ml_model_id'
        ]);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function admin_cannot_make_prediction_with_inactive_model()
    {
        $model = MLModel::factory()->create(['IsActive' => false]);
        $predictionData = $this->validPredictionData($model->id);

        $response = $this->actingAs($this->admin)->postJson(route('admin.predict.make'), $predictionData);

        $response->assertStatus(400);
        $response->assertJson(['success' => false]);
    }
}
