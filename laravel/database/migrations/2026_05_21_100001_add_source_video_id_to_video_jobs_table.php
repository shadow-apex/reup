<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('video_jobs', function (Blueprint $table) {
            $table->foreignId('source_video_id')
                ->nullable()
                ->after('id')
                ->constrained('source_videos')
                ->nullOnDelete();
        });
    }

    public function down(): void
    {
        Schema::table('video_jobs', function (Blueprint $table) {
            $table->dropConstrainedForeignId('source_video_id');
        });
    }
};
