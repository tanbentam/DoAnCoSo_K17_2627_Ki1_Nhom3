# 5.0 – Chuẩn bị nền frontend

**Ngày:** 16–17/10/2026 · **Nhánh:** `feature/frontend-tan` · **Commit:** `419c45f` (giao diện), `949c76e` (`api.js`, `utils.js`)

## Mục tiêu
Có giao diện thống nhất và lớp gọi API dùng chung trước khi code Mục 5 và 6. Sửa 4 lỗi của khung cũ (tài liệu Hướng dẫn phát triển Frontend, Mục 3).

## Đã làm
- **Giao diện** (vẫn là HTML, CSS, JS thuần, CDN, không build):
  - `index.html` dùng Bootswatch Zephyr 5.3.3.
  - `admin.html` dùng Tabler 1.6.1. Tabler đặt Bootstrap ở `window.tabler`, nên trang gán `window.bootstrap = window.tabler`.
  - Chung: Bootstrap Icons 1.13.1, font Be Vietnam Pro. Mọi thẻ CDN có `integrity` tính từ file thật.
  - Bản mẫu giao diện đã được duyệt trước khi áp dụng.
- **Lỗi 1:** đổi `"""` thành `/** */` trong `index.js` và `admin.js`.
- **Lỗi 2:** sửa mã `integrity` của Bootstrap JS.
- **Lỗi 3, 4:** viết lại `api.js`:
  - `apiFetch` ghép `headers` sau cùng, tự đặt `Content-Type` JSON (bỏ qua khi gửi `FormData` / `URLSearchParams`).
  - Có tùy chọn `auth` để gắn token, `raw` để lấy blob.
  - 401: xóa token và gọi `Auth.onUnauthorized`.
  - Ném `ApiError { message, status, detail }`: lỗi 422 được ghép thành câu kiểu `title: Field required`; `status = 0` là mất kết nối.
  - API: `AuthAPI`, `JobAPI` (`listOpen`, `list`, `get`, `create`, `update`, `close`), `ApplicationAPI` (`list`, `getDetail`, `getAiAnalysis`, `getCvBlob`, `updateStatus`, `apply`).
- **`utils.js`** (mới): `escapeHtml`, `formatDate` (thêm `Z`, giờ `vi-VN`), `formatScore`, `scoreClass`, `showToast`, `renderState` (đang tải / rỗng / lỗi + nút Thử lại).

## File thay đổi
`frontend/index.html`, `frontend/admin.html`, `frontend/css/style.css`, `frontend/js/api.js`, `frontend/js/utils.js` (mới), `frontend/js/index.js`, `frontend/js/admin.js`, `docs/Huong dan phat trien Frontend.md`.

## Kiểm thử
Gọi trên trình duyệt với backend thật (`127.0.0.1:8000`), frontend phục vụ ở `127.0.0.1:5598`:

| Ca | Kết quả |
| --- | --- |
| `JobAPI.listOpen()` | 3 tin, đều `open` |
| `JobAPI.get(999999)` | `ApiError 404` "Không tìm thấy tin tuyển dụng" |
| API HR khi chưa đăng nhập | `401`, `Auth.onUnauthorized` được gọi |
| Đăng nhập sai / đúng | 401 "Email hoặc mật khẩu không chính xác" / lưu token và email |
| `ApplicationAPI.list({job_id:1, sort_by:"score_desc"})` | Hồ sơ đầu có điểm 89.33, `done` |
| `JobAPI.create({})`, `apply(new FormData())`, `min_score=500` | 422, thông báo ghép đúng từng trường |
| `getAiAnalysis`, `getCvBlob` | Đủ 5 câu hỏi phỏng vấn; PDF 60 KB |
| `renderState` lỗi + Thử lại; `showToast` với chuỗi chứa HTML | Nút gọi lại được; chuỗi HTML hiện nguyên văn (không XSS) |

Console: không có lỗi ngoài các request cố ý gửi sai. `node --check` đạt cho mọi file JS.

## Lưu ý
- `scoreClass` làm tròn điểm trước khi so sánh (79.6 thành 80, xanh), khớp với số hiển thị.
- Trong `utils.js`, `showToast` cần `bootstrap.Toast`, nên trang phải nạp Bootstrap / Tabler JS trước `utils.js`.
