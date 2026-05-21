<?php

namespace App\Services\Download;

class DouyinUrlNormalizer
{
    /**
     * Convert share/jingxuan/modal links to canonical /video/{id} for yt-dlp Douyin extractor.
     */
    public function normalize(string $url): string
    {
        $url = trim($url);
        if ($url === '') {
            return $url;
        }

        if (! $this->isDouyinHost($url)) {
            return $url;
        }

        $parts = parse_url($url);
        if (! is_array($parts)) {
            return $url;
        }

        $query = [];
        if (isset($parts['query']) && is_string($parts['query'])) {
            parse_str($parts['query'], $query);
        }

        if (isset($query['modal_id']) && preg_match('/^\d{5,}$/', (string) $query['modal_id'])) {
            return 'https://www.douyin.com/video/'.$query['modal_id'];
        }

        $path = (string) ($parts['path'] ?? '');
        if (preg_match('#/video/(\d{5,})#', $path, $matches)) {
            return 'https://www.douyin.com/video/'.$matches[1];
        }

        if (preg_match('#/share/video/(\d{5,})#', $path, $matches)) {
            return 'https://www.douyin.com/video/'.$matches[1];
        }

        if (preg_match('#/note/(\d{5,})#', $path, $matches)) {
            return 'https://www.douyin.com/video/'.$matches[1];
        }

        return $url;
    }

    private function isDouyinHost(string $url): bool
    {
        $host = parse_url($url, PHP_URL_HOST);

        if (! is_string($host) || $host === '') {
            return false;
        }

        $host = strtolower($host);

        return str_contains($host, 'douyin.com')
            || str_contains($host, 'iesdouyin.com')
            || str_contains($host, 'douyin.cn');
    }
}
