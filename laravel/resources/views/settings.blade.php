@extends('layouts.app')

@section('title', 'Cài đặt')

@section('content')
    <div class="max-w-2xl">
        <div class="card mb-5">
            <h3 class="font-semibold text-lg mb-1">⚙️ Cài đặt AI</h3>
            <p class="text-sm text-[#64748b] mb-5">Cấu hình API dịch thuật (OpenAI-compatible). Những giá trị này được lưu vào <code class="bg-[#0f0f13] px-1 rounded">.env</code>.</p>

            <form method="POST" action="{{ route('web.settings.save') }}" class="space-y-5">
                @csrf

                {{-- AI Provider presets --}}
                <div>
                    <label class="block text-sm font-medium text-[#94a3b8] mb-1.5">Provider mẫu</label>
                    <select class="select-field" id="provider-preset" onchange="applyPreset(this.value)">
                        <option value="">— Chọn —</option>
                        <option value="deepseek">DeepSeek</option>
                        <option value="openai">OpenAI</option>
                        <option value="groq">Groq (free)</option>
                        <option value="together">Together AI</option>
                        <option value="gemini">Gemini (proxy)</option>
                        <option value="openrouter">OpenRouter</option>
                    </select>
                </div>

                <hr class="border-[#2e2e3e]">

                {{-- API Key --}}
                <div>
                    <label class="block text-sm font-medium text-[#94a3b8] mb-1.5">API Key</label>
                    <div class="relative">
                        <input type="password" name="api_key" id="api-key" value="{{ $config['api_key'] }}"
                               placeholder="sk-..." class="input-field pr-10">
                        <button type="button" onclick="toggleKey()" class="absolute right-3 top-1/2 -translate-y-1/2 text-[#64748b] hover:text-[#e2e8f0]">
                            👁
                        </button>
                    </div>
                </div>

                {{-- Base URL --}}
                <div>
                    <label class="block text-sm font-medium text-[#94a3b8] mb-1.5">Base URL</label>
                    <input type="url" name="api_base" id="api-base" value="{{ $config['api_base'] }}"
                           placeholder="https://api.deepseek.com" class="input-field">
                </div>

                {{-- Model --}}
                <div>
                    <label class="block text-sm font-medium text-[#94a3b8] mb-1.5">Model</label>
                    <input type="text" name="api_model" id="api-model" value="{{ $config['api_model'] }}"
                           placeholder="deepseek-chat" class="input-field">
                </div>

                <hr class="border-[#2e2e3e]">

                {{-- Default language --}}
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <label class="block text-sm font-medium text-[#94a3b8] mb-1.5">Ngôn ngữ gốc mặc định</label>
                        <select name="source_language" class="select-field">
                            <option value="zh" {{ $config['source_language'] == 'zh' ? 'selected' : '' }}>🇨🇳 Trung (zh)</option>
                            <option value="vi" {{ $config['source_language'] == 'vi' ? 'selected' : '' }}>🇻🇳 Việt (vi)</option>
                            <option value="en" {{ $config['source_language'] == 'en' ? 'selected' : '' }}>🇬🇧 Anh (en)</option>
                            <option value="ja" {{ $config['source_language'] == 'ja' ? 'selected' : '' }}>🇯🇵 Nhật (ja)</option>
                            <option value="ko" {{ $config['source_language'] == 'ko' ? 'selected' : '' }}>🇰🇷 Hàn (ko)</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-[#94a3b8] mb-1.5">Ngôn ngữ đích mặc định</label>
                        <select name="target_language" class="select-field">
                            <option value="vi" {{ $config['target_language'] == 'vi' ? 'selected' : '' }}>🇻🇳 Việt (vi)</option>
                            <option value="zh" {{ $config['target_language'] == 'zh' ? 'selected' : '' }}>🇨🇳 Trung (zh)</option>
                            <option value="en" {{ $config['target_language'] == 'en' ? 'selected' : '' }}>🇬🇧 Anh (en)</option>
                        </select>
                    </div>
                </div>

                {{-- Volume original --}}
                <div>
                    <label class="block text-sm font-medium text-[#94a3b8] mb-1.5">Âm lượng gốc mặc định: <span id="vol-display" class="text-[#e2e8f0]">{{ $config['vol_orig'] }}%</span></label>
                    <input type="range" name="vol_orig" min="0" max="100" value="{{ $config['vol_orig'] }}"
                           class="w-full accent-[#7c5cfc]"
                           oninput="document.getElementById('vol-display').textContent = this.value + '%'">
                </div>

                <div class="flex gap-3 pt-1">
                    <button type="submit" class="btn-primary">💾 Lưu cấu hình</button>
                    <a href="{{ route('web.dashboard') }}" class="btn-secondary">← Quay lại</a>
                </div>
            </form>
        </div>

        <div class="card">
            <h4 class="font-semibold text-sm mb-2 text-[#94a3b8]">📌 Hướng dẫn</h4>
            <ul class="text-sm text-[#64748b] space-y-1.5 list-disc list-inside">
                <li><strong>DeepSeek</strong> — <code>api.deepseek.com</code>, model <code>deepseek-chat</code> (rẻ, tốt cho Trung → Việt)</li>
                <li><strong>OpenAI</strong> — <code>api.openai.com/v1</code>, model <code>gpt-4o-mini</code></li>
                <li><strong>Groq</strong> — miễn phí, model <code>llama-3.3-70b-versatile</code></li>
                <li><strong>Gemini</strong> — cần API key Google, dùng proxy OpenAI-compatible</li>
                <li>API Key được lưu trong <code class="bg-[#0f0f13] px-1 rounded">.env</code> ở dạng plain text — cẩn thận khi commit</li>
            </ul>
        </div>
    </div>

    <script>
    const PRESETS = {
        deepseek:   { url: 'https://api.deepseek.com',          model: 'deepseek-chat' },
        openai:     { url: 'https://api.openai.com/v1',         model: 'gpt-4o-mini' },
        groq:       { url: 'https://api.groq.com/openai/v1',     model: 'llama-3.3-70b-versatile' },
        together:   { url: 'https://api.together.xyz/v1',        model: 'mistralai/Mixtral-8x22B-Instruct-v0.1' },
        gemini:     { url: 'https://generativelanguage.googleapis.com/v1beta/openai/', model: 'gemini-2.0-flash' },
        openrouter: { url: 'https://openrouter.ai/api/v1',       model: 'openai/gpt-4o-mini' },
    };

    function applyPreset(key) {
        const p = PRESETS[key];
        if (!p) return;
        document.getElementById('api-base').value = p.url;
        document.getElementById('api-model').value = p.model;
    }

    function toggleKey() {
        const el = document.getElementById('api-key');
        el.type = el.type === 'password' ? 'text' : 'password';
    }
    </script>
@endsection
