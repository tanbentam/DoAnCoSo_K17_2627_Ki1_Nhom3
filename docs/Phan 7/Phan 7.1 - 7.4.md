# 7.1 – 7.4 – Gửi email tự động cho ứng viên

**Ngày:** 23/10/2026 · **Nhánh:** `feature/email`

## Mục tiêu
- **7.1** Service gửi email qua SMTP (Gmail + App Password).
- **7.2** Thư xác nhận đã nhận hồ sơ, gửi khi ứng viên nộp.
- **7.3** Thư mời phỏng vấn khi HR chuyển thẻ sang *Phỏng vấn*.
- **7.4** Thư báo trúng tuyển (*Đề nghị nhận việc*) hoặc thư cảm ơn, từ chối (*Từ chối*).

**Đã chốt với bạn:**
- Frontend hỏi xác nhận trước khi gửi.
- Địa điểm làm việc là chữ tự do trong tin tuyển dụng, không làm bảng quản lý chi nhánh.
- Giờ và địa điểm phỏng vấn do HR nhập lúc chuyển thẻ, được bỏ trống. Bỏ trống thì thư ghi "HR sẽ liên hệ để thống nhất".

## Đã làm
**7.1 – Service email** (`services/email_service.py`)
- Dùng `smtplib` có sẵn của Python, không thêm thư viện. Cổng 587 dùng STARTTLS, cổng 465 dùng SSL, thời gian chờ 20 giây.
- Có 3 chế độ theo `EMAIL_MODE`:
  - `smtp`: gửi thật.
  - `file`: ghi thư thành tệp `.eml` vào `backend/outbox/`. Đây là **mặc định**, để thử mà không tốn hạn mức Gmail.
  - `off`: tắt.
- Mỗi thư có cả bản chữ thường và bản HTML.
- Địa chỉ người nhận được kiểm tra: phải có `@`, không có khoảng trắng hay xuống dòng (chống chèn header).
- `send_email()` **không bao giờ ném lỗi**. Gửi lỗi (sai mật khẩu, mất mạng) chỉ ghi log và trả `False`, không ảnh hưởng nghiệp vụ.
- Thêm biến môi trường: `EMAIL_MODE`, `SMTP_TIMEOUT_SECONDS`, `EMAIL_FROM_NAME`, `COMPANY_NAME`, `EMAIL_OUTBOX_DIR`. `SMTP_PASSWORD` tự bỏ dấu cách vì Google hiển thị App Password thành 4 nhóm.

**Mẫu thư** (`services/email_templates.py`)
- Có 4 hàm: `application_received`, `interview_invitation`, `offer_letter`, `rejection_letter`. Tất cả dùng chung một khung HTML (inline CSS, rộng tối đa 600px).
- Họ tên, tên vị trí và địa điểm đều được `html.escape` trước khi chèn vào HTML.
- Giờ phỏng vấn đổi từ UTC sang giờ Việt Nam (UTC+7) và ghi kèm thứ, ví dụ "09:30, Thứ Tư 28/10/2026".

**Gửi ngầm** (`services/email_notifications.py`, chạy bằng `BackgroundTasks`, mỗi lần mở session CSDL riêng)
- **7.2:** `POST /api/applications/apply` xếp thư xác nhận **trước** tác vụ AI chấm điểm, nên thư đi sau vài giây chứ không phải chờ AI 30–40 giây.
- **7.3, 7.4:** `PATCH /api/applications/{id}/status`
  - Chỉ gửi khi trạng thái **thật sự đổi** và trạng thái mới là `interview`, `offer` hoặc `rejected`.
  - Body nhận thêm:
    - `send_email` (mặc định `true`);
    - `interview_at` (ISO, có múi giờ);
    - `interview_location`.
  - Lịch phỏng vấn chỉ được lưu khi chuyển sang `interview`. Giờ đã qua (trễ quá 5 phút) bị từ chối với mã 400.
  - Response có thêm `email_queued`.

**CSDL** (`migrate_db.py`, đã chạy trên Aiven)
- Thêm `jobs.location VARCHAR(255)`, `applications.interview_at DATETIME` và `applications.interview_location VARCHAR(255)`. Cả ba cột đều cho phép rỗng.
- Tin tuyển dụng có trường `location`: API tạo và sửa tin nhận trường này; gửi chuỗi rỗng thì địa điểm được xóa thành `null`.

**Frontend**
- **Hộp xác nhận** khi chuyển sang *Phỏng vấn*, *Đề nghị nhận việc* hoặc *Từ chối*. Hộp này mở ra từ cả ba cách chuyển: kéo thả, menu ⋮ trên thẻ và menu trong modal chi tiết.
  - Hộp ghi rõ loại thư và email người nhận, có ô tick "Gửi …" (mặc định bật).
  - Riêng *Phỏng vấn* có thêm ô thời gian (không cho chọn giờ đã qua) và ô địa điểm (điền sẵn địa điểm của tin).
  - Bấm *Hủy* thì thẻ về lại cột cũ.
  - Lỗi khi lưu: hộp vẫn mở, báo lỗi, thẻ ở lại cột cũ.
  - Đang lưu thì không đóng được hộp.
  - Nếu mở từ modal chi tiết thì modal chi tiết tạm ẩn, xong việc tự mở lại.
- Thông báo sau khi chuyển cột ghi thêm "email đang được gửi tới ứng viên" khi `email_queued = true`.
- Modal chi tiết hiện lịch phỏng vấn ("Phỏng vấn: 09:30 28/10/2026 · địa điểm") khi hồ sơ đang ở cột *Phỏng vấn*.
- Form tạo và sửa tin có ô **Địa điểm làm việc**. Địa điểm hiện trên thanh thông tin tin ở Kanban, trên thẻ tin và modal JD của cổng ứng viên. Ô tìm việc của ứng viên tìm được theo địa điểm.

## File thay đổi
- Backend mới:
  - `backend/app/services/email_service.py`
  - `backend/app/services/email_templates.py`
  - `backend/app/services/email_notifications.py`
  - `backend/tests/test_email_service.py`
  - `backend/tests/test_email_templates.py`
  - `backend/tests/test_candidate_schema.py`
- Backend sửa:
  - `backend/app/schemas/candidate.py` (hàm `is_valid_candidate_email`)
  - `backend/scripts/smoke_test_api.py` (thêm mục email sai định dạng)
  - `backend/app/core/config.py`
  - `backend/app/models/job.py`
  - `backend/app/models/application.py`
  - `backend/app/schemas/job.py`
  - `backend/app/schemas/application.py`
  - `backend/app/api/jobs.py`
  - `backend/app/api/applications.py`
  - `backend/migrate_db.py`
- Frontend:
  - `frontend/admin.html`
  - `frontend/js/admin.js`
  - `frontend/js/api.js`
  - `frontend/js/index.js`
- Khác:
  - `.env.example`
  - `.gitignore` (thêm `backend/outbox/`)
  - `README.md`
  - `docs/API cho Frontend.md`
  - `checklist.md`
  - `docs/Phan 7/readme.md`
  - file log này

## Kiểm thử
**Unit test:** `python -m unittest discover -s tests -t .` cho kết quả **207/207 đạt**, gồm 184 test cũ và 23 test mới. Phần mới kiểm:
- giả lập SMTP qua cổng 587 và 465;
- thiếu tài khoản;
- 4 loại lỗi SMTP không làm ném lỗi;
- chế độ `file` và `off`;
- địa chỉ sai, kể cả địa chỉ có chèn `\nBcc:`;
- escape HTML;
- đổi giờ Việt Nam, kể cả khi qua ngày;
- quy tắc trạng thái nào thì gửi thư.

**API trên server thật:** chạy với CSDL Aiven, `EMAIL_MODE=file`, `AI_PROVIDER=local` (Ollama, không gọi Gemini), cổng 8001. Kết quả **28/28 đạt**:
- **Tin tuyển dụng:** địa điểm được bỏ khoảng trắng; chuỗi rỗng thành `null`; dài quá 255 ký tự bị 422; `/api/jobs/open` trả về địa điểm.
- **7.2:** nộp hồ sơ ra đúng 1 thư xác nhận, đúng người nhận và tiêu đề. Tên `<script>` trong bản HTML đã được escape.
- **7.3:**
  - Có lịch: thư ghi 09:30 giờ Việt Nam và đúng địa điểm. CSDL lưu 02:30 UTC.
  - Không lịch: thư ghi "Bộ phận tuyển dụng sẽ liên hệ để thống nhất".
  - Giờ đã qua: trả 400, trạng thái không đổi.
  - Thả lại cùng cột: không gửi.
- **7.4:** *Từ chối* và *Đề nghị nhận việc* gửi đúng thư. `send_email=false` không gửi. Sang *Sàng lọc* không gửi.
- **Lỗi khác:** hồ sơ không tồn tại trả 404; không có token trả 401.

**SMTP Gmail thật:** chỉ thử với tài khoản mẫu trong `.env` (`your_gmail@gmail.com`). Kết nối, EHLO và STARTTLS đạt (mã 220/250). Gmail ngắt ở bước đăng nhập; lỗi được bắt, `send_email` trả `False` sau 2 giây.

**Giao diện:** chạy với backend thử ở trên, đăng nhập bằng tài khoản seed.
- Chuyển thẻ sang *Phỏng vấn* bằng menu ⋮: hộp hiện đúng, địa điểm đã điền sẵn.
  - Nhập giờ năm 2020 thì ô báo đỏ, hộp không đóng.
  - Nhập 09:30 28/10 thì lưu được, có thông báo email, và thư ghi đúng "Thứ Tư 28/10/2026".
- Hủy hộp *Đề nghị nhận việc*: thẻ vẫn ở *Phỏng vấn*.
- Modal chi tiết hiện lịch phỏng vấn.
- Chuyển sang *Từ chối* từ modal chi tiết và bỏ tick gửi email: modal tạm ẩn rồi mở lại, không sinh thư.
- **Mất kết nối** (lỗi do tôi cố ý giả lập bằng cách chặn `fetch` PATCH): hộp vẫn mở, hiện lỗi, thẻ ở lại cột cũ.
- Sửa địa điểm tin thành `Chi nhánh Đà Nẵng <b>x</b>`: hiện nguyên văn dạng chữ trên Kanban và cổng ứng viên (chống XSS). Tìm "da nang" ra đúng tin.
- **Khổ 375px:** hộp xác nhận hiện toàn màn hình, gọn. Bản HTML của thư mời đọc tốt ở 375px.
- Console không có lỗi.
- Tổng cộng `outbox` có đúng 7 thư, khớp với số lần cần gửi.

**Kiểm thử lại 28/10/2026** (trước khi commit, `EMAIL_MODE=file`, `AI_PROVIDER=local`, Ollama tắt nên AI báo lỗi kết nối, thư vẫn gửi bình thường):
- Unit test **210/210 đạt**, gồm 3 test mới trong `tests/test_candidate_schema.py`.
- Kịch bản API email **25/25 đạt**, gồm các trường hợp ở trên và trường hợp email sai định dạng trả 422, không sinh thư.
- `scripts/smoke_test_api.py` **27/28**: thêm mục "Email sai định dạng → 422" (đạt). Mục *Kanban: cập nhật trạng thái* bị script bỏ qua vì cần hồ sơ đã được AI chấm xong (Ollama tắt). Phần này đã được kịch bản email kiểm.
- **Phát hiện lỗi:** email sai lọt vào CSDL làm Kanban lỗi 500. Lỗi do tôi cố ý gửi thẳng API. Đã sửa, xem Lưu ý.
- **Kéo thả bằng chuột trên giao diện:**
  - Sang *Sàng lọc*: không hiện hộp xác nhận.
  - Sang *Phỏng vấn*: hiện hộp xác nhận. Bấm Hủy thì thẻ về cột cũ. Bấm Xác nhận (bỏ trống giờ) thì sinh đúng 1 thư mời, ghi "sẽ liên hệ để thống nhất".
- **Khổ 375px:** hộp *Đề nghị nhận việc* hiện toàn màn hình, không tràn ngang.
- Console không có lỗi, sau khi đã xóa hồ sơ email hỏng.

**Chưa kiểm:**
- **Gửi thật tới hộp thư Gmail:** chưa có App Password thật.
- Hiển thị thư trong Gmail hoặc Outlook thật. Mới xem bản HTML trên trình duyệt.

## Lưu ý
- **Để gửi thật:** bạn điền `SMTP_USER` và `SMTP_PASSWORD` (App Password) rồi đặt `EMAIL_MODE=smtp` trong `.env`, sau đó khởi động lại backend. Gmail cá nhân giới hạn khoảng 500 thư/ngày.
- **Backend đang chạy ở cổng 8000** (không phải tôi mở) vẫn là code cũ. Cần khởi động lại thì mới có địa điểm, lịch phỏng vấn và email.
- **CSDL Aiven dùng chung đã được thêm 3 cột.** Code cũ vẫn chạy được, nhưng nhánh khác cần chạy `python migrate_db.py` nếu dùng CSDL riêng.
- **Hành vi cần biết:**
  - Kéo thẻ ra khỏi *Phỏng vấn* rồi kéo lại sẽ gửi thư mời lần nữa (theo lịch mới nhập).
  - Lịch phỏng vấn cũ vẫn được giữ trong CSDL khi thẻ rời cột, nhưng chỉ hiện khi thẻ đang ở *Phỏng vấn*.
- **Đã sửa 28/10: API nộp hồ sơ kiểm tra định dạng email.** Trước đó gửi thẳng API với email sai (VD thiếu `@`) vẫn được nhận, sau đó `GET /api/applications` trả 500 và cả bảng Kanban của tin đó không tải được. Nay email sai trả 422 "Email không hợp lệ, vui lòng kiểm tra lại", dùng cùng chuẩn `EmailStr` với dữ liệu trả về.
- **Đổi giờ khi thẻ đang ở *Phỏng vấn*** (gửi lại `status=interview` kèm giờ mới) chỉ lưu lịch mới, không gửi lại thư.
- **Dữ liệu thử còn sót:**
  - Không còn dữ liệu thử trong CSDL: đã xóa 2 tin `[TEST] Email 7 …` và 2 ứng viên `test.email7-*@example.com` bằng `scripts/e2e_test_pipeline.py --cleanup`.
  - Đã xóa các tệp `.eml`. Thư mục `backend/outbox/` có thể còn trống và đã nằm trong `.gitignore`.
  - Lần kiểm thử 28/10: đã xóa hết tin `[TEST] Email28 …`, tin smoke `[TEST] …` và ứng viên `test.*` (gồm 1 ứng viên email hỏng `test.bad…example.com`). Kiểm tra lại CSDL còn 0 tin và 0 ứng viên thử.
  - `.claude/launch.json` (không commit) có thêm cấu hình `backend-email-test`.
