"""Tài khoản dùng chung cho Admin, HR và ứng viên."""

import enum

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.job import Job


class UserRole(str, enum.Enum):
    admin = "admin"
    hr = "hr"
    candidate = "candidate"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True,
    )

    full_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )

    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole),
        nullable=False,
        default=UserRole.candidate,
        server_default=UserRole.candidate.value,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
    )

    # API đăng ký ứng viên luôn đặt False.
    # Giá trị mặc định phía database giữ tương thích tài khoản cũ.
    email_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="1",
    )

    # Liên kết với hồ sơ ứng viên sau khi xác minh email.
    candidate_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey(
            "candidates.id",
            name="fk_users_candidate",
            ondelete="SET NULL",
        ),
        nullable=True,
        unique=True,
    )

    # Lưu salt và mã băm OTP, không lưu OTP nguyên bản.
    verification_hash: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        unique=True,
    )

    verification_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
    )

    verification_sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
    )

    # Số lần nhập sai OTP hiện tại.
    verification_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    # Tăng giá trị này để thu hồi các phiên đăng nhập.
    token_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    jobs: Mapped[list["Job"]] = relationship(
        "Job",
        back_populates="creator",
        foreign_keys="Job.created_by",
    )

    def __repr__(self) -> str:
        return (
            f"<User id={self.id} "
            f"email={self.email!r} role={self.role.value}>"
        )