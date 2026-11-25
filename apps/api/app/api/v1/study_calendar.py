from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.content.store import ContentStore
from app.core.db import get_db
from app.core.deps import get_current_user, get_store
from app.services import study_plans
from app.users.models import User

router = APIRouter(prefix="/study-calendar", tags=["study-calendar"])


@router.get("")
def calendar_month(
    month: Optional[str] = None,
    subject: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return study_plans.calendar_month(
        db, user, (subject or "psychology").strip().lower(), month
    )


@router.get("/days/{day}")
def calendar_day(
    day: date,
    subject: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return study_plans.day_detail(
        db, user, (subject or "psychology").strip().lower(), day
    )


@router.post("/tasks/{task_id}/start")
def start_task(
    task_id: str,
    subject: Optional[str] = None,
    db: Session = Depends(get_db),
    store: ContentStore = Depends(get_store),
    user: User = Depends(get_current_user),
):
    return study_plans.start_task(db, store, user, task_id)


@router.post("/tasks/{task_id}/complete")
def complete_task(
    task_id: str,
    subject: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return study_plans.complete_task(db, user, task_id)
