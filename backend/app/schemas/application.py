"""
schemas/application.py — Pydantic models (DTOs) cho Application
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator

from app.models.application import AIStatus, ApplicationStatus
from app.schemas.candidate import CandidateResponse
from app.schemas.job import JobResponse


class ApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus = Field(..., example=ApplicationStatus.screening)
    # Mục 7.3: lịch phỏng vấn, chỉ dùng khi status = interview (bỏ trống → email báo HR sẽ liên hệ chốt lịch)
    interview_at: Optional[datetime] = Field(
        None, description="Thời gian phỏng vấn, ISO 8601 có múi giờ, VD 2026-10-26T02:30:00Z"
    )
    interview_location: Optional[str] = Field(None, max_length=255, description="Địa điểm hoặc link phỏng vấn online")
    # Mục 7.2–7.4: false → chỉ đổi trạng thái, không gửi email (VD kéo nhầm rồi kéo về)
    send_email: bool = Field(True, description="Gửi email cho ứng viên khi sang interview / offer / rejected")

    @field_validator("interview_location")
    @classmethod
    def clean_location(cls, value: Optional[str]) -> Optional[str]:
        return (value or "").strip() or None


class ApplicationResponse(BaseModel):
    id: int
    job_id: int
    candidate_id: int
    status: ApplicationStatus
    ai_status: AIStatus = AIStatus.pending
    ai_error: Optional[str] = None
    matching_score: Optional[float] = None
    semantic_score: Optional[float] = None
    hard_filter_score: Optional[float] = None
    ai_extracted_info: Optional[Dict[str, Any]] = None
    matched_skills: Optional[List[str]] = None
    missing_skills: Optional[List[str]] = None
    interview_questions: Optional[List[str]] = None
    ai_summary: Optional[str] = None
    interview_at: Optional[datetime] = None
    interview_location: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    candidate: Optional[CandidateResponse] = None
    job: Optional[JobResponse] = None
    # Chỉ có trong response của PATCH /status: true = đã xếp email báo ứng viên vào hàng gửi ngầm
    email_queued: Optional[bool] = None

    class Config:
        orm_mode = True


class ApplicationAIDetailResponse(BaseModel):
    application_id: int
    job_id: int
    candidate_id: int
    status: ApplicationStatus
    ai_status: AIStatus = AIStatus.pending
    ai_error: Optional[str] = None
    matching_score: Optional[float] = None
    semantic_score: Optional[float] = None
    hard_filter_score: Optional[float] = None
    ai_extracted_info: Optional[Dict[str, Any]] = None
    matched_skills: Optional[List[str]] = None
    missing_skills: Optional[List[str]] = None
    interview_questions: Optional[List[str]] = None
    ai_summary: Optional[str] = None
    candidate_name: Optional[str] = None
    job_title: Optional[str] = None


class ApplicationApplyResponse(BaseModel):
    message: str
    application_id: int
    candidate_id: int
    job_id: int
    status: ApplicationStatus
    ai_status: AIStatus = AIStatus.pending

