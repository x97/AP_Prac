"""Activation code generation, redemption, and entitlement stacking."""

from __future__ import annotations

import base64
import hashlib
import os
import secrets
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.time import as_utc, utcnow
from app.services.entitlements import enabled_subject_ids
from app.users.models import (
    ActivationCode,
    ActivationCodeBatch,
    ActivationCodeRedemption,
    User,
    UserEntitlement,
)

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_PREFIX = "AP"
CODE_BODY_LENGTH = 12
SHANGHAI = ZoneInfo("Asia/Shanghai")
CODE_KDF_INFO = b"activation-code-encryption-v1"


def normalize_code(value: str) -> str:
    return "".join(ch for ch in (value or "").upper() if ch.isalnum())


def format_code(normalized: str) -> str:
    body = normalized
    if body.startswith(CODE_PREFIX):
        body = body[len(CODE_PREFIX) :]
    groups = [body[i : i + 4] for i in range(0, len(body), 4)]
    return f"{CODE_PREFIX}-" + "-".join(groups)


def _new_code() -> str:
    body = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_BODY_LENGTH))
    return CODE_PREFIX + body


def _hash_code(normalized: str) -> str:
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _code_key() -> bytes:
    settings = get_settings()
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"activation-code-store",
        info=CODE_KDF_INFO,
    ).derive(settings.secret_key.encode("utf-8"))


def _encrypt_code(normalized: str) -> str:
    nonce = os.urandom(12)
    ciphertext = AESGCM(_code_key()).encrypt(nonce, normalized.encode("utf-8"), None)
    return base64.b64encode(nonce + ciphertext).decode("ascii")


def _decrypt_code(value: str) -> str:
    raw = base64.b64decode(value, validate=True)
    return AESGCM(_code_key()).decrypt(raw[:12], raw[12:], None).decode("utf-8")


def _end_of_day(value: date) -> datetime:
    local = datetime.combine(value, time(23, 59, 59), tzinfo=SHANGHAI)
    return local.astimezone(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    return as_utc(value).isoformat() if value else None


def _batch_subjects(scope_type: str, subject_id: str | None) -> list[str]:
    if scope_type == "all":
        subjects = enabled_subject_ids()
        if not subjects:
            raise AppError(400, "NO_SUBJECTS", "没有已启用的科目")
        return subjects
    if not subject_id or subject_id not in enabled_subject_ids():
        raise AppError(400, "SUBJECT_INVALID", "科目不存在或未启用")
    return [subject_id]


def create_batch(
    db: Session,
    *,
    admin_id: str | None,
    scope_type: str,
    subject_id: str | None,
    duration_days: int | None,
    expires_on: date | None,
    count: int,
    note: str | None,
) -> tuple[ActivationCodeBatch, list[str]]:
    if count < 1 or count > 500:
        raise AppError(400, "CODE_COUNT_INVALID", "单批数量必须在 1 到 500 之间")
    if (duration_days is None) == (expires_on is None):
        raise AppError(400, "CODE_TERM_INVALID", "有效时长和指定日期必须二选一")
    if duration_days is not None and not (1 <= duration_days <= 3650):
        raise AppError(400, "CODE_TERM_INVALID", "有效时长必须在 1 到 3650 天之间")
    if expires_on is not None and expires_on < date.today():
        raise AppError(400, "CODE_DATE_INVALID", "指定日期不能早于今天")

    subject_ids = _batch_subjects(scope_type, subject_id)
    batch = ActivationCodeBatch(
        scope_type=scope_type,
        subject_ids=subject_ids,
        duration_days=duration_days,
        expires_on=expires_on,
        count=count,
        note=note,
        status="active",
        created_by=admin_id,
    )
    db.add(batch)
    db.flush()

    raw_codes: list[str] = []
    seen: set[str] = set()
    while len(raw_codes) < count:
        normalized = _new_code()
        code_hash = _hash_code(normalized)
        if code_hash in seen or db.scalar(
            select(ActivationCode.id).where(ActivationCode.code_hash == code_hash)
        ):
            continue
        seen.add(code_hash)
        raw_codes.append(format_code(normalized))
        db.add(
            ActivationCode(
                batch_id=batch.id,
                code_hash=code_hash,
                code_hint=normalized[-4:],
                code_ciphertext=_encrypt_code(normalized),
                max_uses=1,
                used_count=0,
                status="active",
            )
        )
    db.commit()
    db.refresh(batch)
    return batch, raw_codes


def batch_codes(db: Session, batch_id: str) -> list[ActivationCode]:
    return list(
        db.scalars(
            select(ActivationCode)
            .where(ActivationCode.batch_id == batch_id)
            .order_by(ActivationCode.created_at)
        )
    )


def batch_payload(db: Session, batch: ActivationCodeBatch) -> dict[str, Any]:
    codes = batch_codes(db, batch.id)
    used = sum(1 for code in codes if code.used_count > 0)
    voided = sum(1 for code in codes if code.status == "voided" and code.used_count == 0)
    return {
        "id": batch.id,
        "scope_type": batch.scope_type,
        "subject_ids": batch.subject_ids or [],
        "duration_days": batch.duration_days,
        "expires_on": batch.expires_on.isoformat() if batch.expires_on else None,
        "count": batch.count,
        "used": used,
        "voided": voided,
        "available": max(0, len(codes) - used - voided),
        "status": batch.status,
        "note": batch.note,
        "created_at": batch.created_at,
        "voided_at": batch.voided_at,
    }


def code_payload(code: ActivationCode) -> dict[str, Any]:
    return {
        "id": code.id,
        "batch_id": code.batch_id,
        "hint": f"••••-{code.code_hint}",
        "status": code.status,
        "used_count": code.used_count,
        "max_uses": code.max_uses,
        "created_at": code.created_at,
        "last_used_at": code.last_used_at,
        "voided_at": code.voided_at,
    }


def batch_download_text(db: Session, batch: ActivationCodeBatch) -> str:
    codes = batch_codes(db, batch.id)
    term = (
        f"until {batch.expires_on.isoformat()}"
        if batch.expires_on
        else f"{batch.duration_days} days"
    )
    lines = [
        "# AP Psychology activation codes",
        f"# batch: {batch.id}",
        f"# subjects: {', '.join(batch.subject_ids or [])}",
        f"# term: {term}",
        f"# count: {len(codes)}",
        "",
    ]
    lines.extend(format_code(_decrypt_code(code.code_ciphertext)) for code in codes)
    return "\n".join(lines) + "\n"


def void_code(db: Session, code: ActivationCode, admin_id: str | None) -> None:
    if code.status == "used" or code.used_count > 0:
        raise AppError(409, "CODE_ALREADY_USED", "已使用的激活码不能作废")
    if code.status == "voided":
        return
    code.status = "voided"
    code.voided_at = utcnow()
    db.commit()


def void_batch(db: Session, batch: ActivationCodeBatch, admin_id: str | None) -> None:
    if batch.status == "voided":
        return
    batch.status = "voided"
    batch.voided_at = utcnow()
    batch.voided_by = admin_id
    now = utcnow()
    for code in batch_codes(db, batch.id):
        if code.status == "active" and code.used_count == 0:
            code.status = "voided"
            code.voided_at = now
    db.commit()


def redeem(db: Session, user: User, raw_code: str) -> dict[str, Any]:
    normalized = normalize_code(raw_code)
    if len(normalized) < 6:
        raise AppError(400, "CODE_INVALID", "激活码格式不正确")
    code = db.scalar(
        select(ActivationCode)
        .where(ActivationCode.code_hash == _hash_code(normalized))
        .with_for_update()
    )
    if not code:
        raise AppError(404, "CODE_NOT_FOUND", "激活码不存在")
    batch = db.get(ActivationCodeBatch, code.batch_id)
    if not batch:
        raise AppError(404, "CODE_NOT_FOUND", "激活码批次不存在")
    if code.status == "voided" or batch.status == "voided":
        raise AppError(409, "CODE_VOIDED", "激活码已作废")
    if code.status == "used" or code.used_count >= code.max_uses:
        raise AppError(409, "CODE_ALREADY_USED", "激活码已被使用")
    subject_ids = [str(item) for item in (batch.subject_ids or [])]
    if not subject_ids:
        raise AppError(400, "CODE_NO_SUBJECT", "激活码没有可激活的科目")

    now = utcnow()
    existing = {
        row.subject_id: row
        for row in db.scalars(
            select(UserEntitlement)
            .where(
                UserEntitlement.user_id == user.id,
                UserEntitlement.subject_id.in_(subject_ids),
            )
            .with_for_update()
        )
    }
    before: dict[str, str | None] = {}
    after: dict[str, str] = {}
    for subject_id in subject_ids:
        row = existing.get(subject_id)
        current = as_utc(row.expires_at) if row else None
        before[subject_id] = _iso(current)
        if batch.expires_on is not None:
            target = _end_of_day(batch.expires_on)
            if current is not None and current >= target:
                raise AppError(
                    409,
                    "CODE_ALREADY_COVERED",
                    "该科目已覆盖到指定日期，无法重复激活",
                    details={
                        "subject_id": subject_id,
                        "expires_at": _iso(current),
                        "target": _iso(target),
                    },
                )
            after[subject_id] = _iso(target) or ""
        else:
            base = current if current and current > now else now
            after[subject_id] = _iso(base + timedelta(days=int(batch.duration_days or 0))) or ""

    for subject_id, expires_at in after.items():
        row = existing.get(subject_id)
        if row:
            row.expires_at = datetime.fromisoformat(expires_at)
            row.source = "code"
            row.last_code_id = code.id
            row.updated_at = now
        else:
            db.add(
                UserEntitlement(
                    user_id=user.id,
                    subject_id=subject_id,
                    expires_at=datetime.fromisoformat(expires_at),
                    source="code",
                    last_code_id=code.id,
                )
            )

    code.used_count += 1
    code.last_used_at = now
    if code.used_count >= code.max_uses:
        code.status = "used"
    db.add(
        ActivationCodeRedemption(
            code_id=code.id,
            batch_id=batch.id,
            user_id=user.id,
            subject_ids=subject_ids,
            before_json=before,
            after_json=after,
        )
    )
    db.commit()
    return {
        "ok": True,
        "subjects": [
            {
                "subject_id": subject_id,
                "expires_at": after[subject_id],
                "previous_expires_at": before[subject_id],
            }
            for subject_id in subject_ids
        ],
    }
