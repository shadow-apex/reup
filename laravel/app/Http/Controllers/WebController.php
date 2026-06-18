<?php

namespace App\Http\Controllers;

use App\Models\SourceVideo;
use App\Models\VideoJob;
use App\Services\Download\VideoDownloader;
use App\Services\VideoWorkerClient;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;
use Illuminate\View\View;
use Throwable;

class WebController extends Controller
{
    // ─── DASHBOARD ─────────────────────────────────────────────────────

    public function dashboard(): View
    {
        $sourceCount = SourceVideo::count();
        $jobCount = VideoJob::count();
        $completedJobs = VideoJob::where('status', 'completed')->count();
        $failedJobs = VideoJob::where('status', 'failed')->count();
        $processingJobs = VideoJob::whereIn('status', ['queued', 'processing'])->count();
        $recentJobs = VideoJob::with('sourceVideo')
            ->latest()
            ->take(10)
            ->get();
        $workerStatus = $this->checkWorkerHealth();

        return view('dashboard', compact(
            'sourceCount', 'jobCount', 'completedJobs', 'failedJobs',
            'processingJobs', 'recentJobs', 'workerStatus'
        ));
    }

    // ─── DOWNLOAD (Douyin / URL) ──────────────────────────────────────

    public function downloadForm(): View
    {
        return view('download');
    }

    public function downloadSubmit(Request $request, VideoDownloader $downloader): RedirectResponse
    {
        $validated = $request->validate([
            'url' => 'required|string|max:2000',
        ]);

        try {
            $sourceVideo = $downloader->downloadFromUrl($validated['url']);
        } catch (Throwable $e) {
            return back()->withErrors(['url' => 'Lỗi tải video: '.$e->getMessage()])->withInput();
        }

        if ($sourceVideo->status !== SourceVideo::STATUS_COMPLETED) {
            $errorMsg = 'Tải thất bại';
            if (is_array($sourceVideo->last_error)) {
                $errorMsg .= ': '.($sourceVideo->last_error['message'] ?? json_encode($sourceVideo->last_error));
            }
            $redirect = back()->withErrors(['url' => $errorMsg])->withInput();

            if (($sourceVideo->last_error['code'] ?? '') === 'DOWNLOAD_COOKIES_REQUIRED') {
                $redirect->with('info', 'Cần file cookies.txt từ douyin.com (đã đăng nhập). Set YTDLP_COOKIES_FILE trong .env.');
            }

            return $redirect;
        }

        return redirect()->route('web.dashboard')
            ->with('success', '✅ Đã tải xong: '.($sourceVideo->title ?? 'video #'.$sourceVideo->id));
    }

    // ─── UPLOAD (local file) ──────────────────────────────────────────

    public function uploadForm(): View
    {
        return view('upload');
    }

    public function uploadSubmit(Request $request): RedirectResponse
    {
        $validated = $request->validate([
            'video' => 'required|file|mimes:mp4,mkv,avi,mov,webm,flv|max:5120',
        ]);

        $file = $validated['video'];
        $originalName = $file->getClientOriginalName();
        $ext = $file->getClientOriginalExtension();
        $storedName = Str::uuid().'.'.$ext;
        $storedPath = $file->storeAs('uploads', $storedName, 'private');
        $fullPath = Storage::disk('private')->path($storedPath);

        SourceVideo::create([
            'source_url' => null,
            'platform' => 'local',
            'external_id' => (string) Str::uuid(),
            'title' => pathinfo($originalName, PATHINFO_FILENAME),
            'file_path' => $fullPath,
            'file_size_bytes' => $file->getSize(),
            'status' => SourceVideo::STATUS_COMPLETED,
            'metadata_json' => ['original_name' => $originalName],
        ]);

        return redirect()->route('web.dashboard')
            ->with('success', '📁 Đã upload: '.$originalName);
    }

    // ─── PROCESS (dispatch to worker) ─────────────────────────────────

    public function processForm(): View
    {
        $sourceVideos = SourceVideo::where('status', SourceVideo::STATUS_COMPLETED)
            ->latest()
            ->get();

        return view('process', compact('sourceVideos'));
    }

    public function processSubmit(Request $request): RedirectResponse
    {
        $validated = $request->validate([
            'source_video_id' => 'required|integer|exists:source_videos,id',
            'source_language' => 'nullable|string|size:2',
            'target_language' => 'nullable|string|size:2',
            'vol_orig' => 'nullable|integer|min:0|max:100',
        ]);

        $sourceVideo = SourceVideo::findOrFail($validated['source_video_id']);

        if ($sourceVideo->status !== SourceVideo::STATUS_COMPLETED || $sourceVideo->file_path === null) {
            return back()->withErrors(['source_video_id' => 'Video chưa sẵn sàng (status='.$sourceVideo->status.')']);
        }

        $resolved = realpath($sourceVideo->file_path) ?: $sourceVideo->file_path;
        if (! is_file($resolved)) {
            return back()->withErrors(['source_video_id' => 'File video không tồn tại: '.$sourceVideo->file_path]);
        }

        $jobId = (string) Str::uuid();
        $client = app(VideoWorkerClient::class);
        $storage = app(\App\Services\Download\SourceVideoStorage::class);

        $videoJob = VideoJob::create([
            'source_video_id' => $sourceVideo->id,
            'job_id' => $jobId,
            'status' => 'queued',
            'input_path' => $resolved,
            'output_path' => null,
            'worker_payload' => [
                'output_dir' => $storage->outDir(),
                'source_language' => $validated['source_language'] ?? 'zh',
                'target_language' => $validated['target_language'] ?? 'vi',
                'vol_orig' => $validated['vol_orig'] ?? 15,
            ],
            'last_error' => null,
        ]);

        $success = redirect()->route('web.history');

        try {
            $client->submitJob(
                $jobId,
                $resolved,
                $storage->outDir(),
                [
                    'source_language' => $validated['source_language'] ?? 'zh',
                    'target_language' => $validated['target_language'] ?? 'vi',
                ]
            );
        } catch (Throwable $e) {
            $videoJob->update([
                'status' => 'failed',
                'last_error' => ['code' => 'LARAVEL_DISPATCH', 'message' => $e->getMessage()],
            ]);

            return back()->withErrors(['submit' => 'Lỗi gửi job: '.$e->getMessage()]);
        }

        $videoJob->update(['status' => 'processing']);

        try {
            $final = $client->pollUntilTerminal($jobId);
        } catch (Throwable $e) {
            $videoJob->update([
                'status' => 'failed',
                'last_error' => ['code' => 'LARAVEL_POLL', 'message' => $e->getMessage()],
            ]);

            return $success->with('error', 'Job thất bại: '.$e->getMessage());
        }

        $status = $final['status'] ?? 'unknown';
        if ($status === 'completed') {
            $videoJob->update([
                'status' => 'completed',
                'output_path' => $final['output_video_path'] ?? null,
                'last_error' => null,
            ]);

            return $success->with('success', '✅ Xử lý hoàn tất! Output: '.($final['output_video_path'] ?? '(none)'));
        }

        $videoJob->update([
            'status' => 'failed',
            'output_path' => null,
            'last_error' => isset($final['error']) && is_array($final['error'])
                ? $final['error']
                : ['code' => 'WORKER_FAILED', 'message' => json_encode($final)],
        ]);

        return $success->with('error', 'Worker báo lỗi: '.json_encode($final['error'] ?? $final));
    }

    // ─── HISTORY ──────────────────────────────────────────────────────

    public function history(): View
    {
        $jobs = VideoJob::with('sourceVideo')
            ->latest()
            ->paginate(20);

        return view('history', compact('jobs'));
    }

    public function jobDetail(int $id): View
    {
        $job = VideoJob::with('sourceVideo')->findOrFail($id);

        return view('job-detail', compact('job'));
    }

    // ─── SETTINGS (AI config) ─────────────────────────────────────────

    public function settingsForm(): View
    {
        $config = [
            'api_key' => config('services.openai.api_key'),
            'api_base' => config('services.openai.base_url', 'https://api.deepseek.com'),
            'api_model' => config('services.openai.model', 'deepseek-chat'),
            'source_language' => config('services.openai.source_language', 'zh'),
            'target_language' => config('services.openai.target_language', 'vi'),
            'vol_orig' => config('services.openai.vol_orig', 15),
        ];

        return view('settings', compact('config'));
    }

    public function settingsSave(Request $request): RedirectResponse
    {
        $validated = $request->validate([
            'api_key' => 'nullable|string',
            'api_base' => 'nullable|string|url',
            'api_model' => 'nullable|string',
            'source_language' => 'nullable|string|size:2',
            'target_language' => 'nullable|string|size:2',
            'vol_orig' => 'nullable|integer|min:0|max:100',
        ]);

        // Persist to .env via config (best-effort for runtime)
        $envPath = base_path('.env');
        $envContent = file_get_contents($envPath);

        $replacements = [
            'OPENAI_API_KEY' => $validated['api_key'] ?? '',
            'OPENAI_BASE_URL' => $validated['api_base'] ?? 'https://api.deepseek.com',
            'OPENAI_MODEL' => $validated['api_model'] ?? 'deepseek-chat',
            'OPENAI_SOURCE_LANG' => $validated['source_language'] ?? 'zh',
            'OPENAI_TARGET_LANG' => $validated['target_language'] ?? 'vi',
            'OPENAI_VOL_ORIG' => (string) ($validated['vol_orig'] ?? 15),
        ];

        foreach ($replacements as $key => $value) {
            $pattern = "/^{$key}=.*/m";
            $line = "{$key}={$value}";
            if (preg_match($pattern, $envContent)) {
                $envContent = preg_replace($pattern, $line, $envContent);
            } else {
                $envContent .= "\n".$line;
            }
        }

        file_put_contents($envPath, $envContent);

        // Also set runtime config
        config(['services.openai' => array_merge(config('services.openai', []), $replacements)]);

        return redirect()->route('web.settings')
            ->with('success', '✅ Đã lưu cấu hình!');
    }

    // ─── AI TRANSLATE TEST ────────────────────────────────────────────

    public function translateTest(Request $request): RedirectResponse
    {
        $validated = $request->validate([
            'text' => 'required|string|max:1000',
            'source_language' => 'required|string|size:2',
            'target_language' => 'required|string|size:2',
        ]);

        $apiKey = config('services.openai.api_key');
        $baseUrl = config('services.openai.base_url', 'https://api.deepseek.com');
        $model = config('services.openai.model', 'deepseek-chat');

        if (empty($apiKey)) {
            return back()->withErrors(['api' => 'Chưa cấu hình API Key. Vào Settings để thiết lập.']);
        }

        try {
            $response = Http::timeout(60)
                ->withHeaders([
                    'Authorization' => 'Bearer '.$apiKey,
                    'Content-Type' => 'application/json',
                ])
                ->post(rtrim($baseUrl, '/').'/chat/completions', [
                    'model' => $model,
                    'messages' => [
                        [
                            'role' => 'system',
                            'content' => "Dịch {$validated['source_language']} → {$validated['target_language']}. Chỉ ra kết quả, không thêm gì khác.",
                        ],
                        [
                            'role' => 'user',
                            'content' => $validated['text'],
                        ],
                    ],
                    'temperature' => 0.3,
                ])
                ->throw()
                ->json();

            $translated = $response['choices'][0]['message']['content'] ?? '(no response)';

            return back()->with('translation_result', $translated);
        } catch (Throwable $e) {
            return back()->withErrors(['api' => 'Lỗi AI: '.$e->getMessage()]);
        }
    }

    // ─── HELPERS ──────────────────────────────────────────────────────

    private function checkWorkerHealth(): array
    {
        try {
            $client = app(VideoWorkerClient::class);
            $health = $client->health();

            return ['ok' => true, 'data' => $health];
        } catch (Throwable $e) {
            return ['ok' => false, 'error' => $e->getMessage()];
        }
    }
}
