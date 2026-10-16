"""
services/ai_tasks.py — BackgroundTasks xử lý phân tích và chấm điểm AI ngầm
"""
import logging
from app.core.database import SessionLocal
from app.models.application import Application, ApplicationStatus
from app.services.ai_errors import AIProviderError
from app.services.ai_provider import get_provider_mode
from app.services.cv_extractor import extract_cv_info_detailed
from app.services.embedding_service import EmbeddingServiceError
from app.services.hybrid_scoring import compute_hybrid_score
from app.services.semantic_matching import compute_job_cv_match
from app.services.pdf_service import (
    PDFServiceError,
    extract_text_from_candidate_cv,
    get_pdf_document_date,
)

logger = logging.getLogger(__name__)


def process_application_ai(application_id: int) -> None:
    """
    Hàm tác vụ ngầm (FastAPI BackgroundTasks) được gọi ngay sau khi ứng viên nộp hồ sơ:
    1. Mở session CSDL độc lập cho background worker.
    2. Chuyển trạng thái Application sang 'screening' (đang sàng lọc/chấm điểm).
    3. Trích xuất text CV từ tệp PDF (bằng pdfplumber) và lưu vào candidate.cv_text_raw.
    4. AI (Gemini / Ollama theo AI_PROVIDER) bóc tách CV thành JSON (họ tên, kỹ năng, kinh nghiệm, học vấn) lưu vào ai_extracted_info.
    5. Tính Cosine Similarity giữa vector JD và vector CV, lưu semantic_score (0–100).
    6. Tính Hybrid Matching Score (40% Hard Filter + 60% Semantic), lưu matched/missing skills.
    7. Cập nhật kết quả phân tích & điểm số vào CSDL một cách bất đồng bộ không làm nghẽn request của ứng viên.
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

        # 3. AI bóc tách thông tin CV thành JSON chuẩn hóa (Mục 4.4) — Gemini hoặc Ollama theo AI_PROVIDER (Mục 4.10)
        if candidate and candidate.cv_text_raw:
            try:
                logger.info(
                    f"[BackgroundTasks] Đang bóc tách CV Candidate ID {candidate.id} (AI_PROVIDER={get_provider_mode()})..."
                )
                # Ngày lập CV (metadata PDF) làm mốc "present" để CV cũ không bị tính dư kinh nghiệm (Issues/05)
                reference_date = None
                if candidate.cv_file_path and candidate.cv_file_path.lower().endswith(".pdf"):
                    reference_date = get_pdf_document_date(candidate.cv_file_path)
                result = extract_cv_info_detailed(candidate.cv_text_raw, reference_date=reference_date)
                extracted = result.data
                experience_details = result.extras.get("experience_details", {})
                # ai_meta: nhà cung cấp/model đã sinh kết quả, phục vụ truy vết và trình bày kiến trúc Hybrid
                app_record.ai_extracted_info = {
                    **extracted.model_dump(),
                    "experience_details": experience_details,
                    "ai_meta": result.meta(),
                }
                app_record.ai_summary = extracted.summary or None
                db.commit()
                logger.info(
                    f"[BackgroundTasks] Bóc tách CV thành công bằng {result.provider}/{result.model} "
                    f"({result.latency_seconds:.1f}s): {len(extracted.skills)} kỹ năng, "
                    f"{extracted.experience_years} năm kinh nghiệm (Application ID {application_id})."
                )
            except AIProviderError as ae:
                logger.error(f"[BackgroundTasks] Lỗi AI khi bóc tách CV Application ID {application_id}: {ae}")
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

        # 5. Hybrid Matching Score: 40% Hard Filter + 60% Semantic Match (Mục 4.7)
        if job and candidate and (candidate.cv_text_raw or app_record.ai_extracted_info):
            hybrid = compute_hybrid_score(
                job=job,
                extracted_info=app_record.ai_extracted_info,
                cv_text=candidate.cv_text_raw,
                semantic_score=app_record.semantic_score,
            )
            app_record.hard_filter_score = hybrid.hard_filter_score
            app_record.matching_score = hybrid.matching_score
            app_record.matched_skills = hybrid.hard_filter.matched_skills
            app_record.missing_skills = hybrid.hard_filter.missing_skills
            # Gán dict mới để SQLAlchemy nhận biết thay đổi trên cột JSON
            app_record.ai_extracted_info = {
                **(app_record.ai_extracted_info or {}),
                "scoring_details": hybrid.to_details(),
            }
            db.commit()
            logger.info(
                f"[BackgroundTasks] Hybrid score Application ID {application_id}: matching={hybrid.matching_score} "
                f"(hard={hybrid.hard_filter_score}, semantic={hybrid.semantic_score})."
            )

        # 6. Hook kết nối các bước tiếp theo trong Mục 4:
        # - Gemini sinh 3–5 câu hỏi phỏng vấn khai thác kỹ năng còn thiếu (Mục 4.8) → interview_questions

        logger.info(f"[BackgroundTasks] Hoàn tất chấm điểm AI cho Application ID {application_id}.")

    except Exception as e:
        db.rollback()
        logger.error(f"[BackgroundTasks] Lỗi khi xử lý Application ID {application_id}: {str(e)}")
    finally:
        db.close()

