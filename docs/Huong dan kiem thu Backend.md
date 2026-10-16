# Hướng dẫn kiểm thử Backend

Tài liệu này dùng để tự kiểm thử toàn bộ backend SmartRecruit AI trên hệ thống thật (CSDL Aiven, Gemini / Ollama) và lưu lại kết quả kèm mốc thời gian để theo dõi qua các lần test.

Kiểm thử chia 4 cấp:

| Cấp | Nội dung | Thời gian (ước tính) |
| --- | --- | --- |
| 0. Môi trường | `/health`: CSDL mã hóa TLS, mô hình nhúng đã nạp, nhà cung cấp AI sẵn sàng | vài giây |
| 1. Unit test | 184 bài test logic, chạy offline, AI được giả lập | ~20 giây |
| 2. Smoke test API | Xác thực, tin tuyển dụng, nộp hồ sơ, lọc/sắp xếp danh sách, Kanban | ~1 phút |
| 3. End-to-End AI | Nộp CV thật → đọc PDF → AI bóc tách → chấm điểm → câu hỏi phỏng vấn | 30–40 giây mỗi CV |

- Lịch sử và báo cáo các lần test: [Test-Reports/README.md](Test-Reports/README.md)
- Các vấn đề đã phát hiện: [Issues/README.md](Issues/README.md)

---

## 0. Chuẩn bị (làm một lần trên mỗi máy)

Mở terminal tại thư mục `backend/`:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe download_embedding_model.py      # mô hình nhúng ~460MB, tải 1 lần
.\venv\Scripts\python.exe -m pip install fpdf2              # chỉ dùng để tạo CV mẫu
.\venv\Scripts\python.exe scripts\generate_sample_cvs.py    # tạo 3 CV mẫu theo Mục 8.1
```

**Ollama** (cần cho chế độ `local` và `auto`): cài từ https://ollama.com rồi chạy `ollama pull qwen2.5:7b` (~4.7GB).

**Kiểm tra file `.env`** ở thư mục gốc dự án. Mẫu đầy đủ xem `.env.example`.

| Biến | Bắt buộc | Ghi chú |
| --- | --- | --- |
| `DATABASE_URL` | ✅ | Dạng `mysql+pymysql://...`. **Không** thêm `?ssl_disabled=...` (xem [done-03](Issues/done-03-ket-noi-aiven-chua-ssl.md)) |
| `GEMINI_API_KEY` | Chế độ `cloud` / `auto` | Tạo key tại https://aistudio.google.com/apikey |
| `AI_PROVIDER` | | `auto` (mặc định) / `local` / `cloud` |
| `DB_SSL_CA` | Khuyến nghị | CA certificate của Aiven để xác minh máy chủ. Để trống thì vẫn mã hóa nhưng không xác minh |

**Bộ CV dùng để test:**
- **3 CV mẫu** nằm trong `backend/tests/fixtures/sample_cvs/` (tạo bằng lệnh ở trên).
- **5 CV thật** đặt tại `backend/uploads/cv/`, gồm: `Hung-resume.pdf`, `Nguyen_Van_Huy_CV.pdf`, `resume (1).pdf`, `Resume-Nuriana.pdf`, `resume.pdf`. Thư mục này nằm trong `.gitignore` nên không có trên Git; xin tệp từ thành viên khác trong nhóm. Thiếu CV thật thì script tự bỏ qua.

| CV mẫu | Kịch bản | Kỳ vọng với Job 1 (Backend Python/FastAPI) |
| --- | --- | --- |
| `CV1_phu_hop_backend_python.pdf` | Rất phù hợp JD | Matching > 85 |
| `CV2_trai_nganh_ke_toan.pdf` | Trái ngành (kế toán) | Matching < 40 |
| `CV3_dong_nghia_server_side.pdf` | Khác từ ngữ nhưng đồng nghĩa | Ở giữa; Semantic nhận ra liên quan |

---

## 1. Khởi động server (cửa sổ terminal 1)

Chọn chế độ AI cho lần test:

| Chế độ | Khi nào dùng | Lệnh (PowerShell, tại `backend/`) |
| --- | --- | --- |
| `local` | Test lặp lại nhiều lần trong ngày, không tốn lượt Gemini | `$env:AI_PROVIDER='local'; .\venv\Scripts\python.exe -m uvicorn app.main:app` |
| `auto` | Test giống demo: Gemini trước, lỗi hoặc hết lượt thì chuyển Ollama | `$env:AI_PROVIDER='auto'; .\venv\Scripts\python.exe -m uvicorn app.main:app` |
| `cloud` | Chỉ đánh giá Gemini và chuỗi model dự phòng | `$env:AI_PROVIDER='cloud'; .\venv\Scripts\python.exe -m uvicorn app.main:app` |

> **Hạn mức Gemini miễn phí:** khoảng 20 lượt/ngày cho mỗi model. Mỗi CV dùng **2 lượt** (bóc tách CV + sinh câu hỏi phỏng vấn).
> - Test đầy đủ (3 CV mẫu + 7 lượt CV thật + 1 CV của smoke test) ≈ **22 lượt**.
> - Chỉ CV mẫu ≈ **8 lượt**.
>
> Hạn mức được làm mới hằng ngày, nên muốn đánh giá đúng chất lượng Gemini thì chạy `auto` / `cloud` vào **đầu ngày**.

Đợi khoảng 15 giây rồi mở http://127.0.0.1:8000/health. Kết quả tốt trông như sau:

```json
{
  "status": "healthy",
  "database": {"encrypted": true, "tls_version": "TLSv1.3", "cipher": "TLS_AES_256_GCM_SHA384"},
  "embedding_model_loaded": true,
  "ai_provider": {
    "mode": "auto",
    "gemini": {"model_chain": ["gemini-3.8-flash", "gemini-3.7-flash", "..."], "exhausted_models": {}},
    "ollama": {"reachable": true, "model_ready": true, "model": "qwen2.5:7b"}
  }
}
```

Log từng bước của pipeline (`[BackgroundTasks]`, `[GeminiService]`, `[OllamaService]`...) hiện trong cửa sổ terminal này. Giữ cửa sổ mở để theo dõi khi test.

---

## 2. Chạy kiểm thử tự động (cửa sổ terminal 2) — cách khuyến nghị

```powershell
.\venv\Scripts\python.exe scripts\run_backend_tests.py --cleanup-first --note "Lý do test, VD: test sau khi sửa Issue 04"
```

| Tùy chọn | Tác dụng |
| --- | --- |
| `--cleanup-first` | Xóa dữ liệu test cũ trước khi chạy, để báo cáo chỉ chứa dữ liệu của lần này |
| `--only-samples` | E2E chỉ chạy 3 CV mẫu (nhanh, tiết kiệm lượt Gemini) |
| `--note "..."` | Ghi chú đưa vào báo cáo và bảng lịch sử |
| `--skip-unit` / `--skip-smoke` / `--skip-e2e` | Bỏ qua một cấp |
| `--timeout 300` | Số giây chờ tối đa cho mỗi hồ sơ E2E |

**Thứ tự chạy:** Cấp 0 → Cấp 1 → Cấp 3 → Cấp 2. Smoke test chạy sau E2E vì phần Kanban cần một hồ sơ đã được AI chấm xong, để tránh tranh chấp với tác vụ ngầm.

**Kết quả:**
- Màn hình hiện tiến độ từng bước.
- Báo cáo chi tiết được ghi vào `docs/Test-Reports/<ngày>_<giờ>_backend-<chế độ>.md`.
- Bảng lịch sử [Test-Reports/README.md](Test-Reports/README.md) được thêm một dòng.
- Mã thoát `0` nếu tất cả đạt, `1` nếu có kiểm tra không đạt.

Thời gian ước tính:
- Chế độ `local`, đầy đủ 10 hồ sơ: khoảng **7–8 phút**.
- `--only-samples`: khoảng **3 phút**.

Muốn xem nhanh kết quả AI trên màn hình mà không ghi báo cáo:

```powershell
.\venv\Scripts\python.exe scripts\e2e_test_pipeline.py --only-samples
```

---

## 3. Tiêu chí đạt

### Cấp 0 — Môi trường

| Kiểm tra | Đạt khi |
| --- | --- |
| Server | `/health` trả về `status = healthy` |
| CSDL | `database.encrypted = true` |
| Mô hình nhúng | `embedding_model_loaded = true` |
| AI | `local` / `auto`: Ollama `model_ready = true`. `cloud` / `auto`: còn ít nhất một model Gemini chưa hết lượt |

### Cấp 1 — Unit test

Toàn bộ test đạt (`OK`). Các test dùng mô hình nhúng thật sẽ tự bỏ qua nếu chưa tải mô hình.

### Cấp 2 — Smoke test API (35 kiểm tra)

| Nhóm | Nội dung kiểm tra |
| --- | --- |
| Xác thực | Đăng nhập đúng trả JWT; sai mật khẩu, không có token, token giả đều bị chặn (401) |
| Tin tuyển dụng | Tạo (201), thiếu trường (422), không có token (401), xem chi tiết, sửa một phần giữ nguyên các trường khác, 404, danh sách public chỉ có tin đang mở, đóng tin thì tin biến khỏi danh sách public |
| Nộp hồ sơ | PDF hợp lệ (201, trạng thái `applied`); nộp trùng, sai định dạng, quá 5MB, nộp vào tin đã đóng đều bị từ chối (400); tin không tồn tại (404) |
| Danh sách hồ sơ | Lọc theo `job_id`, `min_score`, `status`; sắp xếp `score_desc` (hồ sơ chưa có điểm xếp cuối); tham số sai (422); chi tiết hồ sơ; 404 |
| Kanban | Chuyển trạng thái `interview → offer → rejected → screening`; trạng thái không hợp lệ (422); không có token (401) |
| Tiến trình AI | Hồ sơ vừa nộp có `ai_status`; hồ sơ đã chấm xong có `ai_status = done` |
| Tệp CV | HR xem tệp CV gốc (200, `application/pdf`, inline); không có token (401); hồ sơ không tồn tại (404) |

### Cấp 3 — End-to-End AI (với mỗi hồ sơ)

| Kiểm tra | Đạt khi |
| --- | --- |
| Hoàn tất | Tác vụ ngầm chạy xong trong thời gian chờ |
| Tiến trình AI | `ai_status = done` (không phải `partial` / `failed`) |
| Matching Score | Có điểm; CV1 > 85, CV2 < 40 |
| AI bóc tách CV | Có họ tên ứng viên (`ai_extracted_info.full_name`) |
| Kinh nghiệm | Có `ai_extracted_info.experience_details` (số năm cuối cùng và nguồn) |
| Câu hỏi phỏng vấn | Có 3–5 câu (`interview_questions`) |

Các mục cần **xem bằng mắt** trong báo cáo (script không tự chấm được):
- Câu hỏi phỏng vấn có bám vào kỹ năng còn thiếu và kinh nghiệm thật của ứng viên không.
- Số năm kinh nghiệm có hợp lý với CV không. Khi `discrepancy = lệch`, số năm tự tính khác số CV tự ghi, HR nên kiểm tra lại.
- Hồ sơ có phải dùng model dự phòng không: cột "Bóc tách bởi" có ghi chú "(dự phòng)".

---

## 4. Khi có kiểm tra không đạt

1. Mở báo cáo để xem kiểm tra nào không đạt và lý do. Xem log server ở terminal 1 đúng thời điểm đó.
2. Nếu là lỗi mới:
   - Tạo tệp `docs/Issues/NN-ten-van-de.md` theo mẫu các issue có sẵn (Hiện tượng, Nguyên nhân, Ảnh hưởng, Hướng xử lý).
   - Ghi đường dẫn báo cáo test làm bằng chứng.
   - Thêm một dòng vào [Issues/README.md](Issues/README.md).
3. Sau khi sửa:
   - Chạy lại test với `--note "Kiểm tra lại Issue NN"`.
   - Thêm phần "Kết quả xử lý" vào tệp issue.
   - Đổi tên tệp thành `done-NN-...md` và cập nhật liên kết trong [Issues/README.md](Issues/README.md).

---

## 5. Kiểm thử thủ công trên Swagger UI

Mở http://127.0.0.1:8000/docs.

1. **Nộp CV:** `POST /api/applications/apply` → *Try it out* → nhập:
   - `job_id = 1`
   - họ tên
   - email mới mỗi lần, dạng `test.<tên>@example.com` để lệnh dọn dữ liệu xóa được
   - chọn tệp PDF

   Bấm *Execute* và ghi lại `application_id`.
2. **Đăng nhập HR:** bấm **Authorize**, nhập username `hr@smartrecruit.com`, password `admin123`.
3. **Xem kết quả AI:** chờ log ở terminal 1 hiện dòng `Hoàn tất chấm điểm AI` (30–40 giây), rồi gọi `GET /api/applications/{application_id}/ai-analysis`.

Các trường trong kết quả:

| Trường | Ý nghĩa |
| --- | --- |
| `matching_score`, `hard_filter_score`, `semantic_score` | Điểm tổng (0.4 × Hard + 0.6 × Semantic) và các điểm thành phần |
| `matched_skills`, `missing_skills` | Kỹ năng JD ứng viên đáp ứng / kỹ năng bắt buộc còn thiếu |
| `interview_questions` | 3–5 câu hỏi phỏng vấn |
| `ai_summary` | Tóm tắt ứng viên bằng tiếng Việt |
| `ai_extracted_info` | Thông tin AI bóc tách: họ tên, liên hệ, kỹ năng, kinh nghiệm, học vấn... |
| `ai_extracted_info.experience_details` | Cách xác định số năm kinh nghiệm: `source` = calculated / stated / stated_old_cv / model |
| `ai_extracted_info.scoring_details` | Giải thích điểm: điểm từng tiêu chí, kiểu khớp từng kỹ năng (exact / alias / text / semantic) |
| `ai_extracted_info.interview_details` | Chi tiết từng câu hỏi: kỹ năng nhắm tới, mục đích, gợi ý câu trả lời tốt |
| `ai_extracted_info.ai_meta`, `interview_details.ai_meta` | Model đã dùng, thời gian xử lý, nhật ký các lần thử (thấy được khi chuyển model dự phòng) |

---

## 6. Dọn dữ liệu test

```powershell
.\venv\Scripts\python.exe scripts\e2e_test_pipeline.py --cleanup
```

Lệnh này xóa:
- Ứng viên có email `test.*@example.com`, kèm hồ sơ ứng tuyển và tệp CV đã upload.
- Tin tuyển dụng có tiêu đề bắt đầu bằng `[TEST]`.

Dữ liệu thật (Job 1–3, tài khoản HR) được giữ nguyên.

---

## 7. Lịch kiểm thử khuyến nghị

| Thời điểm | Lệnh |
| --- | --- |
| Trước mỗi lần commit code backend | Unit test: `.\venv\Scripts\python.exe -m unittest discover -s tests -t .` |
| Sau khi sửa phần AI / chấm điểm | `run_backend_tests.py --only-samples` với `AI_PROVIDER=local` |
| Trước buổi họp nhóm hoặc demo | `run_backend_tests.py --cleanup-first` với `AI_PROVIDER=auto`, chạy đầu ngày khi Gemini còn đủ lượt |

Test ngắt mạng (Mục 8.4: `AI_PROVIDER=local` + `HF_HUB_OFFLINE=1`, tắt Wi-Fi) chưa thực hiện, sẽ bổ sung hướng dẫn khi làm Mục 8.
