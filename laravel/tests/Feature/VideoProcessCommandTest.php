<?php

namespace Tests\Feature;

use App\Models\VideoJob;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Artisan;
use Illuminate\Support\Facades\Http;
use Tests\TestCase;

class VideoProcessCommandTest extends TestCase
{
    use RefreshDatabase;

    public function test_video_process_happy_path_with_http_fake(): void
    {
        config([
            'video_worker.base_url' => 'http://127.0.0.1:8765',
            'video_worker.secret' => 'test-secret',
            'video_worker.poll_interval_ms' => 1,
            'video_worker.poll_max_attempts' => 20,
        ]);

        $input = storage_path('app/temp_test_input.mp4');
        if (! is_dir(dirname($input))) {
            mkdir(dirname($input), 0755, true);
        }
        file_put_contents($input, 'fake');

        $jobIdHolder = ['id' => ''];
        $state = ['polls' => 0];

        Http::fake(function (\Illuminate\Http\Client\Request $request) use (&$jobIdHolder, &$state) {
            $url = $request->url();
            if ($request->method() === 'POST' && str_contains($url, '/v1/jobs')) {
                $body = json_decode($request->body(), true);
                $jobIdHolder['id'] = (string) ($body['job_id'] ?? '');
                $this->assertSame('test-secret', $request->header('X-Worker-Secret')[0] ?? null);

                return Http::response([
                    'contract_version' => '1',
                    'job_id' => $jobIdHolder['id'],
                    'status' => 'queued',
                    'message' => 'Accepted',
                ], 202);
            }
            if ($request->method() === 'GET' && str_contains($url, '/v1/jobs/'.$jobIdHolder['id'])) {
                $state['polls']++;
                if ($state['polls'] < 2) {
                    return Http::response([
                        'contract_version' => '1',
                        'job_id' => $jobIdHolder['id'],
                        'status' => 'processing',
                        'message' => 'Running',
                        'output_video_path' => null,
                        'error' => null,
                    ], 200);
                }

                return Http::response([
                    'contract_version' => '1',
                    'job_id' => $jobIdHolder['id'],
                    'status' => 'completed',
                    'message' => 'Done',
                    'output_video_path' => 'D:\\out\\done.mp4',
                    'error' => null,
                ], 200);
            }

            return Http::response(['unexpected' => $url], 500);
        });

        $exit = Artisan::call('video:process', ['input' => $input]);

        $this->assertSame(0, $exit);
        $job = VideoJob::query()->first();
        $this->assertNotNull($job);
        $this->assertSame('completed', $job->status);
        $this->assertSame('D:\\out\\done.mp4', $job->output_path);
        $this->assertNull($job->last_error);
    }
}
