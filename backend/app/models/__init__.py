# app/models/__init__.py
from app.models.user import User, UserRole
from app.models.job import Job, JobStatus
from app.models.candidate import Candidate
from app.models.application import Application, ApplicationStatus

__all__ = [
    "User", "UserRole",
    "Job", "JobStatus",
    "Candidate",
    "Application", "ApplicationStatus",
]
