from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.schemas import (
    AttemptAnswersRequest,
    AttemptCreate,
    FrqScoresRequest,
)
from app.content.store import ContentStore
from app.core.db import get_db
from app.core.deps import get_current_user, get_store
from app.services import exam_engine
from app.users.models import User

router = APIRouter(prefix="/attempts", tags=["attempts"])


@router.post("")
def create_attempt(
    body: AttemptCreate,
    db: Session = Depends(get_db),
    store: ContentStore = Depends(get_store),
    user: User = Depends(get_current_user),
):
    return exam_engine.create_attempt(db, store, user, body)


@router.get("/{attempt_id}")
def get_attempt(
    attempt_id: str,
    db: Session = Depends(get_db),
    store: ContentStore = Depends(get_store),
    user: User = Depends(get_current_user),
):
    return exam_engine.get_attempt(db, store, user, attempt_id)


@router.post("/{attempt_id}/pause")
def pause_attempt(
    attempt_id: str,
    db: Session = Depends(get_db),
    store: ContentStore = Depends(get_store),
    user: User = Depends(get_current_user),
):
    return exam_engine.pause_attempt(db, store, user, attempt_id)


@router.post("/{attempt_id}/resume")
def resume_attempt(
    attempt_id: str,
    db: Session = Depends(get_db),
    store: ContentStore = Depends(get_store),
    user: User = Depends(get_current_user),
):
    return exam_engine.resume_attempt(db, store, user, attempt_id)


@router.patch("/{attempt_id}/answers")
def save_answers(
    attempt_id: str,
    body: AttemptAnswersRequest,
    db: Session = Depends(get_db),
    store: ContentStore = Depends(get_store),
    user: User = Depends(get_current_user),
):
    return exam_engine.save_answers(db, store, user, attempt_id, body.answers)


@router.post("/{attempt_id}/answers:flush")
def flush_answers(
    attempt_id: str,
    body: AttemptAnswersRequest,
    db: Session = Depends(get_db),
    store: ContentStore = Depends(get_store),
    user: User = Depends(get_current_user),
):
    return exam_engine.save_answers(db, store, user, attempt_id, body.answers)


@router.post("/{attempt_id}/sections/{section}/start")
def start_section(
    attempt_id: str,
    section: str,
    db: Session = Depends(get_db),
    store: ContentStore = Depends(get_store),
    user: User = Depends(get_current_user),
):
    return exam_engine.start_section(db, store, user, attempt_id, section)


@router.post("/{attempt_id}/sections/{section}/submit")
def submit_section(
    attempt_id: str,
    section: str,
    db: Session = Depends(get_db),
    store: ContentStore = Depends(get_store),
    user: User = Depends(get_current_user),
):
    return exam_engine.submit_section(db, store, user, attempt_id, section)


@router.post("/{attempt_id}/abandon")
def abandon_attempt(
    attempt_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return exam_engine.abandon_attempt(db, user, attempt_id)


@router.post("/{attempt_id}/frq-scores")
def frq_scores(
    attempt_id: str,
    body: FrqScoresRequest,
    db: Session = Depends(get_db),
    store: ContentStore = Depends(get_store),
    user: User = Depends(get_current_user),
):
    return exam_engine.save_frq_scores(db, store, user, attempt_id, body.scores)


@router.get("/{attempt_id}/review")
def review_attempt(
    attempt_id: str,
    db: Session = Depends(get_db),
    store: ContentStore = Depends(get_store),
    user: User = Depends(get_current_user),
):
    return exam_engine.review_attempt(db, store, user, attempt_id)
