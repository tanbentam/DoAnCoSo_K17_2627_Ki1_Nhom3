"""
models/application.py — SQLAlchemy ORM model cho hồ sơ ứng tuyển

Liên kết Job ↔ Candidate, lưu trạng thái Kanban,
Matching Score và toàn bộ kết quả phân tích AI.
"""
import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ApplicationStatus(str, enum.Enum):
    """Trạng thái ứng viên trên bảng Kanban."""
    applied    = "applied"     # Vừa nộp hồ sơ
    screening  = "screening"   # Đang sàng lọc / AI đang chấm
    interview  = "interview"   # Đã mời phỏng vấn
    offer      = "offer"       # Đã gửi offer
    rejected   = "rejected"    # Đã từ chối


class Application(Base):
    """
    Bảng `applications` — Liên kết Job ↔ Candidate, trung tâm của ATS.

    Columns:
        id              : Khoá chính tự tăng.
        job_id          : FK → jobs.id.
        candidate_id    : FK → candidates.id.
        status          : Trạng thái Kanban: applied|screening|interview|offer|rejected.
        matching_score  : Điểm tổng hợp Hybrid AI (0.0 – 100.0), NULL nếu chưa chấm.
        semantic_score  : Điểm Cosine Similarity (60% trọng số).
        hard_filter_score: Điểm lọc cứng kỹ năng/kinh nghiệm (40% trọng số).
        ai_extracted_info: JSON — thông tin CV do Gemini bóc tách (tên, kỹ năng, kinh nghiệm…).
        matched_skills  : JSON array — kỹ năng trùng với JD.
        missing_skills  : JSON array — kỹ năng còn thiếu so với JD.
        interview_questions: JSON array — 3–5 câu hỏi phỏng vấn do AI gợi ý.
        ai_summary      : Đoạn tóm tắt ngắn do AI sinh ra về ứng viên.
        created_at      : Thời điểm nộp hồ sơ (UTC, tự động).
        updated_at      : Thời điểm cập nhật cuối (UTC, tự động cập nhật).
    """

    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )

    # ── Foreign Keys ───────────────────────────────────────────────────────────
    job_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK → jobs.id",
    )

    candidate_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK → candidates.id",
    )

    # ── Kanban ─────────────────────────────────────────────────────────────────
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus),
        nullable=False,
        default=ApplicationStatus.applied,
        server_default=ApplicationStatus.applied.value,
        index=True,
        comment="Trạng thái trên Kanban board",
    )

    # ── AI Scoring ─────────────────────────────────────────────────────────────
    matching_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Điểm Hybrid tổng hợp 0–100 (NULL = chưa chấm)",
    )

    semantic_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Điểm Cosine Similarity của vector JD vs CV (trọng số 60%)",
    )

    hard_filter_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Điểm lọc cứng (kỹ năng + kinh nghiệm, trọng số 40%)",
    )

    # ── AI Analysis Results (JSON) ─────────────────────────────────────────────
    ai_extracted_info: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="JSON Gemini bóc tách: {name, skills, experience_years, education, ...}",
    )

    matched_skills: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
        comment="JSON array kỹ năng ứng viên trùng với JD",
    )

    missing_skills: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
        comment="JSON array kỹ năng còn thiếu so với yêu cầu JD",
    )

    interview_questions: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
        comment="JSON array 3–5 câu hỏi phỏng vấn do AI gợi ý",
    )

    ai_summary: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Đoạn tóm tắt ngắn về ứng viên do AI sinh ra",
    )

    # ── Timestamps ─────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Thời điểm nộp hồ sơ (UTC)",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Thời điểm cập nhật cuối (UTC)",
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    job: Mapped["Job"] = relationship(          # type: ignore[name-defined]
        "Job",
        back_populates="applications",
    )

    candidate: Mapped["Candidate"] = relationship(  # type: ignore[name-defined]
        "Candidate",
        back_populates="applications",
    )

    def __repr__(self) -> str:
        return (
            f"<Application id={self.id} "
            f"job_id={self.job_id} candidate_id={self.candidate_id} "
            f"status={self.status.value} score={self.matching_score}>"
        )

