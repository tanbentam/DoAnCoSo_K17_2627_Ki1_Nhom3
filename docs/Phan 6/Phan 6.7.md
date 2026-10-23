# 6.7 – Modal hồ sơ chi tiết và đánh giá AI (`admin.html`)

**Ngày:** 17/10/2026 · **Nhánh:** `feature/frontend-tan` · **Màn hình:** A9, A10 (tài liệu Hướng dẫn phát triển Frontend, Mục 4.2)

> Làm chung đợt và chung commit với [6.8](Phan%206.8.md) (bạn duyệt gộp ngày 17/10/2026). Bảng kiểm thử chung của cả 2 mục nằm ở cuối file này.

## Mục tiêu
HR bấm vào thẻ ứng viên thì mở modal xem hồ sơ chi tiết và bảng đánh giá của AI. Có cả CV gốc.

## Đã làm
- **Bản mẫu tĩnh** đã được duyệt rồi mới áp dụng; tệp bản mẫu tạm đã xóa.
- **Modal `#detail-modal`:** khổ `modal-xl`; trên điện thoại (dưới 768px) mở toàn màn hình. Mở bằng cách bấm vào thẻ hoặc Enter / Space khi thẻ đang được chọn.
- **Đầu modal:**
  - Avatar: chữ cái đầu tiên của tên, bỏ qua ký tự như `[` trong `[TEST]`.
  - Tên, vị trí ứng tuyển, ngày nộp, cột hiện tại.
  - Nút **Chuyển cột**: dùng chung `moveApplication` với kéo thả. Khi đang lưu, nút bị khóa và có spinner; lưu xong thì đầu modal đổi theo.
- **Gọi `ApplicationAPI.getAiAnalysis(id)`** mỗi lần mở modal. Có cơ chế bỏ kết quả cũ khi mở nhanh hồ sơ khác hoặc đóng modal.
- **Thông báo theo `ai_status`:**
  - `pending` / `processing`: spinner "AI đang chấm…".
  - `partial`: cảnh báo vàng kèm `ai_error`.
  - `failed`: báo đỏ kèm `ai_error`, nhắc "vẫn xem được CV gốc".
- **Tab Tổng quan:**
  - Vòng tròn Matching Score, màu theo `scoreClass` (dùng lại class `.score-ring` đã có trong `style.css`). Chưa có điểm thì vòng màu xám, hiện "—".
  - Hai thanh điểm lọc cứng / ngữ nghĩa, kèm công thức chấm.
  - Tóm tắt của AI; liên hệ (`ai_extracted_info`, thiếu thì lấy `candidate.email` / `phone`); AI nào đã chấm (`ai_meta`).
- **Tab Kinh nghiệm & học vấn:**
  - Số năm kinh nghiệm so với yêu cầu của tin (đạt / chưa đạt).
  - Cảnh báo ⚠️ khi `experience_details.discrepancy` — chỉ hiện khi cả 2 con số đều hợp lệ.
  - Quá trình làm việc dạng dòng thời gian (`2023-03` → `03/2023`, `present` → `nay`), học vấn, chứng chỉ, ngoại ngữ, kỹ năng mềm.
- **Tab CV gốc** (A10):
  - Chỉ tải khi mở tab: `getCvBlob` → `URL.createObjectURL` → `<iframe>`.
  - Có nút *Mở trong tab mới* và *Tải về*.
  - Tệp không phải PDF (VD `.docx`, Issue 06): không nhúng, chỉ cho *Tải về* (đúng đuôi `.docx`).
  - Lỗi 404 / mất mạng: báo lỗi kèm Thử lại.
  - Đóng modal thì thu hồi object URL.
- **Tự cập nhật:** khi bảng tự gọi lại API (A8) mà hồ sơ đang mở vừa chấm xong hoặc đổi điểm, modal tải lại kết quả mà **giữ nguyên tab đang xem**.
- **3 trạng thái** cho từng tab: đang tải, rỗng ("Chưa có thông tin…"), lỗi kèm Thử lại.
- **Mọi trường AI có thể `null`:** dùng `?.` / `?? []`; dữ liệu đều qua `escapeHtml`.
- **Sửa thêm `showLogin`:** nếu hết phiên đúng lúc modal đang chạy hiệu ứng mở, modal được đóng lại ngay khi mở xong. Trước đó Bootstrap bỏ qua lệnh đóng, khiến modal che lên màn hình đăng nhập.

## File thay đổi (chung 6.7–6.8)
- `frontend/admin.html`: thêm `#detail-modal` (đầu modal, vùng thông báo, 5 tab).
- `frontend/js/admin.js`: các hàm `openApplicationDetail`, `loadDetail`, `renderDetail*`, `overviewHtml`, `skillsHtml`, `experienceHtml`, `questionsHtml`, `loadCv`, `syncDetailWithBoard`; `formatNumber`, `formatPeriod`; sửa `showLogin`, `moveApplication` (cập nhật đầu modal).
- `frontend/css/style.css`: thêm `.detail-avatar`, `.detail-tabs`, `.skill-chip` (`ok` / `missing` / `pref`), `.timeline-item`, `.question-item`, `.cv-frame`, `.metric-label`.
- `checklist.md`, `docs/Phan 6/Phan 6.7.md`, `Phan 6.8.md`, `readme.md`.

## Kiểm thử (chung 6.7–6.8)
Backend thật `127.0.0.1:8000`, trang `127.0.0.1:5598/admin.html`. **Chỉ gọi AI thật 1 lần**: nộp hồ sơ #57 (`test.tan.detail@example.com`, CV1 mẫu) vào tin #1; AI chấm bằng Gemini.

| Ca | Cách thử | Kết quả |
| --- | --- | --- |
| Bấm thẻ #57 khi AI đang chấm | Thật | Modal mở, thông báo "AI đang chấm…", đã có điểm 89% |
| AI chấm xong khi modal đang mở | Thật | Khoảng 24 s sau thông báo tự mất, tab Câu hỏi hiện 4 câu; không phải đóng / mở lại |
| 5 tab với dữ liệu thật | Thật | Tổng quan: 89%, 100 / 82, tóm tắt, liên hệ, "gemini · gemini-3.8-flash". Kỹ năng: 7 đáp ứng, 0 thiếu. Kinh nghiệm: 5,3 năm, đạt ≥ 2 năm, cảnh báo "CV ghi 3 năm…5,3 năm", 2 công việc, học vấn, chứng chỉ, ngoại ngữ. Câu hỏi: 4 câu có nhãn loại, mở ra xem kỹ năng / mục đích / gợi ý |
| CV gốc | Thật | Tải được PDF 60 KB (`%PDF-`), có nút mở tab mới / tải về; đóng modal thì object URL bị thu hồi |
| Chuyển cột từ modal | Thật | Đang lưu: nút khóa, có spinner, nhãn đổi ngay; xong: thẻ trên bảng và backend đều là `interview`, rồi chuyển lại `screening` |
| Dữ liệu chứa `<img onerror>` ở mọi trường | Giả lập `getAiAnalysis` | Hiện nguyên văn, không chạy, không sinh thẻ `<img>` |
| Kết quả `partial`, câu hỏi chỉ là chuỗi | Giả lập | Cảnh báo vàng; câu hỏi hiện dạng danh sách, không có mũi tên mở rộng |
| Kết quả rỗng (`failed`, mọi trường `null`) | Giả lập | Báo đỏ; vòng điểm "—"; các tab hiện "Chưa có…", không vỡ giao diện |
| Số năm trong CV không phải số | Giả lập | Không hiện câu cảnh báo sai ("CV ghi  năm") |
| Lỗi tải kết quả AI → Thử lại | Giả lập lỗi, sau đó bấm Thử lại với API thật | Báo lỗi kèm nút; bấm thì hiện lại 89% |
| CV 404; CV không phải PDF | Giả lập `getCvBlob` | 404: "Không tìm thấy tệp CV…" kèm Thử lại; `.docx`: không nhúng, tải về đúng tên `….docx` |
| Hết phiên (401) ngay lúc modal đang mở | Thật (token giả) | Về màn hình đăng nhập, modal đóng, không còn nền mờ; đăng nhập lại mở modal bình thường |
| Khổ 375px | Thật | Modal toàn màn hình, thanh tab cuộn ngang, trang không tràn ngang |

Console: chỉ có lỗi 401 do **cố ý** dùng token giả, và `ERR_FILE_NOT_FOUND` do **cố ý** gọi lại object URL đã bị thu hồi để kiểm tra. `node --check` đạt.

## Lưu ý
- **Chưa kiểm được bằng mắt** việc PDF hiện trong `<iframe>`: trong khung trình duyệt dùng để thử, khung PDF hiện màu đen (công cụ chụp màn hình không chụp được trình xem PDF). Dữ liệu tệp đã kiểm là đúng. Cần mở thử trên Chrome thật.
- **Dữ liệu thử còn sót:** hồ sơ #57 (`test.tan.detail@example.com`, tin #1, đang ở cột *Sàng lọc*). Tên lưu thành `[TEST] Tân Chi Ti?t` do lệnh `curl` trên Windows gửi sai mã ký tự khi nộp; lỗi này do cách tôi tạo dữ liệu thử, **không phải lỗi frontend** (form nộp CV ở `index.html` gửi UTF-8 đúng). Dọn bằng `python scripts/e2e_test_pipeline.py --cleanup` tại `backend/`.
