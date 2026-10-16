"""
services/ai_tasks.py — BackgroundTasks xử lý phân tích và chấm điểm AI ngầm
"""
import logging
from app.core.database import SessionLocal
from app.models.application import Application, ApplicationStatus
from app.services.cv_extractor import extract_cv_info
from app.services.embedding_service import EmbeddingServiceError
from app.services.semantic_matching import compute_job_cv_match
from app.services.gemini_service import GeminiServiceError
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
    4. Gemini bóc tách CV thành JSON (họ tên, kỹ năng, kinh nghiệm, học vấn) lưu vào ai_extracted_info.
    5. Tính Cosine Similarity giữa vector JD và vector CV, lưu semantic_score (0–100).
    6. Cập nhật kết quả phân tích & điểm số vào CSDL một cách bất đồng bộ không làm nghẽn request của ứng viên.
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
                    logger.info(f"[BackgroundTasks] Đang trích xuất và làm sạch text PDF từ {candidate.cv_file_path}...")
                    cleaned_text = extract_text_from_candidate_cv(candidate.cv_file_path, clean=True)
                    candidate.cv_text_raw = cleaned_text
                    db.commit()
                    logger.info(
                        f"[BackgroundTasks] Trích xuất & làm sạch thành công {len(cleaned_text)} ký tự cho Candidate ID {candidate.id}."
                    )
                except PDFServiceError as pe:
                    logger.error(
                        f"[BackgroundTasks] Lỗi khi trích xuất text CV Candidate ID {candidate.id}: {pe}"
                    )
            else:
                logger.info(
                    f"[BackgroundTasks] Tệp CV {candidate.cv_file_path} không phải PDF (bỏ qua pdfplumber)."
                )

        # 3. Gemini bóc tách thông tin CV thành JSON chuẩn hóa (Mục 4.4)
        if candidate and candidate.cv_text_raw:
            try:
                logger.info(f"[BackgroundTasks] Đang gửi CV Candidate ID {candidate.id} tới Gemini để bóc tách...")
                extracted = extract_cv_info(candidate.cv_text_raw)
                app_record.ai_extracted_info = extracted.model_dump()
                app_record.ai_summary = extracted.summary or None
                db.commit()
                logger.info(
                    f"[BackgroundTasks] Bóc tách CV thành công: {len(extracted.skills)} kỹ năng, "
                    f"{extracted.experience_years} năm kinh nghiệm (Application ID {application_id})."
                )
            except GeminiServiceError as ge:
                logger.error(f"[BackgroundTasks] Lỗi Gemini khi bóc tách CV Application ID {application_id}: {ge}")
        else:
            logger.info(f"[BackgroundTasks] Không có văn bản CV để bóc tách cho Application ID {application_id}.")

        # 4. Tính độ tương đồng ngữ nghĩa Cosine Similarity giữa vector JD và vector CV (Mục 4.6)
        job = app_record.job
        if job and candidate and candidate.cv_text_raw:
            try:
                semantic = compute_job_cv_match(job, candidate.cv_text_raw)
                app_record.semantic_score = semantic.score
                db.commit()
                logger.info(
                    f"[BackgroundTasks] Semantic match Application ID {application_id}: "
                    f"cosine={semantic.similarity:.4f}, semantic_score={semantic.score}."
                )
            except (EmbeddingServiceError, ValueError) as ee:
                logger.error(f"[BackgroundTasks] Lỗi tính semantic score Application ID {application_id}: {ee}")

        # 5. Hook kết nối các bước tiếp theo trong Mục 4:
        # - Tính điểm Hybrid Matching Score: 40% Hard Filter + 60% Semantic Match (Mục 4.7)
        # - Lưu matched_skills, missing_skills, interview_questions, matching_score

        logger.info(f"[BackgroundTasks] Hoàn tất bóc tách CV & semantic match cho Application ID {application_id}.")

    except Exception as e:
        db.rollback()
        logger.error(f"[BackgroundTasks] Lỗi khi xử lý Application ID {application_id}: {str(e)}")
    finally:
        db.close()

