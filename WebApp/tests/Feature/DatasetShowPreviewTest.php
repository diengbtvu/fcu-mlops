<?php

namespace Tests\Feature;

use App\Models\Dataset;
use App\Models\MLModel;
use App\Models\Role;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Facades\View;
use Illuminate\Support\ViewErrorBag;
use Tests\TestCase;

class DatasetShowPreviewTest extends TestCase
{
    use RefreshDatabase;

    private User $admin;

    protected function setUp(): void
    {
        parent::setUp();

        $this->withoutMiddleware();
        View::share('errors', new ViewErrorBag());

        Role::create(['RoleCode' => 'admin', 'RoleName' => 'Administrator']);
        Role::create(['RoleCode' => 'user', 'RoleName' => 'User']);

        $this->admin = User::factory()->create(['role_id' => 1]);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_displays_dataset_preview_data_on_the_show_page(): void
    {
        Storage::disk('public')->put(
            'datasets/test-preview.csv',
            "pH,VSS,Ethanol,Acetate,Propionate,Butyrate,Sucrose_Degradation,ORP_Mid,ORP_Low,VFA,COD-O,HPR\n5.8,3200,1200,450,210,95,68,-120,-260,980,12500,1.42\n"
        );

        $dataset = Dataset::create([
            'DatasetName' => 'Preview Dataset',
            'FilePath' => 'datasets/test-preview.csv',
            'Description' => 'Preview dataset description',
            'UploadedBy' => $this->admin->id,
        ]);

        Http::fake([
            '*' => Http::response([
                'success' => true,
                'status' => 'success',
                'detected_format' => 'csv',
                'sheet_names' => ['CSV'],
                'requires_sheet_selection' => false,
                'selected_sheet' => null,
                'preview_sheet' => 'CSV',
                'preview_columns' => ['pH', 'VSS', 'HPR'],
                'preview_rows' => [
                    ['pH' => 5.8, 'VSS' => 3200, 'HPR' => 1.42],
                    ['pH' => 6.1, 'VSS' => 3400, 'HPR' => 1.57],
                ],
                'required_columns' => [
                    'pH',
                    'VSS',
                    'Ethanol',
                    'Acetate',
                    'Propionate',
                    'Butyrate',
                    'Sucrose_Degradation',
                    'ORP_Mid',
                    'ORP_Low',
                    'VFA',
                    'COD-O',
                    'HPR',
                ],
                'missing_columns' => [],
                'rows_after_preprocessing' => 12,
                'minimum_required_rows' => 6,
                'is_valid' => true,
                'validation_error' => null,
            ], 200),
        ]);

        $response = $this->actingAs($this->admin)
            ->get(route('admin.datasets.show', $dataset->DatasetId));

        $response->assertOk();
        $response->assertSee('Preview Dataset');
        $response->assertSee('Dataset Preview');
        $response->assertSee('pH');
        $response->assertSee('3200');
        $response->assertSee('1.42');
        $response->assertSee('CSV / default sheet');

        Http::assertSentCount(1);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_shows_the_training_bundle_download_button_when_a_bundle_exists(): void
    {
        Storage::disk('public')->put(
            'datasets/test-preview.csv',
            "pH,VSS,Ethanol,Acetate,Propionate,Butyrate,Sucrose_Degradation,ORP_Mid,ORP_Low,VFA,COD-O,HPR\n5.8,3200,1200,450,210,95,68,-120,-260,980,12500,1.42\n"
        );

        $dataset = Dataset::create([
            'DatasetName' => 'Bundle Dataset',
            'FilePath' => 'datasets/test-preview.csv',
            'UploadedBy' => $this->admin->id,
        ]);

        MLModel::create([
            'MLMName' => 'Bundle Model',
            'FilePath' => 'models/best_model.pkl',
            'LibType' => 'sklearn',
            'IsActive' => true,
            'MSEValue' => 0.0128,
            'MAEValue' => 0.0750,
            'R2Value' => 0.8171,
            'RMSEValue' => 0.1131,
            'DatasetId' => $dataset->DatasetId,
            'TrainedBy' => $this->admin->id,
            'training_report' => [
                'report_id' => 'Bundle_Model',
                'route_prefix' => '/train/reports/Bundle_Model',
                'files' => [
                    'training_bundle_zip' => 'training_bundle.zip',
                ],
            ],
        ]);

        Http::fake([
            '*' => Http::response([
                'success' => true,
                'status' => 'success',
                'detected_format' => 'csv',
                'sheet_names' => ['CSV'],
                'requires_sheet_selection' => false,
                'selected_sheet' => null,
                'preview_sheet' => 'CSV',
                'preview_columns' => ['pH', 'VSS', 'HPR'],
                'preview_rows' => [
                    ['pH' => 5.8, 'VSS' => 3200, 'HPR' => 1.42],
                ],
                'required_columns' => ['pH', 'VSS', 'Ethanol', 'Acetate', 'Propionate', 'Butyrate', 'Sucrose_Degradation', 'ORP_Mid', 'ORP_Low', 'VFA', 'COD-O', 'HPR'],
                'missing_columns' => [],
                'rows_after_preprocessing' => 12,
                'minimum_required_rows' => 6,
                'is_valid' => true,
                'validation_error' => null,
            ], 200),
        ]);

        $response = $this->actingAs($this->admin)
            ->get(route('admin.datasets.show', $dataset->DatasetId));

        $response->assertOk();
        $response->assertSee('Download Training ZIP');
        $response->assertSee('http://localhost:5000/train/reports/Bundle_Model/training_bundle.zip', false);
    }
}
