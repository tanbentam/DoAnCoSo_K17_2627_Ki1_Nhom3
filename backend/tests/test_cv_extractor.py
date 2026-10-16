"""
tests/test_cv_extractor.py — Unit test cho module cv_extractor (prompt bóc tách CV → JSON)

Nhà cung cấp AI được giả lập (mock ai_provider.generate_structured), không gọi mạng thật.
"""

import unittest
from datetime import date
from unittest import mock

from app.schemas.cv_extraction import CVExtraction, Education, WorkExperience
from app.services import cv_extractor
from app.services.ai_errors import AIProviderError, StructuredResult
from app.services.cv_extractor import (
    CV_EXTRACTION_SYSTEM_INSTRUCTION,
    build_cv_extraction_prompt,
    calculate_experience_years,
    extract_cv_info,
    extract_cv_info_detailed,
    normalize_cv_extraction,
    resolve_experience_years,
)
from app.services.gemini_service import GeminiAPIError


def _result(data, provider="gemini", model="gemini-test"):
    return StructuredResult(data=data, provider=provider, model=model, latency_seconds=1.0)


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
        experience_years_stated=None,
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
        self.assertIn("Mốc thời gian của CV (dùng cho \"hiện tại\"/\"present\"): 2026-10.", prompt)

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

    def test_nested_fields_normalized(self):
        """Mô hình cục bộ hay trả "" thay vì null và viết "Present"/"nay" không thống nhất."""
        data = _make_extraction(
            work_experience=[
                WorkExperience(company="FPT", position="Dev", start_date="2021-03", end_date="Present", description=""),
                WorkExperience(company="VNG", position="Dev", start_date="", end_date="nay", description=" Làm API "),
            ],
            education=[Education(institution="HUST", degree="", major=" ", graduation_year=2020, gpa="")],
        )
        result = normalize_cv_extraction(data)
        self.assertEqual([w.end_date for w in result.work_experience], ["present", "present"])
        self.assertIsNone(result.work_experience[0].description)
        self.assertIsNone(result.work_experience[1].start_date)
        self.assertEqual(result.work_experience[1].description, "Làm API")
        self.assertIsNone(result.education[0].degree)
        self.assertIsNone(result.education[0].major)
        self.assertIsNone(result.education[0].gpa)


def _job(start, end, company="C"):
    return WorkExperience(company=company, position="Dev", start_date=start, end_date=end, description=None)


class TestExperienceYears(unittest.TestCase):
    """Tính số năm kinh nghiệm bằng code từ các mốc thời gian (docs/Issues/05)."""

    REF = date(2026, 10, 16)

    def test_single_job_inclusive_months(self):
        # 01/2022 → 12/2022 = 12 tháng = 1.0 năm
        self.assertEqual(calculate_experience_years([_job("2022-01", "2022-12")], self.REF), 1.0)

    def test_present_counts_to_reference_date(self):
        # 07/2021 → 10/2026 = 64 tháng ≈ 5.3 năm (CV1 mẫu; qwen2.5:7b trả sai 3.0)
        jobs = [_job("2021-07", "2023-02"), _job("2023-03", "present")]
        self.assertEqual(calculate_experience_years(jobs, self.REF), 5.3)

    def test_old_cv_uses_document_date(self):
        """CV lập 01/2024 ghi 'since 01/2020 – present' → 4.1 năm, không phải 6.8 năm."""
        jobs = [_job("2020-01", "present")]
        self.assertEqual(calculate_experience_years(jobs, date(2024, 1, 28)), 4.1)
        self.assertEqual(calculate_experience_years(jobs, self.REF), 6.8)

    def test_overlapping_jobs_merged(self):
        # 01/2020–12/2021 và 06/2021–06/2022 chồng lấn → 01/2020–06/2022 = 30 tháng
        jobs = [_job("2020-01", "2021-12"), _job("2021-06", "2022-06")]
        self.assertEqual(calculate_experience_years(jobs, self.REF), 2.5)

    def test_gap_between_jobs_not_counted(self):
        jobs = [_job("2019-01", "2019-12"), _job("2022-01", "2022-12")]
        self.assertEqual(calculate_experience_years(jobs, self.REF), 2.0)

    def test_date_formats(self):
        for start, end in [("03/2023", "02/2024"), ("Mar 2023", "February 2024"), ("2023/3", "2024-2")]:
            self.assertEqual(calculate_experience_years([_job(start, end)], self.REF), 1.0, (start, end))
        # Chỉ có năm: tháng 1 → tháng 12
        self.assertEqual(calculate_experience_years([_job("2020", "2021")], self.REF), 2.0)

    def test_invalid_or_missing_dates_ignored(self):
        jobs = [_job(None, "2022-01"), _job("abc", "present"), _job("2025-05", "2024-01"), _job("2030-01", "present")]
        self.assertIsNone(calculate_experience_years(jobs, self.REF))

    def test_future_end_clamped_to_reference(self):
        self.assertEqual(calculate_experience_years([_job("2026-01", "2027-12")], self.REF), 0.8)

    def test_resolution_priority(self):
        with_dates = _make_extraction(experience_years=3.0, experience_years_stated=3.0,
                                      work_experience=[_job("2021-07", "present")])
        details = resolve_experience_years(with_dates, self.REF)
        self.assertEqual((details["final"], details["source"]), (5.3, "calculated"))
        self.assertTrue(details["discrepancy"])

        stated_only = _make_extraction(experience_years=2.0, experience_years_stated=4.0)
        self.assertEqual(resolve_experience_years(stated_only, self.REF)["source"], "stated")

        model_only = _make_extraction(experience_years=2.0)
        details = resolve_experience_years(model_only, self.REF)
        self.assertEqual((details["final"], details["source"]), (2.0, "model"))
        self.assertFalse(details["discrepancy"])

    def test_non_employment_entries_excluded(self):
        """Hoạt động sinh viên (CV Lê Viết Hưng: President of Student Council 2015–2018) không tính kinh nghiệm."""
        jobs = [
            _job("2016-01", "2017-01", company="VNG Company"),
            WorkExperience(company="UIT-VNU", position="President of UIT's Student Council",
                           start_date="2015-01", end_date="2018-01", description=None),
            WorkExperience(company="CLB Tin học", position="Trưởng ban", start_date="2014-01", end_date="2015-01",
                           description=None),
        ]
        self.assertEqual(calculate_experience_years(jobs, self.REF), 1.1)

    def test_unknown_cv_date_prefers_stated_when_much_lower(self):
        """CV không có ngày lập (Google Docs) + số tự tính vượt số CV ghi ≥ 1.5 năm → CV cũ, dùng số CV ghi."""
        data = _make_extraction(experience_years_stated=7.8, work_experience=[_job("2015-07", "present")])
        unknown = resolve_experience_years(data, self.REF, reference_date_known=False)
        self.assertEqual((unknown["final"], unknown["source"]), (7.8, "stated_old_cv"))
        self.assertEqual(unknown["reference_source"], "today")
        # Biết ngày lập CV → tin số tự tính
        known = resolve_experience_years(data, self.REF, reference_date_known=True)
        self.assertEqual((known["final"], known["source"]), (11.3, "calculated"))

    def test_unknown_cv_date_keeps_calculated_when_close_to_stated(self):
        data = _make_extraction(experience_years_stated=5.0, work_experience=[_job("2021-07", "present")])
        self.assertEqual(resolve_experience_years(data, self.REF, reference_date_known=False)["source"], "calculated")

    def test_normalize_overrides_model_years(self):
        data = _make_extraction(experience_years=3.0, work_experience=[_job("2021-07", "Present")])
        self.assertEqual(normalize_cv_extraction(data, self.REF).experience_years, 5.3)


class TestExtractCVInfo(unittest.TestCase):
    """Kiểm thử luồng bóc tách CV."""

    def test_calls_ai_provider_with_schema_and_system_instruction(self):
        with mock.patch.object(cv_extractor, "generate_structured", return_value=_result(_make_extraction())) as m:
            extract_cv_info("CV nội dung", mode="local")

        kwargs = m.call_args.kwargs
        self.assertIs(kwargs["schema"], CVExtraction)
        self.assertEqual(kwargs["system_instruction"], CV_EXTRACTION_SYSTEM_INSTRUCTION)
        self.assertEqual(kwargs["mode"], "local")
        self.assertIn("CV nội dung", kwargs["prompt"])

    def test_result_is_normalized(self):
        raw = _make_extraction(skills=["SQL", "sql"], experience_years=1.04)
        with mock.patch.object(cv_extractor, "generate_structured", return_value=_result(raw)):
            result = extract_cv_info("CV")
        self.assertEqual(result.skills, ["SQL"])
        self.assertEqual(result.experience_years, 1.0)

    def test_detailed_keeps_provider_meta(self):
        with mock.patch.object(cv_extractor, "generate_structured",
                               return_value=_result(_make_extraction(), provider="ollama", model="qwen2.5:7b")):
            result = extract_cv_info_detailed("CV")
        self.assertEqual(result.meta()["provider"], "ollama")
        self.assertEqual(result.meta()["model"], "qwen2.5:7b")
        self.assertEqual(result.extras["experience_details"]["source"], "model")

    def test_reference_date_passed_to_prompt_and_calculation(self):
        raw = _make_extraction(work_experience=[_job("2020-01", "present")])
        with mock.patch.object(cv_extractor, "generate_structured", return_value=_result(raw)) as m:
            result = extract_cv_info_detailed("CV", reference_date=date(2024, 1, 28))
        self.assertIn("2024-01", m.call_args.kwargs["prompt"])
        self.assertEqual(result.data.experience_years, 4.1)
        self.assertEqual(result.extras["experience_details"]["reference_date"], "2024-01-28")

    def test_empty_cv_raises_value_error(self):
        with mock.patch.object(cv_extractor, "generate_structured") as m:
            with self.assertRaises(ValueError):
                extract_cv_info("   ")
        m.assert_not_called()

    def test_ai_error_propagates(self):
        with mock.patch.object(cv_extractor, "generate_structured", side_effect=GeminiAPIError("503", 503)):
            with self.assertRaises(AIProviderError):
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
