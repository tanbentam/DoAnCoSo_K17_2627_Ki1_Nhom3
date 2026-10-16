"""
tests/test_gemini_service.py — Unit test cho module gemini_service (Structured Outputs + chuỗi model dự phòng)

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
    GeminiQuotaExhaustedError,
    GeminiResponseError,
    generate_structured,
    generate_structured_detailed,
    parse_quota_error,
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


def _quota_error(per_day: bool, retry_delay: str = None):
    """Lỗi 429 giống phản hồi thật của Gemini (QuotaFailure + RetryInfo)."""
    quota_id = "GenerateRequestsPerDayPerProjectPerModel-FreeTier" if per_day else "GenerateRequestsPerMinutePerProjectPerModel-FreeTier"
    details = [{
        "@type": "type.googleapis.com/google.rpc.QuotaFailure",
        "violations": [{"quotaMetric": "generativelanguage.googleapis.com/generate_content_free_tier_requests",
                        "quotaId": quota_id}],
    }]
    if retry_delay:
        details.append({"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": retry_delay})
    return errors.ClientError(429, {"error": {"code": 429, "message": "quota", "status": "RESOURCE_EXHAUSTED",
                                              "details": details}})


OK = SampleSchema(full_name="A", skills=[])


class _GeminiTestCase(unittest.TestCase):
    """Client giả lập, không ngủ thật, chuỗi model mặc định = [main, backup]."""

    FALLBACKS: List[str] = []

    def setUp(self):
        self.client = mock.MagicMock()
        patches = [
            mock.patch.object(gemini_service, "get_gemini_client", return_value=self.client),
            mock.patch.object(gemini_service, "GEMINI_MODEL", "main-model"),
            mock.patch.object(gemini_service, "GEMINI_FALLBACK_MODELS", list(self.FALLBACKS)),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        sleep_patcher = mock.patch.object(gemini_service.time, "sleep")
        self.mock_sleep = sleep_patcher.start()
        self.addCleanup(sleep_patcher.stop)
        gemini_service.reset_model_state()
        self.addCleanup(gemini_service.reset_model_state)

    def called_models(self):
        return [c.kwargs["model"] for c in self.client.models.generate_content.call_args_list]


class TestGeminiService(_GeminiTestCase):
    """Structured Outputs và xử lý lỗi trên một model (không có model dự phòng)."""

    def test_returns_parsed_object(self):
        """SDK đã parse sẵn → trả về đúng instance schema."""
        expected = SampleSchema(full_name="Nguyễn Văn A", skills=["Python", "FastAPI"])
        self.client.models.generate_content.return_value = _make_response(parsed=expected)

        self.assertEqual(generate_structured("Bóc tách CV", SampleSchema), expected)

    def test_config_uses_json_mode_and_schema(self):
        """Request phải bật response_mime_type=application/json và response_schema."""
        self.client.models.generate_content.return_value = _make_response(parsed=OK)

        generate_structured("prompt", SampleSchema, system_instruction="Bạn là HR", model="gemini-test")

        kwargs = self.client.models.generate_content.call_args.kwargs
        self.assertEqual(kwargs["model"], "gemini-test")
        self.assertEqual(kwargs["config"].response_mime_type, "application/json")
        self.assertIs(kwargs["config"].response_schema, SampleSchema)
        self.assertEqual(kwargs["config"].system_instruction, "Bạn là HR")

    def test_detailed_result_reports_model(self):
        self.client.models.generate_content.return_value = _make_response(parsed=OK)

        result = generate_structured_detailed("prompt", SampleSchema)

        self.assertEqual((result.provider, result.model), ("gemini", "main-model"))
        self.assertEqual(result.attempts, ["main-model: OK"])

    def test_fallback_to_text_json(self):
        """Không có parsed → validate từ response.text."""
        self.client.models.generate_content.return_value = _make_response(
            text='{"full_name": "Trần B", "skills": ["Java"]}'
        )

        result = generate_structured("prompt", SampleSchema)

        self.assertEqual((result.full_name, result.skills), ("Trần B", ["Java"]))

    def test_invalid_json_raises_response_error(self):
        self.client.models.generate_content.return_value = _make_response(text='{"full_name": 1}')
        with self.assertRaises(GeminiResponseError):
            generate_structured("prompt", SampleSchema)

    def test_empty_response_reports_block_reason(self):
        self.client.models.generate_content.return_value = _make_response(text="", block_reason="SAFETY")
        with self.assertRaises(GeminiResponseError) as ctx:
            generate_structured("prompt", SampleSchema)
        self.assertIn("SAFETY", str(ctx.exception))

    def test_per_minute_rate_limit_waits_then_succeeds(self):
        """429 theo phút → chờ đúng retryDelay rồi thử lại cùng model."""
        self.client.models.generate_content.side_effect = [_quota_error(False, "12s"), _make_response(parsed=OK)]

        self.assertEqual(generate_structured("prompt", SampleSchema, max_retries=1), OK)
        self.mock_sleep.assert_called_once_with(12.0)
        self.assertEqual(self.called_models(), ["main-model", "main-model"])

    def test_rate_limit_without_details_uses_backoff(self):
        self.client.models.generate_content.side_effect = [
            errors.ClientError(429, {"error": {"message": "quota"}}),
            _make_response(parsed=OK),
        ]
        generate_structured("prompt", SampleSchema, max_retries=2)
        self.mock_sleep.assert_called_once_with(1)

    def test_server_error_exhausted_raises_api_error(self):
        """503 liên tục, không có model dự phòng → GeminiAPIError kèm status_code."""
        self.client.models.generate_content.side_effect = errors.ServerError(503, {"error": {"message": "overloaded"}})

        with self.assertRaises(GeminiAPIError) as ctx:
            generate_structured("prompt", SampleSchema, max_retries=2)
        self.assertNotIsInstance(ctx.exception, GeminiQuotaExhaustedError)
        self.assertEqual(ctx.exception.status_code, 503)
        self.assertEqual(self.client.models.generate_content.call_count, 3)

    def test_non_retryable_error_fails_fast(self):
        """Lỗi 403 (sai key) → không thử lại, không chuyển model."""
        self.client.models.generate_content.side_effect = errors.ClientError(403, {"error": {"message": "invalid key"}})

        with self.assertRaises(GeminiAPIError):
            generate_structured("prompt", SampleSchema, max_retries=3)
        self.assertEqual(self.client.models.generate_content.call_count, 1)

    def test_network_error_is_retried(self):
        self.client.models.generate_content.side_effect = httpx.ConnectTimeout("timeout")

        with self.assertRaises(GeminiAPIError):
            generate_structured("prompt", SampleSchema, max_retries=1)
        self.assertEqual(self.client.models.generate_content.call_count, 2)

    def test_empty_prompt_raises_value_error(self):
        with self.assertRaises(ValueError):
            generate_structured("   ", SampleSchema)


class TestModelFallback(_GeminiTestCase):
    """Chuỗi model dự phòng (docs/Issues/01, 02)."""

    FALLBACKS = ["backup-model", "lite-model"]

    def test_daily_quota_switches_immediately_without_retry(self):
        """429 theo ngày → không thử lại vô ích, chuyển ngay sang model dự phòng."""
        self.client.models.generate_content.side_effect = [_quota_error(True, "70290s"), _make_response(parsed=OK)]

        result = generate_structured_detailed("prompt", SampleSchema, max_retries=3)

        self.assertEqual(result.model, "backup-model")
        self.assertEqual(self.called_models(), ["main-model", "backup-model"])
        self.mock_sleep.assert_not_called()
        self.assertIn("main-model: 429 hết hạn mức theo ngày", result.attempts)

    def test_exhausted_model_skipped_on_next_call(self):
        """Model đã hết hạn mức được ghi nhớ → lần gọi sau bỏ qua luôn."""
        self.client.models.generate_content.side_effect = [
            _quota_error(True, "70290s"), _make_response(parsed=OK), _make_response(parsed=OK),
        ]
        generate_structured("prompt 1", SampleSchema)
        result = generate_structured_detailed("prompt 2", SampleSchema)

        self.assertEqual(self.called_models(), ["main-model", "backup-model", "backup-model"])
        self.assertIn("main-model: bỏ qua (đang hết hạn mức)", result.attempts)
        self.assertIn("main-model", gemini_service.get_exhausted_models())

    def test_exhausted_model_available_again_after_reset_time(self):
        with mock.patch.object(gemini_service.time, "time", return_value=1000.0):
            gemini_service.mark_model_exhausted("main-model", 60, "test")
            self.assertTrue(gemini_service.is_model_exhausted("main-model"))
        with mock.patch.object(gemini_service.time, "time", return_value=1061.0):
            self.assertFalse(gemini_service.is_model_exhausted("main-model"))

    def test_long_retry_delay_treated_as_exhausted(self):
        """retryDelay quá 30s (không rõ theo ngày) → cũng chuyển model thay vì chờ."""
        self.client.models.generate_content.side_effect = [_quota_error(False, "600s"), _make_response(parsed=OK)]

        self.assertEqual(generate_structured_detailed("prompt", SampleSchema).model, "backup-model")
        self.mock_sleep.assert_not_called()

    def test_server_error_switches_after_retries(self):
        """503 trên model chính (đã thử lại) → chuyển model dự phòng."""
        self.client.models.generate_content.side_effect = [
            errors.ServerError(503, {"error": {"message": "overloaded"}}),
            errors.ServerError(503, {"error": {"message": "overloaded"}}),
            _make_response(parsed=OK),
        ]
        result = generate_structured_detailed("prompt", SampleSchema, max_retries=1)

        self.assertEqual(self.called_models(), ["main-model", "main-model", "backup-model"])
        self.assertEqual(result.model, "backup-model")
        self.assertNotIn("main-model", gemini_service.get_exhausted_models())  # 503 chỉ tạm thời

    def test_model_not_found_marked_and_switched(self):
        self.client.models.generate_content.side_effect = [
            errors.ClientError(404, {"error": {"message": "no longer available"}}),
            _make_response(parsed=OK),
        ]
        self.assertEqual(generate_structured_detailed("prompt", SampleSchema).model, "backup-model")
        self.assertIn("main-model", gemini_service.get_exhausted_models())

    def test_all_models_quota_exhausted(self):
        self.client.models.generate_content.side_effect = [_quota_error(True, "100s")] * 3

        with self.assertRaises(GeminiQuotaExhaustedError) as ctx:
            generate_structured("prompt", SampleSchema)
        self.assertEqual(ctx.exception.status_code, 429)
        self.assertEqual(self.called_models(), ["main-model", "backup-model", "lite-model"])

        # Lần sau: mọi model đều đang bị bỏ qua → báo lỗi ngay, không gọi API
        with self.assertRaises(GeminiQuotaExhaustedError):
            generate_structured("prompt", SampleSchema)
        self.assertEqual(self.client.models.generate_content.call_count, 3)

    def test_mixed_failures_raise_api_error(self):
        self.client.models.generate_content.side_effect = [
            _quota_error(True, "100s"),
            errors.ServerError(503, {"error": {"message": "overloaded"}}),
            errors.ServerError(503, {"error": {"message": "overloaded"}}),
        ]
        with self.assertRaises(GeminiAPIError) as ctx:
            generate_structured("prompt", SampleSchema, max_retries=0)
        self.assertNotIsInstance(ctx.exception, GeminiQuotaExhaustedError)

    def test_explicit_model_disables_fallback(self):
        self.client.models.generate_content.side_effect = errors.ServerError(503, {"error": {"message": "x"}})
        with self.assertRaises(GeminiAPIError):
            generate_structured("prompt", SampleSchema, model="only-this", max_retries=0)
        self.assertEqual(self.called_models(), ["only-this"])

    def test_model_chain_deduplicated(self):
        with mock.patch.object(gemini_service, "GEMINI_FALLBACK_MODELS", ["main-model", "b", "b"]):
            self.assertEqual(gemini_service.get_model_chain(), ["main-model", "b"])


class TestParseQuotaError(unittest.TestCase):

    def test_daily_quota(self):
        self.assertEqual(parse_quota_error(_quota_error(True, "70290.5s")), (True, 70290.5))

    def test_per_minute_quota(self):
        self.assertEqual(parse_quota_error(_quota_error(False, "19s")), (False, 19.0))

    def test_without_details(self):
        self.assertEqual(parse_quota_error(errors.ClientError(429, {"error": {"message": "x"}})), (False, None))
        self.assertEqual(parse_quota_error(SimpleNamespace(details=None)), (False, None))


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
