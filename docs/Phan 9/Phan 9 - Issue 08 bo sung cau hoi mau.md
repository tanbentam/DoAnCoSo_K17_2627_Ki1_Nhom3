# Phần 9 – Issue 08 (bổ sung): đủ 3 câu hỏi phỏng vấn khi qwen sinh thiếu

## Mục tiêu

Chạy lại test trước khi tạo PR `feature/email` → `main` (30/10/2026), CV2 (trái ngành kế toán) chạy `AI_PROVIDER=local` chỉ còn 2 câu hỏi phỏng vấn, test E2E yêu cầu 3–5 câu. Chạy lại 3 lần đều ra 2 câu nên đây là lỗi thật, không phải ngẫu nhiên. Mục tiêu: hồ sơ nào cũng có ít nhất 3 câu hỏi.

## Đã làm

- **Nguyên nhân:** log backend cho thấy qwen2.5:7b sinh câu `skill_gap` giả định ứng viên đã dùng kỹ năng còn thiếu. Bước kiểm tra của Issue 08 bỏ các câu đó, sinh lại 1 lần, lần sau vẫn sai → chỉ còn 2 câu đạt. CV trái ngành thiếu cả 4 kỹ năng bắt buộc nên dễ gặp nhất.
- **Sửa** (`interview_generator.py`, hàm `_top_up_with_templates`): sau các bước lọc, nếu còn dưới 3 câu thì bổ sung câu hỏi mẫu cho đủ 3:
  1. lần lượt từng kỹ năng bắt buộc còn thiếu, rồi kỹ năng ưu tiên còn thiếu (bỏ kỹ năng đã có câu hỏi): hỏi lộ trình học kỹ năng đó trong 1–2 tháng đầu và kinh nghiệm hiện có nào giúp học nhanh;
  2. hết kỹ năng thiếu thì thêm một câu đào sâu kinh nghiệm liên quan tới vị trí.
- Câu mẫu có ghi chú trong mục đích: "Câu hỏi mẫu do hệ thống bổ sung vì mô hình AI sinh chưa đủ 3 câu", để HR biết đây không phải câu AI soạn.
- Áp dụng cho mọi nhà cung cấp (Gemini hiếm khi thiếu nên thực tế chủ yếu là Ollama). Câu mẫu được viết để không rơi vào lỗi Issue 08.
- Vẫn ghi cảnh báo nếu bổ sung xong vẫn dưới 3 câu (chỉ xảy ra khi không còn kỹ năng nào thiếu).

## File thay đổi

- `backend/app/services/interview_generator.py`
- `backend/tests/test_interview_generator.py`
- `docs/Issues/done-08-qwen-cau-hoi-phong-van-chat-luong-thap.md`, `checklist.md`, `docs/Phan 9/readme.md`
- `docs/Test-Reports/README.md` và 5 biên bản `docs/Test-Reports/2026-10-30_*_backend-local.md`

## Kiểm thử

| Lần chạy (30/10, `local`) | Unit | Smoke | E2E 3 CV mẫu | Ghi chú |
| --- | --- | --- | --- | --- |
| 16:50 | 224/224 | 36/37 | 0/3 | Ollama chưa bật (lỗi môi trường, không phải lỗi code) |
| 16:53 | 224/224 | 37/37 | 2/3 | CV2 chỉ 2 câu hỏi |
| 16:56, 17:04 (chỉ E2E) | — | — | 2/3 | CV2 vẫn 2 câu → lỗi lặp lại |
| **17:08 (sau khi sửa)** | **226/226** | **37/37** | **3/3** | CV2 có 3 câu (2 câu AI + 1 câu mẫu về Python) |

- Điểm 3 CV không đổi: 89.33 / 10.0 / 54.36.
- Unit test: thêm 2 bài (hết kỹ năng thiếu thì thêm câu kinh nghiệm; đã đủ 3 câu thì không bổ sung). Sửa 3 bài cũ cho đúng hành vi mới: bài "ít câu chỉ ghi cảnh báo" thành "bổ sung theo kỹ năng bắt buộc rồi kỹ năng ưu tiên, câu mẫu không rơi vào lỗi Issue 08"; hai bài "giữ câu đạt dù dưới 3 câu" và "không còn câu đạt thì giữ lần đầu" kiểm tra thêm phần bổ sung.
- Frontend thử bằng Playwright: cổng ứng viên hiện 4 tin, HR đăng nhập và tải Kanban được; console chỉ có lỗi 404 `favicon.ico` (có từ trước).
- Cấp 0 lần 17:08 báo ❌ "mô hình nhúng đã nạp": báo động giả đã biết, server vừa khởi động lại nên mô hình chưa nạp.

## Lưu ý

- Dữ liệu thử đã xóa bằng `python scripts/e2e_test_pipeline.py --cleanup`; không còn sót.
- Câu mẫu chung chung hơn câu AI soạn, chỉ dùng để đủ số câu tối thiểu.
- Ollama phải đang chạy (`ollama serve`) trước khi test `local` hoặc demo.
