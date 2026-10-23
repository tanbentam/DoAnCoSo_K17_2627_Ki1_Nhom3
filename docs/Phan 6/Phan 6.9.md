# 6.9 – Trang quản lý tin tuyển dụng (`admin.html#tin-tuyen-dung`)

**Ngày:** 17/10/2026 · **Nhánh:** `feature/frontend-tan` · **Mục bổ sung** (bạn quyết định thêm ngày 17/10/2026, dùng API sẵn có, không sửa backend)

## Mục tiêu
Mục *Tin tuyển dụng* trên thanh điều hướng mở trang danh sách mọi tin: tiêu đề, trạng thái, ngày đăng, kỹ năng bắt buộc, số hồ sơ; có nút Sửa / Đóng tin / Xem Kanban.

## Đã làm
- **Bản mẫu tĩnh** đã được duyệt rồi mới áp dụng; tệp bản mẫu tạm đã xóa.
- **Hai màn hình trong cùng `admin.html`:** `#view-kanban` (mặc định) và `#view-jobs`.
  - Chuyển bằng địa chỉ: `#kanban` / `#tin-tuyen-dung`. Tải lại trang vẫn giữ màn hình đang xem; nút Back của trình duyệt dùng được.
  - Thanh điều hướng tô mục đang mở (`aria-current`). Trên điện thoại, chọn xong thì menu tự thu lại.
  - Rời Kanban thì dừng tự gọi lại API (A8). Quay lại Kanban thì tải lại danh sách tin, vì có thể vừa sửa ở trang quản lý; tin đang chọn vẫn giữ.
- **Dữ liệu:** 2 lời gọi song song — `JobAPI.list()` và `ApplicationAPI.list({ limit: 500 })` — rồi đếm hồ sơ theo `job_id`; "mới" là hồ sơ còn ở cột *Mới nộp*. Nếu đủ 500 hồ sơ (giới hạn của API) thì ghi "500+" và có dòng chú thích.
- **Đầu trang:** số tin, số tin đang mở, số hồ sơ; nút Tải lại, nút *Tạo tin mới* (dùng lại form 6.2).
- **Bộ lọc:**
  - *Tất cả / Đang mở / Đã đóng*, kèm số lượng (`aria-pressed`).
  - Ô tìm theo tiêu đề và kỹ năng, **không phân biệt dấu**.
  - Hàm `normalizeText` chuyển từ `index.js` sang `utils.js` để cả hai trang dùng chung.
- **Bảng** (từ 768px trở lên):
  - Cột: vị trí kèm kinh nghiệm, trạng thái, 3 kỹ năng bắt buộc đầu tiên rồi "+N", số hồ sơ "(N mới)", ngày đăng.
  - Tin đã đóng hiện chữ xám.
  - Thao tác: nút **Kanban**; menu ⋮ gồm *Sửa tin*, *Xem trên cổng ứng viên*, *Đóng tin* (2 mục sau chỉ với tin đang mở). Bấm vào tiêu đề tin cũng mở Kanban.
- **Điện thoại** (dưới 768px): bảng đổi thành danh sách thẻ, nút Kanban / Sửa / Đóng hiện sẵn.
- **Mở Kanban của một tin:** lưu tin đó vào `sr_admin_job`, rồi chuyển địa chỉ sang `#kanban` → Kanban tự chọn đúng tin.
- **Đóng tin** từ trang này: mở thẳng hộp xác nhận của 6.2 (`confirmCloseJob`). *Quay lại* chỉ đóng hộp, không mở form sửa.
- **Sau khi tạo / sửa / đóng** (`refreshAfterJobChange`): tải lại cả danh sách ở trang quản lý lẫn ô chọn tin của Kanban. Đang ở trang quản lý thì vẫn ở lại đó.
- **3 trạng thái:**
  - Đang tải.
  - Rỗng: "Chưa có tin tuyển dụng nào", hoặc "Không tìm thấy tin phù hợp" khi lọc không ra.
  - Lỗi: kèm nút Thử lại.
- Chống XSS: mọi dữ liệu qua `escapeHtml`; `data-job-id` ép kiểu `Number`.

## File thay đổi
- `frontend/admin.html`: bọc Kanban trong `#view-kanban`, thêm `#view-jobs`; mục điều hướng có `data-view-nav` và địa chỉ `#kanban` / `#tin-tuyen-dung`.
- `frontend/js/admin.js`:
  - Thêm `loadJobsPage`, `renderJobsPage`, `filteredJobs`, `showView`, `viewFromHash`, `confirmCloseJob`, `refreshAfterJobChange`.
  - Bỏ toast tạm "sẽ có ở mục 6.9".
  - `schedulePoll` chỉ chạy khi đang ở Kanban.
- `frontend/js/utils.js`: thêm `normalizeText` (chuyển từ `index.js`).
- `frontend/js/index.js`: bỏ `normalizeText` (đã dùng bản trong `utils.js`).
- `frontend/css/style.css`: thêm `.jobs-search`, `.jobs-table`, `.skill-mini`, `.job-title-link`, `.job-row-closed`.
- `checklist.md`, `docs/Phan 6/Phan 6.9.md`, `docs/Phan 6/readme.md`.

## Kiểm thử
Backend thật `127.0.0.1:8000`, trang `127.0.0.1:5598/admin.html`. Không gọi AI.

| Ca | Cách thử | Kết quả |
| --- | --- | --- |
| Bấm *Tin tuyển dụng* trên thanh điều hướng | Thật | Địa chỉ đổi sang `#tin-tuyen-dung`; 3 tin; số hồ sơ khớp API (tin #3: 2 hồ sơ, đều mới; tin #1: 1 hồ sơ); Kanban ngừng tự gọi lại |
| Tìm `vuejs`, `sqlalchemy` | Thật | Ra đúng 1 tin mỗi lần |
| Tìm không dấu `phat trien`, `KIEM THU PHAN MEM`, có dấu `Kiểm thử` | Thật | Đều ra tin `[TEST] Kiểm thử 6.9 Phát triển` |
| Lọc *Đã đóng* khi chưa có tin đóng | Thật | "Không tìm thấy tin phù hợp" |
| Nút Kanban của tin #2 | Thật | Sang `#kanban`, ô chọn tin là #2 |
| *Tạo tin mới* từ trang quản lý | Thật | Tạo tin #7 `[TEST]…`, vẫn ở trang quản lý, tin mới lên đầu |
| *Sửa tin* từ menu ⋮ | Thật | Form điền sẵn, có nút Đóng tin; lưu kinh nghiệm 3 năm, bảng cập nhật |
| *Đóng tin* từ menu ⋮ → *Quay lại* | Thật | Hộp xác nhận mở thẳng; Quay lại không mở form sửa |
| Xác nhận đóng tin #7 | Thật | Backend `closed`; dòng chữ xám, mất nút Đóng; số đếm 4 / 3 / 1; lọc *Đã đóng* ra đúng tin #7 |
| Tiêu đề, kỹ năng, kinh nghiệm chứa `<img onerror>` | Giả lập `JobAPI.list` | Hiện nguyên văn, không chạy, không sinh thẻ `<img>` |
| 500 hồ sơ (chạm giới hạn) | Giả lập | "500 (250 mới)", thống kê "500+ hồ sơ", có dòng chú thích |
| Chưa có tin / đang tải / lỗi → Thử lại | Giả lập, Thử lại bằng API thật | Đủ 3 trạng thái; Thử lại tải được 4 tin |
| Tải lại trang ở `#tin-tuyen-dung`; nút Back | Thật | Vẫn ở trang quản lý; Back về Kanban |
| Cổng ứng viên sau khi chuyển `normalizeText` | Thật | Tìm `python fastapi` ra 2 tin, có báo khi không tìm thấy |
| Khổ 375px | Thật | Danh sách thẻ, bảng ẩn; trang không tràn ngang; menu ☰ tự thu lại sau khi chọn |

Console: không có lỗi mới. Các lỗi 401 còn hiện là log cũ do **cố ý** dùng token giả khi thử 6.7. `node --check` đạt cho `admin.js`, `index.js`, `utils.js`.

## Lưu ý
- *Xem trên cổng ứng viên* chỉ mở `index.html`, chưa mở thẳng tin đó, vì cổng ứng viên chưa hỗ trợ đường dẫn tới từng tin.
- Số hồ sơ được đếm từ tối đa 500 hồ sơ (giới hạn của API); đủ cho demo. Nếu cần chính xác hơn, đề xuất backend thêm API đếm.
- **Dữ liệu thử còn sót:** tin #7 `[TEST] Kiểm thử 6.9 Phát triển` (đã đóng). Dọn bằng `python scripts/e2e_test_pipeline.py --cleanup` tại `backend/`.
