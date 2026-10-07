"""
schemas/application.py — Pydantic models (DTOs) cho Application
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.models.application import ApplicationStatus
from app.schemas.candidate import CandidateResponse


class ApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus = Field(..., example=ApplicationStatus.screening)


class ApplicationResponse(BaseModel):
    id: int
    job_id: int
    candidate_id: int
    status: ApplicationStatus
    matching_score: Optional[float] = None
    semantic_score: Optional[float] = None
    hard_filter_score: Optional[float] = None
    ai_extracted_info: Optional[Dict[str, Any]] = None
    matched_skills: Optional[List[str]] = None
    missing_skills: Optional[List[str]] = None
    interview_questions: Optional[List[str]] = None
    ai_summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    candidate: Optional[CandidateResponse] = None

    class Config:
        orm_mode = True


class ApplicationApplyResponse(BaseModel):
    message: str
    application_id: int
    candidate_id: int
    job_id: int
    status: ApplicationStatus

