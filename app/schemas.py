"""Pydantic schemas — the shapes of data going in and out of the API.

Keeping these separate from the SQLAlchemy models is deliberate:
the database layer and the API contract can evolve independently.
"""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from .models import ApplicationStatus


class ApplicationCreate(BaseModel):
    company: str = Field(..., min_length=1, max_length=120)
    role: str = Field(..., min_length=1, max_length=200)
    location: Optional[str] = None
    job_url: Optional[HttpUrl] = None
    status: ApplicationStatus = ApplicationStatus.APPLIED
    date_applied: date = Field(default_factory=date.today)
    salary_min: Optional[int] = Field(default=None, ge=0)
    salary_max: Optional[int] = Field(default=None, ge=0)
    notes: Optional[str] = None


class ApplicationUpdate(BaseModel):
    """All fields optional — PATCH only changes what is sent."""

    company: Optional[str] = Field(default=None, min_length=1, max_length=120)
    role: Optional[str] = Field(default=None, min_length=1, max_length=200)
    location: Optional[str] = None
    job_url: Optional[HttpUrl] = None
    status: Optional[ApplicationStatus] = None
    date_applied: Optional[date] = None
    salary_min: Optional[int] = Field(default=None, ge=0)
    salary_max: Optional[int] = Field(default=None, ge=0)
    notes: Optional[str] = None


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company: str
    role: str
    location: Optional[str]
    job_url: Optional[str]
    status: ApplicationStatus
    date_applied: date
    salary_min: Optional[int]
    salary_max: Optional[int]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime


class ApplicationPage(BaseModel):
    """A page of results plus the metadata a client needs to paginate."""

    items: list[ApplicationOut]
    total: int
    page: int
    page_size: int


class StatsOut(BaseModel):
    total: int
    by_status: dict[str, int]
    applied_last_7_days: int
    applied_last_30_days: int
    response_rate: float  # share of applications that moved past "applied"
