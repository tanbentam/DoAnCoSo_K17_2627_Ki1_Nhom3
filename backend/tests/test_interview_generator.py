"""
tests/test_interview_generator.py — Unit test cho module sinh câu hỏi phỏng vấn (Mục 4.8)

Nhà cung cấp AI được giả lập (mock ai_provider.generate_structured), không gọi mạng thật.
"""

import json
import re
import unittest
from types import SimpleNamespace
from unittest import mock

from app.schemas.interview import InterviewQuestion, InterviewQuestionSet
from app.services import interview_generator
from app.services.ai_errors import AIProviderError, StructuredResult
from app.services.interview_generator import (
    INTERVIEW_SYSTEM_INSTRUCTION,
    LOCAL_INTERVIEW_SYSTEM_INSTRUCTION,
    MAX_QUESTIONS,
    build_interview_prompt,
    find_assumed_skill_questions,
    generate_interview_questions,
    normalize_interview_questions,
    strip_yes_no_opener,
)

JOB = SimpleNamespace(
    title="Backend Developer (Python/FastAPI)",
    requirements="Thành thạo Python và FastAPI. Có kinh nghiệm SQLAlchemy và MySQL.",
    required_skills=["Python", "FastAPI", "SQLAlchemy", "MySQL"],
    preferred_skills=["Docker", "Redis"],
    experience_years_min=2,
)

INFO = {
    "current_title": "Software Engineer",
    "summary": "Kỹ sư phần mềm 3 năm kinh nghiệm Python.",
    "skills": ["Python", "Flask", "PostgreSQL"],
    "experience_years": 1.5,
    "work_experience": [{"position": "Dev", "company": "ABC", "start_date": "2023-01", "end_date": "present",
                         "description": "Xây dựng API bằng Flask", "extra_field": "bỏ qua"}],
    "experience_details": {"final": 1.5, "stated": 3.0, "calculated": 1.5, "discrepancy": True},
    "scoring_details": {
        "missing_preferred_skills": ["Redis"],
        "skill_matches": [
            {"skill": "Python", "matched": True, "match_type": "exact", "matched_with": "Python"},
            {"skill": "MySQL", "matched": True, "match_type": "semantic", "matched_with": "PostgreSQL"},
            {"skill": "Docker", "matched": True, "match_type": "text", "matched_with": "Docker"},
            {"skill": "FastAPI", "matched": False, "match_type": None, "matched_with": None},
        ],
    },
}


def _q(text, skill="FastAPI", category="skill_gap"):
    return InterviewQuestion(question=text, category=category, target_skill=skill,
                             purpose="Đánh giá năng lực", good_answer_hints="Nêu ví dụ cụ thể")


def _section(prompt: str, tag: str) -> dict:
    return json.loads(re.search(rf"<{tag}>\n(.*?)\n</{tag}>", prompt, re.S).group(1))


class TestBuildPrompt(unittest.TestCase):

    def test_contains_job_profile_and_gaps(self):
        prompt = build_interview_prompt(JOB, INFO, ["FastAPI", "SQLAlchemy"])
        job = _section(prompt, "job")
        gaps = _section(prompt, "gap_analysis")
        profile = _section(prompt, "candidate_profile")

        self.assertEqual(job["required_skills"], JOB.required_skills)
        self.assertEqual(gaps["missing_required_skills"], ["FastAPI", "SQLAlchemy"])
        self.assertEqual(gaps["missing_preferred_skills"], ["Redis"])
        # Chỉ kỹ năng khớp gián tiếp (semantic/text) cần kiểm chứng, không gồm exact
        self.assertEqual(gaps["skills_to_verify"], ["MySQL (CV ghi: PostgreSQL)", "Docker (CV ghi: Docker)"])
        self.assertIn("JD yêu cầu tối thiểu 2 năm", gaps["experience_note"])
        self.assertIn("cần làm rõ", gaps["experience_note"])
        self.assertEqual(profile["skills"], INFO["skills"])
        self.assertNotIn("extra_field", profile["work_experience"][0])

    def test_falls_back_to_cv_text_without_profile(self):
        prompt = build_interview_prompt(JOB, None, ["FastAPI"], cv_text="Nguyễn Văn A - Python " + "x" * 10000)
        self.assertIn("<cv>\nNguyễn Văn A - Python", prompt)
        self.assertNotIn("<candidate_profile>", prompt)
        self.assertLess(len(prompt), 8000)

    def test_no_experience_note_when_sufficient(self):
        info = {**INFO, "experience_details": {"final": 5.0, "discrepancy": False}}
        self.assertIsNone(_section(build_interview_prompt(JOB, info, []), "gap_analysis")["experience_note"])

    def test_system_instruction_forbids_discriminatory_questions(self):
        for word in ("tuổi", "giới tính", "hôn nhân", "tôn giáo"):
            self.assertIn(word, INTERVIEW_SYSTEM_INSTRUCTION)


class TestNormalize(unittest.TestCase):

    def test_dedupe_and_strip(self):
        data = InterviewQuestionSet(questions=[
            _q("  Bạn sẽ xây dựng API   bằng FastAPI thế nào? "),
            _q("Bạn sẽ xây dựng API bằng FastAPI thế nào"),
            _q("   "),
            _q("Hãy kể về một dự án dùng ORM.", skill=" SQLAlchemy "),
        ])
        result = normalize_interview_questions(data)
        self.assertEqual([q.question for q in result.questions],
                         ["Bạn sẽ xây dựng API bằng FastAPI thế nào?", "Hãy kể về một dự án dùng ORM."])
        self.assertEqual(result.questions[1].target_skill, "SQLAlchemy")

    def test_strip_yes_no_opener(self):
        """qwen2.5:7b hay mở đầu "Bạn đã từng... chưa?" dù prompt đã cấm → bỏ vế có/không, giữ câu hỏi mở."""
        cases = {
            "Bạn đã từng làm việc với FastAPI chưa? Hãy so sánh FastAPI với Starlette.":
                "Hãy so sánh FastAPI với Starlette.",
            "Bạn có kinh nghiệm làm việc với Docker không? hãy mô tả cách triển khai.":
                "Hãy mô tả cách triển khai.",
            # Giữ nguyên: lời đề nghị chia sẻ, câu hỏi về hệ thống, không có vế sau, câu trần thuật
            "Bạn có thể chia sẻ về dự án dùng MySQL không? Bạn tối ưu thế nào?":
                "Bạn có thể chia sẻ về dự án dùng MySQL không? Bạn tối ưu thế nào?",
            "Hệ thống của bạn có dùng cache không? Vì sao?": "Hệ thống của bạn có dùng cache không? Vì sao?",
            "Bạn đã từng làm việc với Redis chưa?": "Bạn đã từng làm việc với Redis chưa?",
            "Bạn đã xây dựng API bằng Flask. Nếu chuyển sang FastAPI bạn làm gì?":
                "Bạn đã xây dựng API bằng Flask. Nếu chuyển sang FastAPI bạn làm gì?",
            # Vế sau phụ thuộc câu có/không → giữ nguyên (lỗi gặp ở báo cáo test 2026-10-16 14:28, hồ sơ #41, #49)
            "Bạn đã từng làm việc với FastAPI chưa? Nếu có, hãy so sánh FastAPI với Flask.":
                "Bạn đã từng làm việc với FastAPI chưa? Nếu có, hãy so sánh FastAPI với Flask.",
            "Bạn đã từng làm việc với VueJS và Bootstrap 5 chưa? Nếu không, bạn sẽ làm thế nào để nắm bắt chúng?":
                "Bạn đã từng làm việc với VueJS và Bootstrap 5 chưa? Nếu không, bạn sẽ làm thế nào để nắm bắt chúng?",
        }
        for raw, expected in cases.items():
            self.assertEqual(strip_yes_no_opener(raw), expected, raw)

    def test_normalize_applies_opener_strip(self):
        data = InterviewQuestionSet(questions=[_q("Bạn đã dùng SQLAlchemy chưa? Hãy thiết kế model cho bảng đơn hàng.")])
        self.assertEqual(normalize_interview_questions(data).questions[0].question,
                         "Hãy thiết kế model cho bảng đơn hàng.")

    def test_caps_at_five(self):
        data = InterviewQuestionSet(questions=[_q(f"Câu hỏi số {i}?") for i in range(8)])
        self.assertEqual(len(normalize_interview_questions(data).questions), MAX_QUESTIONS)


class TestGenerate(unittest.TestCase):

    def _result(self, questions):
        return StructuredResult(InterviewQuestionSet(questions=questions), "ollama", "qwen2.5:7b", 2.0)

    def test_calls_provider_with_schema(self):
        questions = [_q(f"Câu {i}?") for i in range(4)]
        with mock.patch.object(interview_generator, "generate_structured", return_value=self._result(questions)) as m:
            result = generate_interview_questions(JOB, INFO, ["FastAPI"], mode="local")
        kwargs = m.call_args.kwargs
        self.assertIs(kwargs["schema"], InterviewQuestionSet)
        self.assertEqual(kwargs["system_instruction"], INTERVIEW_SYSTEM_INSTRUCTION)
        self.assertEqual(kwargs["mode"], "local")
        self.assertEqual(len(result.data.questions), 4)

    def test_too_few_questions_logged_not_failed(self):
        with mock.patch.object(interview_generator, "generate_structured", return_value=self._result([_q("Một câu?")])):
            with self.assertLogs("app.services.interview_generator", level="WARNING"):
                result = generate_interview_questions(JOB, INFO, ["FastAPI"])
        self.assertEqual(len(result.data.questions), 1)

    def test_no_candidate_data_raises(self):
        with mock.patch.object(interview_generator, "generate_structured") as m:
            with self.assertRaises(ValueError):
                generate_interview_questions(JOB, {}, ["FastAPI"], cv_text="  ")
        m.assert_not_called()

    def test_provider_error_propagates(self):
        with mock.patch.object(interview_generator, "generate_structured", side_effect=AIProviderError("down")):
            with self.assertRaises(AIProviderError):
                generate_interview_questions(JOB, INFO, ["FastAPI"])


class TestSchemaCompatibility(unittest.TestCase):

    def test_no_default_values(self):
        for model in (InterviewQuestionSet, InterviewQuestion):
            schema = model.model_json_schema()
            self.assertEqual(set(schema["required"]), set(model.model_fields))

    def test_category_is_enum(self):
        schema = InterviewQuestionSet.model_json_schema()
        category = schema["$defs"]["InterviewQuestion"]["properties"]["category"]
        self.assertEqual(set(category["enum"]), {"skill_gap", "skill_verification", "experience", "behavioral"})

    def test_accepted_by_genai_config(self):
        from google.genai import types
        config = types.GenerateContentConfig(response_mime_type="application/json", response_schema=InterviewQuestionSet)
        self.assertIs(config.response_schema, InterviewQuestionSet)


class TestAssumedSkillQuestions(unittest.TestCase):
    """Issue 08: câu skill_gap giả định ứng viên đã dùng kỹ năng còn thiếu."""

    MISSING = ["FastAPI", "SQLAlchemy", "MySQL"]

    def test_detects_assumed_use(self):
        data = InterviewQuestionSet(questions=[
            _q("Hãy mô tả cách bạn đã sử dụng SQLAlchemy trong một dự án gần đây như thế nào?", "SQLAlchemy"),
            _q("Kể về dự án bạn dùng FastAPI để xây dựng API ra sao?"),
            _q("Kinh nghiệm của bạn với MySQL ra sao?", "MySQL"),
            _q("Bạn đã làm việc với Flask. Nếu dự án yêu cầu FastAPI, bạn sẽ xây dựng API bất đồng bộ như thế nào?"),
            _q("Trong dự án ở ABC, bạn đã sử dụng Python để tối ưu API như thế nào?", "Python", "experience"),
        ])
        self.assertEqual(find_assumed_skill_questions(data, self.MISSING), [0, 1, 2])

    def test_bridge_question_not_flagged(self):
        data = InterviewQuestionSet(questions=[
            _q("Bạn đã làm việc với Flask, nếu cần FastAPI thì bạn sẽ chuyển API sang như thế nào?"),
            _q("Bạn đã dùng PostgreSQL nếu chuyển MySQL bạn sẽ đổi gì ra sao?", "MySQL"),
            _q("Bạn đã sử dụng ORM nào? Với SQLAlchemy bạn sẽ quản lý session như thế nào?", "SQLAlchemy"),
        ])
        self.assertEqual(find_assumed_skill_questions(data, self.MISSING), [])

    def _result(self, questions, latency=2.0):
        return StructuredResult(InterviewQuestionSet(questions=questions), "ollama", "qwen2.5:7b", latency, ["qwen2.5:7b: OK"])

    GOOD = [
        _q("Bạn đã làm việc với Flask. Nếu dự án yêu cầu FastAPI, bạn sẽ thiết kế API như thế nào?"),
        _q("Bạn đã dùng PostgreSQL. Nếu hệ thống chuyển sang MySQL, bạn sẽ thiết kế chỉ mục ra sao?", "MySQL"),
        _q("Trong dự án ở ABC, bạn xử lý lỗi khi API quá tải như thế nào?", "Xử lý sự cố", "experience"),
    ]
    BAD = _q("Hãy mô tả cách bạn đã sử dụng SQLAlchemy trong dự án như thế nào?", "SQLAlchemy")

    def test_local_uses_local_instruction_and_retries_once(self):
        first = self._result([self.BAD, *self.GOOD[:2]])
        second = self._result(list(self.GOOD), latency=3.0)
        with mock.patch.object(interview_generator, "generate_structured", side_effect=[first, second]) as m:
            result = generate_interview_questions(JOB, INFO, self.MISSING, mode="local")
        self.assertEqual(m.call_count, 2)
        self.assertEqual(m.call_args_list[0].kwargs["local_system_instruction"], LOCAL_INTERVIEW_SYSTEM_INSTRUCTION)
        self.assertIn(self.BAD.question, m.call_args_list[1].kwargs["prompt"])
        self.assertEqual([q.question for q in result.data.questions], [q.question for q in self.GOOD])
        self.assertEqual(result.latency_seconds, 5.0)

    def test_drops_bad_questions_when_retry_still_bad(self):
        first = self._result([self.BAD, *self.GOOD])
        with mock.patch.object(interview_generator, "generate_structured", side_effect=[first, first]):
            result = generate_interview_questions(JOB, INFO, self.MISSING, mode="local")
        self.assertEqual(len(result.data.questions), 3)
        self.assertNotIn(self.BAD.question, [q.question for q in result.data.questions])

    def test_merges_good_questions_from_both_attempts(self):
        # Trường hợp gặp ở test thật 28/10: mỗi lần chỉ có 2 câu đạt, gộp lại đủ 3 câu khác nhau
        bad2 = _q("Kể về dự án bạn dùng FastAPI ra sao?")
        first = self._result([self.BAD, bad2, *self.GOOD[:2]])
        second = self._result([self.BAD, bad2, self.GOOD[0], self.GOOD[2]])
        with mock.patch.object(interview_generator, "generate_structured", side_effect=[first, second]):
            result = generate_interview_questions(JOB, INFO, self.MISSING, mode="local")
        self.assertEqual([q.question for q in result.data.questions], [q.question for q in self.GOOD])

    def test_keeps_only_good_questions_even_if_fewer_than_min(self):
        first = self._result([self.BAD, *self.GOOD[:2]])
        with mock.patch.object(interview_generator, "generate_structured", side_effect=[first, AIProviderError("down")]):
            result = generate_interview_questions(JOB, INFO, self.MISSING, mode="local")
        self.assertEqual([q.question for q in result.data.questions], [q.question for q in self.GOOD[:2]])

    def test_keeps_first_result_when_no_good_question(self):
        first = self._result([self.BAD])
        with mock.patch.object(interview_generator, "generate_structured", side_effect=[first, first]):
            result = generate_interview_questions(JOB, INFO, self.MISSING, mode="local")
        self.assertEqual([q.question for q in result.data.questions], [self.BAD.question])

    def test_gemini_result_not_checked(self):
        gemini = StructuredResult(InterviewQuestionSet(questions=[self.BAD, *self.GOOD]), "gemini", "gemini-3.8-flash", 1.0)
        with mock.patch.object(interview_generator, "generate_structured", return_value=gemini) as m:
            result = generate_interview_questions(JOB, INFO, self.MISSING)
        self.assertEqual(m.call_count, 1)
        self.assertEqual(len(result.data.questions), 4)


if __name__ == "__main__":
    unittest.main()
