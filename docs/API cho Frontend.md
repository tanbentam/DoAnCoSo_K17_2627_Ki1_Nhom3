# API Backend cho Frontend

Tài liệu dành cho thành viên làm frontend (Mục 5 – Cổng ứng viên, Mục 6 – Kanban HR). Mọi ví dụ lấy từ dữ liệu trả về thật của server (đã rút gọn).

Màn hình cần xây, quy ước code, việc cần sửa trong khung `frontend/` và cách tự kiểm thử: xem [Huong dan phat trien Frontend.md](Huong%20dan%20phat%20trien%20Frontend.md).

- **Base URL (chạy local):** `http://127.0.0.1:8000`
- **Tài liệu tương tác (thử API trực tiếp):** http://127.0.0.1:8000/docs
- **Cập nhật:** 16/10/2026, kiểm thử tại [Test-Reports/2026-10-16_1505](Test-Reports/2026-10-16_1505_backend-local.md) (smoke test 35/35)

---

## 1. Chạy backend trên máy frontend

1. Nhận file `.env` từ người phụ trách backend qua kênh riêng, đặt ở thư mục gốc dự án. **Không commit `.env`.**
2. Tại `backend/`:

   ```powershell
   .\venv\Scripts\python.exe -m pip install -r requirements.txt
   .\venv\Scripts\python.exe download_embedding_model.py   # 1 lần, ~460MB
   ```

3. Chạy server: `.\venv\Scripts\python.exe -m uvicorn app.main:app --reload`
   - Có Ollama + `qwen2.5:7b`: để `AI_PROVIDER=auto` (mặc định).
   - Không có Ollama: đặt `AI_PROVIDER=cloud` trong `.env`.
4. Mở http://127.0.0.1:8000/health, thấy `"status": "healthy"` là chạy được.

**CORS:** backend cho phép mọi origin. Mở HTML bằng Live Server hay `file://` đều gọi được API.

> **CSDL dùng chung (Aiven):** dữ liệu bạn tạo khi thử, người khác cũng thấy. Khi thử nộp CV, dùng email dạng `test.<tên>@example.com`. Tin tuyển dụng thử nên đặt tiêu đề bắt đầu bằng `[TEST]`. Lệnh `python scripts/e2e_test_pipeline.py --cleanup` sẽ xóa sạch các dữ liệu này.

---

## 2. Xác thực (HR)

### `POST /api/auth/login`

Gửi dạng **form** (`application/x-www-form-urlencoded`), **không phải JSON**. Trường `username` là email.

```js
const body = new URLSearchParams({ username: "hr@smartrecruit.com", password: "admin123" });
const res = await fetch(`${API}/api/auth/login`, { method: "POST", body });
// 200 → { "access_token": "eyJ...", "token_type": "bearer" }
// 401 → { "detail": "Email hoặc mật khẩu không chính xác" }
```

- Lưu token (VD: `localStorage`), gửi kèm mọi API HR bằng header: `Authorization: Bearer <token>`.
- Token hết hạn sau **7 ngày**.
- Mọi API HR trả **401** khi thiếu, sai hoặc hết hạn token. Khi đó chuyển về màn hình đăng nhập.

---

## 3. Cổng ứng viên (Mục 5) — không cần token

| Method | Endpoint | Mô tả |
| --- | --- | --- |
| GET | `/api/jobs/open` | Danh sách tin **đang mở**, mới nhất trước |
| GET | `/api/jobs/{id}` | Chi tiết một tin (JD). Trả cả tin đã đóng, nên kiểm tra `status === "open"` trước khi hiện nút nộp hồ sơ |
| POST | `/api/applications/apply` | Nộp hồ sơ |

**Một tin tuyển dụng (`Job`):**

```json
{
  "id": 1,
  "title": "Backend Developer (Python/FastAPI)",
  "description": "Chúng tôi cần tìm ứng viên cho vị trí Backend Developer ...",
  "requirements": "Thành thạo Python và FastAPI. Có kinh nghiệm làm việc với SQLAlchemy và MySQL. ...",
  "required_skills": ["Python", "FastAPI", "SQLAlchemy", "MySQL"],
  "preferred_skills": ["Docker", "Redis", "Linux"],
  "experience_years_min": 2,
  "status": "open",
  "created_by": 1,
  "created_at": "2026-10-07T14:00:13",
  "updated_at": "2026-10-07T14:00:13"
}
```

`preferred_skills` có thể là `null`.

**Ngày giờ** (`created_at`, `updated_at`) là **giờ UTC, không kèm múi giờ**, vì CSDL Aiven chạy UTC. Hiển thị: `new Date(value + "Z").toLocaleString("vi-VN")`.

### `POST /api/applications/apply` — `multipart/form-data`

| Trường | Bắt buộc | Ghi chú |
| --- | --- | --- |
| `job_id` | ✅ | ID tin đang mở |
| `full_name` | ✅ | ≤ 150 ký tự |
| `email` | ✅ | ≤ 255 ký tự. Mỗi email chỉ nộp 1 lần cho mỗi tin |
| `phone` | | ≤ 30 ký tự |
| `cv_file` | ✅ | `.pdf` (khuyến nghị) hoặc `.docx`, **tối đa 5MB** |

```js
const form = new FormData();
form.append("job_id", jobId);
form.append("full_name", name);
form.append("email", email);
form.append("phone", phone);
form.append("cv_file", fileInput.files[0]);
const res = await fetch(`${API}/api/applications/apply`, { method: "POST", body: form });
// KHÔNG tự đặt header Content-Type, trình duyệt sẽ tự thêm boundary
```

| Mã | Khi nào | `detail` (hiển thị nguyên văn cho ứng viên) |
| --- | --- | --- |
| 201 | Thành công | `{"message": "Nộp hồ sơ ứng tuyển thành công!", "application_id": 51, "candidate_id": 47, "job_id": 1, "status": "applied", "ai_status": "pending"}` |
| 400 | Tin đã đóng | "Tin tuyển dụng này đã đóng, không tiếp nhận thêm hồ sơ" |
| 400 | Sai định dạng | "Định dạng tệp không hợp lệ. Hệ thống chỉ hỗ trợ tệp .pdf hoặc .docx" |
| 400 | Quá dung lượng | "Dung lượng tệp vượt quá giới hạn cho phép (5MB)" |
| 400 | Nộp trùng | "Bạn đã nộp hồ sơ ứng tuyển vào vị trí này rồi" |
| 404 | Tin không tồn tại | "Tin tuyển dụng không tồn tại" |
| 422 | Thiếu trường / sai kiểu | `detail` là **mảng** lỗi của FastAPI. Nên kiểm tra form ở frontend trước khi gửi |

> ⚠️ **CV `.docx`** được nhận nhưng AI **chưa đọc được**: hồ sơ sẽ có `ai_status = "failed"` ([Issue 06](Issues/06-cv-docx-khong-duoc-cham.md)). Nhóm cần chốt: giữ `.docx`, hoặc form chỉ nhận PDF.

Nộp xong, ứng viên **không cần chờ AI**. AI chấm ngầm 30–40 giây sau đó.

---

## 4. Bảng điều khiển HR (Mục 6) — cần token (trừ các API ghi chú "không cần token")

### Tin tuyển dụng

| Method | Endpoint | Body / Ghi chú |
| --- | --- | --- |
| GET | `/api/jobs?status=open\|closed` | Mọi tin (gồm cả tin đã đóng), có thể lọc theo trạng thái. **Không cần token.** Cổng ứng viên dùng `/api/jobs/open` |
| POST | `/api/jobs` | JSON: `title`, `description`, `requirements` (bắt buộc); `required_skills` (mảng), `preferred_skills`, `experience_years_min` → **201** |
| PUT | `/api/jobs/{id}` | Chỉ gửi các trường cần đổi, trường không gửi được giữ nguyên |
| PATCH | `/api/jobs/{id}/close` | Đóng tin: tin biến khỏi `/api/jobs/open`, không nhận hồ sơ mới |

**Gợi ý form tạo tin:** `required_skills` nên là ô nhập dạng tag (mỗi kỹ năng một phần tử, viết tên chuẩn như "FastAPI", "MySQL"). Hệ thống chấm điểm so khớp theo từng phần tử này.

### Danh sách hồ sơ cho Kanban — `GET /api/applications`

| Tham số | Ví dụ | Ý nghĩa |
| --- | --- | --- |
| `job_id` | `1` | Hồ sơ của một tin |
| `status` | `interview` | Lọc theo cột Kanban |
| `min_score`, `max_score` | `50` | Lọc theo Matching Score (0–100, ngoài khoảng trả 422) |
| `sort_by` | `score_desc` | `newest` (mặc định), `oldest`, `score_desc`, `score_asc`. Hồ sơ chưa có điểm luôn xếp cuối |
| `skip`, `limit` | `0`, `100` | Phân trang (`limit` tối đa 500) |

Mỗi phần tử có `id`, `job_id`, `status`, `ai_status`, `ai_error`, `matching_score`, `semantic_score`, `hard_filter_score`, `matched_skills`, `missing_skills`, `interview_questions`, `ai_summary`, `ai_extracted_info`, `created_at`, `updated_at`, kèm `candidate` (`id`, `full_name`, `email`, `phone`) và `job` (đầy đủ như mục 3).

Gợi ý: gọi 1 lần `GET /api/applications?job_id=X&sort_by=score_desc` rồi tự chia thẻ vào các cột theo `status` ở frontend. Chức năng này đáp ứng Mục 7.5 "lọc theo điểm số từ cao xuống thấp".

### Kéo thả Kanban — `PATCH /api/applications/{id}/status`

```js
await fetch(`${API}/api/applications/${id}/status`, {
  method: "PATCH",
  headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
  body: JSON.stringify({ status: "interview" }),
});
// 200 → hồ sơ đầy đủ (giống phần tử của danh sách); 422 → status không hợp lệ; 404 → không có hồ sơ
```

Trong `onEnd` của SortableJS: gọi API; nếu lỗi thì **trả thẻ về cột cũ** và báo lỗi.

**Các trạng thái Kanban (`status`):** `applied`, `screening`, `interview`, `offer`, `rejected`.

> ⚠️ **Cần chốt với nhóm:** checklist ghi 4 cột (*Applied, Screening, Interview, Offer/Reject*), backend có 5 trạng thái. Đề xuất: cột cuối hiển thị cả `offer` và `rejected` (phân biệt bằng màu nhãn), khi thả vào cột này thì hỏi HR chọn "Offer" hay "Từ chối".
>
> AI tự chuyển hồ sơ từ `applied` sang `screening` ngay khi bắt đầu chấm, nên cột *Applied* thường chỉ có hồ sơ vài giây đầu. Nếu HR đã kéo thẻ đi chỗ khác, AI không ghi đè trạng thái.

### Tiến trình AI — trường `ai_status`

| `ai_status` | Ý nghĩa | Gợi ý hiển thị trên thẻ |
| --- | --- | --- |
| `pending` | Vừa nộp, AI chưa bắt đầu | Spinner "Chờ AI chấm" |
| `processing` | AI đang chấm (30–40s) | Spinner "AI đang chấm..." |
| `done` | Hoàn tất mọi bước | Huy hiệu điểm (≥ 80 xanh, 50–79 vàng, < 50 đỏ) |
| `partial` | Có điểm nhưng thiếu một số kết quả (VD: chưa có câu hỏi phỏng vấn) | Huy hiệu điểm + biểu tượng ⚠️, tooltip = `ai_error` |
| `failed` | Không chấm được (CV hỏng, `.docx`, lỗi hệ thống) | Nhãn "Không chấm được", tooltip = `ai_error` |

Khi trên bảng còn thẻ `pending` / `processing`, gọi lại danh sách mỗi **5–10 giây**. Khi mọi thẻ đã `done` / `partial` / `failed` thì dừng gọi.

### Chi tiết AI cho Modal — `GET /api/applications/{id}/ai-analysis`

Ví dụ thật (CV1 mẫu, đã rút gọn):

```json
{
  "application_id": 51, "job_id": 1, "candidate_id": 47,
  "candidate_name": "Nguyễn Minh Khoa", "job_title": "Backend Developer (Python/FastAPI)",
  "status": "screening", "ai_status": "done", "ai_error": null,
  "matching_score": 89.33, "hard_filter_score": 100.0, "semantic_score": 82.21,
  "matched_skills": ["Python", "FastAPI", "SQLAlchemy", "MySQL", "Docker", "Redis", "Linux"],
  "missing_skills": [],
  "interview_questions": ["Hãy mô tả quá trình bạn đã cài đặt và cấu hình môi trường ...", "..."],
  "ai_summary": "Nguyễn Minh Khoa là Backend Developer ...",
  "ai_extracted_info": {
    "full_name": "Nguyễn Minh Khoa", "email": "...", "phone": "...", "location": "Hà Nội",
    "current_title": "Backend Developer - Python", "summary": "...",
    "skills": ["Python", "FastAPI", "..."], "soft_skills": [], "certifications": ["TOEIC 820", "..."], "languages": [],
    "experience_years": 5.3, "experience_years_stated": 3.0,
    "work_experience": [{"company": "...", "position": "...", "start_date": "2023-03", "end_date": "present", "description": "..."}],
    "education": [{"institution": "...", "degree": "Kỹ sư", "major": "...", "graduation_year": 2021, "gpa": "3.4/4"}],
    "experience_details": {"final": 5.3, "source": "calculated", "stated": 3.0, "calculated": 5.3, "discrepancy": true, "...": "..."},
    "scoring_details": {
      "formula": "0.4 × hard_filter + 0.6 × semantic",
      "required_skills_score": 100.0, "experience_score": 100.0, "preferred_skills_score": 100.0,
      "candidate_experience_years": 5.3, "required_experience_years": 2,
      "missing_preferred_skills": [],
      "skill_matches": [{"skill": "Python", "matched": true, "match_type": "exact", "matched_with": "Python", "similarity": null}]
    },
    "interview_details": {
      "questions": [{
        "question": "...", "category": "skill_gap", "target_skill": "FastAPI",
        "purpose": "Kiểm tra kỹ năng triển khai ...",
        "good_answer_hints": "Nêu được quá trình cài đặt FastAPI, cấu hình ..."
      }],
      "ai_meta": {"provider": "ollama", "model": "qwen2.5:7b", "latency_seconds": 15.8, "attempts": ["qwen2.5:7b: OK"]}
    },
    "ai_meta": {"provider": "ollama", "model": "qwen2.5:7b", "latency_seconds": 22.88, "attempts": ["qwen2.5:7b: OK"]}
  }
}
```

**Gợi ý hiển thị trong Modal (Mục 6.7, 6.8):**

| Khu vực | Dữ liệu |
| --- | --- |
| Tổng quan | `matching_score` + 2 thanh thành phần `hard_filter_score`, `semantic_score`; `ai_summary` |
| Kỹ năng | `matched_skills` (xanh), `missing_skills` (đỏ), `scoring_details.missing_preferred_skills` (vàng). Kỹ năng có `match_type` = `semantic` / `alias` nên ghi chú "tương đương: `matched_with`" |
| Kinh nghiệm | `experience_years` năm. Khi `experience_details.discrepancy = true`: ⚠️ "CV ghi `stated` năm, mốc thời gian cho `calculated` năm — cần xác minh" |
| Câu hỏi phỏng vấn | `interview_details.questions[]`: nội dung, nhãn `category`, `target_skill`; phần mở rộng hiển thị `purpose` và `good_answer_hints` |
| Hồ sơ | `work_experience`, `education`, `certifications`, liên hệ |
| (Tùy chọn) Nguồn AI | `ai_meta.provider/model`, hữu ích khi demo kiến trúc Hybrid AI |

**Mọi trường AI đều có thể `null` hoặc rỗng** (khi `ai_status` khác `done`). Giao diện phải xử lý được mà không vỡ, VD dùng `info?.interview_details?.questions ?? []`.

### Xem tệp CV gốc — `GET /api/applications/{id}/cv`

Trả về PDF (`Content-Disposition: inline`). API cần token nên **không dùng trực tiếp** trong `<a href>` / `<iframe src>`. Làm như sau:

```js
const res = await fetch(`${API}/api/applications/${id}/cv`, { headers: { Authorization: `Bearer ${token}` } });
if (!res.ok) { /* 404: hồ sơ hoặc tệp không tồn tại */ }
const url = URL.createObjectURL(await res.blob());
iframe.src = url;            // nhúng vào modal, hoặc window.open(url)
// Đóng modal: URL.revokeObjectURL(url)
```

### Khác

| Method | Endpoint | Mô tả |
| --- | --- | --- |
| GET | `/api/applications/{id}` | Hồ sơ đầy đủ kèm `candidate` và `job` |
| GET | `/health` | Trạng thái server, CSDL, AI (không cần token) |

---

## 5. Quy tắc đóng góp vào backend

Backend đã được kiểm thử toàn bộ (lịch sử test: [Test-Reports](Test-Reports/README.md)). Để không làm hỏng các phần đã tinh chỉnh bằng số liệu đo thực tế, áp dụng các quy tắc sau:

| Loại thay đổi | Quy tắc |
| --- | --- |
| AI, chấm điểm, prompt (`backend/app/services/`), model CSDL (`backend/app/models/`) | ❌ Không tự sửa. Ghi đề xuất thành issue trong `docs/Issues/` để người phụ trách backend làm |
| Cần thêm hoặc đổi API (thêm trường, endpoint mới) | Đề xuất trước. Nếu tự làm: nhánh `feature/<tên>`, mở Pull Request, người phụ trách backend review |
| Sửa lỗi nhỏ, rõ ràng (câu thông báo lỗi, CORS) | Được phép, vẫn qua Pull Request |
| `.env`, khóa API, tệp CV thật trong `uploads/` | ❌ Không commit |

**Trước khi merge mọi thay đổi backend:** chạy và đính kèm báo cáo đạt hết.

```powershell
.\venv\Scripts\python.exe scripts\run_backend_tests.py --only-samples --note "PR: <mô tả>"
```

Hướng dẫn chi tiết: [Huong dan kiem thu Backend.md](Huong%20dan%20kiem%20thu%20Backend.md).

Gặp lỗi API hoặc dữ liệu lạ: ghi lại `application_id`, request đã gửi và response nhận được, gửi người phụ trách backend hoặc tạo issue.
