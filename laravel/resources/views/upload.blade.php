@extends('layouts.app')

@section('title', 'Upload file')

@section('content')
    <div class="max-w-2xl">
        <div class="card mb-5">
            <h3 class="font-semibold text-lg mb-1">📁 Upload video từ máy</h3>
            <p class="text-sm text-[#64748b] mb-5">Chọn file video từ máy tính để xử lý (tối đa 512MB)</p>

            <form method="POST" action="{{ route('web.upload.submit') }}" enctype="multipart/form-data" class="space-y-4">
                @csrf

                <div>
                    <label class="block text-sm font-medium text-[#94a3b8] mb-1.5">File video</label>
                    <div class="border-2 border-dashed border-[#2e2e3e] rounded-xl p-8 text-center hover:border-[#7c5cfc]/50 transition-colors cursor-pointer" onclick="document.getElementById('video-input').click()">
                        <div class="text-4xl mb-3">📂</div>
                        <p class="text-sm text-[#94a3b8] mb-1">Kéo thả hoặc nhấp để chọn file</p>
                        <p class="text-xs text-[#64748b]">MP4, MKV, AVI, MOV, WebM, FLV</p>
                        <input id="video-input" type="file" name="video" accept=".mp4,.mkv,.avi,.mov,.webm,.flv"
                               class="hidden" required onchange="document.getElementById('file-name').textContent = this.files[0]?.name || ''">
                        <p id="file-name" class="text-sm text-[#22c55e] mt-2 font-medium"></p>
                    </div>
                </div>

                <div class="flex gap-3 pt-1">
                    <button type="submit" class="btn-primary">📤 Upload</button>
                    <a href="{{ route('web.dashboard') }}" class="btn-secondary">← Quay lại</a>
                </div>
            </form>
        </div>

        <div class="card">
            <h4 class="font-semibold text-sm mb-2 text-[#94a3b8]">📌 Lưu ý</h4>
            <ul class="text-sm text-[#64748b] space-y-1.5 list-disc list-inside">
                <li>Dung lượng tối đa: <strong>512 MB</strong> (có thể tăng trong config PHP)</li>
                <li>Video sẽ được lưu vào storage và hiển thị trong danh sách xử lý</li>
                <li>Nếu file lớn hơn, hãy dùng tính năng <a href="{{ route('web.download') }}" class="text-[#7c5cfc] hover:text-[#a78bfa]">tải từ URL</a></li>
            </ul>
        </div>
    </div>
@endsection
