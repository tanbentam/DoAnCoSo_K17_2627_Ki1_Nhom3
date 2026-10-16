"""
tests/test_gemini_service.py — Unit test cho module gemini_service (Structured Outputs)

Toàn bộ test dùng client giả lập (mock), không gọi mạng thật tới Google Gemini API.
"""

import unittest
from types import SimpleNamespace
from typing import List
from unittest import mock

import httpx
from google.genai import errors
from pydantic import BaseModel

from app.services import gemini_service
from app.services.gemini_service import (
    GeminiAPIError,
    GeminiConfigError,
    GeminiResponseError,
    generate_structured,
)


class SampleSchema(BaseModel):
    full_name: str
    skills: List[str]


def _make_response(parsed=None, text=None, block_reason=None):
    return SimpleNamespace(
        parsed=parsed,
        text=text,
        prompt_feedback=SimpleNamespace(block_reason=block_reason) if block_reason else None,
        candidates=[],
    )


class TestGeminiService(unittest.TestCase):
    """Bộ kiểm thử cho service gọi Gemini Structured Outputs."""

    def setUp(self):
        self.client = mock.MagicMock()
        patcher = mock.patch.object(gemini_service, "get_gemini_client", return_value=self.client)
        patcher.start()
        self.addCleanup(patcher.stop)
        sleep_patcher = mock.patch.object(gemini_service.time, "sleep")
        self.mock_sleep = sleep_patcher.start()
        self.addCleanup(sleep_patcher.stop)

    def test_returns_parsed_object(self):
        """SDK đã parse sẵn → trả về đúng instance schema."""
        expected = SampleSchema(full_name="Nguyễn Văn A", skills=["Python", "FastAPI"])
        self.client.models.generate_content.return_value = _make_response(parsed=expected)

        result = generate_structured("Bóc tách CV", SampleSchema)

        self.assertEqual(result, expected)

    def test_config_uses_json_mode_and_schema(self):
        """Request phải bật response_mime_type=application/json và response_schema."""
        self.client.models.generate_content.return_value = _make_response(
            parsed=SampleSchema(full_name="A", skills=[])
        )

        generate_structured("prompt", SampleSchema, system_instruction="Bạn là HR", model="gemini-test")

        kwargs = self.client.models.generate_content.call_args.kwargs
        self.assertEqual(kwargs["model"], "gemini-test")
        self.assertEqual(kwargs["config"].response_mime_type, "application/json")
        self.assertIs(kwargs["config"].response_schema, SampleSchema)
        self.assertEqual(kwargs["config"].system_instruction, "Bạn là HR")

    def test_fallback_to_text_json(self):
        """Không có parsed → validate từ response.text."""
        self.client.models.generate_content.return_value = _make_response(
            text='{"full_name": "Trần B", "skills": ["Java"]}'
        )

        result = generate_structured("prompt", SampleSchema)

        self.assertEqual(result.full_name, "Trần B")
        self.assertEqual(result.skills, ["Java"])

    def test_invalid_json_raises_response_error(self):
        """JSON không khớp schema → GeminiResponseError."""
        self.client.models.generate_content.return_value = _make_response(text='{"full_name": 1}')

        with self.assertRaises(GeminiResponseError):
            generate_structured("prompt", SampleSchema)

    def test_empty_response_reports_block_reason(self):
        """Phản hồi rỗng do bị chặn → GeminiResponseError kèm lý do."""
        self.client.models.generate_content.return_value = _make_response(text="", block_reason="SAFETY")

        with self.assertRaises(GeminiResponseError) as ctx:
            generate_structured("prompt", SampleSchema)
        self.assertIn("SAFETY", str(ctx.exception))

    def test_retry_on_rate_limit_then_success(self):
        """Lỗi 429 tạm thời → retry rồi thành công."""
        expected = SampleSchema(full_name="A", skills=[])
        self.client.models.generate_content.side_effect = [
            errors.ClientError(429, {"error": {"message": "quota"}}),
            _make_response(parsed=expected),
        ]

        result = generate_structured("prompt", SampleSchema, max_retries=2)

        self.assertEqual(result, expected)
        self.assertEqual(self.client.models.generate_content.call_count, 2)
        self.mock_sleep.assert_called_once_with(1)

    def test_retry_exhausted_raises_api_error(self):
        """Lỗi 503 liên tục → hết retry thì ném GeminiAPIError kèm status_code."""
        self.client.models.generate_content.side_effect = errors.ServerError(
            503, {"error": {"message": "overloaded"}}
        )

        with self.assertRaises(GeminiAPIError) as ctx:
            generate_structured("prompt", SampleSchema, max_retries=2)
        self.assertEqual(ctx.exception.status_code, 503)
        self.assertEqual(self.client.models.generate_content.call_count, 3)

    def test_non_retryable_error_fails_fast(self):
        """Lỗi 400/403 (sai key, request sai) → không retry."""
        self.client.models.generate_content.side_effect = errors.ClientError(
            403, {"error": {"message": "invalid key"}}
        )

        with self.assertRaises(GeminiAPIError):
            generate_structured("prompt", SampleSchema, max_retries=3)
        self.assertEqual(self.client.models.generate_content.call_count, 1)

    def test_network_error_is_retried(self):
        """Lỗi mạng/timeout → retry, hết lượt thì ném GeminiAPIError."""
        self.client.models.generate_content.side_effect = httpx.ConnectTimeout("timeout")

        with self.assertRaises(GeminiAPIError):
            generate_structured("prompt", SampleSchema, max_retries=1)
        self.assertEqual(self.client.models.generate_content.call_count, 2)

    def test_empty_prompt_raises_value_error(self):
        with self.assertRaises(ValueError):
            generate_structured("   ", SampleSchema)


class TestGeminiClient(unittest.TestCase):
    """Kiểm thử khởi tạo client."""

    def setUp(self):
        gemini_service.reset_gemini_client()
        self.addCleanup(gemini_service.reset_gemini_client)

    def test_missing_api_key_raises_config_error(self):
        with mock.patch.object(gemini_service, "GEMINI_API_KEY", ""):
            with self.assertRaises(GeminiConfigError):
                gemini_service.get_gemini_client()

    def test_client_is_cached(self):
        with mock.patch.object(gemini_service, "GEMINI_API_KEY", "fake-key"):
            first = gemini_service.get_gemini_client()
            second = gemini_service.get_gemini_client()
        self.assertIs(first, second)


if __name__ == "__main__":
    unittest.main()
