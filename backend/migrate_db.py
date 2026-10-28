"""
Script cập nhật cấu trúc CSDL cho bảng đã tồn tại (Base.metadata.create_all chỉ tạo bảng mới, không thêm cột).
Chạy lại nhiều lần an toàn: bước nào đã áp dụng sẽ được bỏ qua.

    python migrate_db.py
"""
import os
import sys

from dotenv import load_dotenv

# Thêm thư mục backend vào sys.path để có thể import từ app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load biến môi trường từ .env
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from sqlalchemy import text  # noqa: E402

from app.core.database import engine  # noqa: E402

# (tên bước, câu lệnh kiểm tra đã áp dụng chưa, các câu lệnh thực hiện)
MIGRATIONS = [
    (
        "2026-10-16: thêm applications.ai_status + ai_error (tiến trình xử lý AI cho frontend)",
        "SELECT COUNT(*) FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'applications' AND COLUMN_NAME = 'ai_status'",
        [
            "ALTER TABLE applications "
            "ADD COLUMN ai_status ENUM('pending','processing','done','partial','failed') NOT NULL DEFAULT 'pending' "
            "COMMENT 'Tiến trình AI: pending|processing|done|partial|failed', "
            "ADD COLUMN ai_error TEXT NULL COMMENT 'Mô tả ngắn các bước AI bị lỗi (khi ai_status = partial/failed)', "
            "ADD INDEX ix_applications_ai_status (ai_status)",
            # Điền trạng thái cho hồ sơ cũ dựa trên kết quả đã có
            "UPDATE applications SET ai_status = CASE "
            "WHEN matching_score IS NOT NULL AND interview_questions IS NOT NULL "
            "     AND JSON_LENGTH(interview_questions) > 0 THEN 'done' "
            "WHEN matching_score IS NOT NULL THEN 'partial' "
            "ELSE 'failed' END",
            "UPDATE applications SET ai_error = 'Hồ sơ tạo trước khi có ai_status; chưa đủ kết quả AI' "
            "WHERE ai_status IN ('partial', 'failed')",
        ],
    ),
    (
        "2026-10-23: thêm jobs.location (địa điểm làm việc / chi nhánh, Mục 7.3)",
        "SELECT COUNT(*) FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'jobs' AND COLUMN_NAME = 'location'",
        [
            "ALTER TABLE jobs ADD COLUMN location VARCHAR(255) NULL "
            "COMMENT 'Địa điểm làm việc / chi nhánh' AFTER experience_years_min",
        ],
    ),
    (
        "2026-10-23: thêm applications.interview_at + interview_location (lịch phỏng vấn, Mục 7.3)",
        "SELECT COUNT(*) FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'applications' AND COLUMN_NAME = 'interview_at'",
        [
            "ALTER TABLE applications "
            "ADD COLUMN interview_at DATETIME NULL COMMENT 'Thời gian phỏng vấn (UTC), NULL = HR sẽ liên hệ chốt lịch', "
            "ADD COLUMN interview_location VARCHAR(255) NULL COMMENT 'Địa điểm hoặc link phỏng vấn online'",
        ],
    ),
]


def migrate():
    print("Đang kết nối đến CSDL Aiven MySQL...")
    with engine.begin() as conn:
        for name, check_sql, statements in MIGRATIONS:
            if conn.execute(text(check_sql)).scalar():
                print(f"⏭️  Đã áp dụng: {name}")
                continue
            for sql in statements:
                conn.execute(text(sql))
            print(f"✅ Áp dụng: {name}")
        rows = conn.execute(text("SELECT ai_status, COUNT(*) FROM applications GROUP BY ai_status")).fetchall()
        print("   Thống kê ai_status:", {status: count for status, count in rows})


if __name__ == "__main__":
    migrate()
