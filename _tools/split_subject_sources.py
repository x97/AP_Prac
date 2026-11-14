#!/usr/bin/env python3
"""Split the legacy combined content DBs into subject-owned source DBs.

This is a one-way local migration helper. The legacy root files are symlinks to
the psychology source after migration, so existing tools keep working.
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "data" / "content"


def _has_table(conn: sqlite3.Connection, table: str) -> bool:
    return bool(
        conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
    )


def _has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    return any(row[1] == column for row in conn.execute(f"PRAGMA table_info({table})"))


def _ids(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> set[str]:
    return {str(row[0]) for row in conn.execute(sql, params) if row[0] is not None}


def _delete_not_in(
    conn: sqlite3.Connection, table: str, column: str, values: set[str]
) -> None:
    if not _has_table(conn, table) or not _has_column(conn, table, column):
        return
    if not values:
        conn.execute(f"DELETE FROM {table}")
        return
    placeholders = ",".join("?" for _ in values)
    conn.execute(
        f"DELETE FROM {table} WHERE {column} NOT IN ({placeholders})",
        tuple(values),
    )


def _delete_subject_mismatch(
    conn: sqlite3.Connection, subject_id: str, tables: tuple[str, ...]
) -> None:
    for table in tables:
        if _has_table(conn, table) and _has_column(conn, table, "subject_id"):
            conn.execute(f"DELETE FROM {table} WHERE subject_id<>?", (subject_id,))


def clean_exam_db(path: Path, subject_id: str) -> None:
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA foreign_keys=OFF")
    _delete_subject_mismatch(
        conn,
        subject_id,
        ("papers", "questions", "practice_groups", "content_sources", "subjects"),
    )
    paper_ids = _ids(
        conn, "SELECT paper_id FROM papers WHERE subject_id=?", (subject_id,)
    )
    question_ids = _ids(
        conn, "SELECT question_id FROM questions WHERE subject_id=?", (subject_id,)
    )
    rubric_ids = _ids(
        conn,
        "SELECT rubric_id FROM frq_rubrics WHERE question_id IN "
        "(SELECT question_id FROM questions WHERE subject_id=?)",
        (subject_id,),
    )
    group_ids = _ids(
        conn, "SELECT group_id FROM practice_groups WHERE subject_id=?", (subject_id,)
    )
    topic_ids = (
        _ids(
            conn,
            "SELECT topic_id FROM practice_topics WHERE group_id IN "
            "(SELECT group_id FROM practice_groups WHERE subject_id=?)",
            (subject_id,),
        )
        if _has_table(conn, "practice_topics")
        else set()
    )

    for table in (
        "paper_question_map",
        "paper_sources",
        "paper_book_sources",
        "paper_exam_configs",
    ):
        _delete_not_in(conn, table, "paper_id", paper_ids)
    for table in (
        "options",
        "assets",
        "question_sources",
        "question_display",
        "question_exclusions",
    ):
        _delete_not_in(conn, table, "question_id", question_ids)
    _delete_not_in(conn, "frq_rubrics", "question_id", question_ids)
    _delete_not_in(conn, "rubric_parts", "rubric_id", rubric_ids)
    _delete_not_in(conn, "practice_group_papers", "group_id", group_ids)
    _delete_not_in(conn, "practice_group_papers", "paper_id", paper_ids)
    if topic_ids:
        _delete_not_in(conn, "practice_topic_questions", "topic_id", topic_ids)
        _delete_not_in(conn, "practice_topic_concepts", "topic_id", topic_ids)
    if _has_table(conn, "practice_topics"):
        _delete_not_in(conn, "practice_topics", "group_id", group_ids)

    conn.commit()
    conn.execute("VACUUM")
    conn.close()


def clean_knowledge_db(
    path: Path, subject_id: str, question_ids: set[str], paper_ids: set[str]
) -> None:
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA foreign_keys=OFF")
    _delete_subject_mismatch(
        conn, subject_id, ("books", "concept_clusters", "subjects", "subject_aliases")
    )
    book_ids = _ids(conn, "SELECT book_id FROM books WHERE subject_id=?", (subject_id,))
    section_ids = _ids(
        conn,
        "SELECT section_id FROM sections WHERE book_id IN "
        "(SELECT book_id FROM books WHERE subject_id=?)",
        (subject_id,),
    )
    kp_ids = _ids(
        conn,
        "SELECT kp_id FROM knowledge_points WHERE book_id IN "
        "(SELECT book_id FROM books WHERE subject_id=?)",
        (subject_id,),
    )
    concept_ids = _ids(
        conn,
        "SELECT cluster_id FROM concept_clusters WHERE subject_id=?",
        (subject_id,),
    )

    _delete_not_in(conn, "sections", "book_id", book_ids)
    _delete_not_in(conn, "section_texts", "section_id", section_ids)
    _delete_not_in(conn, "section_researchers", "section_id", section_ids)
    _delete_not_in(conn, "knowledge_points", "book_id", book_ids)
    _delete_not_in(conn, "knowledge_points", "section_id", section_ids)
    _delete_not_in(conn, "concept_members", "kp_id", kp_ids)
    _delete_not_in(conn, "concept_members", "cluster_id", concept_ids)
    for table, column in (
        ("kp_aliases", "kp_id"),
        ("kp_experiments", "kp_id"),
        ("kp_relations", "kp_id_a"),
        ("kp_relations", "kp_id_b"),
        ("kp_researchers", "kp_id"),
        ("concept_relations", "concept_id_a"),
        ("concept_relations", "concept_id_b"),
    ):
        _delete_not_in(
            conn, table, column, kp_ids if column.startswith("kp_") else concept_ids
        )
    for table in (
        "question_analysis",
        "question_concept_links",
        "question_keywords",
        "question_kp_links",
    ):
        _delete_not_in(conn, table, "question_id", question_ids)
    _delete_not_in(conn, "question_analysis", "paper_id", paper_ids)
    _delete_not_in(conn, "ingestion_runs", "book_id", book_ids)
    _delete_not_in(conn, "validation_issues", "book_id", book_ids)

    conn.commit()
    conn.execute("VACUUM")
    conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subject", default="psychology")
    parser.add_argument("--other-subject", default="statistics")
    args = parser.parse_args()

    psych_dir = CONTENT / args.subject
    stats_dir = CONTENT / args.other_subject
    psych_exam = psych_dir / f"{args.subject}_exam.db"
    psych_know = psych_dir / f"{args.subject}_knowledge.db"
    if not psych_exam.exists() or not psych_know.exists():
        raise SystemExit("subject source DBs do not exist; run after initial migration")

    # Make the statistics copies from the current psychology copies.
    stats_dir.mkdir(parents=True, exist_ok=True)
    stats_exam = stats_dir / f"{args.other_subject}_exam.db"
    stats_know = stats_dir / f"{args.other_subject}_knowledge.db"
    shutil.copy2(psych_exam, stats_exam)
    shutil.copy2(psych_know, stats_know)
    clean_exam_db(stats_exam, args.other_subject)
    stats_q = _ids(
        sqlite3.connect(str(stats_exam)),
        "SELECT question_id FROM questions WHERE subject_id=?",
        (args.other_subject,),
    )
    stats_p = _ids(
        sqlite3.connect(str(stats_exam)),
        "SELECT paper_id FROM papers WHERE subject_id=?",
        (args.other_subject,),
    )
    clean_knowledge_db(stats_know, args.other_subject, stats_q, stats_p)

    # Clean the psychology copies.
    psych_q = _ids(
        sqlite3.connect(str(psych_exam)),
        "SELECT question_id FROM questions WHERE subject_id=?",
        (args.subject,),
    )
    psych_p = _ids(
        sqlite3.connect(str(psych_exam)),
        "SELECT paper_id FROM papers WHERE subject_id=?",
        (args.subject,),
    )
    clean_exam_db(psych_exam, args.subject)
    clean_knowledge_db(psych_know, args.subject, psych_q, psych_p)
    print(f"split complete: {psych_dir} and {stats_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
