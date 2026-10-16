"""
tests/test_database_ssl.py — Unit test cấu hình kết nối SSL/TLS tới Aiven MySQL (docs/Issues/03)
"""

import ssl
import tempfile
import unittest
from pathlib import Path

from app.core.database import build_engine_url, build_ssl_connect_args, resolve_ssl_mode

AIVEN_HOST = "mysql-demo.aivencloud.com"


class TestResolveSSLMode(unittest.TestCase):

    def test_auto_cloud_host_requires_tls(self):
        self.assertEqual(resolve_ssl_mode(AIVEN_HOST, "auto", None), "required")

    def test_auto_with_ca_verifies(self):
        self.assertEqual(resolve_ssl_mode(AIVEN_HOST, "auto", Path("ca.pem")), "verify")

    def test_auto_localhost_disabled(self):
        for host in ("localhost", "127.0.0.1"):
            self.assertEqual(resolve_ssl_mode(host, "auto", None), "disabled")

    def test_explicit_and_invalid_modes(self):
        self.assertEqual(resolve_ssl_mode(AIVEN_HOST, "DISABLED", None), "disabled")
        self.assertEqual(resolve_ssl_mode(AIVEN_HOST, "bogus", None), "required")


class TestBuildConnectArgs(unittest.TestCase):

    def test_required_uses_encrypted_context_without_verification(self):
        args = build_ssl_connect_args(AIVEN_HOST, "required", "")
        ctx = args["ssl"]
        self.assertIsInstance(ctx, ssl.SSLContext)
        self.assertEqual(ctx.verify_mode, ssl.CERT_NONE)
        self.assertFalse(ctx.check_hostname)

    def test_verify_passes_ca_path(self):
        with tempfile.NamedTemporaryFile(suffix=".pem", delete=False) as f:
            ca = f.name
        try:
            self.assertEqual(build_ssl_connect_args(AIVEN_HOST, "auto", ca), {"ssl": {"ca": ca}})
        finally:
            Path(ca).unlink()

    def test_verify_missing_ca_raises(self):
        with self.assertRaises(FileNotFoundError):
            build_ssl_connect_args(AIVEN_HOST, "verify", "certs/khong-ton-tai.pem")

    def test_disabled_returns_no_ssl(self):
        self.assertEqual(build_ssl_connect_args("localhost", "auto", ""), {})


class TestEngineUrl(unittest.TestCase):

    def test_strips_string_ssl_disabled_flag(self):
        """?ssl_disabled=false là chuỗi truthy → PyMySQL tắt SSL; phải loại bỏ khỏi URL."""
        url = build_engine_url(f"mysql+pymysql://u:p@{AIVEN_HOST}:10148/defaultdb?ssl_disabled=false&charset=utf8mb4")
        self.assertNotIn("ssl_disabled", url.query)
        self.assertEqual(url.query["charset"], "utf8mb4")

    def test_url_without_ssl_params_unchanged(self):
        raw = f"mysql+pymysql://u:p@{AIVEN_HOST}:10148/defaultdb"
        self.assertEqual(build_engine_url(raw).render_as_string(hide_password=False), raw)


if __name__ == "__main__":
    unittest.main()
