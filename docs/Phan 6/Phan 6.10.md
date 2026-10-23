# 6.10 – Gộp nhánh frontend-hai, áp giao diện của Hải lên frontend-tan

**Ngày:** 23/10/2026 · **Nhánh:** `feature/frontend-tan` · **Mục bổ sung** (bạn quyết định ngày 23/10/2026 vì Hải không kịp làm Kanban và modal AI)

## Mục tiêu
Giữ toàn bộ JS và chức năng của `frontend-tan` (API, Kanban kéo thả, modal AI, quản lý tin), phủ giao diện (HTML/CSS, menu dọc) của nhánh `frontend-hai` lên `index.html` và `admin.html`. Repo chỉ còn một bộ trang.

## Đã làm
- **Gộp nhánh** (commit `221f835`): merge `origin/feature/frontend-hai` vào `feature/frontend-tan`. Có 7 xung đột, đều giữ bản `frontend-tan`:
  - Hải xóa, Tân sửa: `frontend/admin.html`, `index.html`, `js/admin.js`, `js/index.js`.
  - Cả hai sửa: `js/api.js`, `css/style.css`, `README.md`.
  - Bản sửa backend của Hải (`embedding_service.py`, nạp trước thư viện C++ cho PyTorch trên Windows) gộp tự động; import thử chạy bình thường.
- **Bỏ qua bản mẫu tĩnh:** bạn yêu cầu làm liền từ đầu đến cuối, nên không dừng chờ duyệt bản mẫu.
- **`index.html`** theo bố cục `frontend/user/index.html` của Hải:
  - Đầu trang, menu dọc ứng viên, phần giới thiệu kèm ô tìm kiếm, 3 lợi ích, khu việc làm, banner, hướng dẫn 3 bước, chân trang.
  - Đổi từ Bootswatch Zephyr sang Bootstrap 5.3.3 thường, giống Hải.
  - Giữ nguyên 20 `id` mà `index.js` dùng. Modal JD và form nộp CV giữ markup cũ, chỉ đổi kiểu.
  - **Không mang sang** (thiếu JS bên `index.js`): lọc theo ngành nghề, lọc theo kinh nghiệm, sắp xếp, nút "Xem thêm". Ô tìm kiếm vẫn lọc ngay khi gõ như trước.
- **`admin.html`** theo `frontend/admin/admin.html` của Hải:
  - Đầu trang (logo, email, nút Đăng xuất), trang đăng nhập 2 cột, khung làm việc có menu dọc xanh navy, tiêu đề lớn, thẻ công cụ.
  - **Giữ Tabler làm nền** vì `admin.js` dùng nhiều thành phần riêng của Tabler (`bg-*-lt`, `avatar`, `btn-ghost`, `card-table`, `empty`). Màu xanh của Hải gán qua biến `--tblr-*`.
  - Menu dọc dùng `[data-view-nav]` + `.nav-link` nên `showView()` trong `admin.js` không phải sửa.
  - Giữ nguyên mọi `id` trong Mục 10 của *Huong dan phat trien Frontend.md*. `admin-nav` giờ là thẻ `<nav>` của menu dọc.
- **`css/style.css`** viết lại:
  - Phần chung lấy của Hải: biến màu, font Segoe UI, nút, form, modal, đầu trang, đăng nhập.
  - Phần chức năng giữ của Tân và đổi sang màu mới: Kanban, thẻ ứng viên, huy hiệu điểm, nhãn kỹ năng, vòng điểm, modal AI, trang quản lý tin.
  - Bỏ các class của Hải mà trang không dùng (`career-*`, `discovery-*`, `job-post`…).
- **`css/menu/menu.css`** của Hải: giữ nguyên. Menu được viết thẳng vào HTML thay vì nạp bằng `fetch` (bỏ `hr-menu.js`, `user-menu.js`).
- **`css/user/candidate-home.css`** của Hải: thêm 1 quy tắc ẩn menu dọc ở cổng ứng viên khi màn hình < 992px, vì menu trùng thanh điều hướng trên đầu và chiếm 312px.
- **Sửa thêm sau khi thử:**
  - Menu HR dưới 992px thu thành một hàng 3 nút (từ 312px xuống 71px).
  - Cột Kanban tối thiểu 195px để 5 cột vừa khung ở 1366px khi có menu dọc.
- **Tài liệu:** README (công nghệ frontend, cây thư mục CSS); *Huong dan phat trien Frontend.md* (mục giao diện, ghi chú `[data-view-nav]`).

## File thay đổi
- `frontend/index.html`, `frontend/admin.html`: viết lại phần HTML.
- `frontend/css/style.css`: viết lại.
- `frontend/css/user/candidate-home.css`: thêm 2 dòng.
- `README.md`, `docs/Huong dan phat trien Frontend.md`, `checklist.md`, `docs/Phan 6/readme.md`, `docs/Phan 6/Phan 6.10.md`.
- **Cần xóa (bạn chạy `git rm`, lệnh xóa của Claude bị chặn quyền):** `frontend/admin/`, `frontend/user/`, `frontend/js/admin/`, `frontend/js/user/`, `frontend/js/menu/`, `docs/Frontend-role-menus.md`. Đây là bộ trang trùng của Hải, bị hỏng sau khi gộp vì gọi `AuthSession` (không có trong `api.js` của Tân). Các file vẫn còn trong lịch sử git (`221f835`).
- Không sửa: `js/*.js`, backend.

## Kiểm thử
- **CSDL Aiven không truy cập được:** tên miền báo *Non-existent domain*, có lẽ dịch vụ miễn phí đang bị tắt. Máy vẫn ra Internet bình thường. Vì vậy:
  - Đã thử với backend thật: trang báo lỗi đúng, có nút Thử lại.
  - Còn lại thử bằng **API giả lập trong trình duyệt** (thay `window.fetch`, không sửa code dự án). Dữ liệu giả có tiền tố `[TEST]`, kèm chuỗi `<img onerror>` để thử XSS. Không gọi API trả phí nào.
- **Cổng ứng viên:**
  - Danh sách 2 tin, tìm "fastapi" ra 1 tin, tìm từ khóa không có thì hiện "Không tìm thấy vị trí phù hợp".
  - Mở modal JD, bấm Ứng tuyển, gửi form rỗng thì báo lỗi đủ 3 trường.
  - Gửi hồ sơ hợp lệ (tệp PDF giả) thì hiện "Hồ sơ đã được gửi" kèm email.
  - Mất kết nối khi gửi: "Không kết nối được máy chủ…".
  - Tải chậm 4 giây: có spinner và chữ "Đang tải…".
- **Trang HR:**
  - Đăng nhập rỗng thì báo lỗi 2 ô; đăng nhập (giả) thì vào bảng, hiện email và chữ cái avatar.
  - Kanban 5 cột, số thẻ đúng (1/2/1/1/1), huy hiệu đúng màu (89 xanh, 64 vàng, 32 đỏ, 81 xanh). Thẻ "đang chấm" và "không chấm được" hiện đúng.
  - Chuyển cột qua menu thẻ thì gọi `PATCH …/status`. Mất kết nối thì thẻ về cột cũ và có thông báo.
  - Modal hồ sơ: các tab Tổng quan / Kỹ năng / Câu hỏi / CV đều có nội dung, CV hiện bằng `iframe`.
  - Trang Tin tuyển dụng:
    - Đếm 3/2/1, lọc *Đã đóng* ra 1 tin.
    - Tạo tin: báo lỗi đủ 4 trường; nhập đủ thì gọi `POST`, bảng thêm 1 dòng, có thông báo.
    - Đóng tin: hộp xác nhận đúng tên, gọi `PATCH …/close`, số đếm cập nhật.
  - Đăng xuất: xóa token, về màn hình đăng nhập.
- **Chống XSS:** chuỗi `<img src=x onerror=…>` trong tiêu đề tin, tên ứng viên, tóm tắt AI, kỹ năng, câu hỏi đều hiện thành chữ. Không có thẻ `<img>` nào được tạo, `window.__xss` không bị gán.
- **Khổ 375px:** cả `index.html` và `admin.html` (đăng nhập, Kanban, Tin tuyển dụng) đều có `scrollWidth = 375`, không phần tử nào tràn ngang. Bảng Kanban cuộn ngang trong khung riêng, như thiết kế cũ.
- **Khổ 1366px:** menu dọc 240px, Kanban vừa khung (1037/1037).
- **Console:** không có lỗi JS. Chỉ có lỗi CORS / `ERR_FAILED` của các lời gọi API thật lúc tải trang: backend trả 500 vì không có CSDL, không phải lỗi giao diện.
- **Thử lại với CSDL thật** (23/10/2026, sau khi bạn bật lại Aiven, commit `7efc99f`):
  - Cổng ứng viên tải đủ 4 tin thật, console không có lỗi.
  - Đăng nhập bằng tài khoản seed `hr@smartrecruit.com` thành công.
  - **Kéo thả bằng chuột thật:** kéo thẻ hồ sơ #58 (tin 8 "Frontend Developer (React)") từ *Sàng lọc* sang *Mới nộp*, có thông báo "Đã chuyển…". Sau đó kéo về *Sàng lọc*; API xác nhận `status = screening`, đúng như ban đầu.
  - Modal hồ sơ #58 với dữ liệu AI thật: vòng điểm 71%, lọc cứng 100, ngữ nghĩa 52, tóm tắt AI, 4 câu hỏi phỏng vấn, kinh nghiệm 5,2 năm.
  - Có 1 lỗi 401 trong console lúc mở trang: token giả `mock-token` còn sót trong `localStorage` từ lần thử bằng API giả lập. Trang xử lý đúng: xóa token và chuyển về màn hình đăng nhập.
- **Chưa kiểm:** nộp CV thật để AI chấm thật (`AI_PROVIDER=auto` sẽ gọi Gemini, tốn lượt). Phần nộp CV không đổi JS; để dành cho mục 8.2 (kiểm thử trọn luồng).

## Lưu ý
- **Dữ liệu thử còn sót:** không có. Dữ liệu `[TEST]` chỉ nằm trong bộ nhớ trình duyệt. Trên CSDL thật chỉ có hồ sơ #58 bị đổi trạng thái 2 lần, và đã được trả về `screening` như cũ (`updated_at` của hồ sơ này đổi theo).
- `.claude/launch.json` (cấu hình chạy máy chủ cho Claude) và các file báo cáo `.docx`/`.pdf` trong `docs/` không thuộc commit này.
- `candidate-home.css` còn các class của Hải không dùng tới (lọc ngành nghề, sắp xếp…). Để lại để dọn ở mục 8.5 hoặc khi làm lại các bộ lọc đó.
- Font đổi từ Be Vietnam Pro sang Segoe UI theo thiết kế của Hải. Trên macOS / Linux sẽ dùng font hệ thống thay thế.
