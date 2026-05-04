# PROJECT_PLAN.md — roadmap thực thi cho agent

Mục tiêu file này là làm nguồn sự thật duy nhất về tiến độ triển khai. Mọi agent tab mới cần đọc file này cùng với `AGENTS.md` trước khi code.

**Kiến trúc:** Laravel (orchestrator) + **project local riêng** cho pipeline ML/ffmpeg (worker). MVP monorepo trong repo này: `laravel/`, `worker/`, `contract/`; có thể tách git sau.

## Worker_repo

- `D:\reup-video\worker` (cùng monorepo; đồng bộ contract từ `contract/`).

## Current_focus

- [todo] P2-T1: Tích hợp queue Laravel và lưu job state; worker không double-process cùng `job_id`.

## Phases

### Phase 1 — MVP end-to-end (Laravel + worker local)

**Goal:** Từ Laravel có thể kích hoạt một job xử lý **một video ngắn**; worker thực hiện pipeline và trả output mp4 tiếng Việt; trạng thái theo dõi được trong Laravel.

**Definition_of_done**
- Contract JSON (request/response, lỗi, `job_id`) được document và dùng ở cả hai phía.
- Worker: pipeline ingest → ASR → translate → TTS → mix → render (ffmpeg).
- Laravel: enqueue hoặc sync call worker + persist trạng thái job.
- `.env.example` trên **cả hai** repo; không hard-code secrets.
- Ít nhất 1 smoke test local (thường trên worker; Laravel có thể integration test với mock).

**Tasks**
- `P1-T1` Contract + skeleton repo/worker path (cập nhật `Worker_repo` ở trên).
- `P1-T2` Worker: job mẫu end-to-end cho 1 video (CLI hoặc HTTP).
- `P1-T3` Laravel: job/command gọi worker và cập nhật DB.
- `P1-T4` Smoke test tối thiểu + fixture video ngắn.
- `P1-T5` Logging + error handling (ffmpeg exit code, timeout) thống nhất qua contract.

### Phase 2 — Reliability và queue

**Goal:** Chạy ổn định 1-2 video/ngày với retry hợp lý, tránh job lỗi treo.

**Definition_of_done**
- Laravel queue (Horizon tùy chọn) điều phối job; worker nhận việc ổn định qua HTTP hoặc queue dùng chung (một kiểu đã chốt).
- Có retry policy và idempotency theo hash input.
- Có dashboard/log view trạng thái job cơ bản (Filament hoặc route admin).

**Tasks**
- `P2-T1` Tích hợp queue Laravel và lưu job state; worker không double-process cùng `job_id`.
- `P2-T2` Thêm retry/backoff cho gọi worker và I/O storage.
- `P2-T3` Chặn xử lý trùng theo hash video/script.
- `P2-T4` Trang/endpoint xem lịch sử job và log lỗi từ worker.

### Phase 3 — Publishing workflow an toàn

**Goal:** Tự động hóa mức bán tự động để giảm thao tác tay nhưng vẫn tuân thủ policy nền tảng.

**Definition_of_done**
- Có bước duyệt trước khi đăng.
- Có export metadata (title/caption/hashtags) cho người vận hành.
- Không có bot hành vi vi phạm ToS trong codebase.

**Tasks**
- `P3-T1` Thêm review gate trước publish.
- `P3-T2` Tạo template caption/hashtags theo ngữ cảnh video.
- `P3-T3` Export package để upload thủ công hoặc qua API chính thức (nếu đủ điều kiện).

## Backlog_status

- `P1-T1` done
- `P1-T2` done
- `P1-T3` done
- `P1-T4` done
- `P1-T5` done
- `P2-T1` todo
- `P2-T2` todo
- `P2-T3` todo
- `P2-T4` todo
- `P3-T1` todo
- `P3-T2` todo
- `P3-T3` todo

## Changelog

- 2026-05-04: Phase 1 MVP: thêm `contract/`, `worker/` (FastAPI, stub/real pipeline, pytest), `laravel/` (VideoJob, `video:process`, Http client), `.gitignore` monorepo; smoke test worker (skip nếu không có ffmpeg) + Laravel `Http::fake`.
- 2026-05-04: Chốt kiến trúc **Laravel (orchestrator) + worker project local riêng**; Phase 1 đổi từ CLI-only sang hai repo + contract.
- 2026-05-04: Thêm mục `Worker_repo` và mở rộng `Current_focus` / backlog `P1-T5` (logging ffmpeg).
- 2026-05-04: Khởi tạo roadmap nhiều phase cho dự án reup video.
- 2026-05-04: Chuẩn hóa task ID theo dạng `P{phase}-T{task}` để agent mới bám theo.
