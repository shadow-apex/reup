# AGENTS.md — hướng dẫn cho AI / developer (dự án reup video)

Tài liệu này mô tả **bối cảnh sản phẩm**, **ràng buộc**, và **cách làm việc** khi chỉnh sửa hoặc mở rộng repo. Agent trong Cursor nên đọc file này trước khi thay đổi lớn.

## Nguồn plan và tiến độ

- `AGENTS.md` giữ vai trò định hướng dài hạn (mục tiêu, ràng buộc, nguyên tắc thực thi).
- `PROJECT_PLAN.md` là nguồn sự thật cho lộ trình theo phase, backlog task, `Current_focus`, và `Changelog`.
- Khi bắt đầu phiên mới, agent cần đọc **cả hai file**; khi hoàn thành milestone, cập nhật trạng thái trong `PROJECT_PLAN.md` trước.

## Mục tiêu sản phẩm

- Pipeline **video ngắn** (viral nguồn tiếng Trung) → **bản tiếng Việt** (thuyết minh / lồng tiếng), metadata, file xuất sẵn đăng.
- Quy mô mục tiêu ban đầu: **khoảng 1–2 video/ngày**; ưu tiên **ổn định, lặp lại được**, không cần over-engineer cho hàng nghìn job/giờ trừ khi có yêu cầu rõ.

## Kiến trúc triển khai (đã chốt)

- **Ứng dụng chính (Laravel):** API/admin, người dùng, metadata, trạng thái job, lưu file đầu vào/đầu ra (disk hoặc object storage), queue Laravel (Horizon nếu cần).
- **Project local riêng (worker / ML):** ASR, dịch, TTS, mix, **ffmpeg** render — chạy cùng máy hoặc máy có GPU; không chạy model nặng trong PHP.
- **Tích hợp:** Laravel gọi worker qua **HTTP** (ví dụ `http://127.0.0.1:...`), **queue Redis dùng chung** (cùng format payload), hoặc **Process** tới script trong repo worker (biến môi trường đường dẫn). Giữ **một contract** ổn định (JSON: `job_id`, input path, output path, trạng thái); đổi contract thì cập nhật **cả Laravel và worker**.

Repo git này có thể chỉ chứa **tài liệu + contract**; **Laravel app** và **worker** là hai project clone khác — khi đã tạo, ghi tên/đường dẫn repo worker trong `PROJECT_PLAN.md`.

## Phạm vi kỹ thuật (định hướng)

- **Thu thập / tải:** URL hoặc input thủ công; lưu metadata + hash tránh trùng (thường phía Laravel + storage).
- **ASR:** transcript tiếng Trung có timestamp — **thực thi ở worker** (ví dụ `faster-whisper` hoặc tương đương).
- **Dịch + kịch bản VN:** chunk theo câu/segment; tối ưu token; có thể bước chỉnh sửa “hook” đầu video (Laravel gọi LLM API hoặc worker gom một chỗ — chọn một và nhất quán).
- **TTS tiếng Việt:** theo timeline; mix âm thanh (ducking, loudness) qua **ffmpeg** hoặc thư viện trong worker.
- **Render:** watermark, intro/outro template, phụ đề burn-in hoặc track riêng — **ffmpeg** trong worker.
- **Hàng đợi:** Laravel queue cho điều phối; worker có thể HTTP sync hoặc queue riêng — tránh hai tầng cùng claim một bước mà không có idempotency.

Khi thêm code, **bám pipeline trên** thay vì tạo luồng song song không cần thiết.

## Ràng buộc pháp lý & nền tảng (bắt buộc ghi nhớ)

- **Bản quyền và ToS:** tái sử dụng nội dung thương mại, tải hàng loạt từ nền tảng nguồn, và **tự động đăng** (ví dụ TikTok) có thể vi phạm điều khoản hoặc bản quyền. Không implement hoặc khuyến khích **bot đăng vi phạm ToS**; nếu có tích hợp đăng, ưu tiên **API chính thức / bán tự động (xuất file + duyệt người)** và để người vận hành chịu trách nhiệm tuân thủ.
- Agent **không** nên hard-code key API, cookie, hoặc credential; dùng biến môi trường và tài liệu `.env.example` (không commit file `.env` thật).

## Nguyên tắc khi sửa code

- Thay đổi **nhỏ, đúng mục tiêu**; không refactor lan man không liên quan task.
- Khớp **style, cấu trúc thư mục, và công cụ** của từng repo (Laravel vs worker). Đổi **contract** giữa hai bên thì cập nhật đồng bộ và ghi `Changelog` trong `PROJECT_PLAN.md`.
- Video pipeline: xử lý lỗi rõ ràng (exit code ffmpeg, timeout, disk đầy); tránh nuốt lỗi im lặng.
- Tài liệu: chỉ thêm README/MD khi task hoặc product owner yêu cầu; **file này (`AGENTS.md`)** là ngoại lệ cho hướng dẫn agent.

## Stack gợi ý (đã chốt: Laravel + worker local)

- **Orchestrator:** Laravel (API, auth, Filament/Livewire/Inertia tùy chọn), PostgreSQL hoặc MySQL, Redis cho queue/cache.
- **Worker (repo riêng, cùng máy dev):** Python (FastAPI/CLI + `faster-whisper` hoặc tương đương) + ffmpeg; có thể thêm Celery nếu worker cần queue nội bộ.
- **Biến môi trường:** ví dụ `VIDEO_WORKER_BASE_URL`, `VIDEO_WORKER_SECRET`, hoặc `VIDEO_WORKER_PATH` (khi gọi Process); không hard-code đường dẫn máy cụ thể trong code.
- **GPU:** không bắt buộc với 1–2 clip/ngày; khi cần local ASR/TTS, worker chạy trên máy có GPU (VRAM 6GB+ thoải mái cho video ngắn).

## Kiểm tra trước khi merge / giao

- Laravel: **Pint** / **PHPUnit** hoặc **Pest** theo `composer.json` của app.
- Worker: **pytest** / **ruff** theo `pyproject.toml` nếu có.
- Với thay đổi ffmpeg hoặc pipeline render: smoke test **ít nhất một** file video ngắn mẫu (fixture trong worker hoặc đường dẫn được document).

## Cập nhật tài liệu này

Khi đổi hướng sản phẩm (nguồn video, nền tảng đích, policy đăng), cập nhật **mục tiêu** và **ràng buộc** trong file này để agent sau khớp với quyết định mới.