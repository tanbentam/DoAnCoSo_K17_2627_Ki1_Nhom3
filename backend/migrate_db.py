"""
Cập nhật cấu trúc CSDL MySQL hiện có.

Chạy tại thư mục backend:
    .\\venv\\Scripts\\python.exe -X utf8 migrate_db.py

Không xóa bảng hoặc hồ sơ CV.

MySQL có thể tự commit lệnh ALTER TABLE.
Nếu một bước lỗi, các bước trước đó có thể đã được áp dụng.
Chạy lại sẽ bỏ qua các bước đã hoàn thành.
"""

import sys

from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent

sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import text

# Dùng cùng cấu hình kết nối với backend.
# Không tự nạp thêm một file .env khác tại đây.
from app.core.database import engine


def column_check(table, column):
    return (
        "SELECT COUNT(*) "
        "FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() "
        f"AND TABLE_NAME = '{table}' "
        f"AND COLUMN_NAME = '{column}'"
    )


def index_check(table, name):
    return (
        "SELECT COUNT(*) "
        "FROM information_schema.STATISTICS "
        "WHERE TABLE_SCHEMA = DATABASE() "
        f"AND TABLE_NAME = '{table}' "
        f"AND INDEX_NAME = '{name}'"
    )


MIGRATIONS = [
    # Ưu tiên sửa lỗi đăng ký/đăng nhập hiện tại.
    (
        "users.verification_attempts — số lần nhập sai OTP",
        column_check("users", "verification_attempts"),
        [
            "ALTER TABLE users "
            "ADD COLUMN verification_attempts "
            "INT NOT NULL DEFAULT 0",
        ],
    ),

    # Vai trò ứng viên.
    (
        "users.role — bổ sung candidate",
        "SELECT COUNT(*) "
        "FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() "
        "AND TABLE_NAME = 'users' "
        "AND COLUMN_NAME = 'role' "
        "AND COLUMN_TYPE LIKE '%''candidate''%'",
        [
            "ALTER TABLE users "
            "MODIFY COLUMN role "
            "ENUM('admin','hr','candidate') "
            "NOT NULL DEFAULT 'candidate'",
        ],
    ),

    # Thông tin xác minh tài khoản.
    (
        "users.email_verified",
        column_check("users", "email_verified"),
        [
            "ALTER TABLE users "
            "ADD COLUMN email_verified "
            "TINYINT(1) NOT NULL DEFAULT 1",
        ],
    ),
    (
        "users.verification_hash",
        column_check("users", "verification_hash"),
        [
            "ALTER TABLE users "
            "ADD COLUMN verification_hash VARCHAR(64) NULL",
        ],
    ),
    (
        "users.verification_hash — unique index",
        index_check("users", "uq_users_verification_hash"),
        [
            "ALTER TABLE users "
            "ADD UNIQUE INDEX uq_users_verification_hash "
            "(verification_hash)",
        ],
    ),
    (
        "users.verification_expires_at",
        column_check("users", "verification_expires_at"),
        [
            "ALTER TABLE users "
            "ADD COLUMN verification_expires_at DATETIME NULL",
        ],
    ),
    (
        "users.verification_sent_at",
        column_check("users", "verification_sent_at"),
        [
            "ALTER TABLE users "
            "ADD COLUMN verification_sent_at DATETIME NULL",
        ],
    ),
    (
        "users.token_version",
        column_check("users", "token_version"),
        [
            "ALTER TABLE users "
            "ADD COLUMN token_version INT NOT NULL DEFAULT 0",
        ],
    ),

    # Liên kết tài khoản với hồ sơ ứng viên.
    (
        "users.candidate_id",
        column_check("users", "candidate_id"),
        [
            "ALTER TABLE users "
            "ADD COLUMN candidate_id INT NULL",
        ],
    ),
    (
        "users.candidate_id — unique index",
        index_check("users", "uq_users_candidate_id"),
        [
            "ALTER TABLE users "
            "ADD UNIQUE INDEX uq_users_candidate_id "
            "(candidate_id)",
        ],
    ),
    (
        "users.candidate_id — foreign key",
        "SELECT COUNT(*) "
        "FROM information_schema.KEY_COLUMN_USAGE "
        "WHERE TABLE_SCHEMA = DATABASE() "
        "AND TABLE_NAME = 'users' "
        "AND COLUMN_NAME = 'candidate_id' "
        "AND REFERENCED_TABLE_NAME = 'candidates' "
        "AND REFERENCED_COLUMN_NAME = 'id'",
        [
            "ALTER TABLE users "
            "ADD CONSTRAINT fk_users_candidate "
            "FOREIGN KEY (candidate_id) "
            "REFERENCES candidates(id) "
            "ON DELETE SET NULL",
        ],
    ),

    # Tiến trình AI: kiểm tra riêng từng cột để chạy lại được
    # khi một lần cập nhật trước chưa hoàn tất.
    (
        "applications.ai_status",
        column_check("applications", "ai_status"),
        [
            "ALTER TABLE applications "
            "ADD COLUMN ai_status "
            "ENUM('pending','processing','done','partial','failed') "
            "NOT NULL DEFAULT 'pending'",

            # Chỉ chạy khi vừa bổ sung cột ai_status.
            "UPDATE applications SET ai_status = CASE "
            "WHEN matching_score IS NOT NULL "
            "AND interview_questions IS NOT NULL "
            "AND JSON_LENGTH(interview_questions) > 0 "
            "THEN 'done' "
            "WHEN matching_score IS NOT NULL "
            "THEN 'partial' "
            "ELSE 'failed' END",
        ],
    ),
    (
        "applications.ai_error",
        column_check("applications", "ai_error"),
        [
            "ALTER TABLE applications "
            "ADD COLUMN ai_error TEXT NULL",

            "UPDATE applications "
            "SET ai_error = "
            "'Hồ sơ tạo trước khi có ai_error; chưa đủ kết quả AI' "
            "WHERE ai_status IN ('partial', 'failed') "
            "AND ai_error IS NULL",
        ],
    ),
    (
        "applications.ai_status — index",
        index_check("applications", "ix_applications_ai_status"),
        [
            "ALTER TABLE applications "
            "ADD INDEX ix_applications_ai_status (ai_status)",
        ],
    ),
]


REQUIRED_USER_COLUMNS = {
    "id",
    "full_name",
    "email",
    "hashed_password",
    "role",
    "is_active",
    "email_verified",
    "candidate_id",
    "verification_hash",
    "verification_expires_at",
    "verification_sent_at",
    "verification_attempts",
    "token_version",
    "created_at",
    "updated_at",
}


def ensure_tables(connection):
    for table in ("users", "candidates", "applications"):
        exists = connection.execute(
            text(
                "SELECT COUNT(*) "
                "FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = DATABASE() "
                "AND TABLE_NAME = :table_name"
            ),
            {"table_name": table},
        ).scalar()

        if not exists:
            raise RuntimeError(
                f"Chưa có bảng '{table}'. "
                "Hãy kiểm tra đúng database và chạy init_db.py "
                "nếu đây là database mới."
            )


def verify_user_columns(connection):
    rows = connection.execute(
            text(
                "SELECT COLUMN_NAME "
                "FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() "
                "AND TABLE_NAME = 'users'"
            )
    ).scalars().all()

    existing = set(rows)
    missing = REQUIRED_USER_COLUMNS - existing

    if missing:
        raise RuntimeError(
            "Bảng users vẫn thiếu các cột: "
            + ", ".join(sorted(missing))
        )

    print("[OK] Bảng users có đầy đủ các cột cần thiết.")
    print("[OK] Đã xác nhận tồn tại users.verification_attempts.")


def migrate():
    if engine.dialect.name != "mysql":
        raise RuntimeError(
            "Script này dành cho MySQL. "
            "Hãy kiểm tra DATABASE_URL."
        )

    print("Đang kết nối MySQL...")

    with engine.begin() as connection:
        database_name = connection.execute(
            text("SELECT DATABASE()")
        ).scalar()

        if not database_name:
            raise RuntimeError(
                "DATABASE_URL chưa chỉ định tên database."
            )

        print(f"Database đang cập nhật: {database_name}")

        ensure_tables(connection)

        for name, check_sql, statements in MIGRATIONS:
            print(f"\nKiểm tra: {name}")

            if connection.execute(text(check_sql)).scalar():
                print("[BỎ QUA] Đã tồn tại.")
                continue

            try:
                for statement in statements:
                    connection.execute(text(statement))
            except Exception:
                print(f"[LỖI] Chưa hoàn thành bước: {name}")
                raise

            print("[OK] Đã áp dụng.")

        verify_user_columns(connection)

    print("\nCập nhật CSDL hoàn tất.")
    print("Khởi động lại backend rồi thử đăng ký/đăng nhập.")


if __name__ == "__main__":
    migrate()