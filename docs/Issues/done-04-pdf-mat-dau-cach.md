# 04 – Một số PDF bị đọc ra chữ dính liền, mất dấu cách

**Mức độ:** 🟡 Thấp (giảm độ chính xác ở một số CV)
**Trạng thái:** ✅ Đã xử lý (28/10/2026) — đọc lại trang với `x_tolerance=1.5` khi chữ dính liền
**Thành phần:** `backend/app/services/pdf_service.py`
**Hồ sơ bị ảnh hưởng:** Application #9 (`resume (1).pdf`)

## Hiện tượng

Văn bản trích xuất từ `resume (1).pdf` bị dính liền các từ:

```text
PROFESSIONAL SUMMARY SKILLS | ProficientNodeJSbackendsoftwaredeveloper;7.8yearsexperienceindesigning |
andwritingprojectsfromscratch,writingRESTfulAPIs,Workingonservice-based
```

4 CV thật còn lại và 3 CV mẫu đều đọc bình thường.

## Nguyên nhân

`pdfplumber` dựa vào khoảng cách giữa các ký tự để quyết định chèn dấu cách. Ngưỡng mặc định là `x_tolerance=3`. Một số công cụ tạo CV (Canva, các mẫu LaTeX dùng font đặc biệt) đặt từng ký tự với khoảng cách rất hẹp và không chứa ký tự dấu cách thật, nên các từ bị ghép lại với nhau.

## Ảnh hưởng

- **Gemini vẫn hiểu được:** bóc tách đủ 23 kỹ năng và 10.8 năm kinh nghiệm cho CV này.
- **Tầng so khớp kỹ năng "text"** (tìm tên kỹ năng trong văn bản CV, xem Mục 4.7) không hoạt động, vì cần ranh giới từ để tìm kỹ năng.
- **Semantic Score** có thể bị giảm, vì mô hình nhúng tách chuỗi dính liền thành các token vô nghĩa.
- **Khi chạy Ollama cục bộ** (model nhỏ hơn), khả năng hiểu văn bản dính liền nhiều khả năng sẽ kém hơn Gemini.

## Hướng xử lý (đề xuất)

1. Thêm bước phát hiện: nếu tỷ lệ dấu cách trên tổng số ký tự quá thấp (ví dụ dưới 8%), trích xuất lại bằng `page.extract_text(x_tolerance=1)` hoặc dùng `use_text_flow=True`.
2. Dự phòng thêm: dựng lại dòng từ `page.extract_words(x_tolerance=1)`.
3. Bổ sung unit test với một PDF mẫu có khoảng cách ký tự hẹp.

## Kết quả xử lý (28/10/2026) — ✅ Đã xử lý

**Đo trước khi sửa** (tỷ lệ dấu cách trên số chữ cái, trang 1):

| CV | Mặc định | `x_tolerance=1.5` |
| --- | --- | --- |
| `resume (1).pdf` | **0.022** (dính liền) | **0.156** |
| 5 CV thật khác + 3 CV mẫu | 0.133 – 0.279 | không đổi |

**Đã làm** (`pdf_service.py`, hướng 1 trong đề xuất):
- Hàm `_extract_page_text(page)`: đọc trang như cũ. Nếu tỷ lệ dấu cách dưới `MIN_SPACE_RATIO = 0.08`, đọc lại với `x_tolerance=1.5` và chỉ lấy kết quả mới khi tỷ lệ tốt hơn.
- Trang có ít hơn 50 chữ cái không bị đánh giá (tỷ lệ không có ý nghĩa).
- CV bình thường chỉ đọc một lần như trước, không chậm thêm.
- Có log khi đọc lại: `Trang 1: chữ dính liền (tỷ lệ dấu cách 0.022), đọc lại với x_tolerance=1.5 → 0.156.`

**Unit test** (`tests/test_pdf_service.py`, 4 bài mới): PDF tự sinh đặt các từ sát nhau bằng `TJ` (đọc mặc định ra `ProficientNodeJSbackenddeveloper…`) được tách đúng từ; tính tỷ lệ; CV bình thường chỉ đọc 1 lần; đọc lại không tốt hơn thì giữ bản cũ.

**Kết quả thật** (`resume (1).pdf` → Job 1, chế độ `local`):

| Lần chạy | Matching | Hard | Semantic |
| --- | --- | --- | --- |
| 16/10 (trước khi sửa) | 49.92 | 55.0 | 46.54 |
| 28/10 18:11 (sau khi sửa) | **58.78** | 55.0 | **61.3** |

Semantic tăng 15 điểm vì mô hình nhúng đọc được từ thật thay vì chuỗi dính liền. Hard Filter không đổi vì kỹ năng vẫn được AI bóc tách đúng như trước.
