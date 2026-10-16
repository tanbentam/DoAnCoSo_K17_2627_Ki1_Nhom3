# Các vấn đề phát hiện sau lần kiểm thử thật đầu tiên

**Ngày kiểm thử:** 16/10/2026
**Phạm vi:** Toàn bộ luồng AI từ Mục 4.1 đến 4.7. Ứng viên nộp CV qua API thật (`POST /api/applications/apply`), tác vụ ngầm chạy lần lượt: đọc PDF → làm sạch → Gemini bóc tách → so khớp ngữ nghĩa → Hybrid Score. Kết quả lưu vào CSDL Aiven MySQL và được đọc lại qua `GET /api/applications/{id}/ai-analysis`.
**Công cụ:** `backend/scripts/e2e_test_pipeline.py`, cách chạy xem tại [Huong dan kiem thu AI Pipeline.md](../Huong%20dan%20kiem%20thu%20AI%20Pipeline.md).

## Tóm tắt kết quả

Luồng chạy thông suốt cho cả 10 hồ sơ. Không có lỗi nào làm dừng tác vụ ngầm, và khi Gemini lỗi hệ thống vẫn chấm được điểm.

**Bộ 3 CV mẫu theo Mục 8.1** (Job 1 – Backend Developer Python/FastAPI):

| CV | Matching | Hard Filter | Semantic | Kỳ vọng |
| --- | --- | --- | --- | --- |
| CV1 – Rất phù hợp | 89.33 | 100 | 82.21 | > 85 ✅ |
| CV2 – Trái ngành (kế toán) | 10.00 | 25 | 0 | < 40 ✅ |
| CV3 – Khác từ ngữ, đồng nghĩa | 62.36 | 60 | 63.93 | Ở giữa ✅ |

**5 CV thật** (lập trình viên Node.js / PHP / Full-stack, nộp vào Job 1): Matching từ 43.11 đến 56.66. Mức điểm này hợp lý vì các ứng viên đều thiếu FastAPI và SQLAlchemy. 2 hồ sơ nộp vào Job 2 (Frontend) không có kết quả Gemini, do vấn đề [01](01-gemini-het-han-muc-mien-phi.md).

Dữ liệu test (Application #4 – #13) vẫn còn trong CSDL. Xóa bằng lệnh `python scripts/e2e_test_pipeline.py --cleanup`.

## Danh sách vấn đề

| # | Vấn đề | Mức độ | Thành phần | Kế hoạch xử lý |
| --- | --- | --- | --- | --- |
| [01](01-gemini-het-han-muc-mien-phi.md) | Gemini miễn phí chỉ có 20 lượt/ngày, hết lượt vẫn gọi lại vô ích | 🔴 Cao | `gemini_service.py` | [plan-4.9](../Plans/plan-4.9.md) – Giai đoạn A, B, C |
| [02](02-gemini-qua-tai-503.md) | Gemini thường xuyên quá tải (503), xử lý mất tới 98 giây | 🟠 Trung bình | `gemini_service.py` | [plan-4.9](../Plans/plan-4.9.md) – Giai đoạn A, C |
| [03](03-ket-noi-aiven-chua-ssl.md) | Kết nối Aiven MySQL chưa mã hóa SSL | 🟠 Trung bình | `core/database.py` | Mục 2.1 checklist |
| [04](04-pdf-mat-dau-cach.md) | Một số PDF bị đọc ra chữ dính liền, mất dấu cách | 🟡 Thấp | `pdf_service.py` | Chưa lên kế hoạch |
| [05](05-kinh-nghiem-tinh-du-cv-cu.md) | CV cũ ghi "hiện tại" bị tính dư số năm kinh nghiệm | 🟡 Thấp | `cv_extractor.py` | Chưa lên kế hoạch |
| [06](06-cv-docx-khong-duoc-cham.md) | API nhận CV `.docx` nhưng AI chỉ đọc được PDF | 🟡 Thấp | `ai_tasks.py` | Chưa lên kế hoạch |
| [07](07-kinh-nghiem-trai-nganh-van-co-diem.md) | Kinh nghiệm trái ngành vẫn được tính đủ điểm | 🟡 Thấp | `hybrid_scoring.py` | Cần thảo luận |

Mức độ:
- 🔴 Cao: chặn việc test và demo.
- 🟠 Trung bình: ảnh hưởng độ ổn định hoặc bảo mật.
- 🟡 Thấp: làm giảm độ chính xác trong một số trường hợp.

## Ghi nhận khác (không phải lỗi)

- **Gemini suy luận kỹ năng từ mô tả gián tiếp.** Ở CV3, câu "Hệ quản trị cơ sở dữ liệu quan hệ mã nguồn mở của Oracle" được hiểu thành MySQL, và "container" được hiểu thành Docker. Đây là ví dụ tốt cho tính năng Semantic Matching khi bảo vệ. Tuy nhiên nó hơi lệch với quy tắc "không suy đoán" trong prompt, nên cần theo dõi xem có trường hợp suy luận sai không.
- **CV tiếng Anh vẫn có tóm tắt tiếng Việt.** Gemini bóc tách đúng họ tên, kỹ năng và học vấn cho cả 5 CV thật viết bằng tiếng Anh.
- **Thời gian xử lý mỗi hồ sơ:** 15–33 giây khi Gemini ổn định; 77–98 giây khi phải gọi lại do lỗi 503/504.
