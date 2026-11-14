#!/usr/bin/env python3
"""Complete the truncated 2018 FRQ 2 rubric.

The source PDF's 2018 scoring guidelines end after Point 3 (Superordinate
Goals). Points 4-7 below are a transparent manual reconstruction from the
printed question and standard AP Psychology scoring conventions. They are not
verbatim College Board text; the provenance note is written into the rubric.

Writes only the 2018 FRQ 2 rubric/parts and the paper's answer_text note.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data/content/psychology/psychology_exam.db"
QUESTION_ID = "psychology-2018-frq-002"
RUBRIC_ID = "psychology-rub-2018-frq-002"

PROVENANCE = (
    "RUBRIC PROVENANCE: Points 1–3 are taken from the source PDF. The source "
    "PDF ends after Point 3 (Superordinate Goals); Points 4–7 were reconstructed "
    "from the printed question and standard AP Psychology scoring conventions. "
    "They are not verbatim College Board text."
)

PARTS = [
    {
        "part_id": "psychology-rub-2018-frq-002-Point-4",
        "label": "Point 4",
        "title": "Metacognition",
        "criteria": [
            {
                "points": 1,
                "criterion": (
                    "Response must indicate that students think about their own "
                    "thinking or learning and use that awareness to improve focus, "
                    "behavior, or cooperation. Acceptable examples include monitoring "
                    "one's own attention, reflecting on how one learns or cooperates, "
                    "evaluating one's understanding, or adjusting a learning strategy. "
                    "A definition of metacognition alone does not score, and merely "
                    "working harder, studying more, or listening to the teacher does not score."
                ),
            }
        ],
        "decision_rules": (
            "Score 1 only when the response applies metacognition to Mr. Smith's "
            "students thinking about or monitoring their own thinking/learning. "
            "Score 0 for a definition-only response, generic effort language, or "
            "the teacher doing the thinking for the students."
        ),
        "examples_positive": [
            "Mr. Smith asks students to keep a brief journal about when they lost focus during group work and what strategy they will use to stay on task next time.",
            "Students rate their own understanding after each lesson and use that judgment to decide which problems to review.",
        ],
        "examples_negative": [
            "Mr. Smith tells students to try harder and pay attention.",
            "Students listen to Mr. Smith explain how they should think about their work.",
            "A definition of metacognition without an application to the class.",
        ],
    },
    {
        "part_id": "psychology-rub-2018-frq-002-Point-5",
        "label": "Point 5",
        "title": "Token Economy",
        "criteria": [
            {
                "points": 1,
                "criterion": (
                    "Response must describe a token economy in which Mr. Smith gives "
                    "tokens or points for specified desired classroom behaviors (such "
                    "as staying on task, cooperating, completing assignments, or "
                    "helping peers) and students exchange accumulated tokens for "
                    "backup reinforcers such as privileges, activities, or small "
                    "prizes. The response must apply the system to Mr. Smith's class; "
                    "merely defining a token economy or giving vague rewards without "
                    "a token-exchange procedure does not score."
                ),
            }
        ],
        "decision_rules": (
            "Score 1 only when the response identifies a token/point system, a "
            "specified desired behavior, and an exchange for a backup reward. "
            "Score 0 for a definition only, punishment-only systems, or vague "
            "rewards with no token-exchange procedure."
        ),
        "examples_positive": [
            "Mr. Smith gives students a token each time they stay on task during group work; students trade ten tokens for free time or a small prize.",
            "Students earn points for cooperating and completing assignments, and the points can be exchanged for classroom privileges.",
        ],
        "examples_negative": [
            "Mr. Smith gives students rewards when they behave.",
            "Mr. Smith punishes students who misbehave.",
            "A definition of token economy with no application to Mr. Smith's class.",
        ],
    },
    {
        "part_id": "psychology-rub-2018-frq-002-Point-6",
        "label": "Point 6",
        "title": "Part C: Mean Score",
        "criteria": [
            {
                "points": 1,
                "criterion": (
                    "Response must state that Mr. Smith's class mean of 70 is the "
                    "same as the state mean of 70, so the class's average performance "
                    "is at the state average. It does not show that the class performed "
                    "above or below the state average; the mean alone also does not "
                    "describe the shape or spread of the distribution."
                ),
            }
        ],
        "decision_rules": (
            "Score 1 for explaining that the class mean equals the state mean. "
            "Score 0 for saying the class mean is above/below the state mean, or "
            "for treating the mean as a description of the distribution's shape."
        ),
        "examples_positive": [
            "Mr. Smith's class mean is 70, which is the same as the state mean, so the class's average is at the state average.",
            "The class performed at the state average on mean, but the mean does not show how the scores are spread out.",
        ],
        "examples_negative": [
            "Mr. Smith's class performed above the state average because its mean is 70.",
            "The mean shows that most students scored near 70.",
        ],
    },
    {
        "part_id": "psychology-rub-2018-frq-002-Point-7",
        "label": "Point 7",
        "title": "Part C: Distribution of Scores",
        "criteria": [
            {
                "points": 1,
                "criterion": (
                    "Response must describe the class distribution as bimodal or "
                    "two-peaked (clearly not normal), with clusters of scores at both "
                    "the low and high ends and a dip near the mean. This indicates "
                    "substantial variability, with some students performing below and "
                    "some above the state average, even though the class mean equals "
                    "70. A response that calls the distribution normal, or only "
                    "restates the mean/range without describing the two peaks, does not score."
                ),
            }
        ],
        "decision_rules": (
            "Score 1 for identifying the two peaks/bimodal shape and explaining "
            "that scores cluster at low and high ends rather than around the mean. "
            "Score 0 for describing a normal distribution, only restating the mean, "
            "or giving a generic range statement with no bimodal interpretation."
        ),
        "examples_positive": [
            "The class distribution has two peaks, with many students scoring below the state average and many scoring above it, so the class is split into two groups.",
            "The graph is bimodal rather than normal: scores cluster at the low and high ends with relatively few students near the mean.",
        ],
        "examples_negative": [
            "The class distribution is normal, with most students near 70.",
            "The scores range from low to high, so the class performed at the state average.",
        ],
    },
]


def main() -> int:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = DB.with_name(f"{DB.name}.bak-{stamp}-2018-frq2-complete")
    shutil.copy2(DB, backup)
    print(f"backup: {backup}")

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        conn.execute("BEGIN IMMEDIATE")
        rubric = conn.execute(
            "SELECT rubric_id FROM frq_rubrics WHERE question_id=?",
            (QUESTION_ID,),
        ).fetchone()
        if not rubric:
            raise ValueError("2018 FRQ 2 rubric not found")
        rid = rubric["rubric_id"]

        conn.execute(
            "UPDATE frq_rubrics SET total_points=7, format='legacy_points', "
            "general_considerations=? WHERE rubric_id=?",
            (
                (
                    conn.execute(
                        "SELECT general_considerations FROM frq_rubrics WHERE rubric_id=?",
                        (rid,),
                    ).fetchone()[0]
                    or ""
                ).rstrip()
                + "\n\n"
                + PROVENANCE,
                rid,
            ),
        )

        for part in PARTS:
            conn.execute(
                """
                INSERT INTO rubric_parts (
                  part_id, rubric_id, label, title, max_points, criteria,
                  decision_rules, examples_positive, examples_negative, notes,
                  sort_order
                ) VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(part_id) DO UPDATE SET
                  label=excluded.label, title=excluded.title,
                  max_points=excluded.max_points, criteria=excluded.criteria,
                  decision_rules=excluded.decision_rules,
                  examples_positive=excluded.examples_positive,
                  examples_negative=excluded.examples_negative,
                  notes=excluded.notes, sort_order=excluded.sort_order
                """,
                (
                    part["part_id"],
                    rid,
                    part["label"],
                    part["title"],
                    json.dumps(part["criteria"], ensure_ascii=False),
                    part["decision_rules"],
                    json.dumps(part["examples_positive"], ensure_ascii=False),
                    json.dumps(part["examples_negative"], ensure_ascii=False),
                    "Manual reconstruction; source PDF ends after Point 3.",
                    int(part["label"].split()[-1]),
                ),
            )

        answer_text = conn.execute(
            "SELECT answer_text FROM questions WHERE question_id=?",
            (QUESTION_ID,),
        ).fetchone()[0] or ""
        if "RUBRIC PROVENANCE" not in answer_text:
            conn.execute(
                "UPDATE questions SET answer_text=? WHERE question_id=?",
                (answer_text.rstrip() + "\n\n" + PROVENANCE, QUESTION_ID),
            )

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    parts = conn.execute(
        "SELECT label,title,max_points FROM rubric_parts WHERE rubric_id=? ORDER BY sort_order",
        (RUBRIC_ID,),
    ).fetchall()
    total = conn.execute(
        "SELECT total_points FROM frq_rubrics WHERE rubric_id=?", (RUBRIC_ID,)
    ).fetchone()[0]
    if len(parts) != 7 or sum(p["max_points"] for p in parts) != 7 or total != 7:
        raise ValueError(f"rubric verification failed: {parts}, total={total}")
    if conn.execute("PRAGMA foreign_key_check").fetchall():
        raise ValueError("foreign_key_check failed")
    if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        raise ValueError("integrity_check failed")
    conn.close()
    print(f"2018 FRQ 2 rubric completed: {len(parts)} parts / {total} points")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
