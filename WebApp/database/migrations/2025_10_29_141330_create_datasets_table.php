<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Run the migrations.
     */
    public function up(): void
    {
       Schema::create('datasets', function (Blueprint $table) {
            $table->id('DatasetId'); // Khóa chính
            $table->string('DatasetName', 255);
            $table->string('FilePath', 255); // Đường dẫn file lưu trên server
            $table->text('Description')->nullable();
            $table->foreignId('UploadedBy')->constrained('users'); // FK -> users.id
            $table->timestamp('UploadDate')->useCurrent();
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('datasets');
    }
};
