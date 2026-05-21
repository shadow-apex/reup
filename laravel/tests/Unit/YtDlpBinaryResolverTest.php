<?php

namespace Tests\Unit;

use App\Services\Download\YtDlpBinaryResolver;
use Tests\TestCase;

class YtDlpBinaryResolverTest extends TestCase
{
    public function test_resolve_returns_runnable_prefix(): void
    {
        $appData = getenv('APPDATA');
        if (! is_string($appData) || ! is_file($appData.'\\Python\\Python311\\Scripts\\yt-dlp.exe')) {
            $this->markTestSkipped('yt-dlp not installed in expected Windows location');
        }

        config(['video_storage.ytdlp.path' => 'yt-dlp']);

        $prefix = (new YtDlpBinaryResolver)->resolve();

        $this->assertNotEmpty($prefix);
        $this->assertTrue(
            is_file($prefix[0]) || $prefix[0] === 'yt-dlp' || ($prefix[0] ?? '') === 'python'
        );
    }

    public function test_resolve_honours_explicit_ytdlp_path(): void
    {
        $appData = getenv('APPDATA');
        if (! is_string($appData)) {
            $this->markTestSkipped('APPDATA not set');
        }

        $exe = $appData.'\\Python\\Python311\\Scripts\\yt-dlp.exe';
        if (! is_file($exe)) {
            $this->markTestSkipped('yt-dlp.exe not found');
        }

        config(['video_storage.ytdlp.path' => $exe]);

        $prefix = (new YtDlpBinaryResolver)->resolve();

        $this->assertSame([$exe], $prefix);
    }
}
