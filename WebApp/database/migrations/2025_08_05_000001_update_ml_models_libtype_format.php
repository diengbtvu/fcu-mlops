<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;
use Illuminate\Support\Facades\DB;

return new class extends Migration
{
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        // Update existing LibType values to match the new format
        // Only update if the old values exist
        DB::table('ml_models')->whereIn('LibType', ['TensorFlow', 'Keras'])
            ->update(['LibType' => 'keras']);
            
        DB::table('ml_models')->where('LibType', 'PyTorch')
            ->update(['LibType' => 'pytorch']);
            
        DB::table('ml_models')->where('LibType', 'Scikit-learn')
            ->update(['LibType' => 'sklearn']);
            
        DB::table('ml_models')->whereIn('LibType', ['Other', 'Pickle'])
            ->update(['LibType' => 'pickle']);
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        // Reverse the changes
        DB::table('ml_models')->where('LibType', 'keras')
            ->update(['LibType' => 'Keras']);
            
        DB::table('ml_models')->where('LibType', 'pytorch')
            ->update(['LibType' => 'PyTorch']);
            
        DB::table('ml_models')->where('LibType', 'sklearn')
            ->update(['LibType' => 'Scikit-learn']);
            
        DB::table('ml_models')->where('LibType', 'pickle')
            ->update(['LibType' => 'Other']);
    }
};
