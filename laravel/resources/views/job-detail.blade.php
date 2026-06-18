@extends('layouts.app')

@section('title', 'Job #'.$job->id)

@section('content')
    <div class="max-w-3xl">
        <div class="flex items-center gap-3 mb-5">
            <a href="{{ route('web.history') }}" class="text-[#64748b] hover:text-[#a78bfa] transition-colors">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/></svg>
            </a>
            <h3 class="font-semibold text-lg">Job #{{ $job->id }}</h3>
            @switch($job->status)
                @case('completed')
                    <span class="badge-success">✅ Hoàn tất</span>
                    @break
                @case('failed')
                    <span class="badge-fail">❌ Thất bại</span>
                    @break
                @case('processing')
                    <span class="badge-warn">⏳ Đang xử lý</span>
                    @break
                @default
                    <span class="badge-info">{{ $job->status }}</span>
            @endswitch
        </div>

        {{-- General info --}}
        <div class="card mb-5">
            <h4 class="font-semibold text-sm text-[#94a3b8] mb-3 uppercase tracking-wider">Thông tin chung</h4>
            <dl class="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                <div>
                    <dt class="text-[#64748b] text-xs">Job ID</dt>
                    <dd class="text-[#e2e8f0] font-mono text-xs mt-0.5">{{ $job->job_id }}</dd>
                </div>
                <div>
                    <dt class="text-[#64748b] text-xs">Trạng thái</dt>
                    <dd class="text-[#e2e8f0] mt-0.5">{{ $job->status }}</dd>
                </div>
                <div>
                    <dt class="text-[#64748b] text-xs">Video nguồn</dt>
                    <dd class="text-[#e2e8f0] mt-0.5">{{ $job->sourceVideo?->title ?? 'N/A' }}</dd>
                </div>
                <div>
                    <dt class="text-[#64748b] text-xs">Source Video ID</dt>
                    <dd class="text-[#e2e8f0] mt-0.5">{{ $job->source_video_id ?? 'N/A' }}</dd>
                </div>
                <div>
                    <dt class="text-[#64748b] text-xs">Ngày tạo</dt>
                    <dd class="text-[#e2e8f0] mt-0.5">{{ $job->created_at->format('d/m/Y H:i:s') }}</dd>
                </div>
                <div>
                    <dt class="text-[#64748b] text-xs">Cập nhật</dt>
                    <dd class="text-[#e2e8f0] mt-0.5">{{ $job->updated_at->format('d/m/Y H:i:s') }}</dd>
                </div>
            </dl>
        </div>

        {{-- Paths --}}
        <div class="card mb-5">
            <h4 class="font-semibold text-sm text-[#94a3b8] mb-3 uppercase tracking-wider">Đường dẫn</h4>
            <dl class="space-y-3 text-sm">
                <div>
                    <dt class="text-[#64748b] text-xs">Input</dt>
                    <dd class="text-[#94a3b8] font-mono text-xs mt-0.5 break-all">{{ $job->input_path ?? '—' }}</dd>
                </div>
                <div>
                    <dt class="text-[#64748b] text-xs">Output</dt>
                    <dd class="text-[#94a3b8] font-mono text-xs mt-0.5 break-all">
                        @if ($job->output_path)
                            <span class="text-[#22c55e]">✅ {{ $job->output_path }}</span>
                        @else
                            —
                        @endif
                    </dd>
                </div>
            </dl>
        </div>

        {{-- Worker payload --}}
        @if ($job->worker_payload)
            <div class="card mb-5">
                <h4 class="font-semibold text-sm text-[#94a3b8] mb-3 uppercase tracking-wider">Payload gửi worker</h4>
                <pre class="bg-[#0f0f13] rounded-lg p-4 text-xs text-[#94a3b8] overflow-x-auto font-mono">{{ json_encode($job->worker_payload, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE) }}</pre>
            </div>
        @endif

        {{-- Error detail --}}
        @if ($job->last_error)
            <div class="card border-[#ef4444]/50">
                <h4 class="font-semibold text-sm text-[#ef4444] mb-3 uppercase tracking-wider">❌ Lỗi</h4>
                <pre class="bg-[#0f0f13] rounded-lg p-4 text-xs text-[#ef4444] overflow-x-auto font-mono">{{ json_encode($job->last_error, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE) }}</pre>
            </div>
        @endif

        <div class="mt-5">
            <a href="{{ route('web.history') }}" class="text-sm text-[#7c5cfc] hover:text-[#a78bfa] transition-colors">← Quay lại lịch sử</a>
        </div>
    </div>
@endsection
