from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.core.errors import AppError
from app.services.admin_auth import admin_from_request
from app.users.models import AdminUser


def get_current_admin(
    request: Request,
    db: Session = Depends(get_db),
) -> AdminUser:
    admin = admin_from_request(db, request, get_settings())
    if not admin:
        raise AppError(401, "ADMIN_AUTH_REQUIRED", "请先登录管理员账号")
    return admin


def require_admin_roles(*roles: str):
    allowed = set(roles)

    def dependency(admin: AdminUser = Depends(get_current_admin)) -> AdminUser:
        if admin.role not in allowed:
            raise AppError(403, "ADMIN_FORBIDDEN", "没有权限执行此操作")
        return admin

    return dependency
