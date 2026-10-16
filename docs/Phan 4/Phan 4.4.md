Các nội dung đã hoàn thành:

Thiết kế schema kết quả bóc tách CV backend/app/schemas/cv_extraction.py (dùng làm response_schema cho Gemini Structured Outputs):

CVExtraction: full_name, email, phone, location, current_title, summary, skills (kỹ năng chuyên môn), soft_skills (kỹ năng mềm), experience_years (tổng số năm kinh nghiệm), work_experience, education, certifications, languages.
WorkExperience: company, position, start_date, end_date ("present" nếu đang làm), description.
Education: institution, degree, major, graduation_year, gpa.
Mọi trường đều required (Gemini không hỗ trợ giá trị default trong response schema); trường có thể thiếu trong CV khai báo Optional để mô hình trả null thay vì bịa dữ liệu. Mỗi trường có description gửi kèm để mô hình hiểu đúng ý nghĩa.

Xây dựng service bóc tách CV backend/app/services/cv_extractor.py:

CV_EXTRACTION_SYSTEM_INSTRUCTION: Prompt hệ thống đóng vai chuyên gia HR/ATS với 8 quy tắc: chỉ dùng thông tin có trong CV (không suy đoán), viết đúng dấu tiếng Việt họ tên, chuẩn hóa tên kỹ năng (reactjs → ReactJS, nodejs → Node.js, c sharp → C#), tách riêng kỹ năng mềm, cách tính số năm kinh nghiệm (gộp khoảng chồng lấn, không tính thời gian đi học), chuẩn hóa ngày YYYY-MM, tóm tắt 2-3 câu bằng tiếng Việt.
build_cv_extraction_prompt: Bọc văn bản CV trong thẻ <cv> để tách bạch dữ liệu với chỉ dẫn (hạn chế prompt injection từ nội dung CV), đưa ngày hiện tại vào prompt để tính đúng kinh nghiệm "đến nay", cắt CV quá dài (> 20.000 ký tự) để kiểm soát token.
extract_cv_info: Gọi generate_structured (Mục 4.3) với schema CVExtraction và trả về kết quả đã hậu xử lý.
normalize_cv_extraction: Hậu xử lý kết quả: khử trùng lặp kỹ năng/chứng chỉ/ngoại ngữ không phân biệt hoa thường, giới hạn experience_years trong [0, 50] và làm tròn 1 chữ số, email viết thường, số điện thoại chỉ giữ chữ số và dấu + (VD: "(+84) 912-345-678" → "+84912345678"), chuỗi rỗng → null.

Tích hợp đồng bộ vào hệ thống:

Tác vụ ngầm: backend/app/services/ai_tasks.py sau bước trích xuất PDF sẽ gọi extract_cv_info, lưu kết quả JSON vào Application.ai_extracted_info và đoạn tóm tắt vào Application.ai_summary (API chi tiết phân tích AI ở Mục 3 trả về được ngay). Lỗi Gemini được bắt và ghi log, không làm hỏng tác vụ ngầm.
Package Init: Xuất khẩu các hàm cv_extractor trong backend/app/services/__init__.py.
Cập nhật model Gemini mặc định sang gemini-3.8-flash (gemini-2.5-flash không còn khả dụng cho key mới).

Kiểm thử:

Unit test backend/tests/test_cv_extractor.py (12 bài test, mock Gemini): prompt bọc thẻ <cv> + ngày hiện tại, cắt CV dài, khử trùng lặp kỹ năng, giới hạn/làm tròn số năm kinh nghiệm, chuẩn hóa email/số điện thoại, truyền đúng schema + system instruction, CV rỗng, lan truyền lỗi Gemini, schema không có default và được google-genai chấp nhận.
Chạy toàn bộ test suite dự án: 43/43 tests passed (OK).
Kiểm thử thực tế với Gemini API trên CV mẫu (tiếng Việt không dấu, kỹ năng viết thường): khôi phục đúng họ tên "Nguyễn Văn An", chuẩn hóa 14 kỹ năng (C#, Node.js, ReactJS, MySQL...), tách kỹ năng mềm, tính 4.3 năm kinh nghiệm (gồm thực tập), bóc tách đúng học vấn, GPA, chứng chỉ AWS và TOEIC. Cơ chế retry tự xử lý lỗi 503 quá tải của Gemini.

Cập nhật Checklist:

Đã đánh dấu [x] hoàn thành mục này trong checklist.md.
