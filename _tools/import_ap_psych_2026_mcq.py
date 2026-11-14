#!/usr/bin/env python3
"""Import the 2026 AP Psychology MCQ section into the psychology source DB.

This deliberately imports MCQ only. The PDF's FRQ sources/rubrics are
incomplete, so FRQ rows are not written. The source DB is backed up first and
all writes are limited to paper_id='psychology-ap-2026'.

Usage:
    python3 _tools/import_ap_psych_2026_mcq.py
"""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data/content/psychology/psychology_exam.db"
JSON_PATH = ROOT / "data/content/psychology/extraction/psychology-ap-2026.json"
PAPER_ID = "psychology-ap-2026"
SOURCE_ID = "psychology-ap-2026-pdf"
SOURCE_PDF = "assets/psychology/papers/2026/2026 AP心理学.pdf"
SOURCE_DIR = "assets/psychology/papers/2026"


def backup_db() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = DB.with_name(f"{DB.name}.bak-{stamp}-before-ap2026-mcq")
    shutil.copy2(DB, target)
    return target


def ensure_asset_description_column(conn: sqlite3.Connection) -> None:
    columns = {
        row[1] for row in conn.execute("PRAGMA table_info(assets)").fetchall()
    }
    if "description" not in columns:
        conn.execute("ALTER TABLE assets ADD COLUMN description TEXT")


def delete_paper(conn: sqlite3.Connection) -> None:
    conn.execute(
        "DELETE FROM assets WHERE question_id IN "
        "(SELECT question_id FROM questions WHERE paper_id=?)",
        (PAPER_ID,),
    )
    conn.execute(
        "DELETE FROM question_sources WHERE question_id IN "
        "(SELECT question_id FROM questions WHERE paper_id=?)",
        (PAPER_ID,),
    )
    conn.execute(
        "DELETE FROM options WHERE question_id IN "
        "(SELECT question_id FROM questions WHERE paper_id=?)",
        (PAPER_ID,),
    )
    conn.execute("DELETE FROM questions WHERE paper_id=?", (PAPER_ID,))
    conn.execute(
        "DELETE FROM paper_question_map WHERE paper_id=? OR source_paper_id=?",
        (PAPER_ID, PAPER_ID),
    )
    conn.execute("DELETE FROM practice_group_papers WHERE paper_id=?", (PAPER_ID,))
    conn.execute("DELETE FROM paper_book_sources WHERE paper_id=?", (PAPER_ID,))
    conn.execute("DELETE FROM paper_sources WHERE paper_id=?", (PAPER_ID,))
    conn.execute("DELETE FROM papers WHERE paper_id=?", (PAPER_ID,))


def import_mcq(conn: sqlite3.Connection) -> None:
    payload = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    paper = payload["paper"]
    questions = [
        question
        for question in payload["questions"]
        if question["section"] == "MCQ"
    ]
    if len(questions) != 75:
        raise ValueError(f"expected 75 MCQ rows, got {len(questions)}")
    if paper["paper_id"] != PAPER_ID:
        raise ValueError(f"unexpected paper id in JSON: {paper['paper_id']}")

    conn.execute(
        """
        INSERT INTO content_sources (
          source_id, kind, title, chinese_title, edition, target_year,
          file_path, imported_at, subject_id, book_id
        ) VALUES (?, 'exam_pdf', ?, ?, NULL, 2026, ?, ?, 'psychology', NULL)
        ON CONFLICT(source_id) DO UPDATE SET
          kind=excluded.kind,
          title=excluded.title,
          chinese_title=excluded.chinese_title,
          target_year=excluded.target_year,
          file_path=excluded.file_path,
          imported_at=excluded.imported_at,
          subject_id=excluded.subject_id
        """,
        (
            SOURCE_ID,
            paper["title"],
            paper["chinese_title"],
            SOURCE_PDF,
            datetime.now().astimezone().isoformat(timespec="seconds"),
        ),
    )

    conn.execute(
        """
        INSERT INTO papers (
          paper_id, year, title, chinese_title, subject_id, source_pdf,
          question_count, paper_type, source_id
        ) VALUES (?, ?, ?, ?, 'psychology', ?, ?, 'real_exam', ?)
        """,
        (
            PAPER_ID,
            int(paper["year"]),
            "AP Psychology 2026 (75 MCQs)",
            "2026 年 AP 心理学（75 道选择题；FRQ 暂未入库）",
            SOURCE_DIR,
            len(questions),
            SOURCE_ID,
        ),
    )
    conn.execute(
        """
        INSERT INTO paper_sources (paper_id, role, path, note)
        VALUES (?, 'mcq', ?, ?)
        """,
        (PAPER_ID, SOURCE_PDF, "2026 MCQ section; FRQ intentionally not imported yet."),
    )

    for question in questions:
        conn.execute(
            """
            INSERT INTO questions (
              question_id, paper_id, section, number, stem, context,
              page_start, page_end, correct_answer, answer_text,
              subject_id, form, source_file, answer_source,
              answer_confidence, question_fingerprint
            ) VALUES (?, ?, 'MCQ', ?, ?, ?, ?, ?, ?, NULL,
                      'psychology', NULL, ?, ?, ?, NULL)
            """,
            (
                question["question_id"],
                PAPER_ID,
                int(question["number"]),
                question["stem"],
                question.get("context"),
                int(question["page_start"]),
                int(question["page_end"]),
                question["correct_answer"],
                SOURCE_PDF,
                question.get("answer_source"),
                question.get("answer_confidence"),
            ),
        )
        for option in question["options"]:
            conn.execute(
                """
                INSERT INTO options (
                  question_id, label, content, sort_order, is_correct,
                  explanation, ai_explanation
                ) VALUES (?, ?, ?, ?, ?, NULL, NULL)
                """,
                (
                    question["question_id"],
                    option["label"],
                    option["content"],
                    int(option["sort_order"]),
                    1 if option["is_correct"] else 0,
                ),
            )
        for asset in question.get("assets", []):
            path = ROOT / asset["path"]
            if not path.is_file():
                raise FileNotFoundError(path)
            conn.execute(
                """
                INSERT INTO assets (
                  asset_id, question_id, option_label, kind, path, page, bbox,
                  description
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    asset["asset_id"],
                    question["question_id"],
                    asset.get("option_label"),
                    asset["kind"],
                    asset["path"],
                    int(asset["page"]),
                    json.dumps(asset["bbox"], ensure_ascii=False),
                    asset.get("description"),
                ),
            )


def verify(conn: sqlite3.Connection) -> dict[str, Any]:
    counts = {
        "questions": conn.execute(
            "SELECT COUNT(*) FROM questions WHERE paper_id=?", (PAPER_ID,)
        ).fetchone()[0],
        "mcq": conn.execute(
            "SELECT COUNT(*) FROM questions WHERE paper_id=? AND section='MCQ'",
            (PAPER_ID,),
        ).fetchone()[0],
        "frq": conn.execute(
            "SELECT COUNT(*) FROM questions WHERE paper_id=? AND section='FRQ'",
            (PAPER_ID,),
        ).fetchone()[0],
        "options": conn.execute(
            "SELECT COUNT(*) FROM options o JOIN questions q "
            "ON q.question_id=o.question_id WHERE q.paper_id=?",
            (PAPER_ID,),
        ).fetchone()[0],
        "assets": conn.execute(
            "SELECT COUNT(*) FROM assets a JOIN questions q "
            "ON q.question_id=a.question_id WHERE q.paper_id=?",
            (PAPER_ID,),
        ).fetchone()[0],
        "asset_descriptions": conn.execute(
            "SELECT COUNT(*) FROM assets a JOIN questions q "
            "ON q.question_id=a.question_id "
            "WHERE q.paper_id=? AND a.description IS NOT NULL "
            "AND trim(a.description) <> ''",
            (PAPER_ID,),
        ).fetchone()[0],
    }
    if counts != {
        "questions": 75,
        "mcq": 75,
        "frq": 0,
        "options": 300,
        "assets": 16,
        "asset_descriptions": 12,
    }:
        raise ValueError(f"unexpected 2026 counts: {counts}")

    bad = conn.execute(
        """
        SELECT q.question_id, COUNT(o.label) AS n_opts,
               SUM(CASE WHEN o.is_correct=1 THEN 1 ELSE 0 END) AS n_correct,
               SUM(CASE WHEN o.content IS NULL OR trim(o.content)='' THEN 1 ELSE 0 END) AS n_empty,
               MAX(CASE WHEN o.label=q.correct_answer THEN o.is_correct ELSE 0 END) AS answer_is_correct
        FROM questions q
        LEFT JOIN options o ON o.question_id=q.question_id
        WHERE q.paper_id=?
        GROUP BY q.question_id
        HAVING n_opts != 4 OR n_correct != 1 OR n_empty != 0 OR answer_is_correct != 1
        """,
        (PAPER_ID,),
    ).fetchall()
    if bad:
        raise ValueError(f"MCQ integrity failures: {bad}")

    if conn.execute("PRAGMA foreign_key_check").fetchall():
        raise ValueError("foreign_key_check failed")
    if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        raise ValueError("integrity_check failed")
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    backup = backup_db()
    print(f"backup: {backup}")
    conn = sqlite3.connect(str(DB))
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        conn.execute("BEGIN IMMEDIATE")
        ensure_asset_description_column(conn)
        delete_paper(conn)
        import_mcq(conn)
        counts = verify(conn)
        if args.dry_run:
            conn.rollback()
            print("dry-run: rolled back")
        else:
            conn.commit()
            print("committed")
        print(counts)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
