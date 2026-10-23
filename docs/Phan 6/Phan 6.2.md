# 6.2 – Form tạo / sửa tin tuyển dụng (`admin.html`)

**Ngày:** 17/10/2026 · **Nhánh:** `feature/frontend-tan` · **Màn hình:** A4 (tài liệu Hướng dẫn phát triển Frontend, Mục 4.2)

## Mục tiêu
HR tạo tin tuyển dụng mới ngay trên bảng điều khiển, nhập được **tiêu chí bắt buộc** (kỹ năng bắt buộc dạng nhãn, số năm kinh nghiệm tối thiểu). Thêm sửa tin và đóng tin có hỏi xác nhận (theo A4).

## Đã làm
- **Bản mẫu tĩnh** đã được duyệt rồi mới áp dụng. Tệp bản mẫu tạm đã xóa.
- **Modal `#job-modal`** dùng chung cho tạo và sửa tin. Trên điện thoại modal mở toàn màn hình.
  - Các ô: tiêu đề, kỹ năng bắt buộc, kinh nghiệm tối thiểu, kỹ năng ưu tiên, mô tả, yêu cầu.
  - Bắt buộc: tiêu đề (tối đa 255 ký tự), ít nhất 1 kỹ năng bắt buộc, mô tả, yêu cầu. Kinh nghiệm phải là số nguyên 0–50; bỏ trống tính là 0.
  - Ô sai được tô đỏ kèm lời nhắc, con trỏ chuyển tới ô sai đầu tiên.
- **Ô nhập kỹ năng dạng nhãn** (`createTagInput`):
  - Enter hoặc dấu phẩy để thêm; dán "A, B, C" tự tách thành 3 nhãn. Chữ còn gõ dở được thêm khi rời ô hoặc khi bấm lưu.
  - Xóa bằng nút × hoặc Backspace khi ô trống.
  - Bỏ nhãn trùng (không phân biệt hoa thường), gộp khoảng trắng thừa, mỗi nhãn tối đa 60 ký tự.
  - Bỏ qua phím Enter khi bộ gõ tiếng Việt đang ghép dấu (`isComposing`).
  - Nhãn tạo bằng `textContent`, không dùng `innerHTML`.
- **Lưu tin:**
  - Tạo tin: `JobAPI.create`. Sửa tin: `JobAPI.update`, gửi đủ các trường.
  - Khi đang lưu: khóa toàn bộ ô nhập, nút hiện spinner "Đang lưu…"; bấm lại cũng không gửi lần hai.
  - Thành công: đóng modal, hiện toast, tải lại danh sách tin và **tự chọn tin vừa lưu**.
  - Lỗi: hiện câu lỗi trong modal, giữ nguyên dữ liệu đang nhập.
- **Sửa tin:**
  - Nhắc "Hồ sơ đã nộp giữ nguyên điểm cũ". Đã kiểm tra backend: sửa tin không làm hồ sơ cũ được chấm lại.
  - Nút **Đóng tin** chỉ hiện khi tin đang mở.
- **Đóng tin:**
  - Bootstrap không chồng được 2 modal, nên ẩn form trước rồi mới hiện hộp xác nhận.
  - *Quay lại* hoặc Esc: mở lại form, chữ đang gõ dở vẫn còn.
  - Xác nhận: gọi `JobAPI.close`. Lỗi thì báo ngay trong hộp xác nhận.
- **Hết phiên (401)** khi đang lưu: mọi modal đóng lại, trang về màn hình đăng nhập.
- **Checklist:** thêm mục 6.9 "Trang quản lý tin tuyển dụng" (theo quyết định của bạn, 17/10/2026). Mục *Tin tuyển dụng* trên thanh điều hướng hiện tạm toast "sẽ có ở mục 6.9".

## File thay đổi
- `frontend/admin.html`: thêm `#job-modal` (form) và `#close-job-modal` (xác nhận).
- `frontend/js/admin.js`: thêm `createTagInput`, các hàm mở / kiểm tra / lưu form, đóng tin.
- `frontend/css/style.css`: thêm `.tag-input`, `.tag-chip` (`required` xanh, `preferred` vàng).
- `checklist.md`: đánh `[x]` 6.2; sửa 6.3 thành 5 cột; thêm mục 6.9.
- `docs/Phan 6/Phan 6.2.md`, `docs/Phan 6/readme.md`.

## Kiểm thử
Backend thật `127.0.0.1:8000`, trang `127.0.0.1:5598/admin.html`. Không gọi AI.

| Ca | Cách thử | Kết quả |
| --- | --- | --- |
| Bấm *Đăng tin* khi bỏ trống | Thật | 4 ô báo đỏ, con trỏ về ô tiêu đề, không gửi API |
| Ô nhãn: gõ `Python` + Enter, `Selenium,pytest,`, `python` (trùng), `Jira` + Enter rồi Backspace | Thật (gõ phím) | Còn `Python, Selenium, pytest` |
| Dán `A, B` | Thật | Tách thành 2 nhãn |
| Kinh nghiệm `1.5` | Thật | Báo đỏ ô kinh nghiệm, không gửi |
| Tạo tin `[TEST] Kiểm thử 6.2 Tester` | Thật | Tạo tin #6; backend lưu đúng mọi trường; trang tự chọn tin #6, toast "Đã đăng tin" |
| Kỹ năng ưu tiên `<img src=x onerror=alert(1)>`, mô tả chứa `<script>` | Thật | Hiện nguyên văn, không chạy script, không sinh thẻ `<img>` |
| Sửa tin: form điền sẵn, xóa nhãn bằng ×, thêm `Postman`, lưu | Thật | Backend lưu `["Docker", "Postman"]`, toast "Đã lưu tin" |
| Đóng tin → *Quay lại* | Thật | Form mở lại, chữ đang gõ dở vẫn còn |
| Đóng tin bị mất kết nối | Giả lập `JobAPI.close` | Hộp xác nhận báo lỗi, vẫn mở, bấm lại được |
| Xác nhận đóng tin #6 | Thật | `status = closed`, tin biến khỏi `/api/jobs/open`, ô chọn ghi `[Đã đóng]` |
| Sửa tin đã đóng | Thật | Không có nút *Đóng tin* |
| Mở *Tạo tin mới* sau khi sửa | Thật | Form trống, không còn dữ liệu cũ |
| Lưu chậm rồi lỗi 422 | Giả lập `JobAPI.create` | "Đang lưu…", khóa ô nhập; bấm lại không gửi lần hai; sau đó báo lỗi trong modal, giữ nguyên dữ liệu |
| Token hỏng khi lưu | Thật | 401, modal đóng hết (không còn backdrop), về màn hình đăng nhập; không tạo thêm tin |
| *Hủy* khi đang sửa tin #1 | Thật | Tin #1 không đổi (`updated_at` giữ nguyên) |
| Khổ 375px | Thật | Modal toàn màn hình, không tràn ngang trang |

Console: chỉ có lỗi 401 do **cố ý** dùng token giả khi thử. `node --check` đạt.

## Lưu ý
- **Dữ liệu thử còn sót:** tin #6 `[TEST] Kiểm thử 6.2 Tester` (đã đóng). Dọn bằng `python scripts/e2e_test_pipeline.py --cleanup` tại `backend/`; script này xóa các tin có tiêu đề bắt đầu bằng `[TEST]`. Tôi chưa chạy script vì CSDL dùng chung với backend.
- Bấm *Hủy* khi đã sửa dữ liệu thì modal đóng luôn, không hỏi "bỏ thay đổi?".
- Backend cho phép mở lại tin đã đóng (`PUT` với `status=open`), nhưng giao diện chưa có nút này vì checklist không yêu cầu.
