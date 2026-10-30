# 06 – API nhận CV `.docx` nhưng AI chỉ đọc được PDF

**Mức độ:** 🟡 Thấp (chưa xảy ra trong test, nhưng chắc chắn sẽ gặp)
**Trạng thái:** ✅ Đã xử lý (28/10/2026) — chọn phương án 3: chỉ nhận PDF ở cả API lẫn form
**Thành phần:** `backend/app/api/applications.py`, `backend/app/services/ai_tasks.py`

## Hiện tượng

- `POST /api/applications/apply` chấp nhận cả `.pdf` và `.docx`. Mục 5 trong checklist cũng yêu cầu form nộp CV nhận cả hai định dạng.
- Tác vụ ngầm `process_application_ai` lại chỉ trích xuất văn bản khi tệp là `.pdf`:

  ```python
  if candidate.cv_file_path.lower().endswith(".pdf"):
      ...
  else:
      logger.info("... không phải PDF (bỏ qua pdfplumber).")
  ```

Phát hiện khi đọc lại mã nguồn trong lúc test. Lần test này chỉ dùng PDF nên chưa gặp trực tiếp.

## Ảnh hưởng

Ứng viên nộp CV `.docx` sẽ:
- Không có `cv_text_raw`, nên Gemini không bóc tách được.
- Không có Semantic Score và Hard Filter, nên `matching_score` để trống (NULL).
- Bị kẹt ở trạng thái `screening` mà HR không biết lý do.

## Hướng xử lý (đề xuất)

1. Thêm `docx_service.py` dùng thư viện `python-docx`: đọc các đoạn văn và bảng, sau đó cho qua `clean_cv_text` giống như PDF.
2. Trong `ai_tasks.py`, chọn service đọc tệp theo phần mở rộng (`.pdf` hoặc `.docx`).
3. Nếu không muốn hỗ trợ `.docx`, cần bỏ `.docx` ở cả API lẫn form nộp CV (Mục 5) cho thống nhất.

## Kết quả xử lý (28/10/2026) — ✅ Đã xử lý

**Quyết định:** chọn hướng 3, không hỗ trợ `.docx`. Lý do: sát hạn bảo vệ (30/10), form nộp CV đã chỉ nhận PDF từ Mục 5.4, và thêm thư viện đọc `.docx` cần test lại cả luồng AI.

**Đã làm:**
- `POST /api/applications/apply` chỉ nhận `.pdf`. Tệp khác (kể cả `.docx`) trả 400 "Định dạng tệp không hợp lệ. Hệ thống chỉ hỗ trợ tệp .pdf".
- API xem CV gốc (`GET /api/applications/{id}/cv`) vẫn trả được `.docx` cho hồ sơ cũ nộp trước ngày sửa.
- Smoke test thêm mục "Tệp .docx → 400".
- Cập nhật tài liệu: `docs/API cho Frontend.md`, `README.md`, chú thích trong `frontend/js/index.js`.

**Kiểm thử:** smoke test API 37/37 đạt (lần chạy [2026-10-28 18:11](../Test-Reports/2026-10-28_1811_backend-local.md)), form ở cổng ứng viên chặn `cv.docx` với câu "Chỉ nhận tệp .pdf".
