"""
Script seed dữ liệu mẫu vào CSDL.
Bao gồm:
- 01 tài khoản HR
- 02 tin tuyển dụng lập trình viên
"""
import os
import sys
import hashlib
from dotenv import load_dotenv

# Thêm thư mục backend vào sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load biến môi trường từ .env
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from app.core.database import SessionLocal
from app.models import User, UserRole, Job, JobStatus

def hash_password(password: str) -> str:
    # Tạm thời dùng SHA-256 (sau này module Auth sẽ nâng cấp lên bcrypt)
    return hashlib.sha256(password.encode()).hexdigest()

def seed_data():
    db = SessionLocal()
    try:
        print("Bắt đầu seed dữ liệu...")
        
        # 1. Tạo tài khoản HR
        hr_email = "hr@smartrecruit.com"
        hr_user = db.query(User).filter(User.email == hr_email).first()
        if not hr_user:
            hr_user = User(
                full_name="Nguyễn HR",
                email=hr_email,
                hashed_password=hash_password("admin123"),
                role=UserRole.hr,
                is_active=True
            )
            db.add(hr_user)
            db.commit()
            db.refresh(hr_user)
            print(f"Đã tạo tài khoản HR: {hr_email} / admin123")
        else:
            print(f"Tài khoản HR {hr_email} đã tồn tại.")

        # 2. Tạo 02 tin tuyển dụng
        job1 = db.query(Job).filter(Job.title == "Backend Developer (Python/FastAPI)").first()
        if not job1:
            job1 = Job(
                title="Backend Developer (Python/FastAPI)",
                description="Chúng tôi cần tìm ứng viên cho vị trí Backend Developer làm việc với Python, FastAPI và MySQL để phát triển API cho hệ thống tuyển dụng.",
                requirements="Thành thạo Python và FastAPI. Có kinh nghiệm làm việc với SQLAlchemy và MySQL. Hiểu biết về RESTful API và Git.",
                required_skills=["Python", "FastAPI", "SQLAlchemy", "MySQL"],
                preferred_skills=["Docker", "Redis", "Linux"],
                experience_years_min=2,
                status=JobStatus.open,
                created_by=hr_user.id
            )
            db.add(job1)
            print("Đã tạo Job 1: Backend Developer (Python/FastAPI)")

        job2 = db.query(Job).filter(Job.title == "Frontend Developer (JavaScript/VueJS)").first()
        if not job2:
            job2 = Job(
                title="Frontend Developer (JavaScript/VueJS)",
                description="Tìm kiếm Frontend Developer để xây dựng giao diện ứng viên (Candidate Portal) và bảng Kanban quản lý cho HR.",
                requirements="Nắm vững HTML, CSS, JavaScript (ES6+). Có kinh nghiệm sử dụng framework VueJS (Vue 3). Có kiến thức về Bootstrap 5 hoặc Tailwind CSS là lợi thế.",
                required_skills=["HTML", "CSS", "JavaScript", "VueJS"],
                preferred_skills=["Bootstrap 5", "UI/UX", "Figma"],
                experience_years_min=1,
                status=JobStatus.open,
                created_by=hr_user.id
            )
            db.add(job2)
            print("Đã tạo Job 2: Frontend Developer (JavaScript/VueJS)")

        db.commit()
        print("✅ Seed dữ liệu mẫu thành công!")

    except Exception as e:
        db.rollback()
        print("❌ Lỗi khi seed dữ liệu:", str(e))
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()

