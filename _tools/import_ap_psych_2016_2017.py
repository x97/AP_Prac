#!/usr/bin/env python3
"""Import the parsed 2016 and 2017 AP Psychology papers into the source DB.

The source DB is authoritative for content builds. This script backs it up,
writes only the two target papers, and verifies counts/FKs before committing.
It does not modify an immutable Release and does not activate anything.

Usage:
    python3 _tools/import_ap_psych_2016_2017.py --dry-run
    python3 _tools/import_ap_psych_2016_2017.py --apply
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
EXTRACTION = ROOT / "data/content/psychology/extraction"

PAPERS = {
    2016: {
        "paper_id": "psychology-ap-2016",
        "source_id": "psychology-ap-2016-pdf",
        "title": "AP Psychology 2016 (Section I: 100 MCQs, Section II: 2 FRQs)",
        "chinese_title": "2016 年 AP 心理学（100 道选择题 + 2 道主观题）",
        "source_file": "assets/psychology/papers/2016/2016.pdf",
        "json": EXTRACTION / "psychology-ap-2016.json",
        "expected_assets": 5,
        "expected_parts": 14,
    },
    2017: {
        "paper_id": "psychology-ap-2017",
        "source_id": "psychology-ap-2017-pdf",
        "title": "AP Psychology 2017 (Section I: 100 MCQs, Section II: 2 FRQs)",
        "chinese_title": "2017 年 AP 心理学（100 道选择题 + 2 道主观题）",
        "source_file": "assets/psychology/papers/2017/2017.pdf",
        "json": EXTRACTION / "psychology-ap-2017.json",
        "expected_assets": 15,
        "expected_parts": 13,
    },
}


def backup_db() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = DB.with_name(f"{DB.name}.bak-{stamp}-before-ap2016-2017")
    shutil.copy2(DB, target)
    if target.stat().st_size == 0:
        raise RuntimeError(f"backup is empty: {target}")
    return target


def load_payloads() -> dict[int, dict[str, Any]]:
    payloads = {}
    for year, config in PAPERS.items():
        if not config["json"].is_file():
            raise FileNotFoundError(config["json"])
        payload = json.loads(config["json"].read_text(encoding="utf-8"))
        mcq = [q for q in payload["questions"] if q["section"] == "MCQ"]
        frq = [q for q in payload["questions"] if q["section"] == "FRQ"]
        if len(mcq) != 100 or len(frq) != 2:
            raise ValueError(f"{year}: expected 100 MCQ + 2 FRQ, got {len(mcq)} + {len(frq)}")
        if len(payload["frq_rubrics"]) != 2:
            raise ValueError(f"{year}: expected 2 FRQ rubrics")
        for question in mcq:
            if len(question["options"]) != 5:
                raise ValueError(f"{year} Q{question['number']}: expected 5 options")
            if sum(1 for option in question["options"] if option["is_correct"]) != 1:
                raise ValueError(f"{year} Q{question['number']}: expected exactly one correct option")
            if question["correct_answer"] != next(
                option["label"] for option in question["options"] if option["is_correct"]
            ):
                raise ValueError(f"{year} Q{question['number']}: answer/option mismatch")
        for rubric in payload["frq_rubrics"]:
            if sum(int(part["max_points"]) for part in rubric["parts"]) != int(
                rubric["total_points"]
            ):
                raise ValueError(f"{year}: rubric parts do not sum to total_points")
        payloads[year] = payload
    return payloads


def delete_paper(conn: sqlite3.Connection, paper_id: str) -> None:
    question_ids = [
        row[0]
        for row in conn.execute(
            "SELECT question_id FROM questions WHERE paper_id=?", (paper_id,)
        )
    ]
    if question_ids:
        placeholders = ",".join("?" for _ in question_ids)
        rubric_ids = [
            row[0]
            for row in conn.execute(
                f"SELECT rubric_id FROM frq_rubrics WHERE question_id IN ({placeholders})",
                question_ids,
            )
        ]
        if rubric_ids:
            rubric_ph = ",".join("?" for _ in rubric_ids)
            conn.execute(
                f"DELETE FROM rubric_parts WHERE rubric_id IN ({rubric_ph})",
                rubric_ids,
            )
        conn.execute(
            f"DELETE FROM frq_rubrics WHERE question_id IN ({placeholders})",
            question_ids,
        )
        conn.execute(
            f"DELETE FROM assets WHERE question_id IN ({placeholders})",
            question_ids,
        )
        conn.execute(
            f"DELETE FROM options WHERE question_id IN ({placeholders})",
            question_ids,
        )
        conn.execute(
            f"DELETE FROM question_sources WHERE question_id IN ({placeholders})",
            question_ids,
        )
        conn.execute(f"DELETE FROM questions WHERE question_id IN ({placeholders})", question_ids)
    conn.execute(
        "DELETE FROM paper_question_map WHERE paper_id=? OR source_paper_id=?",
        (paper_id, paper_id),
    )
    conn.execute("DELETE FROM practice_group_papers WHERE paper_id=?", (paper_id,))
    conn.execute("DELETE FROM paper_book_sources WHERE paper_id=?", (paper_id,))
    conn.execute("DELETE FROM paper_sources WHERE paper_id=?", (paper_id,))
    conn.execute("DELETE FROM papers WHERE paper_id=?", (paper_id,))


def insert_paper(
    conn: sqlite3.Connection, year: int, config: dict[str, Any], payload: dict[str, Any]
) -> None:
    paper = payload["paper"]
    question_count = len(payload["questions"])
    conn.execute(
        """
        INSERT INTO content_sources (
          source_id, kind, title, chinese_title, edition, target_year,
          file_path, imported_at, subject_id, book_id
        ) VALUES (?, 'exam_pdf', ?, ?, NULL, ?, ?, ?, 'psychology', NULL)
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
            config["source_id"],
            paper["title"],
            paper["chinese_title"],
            year,
            config["source_file"],
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
            config["paper_id"],
            year,
            config["title"],
            config["chinese_title"],
            config["source_file"],
            question_count,
            config["source_id"],
        ),
    )
    conn.execute(
        """
        INSERT INTO paper_sources (paper_id, role, path, note)
        VALUES (?, 'booklet', ?, ?)
        """,
        (
            config["paper_id"],
            config["source_file"],
            "MCQ + answer key + FRQ prompts and scoring guidelines.",
        ),
    )


def insert_questions_and_rubrics(
    conn: sqlite3.Connection, config: dict[str, Any], payload: dict[str, Any]
) -> None:
    for question in payload["questions"]:
        conn.execute(
            """
            INSERT INTO questions (
              question_id, paper_id, section, number, stem, context,
              page_start, page_end, correct_answer, answer_text,
              subject_id, form, source_file, answer_source,
              answer_confidence, question_fingerprint
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, 'psychology', NULL, ?, ?, ?, NULL)
            """,
            (
                question["question_id"],
                config["paper_id"],
                question["section"],
                int(question["number"]),
                question["stem"],
                question.get("context"),
                int(question["page_start"]),
                int(question["page_end"]),
                question.get("correct_answer"),
                config["source_file"],
                question.get("answer_source"),
                question.get("answer_confidence"),
            ),
        )
        for option in question.get("options", []):
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
            asset_path = ROOT / asset["path"]
            if not asset_path.is_file():
                raise FileNotFoundError(asset_path)
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

    for rubric in payload["frq_rubrics"]:
        conn.execute(
            """
            INSERT INTO frq_rubrics (
              rubric_id, question_id, total_points, general_considerations, format
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                rubric["rubric_id"],
                rubric["question_id"],
                int(rubric["total_points"]),
                rubric.get("general_considerations"),
                rubric.get("format") or "legacy_points",
            ),
        )
        for part in rubric["parts"]:
            conn.execute(
                """
                INSERT INTO rubric_parts (
                  part_id, rubric_id, label, title, max_points, criteria,
                  decision_rules, examples_positive, examples_negative, notes,
                  sort_order
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    part["part_id"],
                    rubric["rubric_id"],
                    part["label"],
                    part.get("title"),
                    int(part["max_points"]),
                    json.dumps(
                        [{"points": int(part["max_points"]), "criterion": part["criteria"]}],
                        ensure_ascii=False,
                    ),
                    part.get("decision_rules") or None,
                    json.dumps(part.get("examples_positive") or [], ensure_ascii=False),
                    json.dumps(part.get("examples_negative") or [], ensure_ascii=False),
                    part.get("notes") or None,
                    int(part["sort_order"]),
                ),
            )


def verify(conn: sqlite3.Connection, payloads: dict[int, dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for year, config in PAPERS.items():
        payload = payloads[year]
        paper_id = config["paper_id"]
        rows = {
            "questions": conn.execute(
                "SELECT COUNT(*) FROM questions WHERE paper_id=?", (paper_id,)
            ).fetchone()[0],
            "mcq": conn.execute(
                "SELECT COUNT(*) FROM questions WHERE paper_id=? AND section='MCQ'",
                (paper_id,),
            ).fetchone()[0],
            "frq": conn.execute(
                "SELECT COUNT(*) FROM questions WHERE paper_id=? AND section='FRQ'",
                (paper_id,),
            ).fetchone()[0],
            "options": conn.execute(
                "SELECT COUNT(*) FROM options o JOIN questions q ON q.question_id=o.question_id "
                "WHERE q.paper_id=?",
                (paper_id,),
            ).fetchone()[0],
            "assets": conn.execute(
                "SELECT COUNT(*) FROM assets a JOIN questions q ON q.question_id=a.question_id "
                "WHERE q.paper_id=?",
                (paper_id,),
            ).fetchone()[0],
            "rubrics": conn.execute(
                "SELECT COUNT(*) FROM frq_rubrics r JOIN questions q ON q.question_id=r.question_id "
                "WHERE q.paper_id=?",
                (paper_id,),
            ).fetchone()[0],
            "rubric_parts": conn.execute(
                "SELECT COUNT(*) FROM rubric_parts rp JOIN frq_rubrics r ON r.rubric_id=rp.rubric_id "
                "JOIN questions q ON q.question_id=r.question_id WHERE q.paper_id=?",
                (paper_id,),
            ).fetchone()[0],
        }
        expected = {
            "questions": 102,
            "mcq": 100,
            "frq": 2,
            "options": 500,
            "assets": config["expected_assets"],
            "rubrics": 2,
            "rubric_parts": config["expected_parts"],
        }
        if rows != expected:
            raise ValueError(f"{year}: counts {rows} != {expected}")
        bad = conn.execute(
            """
            SELECT q.question_id
            FROM questions q
            LEFT JOIN options o ON o.question_id=q.question_id
            WHERE q.paper_id=? AND q.section='MCQ'
            GROUP BY q.question_id
            HAVING COUNT(o.label) <> 5
               OR SUM(CASE WHEN o.is_correct=1 THEN 1 ELSE 0 END) <> 1
            """,
            (paper_id,),
        ).fetchall()
        if bad:
            raise ValueError(f"{year}: bad MCQ options: {[row[0] for row in bad[:5]]}")
        bad_rubric = conn.execute(
            """
            SELECT r.rubric_id
            FROM frq_rubrics r
            JOIN rubric_parts p ON p.rubric_id=r.rubric_id
            JOIN questions q ON q.question_id=r.question_id
            WHERE q.paper_id=?
            GROUP BY r.rubric_id
            HAVING SUM(p.max_points) <> r.total_points
            """,
            (paper_id,),
        ).fetchall()
        if bad_rubric:
            raise ValueError(f"{year}: bad rubrics: {[row[0] for row in bad_rubric]}")
        summary[year] = rows
    if conn.execute("PRAGMA foreign_key_check").fetchall():
        raise ValueError("foreign_key_check failed")
    if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        raise ValueError("integrity_check failed")
    summary["papers_total"] = conn.execute(
        "SELECT COUNT(*) FROM papers WHERE subject_id='psychology'"
    ).fetchone()[0]
    summary["questions_total"] = conn.execute(
        "SELECT COUNT(*) FROM questions WHERE subject_id='psychology'"
    ).fetchone()[0]
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="write to the source DB")
    parser.add_argument("--dry-run", action="store_true", help="validate only (default)")
    args = parser.parse_args()
    if args.apply and args.dry_run:
        parser.error("choose either --apply or --dry-run")

    payloads = load_payloads()
    if not DB.is_file():
        raise FileNotFoundError(DB)

    if not args.apply:
        for year, payload in payloads.items():
            print(
                f"{year}: dry run OK — "
                f"{sum(1 for q in payload['questions'] if q['section']=='MCQ')} MCQ, "
                f"{sum(1 for q in payload['questions'] if q['section']=='FRQ')} FRQ, "
                f"{sum(len(q.get('assets', [])) for q in payload['questions'])} assets"
            )
        print("No database writes. Re-run with --apply to import.")
        return 0

    backup = backup_db()
    print(f"backup: {backup}")
    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        conn.execute("BEGIN IMMEDIATE")
        for year, config in PAPERS.items():
            delete_paper(conn, config["paper_id"])
            insert_paper(conn, year, config, payloads[year])
            insert_questions_and_rubrics(conn, config, payloads[year])
        summary = verify(conn, payloads)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    print("imported:")
    for year in sorted(PAPERS):
        print(f"  {year}: {summary[year]}")
    print(
        f"totals: papers={summary['papers_total']} "
        f"questions={summary['questions_total']}"
    )
    print("No Release was modified or activated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
