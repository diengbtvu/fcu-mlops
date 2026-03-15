<?php

namespace Tests;

use Illuminate\Foundation\Testing\TestCase as BaseTestCase;

abstract class TestCase extends BaseTestCase
{
    /**
     * Force deterministic test env before Laravel boots.
     */
    private function bootstrapTestingEnvironment(): void
    {
        putenv('APP_ENV=testing');
        putenv('DB_CONNECTION=sqlite');
        putenv('DB_DATABASE=:memory:');
        putenv('CACHE_STORE=array');
        putenv('QUEUE_CONNECTION=sync');
        putenv('SESSION_DRIVER=array');
        putenv('MAIL_MAILER=array');

        $_ENV['APP_ENV'] = 'testing';
        $_ENV['DB_CONNECTION'] = 'sqlite';
        $_ENV['DB_DATABASE'] = ':memory:';
        $_ENV['CACHE_STORE'] = 'array';
        $_ENV['QUEUE_CONNECTION'] = 'sync';
        $_ENV['SESSION_DRIVER'] = 'array';
        $_ENV['MAIL_MAILER'] = 'array';

        $_SERVER['APP_ENV'] = 'testing';
        $_SERVER['DB_CONNECTION'] = 'sqlite';
        $_SERVER['DB_DATABASE'] = ':memory:';
        $_SERVER['CACHE_STORE'] = 'array';
        $_SERVER['QUEUE_CONNECTION'] = 'sync';
        $_SERVER['SESSION_DRIVER'] = 'array';
        $_SERVER['MAIL_MAILER'] = 'array';
    }

    /**
     * Setup the test environment.
     */
    protected function setUp(): void
    {
        $this->bootstrapTestingEnvironment();
        parent::setUp();

        config(['app.env' => 'testing']);
    }

    /**
     * Clean up the testing environment before the next test.
     */
    protected function tearDown(): void
    {
        parent::tearDown();
    }

    /**
     * Assert that a database table has a specific count of records with WHERE conditions
     * Use assertDatabaseCount() for simple count checks
     */
    protected function assertDatabaseCountWhere(string $table, int $count, array $where = []): void
    {
        $query = $this->app['db']->table($table);
        
        if (!empty($where)) {
            $query->where($where);
        }
        
        $this->assertEquals($count, $query->count());
    }

    /**
     * Assert that a model has specific attributes
     */
    protected function assertModelAttributes($model, array $attributes): void
    {
        foreach ($attributes as $key => $value) {
            $this->assertEquals($value, $model->getAttribute($key), 
                "Model attribute '{$key}' does not match expected value");
        }
    }

    /**
     * Create an admin user for testing
     */
    protected function createAdminUser(array $attributes = [])
    {
        return \App\Models\User::factory()->create(array_merge([
            'role_id' => 1
        ], $attributes));
    }

    /**
     * Create a regular user for testing
     */
    protected function createUser(array $attributes = [])
    {
        return \App\Models\User::factory()->create(array_merge([
            'role_id' => 2
        ], $attributes));
    }
}
