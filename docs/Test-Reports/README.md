# Lịch sử kiểm thử Backend

Mỗi lần chạy `backend/scripts/run_backend_tests.py`, script tự động làm 2 việc:
- Tạo một báo cáo chi tiết trong thư mục này, tên tệp dạng `YYYY-MM-DD_HHMM_backend-<AI_PROVIDER>.md`.
- Thêm một dòng vào bảng **Các lần chạy tự động** bên dưới.

Cách chạy và tiêu chí đạt: [Huong dan kiem thu Backend.md](../Huong%20dan%20kiem%20thu%20Backend.md).

Ký hiệu:
- Dấu `*` sau commit: lúc chạy test có thay đổi chưa commit, nên code thực tế mới hơn commit đó.
- Các cột Unit / Smoke API / E2E ghi số kiểm tra đạt / tổng số.

## Các lần chạy tự động

| Thời điểm | Commit | AI_PROVIDER | Unit | Smoke API | E2E | Kết quả | Báo cáo / Ghi chú |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-10-16 14:28 | `9b56890`* | `local` | 184 ✅ | 30/30 | 10/10 | ✅ | [2026-10-16_1428_backend-local.md](2026-10-16_1428_backend-local.md) — Test toàn bộ backend sau Mục 4.8 (chạy local, test Gemini đầy đủ vào ngày 17/10) |
| 2026-10-16 15:05 | `4487368`* | `local` | 184 ✅ | 35/35 | 3/3 | ✅ | [2026-10-16_1505_backend-local.md](2026-10-16_1505_backend-local.md) — Thêm ai_status + API xem CV cho frontend; sửa cắt câu có/không |
<!-- Dòng mới được thêm tự động phía trên dòng này -->

## Các lần test thủ công trước khi có script tự động (16/10/2026)

Thời điểm lấy từ log server. Mã commit là trạng thái code lúc test: commit gần nhất cộng các thay đổi được commit ngay sau đó.

| Thời điểm | Code | AI | Phạm vi | Kết quả chính | Tài liệu |
| --- | --- | --- | --- | --- | --- |
| 2026-10-16 11:22 → 11:29 | `0ef32ab`* (Mục 4.1–4.7) | Gemini (chưa có AI_PROVIDER) | E2E 10 hồ sơ: 3 CV mẫu + 7 lượt CV thật | CV1 = 89.33 ✅, CV2 = 10.0 ✅, CV3 = 62.36. Hồ sơ #12, #13 mất kết quả Gemini do hết lượt (429). Phát hiện 7 vấn đề | [Issues/README.md](../Issues/README.md) |
| 2026-10-16 13:21 → 13:26 | `72b4f73`* (+ Mục 4.9, 4.10) | `local` | E2E 10 hồ sơ | 10/10 chạy offline qua qwen2.5:7b, 21–38s mỗi hồ sơ. CV1/CV2 giữ nguyên điểm; qwen tính sai số năm kinh nghiệm | [Phan 4.9 - 4.10.md](../Phan%204/Phan%204.9%20-%204.10.md) |
| 2026-10-16 13:48 → 13:52 | `82c3305`* (+ sửa Issues 03, 05) | `local` | E2E 10 hồ sơ | CSDL mã hóa TLSv1.3. Kinh nghiệm CV1 = 5.3, Huy = 4.1. Phát hiện thêm: Hưng 8.2 (tính cả hoạt động sinh viên), Abhinav 11.0 (CV cũ không có ngày lập) | [done-05](../Issues/done-05-kinh-nghiem-tinh-du-cv-cu.md) |
| 2026-10-16 13:55 → 13:56 | `82c3305`* (sửa tiếp Issue 05) | `local` | E2E 3 hồ sơ (CV1, Hưng, Abhinav) | Kinh nghiệm: Hưng = 7.2, Abhinav = 7.8 (`stated_old_cv`) ✅ | [done-05](../Issues/done-05-kinh-nghiem-tinh-du-cv-cu.md) |
| 2026-10-16 14:09 → 14:11 | `8f9f0a5`* (+ Mục 4.8) | `auto` | E2E 3 CV mẫu | CV1 = 89.33 ✅, CV2 = 10.0 ✅. Sinh 5/5/4 câu hỏi phỏng vấn. Model dự phòng tự xử lý 4 lần lỗi 503 | [Phan 4.8.md](../Phan%204/Phan%204.8.md) |
