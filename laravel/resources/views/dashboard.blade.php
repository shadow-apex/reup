@extends('layouts.app')

@section('title', 'Dashboard')

@section('content')
    {{-- Worker status banner --}}
    @if (!$workerStatus['ok'])
        <div class="flash-info mb-5">
            ⚠️ Worker không phản hồi: {{ $workerStatus['error'] }}
            <br><small>Chạy <code class="bg-[#0f0f13] px-1 rounded">cd worker && PYTHONPATH=src uvicorn video_worker.app:app --host 127.0.0.1 --port 8765</code></small>
        </div>
    @else
        <div class="flash-success mb-5">
            ✅ Worker đang chạy ({{ json_encode($workerStatus['data']) }})
        </div>
    @endif

    {{-- Stats grid --}}
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
        <div class="card">
            <p class="stat-label">Video nguồn</p>
            <p class="stat-value">{{ $sourceCount }}</p>
        </div>
        <div class="card">
            <p class="stat-label">Tổng jobs</p>
            <p class="stat-value">{{ $jobCount }}</p>
        </div>
        <div class="card">
            <p class="stat-label">✅ Hoàn tất</p>
            <p class="stat-value text-[#22c55e]">{{ $completedJobs }}</p>
        </div>
        <div class="card">
            <p class="stat-label">⏳ Đang xử lý</p>
            <p class="stat-value text-[#f59e0b]">{{ $processingJobs }}</p>
        </div>
        <div class="card">
            <p class="stat-label">❌ Thất bại</p>
            <p class="stat-value text-[#ef4444]">{{ $failedJobs }}</p>
        </div>
    </div>

    {{-- Quick actions --}}
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <a href="{{ route('web.download') }}" class="card hover:border-[#7c5cfc]/50 transition-colors group">
            <div class="flex items-center gap-4">
                <div class="w-12 h-12 bg-[#7c5cfc]/20 rounded-xl flex items-center justify-center text-2xl group-hover:scale-110 transition-transform">
                    ⬇️
                </div>
                <div>
                    <p class="font-semibold text-[#e2e8f0]">Tải từ URL</p>
                    <p class="text-xs text-[#64748b]">Douyin, YouTube, TikTok...</p>
                </div>
            </div>
        </a>

        <a href="{{ route('web.upload') }}" class="card hover:border-[#7c5cfc]/50 transition-colors group">
            <div class="flex items-center gap-4">
                <div class="w-12 h-12 bg-[#22c55e]/20 rounded-xl flex items-center justify-center text-2xl group-hover:scale-110 transition-transform">
                    📁
                </div>
                <div>
                    <p class="font-semibold text-[#e2e8f0]">Upload file</p>
                    <p class="text-xs text-[#64748b]">MP4, MKV, AVI...</p>
                </div>
            </div>
        </a>

        <a href="{{ route('web.process') }}" class="card hover:border-[#7c5cfc]/50 transition-colors group">
            <div class="flex items-center gap-4">
                <div class="w-12 h-12 bg-[#f59e0b]/20 rounded-xl flex items-center justify-center text-2xl group-hover:scale-110 transition-transform">
                    🎬
                </div>
                <div>
                    <p class="font-semibold text-[#e2e8f0]">Xử lý video</p>
                    <p class="text-xs text-[#64748b]">Dịch + TTS + ghép</p>
                </div>
            </div>
        </a>
    </div>

    {{-- Recent jobs --}}
    <div class="card">
        <div class="flex items-center justify-between mb-4">
            <h3 class="font-semibold">📋 Job gần đây</h3>
            <a href="{{ route('web.history') }}" class="text-xs text-[#7c5cfc] hover:text-[#a78bfa] transition-colors">Xem tất cả →</a>
        </div>

        @if ($recentJobs->isEmpty())
            <p class="text-sm text-[#64748b] py-4 text-center">Chưa có job nào. Hãy tải hoặc upload video để bắt đầu!</p>
        @else
            <div class="overflow-x-auto">
                <table class="w-full text-sm">
                    <thead>
                        <tr class="text-[#64748b] text-xs uppercase tracking-wider border-b border-[#2e2e3e]">
                            <th class="text-left pb-3 font-medium">Job ID</th>
                            <th class="text-left pb-3 font-medium">Video</th>
                            <th class="text-left pb-3 font-medium">Trạng thái</th>
                            <th class="text-right pb-3 font-medium">Ngày</th>
                        </tr>
                    </thead>
                    <tbody>
                        @foreach ($recentJobs as $job)
                            <tr class="border-b border-[#2e2e3e]/50 hover:bg-[#0f0f13]/50 transition-colors">
                                <td class="py-3">
                                    <a href="{{ route('web.job-detail', $job->id) }}" class="text-[#7c5cfc] hover:text-[#a78bfa] font-mono text-xs">
                                        {{ Str::limit($job->job_id, 12) }}
                                    </a>
                                </td>
                                <td class="py-3 text-[#94a3b8]">
                                    {{ $job->sourceVideo?->title ?? 'N/A' }}
                                </td>
                                <td class="py-3">
                                    @switch($job->status)
                                        @case('completed')
                                            <span class="badge-success">Hoàn tất</span>
                                            @break
                                        @case('failed')
                                            <span class="badge-fail">Thất bại</span>
                                            @break
                                        @case('processing')
                                            <span class="badge-warn">Đang xử lý</span>
                                            @break
                                        @default
                                            <span class="badge-info">{{ $job->status }}</span>
                                    @endswitch
                                </td>
                                <td class="py-3 text-right text-[#64748b] text-xs">
                                    {{ $job->created_at->format('d/m/Y H:i') }}
                                </td>
                            </tr>
                        @endforeach
                    </tbody>
                </table>
            </div>
        @endif
    </div>
@endsection
