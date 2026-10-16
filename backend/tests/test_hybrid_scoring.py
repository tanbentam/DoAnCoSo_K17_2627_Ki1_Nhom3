"""
tests/test_hybrid_scoring.py — Unit test cho module hybrid_scoring (40% Hard Filter + 60% Semantic Match)

Tầng so khớp ngữ nghĩa dùng encoder giả lập; nhóm TestRealModel dùng mô hình nhúng thật
và tự bỏ qua nếu chưa tải mô hình.
"""

import unittest
from types import SimpleNamespace
from unittest import mock

import numpy as np

from app.services import embedding_service, hybrid_scoring
from app.services.embedding_service import EmbeddingModelLoadError
from app.services.hybrid_scoring import (
    combine_scores,
    compute_hard_filter,
    compute_hybrid_score,
    experience_score,
    match_skills,
    normalize_skill,
)
from app.services.semantic_matching import compute_job_cv_match


def _job(required=("Python", "FastAPI", "SQLAlchemy", "MySQL"), preferred=("Docker", "Redis"), years=2):
    return SimpleNamespace(
        title="Backend Developer (Python/FastAPI)",
        description="Phát triển API với Python, FastAPI và MySQL.",
        requirements="Thành thạo Python, FastAPI, SQLAlchemy, MySQL.",
        required_skills=list(required),
        preferred_skills=list(preferred) if preferred is not None else None,
        experience_years_min=years,
    )


class TestNormalizeSkill(unittest.TestCase):
    """Kiểm thử chuẩn hóa tên kỹ năng."""

    def test_spelling_variants(self):
        for variant in ("ReactJS", "React.js", "react", "React JS"):
            self.assertEqual(normalize_skill(variant), "react")
        self.assertEqual(normalize_skill("Node.js"), "node")
        self.assertEqual(normalize_skill("Vue 3"), normalize_skill("VueJS"))

    def test_version_numbers_removed(self):
        self.assertEqual(normalize_skill("HTML5"), "html")
        self.assertEqual(normalize_skill("Python 3.10"), "python")
        self.assertEqual(normalize_skill("Bootstrap 5"), "bootstrap")

    def test_short_names_preserved(self):
        self.assertEqual(normalize_skill("ES6"), "es6")
        self.assertEqual(normalize_skill("C#"), "c#")
        self.assertEqual(normalize_skill("C++"), "c++")
        self.assertNotEqual(normalize_skill("C"), normalize_skill("C#"))

    def test_aliases(self):
        self.assertEqual(normalize_skill("Golang"), normalize_skill("Go"))
        self.assertEqual(normalize_skill("k8s"), "kubernetes")
        self.assertEqual(normalize_skill("RESTful API"), normalize_skill("REST API"))
        self.assertEqual(normalize_skill("Làm việc nhóm"), normalize_skill("Teamwork"))
        self.assertEqual(normalize_skill("JS"), normalize_skill("JavaScript"))

    def test_different_skills_not_merged(self):
        self.assertNotEqual(normalize_skill("Java"), normalize_skill("JavaScript"))
        self.assertNotEqual(normalize_skill("MySQL"), normalize_skill("SQL"))


class TestMatchSkills(unittest.TestCase):
    """Kiểm thử so khớp kỹ năng 4 tầng."""

    def test_exact_and_alias_match_types(self):
        results = match_skills(["Python", "Golang"], ["python 3", "Go"], use_semantic=False)
        self.assertEqual([(r.matched, r.match_type, r.matched_with) for r in results],
                         [(True, "exact", "python 3"), (True, "alias", "Go")])

    def test_text_fallback_finds_skill_in_cv(self):
        results = match_skills(["Docker"], [], cv_text="Triển khai ứng dụng bằng Docker trên AWS.", use_semantic=False)
        self.assertTrue(results[0].matched)
        self.assertEqual(results[0].match_type, "text")

    def test_text_fallback_respects_word_boundaries(self):
        results = match_skills(["SQL", "Java", "C"], [], cv_text="Kinh nghiệm MySQL, JavaScript và C#.", use_semantic=False)
        self.assertFalse(any(r.matched for r in results))

    def test_missing_skill(self):
        results = match_skills(["Kubernetes"], ["Docker"], cv_text="Docker", use_semantic=False)
        self.assertFalse(results[0].matched)
        self.assertIsNone(results[0].match_type)

    def test_ignores_blank_skills(self):
        self.assertEqual(len(match_skills(["Python", " ", None], ["Python"], use_semantic=False)), 1)

    def test_semantic_match_above_threshold(self):
        vectors = {"Redis": [1.0, 0.0], "Redis Cache": [0.9, 0.1], "Excel": [0.0, 1.0]}
        fake = lambda texts: np.array([vectors[t] for t in texts])
        with mock.patch.object(hybrid_scoring, "encode_texts", side_effect=fake):
            results = match_skills(["Redis"], ["Excel", "Redis Cache"], semantic_threshold=0.8)
        self.assertTrue(results[0].matched)
        self.assertEqual(results[0].match_type, "semantic")
        self.assertEqual(results[0].matched_with, "Redis Cache")

    def test_semantic_rejects_broader_candidate_term(self):
        """CV "SQL" (khái niệm rộng) không đáp ứng JD "SQLAlchemy" dù cosine cao."""
        fake = lambda texts: np.array([[1.0, 0.0] for _ in texts])  # cosine = 1 với mọi cặp
        with mock.patch.object(hybrid_scoring, "encode_texts", side_effect=fake):
            results = match_skills(["SQLAlchemy"], ["SQL"], semantic_threshold=0.8)
        self.assertFalse(results[0].matched)

    def test_semantic_below_threshold_not_matched(self):
        vectors = {"MySQL": [1.0, 0.0], "SQL Server": [0.7, 0.714]}
        fake = lambda texts: np.array([vectors[t] for t in texts])
        with mock.patch.object(hybrid_scoring, "encode_texts", side_effect=fake):
            results = match_skills(["MySQL"], ["SQL Server"], semantic_threshold=0.8)
        self.assertFalse(results[0].matched)

    def test_embedding_error_falls_back_gracefully(self):
        with mock.patch.object(hybrid_scoring, "encode_texts", side_effect=EmbeddingModelLoadError("offline")):
            results = match_skills(["Kubernetes"], ["Docker"])
        self.assertFalse(results[0].matched)


class TestExperienceScore(unittest.TestCase):

    def test_no_requirement(self):
        self.assertEqual(experience_score(None, 0), 100.0)

    def test_proportional_and_capped(self):
        self.assertEqual(experience_score(1, 2), 50.0)
        self.assertEqual(experience_score(5, 2), 100.0)
        self.assertEqual(experience_score(-1, 2), 0.0)

    def test_unknown_years(self):
        self.assertIsNone(experience_score(None, 3))


class TestHardFilter(unittest.TestCase):
    """Kiểm thử điểm Hard Filter (60% bắt buộc + 25% kinh nghiệm + 15% ưu tiên)."""

    def test_weighted_score(self):
        info = {"skills": ["Python", "FastAPI", "Docker"], "experience_years": 1}
        result = compute_hard_filter(_job(), info, use_semantic=False)
        # bắt buộc 2/4 = 50, kinh nghiệm 1/2 = 50, ưu tiên 1/2 = 50
        self.assertEqual(result.score, 50.0)
        self.assertEqual(result.matched_skills, ["Python", "FastAPI", "Docker"])
        self.assertEqual(result.missing_skills, ["SQLAlchemy", "MySQL"])
        self.assertEqual(result.missing_preferred_skills, ["Redis"])

    def test_perfect_candidate(self):
        info = {"skills": ["Python", "FastAPI", "SQLAlchemy", "MySQL", "Docker", "Redis"], "experience_years": 3}
        self.assertEqual(compute_hard_filter(_job(), info, use_semantic=False).score, 100.0)

    def test_weights_redistributed_when_no_preferred_skills(self):
        info = {"skills": ["Python", "FastAPI", "SQLAlchemy", "MySQL"], "experience_years": 0}
        result = compute_hard_filter(_job(preferred=None), info, use_semantic=False)
        # (100 × 0.60 + 0 × 0.25) / 0.85
        self.assertIsNone(result.preferred_skills_score)
        self.assertAlmostEqual(result.score, round(60 / 0.85, 2))

    def test_unknown_experience_excluded(self):
        """Gemini lỗi (không có extracted_info) → bỏ tiêu chí kinh nghiệm, vẫn tìm kỹ năng trong CV thô."""
        result = compute_hard_filter(_job(), None, cv_text="Python, FastAPI, SQLAlchemy, MySQL, Docker, Redis",
                                     use_semantic=False)
        self.assertIsNone(result.experience_score)
        self.assertEqual(result.score, 100.0)


class TestCombineScores(unittest.TestCase):
    """Kiểm thử công thức Hybrid 40/60."""

    def test_formula_40_60(self):
        self.assertEqual(combine_scores(50.0, 100.0), 80.0)
        self.assertEqual(combine_scores(100.0, 0.0), 40.0)

    def test_missing_component(self):
        self.assertEqual(combine_scores(70.0, None), 70.0)
        self.assertEqual(combine_scores(None, 55.0), 55.0)
        self.assertIsNone(combine_scores(None, None))

    def test_compute_hybrid_score_and_details(self):
        info = {"skills": ["Python", "FastAPI", "SQLAlchemy", "MySQL", "Docker", "Redis"], "experience_years": 3}
        result = compute_hybrid_score(_job(), info, cv_text=None, semantic_score=50.0, use_semantic_skills=False)
        self.assertEqual(result.matching_score, 70.0)  # 0.4 × 100 + 0.6 × 50
        details = result.to_details()
        self.assertEqual(details["hard_filter_score"], 100.0)
        self.assertEqual(len(details["skill_matches"]), 6)
        self.assertEqual(details["skill_matches"][0]["match_type"], "exact")


def _model_is_cached() -> bool:
    cache = embedding_service.get_cache_dir()
    return cache.exists() and any(cache.glob("*paraphrase-multilingual-MiniLM-L12-v2*"))


@unittest.skipUnless(_model_is_cached(), "Chưa tải mô hình nhúng (chạy download_embedding_model.py)")
class TestRealModel(unittest.TestCase):
    """Kịch bản bảo vệ (Mục 8): CV phù hợp > 85 điểm, CV trái ngành < 40 điểm."""

    def _score(self, cv_text, info):
        job = _job(preferred=("Docker", "Redis", "Linux"))
        semantic = compute_job_cv_match(job, cv_text)
        return compute_hybrid_score(job, info, cv_text, semantic.score)

    def test_strong_candidate_above_85(self):
        cv = ("Backend Developer. Kỹ năng: Python, FastAPI, SQLAlchemy, MySQL, Docker, Redis, Git, Linux. "
              "Kinh nghiệm: 3 năm phát triển RESTful API bằng FastAPI và SQLAlchemy trên MySQL.")
        info = {"skills": ["Python", "FastAPI", "SQLAlchemy", "MySQL", "Docker", "Redis", "Linux"], "experience_years": 3}
        self.assertGreater(self._score(cv, info).matching_score, 85)

    def test_unrelated_candidate_below_40(self):
        cv = "Kế toán tổng hợp. Kỹ năng: Excel, MISA, lập báo cáo tài chính, quyết toán thuế. 4 năm kinh nghiệm."
        info = {"skills": ["Excel", "MISA", "Báo cáo tài chính"], "experience_years": 4}
        result = self._score(cv, info)
        self.assertLess(result.matching_score, 40)
        self.assertEqual(result.hard_filter.missing_skills, ["Python", "FastAPI", "SQLAlchemy", "MySQL"])

    def test_sql_does_not_satisfy_sqlalchemy(self):
        results = match_skills(["SQLAlchemy"], ["SQL"])
        self.assertFalse(results[0].matched)


if __name__ == "__main__":
    unittest.main()
