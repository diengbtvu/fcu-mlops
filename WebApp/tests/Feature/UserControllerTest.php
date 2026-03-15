<?php

namespace Tests\Feature;

use Tests\TestCase;
use App\Models\User;
use App\Models\Role;
use App\Models\MLModel;
use App\Models\Prediction;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Facades\Http;

class UserControllerTest extends TestCase
{
    use RefreshDatabase;

    protected $user;
    protected $admin;

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
            'ml_model_id' => $modelId,
        ], $overrides);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function user_can_access_dashboard()
    {
        Prediction::factory()->count(3)->create(['user_id' => $this->user->id]);

        $response = $this->actingAs($this->user)->get(route('user.dashboard'));

        $response->assertStatus(200);
        $response->assertViewIs('user.dashboard');
        $response->assertViewHas(['totalPredictions', 'recentPredictions']);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function admin_cannot_access_user_dashboard()
    {
        $response = $this->actingAs($this->admin)->get(route('user.dashboard'));

        $response->assertStatus(403);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function guest_cannot_access_user_dashboard()
    {
        $response = $this->get(route('user.dashboard'));

        $response->assertRedirect(route('login'));
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function user_can_view_prediction_form()
    {
        MLModel::factory()->create(['IsActive' => true]);

        $response = $this->actingAs($this->user)->get(route('user.predict'));

        $response->assertStatus(200);
        $response->assertViewIs('user.predict');
        $response->assertViewHas('models');
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function user_can_make_prediction_with_valid_data()
    {
        Http::fake([
            '*/predict/health' => Http::response(['status' => 'healthy'], 200),
            '*/predict/mlflow' => Http::response(['prediction' => 0.758, 'unit' => 'L/h/L'], 200),
        ]);

        $model = MLModel::factory()->create([
            'IsActive' => true,
            'mlflow_run_id' => 'run_user_test_001',
        ]);
        $predictionData = $this->validPredictionData($model->id);

        $response = $this->actingAs($this->user)->postJson(route('user.predict.make'), $predictionData);

        $response->assertStatus(200);
        $response->assertJson(['success' => true]);
        $this->assertDatabaseHas('predictions', [
            'user_id' => $this->user->id,
            'ml_model_id' => $model->id,
            'pH' => 6.5,
            'VSS' => 3500,
            'Ethanol' => 12.0,
            'Acetate' => 25.0,
            'Propionate' => 8.0,
            'Butyrate' => 35.0,
            'Sucrose_Degradation' => 72.0,
            'ORP_Mid' => -180.0,
            'ORP_Low' => -220.0,
            'VFA' => 90.0,
            'COD_O' => 12000.0,
            'HPR' => 0.758,
        ]);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function user_prediction_validation_fails_with_invalid_data()
    {
        $invalidData = $this->validPredictionData(999, [
            'ph' => 'invalid',
            'vss' => -10,
            'cod_o' => '',
            'ml_model_id' => 'invalid',
        ]);

        $response = $this->actingAs($this->user)->postJson(route('user.predict.make'), $invalidData);

        $response->assertStatus(422);
        $response->assertJsonValidationErrors([
            'ph',
            'vss',
            'cod_o',
            'ml_model_id'
        ]);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function user_cannot_make_prediction_with_inactive_model()
    {
        $model = MLModel::factory()->create(['IsActive' => false]);
        $predictionData = $this->validPredictionData($model->id);

        $response = $this->actingAs($this->user)->postJson(route('user.predict.make'), $predictionData);

        $response->assertStatus(400);
        $response->assertJson(['success' => false]);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function user_prediction_fails_when_api_service_unavailable()
    {
        Http::fake([
            '*/predict/health' => Http::response([], 503),
        ]);

        $model = MLModel::factory()->create(['IsActive' => true]);
        $predictionData = $this->validPredictionData($model->id);

        $response = $this->actingAs($this->user)->postJson(route('user.predict.make'), $predictionData);

        $response->assertStatus(503);
        $response->assertJson(['success' => false]);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function user_can_view_prediction_history()
    {
        $model = MLModel::factory()->create();
        Prediction::factory()->count(5)->create([
            'user_id' => $this->user->id,
            'ml_model_id' => $model->id
        ]);

        $response = $this->actingAs($this->user)->get(route('user.history'));

        $response->assertStatus(200);
        $response->assertViewIs('user.history');
        $response->assertViewHas('predictions');
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function user_only_sees_their_own_predictions_in_history()
    {
        $otherUser = User::factory()->create(['role_id' => 2]);
        $model = MLModel::factory()->create();
        
        // Create predictions for current user
        Prediction::factory()->count(3)->create([
            'user_id' => $this->user->id,
            'ml_model_id' => $model->id
        ]);
        
        // Create predictions for other user
        Prediction::factory()->count(2)->create([
            'user_id' => $otherUser->id,
            'ml_model_id' => $model->id
        ]);

        $response = $this->actingAs($this->user)->get(route('user.history'));

        $response->assertStatus(200);
        $predictions = $response->viewData('predictions');
        
        // Should only see their own predictions
        $this->assertEquals(3, $predictions->total());
        foreach ($predictions as $prediction) {
            $this->assertEquals($this->user->id, $prediction->user_id);
        }
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function user_can_view_profile()
    {
        $response = $this->actingAs($this->user)->get(route('user.profile'));

        $response->assertStatus(200);
        $response->assertViewIs('user.profile');
        $response->assertViewHas('user', $this->user);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function user_can_update_profile()
    {
        $updateData = [
            'FullName' => 'Updated Full Name',
            'Gender' => 'Female',
            'BirthDate' => '1995-06-15',
            'Address' => 'Updated Address',
            'Username' => 'updatedusername123'
        ];

        $response = $this->actingAs($this->user)->put(route('user.profile.update'), $updateData);

        $response->assertRedirect(route('user.profile'));
        $response->assertSessionHas('success');
        $this->assertDatabaseHas('users', [
            'id' => $this->user->id,
            'FullName' => 'Updated Full Name',
            'Gender' => 'Female',
            'Address' => 'Updated Address',
            'Username' => 'updatedusername123',
        ]);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function user_profile_update_validation_fails_with_invalid_data()
    {
        $invalidData = [
            'FullName' => '', // required
            'Gender' => 'Other', // not in enum
            'BirthDate' => 'invalid-date',
            'Address' => str_repeat('a', 300), // too long
            'Username' => '' // required
        ];

        $response = $this->actingAs($this->user)->put(route('user.profile.update'), $invalidData);

        $response->assertSessionHasErrors([
            'FullName',
            'Gender',
            'BirthDate',
            'Address',
            'Username'
        ]);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function user_cannot_update_profile_with_existing_username()
    {
        $existingUser = User::factory()->create(['Username' => 'existingusername']);
        
        $updateData = [
            'FullName' => 'Updated Name',
            'Gender' => 'Male',
            'BirthDate' => '1990-01-01',
            'Address' => 'Updated Address',
            'Username' => 'existingusername'
        ];

        $response = $this->actingAs($this->user)->put(route('user.profile.update'), $updateData);

        $response->assertSessionHasErrors(['Username']);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function user_can_view_security_page()
    {
        $response = $this->actingAs($this->user)->get(route('user.security'));

        $response->assertStatus(200);
        $response->assertViewIs('user.security');
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function user_can_change_password_with_correct_current_password()
    {
        $this->user->update(['Password' => Hash::make('currentpassword')]);
        
        $passwordData = [
            'current_password' => 'currentpassword',
            'new_password' => 'newpassword123',
            'new_password_confirmation' => 'newpassword123'
        ];

        $response = $this->actingAs($this->user)->post(route('user.security.change-password'), $passwordData);

        $response->assertRedirect(route('user.security'));
        $response->assertSessionHas('success');
        
        $this->user->refresh();
        $this->assertTrue(Hash::check('newpassword123', $this->user->Password));
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function user_cannot_change_password_with_incorrect_current_password()
    {
        $this->user->update(['Password' => Hash::make('currentpassword')]);
        
        $passwordData = [
            'current_password' => 'wrongpassword',
            'new_password' => 'newpassword123',
            'new_password_confirmation' => 'newpassword123'
        ];

        $response = $this->actingAs($this->user)->post(route('user.security.change-password'), $passwordData);

        $response->assertSessionHasErrors(['current_password']);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function user_password_change_validation_fails_with_invalid_data()
    {
        $invalidData = [
            'current_password' => '', // required
            'new_password' => '123', // too short
            'new_password_confirmation' => 'different' // doesn't match
        ];

        $response = $this->actingAs($this->user)->post(route('user.security.change-password'), $invalidData);

        $response->assertSessionHasErrors([
            'current_password',
            'new_password'
        ]);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function user_dashboard_shows_correct_statistics()
    {
        $model = MLModel::factory()->create();
        
        // Create 5 predictions for the user
        Prediction::factory()->count(5)->create([
            'user_id' => $this->user->id,
            'ml_model_id' => $model->id
        ]);
        
        // Create predictions for another user (should not be counted)
        $otherUser = User::factory()->create(['role_id' => 2]);
        Prediction::factory()->count(3)->create([
            'user_id' => $otherUser->id,
            'ml_model_id' => $model->id
        ]);

        $response = $this->actingAs($this->user)->get(route('user.dashboard'));

        $response->assertStatus(200);
        $totalPredictions = $response->viewData('totalPredictions');
        $recentPredictions = $response->viewData('recentPredictions');
        
        $this->assertEquals(5, $totalPredictions);
        $this->assertCount(5, $recentPredictions);
        
        // Verify all predictions belong to the user
        foreach ($recentPredictions as $prediction) {
            $this->assertEquals($this->user->id, $prediction->user_id);
        }
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function user_dashboard_limits_recent_predictions_to_5()
    {
        $model = MLModel::factory()->create();
        
        // Create 10 predictions for the user
        Prediction::factory()->count(10)->create([
            'user_id' => $this->user->id,
            'ml_model_id' => $model->id
        ]);

        $response = $this->actingAs($this->user)->get(route('user.dashboard'));

        $response->assertStatus(200);
        $totalPredictions = $response->viewData('totalPredictions');
        $recentPredictions = $response->viewData('recentPredictions');
        
        $this->assertEquals(10, $totalPredictions);
        $this->assertCount(5, $recentPredictions); // Should be limited to 5
    }
}
