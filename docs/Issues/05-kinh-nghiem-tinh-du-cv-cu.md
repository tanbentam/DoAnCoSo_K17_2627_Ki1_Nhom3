# 05 – CV cũ ghi "hiện tại" bị tính dư số năm kinh nghiệm

**Mức độ:** 🟡 Thấp (sai lệch tiêu chí kinh nghiệm)
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
