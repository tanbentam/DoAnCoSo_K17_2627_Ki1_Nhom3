"""
tests/test_semantic_matching.py — Unit test cho module semantic_matching (Cosine Similarity JD ↔ CV)

Nhóm TestRealModel dùng mô hình nhúng thật và tự bỏ qua nếu chưa tải mô hình.
"""

import unittest
from types import SimpleNamespace
from unittest import mock

import numpy as np

from app.services import embedding_service, semantic_matching
from app.services.semantic_matching import (
    build_job_text,
    compute_job_cv_match,
    compute_semantic_match,
    cosine_similarity,
    cosine_similarity_matrix,
    similarity_to_score,
)


class TestCosineSimilarity(unittest.TestCase):
    """Kiểm thử công thức cosine similarity."""

    def test_identical_vectors(self):
        self.assertAlmostEqual(cosine_similarity([1, 2, 3], [1, 2, 3]), 1.0)

    def test_scale_invariant(self):
        """Cosine chỉ phụ thuộc hướng, không phụ thuộc độ dài vector."""
        self.assertAlmostEqual(cosine_similarity([1, 2, 3], [10, 20, 30]), 1.0)

    def test_orthogonal_and_opposite(self):
        self.assertAlmostEqual(cosine_similarity([1, 0], [0, 1]), 0.0)
        self.assertAlmostEqual(cosine_similarity([1, 0], [-1, 0]), -1.0)

    def test_known_value(self):
        # cos = (1*2 + 0*1) / (1 * sqrt(5)) = 2 / sqrt(5)
        self.assertAlmostEqual(cosine_similarity([1, 0], [2, 1]), 2 / np.sqrt(5))

    def test_zero_vector_returns_zero(self):
        self.assertEqual(cosine_similarity([0, 0, 0], [1, 2, 3]), 0.0)

    def test_dimension_mismatch_raises(self):
        with self.assertRaises(ValueError):
            cosine_similarity([1, 2], [1, 2, 3])

    def test_result_clipped_to_valid_range(self):
        value = cosine_similarity(np.full(384, 0.1), np.full(384, 0.1))
        self.assertLessEqual(value, 1.0)


class TestCosineSimilarityMatrix(unittest.TestCase):
    """Kiểm thử ma trận cosine nhiều-nhiều."""

    def test_matrix_matches_pairwise(self):
        a = np.array([[1.0, 0.0], [1.0, 1.0]])
        b = np.array([[0.0, 2.0], [3.0, 0.0], [1.0, 1.0]])
        matrix = cosine_similarity_matrix(a, b)
        self.assertEqual(matrix.shape, (2, 3))
        for i in range(2):
            for j in range(3):
                self.assertAlmostEqual(matrix[i, j], cosine_similarity(a[i], b[j]))

    def test_matrix_handles_zero_rows(self):
        matrix = cosine_similarity_matrix([[0.0, 0.0]], [[1.0, 0.0]])
        self.assertEqual(matrix[0, 0], 0.0)

    def test_matrix_dimension_mismatch_raises(self):
        with self.assertRaises(ValueError):
            cosine_similarity_matrix([[1.0, 0.0]], [[1.0, 0.0, 0.0]])


class TestSimilarityToScore(unittest.TestCase):
    """Kiểm thử hiệu chỉnh cosine → điểm 0–100."""

    def test_linear_mapping(self):
        self.assertEqual(similarity_to_score(0.2, floor=0.2, ceil=0.8), 0.0)
        self.assertEqual(similarity_to_score(0.5, floor=0.2, ceil=0.8), 50.0)
        self.assertEqual(similarity_to_score(0.8, floor=0.2, ceil=0.8), 100.0)

    def test_clamped_outside_range(self):
        self.assertEqual(similarity_to_score(-0.5, floor=0.2, ceil=0.8), 0.0)
        self.assertEqual(similarity_to_score(0.95, floor=0.2, ceil=0.8), 100.0)

    def test_invalid_bounds_raise(self):
        with self.assertRaises(ValueError):
            similarity_to_score(0.5, floor=0.8, ceil=0.2)


class TestBuildJobText(unittest.TestCase):
    """Kiểm thử ghép văn bản JD."""

    def test_includes_all_fields(self):
        job = SimpleNamespace(
            title="Backend Developer",
            description="Phát triển API.",
            requirements="Thành thạo Python.",
            required_skills=["Python", "FastAPI"],
            preferred_skills=["Docker"],
        )
        text = build_job_text(job)
        self.assertEqual(
            text,
            "Backend Developer\nPhát triển API.\nYêu cầu: Thành thạo Python.\n"
            "Kỹ năng bắt buộc: Python, FastAPI\nKỹ năng ưu tiên: Docker",
        )

    def test_skips_missing_fields(self):
        job = SimpleNamespace(title="Tester", description="", requirements=None,
                              required_skills=[], preferred_skills=None)
        self.assertEqual(build_job_text(job), "Tester")


class TestComputeSemanticMatch(unittest.TestCase):
    """Kiểm thử luồng so khớp với encoder giả lập."""

    def test_uses_document_vectors(self):
        vectors = {"JD": np.array([1.0, 0.0]), "CV": np.array([0.6, 0.8])}
        with mock.patch.object(semantic_matching, "encode_document", side_effect=lambda t: vectors[t]):
            result = compute_semantic_match("JD", "CV")
        self.assertAlmostEqual(result.similarity, 0.6)
        self.assertEqual(result.score, similarity_to_score(0.6))

    def test_empty_inputs_raise(self):
        with self.assertRaises(ValueError):
            compute_semantic_match("  ", "CV")
        with self.assertRaises(ValueError):
            compute_semantic_match("JD", "")

    def test_compute_job_cv_match_builds_job_text(self):
        job = SimpleNamespace(title="Dev", description="Mô tả", requirements=None,
                              required_skills=None, preferred_skills=None)
        with mock.patch.object(semantic_matching, "compute_semantic_match") as m:
            compute_job_cv_match(job, "CV")
        m.assert_called_once_with("Dev\nMô tả", "CV")


def _model_is_cached() -> bool:
    cache = embedding_service.get_cache_dir()
    return cache.exists() and any(cache.glob("*paraphrase-multilingual-MiniLM-L12-v2*"))


@unittest.skipUnless(_model_is_cached(), "Chưa tải mô hình nhúng (chạy download_embedding_model.py)")
class TestRealModel(unittest.TestCase):
    """CV càng phù hợp JD thì semantic_score càng cao (mô hình thật)."""

    JOB = SimpleNamespace(
        title="Backend Developer (Python/FastAPI)",
        description="Phát triển API cho hệ thống tuyển dụng với Python, FastAPI và MySQL.",
        requirements="Thành thạo Python và FastAPI. Có kinh nghiệm SQLAlchemy và MySQL. Hiểu RESTful API và Git.",
        required_skills=["Python", "FastAPI", "SQLAlchemy", "MySQL"],
        preferred_skills=["Docker", "Redis", "Linux"],
    )
    STRONG_CV = (
        "Backend Developer. Kỹ năng: Python, FastAPI, SQLAlchemy, MySQL, Docker, Redis, Git. "
        "Kinh nghiệm: 3 năm phát triển RESTful API bằng FastAPI và SQLAlchemy trên MySQL."
    )
    SYNONYM_CV = (
        "Software Engineer phía máy chủ. Xây dựng dịch vụ web bằng ngôn ngữ Python, thiết kế cơ sở dữ liệu "
        "quan hệ, ORM, giao diện lập trình ứng dụng theo chuẩn REST, container hóa ứng dụng."
    )
    UNRELATED_CV = (
        "Kế toán tổng hợp. Kỹ năng: Excel, MISA, lập báo cáo tài chính, quyết toán thuế, công nợ. "
        "Kinh nghiệm: 4 năm kế toán tại công ty thương mại."
    )

    def test_scores_rank_by_relevance(self):
        strong = compute_job_cv_match(self.JOB, self.STRONG_CV)
        synonym = compute_job_cv_match(self.JOB, self.SYNONYM_CV)
        unrelated = compute_job_cv_match(self.JOB, self.UNRELATED_CV)

        self.assertGreater(strong.score, synonym.score)
        self.assertGreater(synonym.score, unrelated.score)
        self.assertGreaterEqual(strong.score, 80)
        self.assertLess(unrelated.score, 30)
        # CV diễn đạt khác từ ngữ vẫn được nhận diện là liên quan (Semantic Matching)
        self.assertGreater(synonym.score, 40)


if __name__ == "__main__":
    unittest.main()
