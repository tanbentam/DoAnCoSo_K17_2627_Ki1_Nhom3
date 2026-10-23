# 6.4 – Kéo thả thẻ bằng SortableJS

**Ngày:** 17/10/2026 · **Nhánh:** `feature/frontend-tan` · **Màn hình:** A6 · Làm chung với [6.3](Phan%206.3.md), [6.5](Phan%206.5.md), [6.6](Phan%206.6.md)

## Mục tiêu
HR kéo thẻ ứng viên qua lại giữa 5 cột.

## Đã làm
- Mỗi `.kanban-list` là một `Sortable` cùng nhóm `kanban`. SortableJS 1.15.2 đã nạp sẵn ở 6.1 qua CDN, có `integrity`.
- Tùy chọn:
  - `sort: false`: không đổi thứ tự trong cùng cột, vì thẻ luôn xếp theo điểm. Thả thẻ sang cột khác thì thẻ tự về đúng vị trí theo điểm.
  - `draggable: ".candidate-card"`: không kéo được ô "Kéo thẻ vào đây".
  - `filter: ".is-saving, .card-menu"`: thẻ đang lưu không kéo được; bấm nút ⋮ không bắt đầu kéo.
  - `delay: 150` + `delayOnTouchOnly`: trên điện thoại phải giữ tay một chút mới kéo, để vẫn cuộn ngang bảng được.
  - Dùng sẵn class `sortable-ghost` / `sortable-chosen` có từ trước trong `style.css`.
- Khi bắt đầu kéo, ẩn ô "Kéo thẻ vào đây". Cột có `min-height: 120px` nên cột rỗng vẫn thả vào được.
- Mỗi lần vẽ lại bảng thì hủy các `Sortable` cũ rồi tạo lại, để không bị trùng.
- **Cách chuyển cột không cần kéo:** menu ⋮ trên thẻ → "Chuyển sang …". Dùng được bằng bàn phím, và tiện trên điện thoại khi kéo khó. Menu dùng `strategy: fixed` để không bị khung cuộn của bảng cắt mất.
- Nếu CDN SortableJS không tải được: hiện toast cảnh báo, vẫn chuyển cột được bằng menu ⋮.

## File thay đổi
Xem [6.3](Phan%206.3.md#file-thay-đổi-chung-63–66).

## Kiểm thử
Xem bảng chung ở [6.3](Phan%206.3.md#kiểm-thử-chung-63–66). Riêng 6.4:
- Kéo thẻ thật bằng chuột từ *Mới nộp* sang *Sàng lọc*: thẻ sang đúng cột, số thẻ cập nhật.
- Menu ⋮ ở khổ 375px: hiện đủ 4 cột đích, không bị cắt; bấm nút ⋮ không mở chi tiết hồ sơ.

## Lưu ý
- Chưa kiểm được thao tác kéo bằng **ngón tay trên điện thoại thật**: công cụ thử chỉ giả lập khổ màn hình, thao tác vẫn là chuột.
