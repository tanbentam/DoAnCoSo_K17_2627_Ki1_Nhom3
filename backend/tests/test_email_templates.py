"""
tests/test_email_templates.py — Unit test cho 4 mẫu email và quy tắc gửi theo trạng thái (Mục 7.2 – 7.4)
"""

import unittest
from datetime import datetime, timezone

from app.models.application import ApplicationStatus
from app.services import email_templates as t
from app.services.email_notifications import should_notify_status


class TestFormatDatetime(unittest.TestCase):
    def test_naive_is_utc_converted_to_vietnam(self):
        # 02:30 UTC Thứ Hai 26/10/2026 → 09:30 giờ Việt Nam
        self.assertEqual(t.format_vn_datetime(datetime(2026, 10, 26, 2, 30)), "09:30, Thứ Hai 26/10/2026")

    def test_aware_and_day_rollover(self):
        # 20:00 UTC Chủ Nhật 25/10 → 03:00 Thứ Hai 26/10 giờ Việt Nam
        value = datetime(2026, 10, 25, 20, 0, tzinfo=timezone.utc)
        self.assertEqual(t.format_vn_datetime(value), "03:00, Thứ Hai 26/10/2026")


class TestTemplates(unittest.TestCase):
    NAME = '[TEST] Nguyễn <b>Văn</b> "A"'
    JOB = "Backend <script>alert(1)</script> Developer"

    def all_templates(self):
        return {
            "received": t.application_received(self.NAME, self.JOB),
            "interview": t.interview_invitation(self.NAME, self.JOB, datetime(2026, 10, 26, 2, 30), "Tầng 5 <i>HN</i>"),
            "offer": t.offer_letter(self.NAME, self.JOB),
            "reject": t.rejection_letter(self.NAME, self.JOB),
        }

    def test_html_escapes_user_data(self):
        for key, content in self.all_templates().items():
            with self.subTest(template=key):
                self.assertNotIn("<script>", content.html)
                self.assertNotIn("<b>Văn</b>", content.html)
                self.assertNotIn("<i>HN</i>", content.html)
                self.assertIn("&lt;script&gt;", content.html)

    def test_text_keeps_raw_names(self):
        for key, content in self.all_templates().items():
            with self.subTest(template=key):
                self.assertIn(self.NAME, content.text)
                self.assertIn(self.JOB, content.text)
                self.assertIn(self.JOB, content.subject)
                self.assertNotIn("<p", content.text)

    def test_subjects_differ(self):
        subjects = [c.subject for c in self.all_templates().values()]
        self.assertEqual(len(set(subjects)), 4)

    def test_interview_with_schedule(self):
        c = t.interview_invitation("An", "Dev", datetime(2026, 10, 26, 2, 30), "  Tầng 5, 123 Xuân Thủy  ")
        self.assertIn("09:30, Thứ Hai 26/10/2026 (giờ Việt Nam)", c.text)
        self.assertIn("- Địa điểm: Tầng 5, 123 Xuân Thủy", c.text)
        self.assertIn("xác nhận tham dự", c.text)
        self.assertNotIn("sẽ liên hệ để thống nhất", c.text)

    def test_interview_without_schedule(self):
        c = t.interview_invitation("An", "Dev", None, "   ")
        self.assertIn("- Thời gian: Bộ phận tuyển dụng sẽ liên hệ để thống nhất", c.text)
        self.assertIn("- Địa điểm: Bộ phận tuyển dụng sẽ liên hệ để thống nhất", c.text)
        self.assertIn("thống nhất lịch phỏng vấn", c.text)

    def test_reject_and_offer_wording(self):
        self.assertIn("chưa phù hợp", t.rejection_letter("An", "Dev").text)
        self.assertIn("vượt qua vòng tuyển chọn", t.offer_letter("An", "Dev").text)


class TestShouldNotify(unittest.TestCase):
    S = ApplicationStatus

    def test_email_statuses(self):
        for new in (self.S.interview, self.S.offer, self.S.rejected):
            with self.subTest(new=new):
                self.assertTrue(should_notify_status(self.S.screening, new))

    def test_no_email_for_other_statuses_or_same_column(self):
        self.assertFalse(should_notify_status(self.S.interview, self.S.screening))
        self.assertFalse(should_notify_status(self.S.screening, self.S.applied))
        self.assertFalse(should_notify_status(self.S.interview, self.S.interview))
        self.assertFalse(should_notify_status(self.S.rejected, self.S.rejected))

    def test_offer_to_rejected_sends_again(self):
        self.assertTrue(should_notify_status(self.S.offer, self.S.rejected))


if __name__ == "__main__":
    unittest.main()
