# 8.2 – Kiểm thử toàn luồng từ ứng viên nộp hồ sơ đến HR thao tác trên Kanban

**Ngày:** 28/10/2026 · **Nhánh:** `feature/email` · **Code:** `3de68c4`

## Mục tiêu
Chạy toàn hệ thống trên app thật (CSDL Aiven, backend, frontend) theo đúng thao tác người dùng, với cả AI cloud (Gemini) và AI local (Ollama), cộng thêm các trường hợp biên.

## Đã làm
- Chạy `scripts/run_backend_tests.py --only-samples` hai lần: `AI_PROVIDER=auto` và `AI_PROVIDER=local`. Mỗi lần gồm unit test, smoke test API và E2E 3 CV mẫu của Mục 8.1.
- **Luồng ứng viên trên `index.html`:**
  - xem tin, mở JD;
  - kiểm tra form: bỏ trống, email sai, tệp `.txt`, tệp lớn hơn 5MB;
  - nộp CV1 thật (chế độ `auto`) và CV3 thật (chế độ `local`, khổ 375px);
  - giả lập mất kết nối khi gửi.
- **Luồng HR trên `admin.html`:**
  - xem điểm, sắp xếp và lọc;
  - xem modal chi tiết (4 tab) và nút *CV gốc*;
  - chuyển cột *Phỏng vấn* → *Đề nghị nhận việc*, *Từ chối*; thử Hủy;
  - tạo, sửa, đóng tin;
  - kiểm tra trạng thái rỗng, mất kết nối, *Thử lại*.
- Đếm thư trong `backend/outbox/` (chế độ `EMAIL_MODE=file`).
- Không sửa code.

## File thay đổi
- `docs/Test-Reports/2026-10-28_1711_toan-app-8.2.md` (báo cáo chi tiết, mới)
- `docs/Test-Reports/2026-10-28_1711_backend-auto.md`, `docs/Test-Reports/2026-10-28_1727_backend-local.md` (script tự sinh)
- `docs/Test-Reports/README.md`
- `docs/Phan 8/readme.md`, file log này
- `checklist.md`

## Kiểm thử
Chi tiết: [2026-10-28_1711_toan-app-8.2.md](../Test-Reports/2026-10-28_1711_toan-app-8.2.md).
- **Tự động:** cả `auto` và `local` đều đạt unit 210, smoke 36/36, E2E 3/3.
  - CV1 = 89.33 và CV2 = 10.0 ở cả hai chế độ.
  - CV3 = 62.36 (`auto`) và 54.36 (`local`).
- **Giao diện:** mọi bước của luồng ứng viên và luồng HR đều đạt.
  - Chống XSS: tên và tiêu đề chứa HTML hiện dạng chữ.
  - Khổ 375px không tràn ngang.
  - Có đủ trạng thái đang tải, rỗng, lỗi. Lỗi mất kết nối do tôi cố ý giả lập.
- **Email (`file`):** 19 thư, khớp đúng số lần cần gửi.
- **Chưa kiểm:**
  - gửi thật qua Gmail (chờ App Password);
  - chạy Ollama khi ngắt mạng (Mục 8.4);
  - nhiều hồ sơ nộp cùng lúc (Mục 8.3).

## Lưu ý
- **Gemini hôm nay chậm:** 3–5 phút mỗi hồ sơ do lỗi 503/504, phải chuyển sang model dự phòng. Khi demo nên dùng `local`, hoặc chấm sẵn hồ sơ trước.
- **Có 1 lần mất kết nối MySQL** trong lúc test, không ảnh hưởng kết quả và chưa tái hiện được.
- **Lỗi nhỏ chưa sửa:** câu báo tệp quá 5MB ghi "tệp của bạn: 5.00 MB" (Mục 8.5 có thể sửa).
- **qwen bỏ sót MySQL ở CV3** (Issue 08).
- **Dữ liệu thử:**
  - Đã dọn hết.
  - Còn ứng viên cũ "Background Task Candidate" (`bg_test_1791392071@example.com`, ngày 07/10) không phải của lần này. Chờ nhóm quyết định có xóa không.
