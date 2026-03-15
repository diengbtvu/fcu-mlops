<?php

namespace Tests\Feature;

use Tests\TestCase;
use Illuminate\Foundation\Testing\RefreshDatabase;

class RoutingTest extends TestCase
{
    use RefreshDatabase;

    #[\PHPUnit\Framework\Attributes\Test]
    public function root_redirects_to_login()
    {
        $response = $this->get('/');
        
        $response->assertRedirect(route('login'));
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function search_route_redirects_to_login_with_message()
    {
        $response = $this->get(route('search'));
        
        $response->assertRedirect(route('login'));
        $response->assertSessionHas('message', 'Please login to use search functionality.');
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function login_routes_are_accessible()
    {
        $response = $this->get(route('login'));
        $response->assertStatus(200);
        
        // POST route should return validation errors for empty data
        $response = $this->post(route('login'));
        $response->assertSessionHasErrors();
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function logout_route_exists()
    {
        $response = $this->post(route('logout'));
        $response->assertRedirect(route('login'));
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function dashboard_route_exists()
    {
        $response = $this->get(route('dashboard'));
        $response->assertRedirect(route('login')); // Should redirect to login when not authenticated
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function admin_routes_exist()
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
            $response = $this->get(route($route));
            // All should redirect to login for unauthenticated users
            $response->assertRedirect(route('login'));
        }
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function user_routes_exist()
    {
        $userRoutes = [
            'user.dashboard',
            'user.predict',
            'user.history',
            'user.profile',
            'user.security'
        ];

        foreach ($userRoutes as $route) {
            $response = $this->get(route($route));
            // All should redirect to login for unauthenticated users
            $response->assertRedirect(route('login'));
        }
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function admin_post_routes_exist()
    {
        $adminPostRoutes = [
            ['route' => 'admin.users.store', 'method' => 'post'],
            ['route' => 'admin.models.store', 'method' => 'post'],
            ['route' => 'admin.predict.make', 'method' => 'post'],
        ];

        foreach ($adminPostRoutes as $routeInfo) {
            $response = $this->{$routeInfo['method']}(route($routeInfo['route']));
            // Should redirect to login for unauthenticated users
            $response->assertRedirect(route('login'));
        }
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function user_post_routes_exist()
    {
        $userPostRoutes = [
            ['route' => 'user.predict.make', 'method' => 'post'],
            ['route' => 'user.profile.update', 'method' => 'put'],
            ['route' => 'user.security.change-password', 'method' => 'post'],
        ];

        foreach ($userPostRoutes as $routeInfo) {
            $response = $this->{$routeInfo['method']}(route($routeInfo['route']));
            // Should redirect to login for unauthenticated users
            $response->assertRedirect(route('login'));
        }
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function admin_user_management_routes_exist()
    {
        // These routes need parameters, so we test with dummy IDs
        $userManagementRoutes = [
            ['route' => 'admin.users.edit', 'method' => 'get', 'params' => ['user' => 1]],
            ['route' => 'admin.users.update', 'method' => 'put', 'params' => ['user' => 1]],
            ['route' => 'admin.users.delete', 'method' => 'delete', 'params' => ['user' => 1]],
            ['route' => 'admin.users.force-delete', 'method' => 'delete', 'params' => ['user' => 1]],
            ['route' => 'admin.users.reset-password', 'method' => 'post', 'params' => ['user' => 1]],
            ['route' => 'admin.users.anonymize', 'method' => 'post', 'params' => ['user' => 1]],
        ];

        foreach ($userManagementRoutes as $routeInfo) {
            $response = $this->{$routeInfo['method']}(route($routeInfo['route'], $routeInfo['params']));
            // Should redirect to login for unauthenticated users
            $response->assertRedirect(route('login'));
        }
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function admin_model_management_routes_exist()
    {
        $modelManagementRoutes = [
            ['route' => 'admin.models.report', 'method' => 'get', 'params' => ['model' => 1]],
            ['route' => 'admin.models.edit', 'method' => 'get', 'params' => ['model' => 1]],
            ['route' => 'admin.models.update', 'method' => 'put', 'params' => ['model' => 1]],
            ['route' => 'admin.models.delete', 'method' => 'delete', 'params' => ['model' => 1]],
            ['route' => 'admin.models.force-delete', 'method' => 'delete', 'params' => ['model' => 1]],
            ['route' => 'admin.models.test', 'method' => 'post', 'params' => ['model' => 1]],
        ];

        foreach ($modelManagementRoutes as $routeInfo) {
            $response = $this->{$routeInfo['method']}(route($routeInfo['route'], $routeInfo['params']));
            // Should redirect to login for unauthenticated users
            $response->assertRedirect(route('login'));
        }
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function route_names_are_properly_defined()
    {
        // Test that route names exist and return proper URIs
        $namedRoutes = [
            'login' => '/login',
            'logout' => '/logout',
            'dashboard' => '/dashboard',
            'admin.dashboard' => '/admin/dashboard',
            'admin.users' => '/admin/users',
            'user.dashboard' => '/user/dashboard',
            'user.predict' => '/user/predict',
        ];

        foreach ($namedRoutes as $routeName => $expectedUri) {
            $uri = route($routeName, [], false); // Generate relative URI
            $this->assertEquals($expectedUri, $uri, "Route {$routeName} should generate URI {$expectedUri}");
        }
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function route_parameters_work_correctly()
    {
        // Test routes with parameters
        $parametrizedRoutes = [
            ['name' => 'admin.users.edit', 'params' => ['user' => 5], 'expected' => '/admin/users/5/edit'],
            ['name' => 'admin.users.update', 'params' => ['user' => 5], 'expected' => '/admin/users/5'],
            ['name' => 'admin.models.report', 'params' => ['model' => 3], 'expected' => '/admin/models/3/report'],
            ['name' => 'admin.models.edit', 'params' => ['model' => 3], 'expected' => '/admin/models/3/edit'],
        ];

        foreach ($parametrizedRoutes as $routeInfo) {
            $uri = route($routeInfo['name'], $routeInfo['params'], false);
            $this->assertEquals($routeInfo['expected'], $uri);
        }
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function middleware_groups_are_applied_correctly()
    {
        // In test environment, login request is validated and redirects back with errors.
        $response = $this->post(route('login'));
        
        $response->assertRedirect();
        $response->assertSessionHasErrors(['username', 'password']);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function route_prefixes_work_correctly()
    {
        // Admin routes should have 'admin' prefix
        $adminRoutes = [
            'admin.dashboard' => '/admin/dashboard',
            'admin.users' => '/admin/users',
            'admin.models' => '/admin/models',
        ];

        foreach ($adminRoutes as $routeName => $expectedUri) {
            $uri = route($routeName, [], false);
            $this->assertStringStartsWith('/admin', $uri);
            $this->assertEquals($expectedUri, $uri);
        }

        // User routes should have 'user' prefix
        $userRoutes = [
            'user.dashboard' => '/user/dashboard',
            'user.predict' => '/user/predict',
            'user.history' => '/user/history',
        ];

        foreach ($userRoutes as $routeName => $expectedUri) {
            $uri = route($routeName, [], false);
            $this->assertStringStartsWith('/user', $uri);
            $this->assertEquals($expectedUri, $uri);
        }
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function test_routes_are_only_available_in_local_environment()
    {
        // In testing environment, test routes should not be available
        // unless explicitly configured as local
        
        $this->app['env'] = 'production';
        
        // Try to access a test route (this would typically be defined in test.php)
        $response = $this->get('/test');
        
        // Should return 404 in non-local environment
        $response->assertStatus(404);
    }

    #[\PHPUnit\Framework\Attributes\Test]
    public function all_routes_have_proper_http_methods()
    {
        $routes = \Route::getRoutes();
        
        foreach ($routes as $route) {
            $methods = $route->methods();
            
            // Each route should have at least one HTTP method
            $this->assertNotEmpty($methods);
            
            // Common validation - no route should accept TRACE or CONNECT
            $this->assertNotContains('TRACE', $methods);
            $this->assertNotContains('CONNECT', $methods);
        }
    }
}
