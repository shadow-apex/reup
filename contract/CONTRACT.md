# Laravel ↔ Worker HTTP contract (v1)

Single source of truth for request/response shapes. Implementations: [worker](../worker/) FastAPI, [laravel](../laravel/) HTTP client.

## Headers

| Header | Required | Description |
|--------|----------|-------------|
| `X-Worker-Secret` | Yes | Shared secret; must match worker `WORKER_SECRET` and Laravel `VIDEO_WORKER_SECRET`. |

## Endpoints

### `GET /health`

**200** body matches `schemas/health-response.json`.

### `POST /v1/jobs`

**Request body:** `schemas/job-create-request.json`  
**202** Accepted: job accepted; processing may be async. Body includes `job_id` and `status` (`queued` or `processing`).  
**401** Invalid or missing secret.  
**422** Validation error.  
**500** Server error.

Error bodies: `schemas/error-response.json`.

### `GET /v1/jobs/{job_id}`

**200** body matches `schemas/job-status-response.json`.  
**404** Unknown `job_id`.  
**401** Invalid secret.

## Job status enum

`queued` | `processing` | `completed` | `failed`

## Error codes (worker `error.code`)

| Code | Meaning |
|------|---------|
| `VALIDATION_ERROR` | Request body/paths invalid |
| `UNAUTHORIZED` | Bad `X-Worker-Secret` |
| `NOT_FOUND` | Unknown `job_id` |
| `PIPELINE_ERROR` | Generic pipeline failure |
| `FFMPEG_ERROR` | ffmpeg non-zero exit; `ffmpeg_exit_code` set |
| `FFMPEG_TIMEOUT` | ffmpeg exceeded `FFMPEG_TIMEOUT_SECONDS` |
| `ASR_ERROR` | Speech recognition failed |
| `TRANSLATE_ERROR` | Translation API failed |
| `TTS_ERROR` | Text-to-speech failed (e.g. edge-tts / network) |

## Paths (Windows / shared disk)

`input_video_path` and `output_dir` must be absolute paths readable/writable by the worker process. Laravel and worker on the same machine should use the same base (e.g. `storage/app/...`).
