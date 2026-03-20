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
            'pH' => 5.8,
            'VSS' => 2.36,
            'Ethanol' => 1739.25,
            'Acetate' => 925.5,
            'Propionate' => 1100.0,
            'Butyrate' => 10.6,
            'Sucrose_Degradation' => 91.68,
            'ORP_Mid' => -226.67,
            'ORP_Low' => -481.0,
            'VFA' => 3723.5,
            'COD_O' => 11.52,
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
            'pH' => 6.2,
            'VSS' => 3.4,
            'Ethanol' => 2200.0,
            'Acetate' => 1400.0,
            'Propionate' => 1200.0,
            'Butyrate' => 16.0,
            'Sucrose_Degradation' => 88.0,
            'ORP_Mid' => -260.0,
            'ORP_Low' => -420.0,
            'VFA' => 4800.0,
            'COD_O' => 18.0,
        ]);

        $ranges = config('prediction.features');

        $this->assertTrue($prediction->pH >= $ranges['ph']['min'] && $prediction->pH <= $ranges['ph']['max']);
        $this->assertTrue($prediction->VSS >= $ranges['vss']['min'] && $prediction->VSS <= $ranges['vss']['max']);
        $this->assertTrue($prediction->Ethanol >= $ranges['ethanol']['min'] && $prediction->Ethanol <= $ranges['ethanol']['max']);
        $this->assertTrue($prediction->Acetate >= $ranges['acetate']['min'] && $prediction->Acetate <= $ranges['acetate']['max']);
        $this->assertTrue($prediction->Propionate >= $ranges['propionate']['min'] && $prediction->Propionate <= $ranges['propionate']['max']);
        $this->assertTrue($prediction->Butyrate >= $ranges['butyrate']['min'] && $prediction->Butyrate <= $ranges['butyrate']['max']);
        $this->assertTrue($prediction->Sucrose_Degradation >= $ranges['sucrose_degradation']['min'] && $prediction->Sucrose_Degradation <= $ranges['sucrose_degradation']['max']);
        $this->assertTrue($prediction->ORP_Mid >= $ranges['orp_mid']['min'] && $prediction->ORP_Mid <= $ranges['orp_mid']['max']);
        $this->assertTrue($prediction->ORP_Low >= $ranges['orp_low']['min'] && $prediction->ORP_Low <= $ranges['orp_low']['max']);
        $this->assertTrue($prediction->VFA >= $ranges['vfa']['min'] && $prediction->VFA <= $ranges['vfa']['max']);
        $this->assertTrue($prediction->COD_O >= $ranges['cod_o']['min'] && $prediction->COD_O <= $ranges['cod_o']['max']);
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
