"""
tests/test_candidate_schema.py — Unit test kiểm tra email ứng viên khi nộp hồ sơ

Email được nhận lúc nộp phải qua được EmailStr của CandidateResponse, nếu không
API danh sách hồ sơ (GET /api/applications) sẽ lỗi 500 với cả tin tuyển dụng.
"""

import unittest
from datetime import datetime

from app.schemas.candidate import CandidateResponse, is_valid_candidate_email


class TestCandidateEmail(unittest.TestCase):
    def test_valid(self):
        for value in ["ung.vien+test@gmail.com", "test.email.abc123@example.com", "a@cong-ty.vn"]:
            with self.subTest(value=value):
                self.assertTrue(is_valid_candidate_email(value))

    def test_invalid(self):
        for value in ["", "khong-co-a-cong", "test.badexample.com", "a@b", "a b@c.com", "@gmail.com",
                      "a@b.com\nBcc: x@y.com"]:
            with self.subTest(value=value):
                self.assertFalse(is_valid_candidate_email(value))

    def test_accepted_email_serializes_in_response(self):
        email = "test.email.abc123@example.com"
        self.assertTrue(is_valid_candidate_email(email))
        now = datetime.now()
        resp = CandidateResponse(id=1, full_name="Thử", email=email, created_at=now, updated_at=now)
        self.assertEqual(resp.email, email)


if __name__ == "__main__":
    unittest.main()
