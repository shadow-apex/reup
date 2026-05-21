<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('source_videos', function (Blueprint $table) {
            $table->id();
            $table->text('source_url');
            $table->string('platform', 32);
            $table->string('external_id')->nullable();
            $table->string('title')->nullable();
            $table->string('author')->nullable();
            $table->unsignedInteger('duration_seconds')->nullable();
            $table->text('file_path')->nullable();
            $table->char('sha256', 64)->nullable();
            $table->unsignedBigInteger('file_size_bytes')->nullable();
            $table->string('status', 32);
            $table->json('metadata_json')->nullable();
            $table->json('last_error')->nullable();
            $table->unsignedSmallInteger('download_attempts')->default(0);
            $table->timestamps();

            $table->index('source_url');
            $table->index(['platform', 'status']);
            $table->unique('sha256');
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('source_videos');
    }
};
