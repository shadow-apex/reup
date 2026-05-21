<?php

namespace Tests\Feature;

use App\Models\SourceVideo;
use App\Models\VideoJob;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Artisan;
use Illuminate\Support\Facades\Http;
use Tests\TestCase;

class VideoProcessSourceVideoTest extends TestCase
{
    use RefreshDatabase;

    public function test_video_process_with_source_video_uses_stored_path_without_copy(): void
    {
        config([
            'video_worker.base_url' => 'http://127.0.0.1:8765',
            'video_worker.secret' => 'test-secret',
            'video_worker.poll_interval_ms' => 1,
            'video_worker.poll_max_attempts' => 20,
        ]);

        $input = storage_path('app/private/sources/2026/05/3/original.mp4');
        if (! is_dir(dirname($input))) {
            mkdir(dirname($input), 0755, true);
        }
        file_put_contents($input, 'fake');

        $sourceVideo = SourceVideo::query()->create([
            'source_url' => 'https://www.douyin.com/video/3',
            'platform' => 'douyin',
            'status' => SourceVideo::STATUS_COMPLETED,
            'file_path' => $input,
            'sha256' => hash_file('sha256', $input),
            'file_size_bytes' => 4,
        ]);

        $jobIdHolder = ['id' => ''];
        $capturedInput = ['path' => ''];

        Http::fake(function (\Illuminate\Http\Client\Request $request) use (&$jobIdHolder, &$capturedInput) {
            $url = $request->url();
            if ($request->method() === 'POST' && str_contains($url, '/v1/jobs')) {
                $body = json_decode($request->body(), true);
                $jobIdHolder['id'] = (string) ($body['job_id'] ?? '');
                $capturedInput['path'] = (string) ($body['input_video_path'] ?? '');

                return Http::response([
                    'contract_version' => '1',
                    'job_id' => $jobIdHolder['id'],
                    'status' => 'queued',
                    'message' => 'Accepted',
                ], 202);
            }
            if ($request->method() === 'GET' && str_contains($url, '/v1/jobs/'.$jobIdHolder['id'])) {
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

        $exit = Artisan::call('video:process', [
            '--source-video' => (string) $sourceVideo->id,
        ]);

        $this->assertSame(0, $exit);
        $this->assertSame(realpath($input) ?: $input, $capturedInput['path']);

        $job = VideoJob::query()->first();
        $this->assertNotNull($job);
        $this->assertSame($sourceVideo->id, $job->source_video_id);
        $this->assertSame('completed', $job->status);
    }
}
