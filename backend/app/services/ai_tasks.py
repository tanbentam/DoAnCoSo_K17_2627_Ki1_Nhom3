"""
services/ai_tasks.py — BackgroundTasks xử lý phân tích và chấm điểm AI ngầm
"""
import logging
from app.core.database import SessionLocal
from app.models.application import Application, ApplicationStatus

logger = logging.getLogger(__name__)


def process_application_ai(application_id: int) -> None:
    """
    Hàm tác vụ ngầm (FastAPI BackgroundTasks) được gọi ngay sau khi ứng viên nộp hồ sơ:
    1. Mở session CSDL độc lập cho background worker.
    2. Chuyển trạng thái Application sang 'screening' (đang sàng lọc/chấm điểm).
    3. Đọc tệp CV đã lưu và chuẩn bị dữ liệu đầu vào cho AI Pipeline (Mục 4).
    4. Cập nhật kết quả phân tích & điểm số vào CSDL một cách bất đồng bộ không làm nghẽn request của ứng viên.
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

        # 2. Hook kết nối AI Pipeline (sẽ hoàn thiện tại Mục 4 khi tích hợp pdfplumber & Gemini)
        # Các bước xử lý AI tiếp theo:
        # - Trích xuất text CV từ tệp PDF (pdfplumber)
        # - Gọi Gemini trích xuất Structured Output JSON
        # - Tính điểm Hybrid Matching Score (Semantic + Hard filter)
        # - Lưu matched_skills, missing_skills, interview_questions, matching_score

        logger.info(f"[BackgroundTasks] Hoàn tất chuyển trạng thái screening cho Application ID {application_id}.")

    except Exception as e:
        db.rollback()
        logger.error(f"[BackgroundTasks] Lỗi khi xử lý Application ID {application_id}: {str(e)}")
    finally:
        db.close()

