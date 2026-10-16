"""
services/semantic_matching.py — Tính độ tương đồng ngữ nghĩa Cosine Similarity giữa vector JD và vector CV

Luồng: văn bản JD & CV → embedding_service.encode_document (vector 384 chiều, chuẩn hóa L2)
→ cosine similarity ∈ [-1, 1] → hiệu chỉnh tuyến tính về thang điểm 0–100 (semantic_score, trọng số 60%).

Vì sao cần hiệu chỉnh: với mô hình paraphrase-multilingual-MiniLM-L12-v2, hai văn bản tiếng Việt/Anh
bất kỳ hiếm khi có cosine < 0.2 (do cùng ngôn ngữ, cùng thể loại "hồ sơ"), còn CV rất khớp JD đạt ~0.8.
Đo thực tế trên JD "Backend Developer (Python/FastAPI)":
    CV backend khớp                0.79   → ~98 điểm
    CV diễn đạt khác, đồng nghĩa   0.56   → ~59 điểm
    CV frontend (khác vị trí)      0.32   → ~20 điểm
    CV kế toán (trái ngành)        0.22   → ~3 điểm
Nếu dùng cosine thô × 100, CV trái ngành vẫn được ~22 điểm và CV khớp chỉ ~79 điểm.
"""

import logging
from dataclasses import dataclass
from typing import Any, Iterable, Optional

import numpy as np

from app.core.config import SEMANTIC_SIM_CEIL, SEMANTIC_SIM_FLOOR
from app.services.embedding_service import encode_document

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SemanticMatchResult:
    """Kết quả so khớp ngữ nghĩa JD ↔ CV."""

    similarity: float  # Cosine similarity thô ∈ [-1, 1]
    score: float       # Điểm đã hiệu chỉnh ∈ [0, 100], lưu vào Application.semantic_score


# ── Cosine Similarity ─────────────────────────────────────────────────────────
def cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """
    Cosine similarity giữa 2 vector 1 chiều: cos(θ) = (a · b) / (‖a‖ · ‖b‖).
    Không yêu cầu vector đã chuẩn hóa. Vector 0 (không có thông tin) trả về 0.0.
    """
    a = np.asarray(vec_a, dtype=np.float64).ravel()
    b = np.asarray(vec_b, dtype=np.float64).ravel()
    if a.shape != b.shape:
        raise ValueError(f"Hai vector khác số chiều: {a.shape} vs {b.shape}")
    norm_product = np.linalg.norm(a) * np.linalg.norm(b)
    if norm_product == 0:
        return 0.0
    # clip để loại bỏ sai số dấu phẩy động (VD: 1.0000001)
    return float(np.clip(np.dot(a, b) / norm_product, -1.0, 1.0))


def cosine_similarity_matrix(matrix_a: np.ndarray, matrix_b: np.ndarray) -> np.ndarray:
    """
    Ma trận cosine similarity giữa từng dòng của A (n, d) và từng dòng của B (m, d) → (n, m).
    Dùng cho so khớp nhiều-nhiều (VD: danh sách kỹ năng JD × kỹ năng CV ở Mục 4.7).
    """
    a = np.atleast_2d(np.asarray(matrix_a, dtype=np.float64))
    b = np.atleast_2d(np.asarray(matrix_b, dtype=np.float64))
    if a.shape[1] != b.shape[1]:
        raise ValueError(f"Hai ma trận khác số chiều vector: {a.shape[1]} vs {b.shape[1]}")
    a_norm = np.linalg.norm(a, axis=1, keepdims=True)
    b_norm = np.linalg.norm(b, axis=1, keepdims=True)
    a = np.divide(a, a_norm, out=np.zeros_like(a), where=a_norm != 0)
    b = np.divide(b, b_norm, out=np.zeros_like(b), where=b_norm != 0)
    return np.clip(a @ b.T, -1.0, 1.0)


def similarity_to_score(
    similarity: float,
    floor: Optional[float] = None,
    ceil: Optional[float] = None,
) -> float:
    """
    Hiệu chỉnh tuyến tính cosine similarity về thang 0–100:
        similarity ≤ floor → 0 ; similarity ≥ ceil → 100 ; ở giữa nội suy tuyến tính.
    Làm tròn 2 chữ số thập phân.
    """
    floor = SEMANTIC_SIM_FLOOR if floor is None else floor
    ceil = SEMANTIC_SIM_CEIL if ceil is None else ceil
    if ceil <= floor:
        raise ValueError("SEMANTIC_SIM_CEIL phải lớn hơn SEMANTIC_SIM_FLOOR")
    ratio = (similarity - floor) / (ceil - floor)
    return round(float(np.clip(ratio, 0.0, 1.0)) * 100, 2)


# ── Chuẩn bị văn bản JD ───────────────────────────────────────────────────────
def build_job_text(job: Any) -> str:
    """
    Ghép các trường của tin tuyển dụng (model Job hoặc object có thuộc tính tương tự)
    thành một văn bản để nhúng vector: tiêu đề, mô tả, yêu cầu, kỹ năng bắt buộc & ưu tiên.
    """
    parts = [
        getattr(job, "title", None),
        getattr(job, "description", None),
        _labeled("Yêu cầu", getattr(job, "requirements", None)),
        _labeled("Kỹ năng bắt buộc", _join(getattr(job, "required_skills", None))),
        _labeled("Kỹ năng ưu tiên", _join(getattr(job, "preferred_skills", None))),
    ]
    return "\n".join(p.strip() for p in parts if p and p.strip())


# ── So khớp JD ↔ CV ──────────────────────────────────────────────────────────
def compute_semantic_match(job_text: str, cv_text: str) -> SemanticMatchResult:
    """
    Tính độ tương đồng ngữ nghĩa giữa văn bản JD và văn bản CV.

    Ngoại lệ:
        ValueError: JD hoặc CV rỗng.
        EmbeddingServiceError: Không nạp được mô hình nhúng.
    """
    if not job_text or not job_text.strip():
        raise ValueError("Văn bản JD rỗng, không thể so khớp ngữ nghĩa.")
    if not cv_text or not cv_text.strip():
        raise ValueError("Văn bản CV rỗng, không thể so khớp ngữ nghĩa.")

    job_vector = encode_document(job_text)
    cv_vector = encode_document(cv_text)
    similarity = cosine_similarity(job_vector, cv_vector)
    result = SemanticMatchResult(similarity=round(similarity, 4), score=similarity_to_score(similarity))
    logger.info(f"[SemanticMatching] cosine={result.similarity:.4f} → semantic_score={result.score}")
    return result


def compute_job_cv_match(job: Any, cv_text: str) -> SemanticMatchResult:
    """Tiện ích: so khớp trực tiếp từ đối tượng Job và văn bản CV."""
    return compute_semantic_match(build_job_text(job), cv_text)


# ── Hàm bổ trợ nội bộ ────────────────────────────────────────────────────────
def _join(items: Optional[Iterable[str]]) -> Optional[str]:
    if not items:
        return None
    return ", ".join(str(i).strip() for i in items if str(i).strip())


def _labeled(label: str, value: Optional[str]) -> Optional[str]:
    return f"{label}: {value}" if value and value.strip() else None
