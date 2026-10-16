# 04 – Một số PDF bị đọc ra chữ dính liền, mất dấu cách

**Mức độ:** 🟡 Thấp (giảm độ chính xác ở một số CV)
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
