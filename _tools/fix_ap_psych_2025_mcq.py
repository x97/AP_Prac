#!/usr/bin/env python3
"""Repair known 2025 AP Psychology MCQ extraction defects.

Fixes:
  * Q6: screenshot chrome became the stem; options were shifted; answer was wrong.
  * Q26: same screenshot shift; actual option D was missing.
  * Q36: "Mark for Review" UI text leaked into the stem.
  * Q8-Q10 and Q35-Q37: remove chart titles from the shared stimulus text and
    fix OCR typos in the Q8-Q10 stimulus.

All writes are restricted to the six named question rows/shared contexts.
"""

from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data/content/psychology/psychology_exam.db"
PAPER_ID = "psychology-ap-2025"

Q6_STEM = (
    "Dr. Kambeyanda is conducting a cross-sectional study to investigate whether "
    "there are differences in the absolute thresholds of individuals of different "
    "age groups. Which of the following is the best operational definition that "
    "Dr. Kambeyanda can use to measure the absolute threshold?"
)
Q6_OPTIONS = [
    ("A", "The number of times out of 100 that a participant can correctly identify the presented stimulus", 1),
    ("B", "The number of times out of 100 that a participant can accurately detect a change in the presented stimulus from its original form", 0),
    ("C", "The proportion of a stimulus that must be presented for a participant to detect a change", 0),
    ("D", "Whether a participant is able to perceive a presented stimulus", 0),
]

Q26_STEM = (
    "Which of the following describes the student who was recruited to pretend to "
    "bully other students?"
)
Q26_OPTIONS = [
    ("A", "A dependent variable", 0),
    ("B", "A confounding variable", 0),
    ("C", "A research confederate", 1),
    ("D", "A control group", 0),
]

Q36_STEM = (
    "Which of the following is the best example of the hypothesis Dr. Reyes is "
    "likely studying?"
)

Q8_CONTEXT = (
    "Questions 8 through 10 refer to the following. Dr. Collins measured the "
    "weights in pounds (lbs) and heights (inches) of 29 children. She found that "
    "growth is more continuous than discontinuous. The data are shown in the graph."
)
Q35_CONTEXT = (
    "Questions 35 through 37 refer to the following. For a research study, "
    "Dr. Reyes analyzed data she obtained from local news reports from the entire "
    "sports season for three teams at a local high school. After completing the "
    "analysis, Dr. Reyes found that teams were more likely to win when playing at "
    "their home school than away at another school. The data are shown in the graph."
)


def backup_db() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = DB.with_name(f"{DB.name}.bak-{stamp}-before-ap2025-mcq-fixes")
    shutil.copy2(DB, target)
    return target


def update_options(conn: sqlite3.Connection, question_id: str, options: list[tuple[str, str, int]]) -> None:
    for label, content, is_correct in options:
        conn.execute(
            "UPDATE options SET content=?, is_correct=? WHERE question_id=? AND label=?",
            (content, is_correct, question_id, label),
        )


def fix(conn: sqlite3.Connection) -> None:
    conn.execute(
        "UPDATE questions SET stem=?, context=NULL, correct_answer='A', "
        "answer_source='manual_correction', answer_confidence='reviewed_item_content' "
        "WHERE question_id='psychology-2025-mcq-006'",
        (Q6_STEM,),
    )
    update_options(conn, "psychology-2025-mcq-006", Q6_OPTIONS)

    conn.execute(
        "UPDATE questions SET stem=?, correct_answer='C' "
        "WHERE question_id='psychology-2025-mcq-026'",
        (Q26_STEM,),
    )
    update_options(conn, "psychology-2025-mcq-026", Q26_OPTIONS)

    conn.execute(
        "UPDATE questions SET stem=? WHERE question_id='psychology-2025-mcq-036'",
        (Q36_STEM,),
    )
    for number in (8, 9, 10):
        conn.execute(
            "UPDATE questions SET context=? WHERE question_id=?",
            (Q8_CONTEXT, f"psychology-2025-mcq-{number:03d}"),
        )
    for number in (35, 36, 37):
        conn.execute(
            "UPDATE questions SET context=? WHERE question_id=?",
            (Q35_CONTEXT, f"psychology-2025-mcq-{number:03d}"),
        )


def verify(conn: sqlite3.Connection) -> None:
    q6 = conn.execute(
        "SELECT stem, context, correct_answer FROM questions "
        "WHERE question_id='psychology-2025-mcq-006'"
    ).fetchone()
    assert q6 == (Q6_STEM, None, "A"), q6
    q6_opts = conn.execute(
        "SELECT label, content, is_correct FROM options "
        "WHERE question_id='psychology-2025-mcq-006' ORDER BY label"
    ).fetchall()
    assert q6_opts == [(a, b, c) for a, b, c in Q6_OPTIONS], q6_opts
    q6_correct = conn.execute(
        "SELECT label FROM options WHERE question_id='psychology-2025-mcq-006' AND is_correct=1"
    ).fetchall()
    assert q6_correct == [('A',)], q6_correct

    q26 = conn.execute(
        "SELECT stem, correct_answer FROM questions "
        "WHERE question_id='psychology-2025-mcq-026'"
    ).fetchone()
    assert q26 == (Q26_STEM, "C"), q26
    q26_opts = conn.execute(
        "SELECT label, content, is_correct FROM options "
        "WHERE question_id='psychology-2025-mcq-026' ORDER BY label"
    ).fetchall()
    assert q26_opts == [(a, b, c) for a, b, c in Q26_OPTIONS], q26_opts
    q26_correct = conn.execute(
        "SELECT label FROM options WHERE question_id='psychology-2025-mcq-026' AND is_correct=1"
    ).fetchall()
    assert q26_correct == [('C',)], q26_correct

    q36 = conn.execute(
        "SELECT stem FROM questions WHERE question_id='psychology-2025-mcq-036'"
    ).fetchone()
    assert q36 == (Q36_STEM,), q36

    leaked = conn.execute(
        """
        SELECT number FROM questions
        WHERE paper_id=? AND section='MCQ'
          AND (
            lower(stem) LIKE '%mark for revie%'
            OR lower(context) LIKE '%mark for revie%'
            OR EXISTS (
              SELECT 1 FROM options o
              WHERE o.question_id=questions.question_id
                AND lower(o.content) LIKE '%mark for revie%'
            )
          )
        """,
        (PAPER_ID,),
    ).fetchall()
    assert not leaked, leaked

    for number in (8, 9, 10):
        context = conn.execute(
            "SELECT context FROM questions WHERE question_id=?",
            (f"psychology-2025-mcq-{number:03d}",),
        ).fetchone()[0]
        assert context == Q8_CONTEXT, (number, context)
    for number in (35, 36, 37):
        context = conn.execute(
            "SELECT context FROM questions WHERE question_id=?",
            (f"psychology-2025-mcq-{number:03d}",),
        ).fetchone()[0]
        assert context == Q35_CONTEXT, (number, context)

    if conn.execute("PRAGMA foreign_key_check").fetchall():
        raise AssertionError("foreign_key_check failed")
    if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        raise AssertionError("integrity_check failed")


def main() -> int:
    backup = backup_db()
    print(f"backup: {backup}")
    conn = sqlite3.connect(str(DB))
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        conn.execute("BEGIN IMMEDIATE")
        fix(conn)
        verify(conn)
        conn.commit()
        print("committed 2025 MCQ fixes")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
