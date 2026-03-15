<?php

namespace Database\Factories;

use Illuminate\Database\Eloquent\Factories\Factory;

/**
 * @extends \Illuminate\Database\Eloquent\Factories\Factory<\App\Models\Role>
 */
class RoleFactory extends Factory
{
    /**
     * Define the model's default state.
     *
     * @return array<string, mixed>
     */
    public function definition(): array
    {
        return [
            'RoleCode' => fake()->unique()->randomElement(['admin', 'user', 'moderator', 'viewer']),
            'RoleName' => fake()->jobTitle(),
        ];
    }

    /**
     * Create an admin role.
     */
    public function admin(): static
    {
        return $this->state(fn (array $attributes) => [
            'RoleCode' => 'admin',
            'RoleName' => 'Administrator',
        ]);
    }

    /**
     * Create a user role.
     */
    public function user(): static
    {
        return $this->state(fn (array $attributes) => [
            'RoleCode' => 'user',
            'RoleName' => 'User',
        ]);
    }
}
