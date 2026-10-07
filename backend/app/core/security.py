"""
core/security.py — Tiện ích bảo mật: Băm mật khẩu & tạo JWT Token.
"""
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt

from app.core.config import SECRET_KEY

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """So sánh mật khẩu gốc với mã băm SHA-256."""
    return get_password_hash(plain_password) == hashed_password

def get_password_hash(password: str) -> str:
    """Băm mật khẩu bằng SHA-256 (cho phiên bản cơ bản)."""
    return hashlib.sha256(password.encode()).hexdigest()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Tạo JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

