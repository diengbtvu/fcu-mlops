<?php

namespace Tests\Feature;

use Tests\TestCase;
use App\Models\User;
use App\Models\Role;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Facades\Auth;

class AuthControllerTest extends TestCase
{
    use RefreshDatabase;

    protected function setUp(): void
    {
        parent::setUp();
        
        // Create roles
        Role::create(['RoleCode' => 'admin', 'RoleName' => 'Administrator']);
        Role::create(['RoleCode' => 'user', 'RoleName' => 'User']);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_shows_login_page_when_not_authenticated()
    {
        $response = $this->get(route('login'));

        $response->assertStatus(200);
        $response->assertViewIs('auth.login');
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_redirects_to_dashboard_when_already_authenticated()
    {
        $user = User::factory()->create(['role_id' => 2]);
        
        $response = $this->actingAs($user)->get(route('login'));

        $response->assertRedirect(route('dashboard'));
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_can_login_with_valid_credentials()
    {
        $user = User::factory()->create([
            'Username' => 'testuser',
            'Password' => Hash::make('password'),
            'role_id' => 2
        ]);

        $response = $this->post(route('login'), [
            'username' => 'testuser',
            'password' => 'password',
        ]);

        $response->assertRedirect(route('user.dashboard'));
        $this->assertAuthenticatedAs($user);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_redirects_admin_to_admin_dashboard_after_login()
    {
        $admin = User::factory()->create([
            'Username' => 'admin',
            'Password' => Hash::make('password'),
            'role_id' => 1
        ]);

        $response = $this->post(route('login'), [
            'username' => 'admin',
            'password' => 'password',
        ]);

        $response->assertRedirect(route('admin.dashboard'));
        $this->assertAuthenticatedAs($admin);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_fails_login_with_invalid_credentials()
    {
        $response = $this->post(route('login'), [
            'username' => 'nonexistent',
            'password' => 'wrongpassword',
        ]);

        $response->assertRedirect();
        $response->assertSessionHasErrors(['username']);
        $this->assertGuest();
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_validates_login_form_fields()
    {
        $response = $this->post(route('login'), []);

        $response->assertSessionHasErrors(['username', 'password']);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_can_logout()
    {
        $user = User::factory()->create(['role_id' => 2]);
        
        $response = $this->actingAs($user)->post(route('logout'));

        $response->assertRedirect(route('login'));
        $this->assertGuest();
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function dashboard_redirects_unauthenticated_users_to_login()
    {
        $response = $this->get(route('dashboard'));

        $response->assertRedirect(route('login'));
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function dashboard_redirects_admin_to_admin_dashboard()
    {
        $admin = User::factory()->create(['role_id' => 1]);
        
        $response = $this->actingAs($admin)->get(route('dashboard'));

        $response->assertRedirect(route('admin.dashboard'));
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function dashboard_redirects_user_to_user_dashboard()
    {
        $user = User::factory()->create(['role_id' => 2]);
        
        $response = $this->actingAs($user)->get(route('dashboard'));

        $response->assertRedirect(route('user.dashboard'));
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_regenerates_session_on_successful_login()
    {
        $user = User::factory()->create([
            'Username' => 'testuser',
            'Password' => Hash::make('password'),
            'role_id' => 2
        ]);

        $this->startSession();
        $oldSessionId = session()->getId();

        $this->post(route('login'), [
            'username' => 'testuser',
            'password' => 'password',
        ]);

        $newSessionId = session()->getId();
        $this->assertNotEquals($oldSessionId, $newSessionId);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function it_only_returns_username_on_login_failure()
    {
        $response = $this->post(route('login'), [
            'username' => 'testuser',
            'password' => 'wrongpassword',
        ]);

        $response->assertSessionHasInput('username');
        $response->assertSessionMissing('password');
    }
}
