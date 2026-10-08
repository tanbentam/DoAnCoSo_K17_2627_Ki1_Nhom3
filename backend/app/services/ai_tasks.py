"""
services/ai_tasks.py — BackgroundTasks xử lý phân tích và chấm điểm AI ngầm
"""
import logging
from app.core.database import SessionLocal
from app.models.application import Application, ApplicationStatus
from app.services.pdf_service import (
    PDFServiceError,
    extract_text_from_candidate_cv,
)

logger = logging.getLogger(__name__)


def process_application_ai(application_id: int) -> None:
    """
    Hàm tác vụ ngầm (FastAPI BackgroundTasks) được gọi ngay sau khi ứng viên nộp hồ sơ:
    1. Mở session CSDL độc lập cho background worker.
    2. Chuyển trạng thái Application sang 'screening' (đang sàng lọc/chấm điểm).
    3. Trích xuất text CV từ tệp PDF (bằng pdfplumber) và lưu vào candidate.cv_text_raw.
    4. Chuẩn bị dữ liệu đầu vào cho AI Pipeline (Gemini bóc tách & Hybrid scoring).
    5. Cập nhật kết quả phân tích & điểm số vào CSDL một cách bất đồng bộ không làm nghẽn request của ứng viên.
    """
    db = SessionLocal()
    try:
        app_record = db.query(Application).filter(Application.id == application_id).first()
        if not app_record:
            logger.warning(f"[BackgroundTasks] Application ID {application_id} không tồn tại.")
            return

        logger.info(f"[BackgroundTasks] Bắt đầu xử lý AI cho Application ID {application_id}...")

        # 1. Cập nhật trạng thái sang 'screening'
        app_record.status = ApplicationStatus.screening
        db.commit()

        # 2. Trích xuất text CV từ file PDF bằng pdfplumber
        candidate = app_record.candidate
        if candidate and candidate.cv_file_path:
            if candidate.cv_file_path.lower().endswith(".pdf"):
                try:
                    logger.info(f"[BackgroundTasks] Đang trích xuất text PDF từ {candidate.cv_file_path}...")
                    raw_text = extract_text_from_candidate_cv(candidate.cv_file_path)
                    candidate.cv_text_raw = raw_text
                    db.commit()
                    logger.info(
                        f"[BackgroundTasks] Trích xuất thành công {len(raw_text)} ký tự cho Candidate ID {candidate.id}."
                    )
                except PDFServiceError as pe:
                    logger.error(
                        f"[BackgroundTasks] Lỗi khi trích xuất text CV Candidate ID {candidate.id}: {pe}"
                    )
            else:
                logger.info(
                    f"[BackgroundTasks] Tệp CV {candidate.cv_file_path} không phải PDF (bỏ qua pdfplumber)."
                )

        # 3. Hook kết nối AI Pipeline tiếp theo (Gemini Structured Outputs & Hybrid Matching Score)
        # Các bước tiếp theo trong Mục 4:
        # - Làm sạch chuỗi văn bản (Mục 4.2)
        # - Gọi Gemini trích xuất Structured Output JSON (Mục 4.3 & 4.4)
        # - Tính điểm Hybrid Matching Score (Semantic + Hard filter) (Mục 4.5 - 4.7)
        # - Lưu matched_skills, missing_skills, interview_questions, matching_score

        logger.info(f"[BackgroundTasks] Hoàn tất bước đọc PDF và chuyển screening cho Application ID {application_id}.")

    except Exception as e:
        db.rollback()
        logger.error(f"[BackgroundTasks] Lỗi khi xử lý Application ID {application_id}: {str(e)}")
    finally:
        db.close()

