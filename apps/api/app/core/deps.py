from __future__ import annotations

import re
from typing import Optional

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.content.store import ContentStore
from app.core.config import get_settings
from app.core.db import get_db
from app.core.errors import AppError
from app.core.security import user_from_request
from app.services.effective_content import ensure_effective_content
from app.users.models import User

_SUBJECT_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


def get_optional_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    return user_from_request(db, request)


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    user = user_from_request(db, request)
    if not user:
        raise AppError(401, "AUTH_REQUIRED", "请先登录")
    return user


def request_subject(request: Request) -> str:
    subject = (request.query_params.get("subject") or "psychology").strip().lower()
    if not _SUBJECT_RE.match(subject):
        raise AppError(400, "SUBJECT_INVALID", "科目参数不合法")
    return subject


def get_store(request: Request, db: Session = Depends(get_db)):
    settings = get_settings()
    subject_id = request_subject(request)
    stores = getattr(request.app.state, "stores", None)
    if stores is None:
        stores = {}
        request.app.state.stores = stores
    store = stores.get(subject_id)
    try:
        target = ensure_effective_content(db, subject_id)
    except Exception as exc:  # noqa: BLE001
        raise AppError(503, "CONTENT_NOT_READY", f"科目 {subject_id} 暂无可用内容版本") from exc
    try:
        target_key = target.resolve()
    except OSError:
        target_key = target
    if (
        store is None
        or getattr(store, "resolved_dir", None) is None
        or store.resolved_dir != target_key
    ):
        try:
            store = ContentStore(target, settings, subject_id=subject_id)
        except Exception as exc:  # noqa: BLE001
            raise AppError(503, "CONTENT_NOT_READY", "内容库未就绪") from exc
        for method in (
            "get_topic_concepts",
            "question_context",
            "get_feedback",
            "get_frq_guidelines",
        ):
            cache_clear = getattr(getattr(store, method), "cache_clear", None)
            if cache_clear:
                cache_clear()
        stores[subject_id] = store
        if subject_id == "psychology":
            request.app.state.store = store
    return store
