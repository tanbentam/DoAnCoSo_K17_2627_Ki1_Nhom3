"""
Script khởi tạo cơ sở dữ liệu trên Aiven MySQL.
Tự động tạo các bảng dựa trên định nghĩa SQLAlchemy models.
"""
import os
import sys
from dotenv import load_dotenv

# Thêm thư mục backend vào sys.path để có thể import từ app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load biến môi trường từ .env
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from app.core.database import engine, Base
# Import tất cả các model để SQLAlchemy nhận diện được
from app.models import User, Job, Candidate, Application

def init_db():
    print("Đang kết nối đến CSDL Aiven MySQL...")
    try:
        # Tạo tất cả các bảng chưa tồn tại
        Base.metadata.create_all(bind=engine)
        print("✅ Đã tạo các bảng CSDL thành công!")
    except Exception as e:
        print("❌ Lỗi khi tạo bảng:", str(e))

if __name__ == "__main__":
    init_db()

