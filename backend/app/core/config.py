import os
from dotenv import load_dotenv

load_dotenv()  # Load variables from .env at project root

# --- Database ---
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://root:root@localhost:3306/smartrecruit",
)

# --- AI Provider ---
AI_PROVIDER: str = os.getenv("AI_PROVIDER", "cloud")
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
GEMINI_TEMPERATURE: float = float(os.getenv("GEMINI_TEMPERATURE", "0.2"))
GEMINI_TIMEOUT_SECONDS: int = int(os.getenv("GEMINI_TIMEOUT_SECONDS", "60"))
GEMINI_MAX_RETRIES: int = int(os.getenv("GEMINI_MAX_RETRIES", "3"))

# --- Embedding (Sentence-Transformers, chạy cục bộ) ---
EMBEDDING_MODEL_NAME: str = os.getenv(
    "EMBEDDING_MODEL_NAME", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)
EMBEDDING_DEVICE: str = os.getenv("EMBEDDING_DEVICE", "cpu")
EMBEDDING_BATCH_SIZE: int = int(os.getenv("EMBEDDING_BATCH_SIZE", "16"))
# Thư mục cache mô hình (tương đối theo thư mục backend) — tải 1 lần, dùng offline về sau
EMBEDDING_CACHE_DIR: str = os.getenv("EMBEDDING_CACHE_DIR", "models_cache")
# Nạp sẵn mô hình khi khởi động server để request đầu tiên không bị chậm
EMBEDDING_PRELOAD: bool = os.getenv("EMBEDDING_PRELOAD", "true").lower() in ("1", "true", "yes")

OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

# --- Email ---
SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER: str = os.getenv("SMTP_USER", "")
SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")

from pathlib import Path

# --- File Storage ---
BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent  # backend folder
UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads/cv")
UPLOAD_DIR_PATH: Path = BASE_DIR / UPLOAD_DIR
MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "5"))

# Đảm bảo thư mục lưu trữ CV tồn tại
UPLOAD_DIR_PATH.mkdir(parents=True, exist_ok=True)

# --- App ---
SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-change-me")
APP_ENV: str = os.getenv("APP_ENV", "development")
