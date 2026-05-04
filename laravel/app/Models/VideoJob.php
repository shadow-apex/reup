<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class VideoJob extends Model
{
    protected $fillable = [
        'job_id',
        'status',
        'input_path',
        'output_path',
        'worker_payload',
        'last_error',
    ];

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
