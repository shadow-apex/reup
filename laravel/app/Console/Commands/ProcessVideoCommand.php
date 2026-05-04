<?php

namespace App\Console\Commands;

use App\Models\VideoJob;
use App\Services\VideoWorkerClient;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\File;
use Illuminate\Support\Str;
use Throwable;

class ProcessVideoCommand extends Command
{
    protected $signature = 'video:process {input : Path to input video (absolute or relative to project root)}';

    protected $description = 'Copy input to storage, dispatch worker job, poll until completed or failed';

    public function handle(VideoWorkerClient $client): int
    {
        $raw = (string) $this->argument('input');
        $resolved = $this->resolveInputPath($raw);
        if ($resolved === null || ! is_file($resolved)) {
            $this->error('Input file not found: '.$raw);

            return self::FAILURE;
        }

        $jobId = (string) Str::uuid();
        $inDir = storage_path('app/private/in');
        $outDir = storage_path('app/private/out');
        File::ensureDirectoryExists($inDir);
        File::ensureDirectoryExists($outDir);

        $ext = pathinfo($resolved, PATHINFO_EXTENSION) ?: 'mp4';
        $storedInput = $inDir.DIRECTORY_SEPARATOR.$jobId.'.'.$ext;
        if (! @copy($resolved, $storedInput)) {
            $this->error('Failed to copy input to '.$storedInput);

            return self::FAILURE;
        }

        $videoJob = VideoJob::query()->create([
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
