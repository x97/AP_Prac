#!/usr/bin/env python3
"""Import the 75-question CB Supplemental Practice Exam MCQ.

Source: assets/psychology/papers/cb/26026_CB题库.pdf, pages 755-791 (full stems, options, answers
and explanations).  The paper is stored as ``mock_exam`` and is not tied to
a single curriculum unit.
"""
import os
import sqlite3
import sys

from pypdf import PdfReader

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from parse_cb import parse_unit  # noqa: E402

DB = os.path.join(ROOT, "data", "content", "psychology", "psychology_exam.db")
PDF = os.path.join(ROOT, "assets", "psychology", "papers", "cb", "26026_CB题库.pdf")
PDF_REL = os.path.relpath(PDF, ROOT)

PAPER_ID = "psychology-cb-2026-mock-1"
SOURCE_ID = "psychology-cb-bank-2026"
START_PAGE = 755
END_PAGE = 791
EXPECTED = 75


def main() -> int:
    reader = PdfReader(PDF)
    questions, gaps = parse_unit(reader, START_PAGE, END_PAGE)

    if len(questions) != EXPECTED:
        print(f"expected {EXPECTED} questions, parsed {len(questions)}", file=sys.stderr)
        return 1
    missing_answers = [q["number"] for q in questions if not q["answer"]]
    if missing_answers:
        print(f"missing answers: {missing_answers}", file=sys.stderr)
        return 1
    if gaps:
        print(f"number gaps: {gaps}", file=sys.stderr)
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
                None,
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
