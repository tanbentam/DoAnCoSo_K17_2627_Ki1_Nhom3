"""
schemas/candidate.py — Pydantic models (DTOs) cho Candidate
"""
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class CandidateBase(BaseModel):
    full_name: str = Field(..., max_length=150, example="Nguyễn Văn A")
    email: EmailStr = Field(..., example="nguyenvana@example.com")
    phone: str | None = Field(None, max_length=30, example="0912345678")


class CandidateCreate(CandidateBase):
    pass


class CandidateResponse(CandidateBase):
    id: int
    cv_file_path: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

