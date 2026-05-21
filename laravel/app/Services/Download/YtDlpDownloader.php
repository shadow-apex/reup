<?php

namespace App\Services\Download;

use RuntimeException;
use Symfony\Component\Process\Exception\ProcessTimedOutException;
use Symfony\Component\Process\Process;

class YtDlpDownloader
{
    public function __construct(
        private readonly YtDlpBinaryResolver $binaryResolver = new YtDlpBinaryResolver,
    ) {}

    /**
     * Download video to $outputPath (final path). Uses a temp dir then moves the file.
     */
    public function download(string $url, string $outputPath, int $timeoutSeconds): DownloadResult
    {
        $outputPath = $this->normalizePath($outputPath);
        $dir = dirname($outputPath);
        if (! is_dir($dir) && ! @mkdir($dir, 0755, true) && ! is_dir($dir)) {
            throw new RuntimeException('Cannot create directory: '.$dir);
        }

        $tempDir = $dir.DIRECTORY_SEPARATOR.'.tmp_'.bin2hex(random_bytes(4));
        if (! @mkdir($tempDir, 0755, true) && ! is_dir($tempDir)) {
            throw new RuntimeException('Cannot create temp directory: '.$tempDir);
        }

        try {
            $template = $tempDir.DIRECTORY_SEPARATOR.'download.%(ext)s';
            $command = $this->buildCommand($url, $template);
            $process = new Process($command, null, null, null, (float) $timeoutSeconds);
            $process->run();

            if (! $process->isSuccessful()) {
                $detail = trim($process->getErrorOutput()."\n".$process->getOutput());
                throw new RuntimeException(
                    'yt-dlp failed (exit '.$process->getExitCode().'): '.mb_substr($detail, 0, 2000)
                );
            }

            $downloaded = $this->findDownloadedFile($tempDir);
            if ($downloaded === null) {
                throw new RuntimeException('yt-dlp produced no output file in '.$tempDir);
            }

            if (is_file($outputPath)) {
                @unlink($outputPath);
            }
            if (! @rename($downloaded, $outputPath)) {
                if (! @copy($downloaded, $outputPath)) {
                    throw new RuntimeException('Failed to move download to '.$outputPath);
                }
                @unlink($downloaded);
            }

            $metadata = $this->fetchMetadata($url, $timeoutSeconds);

            return new DownloadResult(
                $outputPath,
                (int) filesize($outputPath),
                $metadata,
            );
        } catch (ProcessTimedOutException $e) {
            throw new RuntimeException('yt-dlp timed out after '.$timeoutSeconds.'s', 0, $e);
        } finally {
            $this->removeDirectory($tempDir);
        }
    }

    /**
     * @return array<string, mixed>
     */
    public function fetchMetadata(string $url, int $timeoutSeconds): array
    {
        $command = $this->buildMetadataCommand($url);
        $process = new Process($command, null, null, null, (float) $timeoutSeconds);
        $process->run();

        if (! $process->isSuccessful()) {
            return [];
        }

        $line = trim($process->getOutput());
        if ($line === '') {
            return [];
        }

        $decoded = json_decode($line, true);

        return is_array($decoded) ? $decoded : [];
    }

    /**
     * @return list<string>
     */
    private function buildCommand(string $url, string $outputTemplate): array
    {
        $command = [
            ...$this->binaryResolver->resolve(),
            '--no-playlist',
            '--no-warnings',
            '-f', 'bv*+ba/b',
            '--merge-output-format', 'mp4',
            '-o', $outputTemplate,
        ];

        return array_merge($command, $this->commonArgs(), [$url]);
    }

    /**
     * @return list<string>
     */
    private function buildMetadataCommand(string $url): array
    {
        $command = [
            ...$this->binaryResolver->resolve(),
            '--no-playlist',
            '--no-warnings',
            '--dump-single-json',
            '--skip-download',
        ];

        return array_merge($command, $this->commonArgs(), [$url]);
    }

    /**
     * @return list<string>
     */
    private function commonArgs(): array
    {
        $args = (array) config('video_storage.ytdlp.extra_args', []);
        $cookies = config('video_storage.ytdlp.cookies_file');
        if (is_string($cookies) && $cookies !== '' && is_file($cookies)) {
            $args[] = '--cookies';
            $args[] = $cookies;
        }

        return $args;
    }

    private function findDownloadedFile(string $directory): ?string
    {
        $files = glob($directory.DIRECTORY_SEPARATOR.'download.*');
        if ($files === false || $files === []) {
            $files = glob($directory.DIRECTORY_SEPARATOR.'*');
        }
        if ($files === false) {
            return null;
        }

        $candidates = array_filter($files, fn (string $f) => is_file($f));
        if ($candidates === []) {
            return null;
        }

        usort($candidates, fn (string $a, string $b) => filesize($b) <=> filesize($a));

        return $candidates[0];
    }

    private function normalizePath(string $path): string
    {
        $real = realpath(dirname($path));
        if ($real !== false) {
            return $real.DIRECTORY_SEPARATOR.basename($path);
        }

        return $path;
    }

    private function removeDirectory(string $directory): void
    {
        if (! is_dir($directory)) {
            return;
        }

        $items = scandir($directory);
        if ($items === false) {
            return;
        }

        foreach ($items as $item) {
            if ($item === '.' || $item === '..') {
                continue;
            }
            $path = $directory.DIRECTORY_SEPARATOR.$item;
            if (is_dir($path)) {
                $this->removeDirectory($path);
            } else {
                @unlink($path);
            }
        }

        @rmdir($directory);
    }
}
