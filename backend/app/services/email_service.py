"""
services/email_service.py — Gửi email tự động qua SMTP (Mục 7.1)

Ba chế độ theo EMAIL_MODE:
- smtp: gửi thật qua SMTP (Gmail + App Password), cổng 587 dùng STARTTLS, cổng 465 dùng SSL.
- file: ghi thư thành tệp .eml vào EMAIL_OUTBOX_DIR (mở bằng Outlook/Thunderbird để xem), dùng khi kiểm thử.
- off : không gửi, chỉ ghi log.

send_email() không bao giờ ném lỗi: được gọi từ BackgroundTasks, gửi thư lỗi chỉ ghi log,
không làm hỏng nghiệp vụ nộp hồ sơ / kéo thả Kanban.
"""
import logging
import re
import smtplib
import ssl
import uuid
from datetime import datetime
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
from pathlib import Path
from typing import Optional

from app.core import config

logger = logging.getLogger(__name__)

EMAIL_MODES = ("smtp", "file", "off")

# Kiểm tra địa chỉ ở mức đủ dùng: có 1 dấu @, không khoảng trắng / xuống dòng (chống chèn header)
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def get_email_mode() -> str:
    mode = config.EMAIL_MODE
    if mode not in EMAIL_MODES:
        logger.warning(f"[Email] EMAIL_MODE={mode!r} không hợp lệ, dùng 'off'.")
        return "off"
    return mode


def is_email_enabled() -> bool:
    return get_email_mode() != "off"


def is_valid_email(address: Optional[str]) -> bool:
    return bool(address) and len(address) <= 255 and bool(_EMAIL_RE.match(address))


def build_message(to: str, subject: str, text: str, html: Optional[str] = None) -> EmailMessage:
    """Tạo thư MIME: bản chữ thường (luôn có) + bản HTML (nếu có)."""
    sender = config.SMTP_USER or "no-reply@smartrecruit.local"
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = formataddr((config.EMAIL_FROM_NAME, sender))
    msg["To"] = to
    msg["Message-ID"] = make_msgid(domain=sender.split("@")[-1])
    msg.set_content(text)
    if html:
        msg.add_alternative(html, subtype="html")
    return msg


def _send_smtp(msg: EmailMessage) -> None:
    if not config.SMTP_USER or not config.SMTP_PASSWORD:
        raise RuntimeError("Chưa cấu hình SMTP_USER / SMTP_PASSWORD trong .env")
    context = ssl.create_default_context()
    timeout = config.SMTP_TIMEOUT_SECONDS
    if config.SMTP_PORT == 465:
        server = smtplib.SMTP_SSL(config.SMTP_HOST, config.SMTP_PORT, timeout=timeout, context=context)
    else:
        server = smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=timeout)
    with server as conn:
        if config.SMTP_PORT != 465:
            conn.starttls(context=context)
        conn.login(config.SMTP_USER, config.SMTP_PASSWORD)
        conn.send_message(msg)


def _save_to_outbox(msg: EmailMessage) -> Path:
    outbox = config.BASE_DIR / config.EMAIL_OUTBOX_DIR
    outbox.mkdir(parents=True, exist_ok=True)
    path = outbox / f"{datetime.now():%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:8]}.eml"
    path.write_bytes(bytes(msg))
    return path


def send_email(to: str, subject: str, text: str, html: Optional[str] = None) -> bool:
    """Gửi một thư theo EMAIL_MODE. Trả về True nếu đã gửi / đã ghi tệp, False nếu bỏ qua hoặc lỗi."""
    mode = get_email_mode()
    if mode == "off":
        logger.info(f"[Email] EMAIL_MODE=off, bỏ qua thư '{subject}'.")
        return False
    if not is_valid_email(to):
        logger.warning(f"[Email] Địa chỉ người nhận không hợp lệ ({to!r}), bỏ qua thư '{subject}'.")
        return False

    try:
        msg = build_message(to, subject, text, html)
        if mode == "file":
            path = _save_to_outbox(msg)
            logger.info(f"[Email] Đã ghi thư '{subject}' gửi {to} vào {path.name} (EMAIL_MODE=file).")
        else:
            _send_smtp(msg)
            logger.info(f"[Email] Đã gửi thư '{subject}' tới {to} qua {config.SMTP_HOST}.")
        return True
    except (smtplib.SMTPException, OSError, RuntimeError, ValueError) as e:
        # OSError gồm lỗi mạng, hết thời gian chờ, lỗi TLS; ValueError khi header có ký tự lạ
        logger.error(f"[Email] Không gửi được thư '{subject}' tới {to}: {type(e).__name__}: {e}")
        return False
