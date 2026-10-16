"""
database.py — SQLAlchemy engine & session factory (Aiven MySQL Cloud, kết nối mã hóa SSL/TLS)

Chế độ SSL (DB_SSL_MODE):
    auto      — (mặc định) có DB_SSL_CA → verify; máy chủ cloud (không phải localhost) → required; localhost → disabled
    verify    — TLS + xác minh chứng chỉ máy chủ bằng CA của Aiven (DB_SSL_CA) + kiểm tra hostname. An toàn nhất.
    required  — TLS mã hóa đường truyền nhưng không xác minh chứng chỉ (chống nghe lén, chưa chống giả mạo máy chủ).
    disabled  — không mã hóa (chỉ dùng cho MySQL cài trên máy local).
"""
import logging
import ssl
from pathlib import Path
from typing import Any, Dict, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import BASE_DIR, DATABASE_URL, DB_SSL_CA, DB_SSL_MODE

logger = logging.getLogger(__name__)

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", None, ""}
VALID_SSL_MODES = ("auto", "verify", "required", "disabled")


def resolve_ssl_mode(host: Optional[str], mode: str, ca_path: Optional[Path]) -> str:
    """Quyết định chế độ SSL thực tế từ cấu hình."""
    mode = (mode or "auto").strip().lower()
    if mode not in VALID_SSL_MODES:
        logger.warning(f"[Database] DB_SSL_MODE='{mode}' không hợp lệ, dùng 'auto'.")
        mode = "auto"
    if mode != "auto":
        return mode
    if ca_path is not None:
        return "verify"
    return "disabled" if host in _LOCAL_HOSTS else "required"


def build_ssl_connect_args(host: Optional[str], mode: str, ca: Optional[str]) -> Dict[str, Any]:
    """
    Tạo connect_args cho PyMySQL theo chế độ SSL.

    Ngoại lệ:
        FileNotFoundError: chế độ verify nhưng không tìm thấy file CA.
    """
    ca_path: Optional[Path] = None
    if ca:
        ca_path = Path(ca)
        if not ca_path.is_absolute():
            ca_path = BASE_DIR / ca_path

    effective = resolve_ssl_mode(host, mode, ca_path)
    if effective == "disabled":
        if host not in _LOCAL_HOSTS:
            logger.warning(f"[Database] ⚠️ Kết nối tới {host} KHÔNG mã hóa SSL (DB_SSL_MODE=disabled).")
        return {}

    if effective == "verify":
        if ca_path is None or not ca_path.exists():
            raise FileNotFoundError(
                f"DB_SSL_MODE=verify nhưng không tìm thấy chứng chỉ CA tại '{ca_path}'. "
                "Tải CA certificate trong Aiven Console → Overview và đặt đường dẫn vào DB_SSL_CA."
            )
        # PyMySQL: có "ca" → verify_mode=CERT_REQUIRED + check_hostname=True
        return {"ssl": {"ca": str(ca_path)}}

    # required: mã hóa TLS, không xác minh chứng chỉ (chưa có CA)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    logger.warning(
        "[Database] Kết nối MySQL có mã hóa TLS nhưng CHƯA xác minh chứng chỉ máy chủ. "
        "Đặt DB_SSL_CA (CA certificate của Aiven) để bật xác minh."
    )
    return {"ssl": ctx}


# Tham số SSL trong query string của DATABASE_URL bị loại bỏ, SSL được quản lý duy nhất qua DB_SSL_MODE.
# Lý do: SQLAlchemy truyền giá trị query dạng chuỗi, nên "?ssl_disabled=false" thành ssl_disabled="false"
# — chuỗi khác rỗng là truthy → PyMySQL TẮT SSL (nguyên nhân docs/Issues/03).
_SSL_QUERY_KEYS = ("ssl_disabled", "ssl-mode", "ssl_mode", "sslmode", "ssl")


def build_engine_url(database_url: str):
    url = make_url(database_url)
    removed = [k for k in _SSL_QUERY_KEYS if k in url.query]
    if removed:
        logger.info(f"[Database] Bỏ qua tham số {removed} trong DATABASE_URL, SSL cấu hình qua DB_SSL_MODE.")
        url = url.difference_update_query(removed)
    return url


_db_url = build_engine_url(DATABASE_URL)

engine = create_engine(
    _db_url,
    connect_args=build_ssl_connect_args(_db_url.host, DB_SSL_MODE, DB_SSL_CA),
    pool_pre_ping=True,
    pool_recycle=300,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


def get_db():
    """FastAPI dependency that provides a DB session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_connection_security() -> Dict[str, Any]:
    """Kiểm tra phiên kết nối hiện tại có được mã hóa không (Ssl_version, Ssl_cipher của MySQL)."""
    with engine.connect() as conn:
        rows = dict(conn.execute(text("SHOW SESSION STATUS WHERE Variable_name IN ('Ssl_version', 'Ssl_cipher')")).fetchall())
    return {
        "encrypted": bool(rows.get("Ssl_cipher")),
        "tls_version": rows.get("Ssl_version") or None,
        "cipher": rows.get("Ssl_cipher") or None,
    }
