"""
api/applications.py — API quản lý hồ sơ ứng tuyển & Nộp hồ sơ
"""
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload

from app.core.config import BASE_DIR, MAX_UPLOAD_SIZE_MB, UPLOAD_DIR_PATH
from app.core.database import get_db
from app.api.deps import get_current_active_hr
from app.models.application import Application, ApplicationStatus
from app.models.candidate import Candidate
from app.models.job import Job, JobStatus
from app.models.user import User
from app.schemas.application import (
    ApplicationAIDetailResponse,
    ApplicationApplyResponse,
    ApplicationResponse,
    ApplicationStatusUpdate,
)
from app.schemas.candidate import is_valid_candidate_email
from app.services.ai_tasks import process_application_ai
from app.services.email_notifications import (
    notify_application_received,
    notify_status_changed,
    should_notify_status,
)
from app.services.email_service import is_email_enabled

router = APIRouter(prefix="/applications", tags=["Applications"])


@router.post("/apply", response_model=ApplicationApplyResponse, status_code=status.HTTP_201_CREATED)
async def apply_job(
    job_id: int = Form(..., description="ID của tin tuyển dụng"),
    full_name: str = Form(..., max_length=150, description="Họ và tên ứng viên"),
    email: str = Form(..., max_length=255, description="Email liên hệ của ứng viên"),
    phone: Optional[str] = Form(None, max_length=30, description="Số điện thoại liên hệ"),
    cv_file: UploadFile = File(..., description="Tệp CV định dạng PDF hoặc DOCX"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
):
    """
    API nộp hồ sơ ứng tuyển (Public):
    - Nhận dữ liệu multipart/form-data gồm thông tin ứng viên và tệp CV.
    - Kiểm tra định dạng email (sai trả 422) và tin tuyển dụng có mở nhận hồ sơ hay không.
    - Kiểm tra định dạng tệp (.pdf, .docx) và kích thước tệp (tối đa 5MB).
    - Lưu tệp CV an toàn vào thư mục cục bộ uploads/cv với tên tệp ngẫu nhiên tránh ghi đè/tấn công path traversal.
    - Tạo hoặc cập nhật thông tin Candidate và tạo bản ghi Application (trạng thái: applied).
    """
    # 0. Kiểm tra định dạng email (email sai lưu vào CSDL sẽ làm lỗi API danh sách hồ sơ)
    clean_email = email.strip().lower()
    if not is_valid_candidate_email(clean_email):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Email không hợp lệ, vui lòng kiểm tra lại",
        )

    # 1. Kiểm tra Job có tồn tại và đang mở hay không
    job =db.query(Job).filter(Job.id == job_id).first()
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

    # 6. Tác vụ ngầm (không làm chậm response của ứng viên), chạy lần lượt theo thứ tự thêm vào:
    #    email xác nhận trước (vài giây) rồi mới tới AI chấm điểm (vài chục giây)
    background_tasks.add_task(notify_application_received, application.id)
    background_tasks.add_task(process_application_ai, application.id)

    return ApplicationApplyResponse(
        message="Nộp hồ sơ ứng tuyển thành công!",
        application_id=application.id,
        candidate_id=candidate.id,
        job_id=job.id,
        status=application.status,
        ai_status=application.ai_status,
    )


@router.get("", response_model=List[ApplicationResponse])
def get_applications(
    job_id: Optional[int] = Query(None, description="Lọc theo ID tin tuyển dụng"),
    status: Optional[ApplicationStatus] = Query(None, description="Lọc theo trạng thái Kanban (applied, screening, interview, offer, rejected)"),
    min_score: Optional[float] = Query(None, ge=0.0, le=100.0, description="Lọc điểm matching tối thiểu (0 - 100)"),
    max_score: Optional[float] = Query(None, ge=0.0, le=100.0, description="Lọc điểm matching tối đa (0 - 100)"),
    sort_by: Optional[str] = Query("newest", description="Sắp xếp: 'newest', 'oldest', 'score_desc' (điểm cao đến thấp), 'score_asc'"),
    skip: int = Query(0, ge=0, description="Số bản ghi bỏ qua"),
    limit: int = Query(100, ge=1, le=500, description="Số bản ghi tối đa trả về"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_hr),
):
    """
    Lấy danh sách hồ sơ ứng tuyển (chỉ HR/Admin):
    - job_id: Lọc theo Job cụ thể
    - status: Lọc theo trạng thái Kanban
    - min_score, max_score: Bộ lọc theo dải điểm Matching Score
    - sort_by: Sắp xếp theo ngày ('newest', 'oldest') hoặc điểm số ('score_desc', 'score_asc')
    """
    query = db.query(Application).options(joinedload(Application.candidate))

    if job_id is not None:
        query = query.filter(Application.job_id == job_id)

    if status is not None:
        query = query.filter(Application.status == status)

    if min_score is not None:
        query = query.filter(Application.matching_score >= min_score)

    if max_score is not None:
        query = query.filter(Application.matching_score <= max_score)

    # Xử lý sắp xếp
    if sort_by == "score_desc":
        # Sắp xếp điểm cao xuống thấp (hồ sơ chưa có điểm xếp cuối)
        query = query.order_by(
            Application.matching_score.is_(None),
            Application.matching_score.desc(),
            Application.created_at.desc(),
        )
    elif sort_by == "score_asc":
        # Sắp xếp điểm thấp lên cao (hồ sơ chưa có điểm xếp cuối)
        query = query.order_by(
            Application.matching_score.is_(None),
            Application.matching_score.asc(),
            Application.created_at.desc(),
        )
    elif sort_by == "oldest":
        query = query.order_by(Application.created_at.asc())
    else:  # newest
        query = query.order_by(Application.created_at.desc())

    apps = query.offset(skip).limit(limit).all()
    return apps


@router.get("/{application_id}", response_model=ApplicationResponse)
def get_application_detail(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_hr),
):
    """
    Lấy chi tiết một hồ sơ ứng tuyển kèm thông tin AI phân tích (chỉ HR/Admin):
    - Đầy đủ thông tin ứng viên (candidate) và tin tuyển dụng (job).
    - Toàn bộ kết quả phân tích AI: điểm số, kỹ năng khớp/thiếu, câu hỏi phỏng vấn.
    """
    app_record = (
        db.query(Application)
        .options(
            joinedload(Application.candidate),
            joinedload(Application.job),
        )
        .filter(Application.id == application_id)
        .first()
    )
    if not app_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy hồ sơ ứng tuyển",
        )
    return app_record


@router.get("/{application_id}/ai-analysis", response_model=ApplicationAIDetailResponse)
def get_application_ai_analysis(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_hr),
):
    """
    API chuyên biệt lấy chi tiết phân tích AI của hồ sơ ứng viên (chỉ HR/Admin):
    - Kỹ năng bóc tách từ CV (ai_extracted_info)
    - Danh sách kỹ năng trùng khớp với JD (matched_skills)
    - Danh sách kỹ năng còn thiếu so với JD (missing_skills)
    - 3 - 5 câu hỏi phỏng vấn gợi ý (interview_questions)
    - Điểm số tổng hợp Hybrid Matching Score và điểm thành phần
    """
    app_record = (
        db.query(Application)
        .options(
            joinedload(Application.candidate),
            joinedload(Application.job),
        )
        .filter(Application.id == application_id)
        .first()
    )
    if not app_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy hồ sơ ứng tuyển",
        )
    return ApplicationAIDetailResponse(
        application_id=app_record.id,
        job_id=app_record.job_id,
        candidate_id=app_record.candidate_id,
        status=app_record.status,
        ai_status=app_record.ai_status,
        ai_error=app_record.ai_error,
        matching_score=app_record.matching_score,
        semantic_score=app_record.semantic_score,
        hard_filter_score=app_record.hard_filter_score,
        ai_extracted_info=app_record.ai_extracted_info,
        matched_skills=app_record.matched_skills or [],
        missing_skills=app_record.missing_skills or [],
        interview_questions=app_record.interview_questions or [],
        ai_summary=app_record.ai_summary,
        candidate_name=app_record.candidate.full_name if app_record.candidate else None,
        job_title=app_record.job.title if app_record.job else None,
    )


_CV_MEDIA_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


@router.get("/{application_id}/cv", response_class=FileResponse)
def download_application_cv(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_hr),
):
    """
    Xem / tải tệp CV gốc của hồ sơ ứng tuyển (chỉ HR/Admin):
    - Trả về tệp PDF (hiển thị trực tiếp trên trình duyệt) hoặc DOCX.
    - Cần header Authorization, nên frontend tải bằng fetch() → Blob → URL.createObjectURL() để mở hoặc nhúng.
    - Lưu ý: mỗi ứng viên lưu một tệp CV mới nhất (nộp lại sẽ thay tệp cũ).
    """
    app_record = (
        db.query(Application)
        .options(joinedload(Application.candidate))
        .filter(Application.id == application_id)
        .first()
    )
    if not app_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy hồ sơ ứng tuyển")

    candidate = app_record.candidate
    if not candidate or not candidate.cv_file_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hồ sơ này không có tệp CV")

    # Chỉ phục vụ tệp nằm trong thư mục uploads/cv (chống path traversal nếu dữ liệu bị sửa)
    upload_root = UPLOAD_DIR_PATH.resolve()
    file_path = (BASE_DIR / candidate.cv_file_path).resolve()
    if upload_root not in file_path.parents or not file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy tệp CV trên máy chủ")

    ext = file_path.suffix.lower()
    safe_name = "".join(c if c.isascii() and (c.isalnum() or c in "-_") else "_" for c in candidate.full_name)
    return FileResponse(
        path=file_path,
        media_type=_CV_MEDIA_TYPES.get(ext, "application/octet-stream"),
        filename=f"CV_{safe_name.strip('_') or candidate.id}{ext}",
        content_disposition_type="inline",
    )


@router.patch("/{application_id}/status", response_model=ApplicationResponse)
def update_application_status(
    application_id: int,
    status_update: ApplicationStatusUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_hr),
):
    """
    Cập nhật trạng thái Kanban của ứng viên khi kéo thả (chỉ HR/Admin):
    - Cho phép chuyển đổi trạng thái giữa: applied, screening, interview, offer, rejected.
    - Sang interview: lưu lịch phỏng vấn interview_at / interview_location (đều tùy chọn).
    - Sang interview / offer / rejected (từ cột khác) và send_email = true: gửi email ngầm cho ứng viên
      (thư mời phỏng vấn, thư trúng tuyển, thư cảm ơn từ chối). Trường email_queued trong response cho biết đã xếp thư hay chưa.
    - Trả về đầy đủ thông tin ứng viên để frontend Kanban cập nhật thẻ ngay lập tức.
    """
    app_record = (
        db.query(Application)
        .options(joinedload(Application.candidate))
        .filter(Application.id == application_id)
        .first()
    )
    if not app_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy hồ sơ ứng tuyển",
        )

    old_status = app_record.status
    new_status = status_update.status

    if new_status == ApplicationStatus.interview:
        interview_at = status_update.interview_at
        if interview_at is not None:
            # CSDL lưu giờ UTC không kèm múi giờ; giờ gửi lên không kèm múi giờ được hiểu là UTC
            if interview_at.tzinfo is not None:
                interview_at = interview_at.astimezone(timezone.utc).replace(tzinfo=None)
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            if interview_at < now - timedelta(minutes=5):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Thời gian phỏng vấn đã qua, vui lòng chọn thời gian sau hiện tại",
                )
        app_record.interview_at = interview_at
        app_record.interview_location = status_update.interview_location

    app_record.status = new_status
    db.commit()
    db.refresh(app_record)

    email_queued = False
    if status_update.send_email and is_email_enabled() and should_notify_status(old_status, new_status):
        background_tasks.add_task(notify_status_changed, app_record.id, new_status)
        email_queued = True

    response = ApplicationResponse.model_validate(app_record, from_attributes=True)
    response.email_queued = email_queued
    return response
