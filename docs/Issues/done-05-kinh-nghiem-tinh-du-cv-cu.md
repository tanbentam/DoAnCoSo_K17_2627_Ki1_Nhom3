# 05 – CV cũ ghi "hiện tại" bị tính dư số năm kinh nghiệm

**Mức độ:** 🟡 Thấp (sai lệch tiêu chí kinh nghiệm)
**Trạng thái:** ✅ Đã xử lý (16/10/2026)
**Thành phần:** `backend/app/services/cv_extractor.py`
**Hồ sơ bị ảnh hưởng:** Application #8 (`Nguyen_Van_Huy_CV.pdf`), có thể cả các CV thật khác

## Hiện tượng

CV của Nguyễn Văn Huy ghi: *"With 3 years of experience under my belt (since 01/2020)"*, tức là CV được viết khoảng năm 2023. Gemini lại trả về **6.8 năm** kinh nghiệm, vì tính từ 01/2020 đến ngày hiện tại (10/2026).

## Nguyên nhân

Ở Mục 4.4, prompt đưa vào "Ngày hiện tại" để Gemini tính các mốc "present" / "nay" cho đúng với CV vừa viết. Với CV đã cũ, "present" thực ra là thời điểm viết CV chứ không phải hôm nay, nên số năm bị cộng dư.

## Ảnh hưởng

- Tiêu chí kinh nghiệm (25% Hard Filter) có thể cho điểm tối đa sai. Ảnh hưởng thực tế nhỏ, vì phần lớn JD chỉ yêu cầu 1–2 năm và ứng viên thường đã đạt mức này.
- HR nhìn thấy số năm kinh nghiệm không khớp với CV.

## Hướng xử lý (đề xuất)

1. Bổ sung quy tắc vào prompt: nếu CV ghi rõ tổng số năm kinh nghiệm (ví dụ "3 years of experience", "5 năm kinh nghiệm") thì ưu tiên con số đó. Chỉ tự tính từ các mốc thời gian khi CV không ghi.
2. Thêm trường `experience_years_stated` (số năm do CV tự ghi) vào schema `CVExtraction`, để HR đối chiếu với số năm tự tính.
3. Lưu ý: trong thực tế ứng viên thường nộp CV mới cập nhật, nên trường hợp này chủ yếu gặp khi test bằng CV mẫu tải từ Internet.

## Kết quả xử lý (16/10/2026) — ✅ Đã xử lý

Khi chạy Ollama, phát hiện thêm: `qwen2.5:7b` bóc tách đúng các mốc ngày nhưng cộng trừ sai (CV1 thực tế 5.3 năm, mô hình trả 3.0). Vì vậy số năm kinh nghiệm được **tính lại bằng code** thay vì tin mô hình.

**Đã sửa trong `backend/app/services/cv_extractor.py`:**

- **Code tự tính số năm** (`calculate_experience_years`):
  - Đổi các mốc `work_experience` về số tháng, gộp các khoảng chồng lấn, tính cả tháng đầu và tháng cuối.
  - Hỗ trợ nhiều định dạng ngày: `2023-03`, `03/2023`, `Mar 2023`, `2023`.
- **Mốc "present" = ngày lập CV**, lấy từ metadata PDF (`ModDate`, nếu không có thì `CreationDate`) qua hàm `get_pdf_document_date` mới trong `pdf_service.py`. File không có ngày thì dùng ngày hôm nay.
- **Thêm trường `experience_years_stated`** vào schema: số năm do CV tự ghi.
- **Thứ tự ưu tiên khi chọn số năm** (`resolve_experience_years`):
  1. Số tự tính.
  2. Số CV tự ghi: khi CV không có mốc ngày, **hoặc** khi không biết ngày lập CV mà số tự tính vượt số CV ghi ≥ 1.5 năm (`stated_old_cv`, nhiều khả năng là CV cũ).
  3. Số mô hình ước lượng.
- **Loại hoạt động không phải công việc:** prompt yêu cầu bỏ hoạt động sinh viên, câu lạc bộ, tình nguyện khỏi `work_experience`. Code có thêm bộ lọc từ khóa làm lưới an toàn.
- **Lưu giải thích cho HR:** `ai_extracted_info.experience_details` = `{final, source, calculated, stated, model, reference_date, reference_source, discrepancy}`. `discrepancy` = true khi số tự tính lệch ≥ 1.5 năm so với số CV ghi.

**Kiểm thử thật** (`AI_PROVIDER=local`, qwen2.5:7b):

| CV | Trước | Sau | Cách xác định |
| --- | --- | --- | --- |
| CV1 mẫu (07/2021 → nay) | 3.0 (qwen) | **5.3** | Tự tính từ mốc ngày |
| Nguyễn Văn Huy (PDF lập 01/2024, "since 01/2020") | 6.8 | **4.1** | Tự tính, "present" = 01/2024 |
| Lê Viết Hưng (PDF lập 02/2023) | 8.2 | **7.2** | Loại "President of Student Council 2015–2018" |
| Abhinav (Google Docs, không có ngày lập; CV ghi 7.8 năm) | 11.0 | **7.8** | `stated_old_cv` |

Unit test bổ sung: 13 bài trong `test_cv_extractor.py` (`TestExperienceYears`) và 4 bài trong `test_pdf_service.py` (`TestPDFDocumentDate`).
