#!/usr/bin/env python3
"""Import Myers 4e module reviews, unit practice, and Appendix A mock exam.

The student edition does not print an MCQ answer key.  Questions are imported
with correct_answer NULL and answer_source='none'; a separate inference pass
can fill them and must mark them ai_inferred.
"""
import argparse
import json
import os
import re
import shutil
import sqlite3
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
EXAM_DB = os.path.join(ROOT, "data", "content", "psychology", "psychology_exam.db")
TEXT = os.path.join(ROOT, "data", "content", "psychology", "extraction", "myers", "cache", "myers.txt")
MODULES = os.path.join(ROOT, "data", "content", "psychology", "extraction", "myers", "myers_modules.json")
REPORT = os.path.join(ROOT, "data", "content", "psychology", "extraction", "myers", "myers_questions_report.md")

SOURCE_ID = "psychology-myers-2024"
PDF_NAME = "assets/psychology/books/教材1--Myers.pdf"
UNIT_TITLES = {
    "0": ("An Introduction to Psychological Science", "科学实践与研究基础"),
    "1": ("Biological Bases of Behavior", "生物基础"),
    "2": ("Cognition", "认知"),
    "3": ("Development and Learning", "发展与学习"),
    "4": ("Social Psychology and Personality", "社会心理学与人格"),
    "5": ("Mental and Physical Health", "心理与身体健康"),
}


def delete_paper(con, paper_id):
    con.execute(
        "DELETE FROM options WHERE question_id IN "
        "(SELECT question_id FROM questions WHERE paper_id=?)", (paper_id,)
    )
    con.execute(
        "DELETE FROM assets WHERE question_id IN "
        "(SELECT question_id FROM questions WHERE paper_id=?)", (paper_id,)
    )
    con.execute("DELETE FROM questions WHERE paper_id=?", (paper_id,))
    con.execute("DELETE FROM papers WHERE paper_id=?", (paper_id,))


def clean_lines(text):
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line or re.fullmatch(r"\d{1,4}", line):
            continue
        if line.startswith("AP® Practice Multiple Choice"):
            continue
        if line == "Questions" and out and out[-1].startswith("AP® Practice"):
            continue
        out.append(line)
    return out


def parse_block(text):
    lines = clean_lines(text)
    questions = []
    current = None
    contexts = []
    index = 0
    while index < len(lines):
        line = lines[index]
        match = re.match(
            r"Use (?:the following|this) .*?questions?\s+(\d+)(?:\s*(?:[–-]|and)\s*(\d+))?",
            line, re.I,
        )
        if match:
            start = int(match.group(1))
            end = int(match.group(2) or start)
            parts = [line]
            index += 1
            while index < len(lines) and not re.match(r"^\d{1,3}\.\s", lines[index]):
                parts.append(lines[index])
                index += 1
            contexts.append((" ".join(parts), start, end))
            continue
        match = re.match(r"^(\d{1,3})\.\s*(.*)$", line)
        if match:
            number = int(match.group(1))
            expected = questions[-1]["n"] + 1 if questions else 1
            if number == expected or (not questions and number == 1):
                current = {"n": number, "stem": [match.group(2)], "options": []}
                questions.append(current)
                index += 1
                continue
        option = re.match(r"^([a-d])\.\s*(.*)$", line)
        if option and current is not None:
            label = option.group(1).upper()
            if label not in [item[0] for item in current["options"]]:
                current["options"].append([label, option.group(2)])
                index += 1
                continue
        if current is not None:
            if current["options"]:
                current["options"][-1][1] += " " + line
            else:
                current["stem"].append(line)
            index += 1
            continue
        index += 1
    for question in questions:
        question["stem"] = " ".join(question["stem"]).strip()
        question["options"] = [
            (label, re.sub(r"\s+", " ", content).strip())
            for label, content in question["options"]
        ]
        question["context"] = next(
            (text for text, start, end in contexts
             if start <= question["n"] <= end),
            None,
        )
    return questions


def find_page(pages, start, end, stem):
    needle = re.sub(r"\s+", " ", stem)[:70].lower()
    for page in range(start, end + 1):
        if needle and needle in re.sub(r"\s+", " ", pages[page - 1]).lower():
            return page
    return start


def collect_units(pages, modules):
    units = {unit: [] for unit in UNIT_TITLES}
    incomplete = []
    for module in modules:
        text = "\n".join(pages[p - 1] for p in range(module["start"], module["end"] + 1))
        heading = text.find("AP® Practice Multiple Choice")
        if heading < 0:
            continue
        segment = re.split(r"Unit\s+\d+\s+AP® Practice", text[heading:])[0]
        for question in parse_block(segment):
            question["form"] = f"Module {module['code']} Review"
            question["page_start"] = find_page(
                pages, module["start"], module["end"], question["stem"]
            )
            question["page_end"] = question["page_start"]
            if len(question["options"]) != 4 or not question["stem"]:
                incomplete.append((module["code"], question))
                continue
            units[module["unit"]].append(question)

    for unit in range(6):
        start = next(
            page for page in range(180, 2605)
            if re.search(rf"Unit\s+{unit}\s+AP® Practice Multiple Choice", pages[page - 1])
        )
        next_starts = [module["start"] for module in modules if module["start"] > start]
        end = min(next_starts) - 1 if next_starts else 2600
        text = "\n".join(pages[p - 1] for p in range(start, end + 1))
        for question in parse_block(text):
            question["form"] = f"Unit {unit} AP Practice"
            question["page_start"] = find_page(pages, start, end, question["stem"])
            question["page_end"] = question["page_start"]
            if len(question["options"]) != 4 or not question["stem"]:
                incomplete.append((f"Unit {unit}", question))
                continue
            units[str(unit)].append(question)
    return units, incomplete


def collect_mock(pages):
    text = "\n".join(pages[p - 1] for p in range(2605, 2635))
    questions = parse_block(text)
    for question in questions:
        question["form"] = "Appendix A Practice Exam"
        question["page_start"] = find_page(pages, 2605, 2634, question["stem"])
        question["page_end"] = question["page_start"]
    # Section II: EBQ + AAQ, stored as prompt text only; no scoring guide in
    # the student edition.
    frq1 = "\n".join(pages[p - 1] for p in range(2635, 2639))
    frq2 = "\n".join(pages[p - 1] for p in range(2639, 2642))
    frq1 = frq1.split("ARTICLE ANALYSIS QUESTION")[0].strip()
    frq2 = frq2.split("Appendix B")[0].strip()
    return questions, [
        {"number": 1, "stem": frq1, "page_start": 2635, "page_end": 2638},
        {"number": 2, "stem": frq2, "page_start": 2639, "page_end": 2641},
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=EXAM_DB)
    parser.add_argument("--no-backup", action="store_true")
    args = parser.parse_args()

    with open(TEXT, encoding="utf-8", errors="replace") as handle:
        pages = handle.read().split("\f")
    with open(MODULES, encoding="utf-8") as handle:
        modules = json.load(handle)
    units, incomplete = collect_units(pages, modules)
    mock_questions, mock_frqs = collect_mock(pages)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    if not args.no_backup:
        backup = args.db + f".bak-{stamp}-before-myers-questions"
        shutil.copy2(args.db, backup)
        print("backup:", backup)

    con = sqlite3.connect(args.db)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    now = datetime.now().astimezone().isoformat(timespec="seconds")

    con.execute(
        """
        INSERT OR IGNORE INTO content_sources
        (source_id, kind, title, chinese_title, edition, target_year,
         file_path, imported_at, subject_id)
        VALUES (?,?,?,?,?,?,?,?,?)
        """,
        (SOURCE_ID, "textbook", "Myers' Psychology for the AP Course",
         "Myers AP 心理学教材", "4th", 2024, PDF_NAME, now, "psychology"),
    )

    paper_ids = []
    for unit, questions in units.items():
        paper_id = f"psychology-myers-2024-u{unit}"
        paper_ids.append(paper_id)
        title_en, title_zh = UNIT_TITLES[unit]
        delete_paper(con, paper_id)
        con.execute(
            """
            INSERT INTO papers
            (paper_id, year, title, chinese_title, subject_id, source_pdf,
             question_count, paper_type, source_id)
            VALUES (?,?,?,?,?,?,?,?,?)
            """,
            (paper_id, 2024,
             f"Myers' AP Psychology Unit {unit} Practice — {title_en}",
             f"Myers AP 心理学 Unit {unit} 练习 · {title_zh}",
             "psychology", PDF_NAME, len(questions), "unit_practice", SOURCE_ID),
        )
        for index, question in enumerate(questions, 1):
            qid = f"psychology-myers24-u{unit}-{index:04d}"
            con.execute(
                """
                INSERT INTO questions
                (question_id, paper_id, section, number, stem, context,
                 page_start, page_end, correct_answer, answer_text, subject_id,
                 form, source_file, answer_source, answer_confidence)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (qid, paper_id, "MCQ", index, question["stem"],
                 question.get("context"), question["page_start"],
                 question["page_end"], None, None, "psychology",
                 question["form"], PDF_NAME, "none", "none"),
            )
            for label, content in question["options"]:
                con.execute(
                    "INSERT INTO options(question_id,label,content,sort_order,is_correct)"
                    " VALUES (?,?,?,?,0)",
                    (qid, label, content, ord(label) - ord("A") + 1),
                )

    mock_id = "psychology-myers-2024-mock-1"
    paper_ids.append(mock_id)
    delete_paper(con, mock_id)
    con.execute(
        """
        INSERT INTO papers
        (paper_id, year, title, chinese_title, subject_id, source_pdf,
         question_count, paper_type, source_id)
        VALUES (?,?,?,?,?,?,?,?,?)
        """,
        (mock_id, 2024,
         "Myers' AP Psychology Practice AP-Style Exam (Appendix A)",
         "Myers AP 心理学模拟题 · Appendix A Practice Exam",
         "psychology", PDF_NAME, len(mock_questions) + len(mock_frqs),
         "mock_exam", SOURCE_ID),
    )
    for index, question in enumerate(mock_questions, 1):
        qid = f"psychology-myers24-mock1-{index:04d}"
        con.execute(
            """
            INSERT INTO questions
            (question_id, paper_id, section, number, stem, context,
             page_start, page_end, correct_answer, answer_text, subject_id,
             form, source_file, answer_source, answer_confidence)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (qid, mock_id, "MCQ", index, question["stem"],
             question.get("context"), question["page_start"],
             question["page_end"], None, None, "psychology",
             question["form"], PDF_NAME, "none", "none"),
        )
        for label, content in question["options"]:
            con.execute(
                "INSERT INTO options(question_id,label,content,sort_order,is_correct)"
                " VALUES (?,?,?,?,0)",
                (qid, label, content, ord(label) - ord("A") + 1),
            )
    for frq in mock_frqs:
        qid = f"psychology-myers24-mock1-frq-{frq['number']:03d}"
        con.execute(
            """
            INSERT INTO questions
            (question_id, paper_id, section, number, stem, context,
             page_start, page_end, correct_answer, answer_text, subject_id,
             form, source_file, answer_source, answer_confidence)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (qid, mock_id, "FRQ", frq["number"], frq["stem"], None,
             frq["page_start"], frq["page_end"], None,
             "Source PDF does not include official scoring guidelines.",
             "psychology", "Appendix A Practice Exam", PDF_NAME, "none", "none"),
        )

    con.commit()
    integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
    fk = con.execute("PRAGMA foreign_key_check").fetchall()

    with open(REPORT, "w", encoding="utf-8") as handle:
        handle.write("# Myers 4e 题目抽取报告\n\n")
        handle.write(f"- Source: `{PDF_NAME}`\n")
        handle.write(f"- Unit practice papers: {len(units)}\n")
        handle.write(f"- Mock paper: 75 MCQ + 2 FRQ\n")
        handle.write("- MCQ answers: **not printed in the student edition**; "
                     "`correct_answer=NULL`, `answer_source='none'`.\n\n")
        handle.write("| Paper | MCQ | FRQ |\n|---|---:|---:|\n")
        for unit, questions in units.items():
            handle.write(f"| Unit {unit} | {len(questions)} | 0 |\n")
        handle.write(f"| Mock | {len(mock_questions)} | {len(mock_frqs)} |\n")
        handle.write("\n## Incomplete source questions (skipped)\n\n")
        for source, question in incomplete:
            handle.write(
                f"- {source} Q{question['n']}: "
                f"{len(question['options'])} options; {question['stem'][:100]}\n"
            )
        handle.write(f"\n- integrity: {integrity}\n")
        handle.write(f"- foreign_key_check: {'OK' if not fk else 'FAIL'}\n")
    print("papers:", paper_ids)
    print("MCQs:", sum(len(qs) for qs in units.values()) + len(mock_questions))
    print("FRQs:", len(mock_frqs), "incomplete skipped:", len(incomplete))
    print("integrity:", integrity, "fk:", "OK" if not fk else fk[:3])
    print("report:", REPORT)
    con.close()


if __name__ == "__main__":
    main()
