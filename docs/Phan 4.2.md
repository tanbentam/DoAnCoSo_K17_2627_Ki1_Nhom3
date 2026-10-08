Các nội dung đã hoàn thành:

Xây dựng module làm sạch văn bản backend/app/services/text_cleaner.py:

remove_control_characters: Loại bỏ triệt để các ký tự điều khiển ASCII, null byte (\x00), form feed (\x0c), BOM (\ufeff), ký tự zero-width spaces (\u200b - \u200d) và ký tự hỏng font từ PDF (\ufffd).
normalize_unicode: Chuẩn hóa Unicode NFKC cho tiếng Việt có dấu (đồng bộ ký tự dựng sẵn & tổ hợp), chuẩn hóa non-breaking spaces và chuyển đổi dấu nháy cong thông minh (“, ”, ‘, ’) về ký tự chuẩn.
normalize_bullet_points: Tự động nhận diện các biểu tượng đầu dòng thường gặp trong CV (•, ●, ▪, ✔, ★, v.v.) và chuyển về định dạng markdown danh sách tiêu chuẩn -.
fix_hyphenated_linebreaks: Ghép nối lại các từ bị ngắt dòng do dấu gạch nối cuối dòng trong layout PDF (ví dụ: micro-\nservices 
→
→ microservices).
normalize_separators: Thu gọn các đường kẻ phân cách trang trí lặp lại (ví dụ: -------------------) về dấu ngắt markdown ---.
clean_whitespace_and_newlines: Chuẩn hóa ngắt dòng \r\n về \n, loại bỏ khoảng trắng ngang và tab dư thừa trên mỗi dòng, gom các đoạn ngắt dòng trống liên tiếp (giới hạn tối đa 2 dòng ngắt giữa các đoạn văn), cắt khoảng trắng thừa ở đầu và cuối văn bản.
clean_cv_text: Pipeline tổng hợp chuyên biệt cho CV/JD, đảm bảo bảo toàn nguyên vẹn các thuật ngữ kỹ thuật (C++, C#, .NET Core, CI/CD, Node.js, Python 3.10+).

Tích hợp đồng bộ vào hệ thống:

Service PDF: Cập nhật backend/app/services/pdf_service.py hỗ trợ cờ clean: bool = True để tự động làm sạch text ngay khi bóc tách từ file PDF.
Tác vụ ngầm: Cập nhật backend/app/services/ai_tasks.py để văn bản được làm sạch chuẩn hóa trước khi lưu vào CSDL (Candidate.cv_text_raw), giúp giảm thiểu lượng token và tránh lỗi định dạng khi gửi sang Gemini API hoặc mô hình Embedding.
Package Init: Xuất khẩu toàn bộ hàm làm sạch trong backend/app/services/__init__.py.

Kiểm thử tự động (Unit Tests):

Viết bộ unit test toàn diện tại backend/tests/test_text_cleaner.py (9 bài test kiểm tra Unicode tiếng Việt, control chars, bullet points, hyphenation, bảo toàn skill lập trình, và các trường hợp biên).
Chạy toàn bộ test suite dự án: 19/19 tests passed (0.043s - OK).

Cập nhật Checklist:

Đã đánh dấu [x] hoàn thành mục này trong checklist.md.