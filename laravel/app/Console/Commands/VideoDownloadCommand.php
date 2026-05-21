<?php

namespace App\Console\Commands;

use App\Models\SourceVideo;
use App\Services\Download\VideoDownloader;
use Illuminate\Console\Command;

class VideoDownloadCommand extends Command
{
    protected $signature = 'video:download {url : Source video URL (Douyin-first via yt-dlp)}';

    protected $description = 'Download source video via yt-dlp, persist metadata and sha256';

    public function handle(VideoDownloader $downloader): int
    {
        $url = (string) $this->argument('url');

        try {
            $sourceVideo = $downloader->downloadFromUrl($url);
        } catch (\Throwable $e) {
            $this->error($e->getMessage());

            return self::FAILURE;
        }

        if ($sourceVideo->status !== SourceVideo::STATUS_COMPLETED) {
            $this->error('Download failed: '.json_encode($sourceVideo->last_error));
            if (($sourceVideo->last_error['code'] ?? '') === 'DOWNLOAD_COOKIES_REQUIRED') {
                $this->line('Set YTDLP_COOKIES_FILE in .env to a cookies.txt exported from douyin.com (logged in).');
            }

            return self::FAILURE;
        }

        $this->info('source_video_id='.$sourceVideo->id);
        $this->info('file_path='.$sourceVideo->file_path);
        $this->info('sha256='.$sourceVideo->sha256);
        $this->info('platform='.$sourceVideo->platform);

        $resolved = is_array($sourceVideo->metadata_json)
            ? ($sourceVideo->metadata_json['resolved_url'] ?? null)
            : null;
        if (is_string($resolved) && $resolved !== '') {
            $this->info('resolved_url='.$resolved);
        }

        return self::SUCCESS;
    }
}
