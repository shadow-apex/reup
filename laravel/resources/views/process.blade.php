@extends('layouts.app')

@section('title', 'Xử lý video')

@section('content')
    <div class="max-w-3xl">
        <div class="card mb-5">
            <h3 class="font-semibold text-lg mb-1">🎬 Xử lý video</h3>
            <p class="text-sm text-[#64748b] mb-5">Chọn video nguồn, cấu hình ngôn ngữ, và gửi job đến worker để xử lý (dịch + TTS + ghép)</p>

            @if($sourceVideos->isEmpty())
                <div class="text-center py-8">
                    <div class="text-4xl mb-3">📭</div>
                    <p class="text-[#64748b] mb-3">Chưa có video nguồn nào. Hãy tải hoặc upload trước.</p>
                    <div class="flex gap-3 justify-center">
                        <a href="{{ route('web.download') }}" class="btn-primary">⬇ Tải từ URL</a>
                        <a href="{{ route('web.upload') }}" class="btn-secondary">📁 Upload file</a>
                    </div>
                </div>
            @else
                <form method="POST" action="{{ route('web.process.submit') }}" class="space-y-5">
                    @csrf

                    {{-- Select source video --}}
                    <div>
                        <label class="block text-sm font-medium text-[#94a3b8] mb-1.5">Video nguồn</label>
                        <select name="source_video_id" class="select-field" required>
                            <option value="">— Chọn video —</option>
                            @foreach($sourceVideos as $sv)
                                <option value="{{ $sv->id }}" data-title="{{ $sv->title }}" {{ old('source_video_id') == $sv->id ? 'selected' : '' }}>
                                    #{{ $sv->id }} — {{ Str::limit($sv->title ?? 'Không tiêu đề', 60) }}
                                    ({{ $sv->created_at->format('d/m/Y') }})
                                </option>
                            @endforeach
                        </select>
                    </div>

                    {{-- Languages --}}
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <label class="block text-sm font-medium text-[#94a3b8] mb-1.5">Ngôn ngữ gốc</label>
                            <select name="source_language" class="select-field">
                                <option value="zh" {{ old('source_language', 'zh') == 'zh' ? 'selected' : '' }}>🇨🇳 Trung (zh)</option>
                                <option value="vi" {{ old('source_language', 'vi') == 'vi' ? 'selected' : '' }}>🇻🇳 Việt (vi)</option>
                                <option value="en" {{ old('source_language', 'en') == 'en' ? 'selected' : '' }}>🇬🇧 Anh (en)</option>
                                <option value="ja" {{ old('source_language', 'ja') == 'ja' ? 'selected' : '' }}>🇯🇵 Nhật (ja)</option>
                                <option value="ko" {{ old('source_language', 'ko') == 'ko' ? 'selected' : '' }}>🇰🇷 Hàn (ko)</option>
                                <option value="fr" {{ old('source_language', 'fr') == 'fr' ? 'selected' : '' }}>🇫🇷 Pháp (fr)</option>
                                <option value="de" {{ old('source_language', 'de') == 'de' ? 'selected' : '' }}>🇩🇪 Đức (de)</option>
                                <option value="th" {{ old('source_language', 'th') == 'th' ? 'selected' : '' }}>🇹🇭 Thái (th)</option>
                                <option value="id" {{ old('source_language', 'id') == 'id' ? 'selected' : '' }}>🇮🇩 Indo (id)</option>
                                <option value="ms" {{ old('source_language', 'ms') == 'ms' ? 'selected' : '' }}>🇲🇾 Mã Lai (ms)</option>
                            </select>
                        </div>

                        <div>
                            <label class="block text-sm font-medium text-[#94a3b8] mb-1.5">Ngôn ngữ đích</label>
                            <select name="target_language" class="select-field">
                                <option value="vi" {{ old('target_language', 'vi') == 'vi' ? 'selected' : '' }}>🇻🇳 Việt (vi)</option>
                                <option value="zh" {{ old('target_language', 'zh') == 'zh' ? 'selected' : '' }}>🇨🇳 Trung (zh)</option>
                                <option value="en" {{ old('target_language', 'en') == 'en' ? 'selected' : '' }}>🇬🇧 Anh (en)</option>
                                <option value="ja" {{ old('target_language', 'ja') == 'ja' ? 'selected' : '' }}>🇯🇵 Nhật (ja)</option>
                                <option value="ko" {{ old('target_language', 'ko') == 'ko' ? 'selected' : '' }}>🇰🇷 Hàn (ko)</option>
                                <option value="fr" {{ old('target_language', 'fr') == 'fr' ? 'selected' : '' }}>🇫🇷 Pháp (fr)</option>
                                <option value="de" {{ old('target_language', 'de') == 'de' ? 'selected' : '' }}>🇩🇪 Đức (de)</option>
                                <option value="th" {{ old('target_language', 'th') == 'th' ? 'selected' : '' }}>🇹🇭 Thái (th)</option>
                                <option value="id" {{ old('target_language', 'id') == 'id' ? 'selected' : '' }}>🇮🇩 Indo (id)</option>
                                <option value="ms" {{ old('target_language', 'ms') == 'ms' ? 'selected' : '' }}>🇲🇾 Mã Lai (ms)</option>
                            </select>
                        </div>
                    </div>

                    {{-- Volume original --}}
                    <div>
                        <label class="block text-sm font-medium text-[#94a3b8] mb-1.5">Âm lượng gốc giữ lại: <span id="vol-display" class="text-[#e2e8f0]">{{ old('vol_orig', 15) }}%</span></label>
                        <input type="range" name="vol_orig" min="0" max="100" value="{{ old('vol_orig', 15) }}"
                               class="w-full accent-[#7c5cfc]"
                               oninput="document.getElementById('vol-display').textContent = this.value + '%'">
                        <div class="flex justify-between text-xs text-[#64748b]">
                            <span>0% (tắt tiếng)</span>
                            <span>100% (giữ nguyên)</span>
                        </div>
                    </div>

                    <div class="flex gap-3 pt-1">
                        <button type="submit" class="btn-primary">🚀 Bắt đầu xử lý</button>
                        <a href="{{ route('web.dashboard') }}" class="btn-secondary">← Quay lại</a>
                    </div>
                </form>
            @endif
        </div>

        {{-- Translation test --}}
        <div class="card">
            <h4 class="font-semibold text-sm mb-1 text-[#94a3b8]">🤖 Dịch thử (AI)</h4>
            <p class="text-xs text-[#64748b] mb-4">Kiểm tra kết nối API dịch thuật trước khi xử lý</p>

            <form method="POST" action="{{ route('web.translate-test') }}" class="space-y-3">
                @csrf

                <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div>
                        <label class="block text-xs text-[#64748b] mb-1">Ngôn ngữ gốc</label>
                        <select name="source_language" class="select-field">
                            <option value="zh">Trung</option>
                            <option value="en">Anh</option>
                            <option value="ja">Nhật</option>
                            <option value="ko">Hàn</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-xs text-[#64748b] mb-1">Ngôn ngữ đích</label>
                        <select name="target_language" class="select-field">
                            <option value="vi">Việt</option>
                            <option value="en">Anh</option>
                        </select>
                    </div>
                </div>

                <div>
                    <input type="text" name="text" placeholder="Nhập văn bản cần dịch..."
                           class="input-field" value="Xin chào, đây là video hôm nay của tôi.">
                </div>

                <button type="submit" class="btn-primary text-sm">▶ Dịch thử</button>
            </form>

            @if (session('translation_result'))
                <div class="mt-4 p-3 bg-[#22c55e]/10 border border-[#22c55e]/30 rounded-lg">
                    <p class="text-xs text-[#64748b] mb-1">Kết quả:</p>
                    <p class="text-sm text-[#22c55e] font-medium">{{ session('translation_result') }}</p>
                </div>
            @endif
        </div>
    </div>
@endsection
