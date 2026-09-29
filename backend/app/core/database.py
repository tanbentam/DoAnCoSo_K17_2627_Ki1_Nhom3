"""
database.py — SQLAlchemy engine & session factory
Will be wired to Aiven MySQL once DATABASE_URL is set in .env
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.core.config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    # Aiven MySQL requires SSL; add connect_args here when using real cloud URL
    # connect_args={"ssl": {"ca": "/path/to/ca.pem"}},
    pool_pre_ping=True,
    pool_recycle=300,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


def get_db():
    """FastAPI dependency that provides a DB session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
