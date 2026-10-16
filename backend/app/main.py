import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ---------------------------------------------------------------------------
# Logging — hiển thị log của AI Pipeline (app.*) trên console cùng log uvicorn
# ---------------------------------------------------------------------------
_app_logger = logging.getLogger("app")
if not _app_logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(message)s", "%H:%M:%S"))
    _app_logger.addHandler(_handler)
    _app_logger.setLevel(logging.INFO)
    _app_logger.propagate = False

app = FastAPI(
    title="SmartRecruit AI",
    description="Hệ thống quản lý tuyển dụng thông minh kết hợp trí tuệ nhân tạo",
    version="0.1.0",
)

# ---------------------------------------------------------------------------
# CORS — allow the local frontend (file:// or dev server) to call the API
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers (will be registered as each module is implemented)
# ---------------------------------------------------------------------------
from app.api import auth, jobs, applications
app.include_router(auth.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(applications.router, prefix="/api")


# ---------------------------------------------------------------------------
# Startup — nạp sẵn mô hình nhúng (chạy luồng nền để server khởi động ngay)
# ---------------------------------------------------------------------------
import threading

from app.core.config import EMBEDDING_PRELOAD
from app.services import embedding_service


@app.on_event("startup")
def preload_ai_models():
    if EMBEDDING_PRELOAD:
        threading.Thread(
            target=embedding_service.preload_embedding_model,
            name="embedding-preload",
            daemon=True,
        ).start()


# ---------------------------------------------------------------------------
# Health-check endpoint
# ---------------------------------------------------------------------------
@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "message": "SmartRecruit AI is running 🚀"}


@app.get("/health", tags=["Health"])
async def health():
    return {
        "status": "healthy",
        "embedding_model_loaded": embedding_service.is_model_loaded(),
    }
