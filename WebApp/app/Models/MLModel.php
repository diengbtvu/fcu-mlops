<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Factories\HasFactory;

class MLModel extends Model
{
    use HasFactory;

    protected $table = 'ml_models';

    protected $fillable = [
        'MLMName',
        'FilePath',
        'LibType',
        'IsActive',
        'MSEValue',
        'MAEValue',
        'R2Value',
        'RMSEValue',
        'ZenmlPipelineId',
        'TrainedBy',
        'DatasetId',
        'CreatedDate',
        'UpdatedDate',
        'mlflow_run_id',
        'mlflow_experiment_id',
        'gra_ranking',     // Grey Relational Analysis feature ranking (JSON)
        'training_report', // Training report metadata from predict-service
    ];

    protected $casts = [
        'IsActive'    => 'boolean',
        'CreatedDate' => 'datetime',
        'UpdatedDate' => 'datetime',
        'gra_ranking' => 'array',  // JSON → PHP array automatically
        'training_report' => 'array',
    ];

    /**
     * Get the top-ranked feature from GRA analysis.
     */
    public function getTopGraFeatureAttribute(): ?string
    {
        $ranking = $this->gra_ranking;
        if (is_array($ranking) && count($ranking) > 0) {
            return $ranking[0]['feature'] ?? null;
        }
        return null;
    }

    /**
     * Relationships
     */
    public function predictions()
    {
        return $this->hasMany(Prediction::class, 'ml_model_id');
    }

    public function dataset()
    {
        return $this->belongsTo(Dataset::class, 'DatasetId');
    }

    public function trainedByUser()
    {
        return $this->belongsTo(User::class, 'TrainedBy');
    }

    // Alias for relationship
    public function trainer()
    {
        return $this->trainedByUser();
    }

    /**
     * Accessors & Utility Functions
     */
    // Alias accessors for consistent naming
    public function getModelNameAttribute()
    {
        return $this->MLMName;
    }

    public function getLibraryTypeAttribute()
    {
        return $this->LibType;
    }

    public function getMSEAttribute()
    {
        return $this->MSEValue;
    }

    public function getMAEAttribute()
    {
        return $this->MAEValue;
    }

    public function getRMSEAttribute()
    {
        // Return stored RMSE value, or calculate from MSE if not stored
        return $this->RMSEValue ?? sqrt($this->MSEValue ?? 0);
    }

    public function getR2Attribute()
    {
        // Return stored R2 value, or default to 0 if not stored
        return $this->R2Value ?? 0;
    }

    public function getTrainedDateAttribute()
    {
        return $this->CreatedDate;
    }

    public function getAbsolutePathAttribute()
    {
        return public_path($this->FilePath);
    }

    public function fileExists()
    {
        return file_exists($this->getAbsolutePathAttribute());
    }

    public function getFileSizeAttribute()
    {
        if ($this->fileExists()) {
            $sizeInBytes = filesize($this->getAbsolutePathAttribute());
            return round($sizeInBytes / 1024 / 1024, 2); // MB
        }
        return 0;
    }

    /**
     * Scopes
     */
    public function scopeActive($query)
    {
        return $query->where('IsActive', true);
    }

    /**
     * Static helper: get default active model
     */
    public static function getDefaultModel()
    {
        return static::active()->first();
    }
}
