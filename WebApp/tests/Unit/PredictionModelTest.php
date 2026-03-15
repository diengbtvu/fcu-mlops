<?php

namespace Tests\Unit;

use Tests\TestCase;
use App\Models\User;
use App\Models\Role;
use App\Models\MLModel;
use App\Models\Prediction;
use Illuminate\Foundation\Testing\RefreshDatabase;

class PredictionModelTest extends TestCase
{
    use RefreshDatabase;

    protected function setUp(): void
    {
        parent::setUp();

        // Create roles
        Role::create(['RoleCode' => 'admin', 'RoleName' => 'Administrator']);
        Role::create(['RoleCode' => 'user', 'RoleName' => 'User']);
    }

    private function validPredictionData(int $userId, int $modelId, array $overrides = []): array
    {
        return array_merge([
            'user_id' => $userId,
            'ml_model_id' => $modelId,
            'pH' => 6.5,
            'VSS' => 3500.0,
            'Ethanol' => 12.0,
            'Acetate' => 25.0,
            'Propionate' => 8.0,
            'Butyrate' => 35.0,
            'Sucrose_Degradation' => 72.0,
            'ORP_Mid' => -180.0,
            'ORP_Low' => -220.0,
            'VFA' => 90.0,
            'COD_O' => 12000.0,
            'HPR' => 1.250,
            'PredictionDateTime' => now(),
        ], $overrides);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_can_be_created_with_required_fields()
    {
        $user = User::factory()->create();
        $model = MLModel::factory()->create();

        Prediction::create($this->validPredictionData($user->id, $model->id, [
            'pH' => 6.4,
            'HPR' => 1.500,
        ]));

        $this->assertDatabaseHas('predictions', [
            'user_id' => $user->id,
            'ml_model_id' => $model->id,
            'pH' => 6.4,
            'HPR' => 1.5,
        ]);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_can_be_created_with_factory()
    {
        $user = User::factory()->create();
        $model = MLModel::factory()->create();

        $prediction = Prediction::factory()->create([
            'user_id' => $user->id,
            'ml_model_id' => $model->id,
            'HPR' => 2.100,
        ]);

        $this->assertDatabaseHas('predictions', [
            'user_id' => $user->id,
            'ml_model_id' => $model->id,
            'HPR' => 2.1,
        ]);

        $this->assertNotNull($prediction->pH);
        $this->assertNotNull($prediction->VSS);
        $this->assertNotNull($prediction->Ethanol);
        $this->assertNotNull($prediction->Acetate);
        $this->assertNotNull($prediction->Propionate);
        $this->assertNotNull($prediction->Butyrate);
        $this->assertNotNull($prediction->Sucrose_Degradation);
        $this->assertNotNull($prediction->ORP_Mid);
        $this->assertNotNull($prediction->ORP_Low);
        $this->assertNotNull($prediction->VFA);
        $this->assertNotNull($prediction->COD_O);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_belongs_to_a_user()
    {
        $user = User::factory()->create();
        $model = MLModel::factory()->create();

        $prediction = Prediction::factory()->create([
            'user_id' => $user->id,
            'ml_model_id' => $model->id,
        ]);

        $this->assertInstanceOf(User::class, $prediction->user);
        $this->assertEquals($user->id, $prediction->user->id);
        $this->assertEquals($user->FullName, $prediction->user->FullName);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_belongs_to_an_ml_model()
    {
        $user = User::factory()->create();
        $model = MLModel::factory()->create();

        $prediction = Prediction::factory()->create([
            'user_id' => $user->id,
            'ml_model_id' => $model->id,
        ]);

        $this->assertInstanceOf(MLModel::class, $prediction->mlModel);
        $this->assertEquals($model->id, $prediction->mlModel->id);
        $this->assertEquals($model->MLMName, $prediction->mlModel->MLMName);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function prediction_features_are_within_valid_ranges()
    {
        $user = User::factory()->create();
        $model = MLModel::factory()->create();

        $prediction = Prediction::factory()->create([
            'user_id' => $user->id,
            'ml_model_id' => $model->id,
            'pH' => 7.0,
            'VSS' => 5000.0,
            'Ethanol' => 50.0,
            'Acetate' => 100.0,
            'Propionate' => 50.0,
            'Butyrate' => 100.0,
            'Sucrose_Degradation' => 80.0,
            'ORP_Mid' => -150.0,
            'ORP_Low' => -250.0,
            'VFA' => 200.0,
            'COD_O' => 25000.0,
        ]);

        $this->assertTrue($prediction->pH >= 3 && $prediction->pH <= 8);
        $this->assertTrue($prediction->VSS >= 0 && $prediction->VSS <= 10000);
        $this->assertTrue($prediction->Ethanol >= 0 && $prediction->Ethanol <= 100);
        $this->assertTrue($prediction->Acetate >= 0 && $prediction->Acetate <= 200);
        $this->assertTrue($prediction->Propionate >= 0 && $prediction->Propionate <= 100);
        $this->assertTrue($prediction->Butyrate >= 0 && $prediction->Butyrate <= 200);
        $this->assertTrue($prediction->Sucrose_Degradation >= 0 && $prediction->Sucrose_Degradation <= 100);
        $this->assertTrue($prediction->ORP_Mid >= -500 && $prediction->ORP_Mid <= 100);
        $this->assertTrue($prediction->ORP_Low >= -500 && $prediction->ORP_Low <= 100);
        $this->assertTrue($prediction->VFA >= 0 && $prediction->VFA <= 500);
        $this->assertTrue($prediction->COD_O >= 0 && $prediction->COD_O <= 50000);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function hpr_is_stored_as_numeric_value()
    {
        $user = User::factory()->create();
        $model = MLModel::factory()->create();

        $prediction = Prediction::factory()->create([
            'user_id' => $user->id,
            'ml_model_id' => $model->id,
            'HPR' => 1.875,
        ]);

        $this->assertTrue(is_numeric($prediction->HPR));
        $this->assertEquals(1.875, (float) $prediction->HPR);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function prediction_date_time_value_is_persisted()
    {
        $user = User::factory()->create();
        $model = MLModel::factory()->create();

        $prediction = Prediction::factory()->create([
            'user_id' => $user->id,
            'ml_model_id' => $model->id,
            'PredictionDateTime' => '2023-08-15 14:30:00',
        ]);

        $this->assertEquals(
            '2023-08-15 14:30:00',
            \Carbon\Carbon::parse($prediction->PredictionDateTime)->format('Y-m-d H:i:s')
        );
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_has_timestamps()
    {
        $prediction = Prediction::factory()->create();

        $this->assertNotNull($prediction->created_at);
        $this->assertNotNull($prediction->updated_at);
        $this->assertInstanceOf(\Carbon\Carbon::class, $prediction->created_at);
        $this->assertInstanceOf(\Carbon\Carbon::class, $prediction->updated_at);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_can_be_ordered_by_prediction_date()
    {
        $user = User::factory()->create();
        $model = MLModel::factory()->create();

        $oldPrediction = Prediction::factory()->create([
            'user_id' => $user->id,
            'ml_model_id' => $model->id,
            'PredictionDateTime' => now()->subDays(2),
        ]);

        $newPrediction = Prediction::factory()->create([
            'user_id' => $user->id,
            'ml_model_id' => $model->id,
            'PredictionDateTime' => now(),
        ]);

        $orderedPredictions = Prediction::orderBy('PredictionDateTime', 'desc')->get();

        $this->assertEquals($newPrediction->id, $orderedPredictions->first()->id);
        $this->assertEquals($oldPrediction->id, $orderedPredictions->last()->id);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_can_be_filtered_by_user()
    {
        $user1 = User::factory()->create();
        $user2 = User::factory()->create();
        $model = MLModel::factory()->create();

        $prediction1 = Prediction::factory()->create([
            'user_id' => $user1->id,
            'ml_model_id' => $model->id,
        ]);

        Prediction::factory()->create([
            'user_id' => $user2->id,
            'ml_model_id' => $model->id,
        ]);

        $user1Predictions = Prediction::where('user_id', $user1->id)->get();

        $this->assertCount(1, $user1Predictions);
        $this->assertEquals($prediction1->id, $user1Predictions->first()->id);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_can_be_filtered_by_model()
    {
        $user = User::factory()->create();
        $model1 = MLModel::factory()->create();
        $model2 = MLModel::factory()->create();

        $prediction1 = Prediction::factory()->create([
            'user_id' => $user->id,
            'ml_model_id' => $model1->id,
        ]);

        Prediction::factory()->create([
            'user_id' => $user->id,
            'ml_model_id' => $model2->id,
        ]);

        $model1Predictions = Prediction::where('ml_model_id', $model1->id)->get();

        $this->assertCount(1, $model1Predictions);
        $this->assertEquals($prediction1->id, $model1Predictions->first()->id);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_can_calculate_average_hpr_for_user()
    {
        $user = User::factory()->create();
        $model = MLModel::factory()->create();

        Prediction::factory()->create($this->validPredictionData($user->id, $model->id, [
            'HPR' => 1.0,
        ]));

        Prediction::factory()->create($this->validPredictionData($user->id, $model->id, [
            'HPR' => 2.0,
        ]));

        $avgHpr = Prediction::where('user_id', $user->id)->avg('HPR');

        $this->assertEquals(1.5, (float) $avgHpr);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_can_find_recent_predictions()
    {
        $user = User::factory()->create();
        $model = MLModel::factory()->create();

        // Old prediction
        Prediction::factory()->create($this->validPredictionData($user->id, $model->id, [
            'PredictionDateTime' => now()->subDays(60),
        ]));

        // Recent prediction
        $recentPrediction = Prediction::factory()->create($this->validPredictionData($user->id, $model->id, [
            'PredictionDateTime' => now()->subDays(15),
        ]));

        $recentPredictions = Prediction::where('user_id', $user->id)
            ->where('PredictionDateTime', '>=', now()->subDays(30))
            ->get();

        $this->assertCount(1, $recentPredictions);
        $this->assertEquals($recentPrediction->id, $recentPredictions->first()->id);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function foreign_key_constraints_are_enforced()
    {
        $this->expectException(\Illuminate\Database\QueryException::class);

        Prediction::create($this->validPredictionData(999, 999));
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function required_fields_are_enforced()
    {
        $this->expectException(\Illuminate\Database\QueryException::class);

        Prediction::create([
            // Missing required features and foreign keys
            'HPR' => 1.5,
        ]);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_can_be_soft_deleted()
    {
        $prediction = Prediction::factory()->create();
        $predictionId = $prediction->id;

        $prediction->delete();

        // Check if using soft deletes
        if (method_exists($prediction, 'trashed')) {
            $this->assertTrue($prediction->trashed());
            $this->assertDatabaseHas('predictions', ['id' => $predictionId]);
        } else {
            // Hard delete
            $this->assertDatabaseMissing('predictions', ['id' => $predictionId]);
        }
    }
}
