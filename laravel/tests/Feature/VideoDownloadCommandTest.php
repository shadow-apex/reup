<?php

namespace Tests\Feature;

use App\Models\SourceVideo;
use App\Services\Download\DownloadResult;
use App\Services\Download\YtDlpDownloader;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Artisan;
use Illuminate\Support\Facades\File;
use Tests\TestCase;

class VideoDownloadCommandTest extends TestCase
{
    use RefreshDatabase;

    public function test_video_download_persists_completed_source_video(): void
    {
        $base = storage_path('app/private/sources/2026/05/1');
        File::ensureDirectoryExists($base);
        $file = $base.DIRECTORY_SEPARATOR.'original.mp4';
        file_put_contents($file, 'video-bytes-for-hash');

        $metadata = [
            'id' => '7123456789',
            'title' => 'Test Douyin',
            'uploader' => 'creator1',
            'duration' => 12.5,
        ];

        $this->mock(YtDlpDownloader::class, function ($mock) use ($file, $metadata) {
            $mock->shouldReceive('download')
                ->once()
                ->andReturn(new DownloadResult($file, (int) filesize($file), $metadata));
        });

        $exit = Artisan::call('video:download', [
            'url' => 'https://www.douyin.com/video/7123456789',
        ]);

        $this->assertSame(0, $exit);
        $sv = SourceVideo::query()->first();
        $this->assertNotNull($sv);
        $this->assertSame(SourceVideo::STATUS_COMPLETED, $sv->status);
        $this->assertSame('douyin', $sv->platform);
        $this->assertSame('Test Douyin', $sv->title);
        $this->assertSame('creator1', $sv->author);
        $this->assertSame(13, $sv->duration_seconds);
        $this->assertNotNull($sv->sha256);
        $this->assertSame(hash_file('sha256', $file), $sv->sha256);
    }

    public function test_duplicate_url_returns_existing_without_second_download(): void
    {
        $url = 'https://www.douyin.com/video/existing';

        SourceVideo::query()->create([
            'source_url' => $url,
            'platform' => 'douyin',
            'status' => SourceVideo::STATUS_COMPLETED,
            'file_path' => storage_path('app/private/sources/2026/05/9/original.mp4'),
            'sha256' => hash('sha256', 'existing'),
            'file_size_bytes' => 8,
        ]);

        $this->mock(YtDlpDownloader::class, function ($mock) {
            $mock->shouldNotReceive('download');
        });

        $exit = Artisan::call('video:download', ['url' => $url]);

        $this->assertSame(0, $exit);
        $this->assertSame(1, SourceVideo::query()->count());
    }

    public function test_duplicate_hash_reuses_existing_record(): void
    {
        $base = storage_path('app/private/sources/2026/05/2');
        File::ensureDirectoryExists($base);
        $file = $base.DIRECTORY_SEPARATOR.'original.mp4';
        file_put_contents($file, 'same-content');

        $sha = hash_file('sha256', $file);

        SourceVideo::query()->create([
            'source_url' => 'https://www.douyin.com/video/first',
            'platform' => 'douyin',
            'status' => SourceVideo::STATUS_COMPLETED,
            'file_path' => $file,
            'sha256' => $sha,
            'file_size_bytes' => (int) filesize($file),
        ]);

        $this->mock(YtDlpDownloader::class, function ($mock) use ($file) {
            $mock->shouldReceive('download')
                ->once()
                ->andReturn(new DownloadResult($file, (int) filesize($file), ['id' => 'second']));
        });

        $exit = Artisan::call('video:download', [
            'url' => 'https://www.douyin.com/video/second',
        ]);

        $this->assertSame(0, $exit);
        $this->assertSame(2, SourceVideo::query()->count());
        $failed = SourceVideo::query()->where('source_url', 'https://www.douyin.com/video/second')->first();
        $this->assertNotNull($failed);
        $this->assertSame(SourceVideo::STATUS_FAILED, $failed->status);
        $this->assertSame('DUPLICATE_HASH', $failed->last_error['code'] ?? null);
    }

    public function test_download_retries_then_fails(): void
    {
        config(['video_storage.download.max_attempts' => 2]);

        $this->mock(YtDlpDownloader::class, function ($mock) {
            $mock->shouldReceive('download')
                ->twice()
                ->andThrow(new \RuntimeException('network error'));
        });

        $exit = Artisan::call('video:download', [
            'url' => 'https://www.douyin.com/video/fail',
        ]);

        $this->assertSame(1, $exit);
        $sv = SourceVideo::query()->first();
        $this->assertNotNull($sv);
        $this->assertSame(SourceVideo::STATUS_FAILED, $sv->status);
        $this->assertSame(2, $sv->download_attempts);
        $this->assertSame('DOWNLOAD_FAILED', $sv->last_error['code'] ?? null);
    }
}
