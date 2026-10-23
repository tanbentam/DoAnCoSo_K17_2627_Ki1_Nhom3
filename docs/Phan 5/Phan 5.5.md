# 5.5 – Gửi `FormData` lên API nộp hồ sơ (`index.html`)

**Ngày:** 17/10/2026 · **Nhánh:** `feature/frontend-tan` · **Màn hình:** P4 (tài liệu Hướng dẫn phát triển Frontend, Mục 4.1)

## Mục tiêu
Form hợp lệ thì gửi hồ sơ lên `POST /api/applications/apply` dạng `multipart/form-data`, báo kết quả cho ứng viên.

## Đã làm
- `buildApplyFormData()` tạo `FormData` gồm `job_id`, `full_name`, `email`, `phone` (chỉ gửi khi có nhập) và `cv_file`. Họ tên và email đã `trim`.
- Gửi qua `ApplicationAPI.apply(formData)` (lấy từ `api.js`). `apiFetch` **không** đặt `Content-Type` cho `FormData`, nên trình duyệt tự thêm boundary.
- `submitApplication()`:
  - Cờ `isSubmitting` chặn gửi lặp khi request trước chưa xong. Không gửi nếu `currentJob.status !== "open"`.
  - Thành công (201): toast "Hồ sơ đã được gửi, bộ phận tuyển dụng sẽ liên hệ với bạn". **Không** hiển thị điểm AI cho ứng viên.
  - Lỗi: toast hiện **nguyên văn** câu lỗi của backend (`ApiError.message`, gồm cả lỗi 400/404 và lỗi 422 đã ghép sẵn).
- Spinner, khóa nút và thông báo hiện ngay trong form thuộc **mục 5.6**. Ở mục này kết quả chỉ báo bằng toast.

## File thay đổi
- `frontend/js/index.js`: thêm `buildApplyFormData`, `submitApplication`, `isSubmitting`; sự kiện submit gọi gửi thật thay cho toast giữ chỗ.

## Kiểm thử
Backend thật (`AI_PROVIDER=auto`; Ollama tắt nên AI dùng Gemini). Email thử `test.tan@example.com`. CV mẫu được đưa vào trình duyệt bằng `DataTransfer`, lấy từ `backend/tests/fixtures/sample_cvs/` qua một server phụ có bật CORS (công cụ thử, không thuộc dự án). Bấm nút "Gửi hồ sơ" như người dùng thật.

| Ca | Kết quả |
| --- | --- |
| Nộp CV1 vào Job 1 | `201 Created`: `application_id: 55`, `ai_status: "pending"`; toast xanh |
| Request gửi đi | Đủ 5 trường `job_id, full_name, email, phone, cv_file` |
| Sau khoảng 40 giây (gọi `GET /api/applications/55`) | `ai_status: done`, `matching_score: 89.33` (đúng mức dự kiến khoảng 89 của CV1); họ tên và SĐT lưu đúng |
| Nộp lại cùng email, cùng tin, bấm Gửi 2 lần liên tiếp | Chỉ **1** request; toast đỏ "Bạn đã nộp hồ sơ ứng tuyển vào vị trí này rồi" |
| Gửi vào tin đã đóng #5 (giả lập frontend chưa biết tin đã đóng) | Toast đỏ "Tin tuyển dụng này đã đóng, không tiếp nhận thêm hồ sơ" |

Chỉ có 1 lần nộp thật đi tới bước AI (tốn lượt Gemini). Hai ca lỗi bị backend chặn trước khi tới AI.

## Lưu ý
- **Dữ liệu thử còn trong CSDL dùng chung:** hồ sơ #55 (`test.tan@example.com`, Job 1). Dọn bằng lệnh `python scripts/e2e_test_pipeline.py --cleanup` tại `backend/` (lệnh này xóa các email `test.*`).
- Backend trả `candidate_id: 47`: email này trùng với một ứng viên thử đã có từ trước, backend dùng lại bản ghi đó. Đây là hành vi của backend, không ảnh hưởng frontend.
- Khi thử nhiều lần, nên bật Ollama hoặc đặt `AI_PROVIDER=local` để không tốn lượt Gemini (tài liệu, Mục 2).
