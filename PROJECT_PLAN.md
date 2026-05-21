# PROJECT_PLAN.md — roadmap thực thi cho agent

Mục tiêu file này là làm nguồn sự thật duy nhất về tiến độ triển khai. Mọi agent tab mới cần đọc file này cùng với `AGENTS.md` trước khi code.

**Kiến trúc:** Laravel (orchestrator) + **project local riêng** cho pipeline ML/ffmpeg (worker). MVP monorepo trong repo này: `laravel/`, `worker/`, `contract/`; có thể tách git sau.

---

# Worker_repo

- `D:\reup-video\worker` (cùng monorepo; đồng bộ contract từ `contract/`).

---

# Current_focus

- [todo] P2-T1: Tích hợp queue Laravel và lưu job state; worker không double-process cùng `job_id`.

---

# Phases

## Phase 0 — Trend ingest & downloader foundation

### Goal

Có thể nhận URL video nguồn hoặc crawl trend cơ bản và tải video ổn định về storage local.

### Definition_of_done

- Có downloader service nhận URL video và lưu local/storage.
- Có metadata DB cho source video.
- Có hash/checksum tránh duplicate.
- Có retry/download timeout handling.
- Có thể mở rộng thêm crawler sau này mà không đổi contract pipeline.

### Tasks

- `P0-T1` Thiết kế source_video schema + metadata.
- `P0-T2` Downloader service cho video nguồn.
- `P0-T3` Retry/backoff và timeout cho download.
- `P0-T4` Hash/checksum chống duplicate.
- `P0-T5` Storage organization cho source/original/processed video.

---

## Phase 1 — MVP end-to-end (Laravel + worker local)

### Goal

Từ Laravel có thể kích hoạt một job xử lý **một video ngắn**; worker thực hiện pipeline và trả output mp4 tiếng Việt; trạng thái theo dõi được trong Laravel.

### Definition_of_done

- Contract JSON (request/response, lỗi, `job_id`) được document và dùng ở cả hai phía.
- Có bước ingest/downloader nhận URL nguồn và lưu file video vào storage local/object storage.
- Có hash/checksum cơ bản cho video đầu vào để phục vụ idempotency và chống trùng ở Phase 2.
- Worker: pipeline download/ingest → normalize → ASR → translate → TTS → mix → render (ffmpeg).
- Laravel: enqueue hoặc sync call worker + persist trạng thái job.
- `.env.example` trên **cả hai** repo; không hard-code secrets.
- Ít nhất 1 smoke test local (thường trên worker; Laravel có thể integration test với mock).

### Tasks

- `P1-T1` Contract + skeleton repo/worker path.
- `P1-T2` Downloader/ingest service: nhận URL video nguồn, tải về local/storage, chuẩn hóa metadata và hash file.
- `P1-T3` Worker: job mẫu end-to-end cho 1 video (CLI hoặc HTTP).
- `P1-T4` Laravel: job/command gọi worker và cập nhật DB.
- `P1-T5` Smoke test tối thiểu + fixture video ngắn.
- `P1-T6` Logging + error handling (download fail, ffmpeg exit code, timeout) thống nhất qua contract.

---

## Phase 2 — Reliability và queue

### Goal

Chạy ổn định 1-2 video/ngày với retry hợp lý, tránh job lỗi treo.

### Definition_of_done

- Laravel queue (Horizon tùy chọn) điều phối job; worker nhận việc ổn định qua HTTP hoặc queue dùng chung (một kiểu đã chốt).
- Có retry policy và idempotency theo hash input.
- Có dashboard/log view trạng thái job cơ bản (Filament hoặc route admin).

### Tasks

- `P2-T1` Tích hợp queue Laravel và lưu job state; worker không double-process cùng `job_id`.
- `P2-T2` Thêm retry/backoff cho gọi worker và I/O storage.
- `P2-T3` Chặn xử lý trùng theo hash video/script.
- `P2-T4` Trang/endpoint xem lịch sử job và log lỗi từ worker.

---

## Phase 2.5 — Monitoring & Review UI

### Goal

Có dashboard realtime quan sát pipeline video processing.

### Definition_of_done

- Có timeline trạng thái từng bước pipeline.
- Có realtime progress update.
- Có trang xem transcript/subtitle.
- Có preview output video.
- Có retry/re-render action.
- Có artifact viewer cho:
  - transcript
  - subtitle
  - translated script
  - generated audio
  - final video

### Tasks

- `P2.5-T1` Job dashboard UI.
- `P2.5-T2` Realtime progress update.
- `P2.5-T3` Transcript/subtitle review UI.
- `P2.5-T4` Video preview + artifact download.
- `P2.5-T5` Retry/re-render workflow.
- `P2.5-T6` Timeline pipeline visualization.
- `P2.5-T7` Step-level logs và duration metrics.

---

## Phase 3 — Publishing workflow an toàn

### Goal

Tự động hóa mức bán tự động để giảm thao tác tay nhưng vẫn tuân thủ policy nền tảng.

### Definition_of_done

- Có bước duyệt trước khi đăng.
- Có export metadata (title/caption/hashtags) cho người vận hành.
- Không có bot hành vi vi phạm ToS trong codebase.

### Tasks

- `P3-T1` Thêm review gate trước publish.
- `P3-T2` Tạo template caption/hashtags theo ngữ cảnh video.
- `P3-T3` Export package để upload thủ công hoặc qua API chính thức (nếu đủ điều kiện).

---

# Backlog_status

- `P0-T1` done
- `P0-T2` done
- `P0-T3` done
- `P0-T4` done
- `P0-T5` done

- `P1-T1` done
- `P1-T2` done
- `P1-T3` done
- `P1-T4` done
- `P1-T5` done
- `P1-T6` done

- `P2-T1` todo
- `P2-T2` todo
- `P2-T3` todo
- `P2-T4` todo

- `P2.5-T1` todo
- `P2.5-T2` todo
- `P2.5-T3` todo
- `P2.5-T4` todo
- `P2.5-T5` todo
- `P2.5-T6` todo
- `P2.5-T7` todo

- `P3-T1` todo
- `P3-T2` todo
- `P3-T3` todo

---

# Changelog

- 2026-05-21: Phase 0 hoàn tất: `source_videos` + migrations, `video:download` (yt-dlp Douyin-first), retry/backoff/timeout, SHA256 dedupe, storage `sources/{Y}/{m}/{id}/`, `video:process --source-video`, tests Laravel, README gốc, ghi chú ingest trong `contract/CONTRACT.md`.
- 2026-05-21: Thêm Phase 2.5 cho realtime monitoring/review dashboard UI.
- 2026-05-21: Thêm Phase 0 cho trend ingest/downloader foundation.
- 2026-05-21: Thêm downloader/ingest vào pipeline chính và bổ sung metadata/hash workflow.
- 2026-05-04: Phase 1 MVP: thêm `contract/`, `worker/` (FastAPI, stub/real pipeline, pytest), `laravel/` (VideoJob, `video:process`, Http client), `.gitignore` monorepo; smoke test worker (skip nếu không có ffmpeg) + Laravel `Http::fake`.
- 2026-05-04: Chốt kiến trúc **Laravel (orchestrator) + worker project local riêng**; Phase 1 đổi từ CLI-only sang hai repo + contract.
- 2026-05-04: Thêm mục `Worker_repo` và mở rộng `Current_focus` / backlog `P1-T5` (logging ffmpeg).
- 2026-05-04: Khởi tạo roadmap nhiều phase cho dự án reup video.
- 2026-05-04: Chuẩn hóa task ID theo dạng `P{phase}-T{task}` để agent mới bám theo.