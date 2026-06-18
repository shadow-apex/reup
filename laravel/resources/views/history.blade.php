@extends('layouts.app')

@section('title', 'Lịch sử')

@section('content')
    <div class="card">
        <h3 class="font-semibold text-lg mb-4">📋 Lịch sử xử lý</h3>

        @if ($jobs->isEmpty())
            <div class="text-center py-10">
                <div class="text-4xl mb-3">📭</div>
                <p class="text-[#64748b]">Chưa có job nào.</p>
                <a href="{{ route('web.process') }}" class="btn-primary mt-3 inline-block">🎬 Xử lý video đầu tiên</a>
            </div>
        @else
            <div class="overflow-x-auto">
                <table class="w-full text-sm">
                    <thead>
                        <tr class="text-[#64748b] text-xs uppercase tracking-wider border-b border-[#2e2e3e]">
                            <th class="text-left pb-3 font-medium">ID</th>
                            <th class="text-left pb-3 font-medium">Job ID</th>
                            <th class="text-left pb-3 font-medium">Video</th>
                            <th class="text-left pb-3 font-medium">Trạng thái</th>
                            <th class="text-left pb-3 font-medium">Output</th>
                            <th class="text-right pb-3 font-medium">Ngày tạo</th>
                        </tr>
                    </thead>
                    <tbody>
                        @foreach ($jobs as $job)
                            <tr class="border-b border-[#2e2e3e]/50 hover:bg-[#0f0f13]/50 transition-colors">
                                <td class="py-3 font-mono text-xs text-[#64748b]">
                                    <a href="{{ route('web.job-detail', $job->id) }}" class="text-[#7c5cfc] hover:text-[#a78bfa]">
                                        #{{ $job->id }}
                                    </a>
                                </td>
                                <td class="py-3">
                                    <code class="text-xs text-[#94a3b8]">{{ Str::limit($job->job_id, 16) }}</code>
                                </td>
                                <td class="py-3 text-[#94a3b8] max-w-[200px] truncate" title="{{ $job->sourceVideo?->title ?? 'N/A' }}">
                                    {{ $job->sourceVideo?->title ?? 'N/A' }}
                                </td>
                                <td class="py-3">
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
                                        @case('queued')
                                            <span class="badge-info">⏳ Đang chờ</span>
                                            @break
                                        @default
                                            <span class="badge-info">{{ $job->status }}</span>
                                    @endswitch
                                </td>
                                <td class="py-3 text-xs text-[#64748b] max-w-[250px] truncate" title="{{ $job->output_path ?? '' }}">
                                    {{ $job->output_path ? basename($job->output_path) : '—' }}
                                </td>
                                <td class="py-3 text-right text-xs text-[#64748b]">
                                    {{ $job->created_at->format('d/m/Y H:i') }}
                                </td>
                            </tr>
                        @endforeach
                    </tbody>
                </table>
            </div>

            {{-- Pagination --}}
            <div class="mt-5">
                {{ $jobs->links() }}
            </div>
        @endif
    </div>
@endsection
