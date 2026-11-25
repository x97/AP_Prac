#!/usr/bin/env python3
"""Import the 75-question CB Supplemental Practice Exam MCQ.

Source: assets/psychology/papers/cb/26026_CB题库.pdf, pages 755-791 (full
stems, options, answers, explanations and shared stimuli).  The paper is stored
as ``mock_exam`` and is not tied to a single curriculum unit.

Shared stimuli are parsed into ``questions.context``.  ``CONTEXT_GROUPS`` is
the paper's explicit stimulus map; every question in a set receives the same
context instead of only the first one.  ``validate()`` fails the import if a
known stimulus is missing or if a page header leaked into a stem/option.
"""
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from parse_cb import extract_layout_text, parse_unit_text  # noqa: E402

DB = os.path.join(ROOT, "data", "content", "psychology", "psychology_exam.db")
PDF = os.path.join(ROOT, "assets", "psychology", "papers", "cb", "26026_CB题库.pdf")
PDF_REL = os.path.relpath(PDF, ROOT)

PAPER_ID = "psychology-cb-2026-mock-1"
SOURCE_ID = "psychology-cb-bank-2026"
START_PAGE = 755
END_PAGE = 791
EXPECTED = 75

# Stimulus map for this paper.  Each list is [anchor, ...members]: the block
# before the anchor question (a passage, study, graph lead-in or table) is
# shared by every question in the set.  The parser copies the anchor context
# to the other members.  Do not remove an entry without re-reading the PDF;
# a missing entry is exactly the bug that left Q2/Q3 without their passage.
# Human-readable copy with pages and standalone stimuli:
# data/content/psychology/extraction/psychology-cb-2026-mock-1_stimulus_map.json
CONTEXT_GROUPS = [
    [8, 9, 10],    # Dr. Collins study + height/weight graph
    [19, 20, 21],  # Dr. Steinberg scary-movie experiment
    [35, 36, 37],  # Dr. Reyes naturalistic observation + graph
    [54, 55, 56],  # Dr. Pilkington teacher-stress interviews + source list
    [65, 66, 67],  # engineering-program table
]
# Questions with an explicitly standalone stimulus.  Q2/Q3 are the page-755
# regression examples; Q8 and Q65 anchor multi-question sets.
REQUIRED_CONTEXT = (2, 3, 8, 19, 35, 54, 65)


def validate(questions: list[dict]) -> list[str]:
    errors: list[str] = []
    if len(questions) != EXPECTED:
        errors.append(f"expected {EXPECTED} questions, parsed {len(questions)}")
    missing_answers = [q["number"] for q in questions if not q["answer"]]
    if missing_answers:
        errors.append(f"missing answers: {missing_answers}")
    by_number = {q["number"]: q for q in questions}
    for number in REQUIRED_CONTEXT:
        if not by_number.get(number, {}).get("context"):
            errors.append(f"Q{number} is missing its shared context")
    for group in CONTEXT_GROUPS:
        anchor_context = by_number.get(group[0], {}).get("context")
        for number in group:
            question = by_number.get(number)
            if question is None:
                errors.append(f"Q{number} from context group is missing")
            elif not question.get("context"):
                errors.append(f"Q{number} has no context but belongs to {group}")
            elif question.get("context") != anchor_context:
                errors.append(
                    f"Q{number} context differs from group anchor Q{group[0]}"
                )
    header_markers = ("Supplemental Practice Exam MCQ", "Scoring Guide", "- PAGE :")
    for question in questions:
        for field in ("stem", "answer_text"):
            if any(marker in question[field] for marker in header_markers):
                errors.append(f"Q{question['number']} {field} contains a page header")
        if set(question["options"]) != {"A", "B", "C", "D"}:
            errors.append(
                f"Q{question['number']} options are {sorted(question['options'])}"
            )
        for label, content in question["options"].items():
            if any(marker in content for marker in header_markers):
                errors.append(
                    f"Q{question['number']} option {label} contains a page header"
                )
    return errors


def main() -> int:
    text = extract_layout_text(PDF, START_PAGE, END_PAGE)
    questions, gaps = parse_unit_text(text, context_groups=CONTEXT_GROUPS)

    errors = validate(questions)
    if gaps:
        errors.append(f"number gaps: {gaps}")
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    con = sqlite3.connect(DB)
    con.execute("PRAGMA foreign_keys=ON")

    # Idempotent re-import of this paper only.
    old_ids = [r[0] for r in con.execute(
        "SELECT question_id FROM questions WHERE paper_id=?", (PAPER_ID,))]
    if old_ids:
        marks = ",".join("?" for _ in old_ids)
        con.execute(f"DELETE FROM assets WHERE question_id IN ({marks})", old_ids)
        con.execute(f"DELETE FROM options WHERE question_id IN ({marks})", old_ids)
        con.execute(f"DELETE FROM question_units WHERE question_id IN ({marks})", old_ids)
    con.execute("DELETE FROM questions WHERE paper_id=?", (PAPER_ID,))
    con.execute("DELETE FROM paper_units WHERE paper_id=?", (PAPER_ID,))
    con.execute("DELETE FROM paper_sources WHERE paper_id=?", (PAPER_ID,))
    con.execute("DELETE FROM papers WHERE paper_id=?", (PAPER_ID,))

    con.execute(
        "INSERT INTO papers (paper_id, year, title, chinese_title, subject_id, "
        "source_pdf, question_count, paper_type, source_id) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        (
            PAPER_ID,
            2026,
            "AP Classroom Supplemental Practice Exam — MCQ",
            "CB 补充模拟卷 · 75 道选择题（面向 2027 考试）",
            "psychology",
            PDF_REL,
            len(questions),
            "mock_exam",
            SOURCE_ID,
        ),
    )
    con.execute(
        "INSERT INTO paper_sources (paper_id, role, path, note) VALUES (?,?,?,?)",
        (PAPER_ID, "questions", PDF_REL, "Supplemental Practice Exam MCQ"),
    )
    con.execute(
        "INSERT INTO paper_sources (paper_id, role, path, note) VALUES (?,?,?,?)",
        (PAPER_ID, "answer_key", PDF_REL, "Answer lines and rationales"),
    )

    for q in questions:
        number = q["number"]
        qid = f"psychology-cb26-mock1-{number:04d}"
        con.execute(
            "INSERT INTO questions (question_id, paper_id, section, number, stem, "
            "context, page_start, page_end, correct_answer, answer_text, subject_id, "
            "source_file, answer_source) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                qid,
                PAPER_ID,
                "MCQ",
                number,
                q["stem"],
                q["context"],
                None,
                None,
                q["answer"],
                q["explanation"] or None,
                "psychology",
                PDF_REL,
                "official",
            ),
        )
        for order, label in enumerate("ABCD"):
            if label not in q["options"]:
                continue
            con.execute(
                "INSERT INTO options (question_id, label, content, sort_order, is_correct) "
                "VALUES (?,?,?,?,?)",
                (qid, label, q["options"][label], order, 1 if label == q["answer"] else 0),
            )

    con.commit()
    print(f"imported {len(questions)} questions into {PAPER_ID}")
    print("  options:", con.execute(
        "SELECT COUNT(*) FROM options WHERE question_id LIKE 'psychology-cb26-mock1-%'"
    ).fetchone()[0])
    print("  answered:", con.execute(
        "SELECT COUNT(*) FROM questions WHERE paper_id=? AND correct_answer IS NOT NULL",
        (PAPER_ID,),
    ).fetchone()[0])
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
