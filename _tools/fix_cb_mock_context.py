#!/usr/bin/env python3
"""Repair shared stimuli in the imported CB mock paper without re-importing.

The first import used ``pypdf`` line extraction and wrote ``context=NULL`` for
every question.  As a result the next question's passage was appended to the
previous question's ``answer_text`` (CB mock Q1/Q2/Q3 on PDF page 755), and
page headers leaked into some stems/options.  This script re-parses the PDF
with the block parser, then updates only the affected fields while keeping
question IDs, options, assets and practice-group memberships intact.

Run without ``--apply`` first to review the diff.  ``--apply`` creates a
timestamped backup of the source SQLite database before writing.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import shutil
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from import_cb_mock import (  # noqa: E402
    CONTEXT_GROUPS,
    DB,
    END_PAGE,
    EXPECTED,
    PAPER_ID,
    PDF,
    START_PAGE,
    validate,
)
from parse_cb import extract_layout_text, parse_unit_text  # noqa: E402


def normalized(value: str | None) -> str:
    return " ".join((value or "").split())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="write the repaired fields (default: show the diff only)",
    )
    args = parser.parse_args()

    text = extract_layout_text(PDF, START_PAGE, END_PAGE)
    questions, gaps = parse_unit_text(text, context_groups=CONTEXT_GROUPS)
    errors = validate(questions)
    if gaps:
        errors.append(f"number gaps: {gaps}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    parsed = {question["number"]: question for question in questions}
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT question_id, number, stem, context, answer_text, correct_answer "
        "FROM questions WHERE paper_id=? ORDER BY number",
        (PAPER_ID,),
    ).fetchall()
    if len(rows) != EXPECTED:
        print(
            f"ERROR: database has {len(rows)} questions for {PAPER_ID}, expected {EXPECTED}",
            file=sys.stderr,
        )
        return 1

    changes: list[str] = []
    updates: list[tuple[str, str | None, str | None, str]] = []
    option_updates: list[tuple[str, str, str]] = []

    for row in rows:
        question = parsed[row["number"]]
        if question["answer"] != (row["correct_answer"] or "").upper():
            print(
                f"ERROR: Q{row['number']} parsed answer {question['answer']!r} != "
                f"stored answer {row['correct_answer']!r}",
                file=sys.stderr,
            )
            return 1
        for field in ("stem", "context", "answer_text"):
            old = row[field]
            new = question["context"] if field == "context" else question[field]
            if normalized(old) != normalized(new):
                changes.append(
                    f"Q{row['number']} {field}: {normalized(old)[:90]!r} -> "
                    f"{normalized(new)[:90]!r}"
                )
        updates.append(
            (
                question["stem"],
                question["context"],
                question["answer_text"],
                row["question_id"],
            )
        )

        options = {
            option["label"]: option["content"]
            for option in con.execute(
                "SELECT label, content FROM options WHERE question_id=? ORDER BY sort_order",
                (row["question_id"],),
            )
        }
        if set(options) != set(question["options"]):
            changes.append(
                f"Q{row['number']} option labels: {sorted(options)} -> "
                f"{sorted(question['options'])}"
            )
        for label, content in question["options"].items():
            if label in options and normalized(options[label]) != normalized(content):
                changes.append(
                    f"Q{row['number']} option {label}: {normalized(options[label])[:80]!r} -> "
                    f"{normalized(content)[:80]!r}"
                )
            option_updates.append((content, row["question_id"], label))

    for group in CONTEXT_GROUPS:
        anchor = parsed[group[0]]
        shared = anchor.get("context") or ""
        print(f"context group {group}: {len(shared)} chars")
        for number in group:
            if parsed[number].get("context") != shared:
                print(
                    f"ERROR: Q{number} has a different context than Q{group[0]}",
                    file=sys.stderr,
                )
                return 1

    print(f"questions: {len(rows)}")
    print(f"changed fields: {len(changes)}")
    for change in changes:
        print(f"  {change}")

    if not args.apply:
        print("\ndry run; pass --apply to write these changes")
        con.close()
        return 0

    backup = f"{DB}.bak-{dt.datetime.now():%Y%m%d-%H%M%S}"
    shutil.copy2(DB, backup)
    print(f"\nbackup: {backup}")

    for stem, context, answer_text, question_id in updates:
        con.execute(
            "UPDATE questions SET stem=?, context=?, answer_text=? WHERE question_id=?",
            (stem, context, answer_text, question_id),
        )
    for content, question_id, label in option_updates:
        con.execute(
            "UPDATE options SET content=? WHERE question_id=? AND label=?",
            (content, question_id, label),
        )
    con.commit()
    con.close()
    print("repaired CB mock context/stem/answer_text/options")
    return 0


if __name__ == "__main__":
    sys.exit(main())
