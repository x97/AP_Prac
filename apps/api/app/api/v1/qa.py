from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.schemas import QaQuestionCreate, QaReplyCreate
from app.content.store import ContentStore
from app.core.db import get_db
from app.core.deps import get_current_user, get_store
from app.services import qa
from app.users.models import User

router = APIRouter(prefix="/qa", tags=["qa"])


@router.get("/questions/{question_id}")
def question_threads(
    question_id: str,
    session_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return qa.question_threads(db, user, session_id, question_id)


@router.post("/questions")
def create_question(
    body: QaQuestionCreate,
    subject: Optional[str] = None,
    db: Session = Depends(get_db),
    store: ContentStore = Depends(get_store),
    user: User = Depends(get_current_user),
):
    return qa.create_question(
        db,
        store,
        user,
        session_id=body.session_id,
        question_id=body.question_id,
        content=body.content,
    )


@router.post("/questions/{question_id}/read")
def mark_question_read(
    question_id: str,
    session_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return qa.mark_question_read(db, user, session_id, question_id)


@router.get("/my-threads")
def my_threads(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return qa.my_threads(db, user, limit=limit, offset=offset)


@router.get("/threads/{thread_id}")
def thread_detail(
    thread_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return qa.thread_detail_student(db, user, thread_id)


@router.post("/threads/{thread_id}/replies")
def reply_thread(
    thread_id: str,
    body: QaReplyCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return qa.student_reply(db, user, thread_id, body.content)


@router.get("/unread-count")
def unread_count(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return {"unread": qa.student_unread_count(db, user)}
