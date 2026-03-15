<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        Schema::table('ml_models', function (Blueprint $table) {
            $table->string('MlflowRunId', 100)->nullable()->after('MAEValue');
            $table->string('ZenmlPipelineId', 100)->nullable()->after('MlflowRunId');
            $table->unsignedBigInteger('TrainedBy')->nullable()->after('ZenmlPipelineId');
            $table->dateTime('CreatedDate')->default(DB::raw('CURRENT_TIMESTAMP'))->after('TrainedBy');
            $table->dateTime('UpdatedDate')->nullable()->after('CreatedDate');
            $table->unsignedBigInteger('DatasetId')->nullable()->after('UpdatedDate');

            // Thiết lập khóa ngoại (giả sử bảng dataset tên là 'datasets')
            $table->foreign('DatasetId')->references('DatasetId')->on('datasets')->onDelete('set null');
            $table->foreign('TrainedBy')->references('id')->on('users')->onDelete('set null');
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::table('ml_models', function (Blueprint $table) {
            $table->dropForeign(['DatasetId']);
            $table->dropColumn([
                'MlflowRunId',
                'ZenmlPipelineId',
                'TrainedBy',
                'CreatedDate',
                'UpdatedDate',
                'DatasetId',
            ]);
        });
    }
};
