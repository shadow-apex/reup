<?php

namespace Tests\Feature;

use App\Models\VideoJob;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\Client\Request;
use Illuminate\Support\Facades\Artisan;
use Illuminate\Support\Facades\Http;
use Tests\TestCase;

class VideoProcessCommandFailedTest extends TestCase
{
    use RefreshDatabase;

    public function test_video_process_records_worker_failure(): void
    {
        config([
            'video_worker.base_url' => 'http://127.0.0.1:8765',
            'video_worker.secret' => 'test-secret',
            'video_worker.poll_interval_ms' => 1,
            'video_worker.poll_max_attempts' => 20,
        ]);

        $input = storage_path('app/temp_test_input_fail.mp4');
        if (! is_dir(dirname($input))) {
            mkdir(dirname($input), 0755, true);
        }
        file_put_contents($input, 'fake');

        $jobIdHolder = ['id' => ''];

        Http::fake(function (Request $request) use (&$jobIdHolder) {
            $url = $request->url();
            if ($request->method() === 'POST' && str_contains($url, '/v1/jobs')) {
                $body = json_decode($request->body(), true);
                $jobIdHolder['id'] = (string) ($body['job_id'] ?? '');

                return Http::response([
                    'contract_version' => '1',
                    'job_id' => $jobIdHolder['id'],
                    'status' => 'queued',
                ], 202);
            }
            if ($request->method() === 'GET' && str_contains($url, '/v1/jobs/'.$jobIdHolder['id'])) {
                return Http::response([
                    'contract_version' => '1',
                    'job_id' => $jobIdHolder['id'],
                    'status' => 'failed',
                    'message' => null,
                    'output_video_path' => null,
                    'error' => [
                        'code' => 'FFMPEG_ERROR',
                        'message' => 'ffmpeg exited with code 1',
                        'detail' => 'mock',
                        'ffmpeg_exit_code' => 1,
                    ],
                ], 200);
            }

            return Http::response([], 500);
        });

        $exit = Artisan::call('video:process', ['input' => $input]);

        $this->assertSame(1, $exit);
        $job = VideoJob::query()->first();
        $this->assertNotNull($job);
        $this->assertSame('failed', $job->status);
        $this->assertIsArray($job->last_error);
        $this->assertSame('FFMPEG_ERROR', $job->last_error['code']);
        $this->assertSame(1, $job->last_error['ffmpeg_exit_code']);
    }
}
