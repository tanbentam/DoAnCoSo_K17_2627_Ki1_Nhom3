"""
models/user.py — SQLAlchemy ORM model cho tài khoản HR / Quản trị viên
"""
import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserRole(str, enum.Enum):
    """Vai trò người dùng trong hệ thống."""
    admin = "admin"
    hr = "hr"


class User(Base):
    """
    Bảng `users` — Lưu thông tin tài khoản HR / Quản trị viên.

    Columns:
        id          : Khoá chính tự tăng.
        full_name   : Họ tên đầy đủ.
        email       : Email đăng nhập (unique, không phân biệt hoa thường).
        hashed_password: Mật khẩu đã băm (bcrypt hoặc tương đương).
        role        : Vai trò — admin | hr.
        is_active   : Tài khoản đang hoạt động (soft-delete).
        created_at  : Thời điểm tạo tài khoản (UTC, tự động).
        updated_at  : Thời điểm cập nhật cuối (UTC, tự động cập nhật).
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)

    full_name: Mapped[str] = mapped_column(String(150), nullable=False)

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="Email đăng nhập — phải là duy nhất trong hệ thống",
    )

    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Mật khẩu đã băm, KHÔNG lưu plaintext",
    )

    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole),
        nullable=False,
        default=UserRole.hr,
        server_default=UserRole.hr.value,
        comment="Vai trò: admin hoặc hr",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
        comment="False = tài khoản bị vô hiệu hoá (soft-delete)",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Thời điểm tạo tài khoản (UTC)",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Thời điểm cập nhật cuối (UTC)",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} role={self.role.value}>"
