"""
tests/test_cv_extractor.py — Unit test cho module cv_extractor (prompt bóc tách CV → JSON)

Gemini được giả lập (mock generate_structured), không gọi mạng thật.
"""

import unittest
from datetime import date
from unittest import mock

from app.schemas.cv_extraction import CVExtraction
from app.services import cv_extractor
from app.services.cv_extractor import (
    CV_EXTRACTION_SYSTEM_INSTRUCTION,
    build_cv_extraction_prompt,
    extract_cv_info,
    normalize_cv_extraction,
)
from app.services.gemini_service import GeminiAPIError


def _make_extraction(**overrides) -> CVExtraction:
    data = dict(
        full_name="Nguyễn Văn An",
        email="an@example.com",
        phone="0912345678",
        location="Hà Nội",
        current_title="Backend Developer",
        summary="Lập trình viên backend 3 năm kinh nghiệm.",
        skills=["Python", "FastAPI"],
        soft_skills=["Làm việc nhóm"],
        experience_years=3.0,
        work_experience=[],
        education=[],
        certifications=[],
        languages=[],
    )
    data.update(overrides)
    return CVExtraction(**data)


class TestBuildPrompt(unittest.TestCase):
    """Kiểm thử tạo prompt."""

    def test_prompt_wraps_cv_and_includes_date(self):
        prompt = build_cv_extraction_prompt("Nguyễn Văn An - Python", today=date(2026, 10, 16))
        self.assertIn("<cv>\nNguyễn Văn An - Python\n</cv>", prompt)
        self.assertIn("Ngày hiện tại: 2026-10.", prompt)

    def test_prompt_truncates_long_cv(self):
        prompt = build_cv_extraction_prompt("a" * 500, max_chars=100)
        self.assertIn("a" * 100 + "\n</cv>", prompt)
        self.assertNotIn("a" * 101, prompt)


class TestNormalize(unittest.TestCase):
    """Kiểm thử hậu xử lý kết quả Gemini."""

    def test_dedupe_skills_case_insensitive(self):
        data = _make_extraction(skills=["Python", "python ", "  FastAPI", "", "Docker", "PYTHON"])
        result = normalize_cv_extraction(data)
        self.assertEqual(result.skills, ["Python", "FastAPI", "Docker"])

    def test_clamp_and_round_experience_years(self):
        self.assertEqual(normalize_cv_extraction(_make_extraction(experience_years=-2)).experience_years, 0.0)
        self.assertEqual(normalize_cv_extraction(_make_extraction(experience_years=99)).experience_years, 50.0)
        self.assertEqual(normalize_cv_extraction(_make_extraction(experience_years=2.46)).experience_years, 2.5)

    def test_normalize_contact_fields(self):
        data = _make_extraction(email=" An.Nguyen@Gmail.COM ", phone="(+84) 912-345-678", location="   ")
        result = normalize_cv_extraction(data)
        self.assertEqual(result.email, "an.nguyen@gmail.com")
        self.assertEqual(result.phone, "+84912345678")
        self.assertIsNone(result.location)

    def test_phone_without_digits_becomes_none(self):
        self.assertIsNone(normalize_cv_extraction(_make_extraction(phone=" - ")).phone)


class TestExtractCVInfo(unittest.TestCase):
    """Kiểm thử luồng bóc tách CV."""

    def test_calls_gemini_with_schema_and_system_instruction(self):
        with mock.patch.object(cv_extractor, "generate_structured", return_value=_make_extraction()) as m:
            extract_cv_info("CV nội dung", model="gemini-test")

        kwargs = m.call_args.kwargs
        self.assertIs(kwargs["schema"], CVExtraction)
        self.assertEqual(kwargs["system_instruction"], CV_EXTRACTION_SYSTEM_INSTRUCTION)
        self.assertEqual(kwargs["model"], "gemini-test")
        self.assertIn("CV nội dung", kwargs["prompt"])

    def test_result_is_normalized(self):
        raw = _make_extraction(skills=["SQL", "sql"], experience_years=1.04)
        with mock.patch.object(cv_extractor, "generate_structured", return_value=raw):
            result = extract_cv_info("CV")
        self.assertEqual(result.skills, ["SQL"])
        self.assertEqual(result.experience_years, 1.0)

    def test_empty_cv_raises_value_error(self):
        with mock.patch.object(cv_extractor, "generate_structured") as m:
            with self.assertRaises(ValueError):
                extract_cv_info("   ")
        m.assert_not_called()

    def test_gemini_error_propagates(self):
        with mock.patch.object(cv_extractor, "generate_structured", side_effect=GeminiAPIError("503", 503)):
            with self.assertRaises(GeminiAPIError):
                extract_cv_info("CV")


class TestSchemaCompatibility(unittest.TestCase):
    """Schema phải chuyển được sang định dạng response_schema của Gemini."""

    def test_schema_has_no_default_values(self):
        """Gemini response_schema không hỗ trợ default → mọi trường phải là required."""
        schema = CVExtraction.model_json_schema()
        self.assertEqual(set(schema["required"]), set(CVExtraction.model_fields))

    def test_schema_accepted_by_genai_config(self):
        from google.genai import types

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=CVExtraction,
        )
        self.assertIs(config.response_schema, CVExtraction)


if __name__ == "__main__":
    unittest.main()
