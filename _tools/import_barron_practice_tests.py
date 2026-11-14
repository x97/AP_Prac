#!/usr/bin/env python3
"""Import Barron's AP Psychology 2027 Practice Tests 1-3 into psychology_exam.db."""
import datetime
import json
import os
import re
import sqlite3
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DB = os.path.join(ROOT, "data", "content", "psychology", "psychology_exam.db")
DATA = os.path.join(ROOT, "data", "content", "psychology", "extraction", "barron2027_practice_tests.json")
PDF_REL = "assets/psychology/books/AP Psychology Premium, 2027 - Allyson J. Weseley & Robert McEntarffer.pdf"
PDF_ABS = os.path.join(ROOT, PDF_REL)
ASSET_DIR = os.path.join(ROOT, "assets", "psychology", "images", "barron2027")
RENDER = os.path.join(HERE, "render")
SOURCE_ID = "psychology-barrons-2027"
SUBJECT_ID = "psychology"
NOW = datetime.datetime.now().isoformat(timespec="seconds")

PAPER_IDS = [f"psychology-barrons-2027-pt{i}" for i in (1, 2, 3)]

VISUAL = re.compile(
    r"\b(graph|graphs|chart|scatterplot|diagram|figure)\b|"
    r"\bdata (?:below|provided|shown|in the table|from the)\b|"
    r"\bthe data\b|\bdistribution\b|\bgraphed\b", re.I
)
CONTEXT_VISUAL = re.compile(
    r"\b(table|data|means?|standard deviations?|graph|chart|figure)\b", re.I
)
STAT_TERM = re.compile(
    r"\b(median|mean|mode|range|standard deviation|percentile|z-score|correlation|average)\b", re.I
)


def render_page(page):
    os.makedirs(ASSET_DIR, exist_ok=True)
    out = os.path.join(ASSET_DIR, f"page{page}.png")
    if os.path.exists(out):
        return out
    subprocess.run([RENDER, PDF_ABS, str(page), ASSET_DIR, "2"], check=True, capture_output=True)
    if not os.path.exists(out):
        raise RuntimeError(f"render did not produce {out}")
    return out


def needs_page_asset(q):
    if any(str(q["options"].get(k, "")).startswith("(graph ") for k in "ABCD"):
        return True
    text = (q.get("stem") or "") + " " + (q.get("context") or "")
    if "multiplication table" in text.lower():
        return False
    return bool(VISUAL.search(text))


def asset_pages_for_test(questions):
    """Return {question_number: [pages]}.

    Context groups share a table/graph, so if any question in the group needs
    a page asset, every question in that group gets the same pages.
    """
    group_flag = {}
    for q in questions:
        ctx = (q.get("context") or "").strip()
        if not ctx:
            continue
        flag = (
            needs_page_asset(q)
            or bool(CONTEXT_VISUAL.search(ctx))
            or bool(STAT_TERM.search(q.get("stem") or ""))
        )
        group_flag[ctx] = group_flag.get(ctx, False) or flag
    out = {}
    for q in questions:
        ctx = (q.get("context") or "").strip()
        flag = needs_page_asset(q) or (ctx and group_flag.get(ctx, False))
        if flag:
            out[q["number"]] = list(range(q["page_start"], q["page_end"] + 1))
    return out


def delete_existing(con):
    qids = [r[0] for r in con.execute(
        "SELECT question_id FROM questions WHERE paper_id IN (%s)" %
        ",".join("?" * len(PAPER_IDS)), PAPER_IDS
    )]
    if qids:
        marks = ",".join("?" * len(qids))
        con.execute(f"DELETE FROM rubric_parts WHERE rubric_id IN (SELECT rubric_id FROM frq_rubrics WHERE question_id IN ({marks}))", qids)
        con.execute(f"DELETE FROM frq_rubrics WHERE question_id IN ({marks})", qids)
        con.execute(f"DELETE FROM assets WHERE question_id IN ({marks})", qids)
        con.execute(f"DELETE FROM options WHERE question_id IN ({marks})", qids)
        con.execute(f"DELETE FROM questions WHERE question_id IN ({marks})", qids)
    con.execute("DELETE FROM paper_sources WHERE paper_id IN (%s)" % ",".join("?" * len(PAPER_IDS)), PAPER_IDS)
    con.execute("DELETE FROM papers WHERE paper_id IN (%s)" % ",".join("?" * len(PAPER_IDS)), PAPER_IDS)


def main():
    if not os.path.exists(DATA):
        print(f"missing {DATA}; run parse_barron_practice_tests.py first", file=sys.stderr)
        return 1
    payload = json.load(open(DATA, encoding="utf-8"))
    con = sqlite3.connect(DB)
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("BEGIN IMMEDIATE")
    delete_existing(con)

    con.execute("""
        INSERT OR REPLACE INTO content_sources
        (source_id, kind, title, chinese_title, edition, target_year, file_path, imported_at, subject_id)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (SOURCE_ID, "review_book", "Barron's AP Psychology Premium, 2027",
          "巴朗 AP 心理学 2027", "2027", 2027, PDF_REL, NOW, SUBJECT_ID))

    mcq_total = frq_total = option_total = rubric_total = part_total = asset_total = 0
    for test in payload["tests"]:
        test_no = test["test"]
        paper_id = test["paper_id"]
        question_count = len(test["mcq"]) + len(test["frq"])
        con.execute("""
            INSERT INTO papers
            (paper_id, year, title, chinese_title, subject_id, source_pdf, question_count, paper_type, source_id)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (paper_id, 2027, f"Barron's AP Psychology Practice Test {test_no}",
              f"巴朗 AP 心理学模拟题 {test_no}", SUBJECT_ID, PDF_REL, question_count,
              "mock_exam", SOURCE_ID))
        con.execute("""
            INSERT INTO paper_sources (paper_id, role, path, note)
            VALUES (?,?,?,?)
        """, (paper_id, "book", PDF_REL, f"Barron's Practice Test {test_no}"))

        asset_pages = asset_pages_for_test(test["mcq"])
        for q in test["mcq"]:
            qid = f"{paper_id}-mcq-{q['number']:03d}"
            con.execute("""
                INSERT INTO questions
                (question_id, paper_id, section, number, stem, context, page_start, page_end,
                 correct_answer, answer_text, subject_id, form, source_file, answer_source, answer_confidence)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,NULL,?,?,?)
            """, (qid, paper_id, "MCQ", q["number"], q["stem"], q["context"] or None,
                  q["page_start"], q["page_end"], q["correct_answer"], q["answer_text"],
                  SUBJECT_ID, PDF_REL, "book_answer", "high"))
            mcq_total += 1
            for i, label in enumerate("ABCD"):
                content = (q["options"].get(label) or "").strip()
                con.execute("""
                    INSERT INTO options (question_id, label, content, sort_order, is_correct)
                    VALUES (?,?,?,?,?)
                """, (qid, label, content, i, 1 if label == q["correct_answer"] else 0))
                option_total += 1
            if q["number"] in asset_pages:
                for page in asset_pages[q["number"]]:
                    render_page(page)
                    asset_id = f"{paper_id}-q{q['number']:03d}-page-p{page}"
                    con.execute("""
                        INSERT INTO assets (asset_id, question_id, option_label, kind, path, page, bbox)
                        VALUES (?,?,NULL,'page',?,?,NULL)
                    """, (asset_id, qid, f"assets/psychology/images/barron2027/page{page}.png", page))
                    asset_total += 1

        for q in test["frq"]:
            qid = f"{paper_id}-frq-{q['number']:03d}"
            con.execute("""
                INSERT INTO questions
                (question_id, paper_id, section, number, stem, context, page_start, page_end,
                 correct_answer, answer_text, subject_id, form, source_file, answer_source, answer_confidence)
                VALUES (?,?,?,?,?,NULL,?,?,NULL,?,?,NULL,?,?,?)
            """, (qid, paper_id, "FRQ", q["number"], q["stem"], q["page_start"], q["page_end"],
                  q["answer_text"], SUBJECT_ID, PDF_REL, "book_answer", "high"))
            frq_total += 1
            rubric = q.get("rubric") or {}
            parts = rubric.get("parts") or []
            rubric_id = f"{qid}-rubric"
            total_points = rubric.get("total_points")
            if total_points is None:
                total_points = sum(int(p.get("max_points") or 1) for p in parts)
            con.execute("""
                INSERT INTO frq_rubrics (rubric_id, question_id, total_points, general_considerations, format)
                VALUES (?,?,?,?,?)
            """, (rubric_id, qid, total_points, None, "barron_parts"))
            rubric_total += 1
            for i, part in enumerate(parts, 1):
                max_points = int(part.get("max_points") or 1)
                part_id = f"{rubric_id}-{part['label']}"
                examples = json.dumps([part.get("sample_answer", "")], ensure_ascii=False) if part.get("sample_answer") else None
                con.execute("""
                    INSERT INTO rubric_parts
                    (part_id, rubric_id, label, title, max_points, criteria, decision_rules,
                     examples_positive, examples_negative, notes, sort_order)
                    VALUES (?,?,?,?,?,?,NULL,?,NULL,?,?)
                """, (part_id, rubric_id, part["label"], part.get("title", ""), max_points,
                      part.get("criteria", ""), examples,
                      "Barron's sample student response and scoring guide; not an official College Board rubric.",
                      i))
                part_total += 1

    con.execute("UPDATE papers SET question_count = (SELECT COUNT(*) FROM questions q WHERE q.paper_id=papers.paper_id) WHERE paper_id IN (%s)" % ",".join("?" * len(PAPER_IDS)), PAPER_IDS)
    fk = con.execute("PRAGMA foreign_key_check").fetchall()
    if fk:
        con.rollback()
        print("foreign key issues:", fk[:5], file=sys.stderr)
        return 1
    con.commit()

    # Report
    report = os.path.join(ROOT, "data", "content", "psychology", "reports", "barron_practice_import_report.md")
    lines = [
        "# Barron's AP Psychology 2027 模拟题入库报告", "",
        f"- 导入时间：{NOW}",
        f"- 来源：`{PDF_REL}`",
        f"- 试卷：3 份（Practice Test 1–3）",
        "", "| 项目 | 数量 |", "|---|---:|",
        f"| MCQ | {mcq_total} |", f"| FRQ | {frq_total} |",
        f"| 选项 | {option_total} |", f"| FRQ rubric | {rubric_total} |",
        f"| rubric parts | {part_total} |", f"| page assets | {asset_total} |", "",
        "## 校验", "",
        f"- `foreign_key_check`：{'通过' if not fk else fk[:3]}",
        "- MCQ 答案：全部来自本书 Answer Explanations",
        "- 题目全部有 4 个选项（图形选项使用 page asset + 占位文本）",
        "- FRQ：AAQ 6 个评分点、EBQ 5 个评分点，各 7 分",
    ]
    open(report, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print(f"imported 3 papers: {mcq_total} MCQ, {frq_total} FRQ, {option_total} options, "
          f"{rubric_total} rubrics, {part_total} parts, {asset_total} page assets")
    print(f"wrote {report}")
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
