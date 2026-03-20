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
        $features = config('prediction.features');

        return [
            'user_id' => User::factory(),
            'ml_model_id' => MLModel::factory(),
            'pH' => fake()->randomFloat(4, $features['ph']['min'], $features['ph']['max']),
            'VSS' => fake()->randomFloat(4, $features['vss']['min'], $features['vss']['max']),
            'Ethanol' => fake()->randomFloat(4, $features['ethanol']['min'], $features['ethanol']['max']),
            'Acetate' => fake()->randomFloat(4, $features['acetate']['min'], $features['acetate']['max']),
            'Propionate' => fake()->randomFloat(4, $features['propionate']['min'], $features['propionate']['max']),
            'Butyrate' => fake()->randomFloat(4, $features['butyrate']['min'], $features['butyrate']['max']),
            'Sucrose_Degradation' => fake()->randomFloat(4, $features['sucrose_degradation']['min'], $features['sucrose_degradation']['max']),
            'ORP_Mid' => fake()->randomFloat(4, $features['orp_mid']['min'], $features['orp_mid']['max']),
            'ORP_Low' => fake()->randomFloat(4, $features['orp_low']['min'], $features['orp_low']['max']),
            'VFA' => fake()->randomFloat(4, $features['vfa']['min'], $features['vfa']['max']),
            'COD_O' => fake()->randomFloat(4, $features['cod_o']['min'], $features['cod_o']['max']),
            'HPR' => fake()->randomFloat(4, 0.0, 22.0),
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
            'HPR' => fake()->randomFloat(4, 10.0, 22.0),
        ]);
    }

    /**
     * Create a prediction with low Hydrogen Production Rate.
     */
    public function lowHpr(): static
    {
        return $this->state(fn (array $attributes) => [
            'HPR' => fake()->randomFloat(4, 0.0, 2.0),
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
        $features = config('prediction.features');

        return $this->state(fn (array $attributes) => [
            'pH' => fake()->randomElement([$features['ph']['min'], $features['ph']['max']]),
            'VSS' => fake()->randomElement([$features['vss']['min'], $features['vss']['max']]),
            'Ethanol' => fake()->randomElement([$features['ethanol']['min'], $features['ethanol']['max']]),
            'Acetate' => fake()->randomElement([$features['acetate']['min'], $features['acetate']['max']]),
            'Propionate' => fake()->randomElement([$features['propionate']['min'], $features['propionate']['max']]),
            'Butyrate' => fake()->randomElement([$features['butyrate']['min'], $features['butyrate']['max']]),
            'Sucrose_Degradation' => fake()->randomElement([$features['sucrose_degradation']['min'], $features['sucrose_degradation']['max']]),
            'ORP_Mid' => fake()->randomElement([$features['orp_mid']['min'], $features['orp_mid']['max']]),
            'ORP_Low' => fake()->randomElement([$features['orp_low']['min'], $features['orp_low']['max']]),
            'VFA' => fake()->randomElement([$features['vfa']['min'], $features['vfa']['max']]),
            'COD_O' => fake()->randomElement([$features['cod_o']['min'], $features['cod_o']['max']]),
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
