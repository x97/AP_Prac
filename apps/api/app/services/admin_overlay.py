from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.users.models import AdminContentRecord, AdminContentRevision, AdminUser

SUBJECT_ID = "psychology"
ORIGIN_CREATED = "admin_created"
ORIGIN_EDITED = "admin_edited"
ORIGIN_DELETED = "admin_deleted"
VALID_ORIGINS = {ORIGIN_CREATED, ORIGIN_EDITED, ORIGIN_DELETED}
ENTITY_TYPES = {
    "paper",
    "question",
    "concept",
    "knowledge_point",
    "question_concept_link",
    "question_kp_link",
}


def get_revision(db: Session, subject_id: str = SUBJECT_ID) -> int:
    row = db.get(AdminContentRevision, subject_id)
    return int(row.revision) if row else 0


def bump_revision(db: Session, subject_id: str = SUBJECT_ID) -> int:
    row = db.get(AdminContentRevision, subject_id)
    if row is None:
        row = AdminContentRevision(subject_id=subject_id, revision=1)
        db.add(row)
    else:
        row.revision = int(row.revision) + 1
        row.updated_at = utcnow()
    db.flush()
    return int(row.revision)


def get_record(
    db: Session,
    entity_type: str,
    entity_id: str,
    subject_id: str = SUBJECT_ID,
) -> Optional[AdminContentRecord]:
    return db.scalar(
        select(AdminContentRecord).where(
            AdminContentRecord.subject_id == subject_id,
            AdminContentRecord.entity_type == entity_type,
            AdminContentRecord.entity_id == entity_id,
        )
    )


def save_record(
    db: Session,
    admin: Optional[AdminUser],
    entity_type: str,
    entity_id: str,
    origin: str,
    data: dict[str, Any],
    *,
    subject_id: str = SUBJECT_ID,
    base_release_id: Optional[str] = None,
) -> AdminContentRecord:
    if entity_type not in ENTITY_TYPES:
        raise ValueError(f"unsupported admin content entity type: {entity_type}")
    if origin not in VALID_ORIGINS:
        raise ValueError(f"unsupported admin content origin: {origin}")
    row = get_record(db, entity_type, entity_id, subject_id)
    if row is None:
        row = AdminContentRecord(
            subject_id=subject_id,
            entity_type=entity_type,
            entity_id=entity_id,
            origin=origin,
            data=data,
            base_release_id=base_release_id,
            created_by=admin.id if admin else None,
        )
        db.add(row)
    else:
        # A created entity stays "created" when edited later.
        if row.origin != ORIGIN_CREATED or origin == ORIGIN_DELETED:
            row.origin = origin
        row.data = data
        row.base_release_id = base_release_id or row.base_release_id
    db.flush()
    bump_revision(db, subject_id)
    return row


def load_records(
    db: Session, subject_id: str = SUBJECT_ID
) -> list[AdminContentRecord]:
    return list(
        db.scalars(
            select(AdminContentRecord)
            .where(AdminContentRecord.subject_id == subject_id)
            .order_by(AdminContentRecord.updated_at, AdminContentRecord.id)
        ).all()
    )


def records_by_type(
    db: Session, subject_id: str = SUBJECT_ID
) -> dict[str, list[AdminContentRecord]]:
    return group_records(load_records(db, subject_id))


def group_records(records: Iterable[AdminContentRecord]) -> dict[str, list[AdminContentRecord]]:
    out: dict[str, list[AdminContentRecord]] = {}
    for row in records:
        out.setdefault(row.entity_type, []).append(row)
    return out


def record_payload(row: AdminContentRecord) -> dict[str, Any]:
    return {
        "id": row.id,
        "entity_type": row.entity_type,
        "entity_id": row.entity_id,
        "origin": row.origin,
        "data": row.data,
        "base_release_id": row.base_release_id,
        "updated_at": row.updated_at.isoformat() if isinstance(row.updated_at, datetime) else None,
    }
