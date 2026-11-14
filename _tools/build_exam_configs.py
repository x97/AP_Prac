#!/usr/bin/env python3
"""Populate paper_exam_configs in a staging/release exam DB.

The root psychology_exam.db is the authoritative source and must stay read-only.
This script is meant to run on a copy produced by build_content_release.py.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "exam_formats" / "psychology.json"

SCHEMA = """
CREATE TABLE IF NOT EXISTS paper_exam_configs (
    paper_id TEXT PRIMARY KEY,
    format_code TEXT NOT NULL,
    mcq_count INTEGER NOT NULL,
    mcq_minutes INTEGER NOT NULL,
    frq_count INTEGER NOT NULL,
    frq_minutes INTEGER NOT NULL,
    frq_forms TEXT,
    section_order TEXT NOT NULL,
    is_complete INTEGER NOT NULL DEFAULT 1,
    frq_rubric_complete INTEGER NOT NULL DEFAULT 1,
    expected_frq_points INTEGER NOT NULL DEFAULT 7,
    notes TEXT
);
"""


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def actual_counts(
    conn: sqlite3.Connection, paper_id: str, subject_id: str = "psychology"
) -> dict[str, Any]:
    row = conn.execute(
        """
        SELECT
          SUM(CASE WHEN section = 'MCQ' THEN 1 ELSE 0 END) AS mcq,
          SUM(CASE WHEN section = 'FRQ' THEN 1 ELSE 0 END) AS frq
        FROM questions
        WHERE paper_id = ? AND subject_id = ?
        """,
        (paper_id, subject_id),
    ).fetchone()
    forms = [
        r[0]
        for r in conn.execute(
            """
            SELECT DISTINCT form FROM questions
            WHERE paper_id = ? AND subject_id = ?
              AND section = 'FRQ' AND form IS NOT NULL AND trim(form) <> ''
            ORDER BY form
            """,
            (paper_id, subject_id),
        )
    ]
    per_form = {
        form: conn.execute(
            """
            SELECT COUNT(*) FROM questions
            WHERE paper_id = ? AND subject_id = ?
              AND section = 'FRQ' AND form = ?
            """,
            (paper_id, subject_id, form),
        ).fetchone()[0]
        for form in forms
    }
    return {
        "mcq": int(row["mcq"] or 0),
        "frq": int(row["frq"] or 0),
        "forms": forms,
        "per_form": per_form,
    }


def validate_row(
    paper_id: str, cfg: dict[str, Any], actual: dict[str, Any]
) -> list[str]:
    errors: list[str] = []
    if actual["mcq"] != int(cfg["mcq"]["count"]):
        errors.append(
            f"{paper_id}: MCQ count {actual['mcq']} != config {cfg['mcq']['count']}"
        )
    forms = cfg["frq"].get("forms") or []
    expected_frq = int(cfg["frq"]["count"])
    if forms:
        if actual["frq"] != expected_frq * len(forms):
            errors.append(
                f"{paper_id}: FRQ total {actual['frq']} != {expected_frq} x {len(forms)} forms"
            )
        missing = [f for f in forms if actual["per_form"].get(f, 0) != expected_frq]
        if missing:
            errors.append(
                f"{paper_id}: FRQ form counts mismatch: "
                + ", ".join(f"{f}={actual['per_form'].get(f, 0)}" for f in missing)
            )
    elif actual["frq"] != expected_frq:
        errors.append(f"{paper_id}: FRQ count {actual['frq']} != config {expected_frq}")
    return errors


def build(
    exam_db: Path,
    config_path: Path,
    dry_run: bool = False,
    subject_id: str = "psychology",
) -> int:
    cfg = load_config(config_path)
    papers = cfg["papers"]
    conn = sqlite3.connect(str(exam_db))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    if not dry_run:
        conn.executescript(SCHEMA)

    errors: list[str] = []
    rows: list[tuple[Any, ...]] = []
    for paper_id, pcfg in papers.items():
        actual = actual_counts(conn, paper_id, subject_id)
        errors.extend(validate_row(paper_id, pcfg, actual))
        forms = pcfg["frq"].get("forms") or []
        rows.append(
            (
                paper_id,
                pcfg["format_code"],
                int(pcfg["mcq"]["count"]),
                int(pcfg["mcq"]["minutes"]),
                int(pcfg["frq"]["count"]),
                int(pcfg["frq"]["minutes"]),
                json.dumps(forms, ensure_ascii=False) if forms else None,
                json.dumps(pcfg["section_order"], ensure_ascii=False),
                1 if pcfg.get("is_complete", True) else 0,
                1 if pcfg.get("frq_rubric_complete", True) else 0,
                int(pcfg.get("expected_frq_points", 7)),
                pcfg.get("notes", ""),
            )
        )

    if errors:
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        conn.close()
        return 1

    if dry_run:
        print(f"Would upsert {len(rows)} paper_exam_configs rows into {exam_db}")
        conn.close()
        return 0

    conn.executemany(
        """
        INSERT INTO paper_exam_configs (
          paper_id, format_code, mcq_count, mcq_minutes,
          frq_count, frq_minutes, frq_forms, section_order,
          is_complete, frq_rubric_complete, expected_frq_points, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(paper_id) DO UPDATE SET
          format_code=excluded.format_code,
          mcq_count=excluded.mcq_count,
          mcq_minutes=excluded.mcq_minutes,
          frq_count=excluded.frq_count,
          frq_minutes=excluded.frq_minutes,
          frq_forms=excluded.frq_forms,
          section_order=excluded.section_order,
          is_complete=excluded.is_complete,
          frq_rubric_complete=excluded.frq_rubric_complete,
          expected_frq_points=excluded.expected_frq_points,
          notes=excluded.notes
        """,
        rows,
    )
    conn.commit()
    conn.close()
    print(f"Upserted {len(rows)} paper_exam_configs rows into {exam_db}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exam-db", required=True, type=Path)
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--subject", default="psychology")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.config is None:
        from subject_config import load_subject

        args.config = Path(load_subject(args.subject)["exam_config"])
    if not args.exam_db.exists():
        print(f"exam db not found: {args.exam_db}", file=sys.stderr)
        return 2
    return build(args.exam_db, args.config, args.dry_run, args.subject)


if __name__ == "__main__":
    raise SystemExit(main())
