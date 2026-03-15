<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Factories\HasFactory;

class Prediction extends Model
{
    use HasFactory;

    protected $fillable = [
        'user_id',
        'ml_model_id',
        // Input features (11 biochemical parameters — Wang et al. 2024)
        'pH',
        'VSS',
        'Ethanol',
        'Acetate',
        'Propionate',
        'Butyrate',
        'Sucrose_Degradation',
        'ORP_Mid',
        'ORP_Low',
        'VFA',
        'COD_O',
        // Output target
        'HPR',              // Hydrogen Production Rate (L/h/L)
        'PredictionDateTime',
    ];


    public function user()
    {
        return $this->belongsTo(User::class);
    }

    public function mlModel()
    {
        return $this->belongsTo(MLModel::class, 'ml_model_id');
    }
}
