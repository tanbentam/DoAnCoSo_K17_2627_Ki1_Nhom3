# 02 – Gemini thường xuyên quá tải (503), xử lý mất tới 98 giây

**Mức độ:** 🟠 Trung bình (ảnh hưởng độ ổn định)
**Trạng thái:** ✅ Đã xử lý (16/10/2026)
**Thành phần:** `backend/app/services/gemini_service.py`
**Hồ sơ bị ảnh hưởng:** Application #4 (CV1), #11, #12

## Hiện tượng

`gemini-3.8-flash` nhiều lần trả lỗi `503 UNAVAILABLE – This model is currently experiencing high demand` hoặc `504` (hết thời gian chờ):

- **CV1 (#4):** chỉ thành công ở lần gọi lại thứ 3, cũng là lần cuối cùng. Thêm một lỗi nữa là hồ sơ mất toàn bộ kết quả bóc tách.

  ```text
  11:22:45 WARNING [GeminiService] Lỗi tạm thời 503 từ Gemini, thử lại lần 1/3 sau 1s...
  11:22:47 WARNING [GeminiService] Lỗi tạm thời 503 từ Gemini, thử lại lần 2/3 sau 2s...
  11:22:50 WARNING [GeminiService] Lỗi tạm thời 503 từ Gemini, thử lại lần 3/3 sau 4s...
  ```

- **#11 (`resume.pdf`):** mất 98 giây.
- **#12:** gặp liên tiếp 504 (chờ 60 giây), rồi 503, rồi 429.

Khi Gemini ổn định, mỗi hồ sơ chỉ mất 15–33 giây.

## Nguyên nhân

- `gemini-3.8-flash` là model mới nhất, nhu cầu sử dụng cao, nên gói miễn phí thường bị ưu tiên thấp khi quá tải.
- Cơ chế gọi lại hiện tại chỉ thử lại **cùng một model**. Nếu model đó quá tải kéo dài, cả 4 lần gọi (1 lần đầu + 3 lần thử lại) đều có thể thất bại.
- Thời gian chờ mỗi lần gọi là 60 giây (`GEMINI_TIMEOUT_SECONDS`). Gặp lỗi 504 là mất trọn 60 giây.

## Ảnh hưởng

- Kết quả không ổn định: cùng một CV có thể có hoặc không có thông tin bóc tách, tùy thời điểm nộp.
- HR phải chờ lâu mới thấy điểm trên bảng Kanban.

## Hướng xử lý

Chi tiết tại [plan-4.9.md](../Plans/plan-4.9.md):

1. **Giai đoạn A:** khi gặp 503/504, chuyển sang model dự phòng (`gemini-3.5-flash`, `gemini-3.1-flash-lite`) thay vì gọi lại cùng model nhiều lần.
2. **Giai đoạn C:** ở chế độ `AI_PROVIDER=auto`, khi tất cả model Gemini đều lỗi thì chuyển sang Ollama cục bộ.
3. Cân nhắc giảm `GEMINI_TIMEOUT_SECONDS` xuống khoảng 30 giây, vì một CV bình thường chỉ cần 5–10 giây để bóc tách.

## Kết quả xử lý (16/10/2026) — ✅ Đã xử lý

- Sau `GEMINI_MAX_RETRIES=1` lần gọi lại, lỗi 503/504 chuyển sang model dự phòng. Kiểm thử thật: `gemini-3.7-flash` trả 503, hệ thống chuyển sang `gemini-3.5-flash` thành công.
- Ở chế độ `auto`, khi mọi model Gemini đều lỗi thì chuyển sang Ollama cục bộ.
- Đã giảm `GEMINI_TIMEOUT_SECONDS` từ 60 xuống 30.

Chi tiết tại [Phan 4.9 - 4.10.md](../Phan%204/Phan%204.9%20-%204.10.md).
