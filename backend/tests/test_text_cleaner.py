"""
tests/test_text_cleaner.py — Unit test cho module text_cleaner (làm sạch chuỗi văn bản CV, JD)
"""

import unittest

from app.services.text_cleaner import (
    clean_cv_text,
    clean_text,
    clean_whitespace_and_newlines,
    fix_hyphenated_linebreaks,
    normalize_bullet_points,
    normalize_separators,
    normalize_unicode,
    remove_control_characters,
)


class TestTextCleaner(unittest.TestCase):
    """Bộ kiểm thử cho service làm sạch văn bản."""

    def test_remove_control_characters(self):
        """Kiểm tra loại bỏ ký tự điều khiển, form feed, null byte, BOM và zero-width space."""
        dirty = "\x0c\ufeffHello\x00 World\u200b!\x08"
        cleaned = remove_control_characters(dirty)
        self.assertEqual(cleaned, "Hello World!")

    def test_normalize_unicode(self):
        """Kiểm tra chuẩn hóa Unicode NFKC và dấu nháy, non-breaking space."""
        # Decomposed 'o' + combining acute accent (\u0301) -> 'ó'
        decomposed = "kho\u0301"
        normalized = normalize_unicode(decomposed)
        self.assertEqual(normalized, "khó")

        # Curly quotes & non-breaking space
        text_with_curly = "“SmartRecruit”\u00a0‘ATS’"
        self.assertEqual(normalize_unicode(text_with_curly), '"SmartRecruit" \'ATS\'')

    def test_normalize_bullet_points(self):
        """Kiểm tra chuẩn hóa các dạng bullet points thành '- '."""
        dirty_bullets = (
            "• Kỹ năng Python\n"
            "● FastAPI & MySQL\n"
            "▪ Docker container\n"
            "✔ Git workflow\n"
            "★ Điểm GPA cao"
        )
        expected = (
            "- Kỹ năng Python\n"
            "- FastAPI & MySQL\n"
            "- Docker container\n"
            "- Git workflow\n"
            "- Điểm GPA cao"
        )
        self.assertEqual(normalize_bullet_points(dirty_bullets), expected)

    def test_fix_hyphenated_linebreaks(self):
        """Kiểm tra nối lại từ bị ngắt dòng do dấu gạch nối cuối dòng."""
        broken = "Thiết kế micro-\nservices và tối ưu hóa hệ thống."
        expected = "Thiết kế microservices và tối ưu hóa hệ thống."
        self.assertEqual(fix_hyphenated_linebreaks(broken), expected)

    def test_normalize_separators(self):
        """Kiểm tra chuẩn hóa đường kẻ phân cách trang trí."""
        text = "THÔNG TIN CÁ NHÂN\n-------------------------\nEmail: test@gmail.com"
        expected = "THÔNG TIN CÁ NHÂN\n---\nEmail: test@gmail.com"
        self.assertEqual(normalize_separators(text), expected)

    def test_clean_whitespace_and_newlines(self):
        """Kiểm tra thu gọn nhiều khoảng trắng và ngắt dòng dư thừa."""
        dirty = "   Dòng 1     với    nhiều   khoảng trắng   \r\n\r\n\r\n\r\n\r\n   Dòng 2   "
        cleaned = clean_whitespace_and_newlines(dirty, max_consecutive_newlines=2)
        expected = "Dòng 1 với nhiều khoảng trắng\n\nDòng 2"
        self.assertEqual(cleaned, expected)

    def test_preserve_technical_terms(self):
        """Kiểm tra bảo toàn các thuật ngữ kỹ thuật đặc thù (C++, C#, .NET, CI/CD, v.v.)."""
        tech_text = "Thành thạo C++, C#, .NET Core, Node.js, CI/CD pipeline, Vue.js, Python 3.10+."
        cleaned = clean_cv_text(tech_text)
        self.assertIn("C++", cleaned)
        self.assertIn("C#", cleaned)
        self.assertIn(".NET Core", cleaned)
        self.assertIn("Node.js", cleaned)
        self.assertIn("CI/CD pipeline", cleaned)
        self.assertIn("Python 3.10+", cleaned)

    def test_clean_cv_text_end_to_end(self):
        """Kiểm tra luồng làm sạch CV hoàn chỉnh với văn bản phức tạp."""
        raw_cv = """\x0c\ufeff
            NGUYỄN VĂN A    
        Email: nguyen.vana@gmail.com | Phone: 0912345678    
        ====================================================


        MỤC TIÊU NGHỀ NGHIỆP:
        • Kỹ sư phần mềm tối ưu hệ thống.
        ● Thành thạo C++, C#, .NET, Node.js, CI/CD.
        ✔ Có kinh nghiệm micro-\nservices.
        ★ Đạt chứng chỉ AWS Solutions Architect.



        KINH NGHIỆM LÀM VIỆC:
          ▪ Công ty Công nghệ XYZ (2022 - 2024):
            - Phát triển RESTful API hiệu năng cao.  \t  
            - Tối ưu hóa truy vấn MySQL giảm 40% latency.
        \x00\x08
        """

        cleaned = clean_cv_text(raw_cv)

        # Không còn ký tự điều khiển rác
        self.assertNotIn("\x0c", cleaned)
        self.assertNotIn("\ufeff", cleaned)
        self.assertNotIn("\x00", cleaned)
        self.assertNotIn("\x08", cleaned)

        # Bullet points đã chuẩn hóa
        self.assertIn("- Kỹ sư phần mềm tối ưu hệ thống.", cleaned)
        self.assertIn("- Thành thạo C++, C#, .NET, Node.js, CI/CD.", cleaned)
        self.assertIn("- Có kinh nghiệm microservices.", cleaned)
        self.assertIn("- Đạt chứng chỉ AWS Solutions Architect.", cleaned)

        # Không còn hơn 2 dấu xuống dòng liên tiếp
        self.assertNotIn("\n\n\n", cleaned)

        # Dòng phân cách chuẩn
        self.assertIn("---", cleaned)

    def test_edge_cases_none_and_empty(self):
        """Kiểm tra xử lý các trường hợp biên: None, chuỗi rỗng, toàn khoảng trắng."""
        self.assertEqual(clean_text(None), "")
        self.assertEqual(clean_text(""), "")
        self.assertEqual(clean_text("   \n\n\t  \x00 "), "")
        self.assertEqual(clean_cv_text(None), "")
        self.assertEqual(clean_cv_text(""), "")
        self.assertEqual(clean_cv_text("   \r\n\t\x0c   "), "")


if __name__ == "__main__":
    unittest.main()

