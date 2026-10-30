"""
tests/test_ai_provider.py — Unit test cho cơ chế chuyển đổi nhà cung cấp AI (AI_PROVIDER=cloud|local|auto)
"""

import unittest
from unittest import mock

from pydantic import BaseModel

from app.services import ai_provider
from app.services.ai_errors import AIProviderError, StructuredResult
from app.services.gemini_service import GeminiAPIError, GeminiConfigError, GeminiQuotaExhaustedError
from app.services.ollama_service import OllamaConnectionError


class SampleSchema(BaseModel):
    name: str


def _result(provider, model):
    return StructuredResult(SampleSchema(name="A"), provider, model, 1.0, [f"{model}: OK"])


class TestProviderSwitch(unittest.TestCase):

    def setUp(self):
        gemini = mock.patch.object(ai_provider.gemini_service, "generate_structured_detailed",
                                   return_value=_result("gemini", "gemini-3.8-flash"))
        ollama = mock.patch.object(ai_provider.ollama_service, "generate_structured_detailed",
                                   return_value=_result("ollama", "qwen2.5:7b"))
        self.gemini = gemini.start()
        self.ollama = ollama.start()
        self.addCleanup(gemini.stop)
        self.addCleanup(ollama.stop)

    def test_cloud_uses_only_gemini(self):
        self.assertEqual(ai_provider.generate_structured("p", SampleSchema, mode="cloud").provider, "gemini")
        self.ollama.assert_not_called()

    def test_cloud_does_not_fall_back(self):
        self.gemini.side_effect = GeminiQuotaExhaustedError("hết lượt", 429)
        with self.assertRaises(GeminiQuotaExhaustedError):
            ai_provider.generate_structured("p", SampleSchema, mode="cloud")
        self.ollama.assert_not_called()

    def test_local_uses_only_ollama(self):
        self.assertEqual(ai_provider.generate_structured("p", SampleSchema, mode="local").provider, "ollama")
        self.gemini.assert_not_called()

    def test_auto_prefers_gemini(self):
        self.assertEqual(ai_provider.generate_structured("p", SampleSchema, mode="auto").model, "gemini-3.8-flash")
        self.ollama.assert_not_called()

    def test_auto_falls_back_to_ollama_on_quota(self):
        self.gemini.side_effect = GeminiQuotaExhaustedError("hết lượt", 429)
        result = ai_provider.generate_structured("p", SampleSchema, "HR", mode="auto")
        self.assertEqual(result.provider, "ollama")
        self.assertEqual(result.attempts[0], "gemini: GeminiQuotaExhaustedError")
        self.ollama.assert_called_once_with("p", SampleSchema, "HR")

    def test_local_system_instruction_only_for_ollama(self):
        # Issue 08: Ollama nhận chỉ dẫn riêng, Gemini giữ chỉ dẫn chung
        ai_provider.generate_structured("p", SampleSchema, "HR", mode="cloud", local_system_instruction="HR-local")
        self.gemini.assert_called_once_with("p", SampleSchema, "HR")
        ai_provider.generate_structured("p", SampleSchema, "HR", mode="local", local_system_instruction="HR-local")
        self.ollama.assert_called_once_with("p", SampleSchema, "HR-local")

    def test_auto_fallback_uses_local_system_instruction(self):
        self.gemini.side_effect = GeminiQuotaExhaustedError("hết lượt", 429)
        ai_provider.generate_structured("p", SampleSchema, "HR", mode="auto", local_system_instruction="HR-local")
        self.ollama.assert_called_once_with("p", SampleSchema, "HR-local")

    def test_auto_falls_back_on_any_gemini_error(self):
        for error in (GeminiAPIError("503", 503), GeminiConfigError("thiếu key")):
            self.gemini.side_effect = error
            self.assertEqual(ai_provider.generate_structured("p", SampleSchema, mode="auto").provider, "ollama")

    def test_auto_both_fail(self):
        self.gemini.side_effect = GeminiAPIError("503", 503)
        self.ollama.side_effect = OllamaConnectionError("chưa bật")
        with self.assertRaises(AIProviderError) as ctx:
            ai_provider.generate_structured("p", SampleSchema, mode="auto")
        self.assertIn("Gemini", str(ctx.exception))
        self.assertIn("Ollama", str(ctx.exception))

    def test_invalid_mode_treated_as_auto(self):
        self.assertEqual(ai_provider.get_provider_mode("gpu"), "auto")
        self.assertEqual(ai_provider.get_provider_mode(" LOCAL "), "local")


class TestProviderStatus(unittest.TestCase):

    def test_auto_reports_both(self):
        with mock.patch.object(ai_provider, "AI_PROVIDER", "auto"), \
                mock.patch.object(ai_provider.ollama_service, "check_ollama_status", return_value={"reachable": True}):
            status = ai_provider.get_provider_status()
        self.assertEqual(status["mode"], "auto")
        self.assertIn("model_chain", status["gemini"])
        self.assertTrue(status["ollama"]["reachable"])

    def test_cloud_skips_ollama_check(self):
        with mock.patch.object(ai_provider, "AI_PROVIDER", "cloud"), \
                mock.patch.object(ai_provider.ollama_service, "check_ollama_status") as check:
            status = ai_provider.get_provider_status()
        check.assert_not_called()
        self.assertNotIn("ollama", status)


if __name__ == "__main__":
    unittest.main()
