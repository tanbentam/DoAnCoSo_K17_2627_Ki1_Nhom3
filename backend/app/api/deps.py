"""Xác thực dùng chung, phân quyền riêng theo vai trò."""

import jwt

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import SECRET_KEY
from app.core.database import get_db
from app.core.security import ALGORITHM
from app.models.user import User, UserRole


TOKEN_AUDIENCE = "smartrecruit-web"
TOKEN_ISSUER = "smartrecruit"

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login"
)


def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
) -> User:
    unauthorized = HTTPException(
        status_code=401,
        detail="Phiên đăng nhập đã hết hạn hoặc không hợp lệ.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            audience=TOKEN_AUDIENCE,
            issuer=TOKEN_ISSUER,
            options={
                "require": [
                    "sub",
                    "role",
                    "ver",
                    "aud",
                    "iss",
                    "iat",
                    "exp",
                ]
            },
        )

        user_id = int(payload["sub"])

        if user_id <= 0:
            raise unauthorized

    except (jwt.PyJWTError, ValueError, TypeError, KeyError):
        raise unauthorized

    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if (
        not user
        or not user.is_active
        or payload["ver"] != user.token_version
        or payload["role"] != user.role.value
    ):
        raise unauthorized

    if (
        user.role == UserRole.candidate
        and not user.email_verified
    ):
        raise HTTPException(
            status_code=403,
            detail="Vui lòng xác minh email trước khi sử dụng tài khoản.",
        )

    return user


def get_current_active_hr(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role not in (
        UserRole.hr,
        UserRole.admin,
    ):
        raise HTTPException(
            status_code=403,
            detail="Chức năng này chỉ dành cho HR hoặc quản trị viên.",
        )

    return current_user


def get_current_active_candidate(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != UserRole.candidate:
        raise HTTPException(
            status_code=403,
            detail="Chức năng này chỉ dành cho ứng viên.",
        )

    return current_user