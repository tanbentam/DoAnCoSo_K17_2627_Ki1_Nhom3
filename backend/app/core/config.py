import os
from dotenv import load_dotenv

load_dotenv()  # Load variables from .env at project root

# --- Database ---
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://root:root@localhost:3306/smartrecruit",
)
# SSL/TLS: auto | verify | required | disabled (xem core/database.py)
DB_SSL_MODE: str = os.getenv("DB_SSL_MODE", "auto")
# CA certificate của Aiven (Aiven Console → Overview → CA certificate), đường dẫn tương đối theo thư mục backend
DB_SSL_CA: str = os.getenv("DB_SSL_CA", "")

# --- AI Provider ---
# cloud: chỉ Gemini | local: chỉ Ollama | auto: Gemini trước, lỗi/hết hạn mức thì chuyển Ollama
AI_PROVIDER: str = os.getenv("AI_PROVIDER", "auto").strip().lower()
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
# Chuỗi model dự phòng khi model chính quá tải / hết hạn mức (mỗi model có hạn mức miễn phí riêng)
GEMINI_FALLBACK_MODELS: list = [
    m.strip()
    for m in os.getenv("GEMINI_FALLBACK_MODELS", "gemini-3.7-flash,gemini-3.5-flash,gemini-3.1-flash-lite").split(",")
    if m.strip()
]
GEMINI_TEMPERATURE: float = float(os.getenv("GEMINI_TEMPERATURE", "0.2"))
GEMINI_TIMEOUT_SECONDS: int = int(os.getenv("GEMINI_TIMEOUT_SECONDS", "30"))
# Số lần thử lại MỖI model khi lỗi tạm thời, sau đó chuyển model dự phòng
GEMINI_MAX_RETRIES: int = int(os.getenv("GEMINI_MAX_RETRIES", "1"))

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

# --- Semantic Matching (hiệu chỉnh cosine similarity → điểm 0–100) ---
# cosine ≤ FLOOR → 0 điểm, cosine ≥ CEIL → 100 điểm (đo thực tế với MiniLM-L12-v2)
SEMANTIC_SIM_FLOOR: float = float(os.getenv("SEMANTIC_SIM_FLOOR", "0.20"))
SEMANTIC_SIM_CEIL: float = float(os.getenv("SEMANTIC_SIM_CEIL", "0.80"))

# --- Hybrid Matching Score = 40% Hard Filter + 60% Semantic Match ---
HYBRID_HARD_FILTER_WEIGHT: float = float(os.getenv("HYBRID_HARD_FILTER_WEIGHT", "0.4"))
HYBRID_SEMANTIC_WEIGHT: float = float(os.getenv("HYBRID_SEMANTIC_WEIGHT", "0.6"))
# Ngưỡng cosine để coi 2 tên kỹ năng là đồng nghĩa (VD: "MySQL" ~ "Cơ sở dữ liệu MySQL")
SKILL_SEMANTIC_THRESHOLD: float = float(os.getenv("SKILL_SEMANTIC_THRESHOLD", "0.80"))

# --- Ollama (mô hình cục bộ trên GPU, dùng khi AI_PROVIDER=local hoặc dự phòng khi auto) ---
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
# Lần gọi đầu phải nạp model vào VRAM (~25s) nên cần timeout rộng
OLLAMA_TIMEOUT_SECONDS: int = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "300"))
# Cửa sổ ngữ cảnh: CV ~20.000 ký tự ≈ 6–7 nghìn token + schema + prompt
OLLAMA_NUM_CTX: int = int(os.getenv("OLLAMA_NUM_CTX", "8192"))
# Giữ model trong VRAM sau lần gọi cuối để các hồ sơ tiếp theo không phải nạp lại
OLLAMA_KEEP_ALIVE: str = os.getenv("OLLAMA_KEEP_ALIVE", "30m")
OLLAMA_TEMPERATURE: float = float(os.getenv("OLLAMA_TEMPERATURE", "0.2"))

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
