# Hướng dẫn phát triển Frontend

Tài liệu cho người làm frontend SmartRecruit AI (Mục 5 – Cổng ứng viên, Mục 6 – Kanban HR trong `checklist.md`). Đọc xong tài liệu này là có thể bắt đầu code.

| Tài liệu | Dùng để |
| --- | --- |
| **Tài liệu này** | Phạm vi, màn hình cần xây, quy ước code, việc cần sửa trước, cách tự kiểm thử |
| [API cho Frontend.md](API%20cho%20Frontend.md) | Chi tiết từng API: tham số, dữ liệu trả về, mã lỗi |
| Swagger UI http://127.0.0.1:8000/docs | Thử gọi API trực tiếp, luôn khớp với code backend |
| [checklist.md](../checklist.md) Mục 5, 6, 9 | Danh sách việc cần làm và các quyết định còn mở |

**Cập nhật:** 17/10/2026. **Mục 5 và Mục 6 đã xong** trên nhánh `feature/frontend-tan`; nhật ký từng mục ở [docs/Phan 5](Phan%205/readme.md) và [docs/Phan 6](Phan%206/readme.md). Muốn đổi giao diện: xem [Mục 10](#10-đổi-giao-diện-những-gì-không-được-đổi-tên).

---

## 1. Phạm vi và công nghệ

- **Hai trang:**
  - `frontend/index.html`: Cổng ứng viên, công khai.
  - `frontend/admin.html`: Bảng điều khiển HR, cần đăng nhập.
- **Công nghệ** (đã chốt trong đề xuất dự án):
  - HTML5, CSS3, **JavaScript thuần ES6+**.
  - **Bootstrap 5.3.3** và **SortableJS 1.15.2** qua CDN.
  - Giao diện (23/10/2026, theo thiết kế của nhánh `frontend-hai`, xem [Phan 6.10](Phan%206/Phan%206.10.md)):
    - `index.html`: **Bootstrap 5.3.3** (CSS + JS).
    - `admin.html`: **Tabler 1.6.1** (dựng trên Bootstrap 5, thay cả CSS lẫn JS của Bootstrap). Tabler đặt Bootstrap ở `window.tabler`; `admin.html` đã gán `window.bootstrap = window.tabler` nên vẫn gọi được `bootstrap.Modal`, `bootstrap.Toast`… Class Bootstrap dùng như bình thường; thành phần riêng của Tabler xem https://preview.tabler.io. `admin.js` dùng nhiều thành phần riêng của Tabler, nên **không bỏ Tabler**.
    - Chung: icon **Bootstrap Icons 1.13.1** (`<i class="bi bi-..."></i>`), font hệ thống **Segoe UI**. Màu khai báo bằng biến CSS ở đầu `css/style.css` (`--primary`, `--line`…, cùng `--bs-*` cho Bootstrap và `--tblr-*` cho Tabler).
    - CSS: `css/style.css` (chung), `css/menu/menu.css` (menu dọc), `css/user/candidate-home.css` (riêng cổng ứng viên).
    - Mọi thẻ CDN đều có `integrity` (SRI) tính từ file thật. Đổi phiên bản thì phải tính lại mã: `curl -sL <url> | openssl dgst -sha384 -binary | openssl base64 -A`.
  - Không dùng framework, không có bước build. Mở file HTML là chạy.
- **Không làm ở frontend:** chấm điểm, phân tích CV, gửi email. Backend lo hết, frontend chỉ hiển thị kết quả.

---

## 2. Chuẩn bị môi trường

1. **Chạy backend** theo [API cho Frontend.md, Mục 1](API%20cho%20Frontend.md#1-chạy-backend-trên-máy-frontend).
   - Kiểm tra http://127.0.0.1:8000/health có `"status": "healthy"`.
   - Đặt `AI_PROVIDER=local` nếu có Ollama, để thử nhiều lần không tốn lượt Gemini.
2. **Chạy frontend** bằng một web server tĩnh (backend đã mở CORS cho mọi origin), chọn một trong hai cách:
   - Tại thư mục gốc dự án: `python -m http.server 5500 --bind 127.0.0.1 --directory frontend`, rồi mở http://127.0.0.1:5500/index.html và http://127.0.0.1:5500/admin.html.
   - Extension **Live Server** của VS Code: chuột phải `frontend/index.html` → *Open with Live Server*.
   - Sửa code xong mà trình duyệt vẫn chạy bản cũ: tải lại bằng **Ctrl + F5**.
3. **Tài khoản HR:** `hr@smartrecruit.com` / `admin123`.
4. **CV để thử nộp:**
   - 3 CV mẫu trong `backend/tests/fixtures/sample_cvs/`. Nếu chưa có thì tạo bằng `python scripts/generate_sample_cvs.py` tại `backend/`.
   - CV1 nộp vào Job 1 sẽ được khoảng 89 điểm (xanh), CV2 khoảng 10 điểm (đỏ), CV3 khoảng 55–62 điểm (vàng). Đủ để thử cả 3 màu huy hiệu.

> **CSDL dùng chung với backend.** Khi thử, dùng email `test.<tên>@example.com` và tin tuyển dụng có tiêu đề bắt đầu bằng `[TEST]`. Dọn dữ liệu thử: `python scripts/e2e_test_pipeline.py --cleanup` tại `backend/`.

---

## 3. Hiện trạng khung `frontend/` và việc cần sửa trước

Khung đã có từ Mục 1.9: `index.html`, `admin.html`, `css/style.css` (đã có class huy hiệu điểm và cột Kanban), `js/api.js`, `js/index.js`, `js/admin.js`. **Làm tiếp trên khung này**, nhưng phải sửa 4 lỗi sau trước khi code tính năng:

| # | Lỗi | Hậu quả | Cách sửa |
| --- | --- | --- | --- |
| 1 | `js/index.js` và `js/admin.js` mở đầu bằng `"""` (cú pháp chú thích của Python) | **SyntaxError**, cả hai file không chạy | Đổi thành chú thích JS `/** ... */` |
| 2 | Mã `integrity` của Bootstrap JS trong cả 2 file HTML bị sai | Trình duyệt **chặn tải** `bootstrap.bundle.min.js`, nên modal, dropdown, toast không hoạt động | Thay bằng mã đúng: `sha384-YvpcrYf0tY3lHB60NNkmXc5s9fDVZLESaAA55NDzOxhy9GkcIdslK1eN7N6jIeHz`. Mã của CSS đã đúng |
| 3 | `apiFetch` trong `api.js` ghép tùy chọn theo thứ tự `{ headers: {...}, ...options }` | Khi truyền `options.headers` (VD: token), header `Content-Type` mặc định bị ghi đè mất | Gộp `headers` sau cùng: `{ ...options, headers: { ...mặcĐịnh, ...options.headers } }` |
| 4 | `api.js` chưa gửi token, chưa xử lý 401 và lỗi 422, thiếu các API: đăng nhập, `/jobs/open`, `ai-analysis`, `/cv`. `apply` không kiểm tra `response.ok` | Gọi API HR sẽ bị 401; lỗi nộp CV không hiện cho ứng viên | Bổ sung theo [Mục 5](#5-quy-ước-code) |

Các lỗi 1 và 2 đã được kiểm tra: lỗi 1 bằng `node --check`, lỗi 2 bằng cách so mã hash của file CDN thật.

> **Cập nhật 16/10/2026:** lỗi 1 và 2 **đã sửa** khi đổi giao diện sang Bootswatch / Tabler.
>
> **Cập nhật 17/10/2026:** lỗi 3 và 4 **đã sửa** (nhánh `feature/frontend-tan`). Cách dùng nhanh:
> - `api.js`: `JobAPI` (`listOpen`, `list`, `get`, `create`, `update`, `close`), `ApplicationAPI` (`list(params)`, `getDetail`, `getAiAnalysis`, `getCvBlob`, `updateStatus`, `apply(formData)`), `AuthAPI.login/logout`, `Auth` (token, email; gán `Auth.onUnauthorized` để hiện màn đăng nhập khi gặp 401). Lỗi ném ra là `ApiError` có `message` hiển thị được ngay (đã ghép lỗi 422) và `status` (`0` = mất kết nối).
> - `utils.js` (nạp trước `api.js`): `escapeHtml`, `formatDate(value, withTime)`, `formatScore`, `scoreClass`, `showToast(message, type)`, `renderState(container, "loading" | "empty" | "error", { message, hint, onRetry })`.

---

## 4. Màn hình cần xây dựng

Mỗi màn hình ghi rõ API dùng và **3 trạng thái bắt buộc**: đang tải (spinner), rỗng (thông báo thân thiện), lỗi (thông báo kèm nút thử lại). Chi tiết dữ liệu xem [API cho Frontend.md](API%20cho%20Frontend.md).

### 4.1. Cổng ứng viên — `index.html`

| Mã | Màn hình / thành phần | Checklist | API | Ghi chú |
| --- | --- | --- | --- | --- |
| P1 | Danh sách việc làm (thẻ: tiêu đề, kỹ năng bắt buộc dạng nhãn, số năm kinh nghiệm, ngày đăng) | 5.1 | `GET /api/jobs/open` | Dùng `/open`, **không** dùng `/api/jobs` (API này trả cả tin đã đóng) |
| P2 | Modal chi tiết JD (mô tả, yêu cầu, kỹ năng bắt buộc / ưu tiên) + nút "Ứng tuyển" | 5.2 | `GET /api/jobs/{id}` | Nếu `status !== "open"` thì ẩn nút và ghi "Tin đã đóng" (API này trả cả tin đã đóng) |
| P3 | Form nộp CV: họ tên, email, số điện thoại, tệp CV | 5.3, 5.4 | — | Kiểm tra ở frontend trước khi gửi (bảng bên dưới) |
| P4 | Gửi hồ sơ | 5.5 | `POST /api/applications/apply` | `FormData`, **không** tự đặt `Content-Type` |
| P5 | Trạng thái nộp: spinner + khóa nút khi đang gửi; thành công; lỗi | 5.6 | — | Lỗi 400/404: hiển thị nguyên văn `detail`. Thành công: "Hồ sơ đã được gửi, bộ phận tuyển dụng sẽ liên hệ với bạn" (**không** hiển thị điểm AI cho ứng viên) |

Kiểm tra form ở frontend (khớp với kiểm tra phía backend):

| Trường | Quy tắc |
| --- | --- |
| Họ tên | Bắt buộc, 2–150 ký tự |
| Email | Bắt buộc, đúng định dạng email, ≤ 255 ký tự |
| Số điện thoại | Không bắt buộc, ≤ 30 ký tự, chỉ chữ số, khoảng trắng, `+`, `-`, `.` |
| Tệp CV | Bắt buộc, đuôi `.pdf` (và `.docx` nếu nhóm chốt giữ, xem Mục 7), **< 5MB** (`file.size < 5 * 1024 * 1024`) |

### 4.2. Bảng điều khiển HR — `admin.html`

| Mã | Màn hình / thành phần | Checklist | API | Ghi chú |
| --- | --- | --- | --- | --- |
| A1 | Đăng nhập (email, mật khẩu) | — | `POST /api/auth/login` | Gửi **form**, không phải JSON. Lưu token và email vào `localStorage`. Có token thì bỏ qua màn hình này |
| A2 | Thanh điều hướng: tên hệ thống, email HR, nút Đăng xuất | 6.1 | — | Không có API "thông tin người dùng": hiển thị email đã lưu lúc đăng nhập. Đăng xuất = xóa token, quay về A1 |
| A3 | Chọn tin tuyển dụng (dropdown, ghi rõ tin đã đóng) + nút "Tạo tin mới" | — | `GET /api/jobs` | Mặc định chọn tin mới nhất đang mở |
| A4 | Form tạo / sửa tin: tiêu đề, mô tả, yêu cầu, **kỹ năng bắt buộc** (ô nhập dạng nhãn), kỹ năng ưu tiên, số năm kinh nghiệm tối thiểu; nút Đóng tin | 6.2 | `POST /api/jobs`, `PUT /api/jobs/{id}`, `PATCH /api/jobs/{id}/close` | Mỗi kỹ năng là một phần tử mảng, viết tên chuẩn ("FastAPI", "MySQL"); AI chấm điểm theo từng phần tử. Đóng tin cần hỏi xác nhận |
| A5 | Bảng Kanban theo tin đã chọn | 6.3 | `GET /api/applications?job_id=X&sort_by=score_desc` | Gọi 1 lần, tự chia thẻ vào cột theo `status`. Trong mỗi cột, thẻ đã xếp sẵn điểm cao → thấp (đáp ứng 7.5) |
| A6 | Kéo thả thẻ giữa các cột | 6.4, 6.6 | `PATCH /api/applications/{id}/status` | Trong `onEnd`: gọi API; lỗi thì **trả thẻ về cột cũ** và báo lỗi |
| A7 | Thẻ ứng viên: họ tên, tiêu đề hiện tại (`ai_extracted_info.current_title`), huy hiệu điểm theo màu, trạng thái AI | 6.5 | (dữ liệu của A5) | Màu: ≥ 80 `badge-high`, 50–79 `badge-medium`, < 50 `badge-low` (đã có trong `style.css`). `ai_status` chưa xong thì hiện spinner thay huy hiệu |
| A8 | Tự cập nhật thẻ đang được AI chấm | — | (gọi lại A5) | Khi còn thẻ `ai_status` là `pending` / `processing`: gọi lại A5 mỗi 5–10 giây; hết thì dừng |
| A9 | Modal hồ sơ chi tiết (bấm vào thẻ) | 6.7, 6.8 | `GET /api/applications/{id}/ai-analysis` | Bố cục đề xuất ở bảng dưới |
| A10 | Xem CV gốc (tab trong A9) | 6.7 | `GET /api/applications/{id}/cv` | Cần token: `fetch` → `blob()` → `URL.createObjectURL()` → `<iframe>` |

Bố cục đề xuất cho modal A9 (dùng Bootstrap Tabs):

| Tab | Nội dung | Trường dữ liệu |
| --- | --- | --- |
| Tổng quan | Điểm tổng (vòng tròn hoặc số lớn) + 2 thanh tiến độ điểm thành phần; tóm tắt AI; liên hệ | `matching_score`, `hard_filter_score`, `semantic_score`, `ai_summary`, `ai_extracted_info.email/phone/location` |
| Kỹ năng | Nhãn xanh: đáp ứng; đỏ: bắt buộc còn thiếu; vàng: ưu tiên còn thiếu; kỹ năng khớp gián tiếp ghi "tương đương: …" | `matched_skills`, `missing_skills`, `scoring_details.missing_preferred_skills`, `scoring_details.skill_matches[]` (`match_type`, `matched_with`) |
| Kinh nghiệm & học vấn | Số năm kinh nghiệm (kèm ⚠️ khi `discrepancy`), danh sách công việc, học vấn, chứng chỉ, ngoại ngữ | `experience_years`, `experience_details`, `work_experience[]`, `education[]`, `certifications`, `languages` |
| Câu hỏi phỏng vấn | 3–5 câu, nhãn loại câu hỏi và kỹ năng; bấm mở rộng xem mục đích và gợi ý câu trả lời tốt | `interview_details.questions[]` (`question`, `category`, `target_skill`, `purpose`, `good_answer_hints`) |
| CV gốc | Nhúng PDF (A10) | — |

Nhãn tiếng Việt gợi ý:
- `category`: `skill_gap` = "Kỹ năng còn thiếu", `skill_verification` = "Kiểm chứng kỹ năng", `experience` = "Kinh nghiệm", `behavioral` = "Tình huống".
- `status`: `applied` = "Mới nộp", `screening` = "Sàng lọc", `interview` = "Phỏng vấn", `offer` = "Đề nghị nhận việc", `rejected` = "Từ chối".

---

## 5. Quy ước code

### 5.1. Tổ chức tệp

```text
frontend/
├── index.html, admin.html
├── css/style.css     # Style dùng chung (đã có huy hiệu điểm, cột Kanban, thẻ ứng viên)
└── js/
    ├── api.js        # MỌI lời gọi API đi qua đây: API_BASE, token, xử lý lỗi
    ├── utils.js      # Hàm dùng chung: escapeHtml, định dạng ngày, màu huy hiệu, toast
    ├── index.js      # Logic Cổng ứng viên
    └── admin.js      # Logic HR (có thể tách thêm kanban.js, modal.js nếu dài)
```

### 5.2. `api.js` cần có

- **`API_BASE` đặt ở một chỗ duy nhất** (đã có).
- **Tự gắn token** `Authorization: Bearer <token>` (lấy từ `localStorage`) cho mọi API HR.
- **401**: xóa token và hiện màn hình đăng nhập A1.
- **Lỗi có `detail`**:
  - `detail` là chuỗi (400/404): ném lỗi kèm câu thông báo đó.
  - `detail` là mảng (422, lỗi kiểm tra dữ liệu của FastAPI): ghép các `msg` lại. Cấu trúc mẫu:

    ```json
    {"detail": [{"type": "missing", "loc": ["body", "title"], "msg": "Field required", "input": {}}]}
    ```

- **Hai trường hợp đặc biệt:**
  - Đăng nhập gửi `URLSearchParams`, nộp CV gửi `FormData`. Với cả hai, **không** đặt `Content-Type` JSON.
  - API xem CV trả về **blob**, không phải JSON.

### 5.3. Bắt buộc khi hiển thị dữ liệu

| Quy tắc | Lý do |
| --- | --- |
| **Không chèn dữ liệu từ API vào `innerHTML` mà chưa escape.** Dùng `textContent`, hoặc qua hàm `escapeHtml()` | Họ tên, nội dung CV, tóm tắt AI đều đến từ người ngoài (ứng viên). Chèn thẳng sẽ bị tấn công XSS |
| **Mọi trường AI có thể `null` hoặc rỗng.** Dùng `?.` và `?? []` (VD `info?.interview_details?.questions ?? []`) | AI có thể chưa chấm xong hoặc bị lỗi (`ai_status`) |
| **Ngày giờ từ API là giờ UTC, không kèm múi giờ** (VD `"2026-10-16T09:45:01"`). Thêm `"Z"` trước khi tạo `Date`, rồi hiển thị bằng `toLocaleString("vi-VN")` | CSDL Aiven chạy giờ UTC. Không xử lý sẽ lệch 7 tiếng |
| Điểm số hiển thị làm tròn: `Math.round(score)` | API trả 2 chữ số thập phân (VD 89.33) |
| Không gắn sự kiện kiểu `onclick="..."` trong HTML; dùng `addEventListener` | Dễ bảo trì, không lẫn logic vào HTML |

---

## 6. Backend chưa có, không cần làm giao diện

| Chức năng | Hiện trạng | Frontend xử lý |
| --- | --- | --- |
| API lấy thông tin người đang đăng nhập (`/me`) | Chưa có | Hiển thị email đã lưu lúc đăng nhập |
| Xóa tin tuyển dụng / xóa hồ sơ | Chưa có | Chỉ có "Đóng tin" |
| Tổng số hồ sơ để phân trang | Chưa có | Tải tối đa `limit=500`, đủ cho demo |
| Gửi email (Mục 7) | Backend đang làm | Kéo thẻ sang *Phỏng vấn* **chưa** gửi thư. Không làm nút gửi email |
| Đọc CV `.docx` | AI chưa đọc được ([Issue 06](Issues/06-cv-docx-khong-duoc-cham.md)) | Hồ sơ `.docx` sẽ có `ai_status = failed` |

Danh sách hồ sơ (A5) trả kèm toàn bộ kết quả AI của từng thẻ, nên dữ liệu khá lớn. Với quy mô demo thì chấp nhận được; **không tự sửa backend** để tối ưu. Nếu thấy chậm, ghi đề xuất vào `docs/Issues/`.

Cần thêm API hoặc trường dữ liệu: ghi đề xuất theo [quy tắc đóng góp](API%20cho%20Frontend.md#5-quy-tắc-đóng-góp-vào-backend). Không tự sửa phần AI và model CSDL.

---

## 7. Quyết định cần chốt trước khi code phần liên quan

| # | Câu hỏi | Ảnh hưởng | Kết quả (17/10/2026) |
| --- | --- | --- | --- |
| 1 | Kanban **4 cột** (checklist) hay **5 trạng thái** (backend: `offer`, `rejected` tách riêng)? | A5, A6 | ✅ **5 cột**, khớp 5 trạng thái backend: Mới nộp, Sàng lọc, Phỏng vấn, Đề nghị nhận việc, Từ chối |
| 2 | Cột *Applied*: AI chuyển hồ sơ sang `screening` ngay khi bắt đầu chấm, nên cột này gần như luôn trống | A5 | ✅ Giữ cột, ghi chú "Hồ sơ mới, AI đang xử lý" |
| 3 | Có nhận CV `.docx` không? | P3, P4 | ⏳ Tạm chỉ nhận **PDF** cho tới khi xử lý xong [Issue 06](Issues/06-cv-docx-khong-duoc-cham.md) |
| 4 | Đăng nhập nằm trong `admin.html` hay tách `login.html`? | A1 | ✅ Trong `admin.html` (ẩn / hiện bằng JS) |
| 5 | Mục *Tin tuyển dụng* trên thanh điều hướng | — | ✅ Thêm trang quản lý tin (checklist 6.9), là màn hình `#tin-tuyen-dung` trong `admin.html` |

---

## 8. Tự kiểm thử trước khi báo xong

Chạy backend ở `AI_PROVIDER=local`, mở DevTools (F12): tab **Console** không có lỗi đỏ, tab **Network** không có request lỗi ngoài dự kiến.

**Cổng ứng viên:**
- [ ] Danh sách chỉ hiện tin đang mở. Tin vừa bị HR đóng biến mất sau khi tải lại trang
- [ ] Nộp CV1 vào Job 1 thành công, có thông báo; nút bị khóa trong lúc gửi
- [ ] Nộp lại cùng email và cùng tin: hiện "Bạn đã nộp hồ sơ ứng tuyển vào vị trí này rồi"
- [ ] Tệp `.txt` và tệp > 5MB bị chặn ngay ở frontend, không gửi request
- [ ] Bỏ trống họ tên hoặc email sai định dạng: báo lỗi ngay trên form

**Bảng HR:**
- [ ] Sai mật khẩu báo lỗi; đúng thì vào bảng; tải lại trang vẫn đăng nhập; Đăng xuất quay về màn hình đăng nhập
- [ ] Tạo tin mới có 3 kỹ năng bắt buộc, sửa tin, đóng tin (có hỏi xác nhận)
- [ ] Sau khi nộp CV1, CV2, CV3: thẻ hiện spinner rồi tự hiện điểm sau 30–40 giây mà **không cần tải lại trang**; đúng màu xanh / đỏ / vàng; xếp điểm cao → thấp
- [ ] Kéo thẻ sang cột khác, tải lại trang thì thẻ vẫn ở cột mới. Tắt backend rồi kéo: thẻ quay về cột cũ và có báo lỗi
- [ ] Modal hiển thị đủ các tab, CV gốc mở được, không vỡ giao diện với hồ sơ `ai_status = failed` (thử bằng một PDF hỏng)
- [ ] Ngày nộp hiển thị đúng giờ Việt Nam
- [ ] Thử nộp CV với họ tên `<b>Test</b><img src=x onerror=alert(1)>`: hiển thị đúng nguyên văn, **không** in đậm, **không** hiện hộp thoại

**Kịch bản demo đề xuất** (giúp ưu tiên đúng màn hình):
1. Ứng viên xem việc → mở JD → nộp CV1.
2. HR đăng nhập → thẻ đang chấm → điểm xanh tự hiện.
3. Mở modal: kỹ năng, câu hỏi phỏng vấn, CV gốc.
4. Nộp thêm CV2 (đỏ) và CV3 (vàng, minh họa so khớp ngữ nghĩa).
5. Kéo thẻ CV1 sang cột Phỏng vấn.

---

## 9. Quy trình làm việc với Git

- Làm trên nhánh `feature/frontend-<tên>` (VD `feature/frontend-portal`, `feature/frontend-kanban`), merge vào `main` qua Pull Request.
- Commit nhỏ, mỗi commit một việc, mô tả theo mục checklist (VD `5.3 form nộp CV`).
- Làm xong mục nào thì đánh dấu `[x]` mục đó trong `checklist.md`.
- Không commit `.env`, tệp CV thật, thư mục `backend/venv/`.
- Gặp lỗi API hoặc dữ liệu lạ: ghi lại `application_id`, request đã gửi và response nhận được, rồi báo người phụ trách backend hoặc tạo issue trong `docs/Issues/`.

---

## 10. Đổi giao diện: những gì không được đổi tên

Giao diện đổi được thoải mái ở `css/style.css` (biến `--sr-*`, màu, font, khoảng cách) và ở phần HTML: `admin.html`, `index.html`, cùng các hàm vẽ trong JS (`cardHtml`, `renderBoard`, `renderJobsPage`, `overviewHtml`… trong `admin.js`; hàm vẽ thẻ tin, modal JD trong `index.js`). Phần gọi API (`api.js`) và logic (kéo thả, lưu trạng thái, xử lý lỗi) không cần sửa.

Chỉ cần **giữ nguyên tên** các móc nối mà JS dùng để tìm phần tử. Đổi tên thì phải sửa đồng thời trong JS.

**`index.html`, các `id`:** `job-list`, `job-count`, `job-search`, `job-modal`, `job-modal-title`, `job-modal-meta`, `job-modal-body`, `job-closed-badge`, `job-apply-btn`, `apply-section`, `apply-form`, `apply-fieldset`, `apply-cv`, `apply-cv-label`, `apply-dropzone`, `apply-submit-btn`, `apply-error`, `apply-error-text`, `apply-success`, `apply-success-email`.

**`admin.html`, các `id`:**
- Khung, đăng nhập: `view-login`, `view-dashboard`, `view-kanban`, `view-jobs`, `admin-nav`, `login-form`, `login-email`, `login-password`, `login-toggle-password`, `login-error`, `login-submit`, `user-avatar`, `logout-btn`.
- Kanban: `job-select`, `job-meta`, `reload-btn`, `edit-job-btn`, `create-job-btn`, `kanban-board`.
- Trang quản lý tin: `jobs-stats`, `jobs-reload-btn`, `jobs-create-btn`, `jobs-filter`, `jobs-search`, `jobs-list`.
- Form tin: `job-modal`, `job-modal-title`, `job-form`, `job-form-error`, `job-fieldset`, `job-title`, `job-required-skills`, `job-preferred-skills`, `job-exp`, `job-description`, `job-requirements`, `job-save-btn`, `job-close-btn`.
- Xác nhận đóng tin: `close-job-modal`, `close-job-name`, `close-job-error`, `close-job-back`, `close-job-confirm`.
- Modal hồ sơ: `detail-modal`, `detail-avatar`, `detail-name`, `detail-sub`, `detail-status`, `detail-move-btn`, `detail-move-menu`, `detail-alert`, các tab `tab-overview` / `tab-skills` / `tab-exp` / `tab-questions` / `tab-cv`, các khung `pane-overview` / `pane-skills` / `pane-exp` / `pane-questions` / `pane-cv`.

**Class và thuộc tính JS dựa vào:**
- Chung (`utils.js`): `#toast-container`, `.state-message`, `.state-hint`, `.state-retry`; class huy hiệu điểm `badge-high` / `badge-medium` / `badge-low` (đổi màu ở `style.css` thì được, đổi tên thì phải sửa `scoreClass`).
- Kanban: `.kanban-list[data-status]` (vùng thả của SortableJS), `.candidate-card[data-id]`, `.kanban-empty`, `.card-menu`, `[data-move]`, `.is-saving`, `.app-stats`.
- Điều hướng: `[data-view-nav]` bọc mỗi mục menu, bên trong có một `.nav-link` (admin.js đặt `aria-current` lên link này, `menu.css` tô màu theo `aria-current`); địa chỉ `#kanban` / `#tin-tuyen-dung`.
- Trang quản lý tin: `[data-job-action]` + `[data-job-id]`, `#jobs-filter [data-filter]`, `[data-count]`.
- Form tin: `.tag-input[data-kind]` (bên trong có một `<input>`), `.tag-chip`, `.job-edit-only`, `.invalid-feedback` đứng ngay sau ô nhập.
- Modal hồ sơ: `.tab-count` trong nút tab, `[data-detail-move]`, `.cv-open`, `.cv-download`.
- Đăng nhập / tài khoản: `.user-email`.

Sau khi đổi giao diện, chạy lại các bước trong [Mục 8](#8-tự-kiểm-thử-trước-khi-báo-xong) để chắc không mất chức năng.
