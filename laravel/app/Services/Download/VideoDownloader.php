<?php

namespace App\Services\Download;

use App\Models\SourceVideo;
use Illuminate\Support\Facades\Log;
use RuntimeException;

class VideoDownloader
{
    public function __construct(
        private readonly YtDlpDownloader $ytDlp,
        private readonly SourceUrlResolver $urlResolver,
        private readonly SourceVideoStorage $storage,
    ) {}

    public function downloadFromUrl(string $url): SourceVideo
    {
        $resolved = $this->urlResolver->resolve($url);
        if ($resolved->originalUrl === '') {
            throw new RuntimeException('URL is empty');
        }

        $existing = $this->findCompletedByUrl($resolved->originalUrl, $resolved->downloadUrl);
        if ($existing !== null) {
            Log::info('source_video.url_dedupe', ['source_video_id' => $existing->id]);

            return $existing;
        }

        $metadataJson = null;
        if ($resolved->wasNormalized()) {
            $metadataJson = [
                'resolved_url' => $resolved->downloadUrl,
            ];
        }

        $sourceVideo = SourceVideo::query()->create([
            'source_url' => $resolved->originalUrl,
            'platform' => $resolved->platform,
            'status' => SourceVideo::STATUS_PENDING,
            'download_attempts' => 0,
            'metadata_json' => $metadataJson,
        ]);

        return $this->runDownload($sourceVideo, $resolved->downloadUrl);
    }

    public function runDownload(SourceVideo $sourceVideo, ?string $downloadUrl = null): SourceVideo
    {
        $downloadUrl ??= $this->resolveDownloadUrlFromRecord($sourceVideo);

        $maxAttempts = (int) config('video_storage.download.max_attempts', 3);
        $timeoutSeconds = (int) config('video_storage.download.timeout_seconds', 600);
        $backoffMs = (array) config('video_storage.download.backoff_ms', [2000, 8000, 32000]);

        $extension = 'mp4';
        $destination = $this->storage->destinationPath($sourceVideo, $extension);

        for ($attempt = 1; $attempt <= $maxAttempts; $attempt++) {
            $sourceVideo->update([
                'status' => SourceVideo::STATUS_DOWNLOADING,
                'download_attempts' => $attempt,
                'last_error' => null,
            ]);

            Log::info('source_video.download_attempt', [
                'source_video_id' => $sourceVideo->id,
                'attempt' => $attempt,
                'download_url' => $downloadUrl,
            ]);

            try {
                $result = $this->ytDlp->download(
                    $downloadUrl,
                    $destination,
                    $timeoutSeconds,
                );

                $sha256 = hash_file('sha256', $result->filePath);
                if ($sha256 === false) {
                    throw new RuntimeException('Failed to compute sha256');
                }

                $duplicate = SourceVideo::query()
                    ->where('sha256', $sha256)
                    ->where('status', SourceVideo::STATUS_COMPLETED)
                    ->where('id', '!=', $sourceVideo->id)
                    ->first();

                if ($duplicate !== null) {
                    @unlink($result->filePath);
                    $this->removeEmptyDir(dirname($result->filePath));

                    Log::info('source_video.hash_dedupe', [
                        'source_video_id' => $sourceVideo->id,
                        'existing_id' => $duplicate->id,
                    ]);

                    $sourceVideo->update([
                        'status' => SourceVideo::STATUS_FAILED,
                        'last_error' => [
                            'code' => 'DUPLICATE_HASH',
                            'message' => 'Video already stored',
                            'detail' => 'Reusing source_video_id '.$duplicate->id,
                            'existing_source_video_id' => $duplicate->id,
                        ],
                    ]);

                    return $duplicate->fresh() ?? $duplicate;
                }

                $meta = $result->metadata;
                $storedMeta = $this->mergeMetadata($sourceVideo->metadata_json, $meta);

                $sourceVideo->update([
                    'status' => SourceVideo::STATUS_COMPLETED,
                    'file_path' => $result->filePath,
                    'sha256' => $sha256,
                    'file_size_bytes' => $result->fileSizeBytes,
                    'external_id' => $this->extractExternalId($meta),
                    'title' => isset($meta['title']) ? (string) $meta['title'] : null,
                    'author' => $this->extractAuthor($meta),
                    'duration_seconds' => isset($meta['duration']) ? (int) round((float) $meta['duration']) : null,
                    'metadata_json' => $storedMeta,
                    'last_error' => null,
                ]);

                return $sourceVideo->fresh() ?? $sourceVideo;
            } catch (RuntimeException $e) {
                $sourceVideo->update([
                    'last_error' => $this->formatDownloadError($e),
                ]);

                if ($attempt >= $maxAttempts) {
                    $sourceVideo->update(['status' => SourceVideo::STATUS_FAILED]);

                    return $sourceVideo->fresh() ?? $sourceVideo;
                }

                $sleepMs = (int) ($backoffMs[$attempt - 1] ?? end($backoffMs));
                usleep($sleepMs * 1000);
            }
        }

        $sourceVideo->update(['status' => SourceVideo::STATUS_FAILED]);

        return $sourceVideo->fresh() ?? $sourceVideo;
    }

    private function findCompletedByUrl(string $originalUrl, string $downloadUrl): ?SourceVideo
    {
        $urls = array_values(array_unique([$originalUrl, $downloadUrl]));

        return SourceVideo::query()
            ->whereIn('source_url', $urls)
            ->where('status', SourceVideo::STATUS_COMPLETED)
            ->first();
    }

    private function resolveDownloadUrlFromRecord(SourceVideo $sourceVideo): string
    {
        $meta = $sourceVideo->metadata_json;
        if (is_array($meta) && isset($meta['resolved_url']) && is_string($meta['resolved_url'])) {
            return $meta['resolved_url'];
        }

        return $this->urlResolver->resolve($sourceVideo->source_url)->downloadUrl;
    }

    /**
     * @param  array<string, mixed>|null  $existing
     * @param  array<string, mixed>  $fromYtDlp
     * @return array<string, mixed>|null
     */
    private function mergeMetadata(?array $existing, array $fromYtDlp): ?array
    {
        if ($fromYtDlp === [] && $existing === null) {
            return null;
        }

        $base = $existing ?? [];

        return array_merge($base, ['ytdlp' => $fromYtDlp]);
    }

    /**
     * @return array{code: string, message: string, detail: string|null}
     */
    private function formatDownloadError(RuntimeException $e): array
    {
        $message = $e->getMessage();
        $lower = strtolower($message);

        if (str_contains($lower, 'unsupported url')) {
            return [
                'code' => 'DOWNLOAD_UNSUPPORTED_URL',
                'message' => 'URL format is not supported by yt-dlp. For Douyin jingxuan/share links, use a /video/{id} URL or a link with modal_id.',
                'detail' => mb_substr($message, 0, 2000),
            ];
        }

        if (str_contains($lower, 'cookies') || str_contains($lower, 'cookie')) {
            return [
                'code' => 'DOWNLOAD_COOKIES_REQUIRED',
                'message' => 'Douyin requires fresh browser cookies. Set YTDLP_COOKIES_FILE in laravel/.env to an exported cookies.txt file.',
                'detail' => mb_substr($message, 0, 2000),
            ];
        }

        $code = str_contains($lower, 'timed out') ? 'DOWNLOAD_TIMEOUT' : 'DOWNLOAD_FAILED';

        return [
            'code' => $code,
            'message' => $message,
            'detail' => null,
        ];
    }

    /**
     * @param  array<string, mixed>  $meta
     */
    private function extractExternalId(array $meta): ?string
    {
        if (isset($meta['id'])) {
            return (string) $meta['id'];
        }

        return null;
    }

    /**
     * @param  array<string, mixed>  $meta
     */
    private function extractAuthor(array $meta): ?string
    {
        if (isset($meta['uploader']) && is_string($meta['uploader'])) {
            return $meta['uploader'];
        }
        if (isset($meta['channel']) && is_string($meta['channel'])) {
            return $meta['channel'];
        }

        return null;
    }

    private function removeEmptyDir(string $dir): void
    {
        if (! is_dir($dir)) {
            return;
        }

        $entries = scandir($dir);
        if ($entries === false) {
            return;
        }

        $onlyDots = array_diff($entries, ['.', '..']);
        if ($onlyDots === []) {
            @rmdir($dir);
        }
    }
}
