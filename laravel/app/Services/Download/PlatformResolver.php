<?php

namespace App\Services\Download;

class PlatformResolver
{
    public function resolve(string $url): string
    {
        $host = parse_url($url, PHP_URL_HOST);
        if (! is_string($host) || $host === '') {
            return 'unknown';
        }

        $host = strtolower($host);

        if (
            str_contains($host, 'douyin.com')
            || str_contains($host, 'iesdouyin.com')
            || str_contains($host, 'douyin.cn')
        ) {
            return 'douyin';
        }

        if (str_contains($host, 'bilibili.com')) {
            return 'bilibili';
        }

        if (str_contains($host, 'youtube.com') || str_contains($host, 'youtu.be')) {
            return 'youtube';
        }

        return 'unknown';
    }
}
