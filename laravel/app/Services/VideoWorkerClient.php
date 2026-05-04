<?php

namespace App\Services;

use Illuminate\Support\Facades\Http;
use RuntimeException;

class VideoWorkerClient
{
    public function health(): array
    {
        $url = $this->base().'/health';

        return Http::timeout($this->timeout())
            ->get($url)
            ->throw()
            ->json();
    }

    /**
     * @param  array{source_language?: string, target_language?: string}  $options
     */
    public function submitJob(string $jobId, string $inputVideoPath, string $outputDir, array $options = []): void
    {
        $payload = [
            'contract_version' => '1',
            'job_id' => $jobId,
            'input_video_path' => $inputVideoPath,
            'output_dir' => $outputDir,
            'source_language' => $options['source_language'] ?? 'zh',
            'target_language' => $options['target_language'] ?? 'vi',
        ];

        $response = Http::timeout($this->timeout())
            ->withHeaders($this->headers())
            ->acceptJson()
            ->post($this->base().'/v1/jobs', $payload);

        if ($response->status() === 401) {
            throw new RuntimeException('Worker rejected secret (401).');
        }

        if ($response->status() === 422) {
            $this->throwFromWorkerError($response->json(), 'Worker validation error');
        }

        if ($response->status() >= 400) {
            throw new RuntimeException('Worker POST /v1/jobs failed: HTTP '.$response->status().' '.$response->body());
        }
    }

    public function getJobStatus(string $jobId): array
    {
        $response = Http::timeout($this->timeout())
            ->withHeaders($this->headers())
            ->acceptJson()
            ->get($this->base().'/v1/jobs/'.$jobId);

        if ($response->status() === 404) {
            throw new RuntimeException('Worker job not found: '.$jobId);
        }

        if ($response->status() >= 400) {
            $this->throwFromWorkerError($response->json(), 'Worker GET job failed');
        }

        return $response->json();
    }

    /**
     * Poll until status is terminal (completed | failed).
     *
     * @return array<string, mixed>
     */
    public function pollUntilTerminal(string $jobId): array
    {
        $intervalMs = (int) config('video_worker.poll_interval_ms', 250);
        $max = (int) config('video_worker.poll_max_attempts', 600);

        for ($i = 0; $i < $max; $i++) {
            $body = $this->getJobStatus($jobId);
            $status = $body['status'] ?? 'unknown';
            if (in_array($status, ['completed', 'failed'], true)) {
                return $body;
            }
            usleep($intervalMs * 1000);
        }

        throw new RuntimeException('Worker job polling timed out: '.$jobId);
    }

    private function base(): string
    {
        return (string) config('video_worker.base_url');
    }

    private function timeout(): int
    {
        return (int) config('video_worker.timeout_seconds', 120);
    }

    /**
     * @return array<string, string>
     */
    private function headers(): array
    {
        $secret = (string) config('video_worker.secret');
        if ($secret === '') {
            throw new RuntimeException('VIDEO_WORKER_SECRET is not set.');
        }

        return [
            'X-Worker-Secret' => $secret,
        ];
    }

    /**
     * @param  array<string, mixed>|null  $json
     */
    private function throwFromWorkerError(?array $json, string $prefix): void
    {
        $err = $json['error'] ?? null;
        if (is_array($err)) {
            $code = $err['code'] ?? 'UNKNOWN';
            $message = $err['message'] ?? '';
            $detail = $err['detail'] ?? null;
            $ff = $err['ffmpeg_exit_code'] ?? null;
            throw new RuntimeException($prefix.": [{$code}] {$message}".($detail ? ' — '.(string) $detail : '').($ff !== null ? " (ffmpeg {$ff})" : ''));
        }

        throw new RuntimeException($prefix.': '.json_encode($json));
    }
}
