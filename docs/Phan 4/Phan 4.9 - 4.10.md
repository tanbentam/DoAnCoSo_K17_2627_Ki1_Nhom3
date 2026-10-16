Các nội dung đã hoàn thành (Mục 4.9, 4.10 và xử lý vấn đề 01, 02 sau lần test thật đầu tiên):

Thực hiện theo kế hoạch docs/Plans/plan-4.9.md. Mục 4.8 (sinh câu hỏi phỏng vấn) làm sau, để dùng luôn cơ chế chuyển đổi nhà cung cấp AI này.

## Giai đoạn A — Gemini chịu lỗi tốt hơn (backend/app/services/gemini_service.py)

Chuỗi model dự phòng: GEMINI_MODEL → GEMINI_FALLBACK_MODELS (gemini-3.7-flash, gemini-3.5-flash, gemini-3.1-flash-lite). Mỗi model có hạn mức miễn phí riêng, nên tổng số lượt gọi mỗi ngày tăng khoảng 4 lần.

Xử lý theo từng loại lỗi:

| Lỗi | Cách xử lý |
| --- | --- |
| 429 hết hạn mức theo ngày (quotaId chứa "PerDay") | Chuyển model ngay, không gọi lại. Ghi nhớ model hết lượt đến thời điểm Google báo (retryDelay) |
| 429 hết hạn mức theo phút | Chờ đúng retryDelay (tối đa 30s) rồi gọi lại cùng model |
| 503 / 504 / 5xx / lỗi mạng | Gọi lại cùng model GEMINI_MAX_RETRIES lần (mặc định 1), sau đó chuyển model |
| 404 model không còn khả dụng | Bỏ qua model đó 24 giờ, chuyển model |
| 400 / 401 / 403 | Dừng ngay, vì đổi model cũng không khắc phục được (sai key, request sai) |

- parse_quota_error đọc QuotaFailure.quotaId và RetryInfo.retryDelay trong phản hồi lỗi của Google để phân biệt 2 loại hạn mức.
- Khi mọi model đều hết lượt, báo GeminiQuotaExhaustedError ngay mà không gọi API.
- Kết quả trả về kèm nhật ký các lần thử, ví dụ: ["gemini-3.8-flash: 429 hết hạn mức theo ngày", "gemini-3.7-flash: OK"].
- Giảm GEMINI_TIMEOUT_SECONDS từ 60 xuống 30.

## Giai đoạn B — Service adapter Ollama (Mục 4.9, backend/app/services/ollama_service.py)

Gọi qwen2.5:7b (Q4_K_M, 4.7GB) trên GPU RTX 4060 Laptop 8GB qua POST /api/chat, dùng thư viện httpx có sẵn, không thêm thư viện mới:

- **format = JSON Schema của Pydantic:** Ollama ràng buộc đầu ra bằng grammar, nên mô hình chỉ có thể sinh JSON đúng cấu trúc. Đây là tính năng tương đương Structured Outputs của Gemini. Đã kiểm tra hoạt động với schema lồng nhau ($defs) của CVExtraction.
- **Schema đưa thêm vào system prompt:** grammar không truyền được description của từng trường, nên schema được đưa vào prompt để mô hình hiểu ý nghĩa trường (khuyến nghị của Ollama).
- **Tham số:**
  - num_ctx=8192: đủ cho CV dài 20.000 ký tự.
  - keep_alive=30m: giữ model trong VRAM giữa các hồ sơ.
  - temperature=0.2.
- **Xử lý lỗi:**
  - JSON sai schema thì gọi lại 1 lần.
  - Ollama chưa bật thì báo OllamaConnectionError, kèm hướng dẫn chạy `ollama serve`.
  - Model chưa tải thì báo OllamaModelNotFoundError, kèm lệnh `ollama pull`.
- **check_ollama_status:** kiểm tra kết nối và model, dùng cho /health.
- **preload_ollama_model:** nạp sẵn model vào GPU khi khởi động server ở chế độ local.

## Giai đoạn C — Chuyển đổi nhà cung cấp AI (Mục 4.10, backend/app/services/ai_provider.py)

AI_PROVIDER có 3 chế độ, mặc định `auto`:

| Chế độ | Hoạt động |
| --- | --- |
| `cloud` | Chỉ dùng Gemini (có chuỗi model dự phòng) |
| `local` | Chỉ dùng Ollama: offline, không giới hạn lượt gọi |
| `auto` | Gemini trước; khi mọi model Gemini đều lỗi, hết lượt hoặc mất mạng thì chuyển sang Ollama |

- **ai_errors.py:** lớp lỗi chung AIProviderError (GeminiServiceError và OllamaServiceError đều kế thừa) và kiểu kết quả StructuredResult (dữ liệu, provider, model, thời gian xử lý, nhật ký các lần thử).
- **cv_extractor.py:** gọi qua ai_provider thay vì gọi thẳng Gemini. Hậu xử lý bổ sung cho các trường lồng nhau: chuỗi rỗng "" chuyển thành null, các cách viết "Present" / "nay" / "hiện tại" chuẩn hóa thành "present". Đây là các lỗi hay gặp ở mô hình cục bộ.
- **ai_tasks.py:** lưu ai_extracted_info.ai_meta = {provider, model, latency_seconds, attempts} để biết kết quả do model nào tạo ra.
- **/health:** hiển thị chế độ đang dùng, chuỗi model Gemini, các model đang hết lượt (kèm thời điểm dùng lại được) và trạng thái Ollama.
- **Cấu hình mới** (config.py, .env.example): GEMINI_FALLBACK_MODELS, OLLAMA_TIMEOUT_SECONDS, OLLAMA_NUM_CTX, OLLAMA_KEEP_ALIVE, OLLAMA_TEMPERATURE. Mặc định của AI_PROVIDER đổi thành auto.

## Giai đoạn D — Kiểm thử

### Unit test

141/141 tests passed. Bổ sung:

- **test_gemini_service.py:**
  - Hạn mức theo ngày: chuyển model ngay, không gọi lại.
  - Hạn mức theo phút: chờ đúng retryDelay.
  - Ghi nhớ model hết lượt, và tự hết hạn khi tới thời điểm làm mới.
  - 503 chuyển model; 404 đánh dấu bỏ qua.
  - Mọi model hết lượt; lỗi hỗn hợp; chỉ định model thì tắt dự phòng.
  - parse_quota_error.
- **test_ollama_service.py:** payload và schema trong prompt, JSON sai thì gọi lại, không kết nối được, chưa có model, quá thời gian chờ, kiểm tra trạng thái.
- **test_ai_provider.py:** 3 chế độ; auto chuyển Ollama khi Gemini lỗi bất kỳ; cả hai cùng lỗi; chế độ không hợp lệ; trạng thái /health.

### Kiểm thử thật chuyển đổi dự phòng

Thời điểm test: gemini-3.8-flash đã hết lượt trong ngày.

| Kịch bản | Kết quả |
| --- | --- |
| cloud, model chính hết lượt ngày | Chuyển ngay sang gemini-3.7-flash (18s); ghi nhớ 3.8-flash hết lượt 17.7 giờ |
| cloud, gọi lần 2 | Bỏ qua 3.8-flash không gọi API; 3.7-flash trả 503, chuyển sang 3.5-flash thành công (21s) |
| auto, mọi model Gemini hết lượt | Chuyển sang Ollama qwen2.5:7b thành công (16.7s) |

### Kiểm thử End-to-End với AI_PROVIDER=local

10 hồ sơ (3 CV mẫu Mục 8.1 + 7 lượt CV thật) chạy qua API thật:
- 10/10 thành công, 0 lỗi.
- Thời gian 21–38 giây mỗi hồ sơ.
- GPU sinh khoảng 45 token/s. Model chỉ nạp 1 lần (6.3s) nhờ keep_alive.

So sánh với lần test dùng Gemini:

| CV | Matching (Gemini) | Matching (qwen2.5:7b) | Ghi chú |
| --- | --- | --- | --- |
| CV1 – Rất phù hợp | 89.33 ✅ | 89.33 ✅ | Giống hệt |
| CV2 – Trái ngành | 10.00 ✅ | 10.00 ✅ | Giống hệt |
| CV3 – Đồng nghĩa | 62.36 | 54.36 | qwen không suy ra MySQL từ "hệ quản trị CSDL mã nguồn mở của Oracle" |
| 5 CV thật → Job 1 | 43.1 – 56.7 | 43.1 – 56.7 | Giống hệt (kỹ năng JD khớp ở tầng exact/text) |
| 2 CV thật → Job 2 | 59.0 / 63.5 (Gemini lỗi 429) | 63.0 / 66.9 | qwen bóc tách được nên có thêm tiêu chí kinh nghiệm |

Nhận xét về chất lượng qwen2.5:7b so với Gemini:
- Họ tên tiếng Việt có dấu, tóm tắt tiếng Việt và ngày tháng từng mục kinh nghiệm đều đúng.
- Danh sách kỹ năng ít hơn, ví dụ CV Hưng có 17 kỹ năng so với 28 của Gemini.
- Suy luận ngữ nghĩa kém hơn (CV3).
- **Tính tổng số năm kinh nghiệm sai:** CV1 thực tế 5.3 năm nhưng trả về 3.0, dù mô hình đã bóc tách đúng các mốc 07/2021 → present. Mô hình nhỏ đọc đúng ngày nhưng cộng trừ ngày tháng kém.

Đề xuất tiếp theo: tính experience_years bằng code từ các mốc work_experience (gộp các khoảng chồng lấn) thay vì để mô hình tự tính. Cách này sửa được điểm yếu của mô hình cục bộ và kết hợp được với vấn đề 05.

## Cập nhật tài liệu & Checklist

- docs/Issues/01, 02 chuyển trạng thái "Đã xử lý" kèm kết quả kiểm thử.
- Đã đánh dấu [x] Mục 4.9 và 4.10 trong checklist.md (4.10 bổ sung chế độ auto).
