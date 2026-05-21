# reup-video

Monorepo: **Laravel** (orchestrator) + **worker** (ASR/TTS/ffmpeg) + **contract** (HTTP API v1).

See [AGENTS.md](AGENTS.md) and [PROJECT_PLAN.md](PROJECT_PLAN.md).

## Phase 0 — ingest (Douyin-first)

1. Install yt-dlp: `pip install yt-dlp` (Windows: binary is often in `%APPDATA%\Python\Python311\Scripts\yt-dlp.exe` — add to PATH or leave `YTDLP_PATH=yt-dlp` for auto-detect).
2. Douyin: `jingxuan?modal_id=…` links are auto-converted to `https://www.douyin.com/video/{id}`. Downloads still need `YTDLP_COOKIES_FILE` (exported `cookies.txt` from a logged-in browser session).

```bash
cd laravel
cp .env.example .env
php artisan migrate
php artisan video:download "https://www.douyin.com/video/..."
php artisan video:process --source-video=1
```

Worker must be running (`worker/README.md`). `video:process` still accepts a local file path without `--source-video`.

## Layout (private storage)

```
laravel/storage/app/private/
  sources/{Y}/{m}/{id}/original.mp4
  out/{job_id}.mp4
  processed/   # reserved
```

## Tests

```bash
cd laravel && php artisan test
cd worker && pytest
```
