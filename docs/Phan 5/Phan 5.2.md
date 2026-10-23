# 5.2 – Modal chi tiết JD (`index.html`)

**Ngày:** 17/10/2026 · **Nhánh:** `feature/frontend-tan` · **Màn hình:** P2 (tài liệu Hướng dẫn phát triển Frontend, Mục 4.1)

## Mục tiêu
Bấm vào một thẻ việc làm sẽ mở modal hiện đầy đủ JD: mô tả, yêu cầu, kỹ năng bắt buộc / ưu tiên, kèm nút "Ứng tuyển". Nếu tin đã đóng thì ẩn nút và ghi "Tin đã đóng".

## Đã làm
- Thêm khung modal `#job-modal` vào `index.html`. Nội dung do JS điền.
- `openJobDetail(id)`:
  - Mở modal ngay, hiện tiêu đề lấy từ danh sách đã có và spinner trong lúc gọi `JobAPI.get(id)` (`GET /api/jobs/{id}`).
  - Có dữ liệu thì hiện: mô tả, yêu cầu (giữ xuống dòng bằng `.jd-text`), kỹ năng bắt buộc (`.skill-tag`), kỹ năng ưu tiên (`.skill-tag-outline`, ẩn cả dòng nếu `preferred_skills` là `null` hoặc rỗng).
  - **`status !== "open"`**: ẩn nút Ứng tuyển, hiện nhãn "Tin đã đóng". Trường hợp này xảy ra khi HR đóng tin sau lúc ứng viên đã tải trang.
  - Lỗi (VD: 404): hiện thông báo của `ApiError` và nút Thử lại.
  - **Chống kết quả cũ:** mỗi lần mở tăng `detailRequestId`; kết quả trả về chậm của tin mở trước bị bỏ qua.
  - Sau mỗi lần vẽ lại, nếu tiêu điểm không nằm trong modal thì đưa về modal, để Esc vẫn đóng được sau khi bấm Thử lại.
- Nút "Ứng tuyển" gọi `openApplyForm(currentJob)`. Hiện hàm này chỉ hiện toast giữ chỗ, **mục 5.3 sẽ thay bằng form nộp CV**.
- Mọi dữ liệu đều qua `escapeHtml`.

## File thay đổi
- `frontend/index.html`: thêm modal `#job-modal` (tiêu đề, dòng thông tin, phần thân, nhãn "Tin đã đóng", nút Ứng tuyển).
- `frontend/js/index.js`: thêm `openJobDetail`, `jobDetailHtml`, `setApplyAvailable`, `openApplyForm` (giữ chỗ).
- `frontend/css/style.css`: thêm `.jd-text`, `.skill-tag-outline`.

## Kiểm thử
Backend thật, trang `127.0.0.1:5598/index.html`:

| Ca | Kết quả |
| --- | --- |
| Bấm thẻ "Backend Developer (Python/FastAPI)" | Modal đủ mô tả, yêu cầu, 4 kỹ năng bắt buộc, 3 kỹ năng ưu tiên, nút Ứng tuyển |
| Bấm Ứng tuyển | Toast giữ chỗ của mục 5.3 |
| Tin đã đóng #5 (`[TEST] Smoke Job`) | Ẩn nút Ứng tuyển, hiện "Tin đã đóng" |
| Tin không tồn tại #999999 | "Không tải được chi tiết công việc" / "Không tìm thấy tin tuyển dụng" + Thử lại, nút Ứng tuyển ẩn |
| Mở tin 1 (giả lập chậm 800ms) rồi mở ngay tin 2 | Modal hiện tin 2, kết quả tin 1 bị bỏ qua |
| `preferred_skills = null`, yêu cầu chứa `<img onerror>` | Không có dòng "Ưu tiên", không tạo thẻ `<img>` |
| Thử lại rồi nhấn Esc | Modal đóng |
| Khổ điện thoại 375px | Modal vừa màn hình, không bị cuộn ngang |
| Console | Chỉ có lỗi 404 do ca thử tin #999999 (cố ý) |

## Lưu ý
- `GET /api/jobs/{id}` trả 404 với câu "Không tìm thấy tin tuyển dụng". Tài liệu API ghi "Tin tuyển dụng không tồn tại", đó là câu trả về khi **nộp hồ sơ** vào tin không tồn tại. Hai câu khác nhau là bình thường.
