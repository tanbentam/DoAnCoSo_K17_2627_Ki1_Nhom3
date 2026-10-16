# 08 – qwen2.5:7b sinh câu hỏi phỏng vấn chất lượng thấp

**Mức độ:** 🟡 Thấp (chỉ ảnh hưởng chế độ `local`, hoặc `auto` khi Gemini không dùng được)
**Trạng thái:** Chưa xử lý
**Thành phần:** `backend/app/services/interview_generator.py` (Mục 4.8), mô hình Ollama `qwen2.5:7b`
**Phát hiện:** [Báo cáo test 2026-10-16 14:28](../Test-Reports/2026-10-16_1428_backend-local.md), phần "Đánh giá thủ công"

## Hiện tượng

Khi chạy `AI_PROVIDER=local`, nhiều câu hỏi phỏng vấn vi phạm quy tắc trong prompt:

| Hồ sơ | Kỹ năng còn thiếu | Câu hỏi | Vấn đề |
| --- | --- | --- | --- |
| #41 (CV kế toán) | Python, FastAPI, SQLAlchemy, MySQL | "Hãy mô tả một dự án cụ thể bạn đã sử dụng Python để xây dựng một ứng dụng..." | Giả định ứng viên đã dùng kỹ năng còn thiếu |
| #43 (Lê Viết Hưng) | Python, FastAPI, SQLAlchemy, MySQL | "Hãy mô tả cách bạn đã sử dụng SQLAlchemy trong một dự án..." | Như trên |
| #44 (Nguyễn Văn Huy) | FastAPI, SQLAlchemy | 3 câu cùng khuôn "Hãy mô tả cách bạn đã sử dụng X..., và nếu được, hãy so sánh..." | Lặp khuôn; câu 3 vô nghĩa ("so sánh MySQL với các cơ sở dữ liệu khác trong FastAPI") |

Với cùng dữ liệu đầu vào, Gemini sinh câu hỏi bám đúng hồ sơ và tuân thủ quy tắc (xem [Phan 4.8.md](../Phan%204/Phan%204.8.md)).

## Nguyên nhân

Mô hình 7 tỷ tham số (bản rút gọn Q4) tuân thủ kém các quy tắc phủ định dài ("KHÔNG giả định...", "KHÔNG mở đầu..."). Mô hình thường lặp một khuôn câu cho mọi kỹ năng. Cách thêm ví dụ mẫu đã thử ở Mục 4.8 nhưng gây hiện tượng sao chép ví dụ (few-shot leakage).

## Ảnh hưởng

- Chỉ xảy ra khi dùng Ollama: chế độ `local`, hoặc chế độ `auto` khi mọi model Gemini đều lỗi hoặc hết lượt.
- Điểm số không bị ảnh hưởng. Chỉ phần gợi ý câu hỏi cho HR kém hữu ích.
- Rủi ro khi demo bảo vệ ở chế độ offline.

## Hướng xử lý (đề xuất)

1. **Prompt riêng cho mô hình cục bộ:** ngắn hơn, ít quy tắc phủ định. Chuyển các quy tắc thành khuôn câu khẳng định cho từng loại câu hỏi. Ví dụ với kỹ năng còn thiếu: "Bạn đã có kinh nghiệm {kỹ năng gần nhất trong hồ sơ}. Nếu dự án yêu cầu {kỹ năng thiếu}, bạn sẽ ... như thế nào?"
2. **Kiểm tra bằng code sau khi sinh:** câu hỏi loại `skill_gap` chứa mẫu "bạn đã (sử dụng|dùng|làm việc với) {target_skill}" thì gọi lại 1 lần hoặc loại bỏ câu đó.
3. **Thử mô hình cục bộ lớn hơn hoặc mới hơn** nếu VRAM 8GB cho phép (VD: `qwen2.5:14b` bản Q3, hoặc thế hệ Qwen mới hơn), đo lại bằng `run_backend_tests.py` ở chế độ `local`.
4. **Cách tối thiểu:** khi chạy `local`, giao diện HR ghi chú "Câu hỏi gợi ý do mô hình cục bộ sinh — tham khảo".
