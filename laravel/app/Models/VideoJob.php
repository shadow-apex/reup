<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class VideoJob extends Model
{
    protected $fillable = [
        'source_video_id',
        'job_id',
        'status',
        'input_path',
        'output_path',
        'worker_payload',
        'last_error',
    ];

    public function sourceVideo(): BelongsTo
    {
        return $this->belongsTo(SourceVideo::class);
    }

    /**
     * @return array<string, string>
     */
    protected function casts(): array
    {
        return [
            'worker_payload' => 'array',
            'last_error' => 'array',
        ];
    }
}
