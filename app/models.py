"""SQLAlchemy models — the database tables, as Python classes."""

import enum
from datetime import date, datetime, timezone

from sqlalchemy import Column, Date, DateTime, Enum, Integer, String, Text

from .database import Base


class ApplicationStatus(str, enum.Enum):
    """Every application sits in exactly one stage of the funnel."""

    WISHLIST = "wishlist"
    APPLIED = "applied"
    OA = "oa"  # online assessment
    INTERVIEW = "interview"
    OFFER = "offer"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    company = Column(String(120), nullable=False, index=True)
    role = Column(String(200), nullable=False)
    location = Column(String(120), nullable=True)
    job_url = Column(String(500), nullable=True)
    status = Column(Enum(ApplicationStatus), nullable=False, default=ApplicationStatus.APPLIED)
    date_applied = Column(Date, nullable=False, default=date.today)
    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
