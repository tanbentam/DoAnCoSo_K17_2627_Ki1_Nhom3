"""Xác thực dùng chung cho HR, Admin và ứng viên."""

import hashlib
import hmac
import logging
import secrets
import smtplib
import ssl
import threading
import time

from collections import deque
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from email.utils import format_datetime, make_msgid
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
)

from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.api.deps import (
    TOKEN_AUDIENCE,
    TOKEN_ISSUER,
    get_current_active_candidate,
    get_current_user,
)

from app.core.config import (
    SECRET_KEY,
    SMTP_HOST,
    SMTP_PORT,
    SMTP_USER,
    SMTP_PASSWORD,
)

from app.core.database import get_db
from app.core.security import create_access_token

from app.models.application import Application
from app.models.candidate import Candidate
from app.models.user import User, UserRole

from app.schemas.token import (
    AccountPublic,
    CandidateRegister,
    EmailRequest,
    Token,
    VerifyEmailRequest,
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

logger = logging.getLogger(__name__)

OTP_EXPIRE_MINUTES = 5
OTP_MAX_ATTEMPTS = 5
OTP_RESEND_SECONDS = 60

PASSWORD_ITERATIONS = 600000
ACCESS_TOKEN_HOURS = 8

EMAIL_MESSAGE = (
    "Nếu email có thể sử dụng cho yêu cầu này, "
    "mã OTP 6 chữ số sẽ được gửi. "
    "Mã có hiệu lực 5 phút. "
    "Vui lòng kiểm tra cả thư mục spam."
)

_rate_lock = threading.Lock()
_rate_buckets = {}


# ==================== TIỆN ÍCH ====================

def utc_now():
    """Thời gian UTC dùng cho cột MySQL DateTime."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def limit_requests(
    request: Request,
    action: str,
    email: str,
    per_ip: int,
    per_email: int,
):
    """Giới hạn yêu cầu trong môi trường chạy một process."""
    now = time.monotonic()
    window = 3600

    ip = request.client.host if request.client else "unknown"

    email_digest = hashlib.sha256(
        email.strip().lower().encode("utf-8")
    ).hexdigest()

    limits = [
        (f"{action}:ip:{ip}", per_ip),
        (f"{action}:email:{email_digest}", per_email),
    ]

    with _rate_lock:
        expired = [
            key
            for key, bucket in _rate_buckets.items()
            if not bucket or bucket[-1] <= now - window
        ]

        for key in expired:
            del _rate_buckets[key]

        if len(_rate_buckets) >= 10000:
            raise HTTPException(
                429,
                "Có quá nhiều yêu cầu. Vui lòng thử lại sau.",
            )

        for key, maximum in limits:
            bucket = _rate_buckets.setdefault(key, deque())

            while bucket and bucket[0] <= now - window:
                bucket.popleft()

            if len(bucket) >= maximum:
                raise HTTPException(
                    429,
                    "Có quá nhiều yêu cầu. Vui lòng thử lại sau.",
                )

        for key, _ in limits:
            _rate_buckets[key].append(now)


def hash_account_password(password: str):
    salt = secrets.token_hex(16)

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        PASSWORD_ITERATIONS,
    )

    return (
        f"pbkdf2_sha256${PASSWORD_ITERATIONS}"
        f"${salt}${digest.hex()}"
    )


def verify_account_password(password: str, encoded: str):
    if not isinstance(encoded, str):
        return False

    try:
        if encoded.startswith("pbkdf2_sha256$"):
            algorithm, iterations, salt, expected = encoded.split("$")

            if (
                algorithm != "pbkdf2_sha256"
                or iterations != str(PASSWORD_ITERATIONS)
            ):
                return False

            actual = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                bytes.fromhex(salt),
                int(iterations),
            )

            return hmac.compare_digest(
                actual.hex(),
                expected,
            )

        # Tương thích mật khẩu SHA-256 của tài khoản HR cũ.
        if len(encoded) == 64:
            actual = hashlib.sha256(
                password.encode("utf-8")
            ).hexdigest()

            return hmac.compare_digest(actual, encoded)

        return False

    except (ValueError, TypeError):
        return False


DUMMY_HASH = hash_account_password(
    "not-a-real-account-password"
)


def public_account(user: User):
    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role.value,
        "email_verified": user.email_verified,
    }


def create_login_response(user: User):
    """Cấp phiên đăng nhập sau khi xác thực thành công."""
    now = datetime.now(timezone.utc)

    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "role": user.role.value,
            "ver": user.token_version,
            "aud": TOKEN_AUDIENCE,
            "iss": TOKEN_ISSUER,
            "iat": now,
        },
        expires_delta=timedelta(hours=ACCESS_TOKEN_HOURS),
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role.value,
        "account": public_account(user),
    }


# ==================== OTP EMAIL ====================

def require_email_configuration():
    if not SMTP_HOST or not SMTP_USER or not SMTP_PASSWORD:
        raise HTTPException(
            503,
            "Chưa cấu hình gửi email OTP. Liên hệ quản trị viên.",
        )


def otp_digest(email: str, salt: str, otp: str):
    content = (
        "smartrecruit:verify-email:v1:"
        f"{email.strip().lower()}:{salt}:{otp}"
    )

    return hmac.new(
        SECRET_KEY.encode("utf-8"),
        content.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()[:30]


def assign_verification(user: User):
    """Tạo OTP mới, đồng thời vô hiệu OTP trước đó."""
    otp = f"{secrets.randbelow(1_000_000):06d}"
    salt = secrets.token_hex(16)

    # Tổng 63 ký tự, vừa cột verification_hash VARCHAR(64).
    user.verification_hash = (
        f"{salt}:{otp_digest(user.email, salt, otp)}"
    )

    user.verification_expires_at = (
        utc_now() + timedelta(minutes=OTP_EXPIRE_MINUTES)
    )

    user.verification_sent_at = utc_now()
    user.verification_attempts = 0

    return otp


def matches_verification_otp(user: User, otp: str):
    try:
        salt, expected = user.verification_hash.split(":", 1)

        if len(salt) != 32 or len(expected) != 30:
            return False

        actual = otp_digest(user.email, salt, otp)

        return hmac.compare_digest(actual, expected)

    except (AttributeError, ValueError, TypeError):
        return False


def clear_verification(user: User):
    user.verification_hash = None
    user.verification_expires_at = None


def send_verification_email(email: str, otp: str):
    """Gửi OTP qua SMTP; không ghi mã vào log."""
    try:
        message = EmailMessage()

        message["Subject"] = "Mã OTP xác minh SmartRecruit AI"
        message["From"] = SMTP_USER
        message["To"] = email
        message["Date"] = format_datetime(datetime.now(timezone.utc))
        message["Message-ID"] = make_msgid()

        message.set_content(
            "Xin chào,\n\n"
            "Mã OTP xác minh tài khoản SmartRecruit AI của bạn là:\n\n"
            f"{otp}\n\n"
            f"Mã có hiệu lực trong {OTP_EXPIRE_MINUTES} phút "
            "và chỉ sử dụng một lần.\n"
            "Sau khi xác minh thành công, bạn có thể sử dụng tài khoản.\n\n"
            "Không chia sẻ mã với người khác.\n"
            "Nếu không phải bạn yêu cầu, hãy bỏ qua email này."
        )

        context = ssl.create_default_context()

        # Mật khẩu ứng dụng Gmail thường được sao chép theo nhóm ký tự.
        # Chỉ bỏ khoảng trắng với Gmail; giữ nguyên mật khẩu SMTP khác.
        smtp_password = SMTP_PASSWORD
        if SMTP_HOST.strip().lower() == "smtp.gmail.com":
            smtp_password = "".join(smtp_password.split())

        if SMTP_PORT == 465:
            with smtplib.SMTP_SSL(
                SMTP_HOST,
                SMTP_PORT,
                timeout=20,
                context=context,
            ) as server:
                server.login(SMTP_USER, smtp_password)
                server.send_message(message)
        else:
            with smtplib.SMTP(
                SMTP_HOST,
                SMTP_PORT,
                timeout=20,
            ) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                server.login(SMTP_USER, smtp_password)
                server.send_message(message)

    except Exception as error:
        logger.error(
            "OTP email delivery failed (%s). Check SMTP configuration.",
            type(error).__name__,
        )

        if isinstance(error, smtplib.SMTPAuthenticationError):
            detail = (
                "Không đăng nhập được máy chủ email. "
                "Kiểm tra SMTP_USER và mật khẩu ứng dụng SMTP_PASSWORD."
            )
        elif isinstance(error, smtplib.SMTPRecipientsRefused):
            detail = "Máy chủ email từ chối địa chỉ nhận OTP."
        elif isinstance(error, (smtplib.SMTPException, OSError)):
            detail = (
                "Không gửi được email OTP. "
                "Vui lòng kiểm tra kết nối SMTP và thử lại sau."
            )
        else:
            detail = "Có lỗi khi gửi email OTP. Liên hệ quản trị viên."

        raise HTTPException(status_code=503, detail=detail) from None

    logger.info("OTP email accepted by SMTP server.")


def email_response():
    return {
        "message": EMAIL_MESSAGE,
        "resend_after": OTP_RESEND_SECONDS,
    }


# ==================== ĐĂNG KÝ ====================

@router.post("/register", status_code=202)
def register_candidate(
    data: CandidateRegister,
    request: Request,
    db: Session = Depends(get_db),
):
    require_email_configuration()

    email = str(data.email).strip().lower()

    limit_requests(
        request,
        "register",
        email,
        20,
        3,
    )

    encoded_password = hash_account_password(data.password)

    existing = db.query(User).filter(
        func.lower(User.email) == email
    ).with_for_update().first()

    if existing:
        # Không ghi đè mật khẩu tài khoản đã có.
        # Đăng ký lại tài khoản chưa xác minh cũng gửi OTP, tuân thủ cooldown.
        eligible = (
            existing.role == UserRole.candidate
            and existing.is_active
            and not existing.email_verified
        )
        recently_sent = (
            existing.verification_sent_at
            and existing.verification_sent_at
            > utc_now() - timedelta(seconds=OTP_RESEND_SECONDS)
        )
        if eligible and not recently_sent:
            otp = assign_verification(existing)
            db.commit()
            send_verification_email(email, otp)
        return email_response()

    user = User(
        full_name=data.full_name,
        email=email,
        hashed_password=encoded_password,
        role=UserRole.candidate,
        email_verified=False,
        is_active=True,
        token_version=0,
        verification_attempts=0,
    )

    otp = assign_verification(user)

    db.add(user)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return email_response()

    send_verification_email(email, otp)

    # Chưa cấp token khi tài khoản chưa xác minh OTP.
    return email_response()


# ==================== GỬI LẠI OTP ====================

@router.post("/resend-verification", status_code=202)
def resend_verification(
    data: EmailRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    require_email_configuration()

    email = str(data.email).strip().lower()

    limit_requests(
        request,
        "resend",
        email,
        20,
        6,
    )

    user = db.query(User).filter(
        func.lower(User.email) == email
    ).with_for_update().first()

    eligible = (
        user
        and user.role == UserRole.candidate
        and user.is_active
        and not user.email_verified
    )

    if eligible:
        recently_sent = (
            user.verification_sent_at
            and user.verification_sent_at
            > utc_now() - timedelta(seconds=OTP_RESEND_SECONDS)
        )

        if not recently_sent:
            otp = assign_verification(user)

            db.commit()

            send_verification_email(email, otp)

    return email_response()


# ==================== OTP ĐÚNG → ĐĂNG NHẬP ====================

@router.post("/verify-email", response_model=Token)
def verify_email(
    data: VerifyEmailRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    email = str(data.email).strip().lower()

    limit_requests(
        request,
        "verify",
        email,
        100,
        30,
    )

    # Khóa hàng để kiểm tra OTP và cập nhật số lần thử.
    user = db.query(User).filter(
        func.lower(User.email) == email
    ).with_for_update().first()

    invalid_message = (
        "Mã OTP không hợp lệ hoặc đã hết hạn. "
        "Vui lòng kiểm tra email hoặc yêu cầu mã mới."
    )

    if (
        not user
        or user.role != UserRole.candidate
        or not user.is_active
        or user.email_verified
        or not user.verification_hash
        or not user.verification_expires_at
    ):
        raise HTTPException(400, invalid_message)

    if user.verification_expires_at <= utc_now():
        clear_verification(user)
        db.commit()

        raise HTTPException(400, invalid_message)

    if user.verification_attempts >= OTP_MAX_ATTEMPTS:
        clear_verification(user)
        db.commit()

        raise HTTPException(
            400,
            "Mã OTP đã bị khóa. Vui lòng yêu cầu mã mới.",
        )

    if not matches_verification_otp(user, data.otp):
        user.verification_attempts += 1

        locked = (
            user.verification_attempts >= OTP_MAX_ATTEMPTS
        )

        if locked:
            clear_verification(user)

        db.commit()

        raise HTTPException(
            400,
            (
                "Bạn đã nhập sai OTP 5 lần. Vui lòng yêu cầu mã mới."
                if locked
                else "Mã OTP không đúng. Vui lòng kiểm tra lại."
            ),
        )

    # OTP đúng: liên kết hồ sơ ứng viên theo email đã xác minh.
    candidate = db.query(Candidate).filter(
        func.lower(Candidate.email) == email
    ).with_for_update().first()

    if not candidate:
        candidate = Candidate(
            full_name=user.full_name,
            email=email,
        )

        db.add(candidate)

        try:
            db.flush()
        except IntegrityError:
            db.rollback()

            raise HTTPException(
                409,
                "Dữ liệu vừa thay đổi. Vui lòng thử xác minh lại.",
            )

    user.candidate_id = candidate.id
    user.email_verified = True
    user.verification_attempts = 0

    clear_verification(user)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()

        raise HTTPException(
            409,
            "Không thể liên kết hồ sơ. Liên hệ quản trị viên.",
        )

    # Chỉ cấp token sau khi xác minh và lưu thành công.
    return create_login_response(user)


# ==================== ĐĂNG NHẬP CHUNG ====================

@router.post("/login", response_model=Token)
def login_access_token(
    request: Request,
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    email = form_data.username.strip().lower()

    limit_requests(
        request,
        "login",
        email,
        100,
        15,
    )

    if len(form_data.password) > 128:
        raise HTTPException(
            401,
            "Email hoặc mật khẩu không chính xác.",
        )

    user = db.query(User).filter(
        func.lower(User.email) == email
    ).first()

    correct = verify_account_password(
        form_data.password,
        user.hashed_password if user else DUMMY_HASH,
    )

    if not user or not correct or not user.is_active:
        raise HTTPException(
            401,
            "Email hoặc mật khẩu không chính xác.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if (
        user.role == UserRole.candidate
        and not user.email_verified
    ):
        raise HTTPException(
            403,
            "Vui lòng xác minh email bằng OTP trước khi đăng nhập.",
        )

    # Nâng cấp mật khẩu tài khoản cũ sau khi đăng nhập đúng.
    if not user.hashed_password.startswith("pbkdf2_sha256$"):
        user.hashed_password = hash_account_password(
            form_data.password
        )

        db.commit()

    return create_login_response(user)


# ==================== TÀI KHOẢN HIỆN TẠI ====================

@router.get("/me", response_model=AccountPublic)
def get_me(
    user: User = Depends(get_current_user),
):
    return public_account(user)


# ==================== ĐĂNG XUẤT ====================

@router.post("/logout")
def logout(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db.query(User).filter(
        User.id == user.id
    ).update(
        {
            User.token_version: User.token_version + 1
        },
        synchronize_session=False,
    )

    db.commit()

    return {
        "message": "Đã đăng xuất và thu hồi các phiên đăng nhập."
    }


# ==================== HỒ SƠ CỦA ỨNG VIÊN ====================

@router.get("/me/applications")
def get_my_applications(
    job_id: Optional[int] = Query(None, ge=1),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user: User = Depends(get_current_active_candidate),
    db: Session = Depends(get_db),
):
    if user.candidate_id is None:
        return {
            "items": [],
            "total": 0,
        }

    query = db.query(Application).filter(
        Application.candidate_id == user.candidate_id
    )

    if job_id is not None:
        query = query.filter(
            Application.job_id == job_id
        )

    total = query.count()

    applications = query.options(
        joinedload(Application.job)
    ).order_by(
        Application.created_at.desc(),
        Application.id.desc(),
    ).offset(skip).limit(limit).all()

    return {
        "total": total,
        "items": [
            {
                "application_id": application.id,
                "job_id": application.job_id,
                "job_title": (
                    application.job.title
                    if application.job
                    else "Tin tuyển dụng"
                ),
                "status": application.status.value,
                "created_at": application.created_at,
                "updated_at": application.updated_at,
            }
            for application in applications
        ],
    }
