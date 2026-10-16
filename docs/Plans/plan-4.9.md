# Kế hoạch: Gemini chịu lỗi + AI cục bộ (Mục 4.9, 4.10)

**Trạng thái:** ✅ Đã hoàn thành ngày 16/10/2026. Kết quả xem tại [Phan 4.9 - 4.10.md](../Phan%204/Phan%204.9%20-%204.10.md).
**Đã chốt:** Ollama + `qwen2.5:7b` do nhóm tự cài; `AI_PROVIDER=auto`.

Kế hoạch kết hợp 2 việc:
- Làm Gemini chịu lỗi tốt hơn, giải quyết vấn đề [01](../Issues/01-gemini-het-han-muc-mien-phi.md) và [02](../Issues/02-gemini-qua-tai-503.md) phát hiện trong lần test thật đầu tiên.
- Làm luôn **Mục 4.9 (Ollama) và Mục 4.10 (`AI_PROVIDER`)**.

**Hiện trạng máy:**
- GPU RTX 4060 Laptop **8GB VRAM**, RAM 15GB. Đủ chạy `qwen2.5:7b` bản rút gọn 4-bit, khoảng 4.7GB, nằm gọn trong VRAM.
- **Chưa cài Ollama.**
- Ổ C còn 78GB, ổ D còn 39GB. Đủ chỗ cho model khoảng 5GB.

---

### Giai đoạn A: Gemini chịu lỗi tốt hơn (vấn đề 01, 02)
1. **Phân biệt 2 loại lỗi 429.** Hết lượt theo phút thì chờ đúng thời gian Google gợi ý rồi gọi lại. Hết lượt **theo ngày** (`limit: 20 ... retry in 19h`) thì dừng ngay, không gọi lại 3 lần vô ích như hiện nay.
2. **Danh sách model dự phòng.** Thêm `GEMINI_FALLBACK_MODELS=gemini-3.5-flash,gemini-3.1-flash-lite`. Khi model chính trả 503, hết lượt hoặc 404 thì chuyển sang model kế tiếp. Mỗi model có hạn mức miễn phí riêng, nên tổng số lượt/ngày tăng lên nhiều lần.
3. **Ghi nhớ model đã hết lượt** trong bộ nhớ server cho tới lúc hạn mức được làm mới, để các hồ sơ sau không phải gọi thử lại vào model đó.

### Giai đoạn B: Ollama chạy trên máy (mục 4.9)
1. **Cài Ollama và tải model:** `winget install Ollama.Ollama` rồi `ollama pull qwen2.5:7b`.
2. **Viết `ollama_service.py` với cùng cách gọi như `generate_structured()` của Gemini**, để phần bóc tách CV không phải sửa gì.
   - Gọi thẳng `POST /api/chat` của Ollama bằng `httpx` (thư viện đã có sẵn). Truyền JSON schema của Pydantic vào tham số `format`, để Ollama buộc model trả JSON đúng cấu trúc, tương tự Structured Outputs của Gemini.
   - Đặt `num_ctx=8192`, vì CV dài khoảng 20 nghìn ký tự, tương đương 6–7 nghìn token. Đặt thêm `keep_alive` để model nằm sẵn trong VRAM, đỡ phải nạp lại mỗi lần.
   - Nếu JSON trả về sai cấu trúc thì gọi lại một lần. Báo lỗi rõ ràng khi Ollama chưa bật hoặc chưa tải model.

### Giai đoạn C: Chuyển đổi nhà cung cấp AI (mục 4.10)
1. **Tạo `ai_provider.py` làm đầu mối chung.** `cv_extractor` (và 4.8 sau này) chỉ gọi đầu mối này, không gọi thẳng Gemini nữa.
2. **`AI_PROVIDER` có 3 chế độ:**
   - `cloud`: chỉ dùng Gemini, có model dự phòng của giai đoạn A.
   - `local`: chỉ dùng Ollama. Dùng khi phát triển, test, và test ngắt mạng ở mục 8.4.
   - `auto`: dùng Gemini trước, Gemini lỗi thì tự chuyển sang Ollama. Phù hợp cho buổi demo.
3. **Lưu nguồn của kết quả.** Ghi `{provider, model, thời gian xử lý}` vào `ai_extracted_info`, để biết kết quả do model nào tạo ra. Điểm này có lợi khi trình bày kiến trúc Hybrid lúc bảo vệ.
4. **Gộp các loại lỗi** về một lớp chung `AIProviderError`. `/health` hiển thị thêm nhà cung cấp đang dùng và Ollama có đang chạy hay không.

### Giai đoạn D: Kiểm thử
- Viết unit test cho Ollama và cho đầu mối chung, dùng phản hồi giả lập.
- **So sánh Gemini với qwen2.5:7b trên 3 CV mẫu và 5 CV thật:** độ chính xác khi bóc tách, đúng dấu tiếng Việt, thời gian chạy, và điểm cuối có còn đạt mục tiêu > 85 / < 40 hay không.
- **Thử ngắt mạng thật** với `AI_PROVIDER=local` và `HF_HUB_OFFLINE=1`. Bước này đánh dấu được luôn mục 8.4.

---

**Cần biết trước khi làm:**
- **qwen2.5:7b sẽ kém Gemini**, nhất là với tiếng Việt và cách tính số năm kinh nghiệm. Phần hậu xử lý và các tầng so khớp kỹ năng đã có sẵn sẽ bù lại được một phần. Kết quả so sánh ở giai đoạn D sẽ cho biết chênh lệch cụ thể.
- **Tốc độ dự kiến khoảng 20–40 giây mỗi CV** trên 4060 Laptop. Đây là ước lượng, sẽ đo thực tế ở giai đoạn D. Mức này chấp nhận được vì phần bóc tách chạy ngầm.
- **Mô hình nhúng vẫn chạy trên CPU**, để không tranh 8GB VRAM với Ollama.
- SSL cho Aiven ([vấn đề 03](../Issues/03-ket-noi-aiven-chua-ssl.md)) là việc riêng, không nằm trong kế hoạch này. Có thể làm xen vào bất kỳ lúc nào, mất khoảng 10 phút.

**Thứ tự đề xuất:** làm A trước, vì nhanh và Gemini dùng tốt hơn ngay. Sau đó làm B và C cùng lúc, rồi đến D.

**Quyết định cần chốt:**
1. **Cài Ollama:** Claude chạy giúp `winget install Ollama.Ollama` và `ollama pull qwen2.5:7b` (khoảng 5GB tải về), hay tự cài?
2. **Chế độ mặc định khi phát triển:** đặt `AI_PROVIDER=local` để không tốn lượt Gemini, rồi chuyển sang `auto` khi demo; hay dùng `auto` ngay từ đầu?