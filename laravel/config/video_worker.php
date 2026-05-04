<?php

return [
    'base_url' => rtrim(env('VIDEO_WORKER_BASE_URL', 'http://127.0.0.1:8765'), '/'),
    'secret' => env('VIDEO_WORKER_SECRET', ''),
    'timeout_seconds' => (int) env('VIDEO_WORKER_TIMEOUT', 120),
    'poll_interval_ms' => (int) env('VIDEO_WORKER_POLL_MS', 250),
    'poll_max_attempts' => (int) env('VIDEO_WORKER_POLL_MAX', 600),
];
