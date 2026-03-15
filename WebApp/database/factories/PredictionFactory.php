<?php

namespace Database\Factories;

use App\Models\User;
use App\Models\MLModel;
use Illuminate\Database\Eloquent\Factories\Factory;

/**
 * @extends \Illuminate\Database\Eloquent\Factories\Factory<\App\Models\Prediction>
 */
class PredictionFactory extends Factory
{
    /**
     * Define the model's default state.
     *
     * @return array<string, mixed>
     */
    public function definition(): array
    {
        return [
            'user_id' => User::factory(),
            'ml_model_id' => MLModel::factory(),
            'pH' => fake()->randomFloat(2, 3, 8),
            'VSS' => fake()->randomFloat(2, 0, 10000),
            'Ethanol' => fake()->randomFloat(2, 0, 100),
            'Acetate' => fake()->randomFloat(2, 0, 200),
            'Propionate' => fake()->randomFloat(2, 0, 100),
            'Butyrate' => fake()->randomFloat(2, 0, 200),
            'Sucrose_Degradation' => fake()->randomFloat(2, 0, 100),
            'ORP_Mid' => fake()->randomFloat(2, -500, 100),
            'ORP_Low' => fake()->randomFloat(2, -500, 100),
            'VFA' => fake()->randomFloat(2, 0, 500),
            'COD_O' => fake()->randomFloat(2, 0, 50000),
            'HPR' => fake()->randomFloat(3, 0.05, 5.0),
            'PredictionDateTime' => fake()->dateTimeBetween('-1 year', 'now'),
        ];
    }

    /**
     * Create a prediction for a specific user.
     */
    public function forUser(User $user): static
    {
        return $this->state(fn (array $attributes) => [
            'user_id' => $user->id,
        ]);
    }

    /**
     * Create a prediction with a specific model.
     */
    public function withModel(MLModel $model): static
    {
        return $this->state(fn (array $attributes) => [
            'ml_model_id' => $model->id,
        ]);
    }

    /**
     * Create a recent prediction (within last 30 days).
     */
    public function recent(): static
    {
        return $this->state(fn (array $attributes) => [
            'PredictionDateTime' => fake()->dateTimeBetween('-30 days', 'now'),
        ]);
    }

    /**
     * Create an old prediction (older than 30 days).
     */
    public function old(): static
    {
        return $this->state(fn (array $attributes) => [
            'PredictionDateTime' => fake()->dateTimeBetween('-1 year', '-31 days'),
        ]);
    }

    /**
     * Create a prediction with high Hydrogen Production Rate.
     */
    public function highHpr(): static
    {
        return $this->state(fn (array $attributes) => [
            'HPR' => fake()->randomFloat(3, 2.5, 5.0),
        ]);
    }

    /**
     * Create a prediction with low Hydrogen Production Rate.
     */
    public function lowHpr(): static
    {
        return $this->state(fn (array $attributes) => [
            'HPR' => fake()->randomFloat(3, 0.05, 1.0),
        ]);
    }

    /**
     * Create a prediction with specific feature set.
     */
    public function withFeatures(array $features): static
    {
        return $this->state($features);
    }

    /**
     * Backward-compatible wrapper for previous API.
     */
    public function withParameters(
        float $ph,
        float $vss,
        float $ethanol,
        float $acetate,
        float $propionate,
        float $butyrate,
        float $sucroseDegradation,
        float $orpMid,
        float $orpLow,
        float $vfa,
        float $codO
    ): static {
        return $this->withFeatures([
            'pH' => $ph,
            'VSS' => $vss,
            'Ethanol' => $ethanol,
            'Acetate' => $acetate,
            'Propionate' => $propionate,
            'Butyrate' => $butyrate,
            'Sucrose_Degradation' => $sucroseDegradation,
            'ORP_Mid' => $orpMid,
            'ORP_Low' => $orpLow,
            'VFA' => $vfa,
            'COD_O' => $codO,
        ]);
    }

    /**
     * Create a prediction with specific HPR value.
     */
    public function withHpr(float $hpr): static
    {
        return $this->state(fn (array $attributes) => [
            'HPR' => $hpr,
        ]);
    }

    /**
     * Backward-compatible alias.
     */
    public function withResult(float $result): static
    {
        return $this->withHpr($result);
    }

    /**
     * Create a prediction from current day.
     */
    public function today(): static
    {
        return $this->state(fn (array $attributes) => [
            'PredictionDateTime' => fake()->dateTimeBetween('today', 'now'),
        ]);
    }

    /**
     * Create a prediction with extreme feature values.
     */
    public function extremeFeatures(): static
    {
        return $this->state(fn (array $attributes) => [
            'pH' => fake()->randomElement([3.0, 8.0]),
            'VSS' => fake()->randomElement([0.0, 10000.0]),
            'Ethanol' => fake()->randomElement([0.0, 100.0]),
            'Acetate' => fake()->randomElement([0.0, 200.0]),
            'Propionate' => fake()->randomElement([0.0, 100.0]),
            'Butyrate' => fake()->randomElement([0.0, 200.0]),
            'Sucrose_Degradation' => fake()->randomElement([0.0, 100.0]),
            'ORP_Mid' => fake()->randomElement([-500.0, 100.0]),
            'ORP_Low' => fake()->randomElement([-500.0, 100.0]),
            'VFA' => fake()->randomElement([0.0, 500.0]),
            'COD_O' => fake()->randomElement([0.0, 50000.0]),
        ]);
    }

    /**
     * Backward-compatible alias.
     */
    public function extremeParameters(): static
    {
        return $this->extremeFeatures();
    }
}
