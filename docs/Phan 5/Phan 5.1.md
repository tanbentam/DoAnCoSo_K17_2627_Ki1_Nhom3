# 5.1 – Danh sách tin tuyển dụng (`index.html`)

**Ngày:** 17/10/2026 · **Nhánh:** `feature/frontend-tan` · **Màn hình:** P1 (tài liệu Hướng dẫn phát triển Frontend, Mục 4.1)

## Mục tiêu
Trang chủ hiện các tin **đang mở** dạng thẻ: tiêu đề, kỹ năng bắt buộc (nhãn), số năm kinh nghiệm, ngày đăng. Có đủ 3 trạng thái: đang tải, rỗng, lỗi.

## Đã làm
- Gọi `JobAPI.listOpen()` (`GET /api/jobs/open`), **không** dùng `/api/jobs` vì API này trả cả tin đã đóng.
- Mỗi thẻ là một `article.job-card` có `data-job-id`:
  - Tiêu đề, `required_skills` (nhãn `.skill-tag`).
  - Kinh nghiệm: `experience_years_min = 0` thì hiện "Không yêu cầu kinh nghiệm".
  - Ngày đăng: `formatDate(created_at, false)`, giờ Việt Nam.
- **Tìm kiếm ngay trên trang** (ô tìm ở phần đầu trang, như bản mẫu đã duyệt):
  - Lọc theo tiêu đề và kỹ năng bắt buộc / ưu tiên, không phân biệt hoa thường và dấu ("lap trinh" vẫn tìm ra "Lập trình").
  - Lọc phía trình duyệt, không gọi thêm API.
- Dòng "N việc đang tuyển" ở phần đầu trang.
- 3 trạng thái dùng `renderState` (lấy từ `utils.js`):
  - Đang tải.
  - Rỗng: "Hiện chưa có vị trí nào đang tuyển" khi không có tin; "Không tìm thấy vị trí phù hợp" khi lọc không ra kết quả.
  - Lỗi: hiện thông báo của `ApiError` và nút **Thử lại**.
- Bấm thẻ, hoặc dùng phím Enter / Space khi thẻ đang được chọn, sẽ gọi `openJobDetail(id)`. Hiện hàm này chỉ hiện toast giữ chỗ, **mục 5.2 sẽ thay bằng modal**.
- Chống XSS: mọi dữ liệu từ API đều qua `escapeHtml`; `data-job-id` ép kiểu `Number`.

## File thay đổi
- `frontend/js/index.js`: viết mới logic 5.1.
- `frontend/index.html`: thêm ô tìm kiếm `#job-search` và `#job-count` ở phần đầu trang.
- `frontend/css/style.css`: thêm `.hero-search`, `.job-icon`, viền khi chọn thẻ bằng bàn phím (`:focus-visible`).

## Kiểm thử
Backend thật `127.0.0.1:8000`, trang `127.0.0.1:5598/index.html`:

| Ca | Kết quả |
| --- | --- |
| Tải trang | 3 thẻ, "3 việc đang tuyển", ngày `07/10/2026` |
| Tìm "vuejs" / "mysql" / "xyzabc" / xóa ô tìm | 1 / 1 / "Không tìm thấy vị trí phù hợp" / lại đủ 3 thẻ |
| Giả lập mất kết nối | "Không tải được danh sách việc làm" + thông báo lỗi + nút Thử lại |
| Bấm Thử lại khi API trả mảng rỗng | "Hiện chưa có vị trí nào đang tuyển" |
| Tiêu đề / kỹ năng chứa `<b>`, `<img onerror>`, `<script>` | Hiện nguyên văn, không có thẻ HTML nào được tạo |
| Enter trên thẻ | Gọi `openJobDetail(3)` |
| Khổ điện thoại 375px | 1 cột, không bị cuộn ngang |
| Console | Không có lỗi |

## Lưu ý
- CSDL dùng chung có tin #3 "Backend Developer", `preferred_skills = ["string"]`. Đây là dữ liệu thử tạo từ Swagger, không phải lỗi frontend. Nên báo người phụ trách backend sửa hoặc đóng tin này trước buổi demo.
- Khi thử trên máy, nếu sửa CSS mà không thấy thay đổi thì tải lại trang và bỏ qua bộ nhớ đệm (Ctrl+F5).
