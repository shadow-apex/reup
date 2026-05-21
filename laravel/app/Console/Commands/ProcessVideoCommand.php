<?php

namespace App\Console\Commands;

use App\Models\SourceVideo;
use App\Models\VideoJob;
use App\Services\Download\SourceVideoStorage;
use App\Services\VideoWorkerClient;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\File;
use Illuminate\Support\Str;
use Throwable;

class ProcessVideoCommand extends Command
{
    protected $signature = 'video:process
                            {input? : Path to input video (absolute or relative to project root)}
                            {--source-video= : source_videos.id — uses stored file_path, no copy}';

    protected $description = 'Dispatch worker job for a local file or a completed source_video';

    public function handle(VideoWorkerClient $client, SourceVideoStorage $storage): int
    {
        $sourceVideoId = $this->option('source-video');
        $sourceVideo = null;
        $resolved = null;

        if ($sourceVideoId !== null && $sourceVideoId !== '') {
            $sourceVideo = SourceVideo::query()->find($sourceVideoId);
            if ($sourceVideo === null) {
                $this->error('Source video not found: '.$sourceVideoId);

                return self::FAILURE;
            }
            if ($sourceVideo->status !== SourceVideo::STATUS_COMPLETED || $sourceVideo->file_path === null) {
                $this->error('Source video is not ready for processing (status='.$sourceVideo->status.')');

                return self::FAILURE;
            }
            $resolved = realpath($sourceVideo->file_path) ?: $sourceVideo->file_path;
            if (! is_file($resolved)) {
                $this->error('Source video file missing: '.$sourceVideo->file_path);

                return self::FAILURE;
            }
        } else {
            $raw = (string) $this->argument('input');
            if ($raw === '') {
                $this->error('Provide {input} path or --source-video=');

                return self::FAILURE;
            }
            $resolved = $this->resolveInputPath($raw);
            if ($resolved === null || ! is_file($resolved)) {
                $this->error('Input file not found: '.$raw);

                return self::FAILURE;
            }
        }

        $jobId = (string) Str::uuid();
        $outDir = $storage->outDir();

        if ($sourceVideo !== null) {
            $storedInput = $resolved;
        } else {
            $inDir = $storage->basePath().DIRECTORY_SEPARATOR.'in';
            File::ensureDirectoryExists($inDir);
            $ext = pathinfo($resolved, PATHINFO_EXTENSION) ?: 'mp4';
            $storedInput = $inDir.DIRECTORY_SEPARATOR.$jobId.'.'.$ext;
            if (! @copy($resolved, $storedInput)) {
                $this->error('Failed to copy input to '.$storedInput);

                return self::FAILURE;
            }
        }

        $videoJob = VideoJob::query()->create([
            'source_video_id' => $sourceVideo?->id,
            'job_id' => $jobId,
            'status' => 'queued',
            'input_path' => $storedInput,
            'output_path' => null,
            'worker_payload' => [
                'output_dir' => $outDir,
            ],
            'last_error' => null,
        ]);

        $this->info('Job '.$jobId.' queued.');

        try {
            $client->submitJob($jobId, $storedInput, $outDir);
        } catch (Throwable $e) {
            $videoJob->update([
                'status' => 'failed',
                'last_error' => [
                    'code' => 'LARAVEL_DISPATCH',
                    'message' => $e->getMessage(),
                ],
            ]);
            $this->error($e->getMessage());

            return self::FAILURE;
        }

        $videoJob->update(['status' => 'processing']);

        try {
            $final = $client->pollUntilTerminal($jobId);
        } catch (Throwable $e) {
            $videoJob->update([
                'status' => 'failed',
                'last_error' => [
                    'code' => 'LARAVEL_POLL',
                    'message' => $e->getMessage(),
                ],
            ]);
            $this->error($e->getMessage());

            return self::FAILURE;
        }

        $status = $final['status'] ?? 'unknown';
        if ($status === 'completed') {
            $videoJob->update([
                'status' => 'completed',
                'output_path' => $final['output_video_path'] ?? null,
                'last_error' => null,
            ]);
            $this->info('Completed. Output: '.($final['output_video_path'] ?? '(none)'));

            return self::SUCCESS;
        }

        $videoJob->update([
            'status' => 'failed',
            'output_path' => null,
            'last_error' => isset($final['error']) && is_array($final['error'])
                ? $final['error']
                : ['code' => 'WORKER_FAILED', 'message' => (string) json_encode($final)],
        ]);
        $this->error('Worker reported failed: '.json_encode($final['error'] ?? $final));

        return self::FAILURE;
    }

    private function resolveInputPath(string $raw): ?string
    {
        if ($raw === '') {
            return null;
        }
        if (preg_match('#^[a-zA-Z]:[/\\\\]#', $raw) || str_starts_with($raw, '\\\\')) {
            return realpath($raw) ?: $raw;
        }
        if (str_starts_with($raw, '/')) {
            return realpath($raw) ?: $raw;
        }

        $candidate = base_path($raw);

        return realpath($candidate) ?: (is_file($candidate) ? $candidate : null);
    }
}
