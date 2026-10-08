Các công việc đã triển khai chi tiết:

Cấu hình & Cài đặt Thư viện:

Cài đặt thư viện pdfplumber
 cùng các dependency xử lý PDF trên nền tảng Python 3.10.
Cập nhật danh sách phụ thuộc vào file backend/requirements.txt.

Xây dựng Service trích xuất PDF:

Tạo file service backend/app/services/pdf_service.py bao gồm:
extract_text_from_pdf: Nhận đường dẫn file (str / Path), chuỗi bytes hoặc io.BytesIO stream; duyệt qua các trang và trích xuất toàn bộ văn bản thô (có xử lý fallback dữ liệu bảng biểu extract_tables()).
extract_pages_text: Trích xuất danh sách văn bản theo từng trang riêng biệt.
get_pdf_metadata: Đọc metadata, số trang, kích thước file.
extract_text_from_candidate_cv: Helper tự động giải quyết đường dẫn tương đối (ví dụ uploads/cv/...) theo BASE_DIR.
Hệ thống custom exceptions phân loại lỗi: PDFServiceError, PDFFileNotFoundError, PDFCorruptedError, PDFEncryptedError, PDFEmptyError.
Xuất khẩu các hàm trong backend/app/services/__init__.py.

Tích hợp vào Background Task:

Cập nhật backend/app/services/ai_tasks.py: Tự động gọi extract_text_from_candidate_cv ngay sau khi ứng viên nộp CV và cập nhật văn bản thô vào trường Candidate.cv_text_raw trong CSDL, sẵn sàng làm dữ liệu đầu vào cho Gemini và Embedding Engine.

Kiểm thử (Unit Tests):

Viết bộ kiểm thử tại backend/tests/test_pdf_service.py bao gồm 10 ca kiểm thử (file path, bytes, stream, file không tồn tại, file hỏng, metadata, v.v.).
Kết quả: 10/10 tests đã chạy thành công (Ran 10 tests in 0.052s - OK).

Cập nhật Checklist:

Đã đánh dấu [x] cho mục này trong checklist.md.