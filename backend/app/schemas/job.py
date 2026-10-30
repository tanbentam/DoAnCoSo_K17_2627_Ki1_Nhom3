"""
schemas/job.py — Pydantic models (DTOs) cho Job
"""
from datetime import datetime
from pydantic import BaseModel, Field, field_validator

from app.models.job import JobStatus


def _blank_to_none(value: str | None) -> str | None:
    """Bỏ khoảng trắng hai đầu; chuỗi rỗng → None (xóa địa điểm)."""
    if value is None:
        return None
    value = value.strip()
    return value or None

class JobBase(BaseModel):
    title: str = Field(..., max_length=255, example="Backend Developer")
    description: str = Field(..., example="JD cho vị trí...")
    requirements: str = Field(..., example="Yêu cầu: ...")
    required_skills: list[str] = Field(default_factory=list, example=["Python", "FastAPI"])
    preferred_skills: list[str] | None = None
    experience_years_min: int = Field(default=0, ge=0)
    location: str | None = Field(None, max_length=255, example="Chi nhánh Cầu Giấy, 123 Xuân Thủy, Hà Nội")

    clean_location = field_validator("location")(_blank_to_none)

class JobCreate(JobBase):
    pass

class JobUpdate(BaseModel):
    title: str | None = Field(None, max_length=255)
    description: str | None = None
    requirements: str | None = None
    required_skills: list[str] | None = None
    preferred_skills: list[str] | None = None
    experience_years_min: int | None = Field(None, ge=0)
    location: str | None = Field(None, max_length=255)
    status: JobStatus | None = None

    clean_location = field_validator("location")(_blank_to_none)

class JobResponse(JobBase):
    id: int
    status: JobStatus
    created_by: int | None
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

