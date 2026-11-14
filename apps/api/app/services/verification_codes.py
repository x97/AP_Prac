from __future__ import annotations

import secrets
from datetime import timedelta

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import hash_code
from app.core.time import is_expired, utcnow
from app.services.email import get_email_sender
from app.users.models import VerificationCode

CODE_PURPOSES = {"register", "reset", "bind_email"}


def _check_rate_limit(db: Session, identifier: str, ip: str, settings: Settings) -> None:
    now = utcnow()
    minute_ago = now - timedelta(minutes=1)
    hour_ago = now - timedelta(hours=1)

    same_identifier_minute = (
        db.scalar(
            select(func.count())
            .select_from(VerificationCode)
            .where(
                VerificationCode.identifier == identifier,
                VerificationCode.created_at >= minute_ago,
            )
        )
        or 0
    )
    same_identifier_hour = (
        db.scalar(
            select(func.count())
            .select_from(VerificationCode)
            .where(
                VerificationCode.identifier == identifier,
                VerificationCode.created_at >= hour_ago,
            )
        )
        or 0
    )
    same_ip_hour = (
        db.scalar(
            select(func.count())
            .select_from(VerificationCode)
            .where(
                VerificationCode.ip == ip,
                VerificationCode.created_at >= hour_ago,
            )
        )
        or 0
    )

    if (
        same_identifier_minute >= settings.otp_email_per_minute
        or same_identifier_hour >= settings.otp_email_per_hour
        or (ip and same_ip_hour >= settings.otp_ip_per_hour)
    ):
        raise AppError(429, "EMAIL_CODE_RATE_LIMITED", "验证码发送过于频繁，请稍后再试")


def issue_code(
    db: Session,
    *,
    identifier: str,
    purpose: str,
    ip: str,
    settings: Settings,
) -> dict:
    if purpose not in CODE_PURPOSES:
        raise AppError(400, "CODE_PURPOSE_INVALID", "验证码用途不合法")

    _check_rate_limit(db, identifier, ip, settings)
    now = utcnow()

    # Only the newest code for a purpose may be valid.
    db.execute(
        update(VerificationCode)
        .where(
            VerificationCode.identifier == identifier,
            VerificationCode.purpose == purpose,
            VerificationCode.consumed_at.is_(None),
        )
        .values(consumed_at=now)
    )

    is_dev = settings.email_provider == "dev"
    code = settings.dev_otp_code if is_dev else f"{secrets.randbelow(10**6):06d}"
    db.add(
        VerificationCode(
            identifier=identifier,
            channel="email",
            purpose=purpose,
            code_hash=hash_code(settings.secret_key, purpose, identifier, code),
            expires_at=now + timedelta(seconds=settings.otp_ttl_seconds),
            ip=ip,
        )
    )
    db.flush()

    try:
        get_email_sender(settings).send_code(identifier, code, purpose)
    except RuntimeError as exc:
        db.rollback()
        raise AppError(
            502, "EMAIL_SEND_FAILED", "验证码邮件发送失败，请稍后重试"
        ) from exc

    db.commit()
    result: dict = {"ok": True, "expires_in": settings.otp_ttl_seconds}
    if is_dev and settings.expose_dev_otp:
        result["debug_code"] = code
    return result


def verify_code(
    db: Session,
    *,
    identifier: str,
    purpose: str,
    code: str,
    settings: Settings,
) -> None:
    if purpose not in CODE_PURPOSES:
        raise AppError(400, "CODE_PURPOSE_INVALID", "验证码用途不合法")

    record = db.scalar(
        select(VerificationCode)
        .where(
            VerificationCode.identifier == identifier,
            VerificationCode.purpose == purpose,
            VerificationCode.consumed_at.is_(None),
        )
        .order_by(VerificationCode.created_at.desc())
        .limit(1)
    )
    if not record or is_expired(record.expires_at):
        raise AppError(400, "EMAIL_CODE_EXPIRED", "验证码已过期，请重新获取")
    if record.attempts >= settings.otp_max_attempts:
        raise AppError(429, "EMAIL_CODE_LOCKED", "验证码尝试次数过多，请重新获取")

    record.attempts += 1
    expected = hash_code(settings.secret_key, purpose, identifier, code.strip())
    if not secrets.compare_digest(record.code_hash, expected):
        db.commit()
        raise AppError(400, "EMAIL_CODE_INVALID", "验证码不正确")

    record.consumed_at = utcnow()
    db.flush()
