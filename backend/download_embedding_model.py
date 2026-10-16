"""
Script tải trước mô hình nhúng sentence-transformers về thư mục cache cục bộ.
Chạy một lần khi có mạng; sau đó hệ thống dùng được mô hình cả khi ngắt mạng.

    python download_embedding_model.py
"""
import os
import sys
import time

import numpy as np
from dotenv import load_dotenv

# Thêm thư mục backend vào sys.path để có thể import từ app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load biến môi trường từ .env
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from app.core.config import EMBEDDING_DEVICE, EMBEDDING_MODEL_NAME
from app.services.embedding_service import (
    EmbeddingServiceError,
    encode_texts,
    get_cache_dir,
    get_embedding_dimension,
    get_embedding_model,
)


def download_model():
    print(f"Đang tải mô hình '{EMBEDDING_MODEL_NAME}' về {get_cache_dir()} ...")
    started = time.perf_counter()
    try:
        model = get_embedding_model()
    except EmbeddingServiceError as e:
        print("❌ Lỗi khi tải mô hình:", str(e))
        sys.exit(1)

    print(f"✅ Đã tải & nạp mô hình sau {time.perf_counter() - started:.1f}s")
    print(f"   Thiết bị: {EMBEDDING_DEVICE} | Số chiều vector: {get_embedding_dimension(model)} "
          f"| max_seq_length: {model.max_seq_length}")

    # Kiểm tra nhanh: câu đồng nghĩa Việt - Anh phải gần nhau hơn câu không liên quan
    vectors = encode_texts([
        "Lập trình viên backend sử dụng Python và FastAPI",
        "Backend developer experienced with Python and FastAPI",
        "Nhân viên kế toán tổng hợp, lập báo cáo thuế",
    ])
    similar = float(np.dot(vectors[0], vectors[1]))
    unrelated = float(np.dot(vectors[0], vectors[2]))
    print(f"   Kiểm tra: tương đồng Việt-Anh cùng nghĩa = {similar:.3f}, khác ngành = {unrelated:.3f}")
    print("✅ Mô hình hoạt động bình thường." if similar > unrelated else "⚠️ Kết quả kiểm tra bất thường.")


if __name__ == "__main__":
    download_model()
