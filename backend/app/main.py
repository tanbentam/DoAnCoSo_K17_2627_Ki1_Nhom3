from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
# Health-check endpoint
# ---------------------------------------------------------------------------
@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "message": "SmartRecruit AI is running 🚀"}


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy"}
