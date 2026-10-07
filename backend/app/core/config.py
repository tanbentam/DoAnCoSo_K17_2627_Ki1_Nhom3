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
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

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
