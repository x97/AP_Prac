from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from app.core.config import REPO_ROOT, get_settings
from app.core.errors import AppError

SUBJECT_ID = "psychology"
_EXAM_DB_OVERRIDE: Optional[Path] = None
_KNOWLEDGE_DB_OVERRIDE: Optional[Path] = None


def _subject_config(subject_id: str = SUBJECT_ID) -> dict[str, Any]:
    path = REPO_ROOT / "config" / "subjects" / f"{subject_id}.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AppError(503, "SUBJECT_CONFIG_MISSING", f"科目配置不可用: {subject_id}") from exc


def _release_paths() -> tuple[Path, Path]:
    """Read-only DBs from the active Release."""
    try:
        release_dir = get_settings().resolve_content_dir(SUBJECT_ID)
    except RuntimeError as exc:
        raise AppError(503, "CONTENT_NOT_READY", "暂无可用内容版本") from exc
    exam_db = release_dir / "exam.db"
    knowledge_db = release_dir / "knowledge.db"
    if not exam_db.exists() or not knowledge_db.exists():
        raise AppError(503, "CONTENT_NOT_READY", "active Release 缺少 exam.db / knowledge.db")
    return exam_db, knowledge_db


def _source_paths() -> tuple[Path, Path]:
    """Writable subject source DBs. Admin writes never touch a Release."""
    config = _subject_config()
    source = REPO_ROOT / str(config["source_dir"])
    return source / str(config["exam_db"]), source / str(config["knowledge_db"])


def _read_paths() -> tuple[Path, Path]:
    if _EXAM_DB_OVERRIDE is not None and _KNOWLEDGE_DB_OVERRIDE is not None:
        return _EXAM_DB_OVERRIDE, _KNOWLEDGE_DB_OVERRIDE
    return _release_paths()


def _write_paths() -> tuple[Path, Path]:
    if _EXAM_DB_OVERRIDE is not None and _KNOWLEDGE_DB_OVERRIDE is not None:
        return _EXAM_DB_OVERRIDE, _KNOWLEDGE_DB_OVERRIDE
    return _source_paths()


def _connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    return conn


def _rows(path: Path, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    conn = _connect(path)
    try:
        return [dict(row) for row in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def _one(path: Path, sql: str, params: tuple[Any, ...] = ()) -> Optional[dict[str, Any]]:
    conn = _connect(path)
    try:
        row = conn.execute(sql, params).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def _write_connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path), timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def list_papers(
    db_path: Optional[Path] = None, subject_id: str = SUBJECT_ID
) -> list[dict[str, Any]]:
    exam_db = db_path or _read_paths()[0]
    return _rows(
        exam_db,
        """
        SELECT p.paper_id, p.year, p.title, p.chinese_title, p.subject_id,
               p.paper_type, p.source_pdf, p.question_count,
               p.admin_origin, p.admin_updated_at,
               CASE
                 WHEN p.paper_type IN ('practice_bundle','bundle') THEN
                   (SELECT COUNT(*) FROM paper_question_map m WHERE m.paper_id=p.paper_id)
                 ELSE
                   (SELECT COUNT(*) FROM questions q WHERE q.paper_id=p.paper_id)
               END AS actual_questions,
               CASE
                 WHEN p.paper_type IN ('practice_bundle','bundle') THEN
                   (SELECT COUNT(*) FROM paper_question_map m
                    JOIN questions q ON q.question_id=m.question_id
                    WHERE m.paper_id=p.paper_id AND q.section='MCQ')
                 ELSE
                   (SELECT COUNT(*) FROM questions q
                    WHERE q.paper_id=p.paper_id AND q.section='MCQ')
               END AS mcq_count,
               CASE
                 WHEN p.paper_type IN ('practice_bundle','bundle') THEN
                   (SELECT COUNT(*) FROM paper_question_map m
                    JOIN questions q ON q.question_id=m.question_id
                    WHERE m.paper_id=p.paper_id AND q.section='FRQ')
                 ELSE
                   (SELECT COUNT(*) FROM questions q
                    WHERE q.paper_id=p.paper_id AND q.section='FRQ')
               END AS frq_count
        FROM papers p
        WHERE p.subject_id=?
        ORDER BY p.year DESC, p.paper_type, p.paper_id
        """,
        (subject_id,),
    )


def get_paper(
    paper_id: str,
    db_path: Optional[Path] = None,
    subject_id: str = SUBJECT_ID,
) -> Optional[dict[str, Any]]:
    exam_db = db_path or _read_paths()[0]
    return _one(
        exam_db,
        """
        SELECT p.paper_id, p.year, p.title, p.chinese_title, p.subject_id,
               p.paper_type, p.source_pdf, p.question_count,
               p.admin_origin, p.admin_updated_at
        FROM papers p
        WHERE p.paper_id=? AND p.subject_id=?
        """,
        (paper_id, subject_id),
    )


def list_questions(
    paper_id: str,
    db_path: Optional[Path] = None,
    subject_id: str = SUBJECT_ID,
) -> list[dict[str, Any]]:
    exam_db = db_path or _read_paths()[0]
    paper = get_paper(paper_id, db_path=exam_db, subject_id=subject_id)
    is_bundle = bool(paper and paper.get("paper_type") in ("practice_bundle", "bundle"))
    if is_bundle:
        return _rows(
            exam_db,
            """
            SELECT q.question_id, q.paper_id, q.section, q.number, q.form, q.stem,
                   q.answer_source, q.answer_confidence, q.subject_id,
                   q.admin_origin, q.admin_updated_at,
                   m.source_paper_id, m.sort_order AS bundle_sort_order,
                   (SELECT COUNT(*) FROM options o
                    WHERE o.question_id=q.question_id) AS option_count,
                   (SELECT COUNT(*) FROM options o
                    WHERE o.question_id=q.question_id AND o.is_correct=1) AS correct_count
            FROM paper_question_map m
            JOIN questions q ON q.question_id=m.question_id
            WHERE m.paper_id=? AND q.subject_id=?
            ORDER BY CASE q.section WHEN 'MCQ' THEN 0 ELSE 1 END,
                     COALESCE(m.sort_order, q.number), q.number, q.form
            """,
            (paper_id, subject_id),
        )
    return _rows(
        exam_db,
        """
        SELECT q.question_id, q.paper_id, q.section, q.number, q.form, q.stem,
               q.answer_source, q.answer_confidence, q.subject_id,
               q.admin_origin, q.admin_updated_at,
               (SELECT COUNT(*) FROM options o WHERE o.question_id=q.question_id) AS option_count,
               (SELECT COUNT(*) FROM options o
                WHERE o.question_id=q.question_id AND o.is_correct=1) AS correct_count
        FROM questions q
        WHERE q.paper_id=? AND q.subject_id=?
        ORDER BY CASE q.section WHEN 'MCQ' THEN 0 ELSE 1 END, q.number, q.form
        """,
        (paper_id, subject_id),
    )


def get_question(
    question_id: str,
    db_path: Optional[Path] = None,
    subject_id: str = SUBJECT_ID,
) -> Optional[dict[str, Any]]:
    exam_db = db_path or _read_paths()[0]
    question = _one(
        exam_db,
        """
        SELECT q.question_id, q.paper_id, q.section, q.number, q.form, q.stem,
               q.context, q.correct_answer, q.answer_text, q.answer_source,
               q.answer_confidence, q.subject_id, q.admin_origin, q.admin_updated_at
        FROM questions q
        WHERE q.question_id=? AND q.subject_id=?
        """,
        (question_id, subject_id),
    )
    if not question:
        return None
    question["options"] = _rows(
        exam_db,
        """
        SELECT question_id, label, content, sort_order, is_correct, explanation,
               ai_explanation, admin_origin, admin_updated_at
        FROM options
        WHERE question_id=?
        ORDER BY sort_order, label
        """,
        (question_id,),
    )
    question["assets"] = _rows(
        exam_db,
        """
        SELECT asset_id, question_id, option_label, kind, path, page, bbox
        FROM assets
        WHERE question_id=?
        ORDER BY kind, option_label, asset_id
        """,
        (question_id,),
    )
    question["concepts"] = get_question_concepts(
        question_id, db_path=db_path, subject_id=subject_id
    )
    return question


def get_question_concepts(
    question_id: str,
    db_path: Optional[Path] = None,
    subject_id: str = SUBJECT_ID,
) -> list[dict[str, Any]]:
    knowledge_db = db_path or _read_paths()[1]
    return _rows(
        knowledge_db,
        """
        SELECT l.link_id, l.question_id, l.concept_id, l.relation_type,
               l.option_label, l.confidence, l.evidence, l.rationale,
               l.admin_origin, l.admin_updated_at,
               c.canonical_name, c.topic, c.ap_unit, c.weight, c.weight_tier
        FROM question_concept_links l
        LEFT JOIN concept_clusters c ON c.cluster_id=l.concept_id
        WHERE l.question_id=? AND c.subject_id=?
        ORDER BY CASE l.relation_type
                   WHEN 'core' THEN 0 WHEN 'supporting' THEN 1 ELSE 2 END,
                 c.canonical_name, l.option_label
        """,
        (question_id, subject_id),
    )


def concept_name_taken(
    name: str, exclude_id: str | None = None, subject_id: str = SUBJECT_ID
) -> bool:
    knowledge_db = _read_paths()[1]
    params: list[Any] = [subject_id, name.strip()]
    where = "WHERE subject_id=? AND lower(canonical_name)=lower(?)"
    if exclude_id:
        where += " AND cluster_id<>?"
        params.append(exclude_id)
    row = _one(
        knowledge_db,
        f"SELECT cluster_id FROM concept_clusters {where} LIMIT 1",
        tuple(params),
    )
    return row is not None


def bundle_practice_stats(paper_id: str) -> Optional[dict[str, Any]]:
    """Mapped vs usable vs excluded counts for a virtual practice bundle."""
    exam_db = _read_paths()[0]
    row = _one(
        exam_db,
        """
        SELECT g.group_id, g.unit_id,
               (SELECT COUNT(*) FROM paper_question_map m WHERE m.paper_id=?) AS mapped,
               (SELECT COUNT(DISTINCT ptq.question_id)
                FROM practice_topics pt
                JOIN practice_topic_questions ptq ON ptq.topic_id=pt.topic_id
                WHERE pt.group_id=g.group_id) AS usable
        FROM practice_groups g
        WHERE g.bundle_paper_id=?
        """,
        (paper_id, paper_id),
    )
    if not row:
        return None
    excluded = _one(
        exam_db,
        """
        SELECT COUNT(*) AS n
        FROM question_exclusions e
        WHERE e.question_id IN (
          SELECT question_id FROM paper_question_map WHERE paper_id=?
        )
        """,
        (paper_id,),
    )
    row["excluded"] = int((excluded or {}).get("n") or 0)
    return row


def list_question_units(
    db_path: Optional[Path] = None, subject_id: str = SUBJECT_ID
) -> list[dict[str, Any]]:
    exam_db = db_path or _read_paths()[0]
    units = _rows(
        exam_db,
        """
        SELECT g.unit_id, g.title, g.bundle_paper_id
        FROM practice_groups g
        WHERE g.subject_id=? AND g.status='active'
        ORDER BY CAST(g.unit_id AS INTEGER), g.unit_id
        """,
        (subject_id,),
    )
    # Unit 0 (Science Practices) has concepts but no practice bundle.
    if not any(str(item["unit_id"]) == "0" for item in units):
        units.insert(
            0,
            {"unit_id": "0", "title": "Unit 0", "bundle_paper_id": None},
        )
    return units


def list_all_questions(
    source: str = "all",
    unit_id: Optional[str] = None,
    topic_id: Optional[str] = None,
    paper_id: Optional[str] = None,
    section: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db_path: Optional[Path] = None,
    knowledge_db_path: Optional[Path] = None,
    subject_id: str = SUBJECT_ID,
) -> dict[str, Any]:
    """Cross-paper question list for the admin question browser.

    ``source=unit`` selects questions mapped into a unit practice bundle via
    ``paper_question_map``. Unit 0 has no practice bundle, so it selects
    questions linked to concepts with ``ap_unit='0'`` instead. Other sources
    map to ``papers.paper_type``. ``unit_id`` and ``topic_id`` also work
    independently of ``source`` for the study-plan question picker.
    """
    exam_db = db_path or _read_paths()[0]
    clauses = ["q.subject_id = ?"]
    params: list[Any] = [subject_id]
    if str(unit_id or "") == "0" and (source == "unit" or unit_id):
        knowledge_db = knowledge_db_path or _read_paths()[1]
        unit0_ids = [
            str(row["question_id"])
            for row in _rows(
                knowledge_db,
                """
                SELECT DISTINCT l.question_id
                FROM question_concept_links l
                JOIN concept_clusters c ON c.cluster_id=l.concept_id
                WHERE c.subject_id=? AND c.ap_unit='0'
                """,
                (subject_id,),
            )
        ]
        if unit0_ids:
            clauses.append(
                f"q.question_id IN ({','.join('?' for _ in unit0_ids)})"
            )
            params.extend(unit0_ids)
        else:
            clauses.append("0=1")
    elif unit_id or source == "unit":
        unit_clause = (
            "EXISTS (SELECT 1 FROM paper_question_map m "
            "JOIN practice_groups g ON g.bundle_paper_id = m.paper_id "
            "WHERE m.question_id = q.question_id AND g.subject_id = ?"
        )
        params.append(subject_id)
        if unit_id:
            unit_clause += " AND g.unit_id = ?"
            params.append(str(unit_id))
        clauses.append(unit_clause + ")")
    if source in ("real_exam", "mock_exam", "unit_practice"):
        clauses.append("p.paper_type = ?")
        params.append(source)
    if topic_id:
        clauses.append(
            "EXISTS (SELECT 1 FROM practice_topic_questions ptq "
            "WHERE ptq.topic_id = ? AND ptq.question_id = q.question_id)"
        )
        params.append(str(topic_id))
    if paper_id:
        clauses.append("q.paper_id = ?")
        params.append(str(paper_id))
    if section in ("MCQ", "FRQ"):
        clauses.append("q.section = ?")
        params.append(section)
    needle = (q or "").strip()
    if needle:
        clauses.append("(q.stem LIKE ? OR q.question_id LIKE ?)")
        params.extend([f"%{needle}%", f"%{needle}%"])
    where = " AND ".join(clauses)
    total = _one(
        exam_db,
        f"""
        SELECT COUNT(*) AS n
        FROM questions q
        JOIN papers p ON p.paper_id=q.paper_id
        WHERE {where}
        """,
        tuple(params),
    )
    rows = _rows(
        exam_db,
        f"""
        SELECT q.question_id, q.paper_id, q.section, q.number, q.form, q.stem,
               q.answer_source, q.answer_confidence, q.subject_id,
               q.admin_origin, q.admin_updated_at,
               p.paper_type, p.title AS paper_title,
               p.chinese_title AS paper_chinese_title, p.year,
               (SELECT COUNT(*) FROM options o WHERE o.question_id=q.question_id) AS option_count,
               (SELECT COUNT(*) FROM options o
                WHERE o.question_id=q.question_id AND o.is_correct=1) AS correct_count
        FROM questions q
        JOIN papers p ON p.paper_id=q.paper_id
        WHERE {where}
        ORDER BY p.year DESC,
                 CASE p.paper_type
                   WHEN 'real_exam' THEN 0
                   WHEN 'mock_exam' THEN 1
                   WHEN 'unit_practice' THEN 2
                   ELSE 3
                 END,
                 p.paper_id,
                 CASE q.section WHEN 'MCQ' THEN 0 ELSE 1 END,
                 q.number, q.form
        LIMIT ? OFFSET ?
        """,
        tuple(params + [limit, max(0, offset)]),
    )
    if rows:
        ids = [str(row["question_id"]) for row in rows]
        placeholders = ",".join("?" for _ in ids)
        unit_rows = _rows(
            exam_db,
            f"""
            SELECT m.question_id, g.unit_id
            FROM paper_question_map m
            JOIN practice_groups g ON g.bundle_paper_id = m.paper_id
            WHERE m.question_id IN ({placeholders}) AND g.subject_id=?
            ORDER BY CAST(g.unit_id AS INTEGER)
            """,
            tuple(ids + [subject_id]),
        )
        unit_map: dict[str, list[str]] = {}
        for unit_row in unit_rows:
            unit_map.setdefault(str(unit_row["question_id"]), []).append(
                str(unit_row["unit_id"])
            )
        for row in rows:
            row["unit_ids"] = unit_map.get(str(row["question_id"]), [])
    return {
        "questions": rows,
        "total": int((total or {}).get("n") or 0),
        "units": list_question_units(exam_db, subject_id),
    }


def list_all_question_ids(
    source: str = "all",
    unit_id: Optional[str] = None,
    topic_id: Optional[str] = None,
    paper_id: Optional[str] = None,
    section: Optional[str] = None,
    q: Optional[str] = None,
    max_ids: int = 2000,
    db_path: Optional[Path] = None,
    knowledge_db_path: Optional[Path] = None,
    subject_id: str = SUBJECT_ID,
) -> dict[str, Any]:
    """Return all matching question ids for the picker's select-all action."""
    max_ids = max(1, min(int(max_ids), 2000))
    ids: list[str] = []
    total = 0
    offset = 0
    while len(ids) < max_ids:
        page_limit = min(200, max_ids - len(ids))
        page = list_all_questions(
            source=source,
            unit_id=unit_id,
            topic_id=topic_id,
            paper_id=paper_id,
            section=section,
            q=q,
            limit=page_limit,
            offset=offset,
            db_path=db_path,
            knowledge_db_path=knowledge_db_path,
            subject_id=subject_id,
        )
        total = int(page.get("total") or 0)
        rows = page.get("questions") or []
        ids.extend(str(row["question_id"]) for row in rows)
        offset += len(rows)
        if len(rows) < page_limit:
            break
    return {
        "question_ids": ids,
        "total": total,
        "truncated": total > len(ids),
    }


def next_question_number(
    paper_id: str, section: str, subject_id: str = SUBJECT_ID
) -> int:
    exam_db = _read_paths()[0]
    row = _one(
        exam_db,
        "SELECT COALESCE(MAX(number), 0) + 1 AS n FROM questions "
        "WHERE paper_id=? AND section=? AND subject_id=?",
        (paper_id, section, subject_id),
    )
    return int((row or {}).get("n") or 1)


def list_concepts(
    q: Optional[str],
    limit: int,
    offset: int = 0,
    db_path: Optional[Path] = None,
    subject_id: str = SUBJECT_ID,
) -> list[dict[str, Any]]:
    knowledge_db = db_path or _read_paths()[1]
    params: list[Any] = [subject_id]
    where = "WHERE subject_id=?"
    if q:
        where += " AND canonical_name LIKE ?"
        params.append(f"%{q}%")
    params.extend([limit, max(0, offset)])
    return _rows(
        knowledge_db,
        f"""
        SELECT cluster_id, subject_id, canonical_name, description, ap_unit, topic,
               status, weight, weight_tier, member_count, canonical_kp_id,
               admin_origin, admin_updated_at
        FROM concept_clusters
        {where}
        ORDER BY CASE WHEN admin_origin IS NOT NULL THEN 0 ELSE 1 END,
                 weight DESC, canonical_name
        LIMIT ? OFFSET ?
        """,
        tuple(params),
    )


def count_concepts(
    q: Optional[str], db_path: Optional[Path] = None, subject_id: str = SUBJECT_ID
) -> int:
    knowledge_db = db_path or _read_paths()[1]
    params: list[Any] = [subject_id]
    where = "WHERE subject_id=?"
    if q:
        where += " AND canonical_name LIKE ?"
        params.append(f"%{q}%")
    row = _one(
        knowledge_db,
        f"SELECT COUNT(*) AS n FROM concept_clusters {where}",
        tuple(params),
    )
    return int((row or {}).get("n") or 0)


def get_concept(
    cluster_id: str,
    db_path: Optional[Path] = None,
    subject_id: str = SUBJECT_ID,
) -> Optional[dict[str, Any]]:
    knowledge_db = db_path or _read_paths()[1]
    concept = _one(
        knowledge_db,
        """
        SELECT cluster_id, subject_id, canonical_name, description, ap_unit, topic,
               status, weight, weight_tier, member_count, canonical_kp_id,
               admin_origin, admin_updated_at
        FROM concept_clusters
        WHERE cluster_id=? AND subject_id=?
        """,
        (cluster_id, subject_id),
    )
    if not concept:
        return None
    concept["members"] = _rows(
        knowledge_db,
        """
        SELECT kp.kp_id, kp.name, kp.plain_en, kp.definition_quote,
               kp.book_id, kp.section_id, kp.subheading, cm.confidence
        FROM concept_members cm
        JOIN knowledge_points kp ON kp.kp_id=cm.kp_id
        WHERE cm.cluster_id=?
        ORDER BY cm.confidence DESC, kp.kp_id
        """,
        (cluster_id,),
    )
    return concept


def list_kps(
    q: Optional[str],
    limit: int,
    offset: int = 0,
    db_path: Optional[Path] = None,
    subject_id: str = SUBJECT_ID,
) -> list[dict[str, Any]]:
    knowledge_db = db_path or _read_paths()[1]
    params: list[Any] = [f"{subject_id}-%"]
    where = "WHERE book_id LIKE ?"
    if q:
        where += " AND name LIKE ?"
        params.append(f"%{q}%")
    params.extend([limit, max(0, offset)])
    rows = _rows(
        knowledge_db,
        f"""
        SELECT kp_id, book_id, section_id, subheading, name, plain_en,
               definition_quote, status, confidence, weight, weight_tier,
               concept_cluster_id, admin_origin, admin_updated_at
        FROM knowledge_points
        {where}
        ORDER BY CASE WHEN admin_origin IS NOT NULL THEN 0 ELSE 1 END,
                 book_id, section_id, kp_id
        LIMIT ? OFFSET ?
        """,
        tuple(params),
    )
    for row in rows:
        row["subject_id"] = subject_id
    return rows


def count_kps(
    q: Optional[str], db_path: Optional[Path] = None, subject_id: str = SUBJECT_ID
) -> int:
    knowledge_db = db_path or _read_paths()[1]
    params: list[Any] = [f"{subject_id}-%"]
    where = "WHERE book_id LIKE ?"
    if q:
        where += " AND name LIKE ?"
        params.append(f"%{q}%")
    row = _one(
        knowledge_db,
        f"SELECT COUNT(*) AS n FROM knowledge_points {where}",
        tuple(params),
    )
    return int((row or {}).get("n") or 0)


def get_kp(
    kp_id: str,
    db_path: Optional[Path] = None,
    subject_id: str = SUBJECT_ID,
) -> Optional[dict[str, Any]]:
    knowledge_db = db_path or _read_paths()[1]
    row = _one(
        knowledge_db,
        """
        SELECT kp_id, book_id, section_id, subheading, name, plain_en,
               definition_quote, status, confidence, weight, weight_tier,
               concept_cluster_id, source_page, definition_type,
               admin_origin, admin_updated_at
        FROM knowledge_points
        WHERE kp_id=? AND book_id LIKE ?
        """,
        (kp_id, f"{subject_id}-%"),
    )
    if row:
        row["subject_id"] = subject_id
    return row


def update_paper(paper_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    exam_db, _ = _write_paths()
    paper = get_paper(paper_id, db_path=exam_db)
    if not paper:
        raise AppError(404, "PAPER_NOT_FOUND", "试卷不存在")
    allowed = {"year", "title", "chinese_title", "paper_type"}
    fields = {key: value for key, value in updates.items() if key in allowed}
    if not fields:
        return paper
    if "paper_type" in fields and not str(fields["paper_type"]).strip():
        raise AppError(400, "PAPER_TYPE_REQUIRED", "试卷类型不能为空")
    assignments = ", ".join(f"{key}=?" for key in fields)
    params = [fields[key] for key in fields] + [paper_id]
    conn = _write_connect(exam_db)
    try:
        with conn:
            conn.execute(
                f"UPDATE papers SET {assignments} WHERE paper_id=? AND subject_id='psychology'",
                params,
            )
    finally:
        conn.close()
    result = get_paper(paper_id, db_path=exam_db)
    if not result:
        raise AppError(404, "PAPER_NOT_FOUND", "试卷不存在")
    return result


def update_question(question_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    exam_db, _ = _write_paths()
    current = get_question(question_id, db_path=exam_db)
    if not current:
        raise AppError(404, "QUESTION_NOT_FOUND", "题目不存在")

    fields = {
        key: updates[key]
        for key in ("stem", "context", "answer_text", "answer_source", "answer_confidence")
        if key in updates
    }
    options = updates.get("options")
    correct_label: Optional[str] = None

    if options is not None:
        if len(options) < 2 or len(options) > 5:
            raise AppError(400, "OPTION_COUNT_INVALID", "选项数量必须在 2 到 5 个之间")
        labels = [str(item["label"]).strip().upper() for item in options]
        if len(set(labels)) != len(labels):
            raise AppError(400, "OPTION_LABEL_DUPLICATE", "选项标签不能重复")
        correct = [label for label, item in zip(labels, options) if bool(item.get("is_correct"))]
        if current["section"] == "MCQ" and len(correct) != 1:
            raise AppError(400, "MCQ_CORRECT_COUNT", "MCQ 必须恰好有一个正确选项")
        if len(correct) > 1:
            raise AppError(400, "MCQ_CORRECT_COUNT", "只能有一个正确选项")
        correct_label = correct[0] if correct else None

    conn = _write_connect(exam_db)
    try:
        with conn:
            if fields:
                assignments = ", ".join(f"{key}=?" for key in fields)
                conn.execute(
                    f"UPDATE questions SET {assignments} WHERE question_id=?",
                    [fields[key] for key in fields] + [question_id],
                )
            if options is not None:
                conn.execute("DELETE FROM options WHERE question_id=?", (question_id,))
                for sort_order, item in enumerate(options, start=1):
                    label = str(item["label"]).strip().upper()
                    conn.execute(
                        """
                        INSERT INTO options
                          (question_id, label, content, sort_order, is_correct,
                           explanation, ai_explanation)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            question_id,
                            label,
                            str(item.get("content") or ""),
                            sort_order,
                            1 if label == correct_label else 0,
                            item.get("explanation"),
                            item.get("ai_explanation"),
                        ),
                    )
                if correct_label:
                    conn.execute(
                        "UPDATE questions SET correct_answer=? WHERE question_id=?",
                        (correct_label, question_id),
                    )
    finally:
        conn.close()
    result = get_question(question_id, db_path=exam_db)
    if not result:
        raise AppError(404, "QUESTION_NOT_FOUND", "题目不存在")
    return result


def update_concept(cluster_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    _, knowledge_db = _write_paths()
    if not get_concept(cluster_id, db_path=knowledge_db):
        raise AppError(404, "CONCEPT_NOT_FOUND", "概念不存在")
    allowed = {"canonical_name", "description", "ap_unit", "topic", "status", "weight"}
    fields = {key: value for key, value in updates.items() if key in allowed}
    if not fields:
        result = get_concept(cluster_id, db_path=knowledge_db)
        if not result:
            raise AppError(404, "CONCEPT_NOT_FOUND", "概念不存在")
        return result
    if "canonical_name" in fields and not str(fields["canonical_name"]).strip():
        raise AppError(400, "CONCEPT_NAME_REQUIRED", "概念名称不能为空")
    assignments = ", ".join(f"{key}=?" for key in fields)
    conn = _write_connect(knowledge_db)
    try:
        with conn:
            conn.execute(
                f"UPDATE concept_clusters SET {assignments} "
                "WHERE cluster_id=? AND subject_id='psychology'",
                [fields[key] for key in fields] + [cluster_id],
            )
    finally:
        conn.close()
    result = get_concept(cluster_id, db_path=knowledge_db)
    if not result:
        raise AppError(404, "CONCEPT_NOT_FOUND", "概念不存在")
    return result


def update_kp(kp_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    _, knowledge_db = _write_paths()
    if not get_kp(kp_id, db_path=knowledge_db):
        raise AppError(404, "KP_NOT_FOUND", "知识点不存在")
    allowed = {"name", "plain_en", "definition_quote", "subheading", "status", "weight"}
    fields = {key: value for key, value in updates.items() if key in allowed}
    if not fields:
        result = get_kp(kp_id, db_path=knowledge_db)
        if not result:
            raise AppError(404, "KP_NOT_FOUND", "知识点不存在")
        return result
    if "name" in fields:
        name = str(fields["name"]).strip()
        if not name:
            raise AppError(400, "KP_NAME_REQUIRED", "知识点名称不能为空")
        fields["name"] = name
        fields["name_normalized"] = name.lower()
    fields["updated_at"] = datetime.now().isoformat(timespec="seconds")
    assignments = ", ".join(f"{key}=?" for key in fields)
    conn = _write_connect(knowledge_db)
    try:
        with conn:
            conn.execute(
                f"UPDATE knowledge_points SET {assignments} WHERE kp_id=?",
                [fields[key] for key in fields] + [kp_id],
            )
    finally:
        conn.close()
    result = get_kp(kp_id, db_path=knowledge_db)
    if not result:
        raise AppError(404, "KP_NOT_FOUND", "知识点不存在")
    return result
