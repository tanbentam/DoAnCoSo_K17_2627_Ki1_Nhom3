"""
api/jobs.py — API quản lý tin tuyển dụng
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_active_hr
from app.models.job import Job, JobStatus
from app.models.user import User
from app.schemas.job import JobCreate, JobUpdate, JobResponse

router = APIRouter(prefix="/jobs", tags=["Jobs"])

@router.get("", response_model=List[JobResponse])
def get_jobs(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    status: JobStatus | None = None
):
    """Lấy danh sách tin tuyển dụng. Có thể lọc theo status."""
    query = db.query(Job)
    if status:
        query = query.filter(Job.status == status)
    jobs = query.order_by(Job.created_at.desc()).offset(skip).limit(limit).all()
    return jobs

@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_job(
    job_in: JobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_hr)
):
    """Tạo tin tuyển dụng mới (chỉ HR/Admin)."""
    new_job = Job(
        title=job_in.title,
        description=job_in.description,
        requirements=job_in.requirements,
        required_skills=job_in.required_skills,
        preferred_skills=job_in.preferred_skills,
        experience_years_min=job_in.experience_years_min,
        status=JobStatus.open,
        created_by=current_user.id
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    return new_job

@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: int, db: Session = Depends(get_db)):
    """Xem chi tiết 1 tin tuyển dụng."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Không tìm thấy tin tuyển dụng")
    return job

@router.put("/{job_id}", response_model=JobResponse)
def update_job(
    job_id: int,
    job_in: JobUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_hr)
):
    """Cập nhật hoặc đóng tin tuyển dụng (chỉ HR/Admin)."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Không tìm thấy tin tuyển dụng")
    
    update_data = job_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(job, field, value)
        
    db.commit()
    db.refresh(job)
    return job

