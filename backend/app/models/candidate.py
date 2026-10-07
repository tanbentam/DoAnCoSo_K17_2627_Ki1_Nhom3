"""
models/candidate.py — SQLAlchemy ORM model cho hồ sơ ứng viên
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Candidate(Base):
    """
    Bảng `candidates` — Lưu thông tin ứng viên nộp hồ sơ.

    Columns:
        id          : Khoá chính tự tăng.
        full_name   : Họ tên đầy đủ của ứng viên.
        email       : Email liên hệ (unique — mỗi email chỉ được tạo 1 hồ sơ).
        phone       : Số điện thoại liên hệ (tuỳ chọn).
        cv_file_path: Đường dẫn tương đối đến file PDF CV đã lưu trên server.
        cv_text_raw : Văn bản thô trích xuất từ PDF — dùng cho AI pipeline.
        created_at  : Thời điểm tạo hồ sơ (UTC, tự động).
        updated_at  : Thời điểm cập nhật cuối (UTC, tự động cập nhật).
    """

    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )

    full_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        comment="Họ tên đầy đủ của ứng viên",
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="Email liên hệ — unique per candidate",
    )

    phone: Mapped[Optional[str]] = mapped_column(
        String(30),
        nullable=True,
        comment="Số điện thoại liên hệ (tuỳ chọn)",
    )

    cv_file_path: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
        comment="Đường dẫn tương đối tới file CV, VD: uploads/cv/abc123.pdf",
    )

    cv_text_raw: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Văn bản thô trích xuất từ PDF CV — input cho AI pipeline",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Thời điểm tạo hồ sơ (UTC)",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Thời điểm cập nhật cuối (UTC)",
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    applications: Mapped[list["Application"]] = relationship(  # type: ignore[name-defined]
        "Application",
        back_populates="candidate",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Candidate id={self.id} email={self.email!r}>"

