# 7.5 – Sắp xếp và lọc ứng viên theo điểm trên bảng Kanban

**Ngày:** 23/10/2026 · **Nhánh:** `feature/frontend-tan` · Phần backend (`sort_by=score_desc`, `min_score`) đã có từ trước, mục này chỉ làm frontend.

## Mục tiêu
HR xem được thẻ ứng viên trong mỗi cột theo điểm từ cao xuống thấp, và lọc ẩn hồ sơ dưới một ngưỡng điểm. Bạn chọn **mức 2**: thêm ô *Sắp xếp* và ô *Điểm tối thiểu* lên thanh công cụ Kanban, thay vì chỉ ghi chú thứ tự.

## Đã làm
- **Thanh công cụ Kanban** (`admin.html`), cạnh ô chọn tin:
  - *Sắp xếp*: **Điểm cao → thấp** (mặc định) / **Mới nộp trước**.
  - *Điểm tối thiểu*: **Tất cả hồ sơ** (mặc định) / **Từ 50 điểm** / **Từ 80 điểm**. Hai ngưỡng này trùng mốc màu huy hiệu vàng / xanh.
- **Xử lý ngay trên trình duyệt** (`admin.js`, hàm `visibleApplications`), dựa trên danh sách hồ sơ đã tải. Đổi lựa chọn không gọi lại API.
  - Không dùng `min_score` của backend, vì như vậy các hồ sơ đang chờ AI (chưa có điểm) sẽ bị loại khỏi kết quả, và bảng không còn tự cập nhật khi AI chấm xong.
  - *Điểm cao → thấp*: hồ sơ chưa có điểm (đang chấm, không chấm được) xếp cuối; bằng điểm thì giữ thứ tự của API.
  - Lọc điểm so với **điểm đã làm tròn**, giống số hiện trên huy hiệu (79,6 hiện "80%" thì được tính là từ 80). Khi đang lọc thì ẩn hồ sơ chưa có điểm.
- **Thông báo khi đang lọc:**
  - Thêm ô thống kê "Đang hiện N hồ sơ từ X điểm" cạnh "M hồ sơ".
  - Lọc mà không còn hồ sơ nào: hiện dòng "Không có hồ sơ nào từ X điểm trở lên" kèm nút **Hiện tất cả hồ sơ**.
- **Ghi nhớ lựa chọn** trong `localStorage` (`sr_admin_sort`, `sr_admin_min_score`), tải lại trang vẫn giữ. Bị chặn `localStorage` thì dùng mặc định.
- Kéo thả, menu chuyển cột, tự gọi lại API khi còn thẻ đang chấm: giữ nguyên. Các thẻ vẫn không đổi thứ tự trong cùng cột (`sort: false`), luôn theo ô *Sắp xếp*.
- **CSS:** thanh công cụ cho phép xuống dòng (`flex-wrap`), mỗi ô lọc rộng 190px; trên điện thoại các ô xếp dọc, rộng hết khung.

## File thay đổi
- `frontend/admin.html`: thêm 2 ô `#board-sort`, `#board-min-score`.
- `frontend/js/admin.js`: hằng `BOARD_SORT_KEY`, `BOARD_MIN_SCORE_KEY`; các hàm `loadBoardFilters`, `saveBoardFilters`, `visibleApplications`, `onBoardFilterChanged`; sửa `renderBoard`, `renderAppStats`.
- `frontend/css/style.css`: `.job-toolbar`, `.job-selector`, `.board-filter`.
- `checklist.md` (7.5 → `[x]`), `docs/Phan 7/readme.md`, `docs/Phan 7/Phan 7.5.md`.

## Kiểm thử
Chạy với backend và CSDL Aiven thật, đăng nhập bằng tài khoản seed. Chỉ đọc dữ liệu, không ghi gì vào CSDL.
- **Tin 8** có 2 hồ sơ ở cột *Sàng lọc*: #58 được 71 điểm (nộp 17/10) và #59 được 54 điểm (nộp 23/10).
  - *Điểm cao → thấp*: thứ tự 58, 59. *Mới nộp trước*: 59, 58.
  - *Từ 50 điểm*: hiện cả 2, thống kê "Đang hiện 2 hồ sơ từ 50 điểm".
  - *Từ 80 điểm*: không còn thẻ nào, hiện dòng thông báo; bấm **Hiện tất cả hồ sơ** thì ô lọc về "Tất cả", thẻ hiện lại.
- **Tin 3:** hồ sơ #1 (85,5 điểm) và #2 (không chấm được). *Từ 80 điểm* chỉ hiện #1; hồ sơ chưa có điểm bị ẩn đúng.
- **Ghi nhớ:** chọn *Mới nộp trước* + *Từ 80 điểm*, tải lại trang thì vẫn giữ cả hai lựa chọn.
- **Giao diện:**
  - Ở khung rộng khoảng 800px, các ô tự xuống dòng gọn; chữ "Điểm cao → thấp" hiện đủ (lần đầu bị cắt ở 170px, đã nới lên 190px).
  - **Khổ 375px:** không tràn ngang. Lần đầu có một khoảng trống lớn dưới ô chọn tin, do `flex-basis: 260px` thành chiều cao khi thanh công cụ xếp dọc; đã sửa.
- **Console:** không có lỗi.
- **Chưa kiểm:**
  - Hồ sơ đang được AI chấm trong lúc đang lọc. Theo code: hồ sơ chưa có điểm bị ẩn, chấm xong và đủ ngưỡng thì lần tự gọi lại kế tiếp sẽ hiện ra.
  - Tin có nhiều hồ sơ trong cùng cột, vì CSDL hiện chỉ có tối đa 2 hồ sơ mỗi tin.

## Lưu ý
- Dữ liệu thử còn sót: không có (chỉ đọc). `localStorage` của trình duyệt thử đã được trả về mặc định.
- Trang quản lý tin (6.9) không có bộ lọc này; đây chỉ là bộ lọc của bảng Kanban.
