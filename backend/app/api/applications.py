"""
api/applications.py — API quản lý hồ sơ ứng tuyển & Nộp hồ sơ
"""
import os
import uuid
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
from sqlalchemy.orm import Session, joinedload

from app.core.config import MAX_UPLOAD_SIZE_MB, UPLOAD_DIR_PATH
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
from app.services.ai_tasks import process_application_ai

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

    # 6. Kích hoạt xử lý AI ngầm qua BackgroundTasks (không làm chậm response của ứng viên)
    background_tasks.add_task(process_application_ai, application.id)

    return ApplicationApplyResponse(
        message="Nộp hồ sơ ứng tuyển thành công!",
        application_id=application.id,
        candidate_id=candidate.id,
        job_id=job.id,
        status=application.status,
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


@router.patch("/{application_id}/status", response_model=ApplicationResponse)
def update_application_status(
    application_id: int,
    status_update: ApplicationStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_hr),
):
    """
    Cập nhật trạng thái Kanban của ứng viên khi kéo thả (chỉ HR/Admin):
    - Cho phép chuyển đổi trạng thái giữa: applied, screening, interview, offer, rejected.
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

    app_record.status = status_update.status
    db.commit()
    db.refresh(app_record)
    return app_record

