#!/usr/bin/env python3
"""Reduce psychology_exam.db to exam content only.

Keep: subjects, paper_types, papers, paper_sources, questions, options,
assets, frq_rubrics, rubric_parts, content_sources (exam sources only).

Drop: textbook/curriculum/chunk/KP/summary/tag/collection tables, the
question/paper<->unit link tables, the KP relevance view, and the
primary_unit_id / primary_chapter_id columns on questions.
"""
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DB = os.path.join(ROOT, "data", "content", "psychology", "psychology_exam.db")

DROP_ORDER = [
    "v_question_kp_relevance",
    "question_keywords",
    "question_keypoints",
    "knowledge_points",
    "summaries",
    "knowledge_chunks",
    "question_units",
    "paper_units",
    "question_tags",
    "tags",
    "collection_items",
    "collections",
    "curriculum_units",
    "textbooks",
]

KEEP_TABLES = [
    "subjects",
    "paper_types",
    "papers",
    "paper_sources",
    "questions",
    "options",
    "assets",
    "frq_rubrics",
    "rubric_parts",
    "content_sources",
]


def main() -> int:
    con = sqlite3.connect(DB)
    con.execute("PRAGMA foreign_keys=OFF")

    existing = {
        r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table','view')"
        )
    }
    for name in DROP_ORDER:
        if name in existing:
            kind = "VIEW" if name == "v_question_kp_relevance" else "TABLE"
            con.execute(f"DROP {kind} IF EXISTS {name}")

    # The Barron's textbook source is not referenced by any paper.
    con.execute(
        "DELETE FROM content_sources WHERE source_id='psychology-barrons-2027'"
    )

    # These were derived from knowledge points; remove them from questions.
    question_columns = {
        r[1] for r in con.execute("PRAGMA table_info(questions)")
    }
    for column in ("primary_unit_id", "primary_chapter_id"):
        if column in question_columns:
            con.execute(f"ALTER TABLE questions DROP COLUMN {column}")

    con.commit()
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("VACUUM")

    # Verification.
    fk = con.execute("PRAGMA foreign_key_check").fetchall()
    integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
    tables = [
        r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
    ]
    print("kept tables:", ", ".join(tables))
    for table in KEEP_TABLES:
        try:
            count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"  {table}: {count}")
        except sqlite3.Error as error:
            print(f"  {table}: ERROR {error}")
    print("questions columns:", [
        r[1] for r in con.execute("PRAGMA table_info(questions)")
    ])
    print("content_sources:", [
        r[0] for r in con.execute("SELECT source_id FROM content_sources")
    ])
    print("foreign_key_check:", "OK" if not fk else fk[:5])
    print("integrity_check:", integrity)
    con.close()
    return 0 if not fk and integrity == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
