<?php

namespace Tests\Feature;

use App\Models\Role;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Http;
use Tests\TestCase;

class TrainingProgressControllerTest extends TestCase
{
    use RefreshDatabase;

    protected function setUp(): void
    {
        parent::setUp();

        Role::create(['RoleCode' => 'admin', 'RoleName' => 'Administrator']);
        Role::create(['RoleCode' => 'user', 'RoleName' => 'User']);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_generates_a_training_session_id_as_json()
    {
        $admin = User::factory()->admin()->create();

        $response = $this->actingAs($admin)->postJson(route('training.progress.session'));

        $response->assertOk()
            ->assertJsonPath('success', true);

        $sessionId = (string) $response->json('session_id');
        $this->assertMatchesRegularExpression(
            '/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i',
            $sessionId
        );
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_reads_progress_from_the_local_shared_progress_directory()
    {
        $admin = User::factory()->admin()->create();
        $sessionId = '7d85086d-a9bf-4510-b6f0-b8108fca90d8';
        $progressDir = storage_path('framework/testing/training-progress');

        if (!is_dir($progressDir)) {
            mkdir($progressDir, 0777, true);
        }

        file_put_contents($progressDir . DIRECTORY_SEPARATOR . $sessionId . '.json', json_encode([
            'session_id' => $sessionId,
            'status' => 'running',
            'progress' => 42,
            'message' => 'Training in progress',
        ], JSON_PRETTY_PRINT));

        config(['services.predict_service.progress_path' => $progressDir]);

        $response = $this->actingAs($admin)->getJson(route('training.progress.show', ['sessionId' => $sessionId]));

        $response->assertOk()
            ->assertJsonPath('success', true)
            ->assertJsonPath('progress.session_id', $sessionId)
            ->assertJsonPath('progress.progress', 42)
            ->assertJsonPath('progress.message', 'Training in progress');
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_returns_a_json_error_when_the_upstream_progress_service_is_not_json()
    {
        $admin = User::factory()->admin()->create();
        $sessionId = '11111111-2222-4333-8444-555555555555';

        config([
            'services.predict_service.progress_path' => storage_path('framework/testing/missing-progress'),
            'services.predict_service.url' => 'http://predict-service:5000',
        ]);

        Http::fake([
            'http://predict-service:5000/progress/*' => Http::response(
                '<html><body>Bad Gateway</body></html>',
                502,
                ['Content-Type' => 'text/html']
            ),
        ]);

        $response = $this->actingAs($admin)->getJson(route('training.progress.show', ['sessionId' => $sessionId]));

        $response->assertStatus(502)
            ->assertJsonPath('success', false)
            ->assertJsonPath('error', 'Training progress service returned an invalid response.');
    }
}
