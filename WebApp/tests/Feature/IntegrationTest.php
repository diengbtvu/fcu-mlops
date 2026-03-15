<?php

namespace Tests\Feature;

use Tests\TestCase;
use App\Models\User;
use App\Models\Role;
use App\Models\MLModel;
use App\Models\Prediction;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Storage;
use Illuminate\Http\UploadedFile;
use Illuminate\Database\QueryException;

class IntegrationTest extends TestCase
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

    private function validFeatureData(array $overrides = []): array
    {
        return array_merge([
            'ph' => 6.5,
            'vss' => 3500,
            'ethanol' => 12.0,
            'acetate' => 25.0,
            'propionate' => 8.0,
            'butyrate' => 35.0,
            'sucrose_degradation' => 72.0,
            'orp_mid' => -180.0,
            'orp_low' => -220.0,
            'vfa' => 90.0,
            'cod_o' => 12000.0,
        ], $overrides);
    }

    private function validPredictionData(int $modelId, array $overrides = []): array
    {
        return array_merge($this->validFeatureData(), ['ml_model_id' => $modelId], $overrides);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function complete_admin_workflow_for_user_management()
    {
        // 1. Admin logs in
        $loginResponse = $this->post(route('login'), [
            'username' => $this->admin->Username,
            'password' => 'password',
        ]);
        $loginResponse->assertRedirect(route('admin.dashboard'));

        // 2. Admin views dashboard
        $dashboardResponse = $this->actingAs($this->admin)->get(route('admin.dashboard'));
        $dashboardResponse->assertStatus(200);
        $dashboardResponse->assertViewHas(['totalUsers', 'totalModels', 'activeModels', 'adminPredictions']);

        // 3. Admin views users list
        $usersResponse = $this->actingAs($this->admin)->get(route('admin.users'));
        $usersResponse->assertStatus(200);
        $usersResponse->assertViewHas('users');

        // 4. Admin creates a new user
        $userData = [
            'FullName' => 'Integration Test User',
            'Gender' => 'Female',
            'BirthDate' => '1992-03-15',
            'Address' => 'Test Address 123',
            'Username' => 'integrationuser',
            'Password' => 'password123'
        ];

        $createResponse = $this->actingAs($this->admin)->post(route('admin.users.store'), $userData);
        $createResponse->assertRedirect(route('admin.users'));
        $createResponse->assertSessionHas('success');

        // Verify user was created
        $this->assertDatabaseHas('users', [
            'FullName' => 'Integration Test User',
            'Username' => 'integrationuser',
            'role_id' => 2
        ]);

        $createdUser = User::where('Username', 'integrationuser')->first();

        // 5. Admin edits the user
        $editResponse = $this->actingAs($this->admin)->get(route('admin.users.edit', $createdUser));
        $editResponse->assertStatus(200);
        $editResponse->assertViewHas('user', $createdUser);

        $updateData = [
            'FullName' => 'Updated Integration User',
            'Gender' => 'Female',
            'BirthDate' => '1992-03-15',
            'Address' => 'Updated Address 456',
            'Username' => 'updatedintegrationuser',
            'role_id' => 2,
        ];

        $updateResponse = $this->actingAs($this->admin)->put(route('admin.users.update', $createdUser), $updateData);
        $updateResponse->assertRedirect(route('admin.users'));
        $updateResponse->assertSessionHas('success');

        // 6. Admin resets user password
        $resetResponse = $this->actingAs($this->admin)->post(route('admin.users.reset-password', $createdUser));
        $resetResponse->assertRedirect(route('admin.users'));
        $resetResponse->assertSessionHas('success');

        // 7. Admin deletes the user
        $deleteResponse = $this->actingAs($this->admin)->delete(route('admin.users.delete', $createdUser));
        $deleteResponse->assertRedirect(route('admin.users'));
        $deleteResponse->assertSessionHas('success');
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function complete_admin_workflow_for_model_management()
    {
        Storage::fake('public');

        // Create an undeletable default model first so integration model is deletable.
        MLModel::factory()->create([
            'MLMName' => 'Hydrogen RF Baseline',
            'FilePath' => 'models/hydrogen_rf_baseline.pkl',
            'IsActive' => true,
        ]);

        // 1. Admin views models list
        $modelsResponse = $this->actingAs($this->admin)->get(route('admin.models'));
        $modelsResponse->assertStatus(200);
        $modelsResponse->assertViewHas('models');

        // 2. Admin creates a new model
        $file = UploadedFile::fake()->create('test_integration_model.h5', 1000);
        
        $modelData = [
            'MLMName' => 'Integration Test Model',
            'model_file' => $file,
            'LibType' => 'keras',
            'IsActive' => '1',
            'MSEValue' => 0.21,
            'MAEValue' => 0.12,
        ];

        $createResponse = $this->actingAs($this->admin)->post(route('admin.models.store'), $modelData);
        $createResponse->assertRedirect(route('admin.models'));
        $createResponse->assertSessionHas('success');

        // Verify model was created
        $this->assertDatabaseHas('ml_models', [
            'MLMName' => 'Integration Test Model',
            'LibType' => 'keras',
            'IsActive' => true
        ]);

        $createdModel = MLModel::where('MLMName', 'Integration Test Model')->first();

        // 3. Admin edits the model
        $editResponse = $this->actingAs($this->admin)->get(route('admin.models.edit', $createdModel));
        $editResponse->assertStatus(200);
        $editResponse->assertViewHas('model', $createdModel);

        $updateData = [
            'MLMName' => 'Updated Integration Model',
            'LibType' => 'keras',
            'IsActive' => '1',
            'MSEValue' => 0.19,
            'MAEValue' => 0.11,
        ];

        $updateResponse = $this->actingAs($this->admin)->put(route('admin.models.update', $createdModel), $updateData);
        $updateResponse->assertRedirect(route('admin.models'));
        $updateResponse->assertSessionHas('success');

        // 4. Admin tests the model
        Http::fake([
            '*/predict/health' => Http::response(['status' => 'healthy'], 200),
            '*/predict/model' => Http::response(['prediction' => 78.5, 'model_used' => 'Integration Test Model'], 200),
        ]);

        $testData = $this->validFeatureData([
            'ph' => 6.2,
            'vss' => 3200,
        ]);

        $testResponse = $this->actingAs($this->admin)->postJson(route('admin.models.test', $createdModel), $testData);
        $testResponse->assertStatus(200);
        $testResponse->assertJson(['success' => true]);

        // 5. Admin deletes the model
        $deleteResponse = $this->actingAs($this->admin)->delete(route('admin.models.delete', $createdModel));
        $deleteResponse->assertRedirect(route('admin.models'));
        $deleteResponse->assertSessionHas('success');
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function complete_user_workflow_for_predictions()
    {
        // Setup: Create a model for predictions
        $model = MLModel::factory()->active()->create([
            'mlflow_run_id' => 'run_user_flow_001',
        ]);

        // 1. User logs in
        $loginResponse = $this->post(route('login'), [
            'username' => $this->user->Username,
            'password' => 'password',
        ]);
        $loginResponse->assertRedirect(route('user.dashboard'));

        // 2. User views dashboard
        $dashboardResponse = $this->actingAs($this->user)->get(route('user.dashboard'));
        $dashboardResponse->assertStatus(200);
        $dashboardResponse->assertViewHas(['totalPredictions', 'recentPredictions']);

        // 3. User views prediction form
        $predictResponse = $this->actingAs($this->user)->get(route('user.predict'));
        $predictResponse->assertStatus(200);
        $predictResponse->assertViewHas('models');

        // 4. User makes a prediction
        Http::fake([
            '*/predict/health' => Http::response(['status' => 'healthy'], 200),
            '*/predict/mlflow' => Http::response(['prediction' => 0.852, 'unit' => 'L/h/L'], 200),
        ]);

        $predictionData = $this->validPredictionData($model->id, [
            'ph' => 6.3,
            'vss' => 3300,
        ]);

        $makePredictionResponse = $this->actingAs($this->user)->postJson(route('user.predict.make'), $predictionData);
        $makePredictionResponse->assertStatus(200);
        $makePredictionResponse->assertJson(['success' => true]);

        // Verify prediction was saved
        $this->assertDatabaseHas('predictions', [
            'user_id' => $this->user->id,
            'ml_model_id' => $model->id,
            'pH' => 6.3,
            'VSS' => 3300,
            'HPR' => 0.852
        ]);

        // 5. User views prediction history
        $historyResponse = $this->actingAs($this->user)->get(route('user.history'));
        $historyResponse->assertStatus(200);
        $historyResponse->assertViewHas('predictions');

        // 6. User views profile
        $profileResponse = $this->actingAs($this->user)->get(route('user.profile'));
        $profileResponse->assertStatus(200);
        $profileResponse->assertViewHas('user', $this->user);

        // 7. User updates profile
        $profileUpdateData = [
            'FullName' => 'Updated User Name',
            'Gender' => $this->user->Gender,
            'BirthDate' => $this->user->BirthDate->format('Y-m-d'),
            'Address' => 'Updated User Address',
            'Username' => 'updatedusername'
        ];

        $updateProfileResponse = $this->actingAs($this->user)->put(route('user.profile.update'), $profileUpdateData);
        $updateProfileResponse->assertRedirect(route('user.profile'));
        $updateProfileResponse->assertSessionHas('success');

        // 8. User changes password
        $passwordChangeData = [
            'current_password' => 'password',
            'new_password' => 'newpassword123',
            'new_password_confirmation' => 'newpassword123'
        ];

        $changePasswordResponse = $this->actingAs($this->user)->post(route('user.security.change-password'), $passwordChangeData);
        $changePasswordResponse->assertRedirect(route('user.security'));
        $changePasswordResponse->assertSessionHas('success');
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function complete_admin_prediction_workflow()
    {
        // Setup: Create a model for predictions
        $model = MLModel::factory()->active()->create([
            'mlflow_run_id' => 'run_admin_flow_001',
        ]);

        Http::fake([
            '*/predict/health' => Http::response(['status' => 'healthy'], 200),
            '*/predict/mlflow' => Http::response(['prediction' => 0.927, 'unit' => 'L/h/L'], 200),
        ]);

        // 1. Admin views prediction form
        $predictResponse = $this->actingAs($this->admin)->get(route('admin.predict'));
        $predictResponse->assertStatus(200);
        $predictResponse->assertViewHas('models');

        // 2. Admin makes a prediction
        $predictionData = $this->validPredictionData($model->id, [
            'ph' => 6.8,
            'vss' => 3800,
        ]);

        $makePredictionResponse = $this->actingAs($this->admin)->postJson(route('admin.predict.make'), $predictionData);
        $makePredictionResponse->assertStatus(200);
        $makePredictionResponse->assertJson(['success' => true]);

        // 3. Admin views prediction history
        $historyResponse = $this->actingAs($this->admin)->get(route('admin.history'));
        $historyResponse->assertStatus(200);
        $historyResponse->assertViewHas('predictions');

        // Verify prediction was saved for admin
        $this->assertDatabaseHas('predictions', [
            'user_id' => $this->admin->id,
            'ml_model_id' => $model->id,
            'pH' => 6.8,
            'VSS' => 3800,
            'HPR' => 0.927
        ]);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function role_based_access_control_integration()
    {
        // 1. User tries to access admin routes - should be denied
        $adminRoutes = [
            'admin.dashboard',
            'admin.users',
            'admin.models'
        ];

        foreach ($adminRoutes as $route) {
            $response = $this->actingAs($this->user)->get(route($route));
            $response->assertStatus(403);
        }

        // 2. Admin tries to access user routes - should be denied
        $userRoutes = [
            'user.dashboard',
            'user.predict',
            'user.profile'
        ];

        foreach ($userRoutes as $route) {
            $response = $this->actingAs($this->admin)->get(route($route));
            $response->assertStatus(403);
        }

        // 3. Guest tries to access any protected route - should redirect to login
        $protectedRoutes = array_merge($adminRoutes, $userRoutes);
        auth()->logout();

        foreach ($protectedRoutes as $route) {
            $response = $this->get(route($route));
            $response->assertRedirect(route('login'));
        }
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function full_application_error_handling()
    {
        // 1. Test invalid login
        $invalidLoginResponse = $this->post(route('login'), [
            'username' => 'nonexistent',
            'password' => 'wrongpassword'
        ]);
        $invalidLoginResponse->assertRedirect();
        $invalidLoginResponse->assertSessionHasErrors(['username']);

        // 2. Test prediction with invalid data
        $model = MLModel::factory()->active()->create();
        
        $invalidPredictionData = $this->validPredictionData(999, [
            'ph' => -0.1,
            'vss' => -1,
            'ethanol' => '',
            'cod_o' => 'abc',
        ]);

        $invalidPredictionResponse = $this->actingAs($this->user)->postJson(route('user.predict.make'), $invalidPredictionData);
        $invalidPredictionResponse->assertStatus(422);
        $invalidPredictionResponse->assertJsonValidationErrors([
            'ph',
            'vss',
            'ethanol',
            'cod_o',
            'ml_model_id',
        ]);

        // 3. Test prediction with API service down
        Http::fake([
            '*/predict/health' => Http::response([], 503),
        ]);

        $validPredictionData = $this->validPredictionData($model->id);

        $apiDownResponse = $this->actingAs($this->user)->postJson(route('user.predict.make'), $validPredictionData);
        $apiDownResponse->assertStatus(503);
        $apiDownResponse->assertJson(['success' => false]);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function data_consistency_and_relationships()
    {
        // 1. Create related data
        $model = MLModel::factory()->active()->create();
        $prediction = Prediction::factory()->create([
            'user_id' => $this->user->id,
            'ml_model_id' => $model->id
        ]);

        // 2. Test relationships work correctly
        $this->assertEquals($this->user->id, $prediction->user->id);
        $this->assertEquals($model->id, $prediction->mlModel->id);
        $this->assertContains($prediction->id, $this->user->predictions->pluck('id'));
        $this->assertContains($prediction->id, $model->predictions->pluck('id'));

        // 3. Test cascade behaviors
        $predictionId = $prediction->id;
        
        // Delete user may be blocked by FK constraints depending on DB settings.
        try {
            $this->user->delete();
            $this->assertDatabaseMissing('users', ['id' => $this->user->id]);
        } catch (QueryException $e) {
            $this->assertDatabaseHas('users', ['id' => $this->user->id]);
            $this->assertDatabaseHas('predictions', ['id' => $predictionId]);
        }
    }
}
