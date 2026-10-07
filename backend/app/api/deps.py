"""
api/deps.py — FastAPI Dependencies dùng chung (Auth, DB, v.v.)
"""
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import SECRET_KEY
from app.core.database import get_db
from app.core.security import ALGORITHM
from app.models.user import User, UserRole
from app.schemas.token import TokenData

# Chỉ định URL endpoint mà form đăng nhập sẽ gửi dữ liệu (OAuth2)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    """Dependency: Xác thực JWT token và trả về object User hiện tại."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        token_data = TokenData(user_id=int(user_id))
    except (jwt.PyJWTError, ValidationError):
        raise credentials_exception
    
    user = db.query(User).filter(User.id == token_data.user_id).first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user

def get_current_active_hr(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency: Yêu cầu người dùng hiện tại phải có role HR hoặc Admin."""
    if current_user.role not in (UserRole.hr, UserRole.admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )
    return current_user

