"""
api/applications.py — API quản lý hồ sơ ứng tuyển & Nộp hồ sơ
"""
import os
import uuid
from typing import List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import MAX_UPLOAD_SIZE_MB, UPLOAD_DIR_PATH
from app.core.database import get_db
from app.api.deps import get_current_active_hr
from app.models.application import Application, ApplicationStatus
from app.models.candidate import Candidate
from app.models.job import Job, JobStatus
from app.models.user import User
from app.schemas.application import (
    ApplicationApplyResponse,
    ApplicationResponse,
    ApplicationStatusUpdate,
)

router = APIRouter(prefix="/applications", tags=["Applications"])


@router.post("/apply", response_model=ApplicationApplyResponse, status_code=status.HTTP_201_CREATED)
async def apply_job(
    job_id: int = Form(..., description="ID của tin tuyển dụng"),
    full_name: str = Form(..., max_length=150, description="Họ và tên ứng viên"),
    email: str = Form(..., max_length=255, description="Email liên hệ của ứng viên"),
    phone: Optional[str] = Form(None, max_length=30, description="Số điện thoại liên hệ"),
    cv_file: UploadFile = File(..., description="Tệp CV định dạng PDF hoặc DOCX"),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
):
    """
    API nộp hồ sơ ứng tuyển (Public):
    - Nhận dữ liệu multipart/form-data gồm thông tin ứng viên và tệp CV.
    - Kiểm tra tin tuyển dụng có mở nhận hồ sơ hay không.
    - Kiểm tra định dạng tệp (.pdf, .docx) và kích thước tệp (tối đa 5MB).
    - Lưu tệp CV an toàn vào thư mục cục bộ uploads/cv với tên tệp ngẫu nhiên tránh ghi đè/tấn công path traversal.
    - Tạo hoặc cập nhật thông tin Candidate và tạo bản ghi Application (trạng thái: applied).
    """
    # 1. Kiểm tra Job có tồn tại và đang mở hay không
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tin tuyển dụng không tồn tại",
        )
    if job.status != JobStatus.open:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tin tuyển dụng này đã đóng, không tiếp nhận thêm hồ sơ",
        )

    # 2. Kiểm tra tệp CV đính kèm
    if not cv_file or not cv_file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vui lòng đính kèm tệp CV",
        )

    ext = os.path.splitext(cv_file.filename)[1].lower()
    if ext not in [".pdf", ".docx"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Định dạng tệp không hợp lệ. Hệ thống chỉ hỗ trợ tệp .pdf hoặc .docx",
        )

    # Đọc nội dung tệp và kiểm tra dung lượng
    content = await cv_file.read()
    max_bytes = MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Dung lượng tệp vượt quá giới hạn cho phép ({MAX_UPLOAD_SIZE_MB}MB)",
        )

    # 3. Quản lý Candidate & Kiểm tra nộp trùng
    clean_email = email.strip().lower()
    clean_name = full_name.strip()
    clean_phone = phone.strip() if phone else None

    candidate = db.query(Candidate).filter(Candidate.email == clean_email).first()
    if candidate:
        # Kiểm tra xem ứng viên đã nộp vào job này trước đó chưa
        existing_app = (
            db.query(Application)
            .filter(
                Application.job_id == job_id,
                Application.candidate_id == candidate.id,
            )
            .first()
        )
        if existing_app:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bạn đã nộp hồ sơ ứng tuyển vào vị trí này rồi",
            )
        # Cập nhật thông tin mới nhất
        candidate.full_name = clean_name
        if clean_phone:
            candidate.phone = clean_phone
    else:
        candidate = Candidate(
            full_name=clean_name,
            email=clean_email,
            phone=clean_phone,
        )
        db.add(candidate)
        db.flush()  # Lấy candidate.id

    # 4. Lưu tệp CV an toàn vào uploads/cv
    file_uuid = uuid.uuid4().hex
    safe_filename = f"{file_uuid}_{candidate.id}{ext}"
    dest_path = UPLOAD_DIR_PATH / safe_filename

    with open(dest_path, "wb") as f:
        f.write(content)

    # Cập nhật đường dẫn tệp CV của ứng viên
    relative_cv_path = f"uploads/cv/{safe_filename}"
    candidate.cv_file_path = relative_cv_path

    # 5. Khởi tạo bản ghi Application
    application = Application(
        job_id=job.id,
        candidate_id=candidate.id,
        status=ApplicationStatus.applied,
    )
    db.add(application)
    db.commit()
    db.refresh(application)

    return ApplicationApplyResponse(
        message="Nộp hồ sơ ứng tuyển thành công!",
        application_id=application.id,
        candidate_id=candidate.id,
        job_id=job.id,
        status=application.status,
    )


@router.get("", response_model=List[ApplicationResponse])
def get_applications(
    job_id: Optional[int] = None,
    status_filter: Optional[ApplicationStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_hr),
):
    """
    Lấy danh sách hồ sơ ứng tuyển (chỉ HR/Admin):
    - Có thể lọc theo job_id và status
    """
    query = db.query(Application)
    if job_id is not None:
        query = query.filter(Application.job_id == job_id)
    if status_filter is not None:
        query = query.filter(Application.status == status_filter)
    
    apps = query.order_by(Application.created_at.desc()).all()
    return apps


@router.get("/{application_id}", response_model=ApplicationResponse)
def get_application_detail(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_hr),
):
    """Lấy chi tiết một hồ sơ ứng tuyển (chỉ HR/Admin)."""
    app_record = db.query(Application).filter(Application.id == application_id).first()
    if not app_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy hồ sơ ứng tuyển",
        )
    return app_record


@router.patch("/{application_id}/status", response_model=ApplicationResponse)
def update_application_status(
    application_id: int,
    status_update: ApplicationStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_hr),
):
    """Cập nhật trạng thái Kanban của ứng viên (chỉ HR/Admin)."""
    app_record = db.query(Application).filter(Application.id == application_id).first()
    if not app_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy hồ sơ ứng tuyển",
        )
    app_record.status = status_update.status
    db.commit()
    db.refresh(app_record)
    return app_record

