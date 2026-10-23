# 5.6 – Trạng thái nộp hồ sơ (`index.html`)

**Ngày:** 17/10/2026 · **Nhánh:** `feature/frontend-tan` · **Màn hình:** P5 (tài liệu Hướng dẫn phát triển Frontend, Mục 4.1)

## Mục tiêu
Ứng viên luôn biết hồ sơ đang ở trạng thái nào: **đang gửi** (spinner, khóa nút), **thành công**, **lỗi** (hiện nguyên văn câu lỗi của backend, sửa xong gửi lại được).

## Đã làm
- **Đang gửi** (`setSubmitting(true)`):
  - Nút "Gửi hồ sơ" bị khóa, đổi thành spinner + "Đang gửi…".
  - Toàn bộ ô nhập nằm trong `<fieldset id="apply-fieldset">` cũng bị khóa (`disabled`).
  - Kéo thả tệp bị bỏ qua.
  - Cờ `isSubmitting` (có từ 5.5) vẫn chặn gửi lặp.
- **Thành công** (`showApplySuccess`):
  - Form được thay bằng khối `#apply-success`: biểu tượng ✓, "Hồ sơ đã được gửi", "Bộ phận tuyển dụng sẽ liên hệ với bạn qua email …", nút "Xem các việc làm khác" (đóng modal).
  - Ẩn nút Gửi.
  - **Không** hiển thị điểm AI.
  - Tiêu điểm chuyển vào khối thông báo (hỗ trợ trình đọc màn hình).
- **Lỗi** (`showApplyError`):
  - Khung `alert-danger` `#apply-error` (`role="alert"`) ở đầu form: "Chưa gửi được hồ sơ" kèm **nguyên văn** câu lỗi (400/404 từ backend, 0 khi mất kết nối).
  - Giữ nguyên dữ liệu đã nhập, mở khóa form để sửa rồi gửi lại.
  - Lần gửi sau sẽ xóa lỗi cũ.
- **Đóng modal hoặc mở tin khác khi đang gửi:** kết quả không vẽ vào modal (so sánh `detailRequestId`), mà báo bằng toast kèm tên vị trí.
- Mở lại tin: `resetApplyForm` → `resetApplyStatus` xóa thông báo thành công / lỗi, hiện lại form.
- Thay toast của 5.5 bằng thông báo ngay trong form.

## File thay đổi
- `frontend/index.html`: thêm `#apply-success`, `#apply-error`, bọc các trường trong `<fieldset id="apply-fieldset">`.
- `frontend/js/index.js`: thêm `setSubmitting`, `showApplyError`, `clearApplyError`, `showApplySuccess`, `resetApplyStatus`; viết lại `submitApplication`; chặn kéo thả khi đang gửi.

## Kiểm thử
Thành công và mất kết nối được **giả lập** (thay tạm `ApplicationAPI.apply`) để không tốn lượt Gemini; luồng gửi thật đã kiểm ở 5.5. Nộp trùng gửi **thật** lên backend.

| Ca | Kết quả |
| --- | --- |
| Đang gửi (giả lập chậm 2–5 giây) | Nút khóa, chữ "Đang gửi…" kèm spinner; fieldset khóa |
| Thành công | Form ẩn, hiện "Hồ sơ đã được gửi" kèm `test.tan@example.com`; nút Gửi ẩn; tiêu điểm vào thông báo; không có điểm số |
| Nộp trùng (backend thật, `400`) | Khung đỏ "Bạn đã nộp hồ sơ ứng tuyển vào vị trí này rồi"; form mở khóa, giữ email; tiêu điểm vào khung lỗi |
| Mất kết nối (`ApiError` status 0) | Khung đỏ "Không kết nối được máy chủ…" |
| Gửi lại sau lỗi | Khung lỗi biến mất ngay khi bấm; sau đó hiện thành công |
| Đóng modal khi đang gửi | Toast `Hồ sơ ứng tuyển "Backend Developer (Python/FastAPI)" đã được gửi`; modal không bị vẽ lại |
| Mở lại tin | Form sạch, không còn lỗi / thông báo cũ, nút Gửi dùng được |
| Khổ điện thoại 375px | Khung lỗi và form hiển thị gọn, không cuộn ngang |
| Network | Cả mục chỉ có các request `400` (nộp trùng); không phát sinh hồ sơ mới |

## Lưu ý
- Khi chụp màn hình lúc spinner đang chạy, ảnh có thể bị mờ. Đây là lỗi của công cụ chụp, trạng thái trên trang vẫn đúng.
- Phần 5 (Cổng ứng viên) đã xong. Có thể đối chiếu với checklist tự kiểm thử "Cổng ứng viên" trong tài liệu Hướng dẫn phát triển Frontend, Mục 8.
