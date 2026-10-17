# 5.4 – Kiểm tra định dạng và dung lượng tệp CV (`index.html`)

**Ngày:** 17/10/2026 · **Nhánh:** `feature/frontend-tan` · **Màn hình:** P3 (tài liệu Hướng dẫn phát triển Frontend, Mục 4.1)

## Mục tiêu
Chặn ngay ở frontend, trước khi gửi request: tệp sai định dạng và tệp từ 5MB trở lên.

## Đã làm
- Hằng số trong `index.js`:
  - `CV_ALLOWED_EXTENSIONS = [".pdf"]`
  - `CV_MAX_BYTES = 5 * 1024 * 1024`
- `validateCvFile(file)` thay cho phần kiểm tra "có tệp" của 5.3. Kiểm tra lần lượt:
  1. Chưa chọn tệp: "Vui lòng chọn tệp CV".
  2. Đuôi tệp (lấy sau dấu chấm **cuối cùng**, không phân biệt hoa thường) không có trong danh sách: "Chỉ nhận tệp .pdf…". Vì vậy `cv.pdf.exe` bị chặn, `CV.PDF` được nhận.
  3. Tệp 0 byte: "Tệp rỗng…".
  4. `size >= 5MB`: "Tệp phải nhỏ hơn 5MB (tệp của bạn: 7.30 MB)".
- **Kiểm tra ngay khi chọn hoặc kéo thả tệp**, không đợi bấm Gửi. Tệp lỗi: viền đỏ kèm câu lỗi. Tệp hợp lệ: viền xanh (`has-file` chỉ bật khi hợp lệ).
- Bấm Gửi khi tệp lỗi: không gửi, tiêu điểm chuyển vào ô chọn tệp.
- Nhãn vùng chọn tệp hiện dung lượng dạng KB hoặc MB (`formatFileSize`).

## File thay đổi
- `frontend/js/index.js`: thêm `CV_ALLOWED_EXTENSIONS`, `CV_MAX_BYTES`, `fileExtension`, `formatFileSize`, `validateCvFile`; kiểm tra tệp ngay khi `change`; viền xanh chỉ khi tệp hợp lệ.

## Kiểm thử
Tạo tệp giả bằng `File` + `DataTransfer` trên trình duyệt (giống khi kéo thả):

| Tệp | Kết quả |
| --- | --- |
| `cv.txt`, `cv.docx`, `cv.pdf.exe`, `cv` (không đuôi) | Chặn: "Chỉ nhận tệp .pdf…" |
| `cv.pdf` 0 byte | Chặn: "Tệp rỗng…" |
| `cv.pdf` đúng 5MB / 7.3MB | Chặn: "Tệp phải nhỏ hơn 5MB (tệp của bạn: 5.00 MB / 7.30 MB)" |
| `cv.pdf` 5MB − 1 byte, `CV_NguyenVanA.PDF` 300KB | Hợp lệ, viền xanh |
| Điền đủ thông tin nhưng tệp `.txt`, bấm Gửi | Không gửi, tiêu điểm vào ô chọn tệp |
| Đổi sang PDF 200KB, bấm Gửi | Hợp lệ (toast giữ chỗ của 5.5) |
| Console | Không có lỗi mới |

## Lưu ý
- **Chỉ nhận PDF** theo đề xuất ở Mục 7 #3 của tài liệu (Issue 06: AI chưa đọc được `.docx`). Checklist ghi "`.pdf`, `.docx`". Nếu nhóm chốt nhận `.docx`:
  - Thêm `".docx"` vào `CV_ALLOWED_EXTENSIONS`.
  - Sửa `accept` của `#apply-cv` và nhãn "CV (PDF, dưới 5MB)" trong `index.html`.
- Backend (`backend/app/api/applications.py`) vẫn nhận `.pdf` và `.docx`, chặn khi `size > 5MB`. Frontend chặt hơn: chỉ PDF và `size < 5MB` (đúng như tài liệu). Tệp đúng 5MB bị frontend chặn dù backend vẫn nhận; chênh lệch 1 byte này không ảnh hưởng thực tế.
- Kiểm tra theo đuôi tệp, không theo MIME type, vì trình duyệt báo MIME không ổn định. Backend cũng kiểm tra theo đuôi.
