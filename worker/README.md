# reup-video-worker

HTTP worker for Phase 1 MVP. See [`../contract/CONTRACT.md`](../contract/CONTRACT.md).

Run: `uvicorn video_worker.app:app --host 127.0.0.1 --port 8765` from `worker/` with `PYTHONPATH=src`.

Install ASR: `pip install -e ".[asr]"` (optional; `PIPELINE_MODE=stub` skips ASR).
