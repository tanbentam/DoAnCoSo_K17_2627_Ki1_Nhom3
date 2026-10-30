"""
tests/test_email_service.py — Unit test cho service gửi email (Mục 7.1)

SMTP được giả lập (mock smtplib), không gửi thư thật; chế độ file ghi vào thư mục tạm.
"""

import smtplib
import tempfile
import unittest
from email import message_from_bytes
from email.policy import default as default_policy
from pathlib import Path
from unittest import mock

from app.core import config
from app.services import email_service
from app.services.email_service import build_message, is_valid_email, send_email


def _patch_config(**values):
    return mock.patch.multiple(config, **values)


class TestValidEmail(unittest.TestCase):
    def test_valid(self):
        self.assertTrue(is_valid_email("ung.vien+test@gmail.com"))

    def test_invalid(self):
        for value in ["", None, "khong-co-a-cong", "a@b", "a b@c.com", "a@b.com\nBcc: x@y.com", "@gmail.com"]:
            with self.subTest(value=value):
                self.assertFalse(is_valid_email(value))


class TestBuildMessage(unittest.TestCase):
    def test_headers_and_parts(self):
        with _patch_config(SMTP_USER="hr@gmail.com", EMAIL_FROM_NAME="Phòng Nhân sự"):
            msg = build_message("uv@gmail.com", "Tiêu đề có dấu", "Nội dung", "<p>Nội dung</p>")
        self.assertEqual(msg["To"], "uv@gmail.com")
        self.assertEqual(msg["Subject"], "Tiêu đề có dấu")
        self.assertIn("hr@gmail.com", msg["From"])
        self.assertEqual(msg.get_content_type(), "multipart/alternative")
        self.assertEqual([p.get_content_type() for p in msg.iter_parts()], ["text/plain", "text/html"])

    def test_text_only(self):
        msg = build_message("uv@gmail.com", "A", "Nội dung")
        self.assertEqual(msg.get_content_type(), "text/plain")


class TestSendEmail(unittest.TestCase):
    def test_off_mode_does_nothing(self):
        with _patch_config(EMAIL_MODE="off"), mock.patch.object(email_service.smtplib, "SMTP") as smtp:
            self.assertFalse(send_email("uv@gmail.com", "A", "B"))
        smtp.assert_not_called()

    def test_unknown_mode_treated_as_off(self):
        with _patch_config(EMAIL_MODE="abc"):
            self.assertFalse(email_service.is_email_enabled())

    def test_invalid_recipient_skipped(self):
        with _patch_config(EMAIL_MODE="smtp"), mock.patch.object(email_service.smtplib, "SMTP") as smtp:
            self.assertFalse(send_email("sai-dia-chi", "A", "B"))
        smtp.assert_not_called()

    def test_file_mode_writes_eml(self):
        with tempfile.TemporaryDirectory() as tmp:
            with _patch_config(EMAIL_MODE="file", BASE_DIR=Path(tmp), EMAIL_OUTBOX_DIR="outbox"):
                self.assertTrue(send_email("uv@gmail.com", "Thư thử", "Xin chào", "<p>Xin chào</p>"))
            files = list((Path(tmp) / "outbox").glob("*.eml"))
            self.assertEqual(len(files), 1)
            msg = message_from_bytes(files[0].read_bytes(), policy=default_policy)
            self.assertEqual(msg["Subject"], "Thư thử")
            self.assertIn("Xin chào", msg.get_body(("plain",)).get_content())

    def test_smtp_starttls_port_587(self):
        with _patch_config(EMAIL_MODE="smtp", SMTP_HOST="smtp.gmail.com", SMTP_PORT=587,
                           SMTP_USER="hr@gmail.com", SMTP_PASSWORD="abcdabcdabcdabcd"), \
                mock.patch.object(email_service.smtplib, "SMTP") as smtp:
            self.assertTrue(send_email("uv@gmail.com", "A", "B"))
        smtp.assert_called_once()
        server = smtp.return_value.__enter__.return_value
        server.starttls.assert_called_once()
        server.login.assert_called_once_with("hr@gmail.com", "abcdabcdabcdabcd")
        server.send_message.assert_called_once()

    def test_smtp_ssl_port_465(self):
        with _patch_config(EMAIL_MODE="smtp", SMTP_PORT=465, SMTP_USER="hr@gmail.com", SMTP_PASSWORD="x"), \
                mock.patch.object(email_service.smtplib, "SMTP_SSL") as smtp_ssl, \
                mock.patch.object(email_service.smtplib, "SMTP") as smtp:
            self.assertTrue(send_email("uv@gmail.com", "A", "B"))
        smtp_ssl.assert_called_once()
        smtp.assert_not_called()
        smtp_ssl.return_value.__enter__.return_value.starttls.assert_not_called()

    def test_smtp_missing_credentials_returns_false(self):
        with _patch_config(EMAIL_MODE="smtp", SMTP_USER="", SMTP_PASSWORD=""), \
                mock.patch.object(email_service.smtplib, "SMTP") as smtp:
            self.assertFalse(send_email("uv@gmail.com", "A", "B"))
        smtp.assert_not_called()

    def test_smtp_errors_never_raise(self):
        errors = [
            smtplib.SMTPAuthenticationError(535, b"Username and Password not accepted"),
            smtplib.SMTPRecipientsRefused({"uv@gmail.com": (550, b"no")}),
            TimeoutError("timed out"),
            ConnectionRefusedError("refused"),
        ]
        for err in errors:
            with self.subTest(err=type(err).__name__):
                with _patch_config(EMAIL_MODE="smtp", SMTP_PORT=587, SMTP_USER="hr@gmail.com", SMTP_PASSWORD="x"), \
                        mock.patch.object(email_service.smtplib, "SMTP") as smtp:
                    smtp.return_value.__enter__.return_value.login.side_effect = err
                    self.assertFalse(send_email("uv@gmail.com", "A", "B"))


if __name__ == "__main__":
    unittest.main()
