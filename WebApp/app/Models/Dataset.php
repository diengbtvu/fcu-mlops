<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

class Dataset extends Model
{
    use HasFactory;

    protected $table = 'datasets';
    protected $primaryKey = 'DatasetId';
    public $timestamps = true;

    protected $fillable = [
        'DatasetName',
        'FilePath',
        'Description',
        'UploadedBy',
        'UploadDate',
    ];

    /**
     * Relationships
     */
    
    // Liên kết đến User (người upload dataset)
    public function user()
    {
        return $this->belongsTo(User::class, 'UploadedBy', 'id');
    }

    // Liên kết đến MLModels (các models được train từ dataset này)
    public function mlModels()
    {
        return $this->hasMany(MLModel::class, 'DatasetId', 'DatasetId');
    }
}
