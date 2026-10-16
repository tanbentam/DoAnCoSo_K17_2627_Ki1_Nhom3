Các nội dung đã hoàn thành:

Xây dựng module tích hợp Gemini backend/app/services/gemini_service.py (SDK chính thức google-genai):

get_gemini_client: Khởi tạo genai.Client một lần duy nhất (lazy singleton) từ GEMINI_API_KEY, cấu hình timeout; báo GeminiConfigError nếu thiếu key hoặc chưa cài thư viện. reset_gemini_client dùng khi đổi cấu hình / unit test.
generate_structured(prompt, schema, system_instruction, model, temperature, max_retries): Gọi Gemini ở chế độ Structured Outputs với response_mime_type="application/json" và response_schema là một lớp Pydantic, đảm bảo mô hình luôn trả về JSON đúng cấu trúc. Kết quả trả về là instance Pydantic đã được validate, sẵn sàng lưu vào CSDL.
Cơ chế parse 2 lớp: ưu tiên response.parsed do SDK tự parse; dự phòng validate từ response.text bằng schema.model_validate_json.
Cơ chế retry với exponential backoff (1s, 2s, 4s...) cho lỗi tạm thời 408/429/500/502/503/504 và lỗi mạng/timeout (httpx.TransportError). Lỗi không thể khắc phục (400/401/403 - sai key, request sai) dừng ngay, không retry.
Bộ Exception chuẩn hóa: GeminiServiceError (cơ sở), GeminiConfigError, GeminiAPIError (kèm status_code), GeminiResponseError (phản hồi rỗng / bị chặn bởi bộ lọc an toàn kèm lý do / JSON sai schema).

Cấu hình (backend/app/core/config.py, .env.example):

GEMINI_MODEL mặc định chuyển sang gemini-3.8-flash (gemini-1.5-flash và gemini-2.5-flash không còn khả dụng cho tài khoản mới).
Bổ sung GEMINI_TEMPERATURE=0.2 (kết quả bóc tách ổn định), GEMINI_TIMEOUT_SECONDS=60, GEMINI_MAX_RETRIES=3.
Cập nhật requirements.txt với google-genai==2.31.0 và các thư viện phụ thuộc.

Tích hợp đồng bộ vào hệ thống:

Package Init: Xuất khẩu client, hàm generate_structured và các exception trong backend/app/services/__init__.py.
Tác vụ ngầm: Cập nhật ghi chú hook trong backend/app/services/ai_tasks.py; việc gọi Gemini bóc tách CV thực tế sẽ được nối ở Mục 4.4 (prompt + schema CV).

Kiểm thử tự động (Unit Tests):

Viết bộ unit test backend/tests/test_gemini_service.py (12 bài test, dùng client giả lập, không gọi mạng): parse từ response.parsed, fallback response.text, cấu hình JSON mode + schema, JSON sai schema, phản hồi bị chặn SAFETY, retry 429 thành công, hết retry 503, không retry lỗi 403, retry lỗi mạng, prompt rỗng, thiếu API key, cache client.
Chạy toàn bộ test suite dự án: 31/31 tests passed (OK).

Cập nhật Checklist:

Đã đánh dấu [x] hoàn thành mục này trong checklist.md.
