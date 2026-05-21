# AGENTS.md — hướng dẫn cho AI / developer (dự án reup video)

Tài liệu này mô tả **bối cảnh sản phẩm**, **ràng buộc**, và **cách làm việc** khi chỉnh sửa hoặc mở rộng repo. Agent trong Cursor nên đọc file này trước khi thay đổi lớn.

---

# Nguồn plan và tiến độ

- `AGENTS.md` giữ vai trò định hướng dài hạn (mục tiêu, ràng buộc, nguyên tắc thực thi).
- `PROJECT_PLAN.md` là nguồn sự thật cho lộ trình theo phase, backlog task, `Current_focus`, và `Changelog`.
- Khi bắt đầu phiên mới, agent cần đọc **cả hai file**; khi hoàn thành milestone, cập nhật trạng thái trong `PROJECT_PLAN.md` trước.

---

# Mục tiêu sản phẩm

- Pipeline video ngắn (viral nguồn tiếng Trung) → bản tiếng Việt (thuyết minh / lồng tiếng), metadata, file xuất sẵn đăng.
- Quy mô mục tiêu ban đầu:
  - khoảng 1–2 video/ngày
  - ưu tiên ổn định
  - pipeline quan sát/debug được
  - không over-engineer cho scale lớn giai đoạn đầu

---

# Product workflow

Trend discovery
↓
Crawler / downloader
↓
Video ingest
↓
ASR
↓
Translate
↓
TTS
↓
Mix / render
↓
Review / QC
↓
Export package

---

# Monitoring / UX workflow

Import video
↓
Create processing job
↓
Realtime pipeline timeline
↓
Transcript/subtitle review
↓
Preview rendered output
↓
Approve / reject
↓
Export package

Dashboard phải cho phép:
- xem progress realtime
- xem từng step pipeline
- retry step
- re-render
- xem logs
- preview artifact

---

# Kiến trúc triển khai (đã chốt)

## Laravel (orchestrator)

Phụ trách:
- API
- admin/dashboard
- auth
- queue
- metadata
- job orchestration
- realtime monitoring
- artifact management

## Worker project local riêng

Phụ trách:
- ASR
- translation
- TTS
- audio mix
- ffmpeg render
- subtitle generation
- pipeline processing

Không chạy model ML nặng trong PHP.

**Ingest / downloader (Phase 0):** Laravel orchestrator — `source_videos` DB, `video:download` (yt-dlp, Douyin-first), retry/hash/storage. Worker chỉ nhận `input_video_path` đã tải sẵn.

---

# Tích hợp Laravel ↔ worker

Laravel gọi worker qua:
- HTTP
- queue Redis dùng chung
- hoặc Process local

Contract JSON phải ổn định:

```json
{
  "job_id": "uuid",
  "input_path": "...",
  "output_path": "...",
  "status": "processing"
}