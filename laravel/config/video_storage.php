<?php

return [

    'base_path' => storage_path('app/private'),

    'sources_dir' => 'sources',

    'processed_dir' => 'processed',

    'out_dir' => 'out',

    'ytdlp' => [
        // Empty or "yt-dlp" = auto-detect (Windows Scripts folder, python -m yt_dlp)
        'path' => env('YTDLP_PATH', 'yt-dlp'),
        'cookies_file' => env('YTDLP_COOKIES_FILE'),
        'extra_args' => array_values(array_filter(
            array_map('trim', explode(' ', (string) env('YTDLP_EXTRA_ARGS', '')))
        )),
    ],

    'download' => [
        'max_attempts' => (int) env('DOWNLOAD_MAX_ATTEMPTS', 3),
        'timeout_seconds' => (int) env('DOWNLOAD_TIMEOUT_SECONDS', 600),
        'backoff_ms' => [2000, 8000, 32000],
    ],

];
