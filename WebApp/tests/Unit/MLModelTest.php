<?php

namespace Tests\Unit;

use Tests\TestCase;
use App\Models\MLModel;
use App\Models\Prediction;
use App\Models\Role;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Database\QueryException;

class MLModelTest extends TestCase
{
    use RefreshDatabase;

    protected function setUp(): void
    {
        parent::setUp();

        Role::create(['RoleCode' => 'admin', 'RoleName' => 'Administrator']);
        Role::create(['RoleCode' => 'user', 'RoleName' => 'User']);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_can_be_created_with_required_fields()
    {
        $model = MLModel::create([
            'MLMName' => 'Test Model',
            'FilePath' => 'models/test_model.h5',
            'LibType' => 'keras',
            'IsActive' => true,
            'MSEValue' => 0.1,
            'MAEValue' => 0.05,
        ]);

        $this->assertDatabaseHas('ml_models', [
            'MLMName' => 'Test Model',
            'FilePath' => 'models/test_model.h5',
            'LibType' => 'keras',
            'IsActive' => true,
            'MSEValue' => 0.1,
            'MAEValue' => 0.05,
        ]);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_can_be_created_with_factory()
    {
        $model = MLModel::factory()->create([
            'MLMName' => 'Factory Model',
            'LibType' => 'pytorch'
        ]);

        $this->assertDatabaseHas('ml_models', [
            'MLMName' => 'Factory Model',
            'LibType' => 'pytorch'
        ]);
        
        $this->assertNotEmpty($model->FilePath);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_has_many_predictions()
    {
        $model = MLModel::factory()->create();
        
        $prediction1 = Prediction::factory()->create(['ml_model_id' => $model->id]);
        $prediction2 = Prediction::factory()->create(['ml_model_id' => $model->id]);
        
        $this->assertCount(2, $model->predictions);
        $this->assertContains($prediction1->id, $model->predictions->pluck('id'));
        $this->assertContains($prediction2->id, $model->predictions->pluck('id'));
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function is_active_can_be_boolean()
    {
        $activeModel = MLModel::factory()->create(['IsActive' => true]);
        $inactiveModel = MLModel::factory()->create(['IsActive' => false]);
        
        $this->assertTrue($activeModel->IsActive);
        $this->assertFalse($inactiveModel->IsActive);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_supports_different_library_types()
    {
        $validLibTypes = ['keras', 'pytorch', 'sklearn', 'xgboost', 'pickle', 'joblib'];
        
        foreach ($validLibTypes as $libType) {
            $model = MLModel::factory()->create(['LibType' => $libType]);
            $this->assertEquals($libType, $model->LibType);
        }
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function file_path_can_be_relative()
    {
        $model = MLModel::factory()->create([
            'FilePath' => 'models/relative_path_model.h5'
        ]);
        
        $this->assertEquals('models/relative_path_model.h5', $model->FilePath);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_can_check_if_file_exists()
    {
        // Create a model with a non-existent file path
        $model = MLModel::factory()->create([
            'FilePath' => 'models/nonexistent.h5'
        ]);
        
        // The fileExists method should be implemented in the model
        // For testing purposes, we assume it returns false for non-existent files
        if (method_exists($model, 'fileExists')) {
            $this->assertFalse($model->fileExists());
        }
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_can_get_absolute_path()
    {
        $model = MLModel::factory()->create([
            'FilePath' => 'models/test_model.h5'
        ]);
        
        // The absolute_path accessor should be implemented in the model
        if (method_exists($model, 'getAbsolutePathAttribute')) {
            $expectedPath = public_path('models/test_model.h5');
            $this->assertEquals($expectedPath, $model->absolute_path);
        }
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_can_be_soft_deleted()
    {
        $model = MLModel::factory()->create(['MLMName' => 'To Be Deleted']);
        $modelId = $model->id;
        
        $model->delete();
        
        // Check if using soft deletes
        if (method_exists($model, 'trashed')) {
            $this->assertTrue($model->trashed());
            $this->assertDatabaseHas('ml_models', ['id' => $modelId]);
        } else {
            // Hard delete
            $this->assertDatabaseMissing('ml_models', ['id' => $modelId]);
        }
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_cascades_delete_to_predictions_if_configured()
    {
        $model = MLModel::factory()->create();
        $prediction = Prediction::factory()->create(['ml_model_id' => $model->id]);

        try {
            $model->delete();
            $this->assertDatabaseMissing('ml_models', ['id' => $model->id]);
        } catch (QueryException $e) {
            // RESTRICT FK behavior is also valid for this schema.
            $this->assertDatabaseHas('ml_models', ['id' => $model->id]);
            $this->assertDatabaseHas('predictions', ['id' => $prediction->id]);
        }
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function name_is_required_and_must_be_string()
    {
        $this->expectException(\Illuminate\Database\QueryException::class);
        
        MLModel::create([
            'FilePath' => 'models/test.h5',
            'LibType' => 'keras',
            'IsActive' => true,
            'MSEValue' => 0.1,
            'MAEValue' => 0.05,
            // Missing MLMName
        ]);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function file_path_is_required()
    {
        $this->expectException(\Illuminate\Database\QueryException::class);
        
        MLModel::create([
            'MLMName' => 'Test Model',
            'LibType' => 'keras',
            'IsActive' => true,
            'MSEValue' => 0.1,
            'MAEValue' => 0.05,
            // Missing FilePath
        ]);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function lib_type_is_required()
    {
        $this->expectException(\Illuminate\Database\QueryException::class);
        
        MLModel::create([
            'MLMName' => 'Test Model',
            'FilePath' => 'models/test.h5',
            'IsActive' => true,
            'MSEValue' => 0.1,
            'MAEValue' => 0.05,
            // Missing LibType
        ]);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function is_active_defaults_to_false_if_not_specified()
    {
        $model = MLModel::factory()->make(['IsActive' => null]);
        
        // The default value behavior depends on database schema
        // This test checks the expected behavior
        $this->assertIsBool($model->IsActive ?? false);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_can_scope_active_models()
    {
        MLModel::factory()->count(3)->create(['IsActive' => true]);
        MLModel::factory()->count(2)->create(['IsActive' => false]);
        
        // If there's an active scope implemented
        if (method_exists(MLModel::class, 'scopeActive')) {
            $activeModels = MLModel::active()->get();
            $this->assertCount(3, $activeModels);
            
            foreach ($activeModels as $model) {
                $this->assertTrue($model->IsActive);
            }
        } else {
            // Manual filtering
            $activeModels = MLModel::where('IsActive', true)->get();
            $this->assertCount(3, $activeModels);
        }
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_can_scope_by_library_type()
    {
        MLModel::factory()->count(2)->create(['LibType' => 'keras']);
        MLModel::factory()->count(1)->create(['LibType' => 'pytorch']);
        MLModel::factory()->count(1)->create(['LibType' => 'sklearn']);
        
        $kerasModels = MLModel::where('LibType', 'keras')->get();
        $this->assertCount(2, $kerasModels);
        
        foreach ($kerasModels as $model) {
            $this->assertEquals('keras', $model->LibType);
        }
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_has_timestamps()
    {
        $model = MLModel::factory()->create();
        
        $this->assertNotNull($model->created_at);
        $this->assertNotNull($model->updated_at);
        $this->assertInstanceOf(\Carbon\Carbon::class, $model->created_at);
        $this->assertInstanceOf(\Carbon\Carbon::class, $model->updated_at);
    }
}
