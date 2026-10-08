"""
tests/test_pdf_service.py — Unit test cho pdf_service (trích xuất văn bản PDF bằng pdfplumber)
"""

import io
import os
import tempfile
import unittest
from pathlib import Path

from app.core.config import BASE_DIR
from app.services.pdf_service import (
    PDFCorruptedError,
    PDFFileNotFoundError,
    PDFServiceError,
    extract_pages_text,
    extract_text_from_candidate_cv,
    extract_text_from_pdf,
    get_pdf_metadata,
)


def _generate_minimal_pdf(text_content: str = "Nguyen Van A - Senior Backend Developer") -> bytes:
    """Tạo file PDF hợp lệ tối giản chuẩn PDF 1.4 có chứa text_content để test."""
    escaped_text = text_content.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream_content = f"BT /F1 12 Tf 72 712 Td ({escaped_text}) Tj ET".encode("latin1")
    stream_len = len(stream_content)

    pdf_template = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> /MediaBox [0 0 612 792] /Contents 5 0 R >>\nendobj\n"
        b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
        b"5 0 obj\n<< /Length " + str(stream_len).encode("latin1") + b" >>\nstream\n"
        + stream_content + b"\nendstream\nendobj\n"
        b"xref\n0 6\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"0000000227 00000 n \n"
        b"0000000295 00000 n \n"
        b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n"
        + str(390 + stream_len).encode("latin1") + b"\n%%EOF"
    )
    return pdf_template


class TestPDFService(unittest.TestCase):
    """Bộ kiểm thử cho service trích xuất PDF."""

    def setUp(self):
        self.sample_text = "Tran Thi B - Fullstack Python Engineer"
        self.sample_pdf_bytes = _generate_minimal_pdf(self.sample_text)

        # Tạo file PDF tạm thời trên ổ đĩa
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        self.temp_file.write(self.sample_pdf_bytes)
        self.temp_file.close()

    def tearDown(self):
        # Dọn dẹp file tạm
        if os.path.exists(self.temp_file.name):
            os.remove(self.temp_file.name)

    def test_extract_text_from_pdf_bytes(self):
        """Kiểm tra trích xuất text trực tiếp từ chuỗi bytes."""
        text = extract_text_from_pdf(self.sample_pdf_bytes)
        self.assertIn("Tran Thi B", text)
        self.assertIn("Fullstack Python Engineer", text)

    def test_extract_text_from_pdf_stream(self):
        """Kiểm tra trích xuất text từ io.BytesIO stream."""
        stream = io.BytesIO(self.sample_pdf_bytes)
        text = extract_text_from_pdf(stream)
        self.assertIn("Tran Thi B", text)

    def test_extract_text_from_pdf_file_path(self):
        """Kiểm tra trích xuất text từ đường dẫn file trên đĩa."""
        text = extract_text_from_pdf(self.temp_file.name)
        self.assertIn("Tran Thi B", text)

    def test_extract_text_from_pdf_pathlib_path(self):
        """Kiểm tra trích xuất text khi truyền vào pathlib.Path."""
        path_obj = Path(self.temp_file.name)
        text = extract_text_from_pdf(path_obj)
        self.assertIn("Tran Thi B", text)

    def test_extract_pages_text(self):
        """Kiểm tra trích xuất theo từng trang."""
        pages = extract_pages_text(self.temp_file.name)
        self.assertIsInstance(pages, list)
        self.assertEqual(len(pages), 1)
        self.assertIn("Tran Thi B", pages[0])

    def test_get_pdf_metadata(self):
        """Kiểm tra đọc metadata của file PDF."""
        metadata = get_pdf_metadata(self.temp_file.name)
        self.assertIn("total_pages", metadata)
        self.assertEqual(metadata["total_pages"], 1)
        self.assertIn("file_name", metadata)
        self.assertGreater(metadata["file_size_bytes"], 0)

    def test_file_not_found_raises_exception(self):
        """Kiểm tra lỗi khi file không tồn tại."""
        non_existent_path = "uploads/cv/this_file_does_not_exist_12345.pdf"
        with self.assertRaises(PDFFileNotFoundError):
            extract_text_from_pdf(non_existent_path)

    def test_corrupted_file_raises_corrupted_error(self):
        """Kiểm tra lỗi khi file không phải định dạng PDF chuẩn."""
        bad_file = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        bad_file.write(b"This is not a real PDF file content, just corrupt text.")
        bad_file.close()

        try:
            with self.assertRaises(PDFCorruptedError):
                extract_text_from_pdf(bad_file.name)
        finally:
            if os.path.exists(bad_file.name):
                os.remove(bad_file.name)

    def test_extract_text_from_candidate_cv_relative_path(self):
        """Kiểm tra hàm helper candidate CV với đường dẫn tương đối."""
        # Lưu file PDF mẫu vào uploads/cv
        uploads_test_dir = BASE_DIR / "uploads" / "cv"
        uploads_test_dir.mkdir(parents=True, exist_ok=True)
        test_filename = "test_candidate_cv_service.pdf"
        test_file_path = uploads_test_dir / test_filename
        
        with open(test_file_path, "wb") as f:
            f.write(self.sample_pdf_bytes)

        try:
            relative_path = f"uploads/cv/{test_filename}"
            text = extract_text_from_candidate_cv(relative_path)
            self.assertIn("Tran Thi B", text)
        finally:
            if test_file_path.exists():
                test_file_path.unlink()

    def test_non_pdf_file_raises_error_in_candidate_helper(self):
        """Kiểm tra helper candidate CV từ chối các file không có đuôi .pdf."""
        dummy_docx = BASE_DIR / "uploads" / "cv" / "dummy_test.docx"
        dummy_docx.write_text("dummy docx content")
        try:
            with self.assertRaises(PDFServiceError):
                extract_text_from_candidate_cv("uploads/cv/dummy_test.docx")
        finally:
            if dummy_docx.exists():
                dummy_docx.unlink()


if __name__ == "__main__":
    unittest.main()

