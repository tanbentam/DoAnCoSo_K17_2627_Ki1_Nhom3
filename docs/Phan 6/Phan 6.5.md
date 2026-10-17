# 6.5 – Thẻ ứng viên (Candidate Card)

**Ngày:** 17/10/2026 · **Nhánh:** `feature/frontend-tan` · **Màn hình:** A7 · Làm chung với [6.3](Phan%206.3.md), [6.4](Phan%206.4.md), [6.6](Phan%206.6.md)

## Mục tiêu
Thẻ hiện tên, vị trí, và huy hiệu Matching Score có màu: ≥ 80% xanh, 50–79% vàng, < 50% đỏ.

## Đã làm
- **Bố cục thẻ** (theo bản mẫu 6.1 đã duyệt; sửa lại sau lần thử đầu vì huy hiệu dài làm tên bị bóp dọc):
  - Dòng 1: họ tên (`candidate.full_name`) và nút ⋮.
  - Dòng 2: **vị trí** = chức danh hiện tại do AI bóc tách (`ai_extracted_info.current_title`). Chưa có thì ghi nghiêng "Chưa có chức danh". (Mọi thẻ trên bảng cùng một tin, nên không lặp lại tên tin.)
  - Dòng 3: huy hiệu và ngày nộp (`formatDate`, giờ Việt Nam).
- **Huy hiệu theo `ai_status`** (theo bảng trong `API cho Frontend.md`):
  - `done`: `NN%`, màu lấy từ `scoreClass` (xanh / vàng / đỏ). Làm tròn trước khi so sánh, nên 79,6 hiện 80% và tô xanh.
  - `partial`: điểm kèm ⚠️, chú thích là `ai_error`.
  - `pending` / `processing`: spinner nhỏ, chữ "Chờ AI" / "Đang chấm".
  - `failed`: "Không chấm được", chú thích là `ai_error`.
  - Có điểm `null` mà không thuộc các trường hợp trên: hiện "—".
- Chống XSS: tên, chức danh, `ai_error` đều qua `escapeHtml`; `data-id` ép kiểu `Number`.
- Bấm vào thẻ hoặc dùng bàn phím: thẻ có `tabindex="0"`, có viền khi được chọn bằng bàn phím.

## File thay đổi
Xem [6.3](Phan%206.3.md#file-thay-đổi-chung-63–66).

## Kiểm thử
Xem bảng chung ở [6.3](Phan%206.3.md#kiểm-thử-chung-63–66): đủ 5 kiểu `ai_status`, các mốc màu 92 / 79,6 / 61 / 20, XSS, và thẻ thật #56 tự đổi từ "Đang chấm" sang 61%.

## Lưu ý
- Thẻ chưa hiện tên kỹ năng hay email. Thông tin chi tiết làm trong modal ở mục 6.7–6.8.
