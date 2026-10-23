# 6.6 – Gọi API đổi trạng thái khi thả thẻ (`onEnd`)

**Ngày:** 17/10/2026 · **Nhánh:** `feature/frontend-tan` · **Màn hình:** A6 · Làm chung với [6.3](Phan%206.3.md), [6.4](Phan%206.4.md), [6.5](Phan%206.5.md)

## Mục tiêu
Thả thẻ sang cột khác thì gọi `PATCH /api/applications/{id}/status` ngay. Lỗi thì **trả thẻ về cột cũ** và báo lỗi.

## Đã làm
- `onEnd` của SortableJS: thả sang cột khác thì gọi `moveApplication(id, cột mới)`; thả lại cột cũ thì chỉ vẽ lại bảng. Menu ⋮ cũng gọi cùng hàm này.
- `moveApplication`:
  1. Đổi `status` trong dữ liệu đang hiện và vẽ lại ngay, để thẻ sang cột mới đúng vị trí theo điểm. Thẻ bị đánh dấu đang lưu: mờ đi, không kéo được, bấm chuyển lần nữa thì bỏ qua.
  2. Gọi `ApplicationAPI.updateStatus`.
  3. Thành công: thay bằng hồ sơ backend trả về, hiện toast "Đã chuyển … sang …".
  4. Lỗi: đổi lại `status` cũ, vẽ lại (thẻ về cột cũ), toast đỏ "Chưa chuyển được …: lý do. Thẻ đã về cột …".
  5. Lỗi 401: không hiện toast; `Auth.onUnauthorized` đã đưa về màn hình đăng nhập.
- Không tự gọi lại API trong lúc đang có thẻ chờ lưu, để kết quả cũ không ghi đè.

## File thay đổi
Xem [6.3](Phan%206.3.md#file-thay-đổi-chung-63–66).

## Kiểm thử
Xem bảng chung ở [6.3](Phan%206.3.md#kiểm-thử-chung-63–66). Riêng 6.6:
- Kéo thả thật và menu ⋮ thật: backend lưu đúng `screening`, rồi `applied`.
- Lỗi mạng (giả lập): thẻ về cột cũ, toast nêu lý do. Đã sửa lỗi câu thông báo bị hai dấu chấm ("sau..").
- Token hỏng (thật): 401, về màn hình đăng nhập, backend không đổi.

## Lưu ý
- Kéo thẻ sang *Phỏng vấn* hoặc *Đề nghị / Từ chối* **chưa** gửi email. Mục 7 do backend làm.
