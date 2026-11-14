from __future__ import annotations

import json
import os
import shutil
import sqlite3
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Optional

from sqlalchemy.orm import Session

from app.core.config import get_settings, release_includes_subject
from app.services import admin_overlay

SUBJECT_ID = "psychology"
MARKER_COLUMNS = ("admin_origin", "admin_updated_at")
MARKER_TABLES = {
    "exam": ("papers", "questions", "options"),
    "knowledge": (
        "concept_clusters",
        "knowledge_points",
        "question_concept_links",
        "question_kp_links",
    ),
}


def _manifest(path: Path) -> dict[str, Any]:
    try:
        return json.loads((path / "release.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _release_id(base: Path) -> str:
    payload = _manifest(base)
    return str(payload.get("release_id") or base.name)


def _body(conn: sqlite3.Connection, table: str) -> list[str]:
    return [str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})")]


def _ensure_marker_columns(conn: sqlite3.Connection, table: str) -> None:
    cols = set(_body(conn, table))
    if not cols:
        return
    for column in MARKER_COLUMNS:
        if column not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} TEXT")


def _copy_db(source: Path, target: Path) -> None:
    src = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
    dst = sqlite3.connect(str(target))
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()


def _insert(conn: sqlite3.Connection, table: str, data: dict[str, Any]) -> None:
    cols = set(_body(conn, table))
    payload = {key: value for key, value in data.items() if key in cols}
    if not payload:
        return
    keys = list(payload)
    placeholders = ",".join("?" for _ in keys)
    conn.execute(
        f"INSERT INTO {table} ({','.join(keys)}) VALUES ({placeholders})",
        [payload[key] for key in keys],
    )


def _update(
    conn: sqlite3.Connection,
    table: str,
    key_column: str,
    key_value: Any,
    data: dict[str, Any],
) -> bool:
    cols = set(_body(conn, table))
    payload = {
        key: value
        for key, value in data.items()
        if key in cols and key != key_column
    }
    if not payload:
        return False
    assignments = ", ".join(f"{key}=?" for key in payload)
    cur = conn.execute(
        f"UPDATE {table} SET {assignments} WHERE {key_column}=?",
        [payload[key] for key in payload] + [key_value],
    )
    return cur.rowcount > 0


def _upsert_entity(
    conn: sqlite3.Connection,
    table: str,
    key_column: str,
    data: dict[str, Any],
    origin: str,
    now: str,
) -> None:
    payload = {
        **data,
        "admin_origin": origin,
        "admin_updated_at": now,
    }
    if not _update(conn, table, key_column, data.get(key_column), payload):
        _insert(conn, table, payload)


def _apply_papers(conn: sqlite3.Connection, records: Iterable[Any], now: str) -> None:
    for row in records:
        if row.origin == admin_overlay.ORIGIN_DELETED:
            continue
        data = dict(row.data or {})
        _upsert_entity(conn, "papers", "paper_id", data, row.origin, now)


def _apply_questions(conn: sqlite3.Connection, records: Iterable[Any], now: str) -> None:
    for row in records:
        if row.origin == admin_overlay.ORIGIN_DELETED:
            question_id = str((row.data or {}).get("question_id") or row.entity_id)
            conn.execute("DELETE FROM questions WHERE question_id=?", (question_id,))
            continue
        data = dict(row.data or {})
        question_id = str(data.get("question_id") or row.entity_id)
        data["question_id"] = question_id
        _upsert_entity(conn, "questions", "question_id", data, row.origin, now)
        options = data.get("options") or []
        if isinstance(options, list):
            conn.execute("DELETE FROM options WHERE question_id=?", (question_id,))
            for sort_order, option in enumerate(options, start=1):
                if not isinstance(option, dict):
                    continue
                _insert(
                    conn,
                    "options",
                    {
                        "question_id": question_id,
                        "label": str(option.get("label") or "").strip().upper(),
                        "content": str(option.get("content") or ""),
                        "sort_order": int(option.get("sort_order") or sort_order),
                        "is_correct": 1 if option.get("is_correct") else 0,
                        "explanation": option.get("explanation"),
                        "ai_explanation": option.get("ai_explanation"),
                        "admin_origin": row.origin,
                        "admin_updated_at": now,
                    },
                )
        cols = set(_body(conn, "question_display"))
        if cols:
            existing_display = conn.execute(
                "SELECT display_number FROM question_display WHERE question_id=?",
                (question_id,),
            ).fetchone()
            display_number = int(
                data.get("display_number")
                or (existing_display[0] if existing_display else 0)
                or data.get("number")
                or 0
            )
            if display_number:
                conn.execute(
                    "DELETE FROM question_display WHERE question_id=?", (question_id,)
                )
                _insert(
                    conn,
                    "question_display",
                    {
                        "question_id": question_id,
                        "display_number": display_number,
                        "note": "admin created/edited",
                    },
                )


def _apply_concepts(conn: sqlite3.Connection, records: Iterable[Any], now: str) -> None:
    for row in records:
        if row.origin == admin_overlay.ORIGIN_DELETED:
            continue
        data = dict(row.data or {})
        data.setdefault("subject_id", SUBJECT_ID)
        _upsert_entity(conn, "concept_clusters", "cluster_id", data, row.origin, now)


def _apply_kps(conn: sqlite3.Connection, records: Iterable[Any], now: str) -> None:
    for row in records:
        if row.origin == admin_overlay.ORIGIN_DELETED:
            continue
        data = dict(row.data or {})
        _upsert_entity(conn, "knowledge_points", "kp_id", data, row.origin, now)


def _apply_link_records(
    conn: sqlite3.Connection,
    records: Iterable[Any],
    now: str,
    *,
    table: str,
    id_column: str,
) -> None:
    cols = set(_body(conn, table))
    for row in records:
        data = dict(row.data or {})
        question_id = str(data.get("question_id") or "")
        target_id = str(
            data.get("concept_id") if table == "question_concept_links" else data.get("kp_id") or ""
        )
        relation_type = str(data.get("relation_type") or "")
        option_label = data.get("option_label")
        if not question_id or not target_id or not relation_type:
            continue
        conn.execute(
            f"""
            DELETE FROM {table}
            WHERE question_id=? AND {id_column}=? AND relation_type=?
              AND COALESCE(option_label,'')=COALESCE(?, '')
            """,
            (question_id, target_id, relation_type, option_label),
        )
        if row.origin == admin_overlay.ORIGIN_DELETED:
            continue
        next_id = conn.execute(
            f"SELECT COALESCE(MAX(link_id), 0) + 1 FROM {table}"
        ).fetchone()[0]
        _insert(
            conn,
            table,
            {
                "link_id": next_id,
                "question_id": question_id,
                id_column: target_id,
                "relation_type": relation_type,
                "option_label": option_label,
                "confidence": data.get("confidence"),
                "evidence": data.get("evidence"),
                "rationale": data.get("rationale"),
                "created_at": data.get("created_at")
                or datetime.now().astimezone().isoformat(timespec="seconds"),
                "admin_origin": row.origin,
                "admin_updated_at": now,
            },
        )


def _recalculate_papers(exam: sqlite3.Connection) -> None:
    exam.execute(
        """
        UPDATE papers
        SET question_count = (
            SELECT COUNT(*) FROM questions q WHERE q.paper_id = papers.paper_id
        )
        """
    )
    # Keep MCQ counts in sync with admin-created/deleted questions. FRQ counts
    # are intentionally left alone because a paper may carry two FRQ sets in
    # the source table while the exam config counts one set.
    for row in exam.execute(
        "SELECT paper_id, mcq_count FROM paper_exam_configs WHERE mcq_count IS NOT NULL AND mcq_count > 0"
    ).fetchall():
        actual = exam.execute(
            "SELECT COUNT(*) FROM questions WHERE paper_id=? AND section='MCQ'",
            (row["paper_id"],),
        ).fetchone()[0]
        if int(actual or 0) != int(row["mcq_count"] or 0):
            exam.execute(
                "UPDATE paper_exam_configs SET mcq_count=? WHERE paper_id=?",
                (actual, row["paper_id"]),
            )


def _write_manifest(staging: Path, base: Path, revision: int) -> None:
    payload = _manifest(base)
    payload["admin_revision"] = revision
    payload["effective_from_release"] = str(payload.get("release_id") or base.name)
    (staging / "release.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    exclusions = base / "exclusions.json"
    if exclusions.exists():
        shutil.copy2(exclusions, staging / "exclusions.json")
    manifest = base / "assets-manifest.json"
    if manifest.exists():
        shutil.copy2(manifest, staging / "assets-manifest.json")
    pronunciation_manifest = base / "pronunciation-manifest.json"
    if pronunciation_manifest.exists():
        shutil.copy2(pronunciation_manifest, staging / "pronunciation-manifest.json")


def _build(
    base: Path,
    target: Path,
    revision: int,
    records: list[Any],
) -> None:
    staging = target.parent / f".staging-{target.name}-{uuid.uuid4().hex[:8]}"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    try:
        _copy_db(base / "exam.db", staging / "exam.db")
        _copy_db(base / "knowledge.db", staging / "knowledge.db")
        _write_manifest(staging, base, revision)
        assets = base / "assets"
        if assets.exists():
            os.symlink(assets, staging / "assets", target_is_directory=True)
        else:
            (staging / "assets").mkdir()

        exam = sqlite3.connect(str(staging / "exam.db"))
        know = sqlite3.connect(str(staging / "knowledge.db"))
        exam.row_factory = sqlite3.Row
        know.row_factory = sqlite3.Row
        try:
            exam.execute("PRAGMA foreign_keys=ON")
            know.execute("PRAGMA foreign_keys=ON")
            for table in MARKER_TABLES["exam"]:
                _ensure_marker_columns(exam, table)
            for table in MARKER_TABLES["knowledge"]:
                _ensure_marker_columns(know, table)
            now = datetime.now().astimezone().isoformat(timespec="seconds")
            grouped = admin_overlay.group_records(records)
            with exam:
                _apply_papers(exam, grouped.get("paper", []), now)
                _apply_questions(exam, grouped.get("question", []), now)
                _recalculate_papers(exam)
            with know:
                _apply_concepts(know, grouped.get("concept", []), now)
                _apply_kps(know, grouped.get("knowledge_point", []), now)
                _apply_link_records(
                    know,
                    grouped.get("question_concept_link", []),
                    now,
                    table="question_concept_links",
                    id_column="concept_id",
                )
                _apply_link_records(
                    know,
                    grouped.get("question_kp_link", []),
                    now,
                    table="question_kp_links",
                    id_column="kp_id",
                )
        finally:
            exam.close()
            know.close()

        if target.exists():
            shutil.rmtree(staging)
        else:
            staging.rename(target)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def _pointer_matches(pointer: Path, target: Path) -> bool:
    try:
        return pointer.resolve() == target.resolve()
    except OSError:
        return False


def _switch_pointer(subject_root: Path, target: Path) -> None:
    subject_root.mkdir(parents=True, exist_ok=True)
    tmp = subject_root / f".current-{uuid.uuid4().hex[:8]}"
    os.symlink(target.name, tmp, target_is_directory=True)
    os.replace(tmp, subject_root / "current")


def _cleanup(subject_root: Path, keep: Path) -> None:
    directories = [
        path
        for path in subject_root.iterdir()
        if path.is_dir()
        and not path.is_symlink()
        and path != keep
        and not path.name.startswith(".")
    ]
    directories.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    now = time.time()
    for path in directories[3:]:
        # Do not remove a directory that a long-running request may still use.
        try:
            if now - path.stat().st_mtime < 600:
                continue
        except OSError:
            continue
        shutil.rmtree(path, ignore_errors=True)


def ensure_effective_content(
    db: Session,
    subject_id: str = SUBJECT_ID,
    *,
    force_marker_columns: bool = False,
) -> Path:
    """Materialize Release + admin overlay and return the current directory.

    With no overlay and no force request, the immutable Release is returned;
    this keeps tests and a fresh install from copying content unnecessarily.
    Admin pages pass ``force_marker_columns=True`` so their read queries can
    always select the admin marker columns.
    """
    settings = get_settings()
    base = settings.resolve_base_content_dir(subject_id).resolve()
    revision = admin_overlay.get_revision(db, subject_id)
    if revision == 0 and not force_marker_columns:
        return settings.resolve_content_dir(subject_id)

    release_id = _release_id(base)
    subject_root = settings.effective_root / subject_id
    subject_root.mkdir(parents=True, exist_ok=True)
    target = subject_root / f"{release_id}-r{revision}"
    pointer = subject_root / "current"

    if revision == 0:
        # Even the marker-only materialization is keyed by release id.
        target = subject_root / f"{release_id}-r0"

    if not target.exists():
        records = admin_overlay.load_records(db, subject_id)
        _build(base, target, revision, records)
    if not _pointer_matches(pointer, target):
        _switch_pointer(subject_root, target)
    _cleanup(subject_root, target)
    return pointer
