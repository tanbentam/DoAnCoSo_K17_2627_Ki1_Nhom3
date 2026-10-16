# 01 – Gemini miễn phí chỉ có 20 lượt/ngày, hết lượt vẫn gọi lại vô ích

**Mức độ:** 🔴 Cao (chặn việc test và demo)
**Trạng thái:** ✅ Đã xử lý (16/10/2026)
**Thành phần:** `backend/app/services/gemini_service.py`
**Hồ sơ bị ảnh hưởng:** Application #12, #13

## Hiện tượng

2 hồ sơ cuối của lần test không có thông tin Gemini bóc tách: không có họ tên, danh sách kỹ năng hay số năm kinh nghiệm. Log server:

```text
11:28:42 WARNING [GeminiService] Lỗi tạm thời 429 từ Gemini, thử lại lần 3/3 sau 4s...
11:28:46 ERROR   [GeminiService] Gemini API lỗi 429: 429 RESOURCE_EXHAUSTED.
  Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests,
  limit: 20, model: gemini-3.8-flash
  Please retry in 19h31m10s.
```

## Nguyên nhân

- **Hạn mức thấp:** gói miễn phí của `gemini-3.8-flash` chỉ cho **20 lượt gọi mỗi ngày**. Chỉ riêng các lần thử nhanh khi phát triển Mục 4.3 – 4.4 và lần test này đã dùng hết.
- **Gọi lại vô ích:** `generate_structured()` coi mọi lỗi 429 là lỗi tạm thời và gọi lại 3 lần. Với hạn mức theo ngày (`retry in 19h`), gọi lại sau vài giây chắc chắn vẫn thất bại. Việc này làm mỗi hồ sơ chậm thêm khoảng 7 giây.
- **Không có phương án thay thế:** khi model chính hết lượt, hệ thống không thử model Gemini khác (mỗi model có hạn mức riêng), cũng không chuyển sang AI chạy cục bộ.

## Ảnh hưởng

- Sau khoảng 20 hồ sơ mỗi ngày, mọi CV đều mất thông tin bóc tách.
- Hard Filter chỉ còn dựa vào việc tìm tên kỹ năng trong văn bản CV, và tiêu chí kinh nghiệm bị bỏ ra khỏi công thức.
- Mục 4.8 (sinh câu hỏi phỏng vấn) sẽ gọi Gemini thêm một lần cho mỗi hồ sơ, nên hạn mức sẽ hết nhanh gấp đôi.
- Không thể test lặp lại nhiều lần trong ngày.
- Có rủi ro hết lượt ngay trong buổi demo bảo vệ.

## Điểm tốt đã xác nhận

Khi Gemini lỗi, tác vụ ngầm không dừng: vẫn tính được Semantic Score và Hybrid Score (#12 được 58.96 điểm, #13 được 63.53 điểm).

## Hướng xử lý

Chi tiết tại [plan-4.9.md](../Plans/plan-4.9.md):

1. **Giai đoạn A:**
   - Phân biệt hết lượt theo phút (chờ đúng thời gian Google gợi ý rồi gọi lại) với hết lượt theo ngày (dừng ngay).
   - Thêm danh sách model dự phòng `GEMINI_FALLBACK_MODELS`.
   - Ghi nhớ model đã hết lượt cho tới khi hạn mức được làm mới.
2. **Giai đoạn B, C:** thêm Ollama chạy cục bộ trên GPU (Mục 4.9) và biến `AI_PROVIDER=cloud|local|auto` (Mục 4.10). Khi phát triển dùng `local`, nên không tốn lượt Gemini.

## Kết quả xử lý (16/10/2026) — ✅ Đã xử lý

Đã triển khai theo [plan-4.9.md](../Plans/plan-4.9.md), chi tiết tại [Phan 4.9 - 4.10.md](../Phan%204/Phan%204.9%20-%204.10.md).

Kết quả kiểm thử thật (lúc gemini-3.8-flash đã hết lượt trong ngày):
- Hết hạn mức theo ngày: chuyển ngay sang `gemini-3.7-flash`, không gọi lại vô ích. Model hết lượt được ghi nhớ 17.7 giờ, các hồ sơ sau bỏ qua mà không gọi API.
- `AI_PROVIDER=auto` khi mọi model Gemini đều hết lượt: tự chuyển sang Ollama `qwen2.5:7b` cục bộ (16.7s).
- `AI_PROVIDER=local`: 10/10 hồ sơ chạy offline qua Ollama, không tốn lượt Gemini.

Hạn mức 20 lượt/ngày của từng model vẫn còn, nhưng không còn chặn việc test và demo.
