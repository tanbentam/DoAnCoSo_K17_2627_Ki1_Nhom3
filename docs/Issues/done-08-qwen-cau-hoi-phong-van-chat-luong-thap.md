# 08 – qwen2.5:7b sinh câu hỏi phỏng vấn chất lượng thấp

**Mức độ:** 🟡 Thấp (chỉ ảnh hưởng chế độ `local`, hoặc `auto` khi Gemini không dùng được)
**Trạng thái:** ✅ Đã xử lý (28/10/2026) — prompt riêng cho Ollama, kiểm tra và sinh lại, ghi chú trên giao diện
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

## Kết quả xử lý (28/10/2026) — ✅ Đã xử lý

Làm theo hướng 1, 2 và 4 trong đề xuất. Không đổi model (hướng 3).

**Đã làm:**
1. **Prompt riêng cho Ollama** (`LOCAL_INTERVIEW_SYSTEM_INSTRUCTION` trong `interview_generator.py`):
   - Ngắn hơn, không có quy tắc phủ định, không có ví dụ nội dung (tránh mô hình sao chép ví dụ).
   - Cho mỗi loại câu một khuôn khẳng định. Ví dụ câu `skill_gap`: "Bạn đã làm việc với <kỹ năng gần nhất trong hồ sơ>. Nếu dự án yêu cầu <kỹ năng còn thiếu>, bạn sẽ … như thế nào?"
   - `ai_provider.generate_structured` có thêm tham số `local_system_instruction`, chỉ Ollama dùng (kể cả khi `auto` chuyển sang Ollama). Gemini vẫn dùng prompt cũ.
2. **Kiểm tra bằng code sau khi sinh** (`find_assumed_skill_questions`):
   - Bắt các câu giả định ứng viên đã dùng một kỹ năng còn thiếu: "bạn đã sử dụng/dùng/làm việc với … X", "dự án bạn dùng X", "kinh nghiệm của bạn với X".
   - Không bắt câu cầu nối đúng khuôn ("Bạn đã dùng Flask, nếu cần FastAPI…").
   - Có câu sai thì gọi Ollama lại 1 lần, kèm danh sách câu sai. Sau đó gộp các câu đạt của cả hai lần (mỗi cặp loại câu hỏi + kỹ năng một câu, tối đa 5 câu).
   - Còn ít nhất 1 câu đạt thì chỉ giữ câu đạt. Không còn câu nào đạt thì giữ nguyên lần đầu.
   - Chỉ áp dụng khi câu hỏi do Ollama sinh.
3. **Ghi chú trên giao diện HR** (`frontend/js/admin.js`, tab *Câu hỏi phỏng vấn*): khi `interview_details.ai_meta.provider = "ollama"` thì hiện "Câu hỏi gợi ý do mô hình cục bộ (Ollama) sinh khi chạy offline, chỉ dùng để tham khảo."

**Unit test:** thêm 8 bài trong `tests/test_interview_generator.py` (phát hiện, không bắt nhầm câu cầu nối, sinh lại, gộp, giữ câu đạt khi ít hơn 3 câu, giữ nguyên khi không còn câu đạt, không kiểm tra kết quả Gemini) và 2 bài trong `tests/test_ai_provider.py` (Ollama nhận đúng chỉ dẫn riêng).

**Kết quả thật** (đếm bằng chính `find_assumed_skill_questions` trên câu hỏi của 10 hồ sơ: 3 CV mẫu và 7 lượt CV thật, chế độ `local`):

| Lần chạy | Câu giả định đã dùng kỹ năng còn thiếu |
| --- | --- |
| 16/10 14:28 (trước khi sửa) | 11 / 44 câu |
| 28/10 18:11 (prompt riêng + sinh lại, chưa gộp) | 6 / 36 câu |
| 28/10 18:24 (gộp, nhưng giữ lần đầu khi < 3 câu đạt) | 4 / 41 câu |
| 28/10 (bản cuối, sinh lại trên dữ liệu thật của 11 hồ sơ) | **0 / 46 câu**, hồ sơ nào cũng có 3–5 câu |

**Còn lại:**
- Câu hỏi của qwen vẫn kém tự nhiên hơn Gemini: hay mở đầu "Bạn có thể chia sẻ…", đôi khi 2 câu `experience` gần giống nhau.
- qwen không suy luận được "hệ quản trị CSDL quan hệ mã nguồn mở của Oracle" là MySQL như Gemini (CV3), nên CV3 ở `local` được 54.36 điểm so với 62.36 khi dùng Gemini.
- Mỗi hồ sơ có câu sai tốn thêm khoảng 13 giây cho lần sinh lại.
