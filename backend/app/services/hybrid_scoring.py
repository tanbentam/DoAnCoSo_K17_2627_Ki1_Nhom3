"""
services/hybrid_scoring.py — Thuật toán Hybrid Matching Score: 40% Hard Filter + 60% Semantic Match

    matching_score = HYBRID_HARD_FILTER_WEIGHT × hard_filter_score + HYBRID_SEMANTIC_WEIGHT × semantic_score

Hard Filter (0–100) — tiêu chí cứng trong JD:
    - 60% Kỹ năng bắt buộc  (required_skills): tỷ lệ kỹ năng JD tìm thấy ở ứng viên.
    - 25% Kinh nghiệm       (experience_years_min): min(số năm của ứng viên / số năm yêu cầu, 1).
    - 15% Kỹ năng ưu tiên   (preferred_skills).
  Tiêu chí không áp dụng được (JD không có kỹ năng ưu tiên, không rõ số năm kinh nghiệm...)
  được loại ra và chia lại trọng số cho các tiêu chí còn lại.

So khớp kỹ năng 4 tầng (từ chặt đến lỏng), mỗi kỹ năng JD dừng ở tầng đầu tiên khớp:
    1. exact    — trùng sau chuẩn hóa: "ReactJS" = "React.js" = "react", "HTML5" = "HTML", "Vue 3" = "VueJS".
    2. alias    — từ điển đồng nghĩa: "Golang" = "Go", "k8s" = "Kubernetes", "Làm việc nhóm" = "Teamwork".
    3. text     — tên kỹ năng xuất hiện nguyên văn trong văn bản CV (bắt kỹ năng Gemini bỏ sót).
    4. semantic — cosine giữa vector tên kỹ năng ≥ SKILL_SEMANTIC_THRESHOLD (0.80).
  Ngưỡng 0.80 chọn theo đo đạc: "MySQL ~ Cơ sở dữ liệu MySQL" = 0.90, "Teamwork ~ Làm việc nhóm" = 0.84
  được chấp nhận; "MySQL ~ SQL Server" = 0.70, "Java ~ JavaScript" = 0.44 bị loại.
  (Không thể chỉ dùng embedding vì "VueJS ~ Vue 3" chỉ đạt 0.64 thấp hơn cả cặp khác nhau MySQL ~ SQL Server.)
"""

import logging
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from app.core.config import (
    HYBRID_HARD_FILTER_WEIGHT,
    HYBRID_SEMANTIC_WEIGHT,
    SKILL_SEMANTIC_THRESHOLD,
)
from app.services.embedding_service import EmbeddingServiceError, encode_texts
from app.services.semantic_matching import cosine_similarity_matrix

logger = logging.getLogger(__name__)

# Trọng số các tiêu chí trong Hard Filter (tổng = 1.0)
REQUIRED_SKILLS_WEIGHT = 0.60
EXPERIENCE_WEIGHT = 0.25
PREFERRED_SKILLS_WEIGHT = 0.15

# Từ điển đồng nghĩa: khóa chuẩn hóa → khóa chính tắc
SKILL_ALIASES: Dict[str, str] = {
    "golang": "go",
    "js": "javascript",
    "ecmascript": "javascript",
    "ts": "typescript",
    "k8s": "kubernetes",
    "postgres": "postgresql",
    "psql": "postgresql",
    "mongo": "mongodb",
    "py": "python",
    "csharp": "c#",
    "cplusplus": "c++",
    "cpp": "c++",
    "dotnet": ".net",
    "net": ".net",
    "aspnet": ".net",
    "restful": "restapi",
    "restfulapi": "restapi",
    "restapis": "restapi",
    "rest": "restapi",
    "ml": "machinelearning",
    "họcmáy": "machinelearning",
    "ai": "artificialintelligence",
    "tríthôngminhnhântạo": "artificialintelligence",
    "amazonwebservices": "aws",
    "googlecloud": "gcp",
    "googlecloudplatform": "gcp",
    "msexcel": "excel",
    "microsoftexcel": "excel",
    "làmviệcnhóm": "teamwork",
    "teamworking": "teamwork",
    "giaotiếp": "communication",
    "communicationskills": "communication",
    "tailwindcss": "tailwind",
    "springboot": "spring",
    "springframework": "spring",
}


# ── Cấu trúc kết quả ─────────────────────────────────────────────────────────
@dataclass
class SkillMatch:
    skill: str                          # Tên kỹ năng trong JD
    matched: bool
    match_type: Optional[str] = None    # exact | alias | text | semantic
    matched_with: Optional[str] = None  # Kỹ năng/cụm từ tương ứng của ứng viên
    similarity: Optional[float] = None  # Chỉ có với match_type = semantic


@dataclass
class HardFilterResult:
    score: float                                  # 0–100
    required_skills_score: Optional[float]        # 0–100, None nếu JD không có kỹ năng bắt buộc
    preferred_skills_score: Optional[float]
    experience_score: Optional[float]             # None nếu không xác định được
    candidate_experience_years: Optional[float]
    required_experience_years: int
    required_matches: List[SkillMatch] = field(default_factory=list)
    preferred_matches: List[SkillMatch] = field(default_factory=list)

    @property
    def matched_skills(self) -> List[str]:
        """Kỹ năng JD (bắt buộc + ưu tiên) ứng viên đáp ứng."""
        return [m.skill for m in self.required_matches + self.preferred_matches if m.matched]

    @property
    def missing_skills(self) -> List[str]:
        """Kỹ năng bắt buộc của JD ứng viên còn thiếu."""
        return [m.skill for m in self.required_matches if not m.matched]

    @property
    def missing_preferred_skills(self) -> List[str]:
        return [m.skill for m in self.preferred_matches if not m.matched]


@dataclass
class HybridScoreResult:
    matching_score: Optional[float]   # 0–100, None nếu không có thành phần nào
    hard_filter_score: float
    semantic_score: Optional[float]
    hard_filter: HardFilterResult

    def to_details(self) -> Dict[str, Any]:
        """Chi tiết chấm điểm dạng JSON (lưu kèm ai_extracted_info để HR xem giải thích điểm)."""
        hf = self.hard_filter
        return {
            "formula": f"{HYBRID_HARD_FILTER_WEIGHT:g} × hard_filter + {HYBRID_SEMANTIC_WEIGHT:g} × semantic",
            "matching_score": self.matching_score,
            "hard_filter_score": self.hard_filter_score,
            "semantic_score": self.semantic_score,
            "required_skills_score": hf.required_skills_score,
            "preferred_skills_score": hf.preferred_skills_score,
            "experience_score": hf.experience_score,
            "candidate_experience_years": hf.candidate_experience_years,
            "required_experience_years": hf.required_experience_years,
            "missing_preferred_skills": hf.missing_preferred_skills,
            "skill_matches": [asdict(m) for m in hf.required_matches + hf.preferred_matches],
        }


# ── Chuẩn hóa & so khớp kỹ năng ──────────────────────────────────────────────
def normalize_skill(skill: str) -> str:
    """
    Đưa tên kỹ năng về khóa so sánh:
    "React.js" / "ReactJS" / "react" → "react" ; "HTML5" → "html" ; "Vue 3" → "vue" ;
    "Node.js" → "node" ; "C#" giữ "c#" ; "Golang" → "go" (qua từ điển alias).
    """
    key = _base_key(skill)
    return SKILL_ALIASES.get(key, key)


def _base_key(skill: str) -> str:
    """Khóa chuẩn hóa cách viết (chưa áp dụng từ điển alias)."""
    key = re.sub(r"[\s\-_./]+", "", (skill or "").casefold())  # bỏ khoảng trắng, gạch, chấm
    if len(key) > 3:
        key = re.sub(r"(?<=[^\d])v?\d+$", "", key)             # bỏ số phiên bản: html5, vue3, python3 (giữ es6, s3)
    if len(key) > 4 and key.endswith("js"):
        key = key[:-2]                                         # reactjs → react, vuejs → vue
    return key


def _found_in_text(skill: str, text: str) -> bool:
    """Tìm tên kỹ năng nguyên văn trong văn bản CV (không phân biệt hoa thường, đúng ranh giới từ)."""
    if not skill.strip() or not text:
        return False
    pattern = r"(?<![\w+#])" + re.escape(skill.strip()) + r"(?![\w+#])"
    return re.search(pattern, text, flags=re.IGNORECASE) is not None


def match_skills(
    jd_skills: Sequence[str],
    cv_skills: Sequence[str],
    cv_text: Optional[str] = None,
    use_semantic: bool = True,
    semantic_threshold: Optional[float] = None,
) -> List[SkillMatch]:
    """So khớp từng kỹ năng JD với danh sách kỹ năng ứng viên theo 4 tầng (xem docstring module)."""
    threshold = SKILL_SEMANTIC_THRESHOLD if semantic_threshold is None else semantic_threshold
    cv_skills = [s for s in (cv_skills or []) if isinstance(s, str) and s.strip()]
    cv_by_key: Dict[str, str] = {}
    for s in cv_skills:
        cv_by_key.setdefault(normalize_skill(s), s)

    results: List[SkillMatch] = []
    pending: List[int] = []  # vị trí các kỹ năng JD chưa khớp, chờ so khớp ngữ nghĩa
    for jd_skill in jd_skills or []:
        if not isinstance(jd_skill, str) or not jd_skill.strip():
            continue
        jd_skill = jd_skill.strip()
        key = normalize_skill(jd_skill)
        if key in cv_by_key:
            cv_skill = cv_by_key[key]
            # Khác khóa cách viết nhưng cùng khóa alias → khớp nhờ từ điển đồng nghĩa
            match_type = "alias" if _base_key(jd_skill) != _base_key(cv_skill) else "exact"
            results.append(SkillMatch(jd_skill, True, match_type, cv_skill))
        elif cv_text and _found_in_text(jd_skill, cv_text):
            results.append(SkillMatch(jd_skill, True, "text", jd_skill))
        else:
            results.append(SkillMatch(jd_skill, False))
            pending.append(len(results) - 1)

    if use_semantic and pending and cv_skills:
        _apply_semantic_matches(results, pending, cv_skills, threshold)
    return results


def _apply_semantic_matches(
    results: List[SkillMatch],
    pending: List[int],
    cv_skills: List[str],
    threshold: float,
) -> None:
    """Tầng 4: so khớp ngữ nghĩa các kỹ năng JD còn thiếu với kỹ năng ứng viên bằng embedding."""
    try:
        jd_vectors = encode_texts([results[i].skill for i in pending])
        cv_vectors = encode_texts(cv_skills)
    except EmbeddingServiceError as e:
        logger.warning(f"[HybridScoring] Bỏ qua so khớp kỹ năng ngữ nghĩa: {e}")
        return

    sims = cosine_similarity_matrix(jd_vectors, cv_vectors)
    cv_keys = [_base_key(s) for s in cv_skills]
    for row, idx in enumerate(pending):
        jd_key = _base_key(results[idx].skill)
        best, best_sim = None, threshold
        for col, sim in enumerate(sims[row]):
            # Kỹ năng ứng viên là khái niệm rộng hơn nằm trong tên kỹ năng JD (VD: CV "SQL" vs JD "SQLAlchemy",
            # cosine 0.85) không đáp ứng được yêu cầu cụ thể → bỏ qua. Chiều ngược lại vẫn hợp lệ
            # (CV "Redis Cache" đáp ứng JD "Redis").
            if cv_keys[col] and cv_keys[col] != jd_key and cv_keys[col] in jd_key:
                continue
            if sim >= best_sim:
                best, best_sim = col, float(sim)
        if best is not None:
            results[idx] = SkillMatch(results[idx].skill, True, "semantic", cv_skills[best], round(best_sim, 4))


# ── Các tiêu chí Hard Filter ──────────────────────────────────────────────────
def skills_coverage_score(matches: Sequence[SkillMatch]) -> Optional[float]:
    """Tỷ lệ kỹ năng khớp × 100; None nếu JD không có kỹ năng nào ở nhóm này."""
    if not matches:
        return None
    return round(100.0 * sum(1 for m in matches if m.matched) / len(matches), 2)


def experience_score(candidate_years: Optional[float], required_years: Optional[int]) -> Optional[float]:
    """
    Điểm kinh nghiệm: JD không yêu cầu → 100; không rõ số năm của ứng viên → None (loại khỏi công thức);
    còn lại = min(số năm ứng viên / số năm yêu cầu, 1) × 100.
    """
    required = required_years or 0
    if required <= 0:
        return 100.0
    if candidate_years is None:
        return None
    return round(min(max(float(candidate_years), 0.0) / required, 1.0) * 100, 2)


def _weighted_average(parts: Sequence[tuple]) -> float:
    """Trung bình có trọng số, bỏ qua thành phần None và chia lại trọng số."""
    available = [(score, weight) for score, weight in parts if score is not None]
    total_weight = sum(w for _, w in available)
    if total_weight == 0:
        return 0.0
    return round(sum(s * w for s, w in available) / total_weight, 2)


def compute_hard_filter(
    job: Any,
    extracted_info: Optional[Dict[str, Any]],
    cv_text: Optional[str] = None,
    use_semantic: bool = True,
) -> HardFilterResult:
    """
    Tính điểm Hard Filter từ tin tuyển dụng và thông tin CV do Gemini bóc tách (Mục 4.4).
    Nếu chưa có extracted_info (Gemini lỗi), vẫn so khớp kỹ năng bằng văn bản CV thô.
    """
    info = extracted_info or {}
    cv_skills = list(info.get("skills") or [])
    candidate_years = info.get("experience_years")
    candidate_years = float(candidate_years) if isinstance(candidate_years, (int, float)) else None
    required_years = int(getattr(job, "experience_years_min", 0) or 0)

    required_matches = match_skills(getattr(job, "required_skills", None) or [], cv_skills, cv_text, use_semantic)
    preferred_matches = match_skills(getattr(job, "preferred_skills", None) or [], cv_skills, cv_text, use_semantic)

    required_score = skills_coverage_score(required_matches)
    preferred_score = skills_coverage_score(preferred_matches)
    exp_score = experience_score(candidate_years, required_years)

    score = _weighted_average([
        (required_score, REQUIRED_SKILLS_WEIGHT),
        (exp_score, EXPERIENCE_WEIGHT),
        (preferred_score, PREFERRED_SKILLS_WEIGHT),
    ])
    return HardFilterResult(
        score=score,
        required_skills_score=required_score,
        preferred_skills_score=preferred_score,
        experience_score=exp_score,
        candidate_experience_years=candidate_years,
        required_experience_years=required_years,
        required_matches=required_matches,
        preferred_matches=preferred_matches,
    )


# ── Hybrid Matching Score ─────────────────────────────────────────────────────
def combine_scores(hard_filter_score: Optional[float], semantic_score: Optional[float]) -> Optional[float]:
    """
    matching_score = w_hard × hard_filter + w_semantic × semantic (trọng số chuẩn hóa về tổng 1).
    Thiếu một thành phần (VD: mô hình nhúng lỗi) → dùng thành phần còn lại; thiếu cả hai → None.
    """
    score = _weighted_average([
        (hard_filter_score, HYBRID_HARD_FILTER_WEIGHT),
        (semantic_score, HYBRID_SEMANTIC_WEIGHT),
    ])
    if hard_filter_score is None and semantic_score is None:
        return None
    return round(min(max(score, 0.0), 100.0), 2)


def compute_hybrid_score(
    job: Any,
    extracted_info: Optional[Dict[str, Any]],
    cv_text: Optional[str],
    semantic_score: Optional[float],
    use_semantic_skills: bool = True,
) -> HybridScoreResult:
    """Tính Hybrid Matching Score đầy đủ từ JD, thông tin CV và semantic_score (Mục 4.6)."""
    hard = compute_hard_filter(job, extracted_info, cv_text, use_semantic_skills)
    matching = combine_scores(hard.score, semantic_score)
    logger.info(
        f"[HybridScoring] hard_filter={hard.score} semantic={semantic_score} → matching_score={matching} "
        f"(thiếu: {hard.missing_skills})"
    )
    return HybridScoreResult(
        matching_score=matching,
        hard_filter_score=hard.score,
        semantic_score=semantic_score,
        hard_filter=hard,
    )
