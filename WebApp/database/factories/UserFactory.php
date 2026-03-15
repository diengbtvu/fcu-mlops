<?php

namespace Database\Factories;

use Illuminate\Database\Eloquent\Factories\Factory;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Str;

/**
 * @extends \Illuminate\Database\Eloquent\Factories\Factory<\App\Models\User>
 */
class UserFactory extends Factory
{
    /**
     * The current password being used by the factory.
     */
    protected static ?string $password;

    /**
     * Define the model's default state.
     *
     * @return array<string, mixed>
     */
    public function definition(): array
    {
        return [
            'UserCode' => 'USR' . str_pad(fake()->unique()->numberBetween(1000000, 9999999), 7, '0', STR_PAD_LEFT),
            'FullName' => fake()->name(),
            'Gender' => fake()->randomElement(['Male', 'Female']),
            'BirthDate' => fake()->dateTimeBetween('-60 years', '-18 years')->format('Y-m-d'),
            'Address' => fake()->address(),
            'Username' => fake()->unique()->userName(),
            'Password' => static::$password ??= Hash::make('password'),
            'role_id' => 2, // Default to user role
            'remember_token' => Str::random(10),
        ];
    }

    /**
     * Create an admin user.
     */
    public function admin(): static
    {
        return $this->state(fn (array $attributes) => [
            'role_id' => 1,
        ]);
    }

    /**
     * Create a user with specific role.
     */
    public function role(int $roleId): static
    {
        return $this->state(fn (array $attributes) => [
            'role_id' => $roleId,
        ]);
    }
}
