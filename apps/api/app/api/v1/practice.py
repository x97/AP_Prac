from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.schemas import (
    PracticeAnswerRequest,
    PracticeFlagRequest,
    PracticeFlushRequest,
    PracticeSessionCreate,
)
from app.content.store import ContentStore
from app.core.db import get_db
from app.core.deps import get_current_user, get_store
from app.services import practice_engine
from app.users.models import User

router = APIRouter(prefix="/practice-sessions", tags=["practice"])


@router.post("")
def create_session(
    body: PracticeSessionCreate,
    db: Session = Depends(get_db),
    store: ContentStore = Depends(get_store),
    user: User = Depends(get_current_user),
):
    return practice_engine.create_session(db, store, user, body)


@router.get("/{session_id}")
def get_session(
    session_id: str,
    db: Session = Depends(get_db),
    store: ContentStore = Depends(get_store),
    user: User = Depends(get_current_user),
):
    return practice_engine.get_session(db, store, user, session_id)


@router.get("/{session_id}/questions/{question_id}/topic-concepts")
def question_topic_concepts(
    session_id: str,
    question_id: str,
    db: Session = Depends(get_db),
    store: ContentStore = Depends(get_store),
    user: User = Depends(get_current_user),
):
    return practice_engine.topic_context_for_question(
        db, store, user, session_id, question_id
    )


@router.post("/{session_id}/answers")
def answer_question(
    session_id: str,
    body: PracticeAnswerRequest,
    db: Session = Depends(get_db),
    store: ContentStore = Depends(get_store),
    user: User = Depends(get_current_user),
):
    return practice_engine.answer_question(db, store, user, session_id, body)


@router.patch("/{session_id}/answers")
def flag_question(
    session_id: str,
    body: PracticeFlagRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return practice_engine.flag_question(db, user, session_id, body.question_id, body.flagged)


@router.post("/{session_id}/answers:flush")
def flush_answers(
    session_id: str,
    body: PracticeFlushRequest,
    db: Session = Depends(get_db),
    store: ContentStore = Depends(get_store),
    user: User = Depends(get_current_user),
):
    return practice_engine.flush_answers(db, store, user, session_id, body.answers)


@router.post("/{session_id}/submit")
def submit_session(
    session_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return practice_engine.submit_session(db, user, session_id)


@router.post("/{session_id}/abandon")
def abandon_session(
    session_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return practice_engine.abandon_session(db, user, session_id)


@router.get("/{session_id}/review")
def review_session(
    session_id: str,
    db: Session = Depends(get_db),
    store: ContentStore = Depends(get_store),
    user: User = Depends(get_current_user),
):
    return practice_engine.review_session(db, store, user, session_id)
