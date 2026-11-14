"""Subject entitlements, free previews, and access checks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import REPO_ROOT
from app.core.errors import AppError
from app.core.time import as_utc, utcnow
from app.services.subject_catalog import all_subject_configs
from app.users.models import UserEntitlement

SUBJECT_CONFIG_DIR = REPO_ROOT / "config" / "subjects"
FREE_CONFIG_DIR = REPO_ROOT / "config" / "entitlements"


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def enabled_subject_ids() -> list[str]:
    subject_ids = []
    if not SUBJECT_CONFIG_DIR.exists():
        return ["psychology"]
    for path in sorted(SUBJECT_CONFIG_DIR.glob("*.json")):
        payload = _read_json(path)
        if payload.get("enabled") and payload.get("subject_id"):
            subject_ids.append(str(payload["subject_id"]))
    return subject_ids or ["psychology"]


def free_config(subject_id: str) -> dict[str, Any]:
    return _read_json(FREE_CONFIG_DIR / f"{subject_id}.json")


def is_free_unit(subject_id: str, unit_id: str | int | None) -> bool:
    if unit_id is None:
        return False
    free_units = {str(item) for item in free_config(subject_id).get("free_unit_ids", [])}
    return str(unit_id) in free_units


def is_free_paper(subject_id: str, paper_id: str) -> bool:
    free_papers = {str(item) for item in free_config(subject_id).get("free_paper_ids", [])}
    return paper_id in free_papers


def active_entitlements(db: Session, user_id: str) -> dict[str, UserEntitlement]:
    now = utcnow()
    rows = db.scalars(
        select(UserEntitlement).where(
            UserEntitlement.user_id == user_id,
            UserEntitlement.expires_at > now,
        )
    )
    return {row.subject_id: row for row in rows}


def has_subject_access(db: Session, user_id: str, subject_id: str) -> bool:
    now = utcnow()
    row = db.scalar(
        select(UserEntitlement).where(
            UserEntitlement.user_id == user_id,
            UserEntitlement.subject_id == subject_id,
            UserEntitlement.expires_at > now,
        )
    )
    return row is not None


def entitlement_payload(db: Session, user_id: str) -> list[dict[str, Any]]:
    active = active_entitlements(db, user_id)
    configs = {item["subject_id"]: item for item in all_subject_configs()}
    # Include active entitlements whose config was removed/disabled so the
    # student can still see what they have activated.
    for subject_id in active:
        configs.setdefault(
            subject_id,
            {
                "subject_id": subject_id,
                "name": subject_id,
                "name_zh": subject_id,
                "enabled": False,
            },
        )
    out = []
    for subject_id, config in configs.items():
        row = active.get(subject_id)
        free = free_config(subject_id)
        out.append(
            {
                "subject_id": subject_id,
                "name": config.get("name") or subject_id,
                "name_zh": config.get("name_zh") or subject_id,
                "enabled": bool(config.get("enabled")),
                "active": row is not None,
                "expires_at": row.expires_at if row else None,
                "source": row.source if row else None,
                "free_unit_ids": free.get("free_unit_ids", []),
                "free_paper_ids": free.get("free_paper_ids", []),
            }
        )
    out.sort(
        key=lambda item: (
            not item["active"],
            not item["enabled"],
            str(item.get("name") or item["subject_id"]),
        )
    )
    return out


def _subject_from_store(store) -> str:
    return str(getattr(store, "subject_id", "psychology"))


def assert_group_access(db: Session, user_id: str, store, group_id: str) -> None:
    group = store.get_group(group_id)
    if not group:
        return
    subject_id = _subject_from_store(store)
    if is_free_unit(subject_id, group.get("unit_id")):
        return
    if subject_id not in active_entitlements(db, user_id):
        raise AppError(
            403,
            "SUBJECT_LOCKED",
            "该科目需要激活码才能继续使用",
            details={"subject_id": subject_id, "kind": "group", "group_id": group_id},
        )


def assert_paper_access(db: Session, user_id: str, store, paper_id: str) -> None:
    paper = store.get_paper(paper_id)
    if not paper:
        return
    subject_id = _subject_from_store(store)
    if is_free_paper(subject_id, paper_id):
        return
    if subject_id not in active_entitlements(db, user_id):
        raise AppError(
            403,
            "SUBJECT_LOCKED",
            "该科目需要激活码才能继续使用",
            details={"subject_id": subject_id, "kind": "paper", "paper_id": paper_id},
        )


def is_group_locked(db: Session, user_id: str, subject_id: str, unit_id) -> bool:
    return subject_id not in active_entitlements(db, user_id) and not is_free_unit(
        subject_id, unit_id
    )


def is_paper_locked(db: Session, user_id: str, subject_id: str, paper_id: str) -> bool:
    return subject_id not in active_entitlements(db, user_id) and not is_free_paper(
        subject_id, paper_id
    )


def mark_locked_groups(
    db: Session, user_id: str, subject_id: str, groups: Iterable[dict[str, Any]]
) -> None:
    active = subject_id in active_entitlements(db, user_id)
    for group in groups:
        group["locked"] = not active and not is_free_unit(subject_id, group.get("unit_id"))


def mark_locked_papers(
    db: Session, user_id: str, subject_id: str, papers: Iterable[dict[str, Any]]
) -> None:
    active = subject_id in active_entitlements(db, user_id)
    for paper in papers:
        paper["locked"] = not active and not is_free_paper(subject_id, paper.get("paper_id", ""))


def expires_iso(value) -> Optional[str]:
    if value is None:
        return None
    return as_utc(value).isoformat()
