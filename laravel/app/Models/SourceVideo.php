<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;

class SourceVideo extends Model
{
    public const STATUS_PENDING = 'pending';

    public const STATUS_DOWNLOADING = 'downloading';

    public const STATUS_COMPLETED = 'completed';

    public const STATUS_FAILED = 'failed';

    protected $fillable = [
        'source_url',
        'platform',
        'external_id',
        'title',
        'author',
        'duration_seconds',
        'file_path',
        'sha256',
        'file_size_bytes',
        'status',
        'metadata_json',
        'last_error',
        'download_attempts',
    ];

    /**
     * @return array<string, string>
     */
    protected function casts(): array
    {
        return [
            'metadata_json' => 'array',
            'last_error' => 'array',
            'duration_seconds' => 'integer',
            'file_size_bytes' => 'integer',
            'download_attempts' => 'integer',
        ];
    }

    public function videoJobs(): HasMany
    {
        return $this->hasMany(VideoJob::class);
    }

    public function isCompleted(): bool
    {
        return $this->status === self::STATUS_COMPLETED;
    }
}
