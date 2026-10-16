"""
services/ai_tasks.py — BackgroundTasks xử lý phân tích và chấm điểm AI ngầm
"""
import logging
from typing import List
from app.core.database import SessionLocal
from app.models.application import AIStatus, Application, ApplicationStatus
from app.services.ai_errors import AIProviderError
from app.services.ai_provider import get_provider_mode
from app.services.cv_extractor import extract_cv_info_detailed
from app.services.embedding_service import EmbeddingServiceError
from app.services.hybrid_scoring import compute_hybrid_score
from app.services.interview_generator import generate_interview_questions
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
    2. Đặt ai_status = processing; chuyển Kanban sang 'screening' nếu hồ sơ vẫn ở 'applied'.
    3. Trích xuất text CV từ tệp PDF (bằng pdfplumber) và lưu vào candidate.cv_text_raw.
    4. AI (Gemini / Ollama theo AI_PROVIDER) bóc tách CV thành JSON (họ tên, kỹ năng, kinh nghiệm, học vấn) lưu vào ai_extracted_info.
    5. Tính Cosine Similarity giữa vector JD và vector CV, lưu semantic_score (0–100).
    6. Tính Hybrid Matching Score (40% Hard Filter + 60% Semantic), lưu matched/missing skills.
    7. AI sinh 3–5 câu hỏi phỏng vấn khai thác kỹ năng còn thiếu, lưu interview_questions.
    8. Chốt ai_status (done | partial | failed) kèm ai_error để frontend biết hồ sơ đã chấm xong chưa.
    Mọi kết quả được ghi vào CSDL bất đồng bộ, không làm nghẽn request nộp hồ sơ của ứng viên.
    """
    db = SessionLocal()
    try:
        app_record = db.query(Application).filter(Application.id == application_id).first()
        if not app_record:
            logger.warning(f"[BackgroundTasks] Application ID {application_id} không tồn tại.")
            return

        logger.info(f"[BackgroundTasks] Bắt đầu xử lý AI cho Application ID {application_id}...")
        errors: List[str] = []  # Các bước AI bị lỗi → ai_status = partial/failed, ai_error cho frontend hiển thị

        # 1. Đánh dấu đang xử lý AI; chuyển Kanban sang 'screening' chỉ khi HR chưa kéo thẻ đi nơi khác
        app_record.ai_status = AIStatus.processing
        app_record.ai_error = None
        if app_record.status == ApplicationStatus.applied:
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
                    errors.append(f"Đọc PDF: {pe}")
                    logger.error(
                        f"[BackgroundTasks] Lỗi khi trích xuất text CV Candidate ID {candidate.id}: {pe}"
                    )
            else:
                errors.append("Định dạng CV chưa hỗ trợ đọc tự động (chỉ hỗ trợ PDF)")
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
                errors.append(f"AI bóc tách CV: {type(ae).__name__}")
                logger.error(f"[BackgroundTasks] Lỗi AI khi bóc tách CV Application ID {application_id}: {ae}")
        else:
            errors.append("Không có văn bản CV để phân tích")
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
                errors.append(f"So khớp ngữ nghĩa: {type(ee).__name__}")
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

        # 6. AI sinh 3–5 câu hỏi phỏng vấn khai thác lỗ hổng kỹ năng (Mục 4.8)
        if job and candidate and (candidate.cv_text_raw or app_record.ai_extracted_info):
            try:
                interview = generate_interview_questions(
                    job=job,
                    extracted_info=app_record.ai_extracted_info,
                    missing_skills=app_record.missing_skills or [],
                    cv_text=candidate.cv_text_raw,
                )
                questions = interview.data.questions
                # Cột interview_questions giữ danh sách chuỗi (API/Kanban hiển thị trực tiếp),
                # chi tiết từng câu (kỹ năng, mục đích, gợi ý đáp án) lưu kèm ai_extracted_info
                app_record.interview_questions = [q.question for q in questions]
                app_record.ai_extracted_info = {
                    **(app_record.ai_extracted_info or {}),
                    "interview_details": {
                        "questions": [q.model_dump() for q in questions],
                        "ai_meta": interview.meta(),
                    },
                }
                db.commit()
                logger.info(
                    f"[BackgroundTasks] Sinh {len(questions)} câu hỏi phỏng vấn bằng {interview.provider}/"
                    f"{interview.model} ({interview.latency_seconds:.1f}s) cho Application ID {application_id}."
                )
            except (AIProviderError, ValueError) as ie:
                errors.append(f"Sinh câu hỏi phỏng vấn: {type(ie).__name__}")
                logger.error(f"[BackgroundTasks] Lỗi sinh câu hỏi phỏng vấn Application ID {application_id}: {ie}")

        # 7. Chốt tiến trình AI: done (đủ bước) | partial (có điểm nhưng thiếu bước) | failed (không có điểm)
        if app_record.matching_score is None:
            app_record.ai_status = AIStatus.failed
        else:
            app_record.ai_status = AIStatus.partial if errors else AIStatus.done
        app_record.ai_error = "; ".join(errors)[:1000] or None
        db.commit()

        logger.info(
            f"[BackgroundTasks] Hoàn tất chấm điểm AI cho Application ID {application_id} "
            f"(ai_status={app_record.ai_status.value}{', lỗi: ' + app_record.ai_error if app_record.ai_error else ''})."
        )

    except Exception as e:
        db.rollback()
        logger.error(f"[BackgroundTasks] Lỗi khi xử lý Application ID {application_id}: {str(e)}")
        _mark_failed(db, application_id, f"Lỗi hệ thống: {type(e).__name__}: {e}")
    finally:
        db.close()


def _mark_failed(db, application_id: int, message: str) -> None:
    """Ghi ai_status = failed khi tác vụ ngầm gặp lỗi không lường trước (không ném lỗi tiếp)."""
    try:
        record = db.query(Application).filter(Application.id == application_id).first()
        if record:
            record.ai_status = AIStatus.failed
            record.ai_error = message[:1000]
            db.commit()
    except Exception as e:  # CSDL cũng lỗi → chỉ ghi log
        db.rollback()
        logger.error(f"[BackgroundTasks] Không ghi được ai_status=failed cho Application ID {application_id}: {e}")
