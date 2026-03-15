<?php

namespace Tests\Feature;

use Tests\TestCase;
use App\Models\User;
use App\Models\Role;
use Illuminate\Foundation\Testing\RefreshDatabase;

class MiddlewareTest extends TestCase
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
    public function auth_middleware_redirects_guest_to_login()
    {
        $response = $this->get(route('user.dashboard'));
        
        $response->assertRedirect(route('login'));
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function admin_middleware_allows_admin_access()
    {
        $admin = User::factory()->create(['role_id' => 1]);
        
        $response = $this->actingAs($admin)->get(route('admin.dashboard'));
        
        $response->assertStatus(200);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function admin_middleware_denies_user_access()
    {
        $user = User::factory()->create(['role_id' => 2]);
        
        $response = $this->actingAs($user)->get(route('admin.dashboard'));
        
        $response->assertStatus(403);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function user_middleware_allows_user_access()
    {
        $user = User::factory()->create(['role_id' => 2]);
        
        $response = $this->actingAs($user)->get(route('user.dashboard'));
        
        $response->assertStatus(200);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function user_middleware_denies_admin_access()
    {
        $admin = User::factory()->create(['role_id' => 1]);
        
        $response = $this->actingAs($admin)->get(route('user.dashboard'));
        
        $response->assertStatus(403);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function admin_routes_require_authentication_and_admin_role()
    {
        $adminRoutes = [
            'admin.dashboard',
            'admin.users',
            'admin.users.create',
            'admin.models',
            'admin.models.create',
            'admin.predict',
            'admin.history'
        ];

        foreach ($adminRoutes as $route) {
            // Test guest access
            auth()->logout();
            $response = $this->get(route($route));
            $response->assertRedirect(route('login'));
            
            // Test user access
            $user = User::factory()->create(['role_id' => 2]);
            $response = $this->actingAs($user)->get(route($route));
            $response->assertStatus(403);
            
            // Test admin access
            $admin = User::factory()->create(['role_id' => 1]);
            $response = $this->actingAs($admin)->get(route($route));
            $response->assertStatus(200);
        }
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function user_routes_require_authentication_and_user_role()
    {
        $userRoutes = [
            'user.dashboard',
            'user.predict',
            'user.history',
            'user.profile',
            'user.security'
        ];

        foreach ($userRoutes as $route) {
            // Test guest access
            auth()->logout();
            $response = $this->get(route($route));
            $response->assertRedirect(route('login'));
            
            // Test admin access
            $admin = User::factory()->create(['role_id' => 1]);
            $response = $this->actingAs($admin)->get(route($route));
            $response->assertStatus(403);
            
            // Test user access
            $user = User::factory()->create(['role_id' => 2]);
            $response = $this->actingAs($user)->get(route($route));
            $response->assertStatus(200);
        }
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function admin_post_routes_require_admin_role()
    {
        $user = User::factory()->create(['role_id' => 2]);
        $admin = User::factory()->create(['role_id' => 1]);

        // Test user management routes
        $userData = [
            'FullName' => 'Test User',
            'Gender' => 'Male',
            'BirthDate' => '1990-01-01',
            'Address' => 'Test Address',
            'Username' => 'testuser123',
            'Password' => 'password123'
        ];

        // User should be denied
        $response = $this->actingAs($user)->post(route('admin.users.store'), $userData);
        $response->assertStatus(403);

        // Admin should be allowed
        $response = $this->actingAs($admin)->post(route('admin.users.store'), $userData);
        $response->assertRedirect(route('admin.users'));
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function user_post_routes_require_user_role()
    {
        $user = User::factory()->create(['role_id' => 2]);
        $admin = User::factory()->create(['role_id' => 1]);

        $profileData = [
            'FullName' => 'Updated Name',
            'Gender' => 'Female',
            'BirthDate' => '1995-01-01',
            'Address' => 'Updated Address',
            'Username' => 'updateduser'
        ];

        // Admin should be denied
        $response = $this->actingAs($admin)->put(route('user.profile.update'), $profileData);
        $response->assertStatus(403);

        // User should be allowed
        $response = $this->actingAs($user)->put(route('user.profile.update'), $profileData);
        $response->assertRedirect(route('user.profile'));
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function middleware_handles_non_existent_user_gracefully()
    {
        // Create a user then delete them while keeping the session
        $user = User::factory()->create(['role_id' => 2]);
        $this->actingAs($user);
        
        // Delete the user from database
        $user->delete();
        
        $response = $this->get(route('user.dashboard'));
        
        // Should redirect to login as the user no longer exists
        $response->assertRedirect(route('login'));
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function middleware_handles_role_changes_correctly()
    {
        $user = User::factory()->create(['role_id' => 2]);
        
        // User can access user routes
        $response = $this->actingAs($user)->get(route('user.dashboard'));
        $response->assertStatus(200);
        
        // Change role to admin
        $user->update(['role_id' => 1]);
        $user->refresh();
        
        // Now should not be able to access user routes
        $response = $this->actingAs($user)->get(route('user.dashboard'));
        $response->assertStatus(403);
        
        // But should be able to access admin routes
        $response = $this->actingAs($user)->get(route('admin.dashboard'));
        $response->assertStatus(200);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function api_routes_require_proper_authentication()
    {
        // Test prediction API routes
        $predictionData = [
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
            'ml_model_id' => 1
        ];

        // Guest access should be denied
        $response = $this->postJson(route('user.predict.make'), $predictionData);
        $response->assertStatus(401);

        // Admin access to user prediction should be denied
        $admin = User::factory()->create(['role_id' => 1]);
        $response = $this->actingAs($admin)->postJson(route('user.predict.make'), $predictionData);
        $response->assertStatus(403);
    }
}
