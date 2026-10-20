"""Job Application Tracker API.

A small REST API for tracking job applications through their funnel:
wishlist -> applied -> oa -> interview -> offer / rejected / withdrawn.

Run locally:  uvicorn app.main:app --reload
Docs (auto):  http://127.0.0.1:8000/docs
"""

from datetime import date, timedelta
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from . import models, schemas
from .database import Base, engine, get_db

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Job Application Tracker", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/applications", response_model=schemas.ApplicationOut, status_code=201)
def create_application(payload: schemas.ApplicationCreate, db: Session = Depends(get_db)):
    data = payload.model_dump()
    if data.get("job_url") is not None:
        data["job_url"] = str(data["job_url"])
    application = models.Application(**data)
    db.add(application)
    db.commit()
    db.refresh(application)
    return application


@app.get("/applications", response_model=schemas.ApplicationPage)
def list_applications(
    status: Optional[models.ApplicationStatus] = None,
    company: Optional[str] = Query(default=None, description="Case-insensitive substring match"),
    applied_after: Optional[date] = None,
    applied_before: Optional[date] = None,
    sort: str = Query(default="date_desc", pattern="^(date_desc|date_asc|company)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(models.Application)
    if status is not None:
        query = query.filter(models.Application.status == status)
    if company:
        query = query.filter(models.Application.company.ilike(f"%{company}%"))
    if applied_after:
        query = query.filter(models.Application.date_applied >= applied_after)
    if applied_before:
        query = query.filter(models.Application.date_applied <= applied_before)

    if sort == "date_asc":
        query = query.order_by(models.Application.date_applied.asc(), models.Application.id.asc())
    elif sort == "company":
        query = query.order_by(models.Application.company.asc())
    else:
        query = query.order_by(models.Application.date_applied.desc(), models.Application.id.desc())

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def _get_or_404(db: Session, application_id: int) -> models.Application:
    application = db.get(models.Application, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return application


@app.get("/applications/{application_id}", response_model=schemas.ApplicationOut)
def get_application(application_id: int, db: Session = Depends(get_db)):
    return _get_or_404(db, application_id)


@app.patch("/applications/{application_id}", response_model=schemas.ApplicationOut)
def update_application(
    application_id: int, payload: schemas.ApplicationUpdate, db: Session = Depends(get_db)
):
    application = _get_or_404(db, application_id)
    updates = payload.model_dump(exclude_unset=True)
    if updates.get("job_url") is not None:
        updates["job_url"] = str(updates["job_url"])
    for field, value in updates.items():
        setattr(application, field, value)
    db.commit()
    db.refresh(application)
    return application


@app.delete("/applications/{application_id}", status_code=204)
def delete_application(application_id: int, db: Session = Depends(get_db)):
    application = _get_or_404(db, application_id)
    db.delete(application)
    db.commit()
    return None


@app.get("/stats", response_model=schemas.StatsOut)
def stats(db: Session = Depends(get_db)):
    today = date.today()
    total = db.query(func.count(models.Application.id)).scalar() or 0

    rows = (
        db.query(models.Application.status, func.count(models.Application.id))
        .group_by(models.Application.status)
        .all()
    )
    by_status = {status.value: 0 for status in models.ApplicationStatus}
    for status, count in rows:
        by_status[status.value] = count

    def applied_since(days: int) -> int:
        return (
            db.query(func.count(models.Application.id))
            .filter(models.Application.date_applied >= today - timedelta(days=days))
            .scalar()
            or 0
        )

    moved_past_applied = total - by_status["applied"] - by_status["wishlist"]
    response_rate = round(moved_past_applied / total, 4) if total else 0.0

    return {
        "total": total,
        "by_status": by_status,
        "applied_last_7_days": applied_since(7),
        "applied_last_30_days": applied_since(30),
        "response_rate": response_rate,
    }
