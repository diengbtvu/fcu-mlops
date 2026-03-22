<?php

namespace Tests\Feature;

use App\Models\Role;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\Client\Request as HttpRequest;
use Illuminate\Http\UploadedFile;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Storage;
use Tests\TestCase;

class DatasetUploadValidationTest extends TestCase
{
    use RefreshDatabase;

    private User $admin;

    protected function setUp(): void
    {
        parent::setUp();

        $this->withoutMiddleware();

        Role::create(['RoleCode' => 'admin', 'RoleName' => 'Administrator']);
        Role::create(['RoleCode' => 'user', 'RoleName' => 'User']);

        $this->admin = User::factory()->create(['role_id' => 1]);
    }

    private function fakeInspectResponse(array $overrides = []): void
    {
        $payload = array_merge([
            'success' => true,
            'status' => 'success',
            'detected_format' => 'csv',
            'sheet_names' => ['CSV'],
            'requires_sheet_selection' => false,
            'selected_sheet' => null,
            'preview_sheet' => 'CSV',
            'preview_columns' => ['pH', 'VSS', 'HPR'],
            'preview_rows' => [],
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
            'rows_after_preprocessing' => 10,
            'minimum_required_rows' => 6,
            'is_valid' => true,
            'validation_error' => null,
        ], $overrides);

        Http::fake([
            '*' => Http::response($payload, 200),
        ]);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_accepts_csv_dataset_upload_after_remote_inspection(): void
    {
        Storage::fake('public');
        $this->fakeInspectResponse();

        $response = $this->actingAs($this->admin)->post(route('admin.datasets.store'), [
            'DatasetName' => 'CSV Dataset',
            'Description' => 'CSV file upload',
            'dataset_file' => UploadedFile::fake()->create('template.csv', 20, 'text/csv'),
        ]);

        $response->assertRedirect(route('admin.datasets.index'));
        $this->assertDatabaseHas('datasets', [
            'DatasetName' => 'CSV Dataset',
            'SelectedSheet' => null,
        ]);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_accepts_single_sheet_xlsx_upload_and_saves_the_resolved_sheet(): void
    {
        Storage::fake('public');
        $this->fakeInspectResponse([
            'detected_format' => 'xlsx',
            'sheet_names' => ['TrainData'],
            'selected_sheet' => 'TrainData',
            'preview_sheet' => 'TrainData',
        ]);

        $response = $this->actingAs($this->admin)->post(route('admin.datasets.store'), [
            'DatasetName' => 'XLSX Dataset',
            'Description' => 'Single-sheet workbook upload',
            'dataset_file' => UploadedFile::fake()->create(
                'template.xlsx',
                20,
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            ),
        ]);

        $response->assertRedirect(route('admin.datasets.index'));
        $this->assertDatabaseHas('datasets', [
            'DatasetName' => 'XLSX Dataset',
            'SelectedSheet' => 'TrainData',
        ]);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_accepts_xls_dataset_upload_when_the_selected_sheet_is_valid(): void
    {
        Storage::fake('public');
        $this->fakeInspectResponse([
            'detected_format' => 'xls',
            'sheet_names' => ['Sheet1'],
            'selected_sheet' => 'Sheet1',
            'preview_sheet' => 'Sheet1',
        ]);

        $response = $this->actingAs($this->admin)->post(route('admin.datasets.store'), [
            'DatasetName' => 'XLS Dataset',
            'Description' => 'Legacy Excel upload',
            'dataset_file' => UploadedFile::fake()->create(
                'template.xls',
                20,
                'application/vnd.ms-excel'
            ),
        ]);

        $response->assertRedirect(route('admin.datasets.index'));
        $this->assertDatabaseHas('datasets', [
            'DatasetName' => 'XLS Dataset',
            'SelectedSheet' => 'Sheet1',
        ]);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_rejects_txt_dataset_upload_before_remote_inspection(): void
    {
        Storage::fake('public');
        Http::fake();

        $response = $this
            ->actingAs($this->admin)
            ->from(route('admin.datasets.create'))
            ->post(route('admin.datasets.store'), [
                'DatasetName' => 'TXT Dataset',
                'Description' => 'TXT should be rejected',
                'dataset_file' => UploadedFile::fake()->create('template.txt', 20, 'text/plain'),
            ]);

        $response->assertRedirect(route('admin.datasets.create'));
        $response->assertSessionHasErrors(['dataset_file']);
        $this->assertDatabaseMissing('datasets', ['DatasetName' => 'TXT Dataset']);
        Http::assertNothingSent();
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_requires_sheet_selection_for_multi_sheet_workbooks(): void
    {
        Storage::fake('public');
        $this->fakeInspectResponse([
            'detected_format' => 'xlsx',
            'sheet_names' => ['Summary', 'TrainData'],
            'requires_sheet_selection' => true,
            'selected_sheet' => null,
            'preview_sheet' => 'Summary',
            'is_valid' => false,
            'validation_error' => 'Please choose a sheet before uploading this workbook.',
        ]);

        $response = $this
            ->actingAs($this->admin)
            ->from(route('admin.datasets.create'))
            ->post(route('admin.datasets.store'), [
                'DatasetName' => 'Workbook Dataset',
                'Description' => 'Workbook with multiple sheets',
                'dataset_file' => UploadedFile::fake()->create(
                    'template.xlsx',
                    20,
                    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                ),
            ]);

        $response->assertRedirect(route('admin.datasets.create'));
        $response->assertSessionHasErrors(['selected_sheet']);
        $this->assertDatabaseMissing('datasets', ['DatasetName' => 'Workbook Dataset']);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_sends_the_selected_sheet_to_the_inspection_api_and_saves_it(): void
    {
        Storage::fake('public');
        $this->fakeInspectResponse([
            'detected_format' => 'xlsx',
            'sheet_names' => ['Summary', 'TrainData'],
            'selected_sheet' => 'TrainData',
            'preview_sheet' => 'TrainData',
        ]);

        $response = $this->actingAs($this->admin)->post(route('admin.datasets.store'), [
            'DatasetName' => 'Workbook Dataset',
            'Description' => 'Workbook with selected sheet',
            'selected_sheet' => 'TrainData',
            'dataset_file' => UploadedFile::fake()->create(
                'template.xlsx',
                20,
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            ),
        ]);

        $response->assertRedirect(route('admin.datasets.index'));
        $this->assertDatabaseHas('datasets', [
            'DatasetName' => 'Workbook Dataset',
            'SelectedSheet' => 'TrainData',
        ]);

        Http::assertSent(function (HttpRequest $request): bool {
            return str_contains($request->url(), '/train/inspect')
                && ($request['sheet_name'] ?? null) === 'TrainData';
        });
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_rejects_a_sheet_that_is_missing_required_columns(): void
    {
        Storage::fake('public');
        $this->fakeInspectResponse([
            'detected_format' => 'xlsx',
            'sheet_names' => ['Summary'],
            'selected_sheet' => 'Summary',
            'preview_sheet' => 'Summary',
            'missing_columns' => ['pH', 'VSS', 'HPR'],
            'is_valid' => false,
            'validation_error' => 'Missing required columns: pH, VSS, HPR',
        ]);

        $response = $this
            ->actingAs($this->admin)
            ->from(route('admin.datasets.create'))
            ->post(route('admin.datasets.store'), [
                'DatasetName' => 'Invalid Workbook',
                'Description' => 'Missing required columns',
                'selected_sheet' => 'Summary',
                'dataset_file' => UploadedFile::fake()->create(
                    'template.xlsx',
                    20,
                    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                ),
            ]);

        $response->assertRedirect(route('admin.datasets.create'));
        $response->assertSessionHasErrors(['dataset_file']);
        $this->assertDatabaseMissing('datasets', ['DatasetName' => 'Invalid Workbook']);
    }
}
