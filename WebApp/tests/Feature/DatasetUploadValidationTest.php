<?php

namespace Tests\Feature;

use App\Models\Role;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\UploadedFile;
use Illuminate\Support\Facades\Storage;
use Tests\TestCase;

class DatasetUploadValidationTest extends TestCase
{
    use RefreshDatabase;

    private User $admin;

    protected function setUp(): void
    {
        parent::setUp();

        // Focus these tests on upload validation rules.
        $this->withoutMiddleware();

        Role::create(['RoleCode' => 'admin', 'RoleName' => 'Administrator']);
        Role::create(['RoleCode' => 'user', 'RoleName' => 'User']);

        $this->admin = User::factory()->create(['role_id' => 1]);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_accepts_csv_dataset_upload(): void
    {
        Storage::fake('public');

        $response = $this->actingAs($this->admin)->post(route('admin.datasets.store'), [
            'DatasetName' => 'CSV Dataset',
            'Description' => 'CSV file upload',
            'dataset_file' => UploadedFile::fake()->create('template.csv', 20, 'text/csv'),
        ]);

        $response->assertRedirect(route('admin.datasets.index'));
        $this->assertDatabaseHas('datasets', ['DatasetName' => 'CSV Dataset']);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_accepts_xlsx_dataset_upload(): void
    {
        Storage::fake('public');

        $response = $this->actingAs($this->admin)->post(route('admin.datasets.store'), [
            'DatasetName' => 'XLSX Dataset',
            'Description' => 'XLSX file upload',
            'dataset_file' => UploadedFile::fake()->create(
                'template.xlsx',
                20,
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            ),
        ]);

        $response->assertRedirect(route('admin.datasets.index'));
        $this->assertDatabaseHas('datasets', ['DatasetName' => 'XLSX Dataset']);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_rejects_txt_dataset_upload(): void
    {
        Storage::fake('public');

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
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_rejects_xls_dataset_upload(): void
    {
        Storage::fake('public');

        $response = $this
            ->actingAs($this->admin)
            ->from(route('admin.datasets.create'))
            ->post(route('admin.datasets.store'), [
                'DatasetName' => 'XLS Dataset',
                'Description' => 'XLS should be rejected',
                'dataset_file' => UploadedFile::fake()->create(
                    'template.xls',
                    20,
                    'application/vnd.ms-excel'
                ),
            ]);

        $response->assertRedirect(route('admin.datasets.create'));
        $response->assertSessionHasErrors(['dataset_file']);
        $this->assertDatabaseMissing('datasets', ['DatasetName' => 'XLS Dataset']);
    }
}
