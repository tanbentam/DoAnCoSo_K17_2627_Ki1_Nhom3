# 6.1 – Khung bảng điều khiển HR (`admin.html`)

**Ngày:** 17/10/2026 · **Nhánh:** `feature/frontend-tan` · **Màn hình:** A1, A2, A3 (tài liệu Hướng dẫn phát triển Frontend, Mục 4.2)

## Mục tiêu
Có khung trang `admin.html` theo bản mẫu đã duyệt: màn hình đăng nhập, thanh điều hướng Bootstrap 5 (Tabler), ô chọn tin tuyển dụng, khung Kanban **5 cột**. Đủ 3 trạng thái: đang tải, rỗng, lỗi.

## Đã làm
- **Quyết định đã chốt (17/10/2026):** Kanban **5 cột** khớp 5 trạng thái của backend: Mới nộp (`applied`), Sàng lọc (`screening`), Phỏng vấn (`interview`), Đề nghị nhận việc (`offer`), Từ chối (`rejected`). Khai báo trong mảng `KANBAN_COLUMNS` của `admin.js`.
- **Bản mẫu tĩnh** đã được duyệt rồi mới áp dụng. Tệp bản mẫu tạm (`frontend/_mau-admin.html`) đã xóa, không đưa vào commit.
- **A1 – Đăng nhập** (trong `admin.html`, ẩn / hiện bằng JS, theo đề xuất số 4 của tài liệu):
  - Kiểm tra ô trống / email sai định dạng ngay trên trình duyệt (`is-invalid`).
  - Khi đang gửi: khóa nút, hiện spinner "Đang đăng nhập…".
  - Lỗi: hiện nguyên văn câu lỗi của backend trong khung đỏ.
  - Nút hiện / ẩn mật khẩu (`aria-pressed`).
  - Có token thì vào thẳng bảng điều khiển.
  - API HR trả 401 (token hỏng hoặc hết hạn): `Auth.onUnauthorized` đưa về màn hình đăng nhập, báo "Phiên đăng nhập đã hết hạn" và tự điền lại email vừa dùng.
- **A2 – Thanh điều hướng:**
  - Logo, các mục *Bảng Kanban*, *Tin tuyển dụng*, *Cổng ứng viên* (mở tab mới).
  - Menu tài khoản: avatar chữ cái đầu, email đã lưu lúc đăng nhập (backend không có API `/me`), nút **Đăng xuất**: xóa token, về màn hình đăng nhập.
  - Trên điện thoại, các mục thu vào nút ☰; menu tài khoản vẫn luôn hiện.
- **A3 – Chọn tin tuyển dụng:**
  - Gọi `JobAPI.list()` (`GET /api/jobs`, gồm cả tin đã đóng).
  - Tin đang mở xếp trước, mới nhất lên trước. Tin đã đóng ghi `[Đã đóng]`.
  - Ghi nhớ tin đang chọn trong `localStorage` (`sr_admin_job`). Không còn tin đó thì chọn tin mới nhất đang mở. Mọi lần đọc / ghi đều bọc `try/catch`.
  - Dòng thông tin dưới ô chọn: trạng thái tin, ngày đăng (`formatDate`), số năm kinh nghiệm tối thiểu.
  - Nút *Tải lại*. Nếu bấm tải lại nhiều lần, kết quả của lần tải cũ bị bỏ qua.
  - Nút *Tạo tin mới*, *Sửa tin* và mục *Tin tuyển dụng* hiện tạm toast "sẽ có ở mục 6.2".
- **Khung Kanban:** 5 cột rỗng (`.kanban-col[data-status]`, vùng thả `.kanban-list`), số đếm 0, cột *Mới nộp* có ghi chú "Hồ sơ mới, AI đang xử lý". Thẻ ứng viên làm ở 6.3–6.5. Màn hình hẹp thì cuộn ngang trong khung bảng, trang không bị tràn ngang.
- **3 trạng thái** (`renderState`): đang tải; rỗng ("Chưa có tin tuyển dụng nào"); lỗi kèm nút **Thử lại**.
- Chống XSS: tiêu đề tin gán bằng `textContent`, các trường khác qua `escapeHtml`.

## File thay đổi
- `frontend/admin.html`: viết lại theo bản mẫu (đăng nhập, thanh điều hướng, đầu trang chọn tin, vùng Kanban).
- `frontend/js/admin.js`: viết mới logic 6.1.
- `frontend/css/style.css`: thêm `.admin-body`, `.login-page`, `.login-card`, `.job-switch`, `.stat-pill`, `.kanban-board`, `.col-dot`, `.col-hint`…
- `docs/Phan 6/Phan 6.1.md`, `docs/Phan 6/readme.md` (mới), `checklist.md`.
- `docs/Phan 5/readme.md`: điền mã commit 5.6 (`84b3510`).

## Kiểm thử
Backend thật `127.0.0.1:8000`, trang `127.0.0.1:5598/admin.html`. Không gọi AI.

| Ca | Cách thử | Kết quả |
| --- | --- | --- |
| Bấm Đăng nhập khi bỏ trống | Thật | Cả 2 ô báo đỏ, con trỏ về ô email, không gửi API |
| Sai mật khẩu | Thật | Khung đỏ "Email hoặc mật khẩu không chính xác"; nút có spinner khi đang gửi; không lưu token |
| Hiện / ẩn mật khẩu | Thật | Ô đổi `text` ↔ `password`, `aria-pressed` đổi theo |
| Đăng nhập đúng (gõ phím, Enter) | Thật | Vào bảng điều khiển, email và avatar "H" đúng |
| Danh sách tin | Thật | 4 tin: 3 đang mở (mới nhất trước) + `[Đã đóng] [TEST] Smoke Job…` cuối |
| Đổi tin, tải lại trang | Thật | Thông tin dưới ô chọn đổi theo tin; tải lại vẫn giữ tin đã chọn |
| Token hỏng → API HR 401 | Thật (gọi `ApplicationAPI.list` với token giả) | Về màn hình đăng nhập, báo hết phiên, email điền sẵn, đăng nhập lại được |
| Đăng xuất | Thật | Xóa token, về màn hình đăng nhập, toast "Đã đăng xuất" |
| Tiêu đề tin chứa `<img onerror>` | Giả lập `JobAPI.list` | Hiện nguyên văn, không chạy script, không sinh thẻ `<img>` |
| Chưa có tin | Giả lập | "Chưa có tin tuyển dụng nào", ô chọn và nút *Sửa tin* bị khóa |
| Đang tải chậm | Giả lập (trễ 1,5 s) | Spinner, ô chọn ghi "Đang tải tin tuyển dụng…" |
| Mất kết nối → Thử lại | Giả lập lỗi, sau đó bấm Thử lại với API thật | Báo lỗi kèm nút Thử lại; bấm thì tải lại đủ 4 tin và 5 cột |
| Khổ 375px | Thật | Không tràn ngang trang (`scrollWidth = 375`), menu ☰ và menu tài khoản hoạt động, bảng cuộn ngang trong khung |

Console: chỉ có 3 lỗi 401, đều do **cố ý** gửi sai khi thử (1 lần sai mật khẩu, 2 lần dùng token giả). `node --check` đạt.

## Lưu ý
- Lúc mở trang, frontend chỉ kiểm tra token có trong `localStorage` hay không, chưa gọi API để xác minh. Token hết hạn sẽ được phát hiện ở lời gọi API HR đầu tiên (danh sách hồ sơ, mục 6.3), lúc đó trang tự về màn hình đăng nhập.
- Trình duyệt có thể dùng bản `admin.js` cũ trong bộ nhớ đệm. Khi thử, nên tải lại bằng Ctrl+F5.
- Dữ liệu thử: không tạo dữ liệu mới. Tin #5 `[TEST] Smoke Job…` (đã đóng, của backend) vẫn hiện trong danh sách.
