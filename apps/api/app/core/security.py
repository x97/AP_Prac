from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
from datetime import timedelta
from typing import Optional

from fastapi import Request, Response
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AppError
from app.core.time import as_utc, is_expired, utcnow
from app.users.models import User, UserSession

COOKIE_NAME = "ap_session"
_PHONE_RE = re.compile(r"^\+861[3-9]\d{9}$")
_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$")
PBKDF2_ITERATIONS = 600_000


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def hash_code(secret_key: str, purpose: str, identifier: str, code: str) -> str:
    """Bind a verification code to its purpose and identifier.

    Including the purpose prevents a registration code from being replayed
    against the password-reset endpoint.
    """
    return hmac.new(
        secret_key.encode("utf-8"),
        f"{purpose}:{identifier}:{code}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def normalize_email(raw: str) -> str:
    value = (raw or "").strip().lower()
    if len(value) > 254 or not _EMAIL_RE.match(value):
        raise AppError(400, "INVALID_EMAIL", "请输入有效的邮箱地址")
    local, _, domain = value.partition("@")
    if len(local) > 64 or not domain or domain.startswith(".") or domain.endswith("."):
        raise AppError(400, "INVALID_EMAIL", "请输入有效的邮箱地址")
    return value


def mask_email(email: Optional[str]) -> Optional[str]:
    if not email:
        return None
    local, _, domain = email.partition("@")
    if not domain:
        return "***"
    visible = local[:1] or "*"
    return f"{visible}***@{domain}"


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
        dklen=32,
    )
    return "$".join(
        [
            "pbkdf2_sha256",
            str(PBKDF2_ITERATIONS),
            base64.b64encode(salt).decode("ascii"),
            base64.b64encode(digest).decode("ascii"),
        ]
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, iterations, salt_b64, digest_b64 = encoded.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            int(iterations),
            dklen=len(expected),
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def validate_password(password: str, settings: Settings) -> None:
    if len(password) < settings.password_min_length:
        raise AppError(
            400,
            "PASSWORD_TOO_SHORT",
            f"密码至少需要 {settings.password_min_length} 位",
        )
    if len(password) > 128:
        raise AppError(400, "PASSWORD_TOO_LONG", "密码不能超过 128 位")


def normalize_phone(raw: str) -> str:
    value = re.sub(r"[\s\-()]", "", (raw or "").strip())
    if value.startswith("0086"):
        value = "+86" + value[4:]
    elif value.startswith("86") and len(value) == 13:
        value = "+" + value
    elif value.isdigit() and len(value) == 11:
        value = "+86" + value
    if not _PHONE_RE.match(value):
        raise AppError(400, "INVALID_PHONE", "请输入有效的中国大陆手机号")
    return value


def mask_phone(phone: Optional[str]) -> Optional[str]:
    if not phone:
        return None
    if phone.startswith("+86") and len(phone) >= 14:
        return f"+86 {phone[3:6]}****{phone[-4:]}"
    if len(phone) >= 7:
        return phone[:3] + "****" + phone[-4:]
    return phone


def create_session(db: Session, user: User, request: Request, settings: Settings) -> str:
    token = new_session_token()
    expires = utcnow() + timedelta(days=settings.session_days)
    db.add(
        UserSession(
            user_id=user.id,
            token_hash=hash_token(token),
            expires_at=expires,
            ip=client_ip(request),
            user_agent=(request.headers.get("user-agent") or "")[:256],
        )
    )
    user.last_login_at = utcnow()
    return token


def revoke_user_sessions(
    db: Session, user_id: str, keep_token_hash: Optional[str] = None
) -> int:
    stmt = delete(UserSession).where(UserSession.user_id == user_id)
    if keep_token_hash:
        stmt = stmt.where(UserSession.token_hash != keep_token_hash)
    result = db.execute(stmt)
    return int(result.rowcount or 0)


def set_session_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=settings.session_days * 24 * 3600,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/")


def resolve_merged_user(db: Session, user: Optional[User]) -> Optional[User]:
    """Follow merge tombstones so an old id still resolves to the live account."""
    seen: set[str] = set()
    while user and user.merged_into_id and user.id not in seen:
        seen.add(user.id)
        user = db.get(User, user.merged_into_id)
    return user


def get_user_by_session(db: Session, token: str) -> Optional[User]:
    session = db.scalar(select(UserSession).where(UserSession.token_hash == hash_token(token)))
    if not session or is_expired(session.expires_at):
        return None
    session.last_seen_at = utcnow()
    return resolve_merged_user(db, db.get(User, session.user_id))


def bearer_token(request: Request) -> Optional[str]:
    """Read a mini-program/API client token from the Authorization header."""
    header = request.headers.get("authorization") or ""
    scheme, _, value = header.partition(" ")
    if scheme.lower() != "bearer":
        return None
    token = value.strip()
    return token or None


def request_token(request: Request) -> Optional[str]:
    return request.cookies.get(COOKIE_NAME) or bearer_token(request)


def user_from_request(db: Session, request: Request) -> Optional[User]:
    token = request_token(request)
    if not token:
        return None
    return get_user_by_session(db, token)


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def session_expiry(request: Request) -> Optional[str]:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    return None


def ensure_not_expired(value) -> None:  # noqa: ANN001
    if is_expired(as_utc(value)):
        raise AppError(401, "SESSION_EXPIRED", "登录已过期，请重新登录")
