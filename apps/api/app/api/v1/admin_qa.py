from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.v1.schemas import QaReplyCreate
from app.core.admin_deps import get_current_admin, require_admin_roles
from app.core.db import get_db
from app.services import qa
from app.services.admin_auth import record_audit
from app.users.models import AdminUser

router = APIRouter(prefix="/admin/qa", tags=["admin-qa"])

WRITE_ROLES = ("super_admin", "content_editor", "support")


@router.get("/threads")
def list_threads(
    subject: Optional[str] = None,
    unread: bool = False,
    q: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    return qa.admin_threads(
        db,
        subject_id=(subject or "").strip() or None,
        unread_only=unread,
        q=q,
        limit=limit,
        offset=offset,
    )


@router.get("/threads/{thread_id}")
def thread_detail(
    thread_id: str,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    return qa.admin_thread_detail(db, thread_id)


@router.post("/threads/{thread_id}/replies")
def reply_thread(
    thread_id: str,
    body: QaReplyCreate,
    request: Request,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin_roles(*WRITE_ROLES)),
):
    result = qa.admin_reply(db, admin, thread_id, body.content)
    record_audit(
        db,
        admin,
        "qa.reply",
        target_type="qa_thread",
        target_id=thread_id,
        detail={"reply_id": result.get("id")},
        request=request,
    )
    db.commit()
    return result


@router.get("/unread-count")
def unread_count(
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    return {"unread": qa.admin_unread_count(db)}
