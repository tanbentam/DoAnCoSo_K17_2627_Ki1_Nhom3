"""
services/email_notifications.py — Tác vụ ngầm gửi email cho ứng viên (Mục 7.2 – 7.4)

Được gọi qua FastAPI BackgroundTasks sau khi response đã trả về:
- notify_application_received: ứng viên vừa nộp hồ sơ (mẫu 1).
- notify_status_changed      : HR chuyển hồ sơ sang interview / offer / rejected (mẫu 2, 3).
Mỗi hàm mở session CSDL riêng (giống ai_tasks) và không ném lỗi ra ngoài.
"""
import logging

from app.core.database import SessionLocal
from app.models.application import Application, ApplicationStatus
from app.services import email_templates
from app.services.email_service import is_email_enabled, send_email

logger = logging.getLogger(__name__)

# Trạng thái Kanban có gửi email khi HR chuyển hồ sơ sang
EMAIL_STATUSES = (ApplicationStatus.interview, ApplicationStatus.offer, ApplicationStatus.rejected)


def should_notify_status(old_status: ApplicationStatus, new_status: ApplicationStatus) -> bool:
    """Chỉ gửi khi trạng thái thật sự đổi và trạng thái mới cần báo cho ứng viên."""
    return old_status != new_status and new_status in EMAIL_STATUSES


def _load(db, application_id: int):
    record = db.query(Application).filter(Application.id == application_id).first()
    if not record or not record.candidate or not record.job:
        logger.warning(f"[Email] Không gửi được: Application ID {application_id} không tồn tại hoặc thiếu ứng viên/tin.")
        return None
    return record


def notify_application_received(application_id: int) -> None:
    """Mẫu 1 (7.2): xác nhận đã nhận hồ sơ."""
    if not is_email_enabled():
        return
    db = SessionLocal()
    try:
        record = _load(db, application_id)
        if record:
            content = email_templates.application_received(record.candidate.full_name, record.job.title)
            send_email(record.candidate.email, content.subject, content.text, content.html)
    except Exception as e:  # CSDL lỗi cũng không được làm hỏng tác vụ ngầm khác
        logger.error(f"[Email] Lỗi gửi thư xác nhận Application ID {application_id}: {type(e).__name__}: {e}")
    finally:
        db.close()


def notify_status_changed(application_id: int, new_status: ApplicationStatus) -> None:
    """Mẫu 2 (7.3) khi sang interview; mẫu 3 (7.4) khi sang offer / rejected."""
    if not is_email_enabled() or new_status not in EMAIL_STATUSES:
        return
    db = SessionLocal()
    try:
        record = _load(db, application_id)
        if not record:
            return
        name, job_title = record.candidate.full_name, record.job.title
        if new_status == ApplicationStatus.interview:
            content = email_templates.interview_invitation(
                name, job_title, record.interview_at, record.interview_location
            )
        elif new_status == ApplicationStatus.offer:
            content = email_templates.offer_letter(name, job_title)
        else:
            content = email_templates.rejection_letter(name, job_title)
        send_email(record.candidate.email, content.subject, content.text, content.html)
    except Exception as e:
        logger.error(
            f"[Email] Lỗi gửi thư '{new_status.value}' cho Application ID {application_id}: {type(e).__name__}: {e}"
        )
    finally:
        db.close()
