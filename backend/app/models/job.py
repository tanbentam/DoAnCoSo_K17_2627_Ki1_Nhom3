"""
models/job.py — SQLAlchemy ORM model cho tin tuyển dụng (Job Posting)
"""
import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class JobStatus(str, enum.Enum):
    """Trạng thái của tin tuyển dụng."""
    open = "open"        # Đang mở, nhận hồ sơ
    closed = "closed"    # Đã đóng, không nhận thêm


class Job(Base):
    """
    Bảng `jobs` — Lưu thông tin tin tuyển dụng do HR tạo.

    Columns:
        id                  : Khoá chính tự tăng.
        title               : Tiêu đề vị trí (VD: "Backend Developer – Python").
        description         : Mô tả công việc đầy đủ (JD), plain-text hoặc markdown.
        requirements        : Các yêu cầu bắt buộc (text dài), dùng để tạo vector nhúng JD.
        required_skills     : Danh sách kỹ năng bắt buộc dạng JSON array (VD: ["Python","SQL"]).
        preferred_skills    : Danh sách kỹ năng ưu tiên dạng JSON array (tùy chọn).
        experience_years_min: Số năm kinh nghiệm tối thiểu yêu cầu (mặc định 0).
        status              : Trạng thái tin — open | closed.
        created_by          : FK tới users.id — HR đã tạo tin.
        created_at          : Thời điểm tạo (UTC, tự động).
        updated_at          : Thời điểm cập nhật cuối (UTC, tự động cập nhật).
    """

    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Tiêu đề vị trí tuyển dụng",
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Mô tả công việc đầy đủ (JD) — hiển thị cho ứng viên",
    )

    requirements: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Yêu cầu kỹ năng / kinh nghiệm chi tiết — dùng để tạo vector nhúng JD",
    )

    required_skills: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        comment='Mảng JSON kỹ năng bắt buộc, VD: ["Python", "FastAPI", "MySQL"]',
    )

    preferred_skills: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
        default=None,
        comment='Mảng JSON kỹ năng ưu tiên (không bắt buộc)',
    )

    experience_years_min: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Số năm kinh nghiệm tối thiểu (0 = không yêu cầu)",
    )

    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus),
        nullable=False,
        default=JobStatus.open,
        server_default=JobStatus.open.value,
        index=True,
        comment="Trạng thái tin tuyển dụng: open | closed",
    )

    created_by: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="FK → users.id — HR đã tạo tin này",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Thời điểm tạo tin (UTC)",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Thời điểm cập nhật cuối (UTC)",
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    creator: Mapped[Optional["User"]] = relationship(   # type: ignore[name-defined]
        "User",
        back_populates="jobs",
        foreign_keys=[created_by],
    )

    applications: Mapped[list["Application"]] = relationship(  # type: ignore[name-defined]
        "Application",
        back_populates="job",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Job id={self.id} title={self.title!r} status={self.status.value}>"

