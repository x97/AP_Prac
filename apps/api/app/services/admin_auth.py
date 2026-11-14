from __future__ import annotations

from datetime import timedelta
from typing import Optional

from fastapi import Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import client_ip, hash_token, new_session_token
from app.core.time import is_expired, utcnow
from app.users.models import AdminAuditLog, AdminSession, AdminUser


def create_admin_session(
    db: Session, admin: AdminUser, request: Request, settings: Settings
) -> str:
    token = new_session_token()
    now = utcnow()
    db.add(
        AdminSession(
            admin_id=admin.id,
            token_hash=hash_token(token),
            expires_at=now + timedelta(hours=settings.admin_session_hours),
            created_at=now,
            last_seen_at=now,
            ip=client_ip(request),
            user_agent=(request.headers.get("user-agent") or "")[:256],
        )
    )
    admin.last_login_at = now
    return token


def set_admin_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        key=settings.admin_cookie_name,
        value=token,
        max_age=settings.admin_session_hours * 3600,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def clear_admin_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(settings.admin_cookie_name, path="/")


def get_admin_by_session(db: Session, token: str) -> Optional[AdminUser]:
    session = db.scalar(select(AdminSession).where(AdminSession.token_hash == hash_token(token)))
    if not session or is_expired(session.expires_at):
        return None
    admin = db.get(AdminUser, session.admin_id)
    if not admin or admin.status != "active":
        return None
    session.last_seen_at = utcnow()
    return admin


def admin_from_request(db: Session, request: Request, settings: Settings) -> Optional[AdminUser]:
    token = request.cookies.get(settings.admin_cookie_name)
    if not token:
        return None
    return get_admin_by_session(db, token)


def admin_payload(admin: AdminUser) -> dict:
    return {
        "id": admin.id,
        "username": admin.username,
        "email": admin.email,
        "role": admin.role,
        "status": admin.status,
        "can_edit_content": admin.role in {"super_admin", "content_editor"},
        "created_at": admin.created_at,
        "last_login_at": admin.last_login_at,
    }


def record_audit(
    db: Session,
    admin: Optional[AdminUser],
    action: str,
    *,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    detail: Optional[dict] = None,
    request: Optional[Request] = None,
) -> None:
    db.add(
        AdminAuditLog(
            admin_id=admin.id if admin else None,
            action=action,
            target_type=target_type,
            target_id=target_id,
            detail=detail,
            ip=client_ip(request) if request else None,
        )
    )
