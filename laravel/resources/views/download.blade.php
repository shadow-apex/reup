@extends('layouts.app')

@section('title', 'Tải từ URL')

@section('content')
    <div class="max-w-2xl">
        <div class="card mb-5">
            <h3 class="font-semibold text-lg mb-1">⬇️ Tải video từ URL</h3>
            <p class="text-sm text-[#64748b] mb-5">Hỗ trợ Douyin, YouTube, TikTok, Facebook, Instagram... (qua yt-dlp)</p>

            <form method="POST" action="{{ route('web.download.submit') }}" class="space-y-4">
                @csrf

                <div>
                    <label class="block text-sm font-medium text-[#94a3b8] mb-1.5">Link video</label>
                    <input type="url" name="url" value="{{ old('url') }}"
                           placeholder="https://www.douyin.com/video/..."
                           class="input-field" required>
                    <p class="text-xs text-[#64748b] mt-1">Dán link Douyin, YouTube, hoặc bất kỳ nền tảng nào yt-dlp hỗ trợ.</p>
                </div>

                <div class="flex gap-3 pt-1">
                    <button type="submit" class="btn-primary">⬇ Tải xuống</button>
                    <a href="{{ route('web.dashboard') }}" class="btn-secondary">← Quay lại</a>
                </div>
            </form>
        </div>

        <div class="card">
            <h4 class="font-semibold text-sm mb-2 text-[#94a3b8]">📌 Lưu ý</h4>
            <ul class="text-sm text-[#64748b] space-y-1.5 list-disc list-inside">
                <li>Douyin yêu cầu file <code class="bg-[#0f0f13] px-1 rounded text-xs">cookies.txt</code> — cấu hình trong <code class="bg-[#0f0f13] px-1 rounded text-xs">.env</code> (<code class="bg-[#0f0f13] px-1 rounded text-xs">YTDLP_COOKIES_FILE</code>)</li>
                <li>Video đã tải sẽ xuất hiện trong danh sách nguồn để xử lý tiếp</li>
                <li>Định dạng: MP4 (tự động chọn chất lượng tốt nhất)</li>
            </ul>
        </div>
    </div>
@endsection
