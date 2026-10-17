# 5.3 – Form nộp CV (`index.html`)

**Ngày:** 17/10/2026 · **Nhánh:** `feature/frontend-tan` · **Màn hình:** P3 (tài liệu Hướng dẫn phát triển Frontend, Mục 4.1)

## Mục tiêu
Form nộp hồ sơ gồm Họ tên, Email, Số điện thoại, tệp CV. Kiểm tra dữ liệu ngay trên form theo đúng quy tắc của backend, báo lỗi ngay dưới từng trường.

## Đã làm
- Form `#apply-form` đặt **trong modal JD** (theo bản mẫu đã duyệt), ẩn sẵn:
  - Bấm "Ứng tuyển": hiện form, cuộn tới form, đưa tiêu điểm vào ô Họ tên. Nút ở footer đổi thành **"Gửi hồ sơ"** (`type="submit" form="apply-form"`).
  - Mở tin khác: form ẩn đi và được làm sạch (`hideApplyForm` → `resetApplyForm`).
  - Tin đã đóng: không mở được form (kiểm tra lại `status === "open"` khi bấm).
- Kiểm tra từng trường (`fieldValidators`), khớp bảng quy tắc trong tài liệu:

  | Trường | Quy tắc | Câu lỗi |
  | --- | --- | --- |
  | Họ tên | Bắt buộc, 2–150 ký tự (đã `trim`) | "Vui lòng nhập họ tên" / "Họ tên cần từ 2 đến 150 ký tự" |
  | Email | Bắt buộc, ≤ 255 ký tự, đúng định dạng | "Vui lòng nhập email" / "Email chưa đúng định dạng" |
  | Số điện thoại | Không bắt buộc, ≤ 30 ký tự, chỉ chữ số, khoảng trắng, `+ - .` | "Số điện thoại chỉ gồm chữ số…" / "…tối đa 30 ký tự" |
  | Tệp CV | Bắt buộc có tệp | "Vui lòng chọn tệp CV" |

- Bấm Gửi khi còn lỗi: tô đỏ (`is-invalid`) tất cả trường lỗi và đưa tiêu điểm vào trường lỗi đầu tiên. Sau lần bấm Gửi đầu tiên, các trường được kiểm tra lại ngay khi đang gõ.
- **Vùng chọn CV:** bấm để chọn tệp hoặc kéo thả (chỉ lấy 1 tệp). Khi đã có tệp: hiện tên và dung lượng, viền xanh; tên tệp gán bằng `textContent`. Ô `input file` bị ẩn nhưng vẫn dùng được bằng phím Tab (viền vùng chọn sáng lên nhờ `:has()`). Thuộc tính `accept=".pdf"`.
- Form hợp lệ: tạm thời hiện toast giữ chỗ. **Mục 5.5 sẽ gửi `FormData`**.

## File thay đổi
- `frontend/index.html`: thêm `#apply-section` / `#apply-form` vào modal, nút `#apply-submit-btn`.
- `frontend/js/index.js`: thêm `fieldValidators`, `validateField`, `validateApplyForm`, `updateCvLabel`, `resetApplyForm`, `hideApplyForm`, `openApplyForm`, xử lý kéo thả.
- `frontend/css/style.css`: thêm `.apply-box`, `.dropzone` (các trạng thái hover, kéo vào, đã có tệp, lỗi, tiêu điểm bàn phím).

## Kiểm thử
Trên trình duyệt, bấm như người dùng thật (thẻ → Ứng tuyển → Gửi hồ sơ), cộng thêm script thử từng quy tắc:

| Ca | Kết quả |
| --- | --- |
| Bấm Gửi khi chưa điền gì | Lỗi ở Họ tên, Email, CV; tiêu điểm vào Họ tên; SĐT không báo lỗi |
| Họ tên `A`, 151 ký tự, `"  Nguyễn Văn A  "` | Lỗi, lỗi, hợp lệ |
| Email `abc@`, `a b@x.com`, `test.tan@example.com` | Lỗi, lỗi, hợp lệ |
| SĐT `0901-abc`, 31 chữ số, `+84 901.234-567`, rỗng | Lỗi, lỗi, hợp lệ, hợp lệ |
| Kéo thả tệp tên `<img src=x onerror=alert(1)>.pdf` | Nhận 1 tệp, viền xanh, tên hiện nguyên văn, không tạo thẻ `<img>` |
| Điền đủ, bấm Gửi | Hết lỗi, hiện toast giữ chỗ của 5.5 |
| Mở tin khác | Form ẩn, các ô và tệp được xóa, footer quay lại nút "Ứng tuyển" |
| Tin đã đóng #5, bấm Ứng tuyển bằng script | Form không mở |
| Khổ điện thoại 375px | Các trường xếp 1 cột, không cuộn ngang |
| Console / Network | Không có request lỗi mới (các lỗi 404 còn lại là do ca thử tin #999999 của mục 5.2) |

## Lưu ý
- Thuộc tính `maxlength` trên input chặn gõ quá giới hạn; các hàm kiểm tra vẫn xét độ dài cho trường hợp dán chuỗi hoặc gán bằng script.
- Kiểm tra định dạng `.pdf` và dung lượng < 5MB thuộc **mục 5.4**. Hiện mọi tệp đều qua, chỉ cần có tệp.
- Form chỉ nhận PDF, theo đề xuất ở Mục 7 #3 của tài liệu (Issue 06: AI chưa đọc được `.docx`). Nếu nhóm quyết định nhận `.docx` thì sửa `accept` và quy tắc ở 5.4.
