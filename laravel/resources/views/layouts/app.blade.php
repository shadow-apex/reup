<!DOCTYPE html>
<html lang="{{ str_replace('_', '-', app()->getLocale()) }}">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>@yield('title', 'Video Reup') — {{ config('app.name') }}</title>
    <meta name="csrf-token" content="{{ csrf_token() }}">
    @vite(['resources/css/app.css', 'resources/js/app.js'])
    <style>
        .sidebar-link { @apply flex items-center gap-3 px-4 py-2.5 text-sm rounded-lg transition-colors; }
        .sidebar-link:hover { @apply bg-[#2a2a3a] text-[#a78bfa]; }
        .sidebar-link.active { @apply bg-[#7c5cfc]/20 text-[#a78bfa] border border-[#7c5cfc]/30; }
        .card { @apply bg-[#1a1a22] border border-[#2e2e3e] rounded-xl p-5; }
        .stat-value { @apply text-2xl font-bold text-[#e2e8f0]; }
        .stat-label { @apply text-xs text-[#94a3b8]; }
        .btn-primary { @apply bg-[#7c5cfc] hover:bg-[#a78bfa] text-white text-sm font-medium px-5 py-2.5 rounded-lg transition-colors cursor-pointer disabled:opacity-50; }
        .btn-secondary { @apply bg-[#334155] hover:bg-[#475569] text-white text-sm font-medium px-5 py-2.5 rounded-lg transition-colors cursor-pointer; }
        .btn-danger { @apply bg-[#ef4444] hover:bg-[#f87171] text-white text-sm font-medium px-5 py-2.5 rounded-lg transition-colors cursor-pointer; }
        .input-field { @apply w-full bg-[#0f0f13] border border-[#2e2e3e] rounded-lg px-4 py-2.5 text-sm text-[#e2e8f0] placeholder-[#64748b] focus:border-[#7c5cfc] focus:outline-none transition-colors; }
        .select-field { @apply w-full bg-[#0f0f13] border border-[#2e2e3e] rounded-lg px-4 py-2.5 text-sm text-[#e2e8f0] focus:border-[#7c5cfc] focus:outline-none transition-colors; }
        .badge { @apply inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium; }
        .badge-success { @apply badge bg-[#22c55e]/20 text-[#22c55e]; }
        .badge-fail { @apply badge bg-[#ef4444]/20 text-[#ef4444]; }
        .badge-warn { @apply badge bg-[#f59e0b]/20 text-[#f59e0b]; }
        .badge-info { @apply badge bg-[#7c5cfc]/20 text-[#a78bfa]; }
        .flash-message { @apply px-5 py-3 rounded-lg text-sm font-medium border; }
        .flash-success { @apply flash-message bg-[#22c55e]/10 text-[#22c55e] border-[#22c55e]/30; }
        .flash-error { @apply flash-message bg-[#ef4444]/10 text-[#ef4444] border-[#ef4444]/30; }
        .flash-info { @apply flash-message bg-[#7c5cfc]/10 text-[#a78bfa] border-[#7c5cfc]/30; }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: #0f0f13; }
        ::-webkit-scrollbar-thumb { background: #2e2e3e; border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: #475569; }
    </style>
</head>
<body class="bg-[#0f0f13] text-[#e2e8f0] font-sans antialiased min-h-screen">
    <div class="flex h-screen overflow-hidden">
        {{-- Sidebar --}}
        <aside class="w-64 bg-[#1a1a22] border-r border-[#2e2e3e] flex flex-col shrink-0">
            <div class="p-5 border-b border-[#2e2e3e]">
                <h1 class="text-lg font-bold text-[#a78bfa]">🎬 Video Reup</h1>
                <p class="text-xs text-[#64748b] mt-0.5">Tool dịch & lồng tiếng</p>
            </div>

            <nav class="flex-1 p-4 space-y-1 overflow-y-auto">
                <a href="{{ route('web.dashboard') }}" class="sidebar-link {{ request()->routeIs('web.dashboard') ? 'active' : '' }}">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"/></svg>
                    Dashboard
                </a>

                <div class="pt-3 pb-1">
                    <p class="text-xs font-medium text-[#64748b] uppercase tracking-wider px-4">Nhập liệu</p>
                </div>

                <a href="{{ route('web.download') }}" class="sidebar-link {{ request()->routeIs('web.download') ? 'active' : '' }}">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
                    Tải từ URL
                </a>

                <a href="{{ route('web.upload') }}" class="sidebar-link {{ request()->routeIs('web.upload') ? 'active' : '' }}">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/></svg>
                    Upload file
                </a>

                <div class="pt-3 pb-1">
                    <p class="text-xs font-medium text-[#64748b] uppercase tracking-wider px-4">Xử lý</p>
                </div>

                <a href="{{ route('web.process') }}" class="sidebar-link {{ request()->routeIs('web.process') ? 'active' : '' }}">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                    Xử lý video
                </a>

                <div class="pt-3 pb-1">
                    <p class="text-xs font-medium text-[#64748b] uppercase tracking-wider px-4">Theo dõi</p>
                </div>

                <a href="{{ route('web.history') }}" class="sidebar-link {{ request()->routeIs('web.history') || request()->routeIs('web.job-detail') ? 'active' : '' }}">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/></svg>
                    Lịch sử
                </a>

                <div class="pt-3 pb-1">
                    <p class="text-xs font-medium text-[#64748b] uppercase tracking-wider px-4">Cấu hình</p>
                </div>

                <a href="{{ route('web.settings') }}" class="sidebar-link {{ request()->routeIs('web.settings') ? 'active' : '' }}">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
                    Cài đặt
                </a>
            </nav>

            <div class="p-4 border-t border-[#2e2e3e]">
                <div class="flex items-center gap-3">
                    <div class="w-8 h-8 bg-[#7c5cfc]/20 rounded-full flex items-center justify-center">
                        <span class="text-xs font-bold text-[#a78bfa]">R</span>
                    </div>
                    <div class="text-xs text-[#64748b]">
                        <p class="font-medium text-[#94a3b8]">reup-video</p>
                        <p>v1.0</p>
                    </div>
                </div>
            </div>
        </aside>

        {{-- Main content --}}
        <main class="flex-1 flex flex-col overflow-hidden">
            {{-- Top bar --}}
            <header class="h-14 bg-[#1a1a22] border-b border-[#2e2e3e] flex items-center justify-between px-6 shrink-0">
                <h2 class="text-base font-semibold">@yield('title', 'Dashboard')</h2>
                <div class="flex items-center gap-3">
                    <a href="https://github.com" target="_blank" class="text-[#64748b] hover:text-[#a78bfa] transition-colors">
                        <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/></svg>
                    </a>
                </div>
            </header>

            {{-- Page content --}}
            <div class="flex-1 overflow-y-auto p-6">
                {{-- Flash messages --}}
                @if (session('success'))
                    <div class="flash-success mb-4">{{ session('success') }}</div>
                @endif
                @if (session('error'))
                    <div class="flash-error mb-4">{{ session('error') }}</div>
                @endif
                @if (session('info'))
                    <div class="flash-info mb-4">{{ session('info') }}</div>
                @endif

                {{-- Validation errors --}}
                @if ($errors->any())
                    <div class="flash-error mb-4">
                        <ul class="list-disc list-inside space-y-1">
                            @foreach ($errors->all() as $error)
                                <li>{{ $error }}</li>
                            @endforeach
                        </ul>
                    </div>
                @endif

                @yield('content')
            </div>
        </main>
    </div>
</body>
</html>
