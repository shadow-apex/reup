<?php

return [

    /*
    |--------------------------------------------------------------------------
    | Third Party Services
    |--------------------------------------------------------------------------
    */

    'postmark' => [
        'key' => env('POSTMARK_API_KEY'),
    ],

    'resend' => [
        'key' => env('RESEND_API_KEY'),
    ],

    'ses' => [
        'key' => env('AWS_ACCESS_KEY_ID'),
        'secret' => env('AWS_SECRET_ACCESS_KEY'),
        'region' => env('AWS_DEFAULT_REGION', 'us-east-1'),
    ],

    'slack' => [
        'notifications' => [
            'bot_user_oauth_token' => env('SLACK_BOT_USER_OAUTH_TOKEN'),
            'channel' => env('SLACK_BOT_USER_DEFAULT_CHANNEL'),
        ],
    ],

    // ─── AI Translation (OpenAI-compatible) ───────────────────────────
    'openai' => [
        'api_key' => env('OPENAI_API_KEY', ''),
        'base_url' => env('OPENAI_BASE_URL', 'https://api.deepseek.com'),
        'model' => env('OPENAI_MODEL', 'deepseek-chat'),
        'source_language' => env('OPENAI_SOURCE_LANG', 'zh'),
        'target_language' => env('OPENAI_TARGET_LANG', 'vi'),
        'vol_orig' => (int) env('OPENAI_VOL_ORIG', 15),
    ],

];
