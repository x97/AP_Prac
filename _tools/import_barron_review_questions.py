#!/usr/bin/env python3
"""Import Barron's AP Psychology 2027 chapter-end Review Questions.

Each chapter becomes one ``unit_practice`` paper, matching the CB unit-practice
paper type while preserving the book's chapter-level numbering.
"""
import datetime
import json
import os
import sqlite3
import subprocess
import sys
from collections import defaultdict

from PIL import Image, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DB = os.path.join(ROOT, "data", "content", "psychology", "psychology_exam.db")
DATA = os.path.join(ROOT, "data", "content", "psychology", "extraction", "barron2027_review_questions.json")
PDF_REL = "assets/psychology/books/AP Psychology Premium, 2027 - Allyson J. Weseley & Robert McEntarffer.pdf"
PDF_ABS = os.path.join(ROOT, PDF_REL)
ASSET_DIR = os.path.join(ROOT, "assets", "psychology", "images", "barron2027_review")
RENDER = os.path.join(HERE, "render")
LINES = os.path.join(ROOT, "data", "content", "psychology", "extraction", "book_text", "review_line_boxes.tsv")
SOURCE_ID = "psychology-barrons-2027"
SUBJECT_ID = "psychology"
NOW = datetime.datetime.now().isoformat(timespec="seconds")

PAGE_W = 612.0
PAGE_H = 792.0
RENDER_SCALE = 2.0
CROP_PAD = 14

# One entry per visual stimulus. A figure/table is attached to each question in
# ``questions``; the image itself is cropped from the source page, never a full
# page screenshot. ``after`` and ``before`` are text anchors immediately above
# and below the visual.
FIGURES = [
    dict(chapter=4, key="neuron-diagram", kind="figure", page=88,
         questions=[8, 9, 10],
         after="Use this diagram for items 8–10.",
         before="In the diagram, X represents one neuron and Y represents"),
    dict(chapter=5, key="rem-sleep-graph", kind="figure", page=109,
         questions=[2, 3, 4],
         after="Monday. The graph below shows the results of the study.",
         before="The results provide the strongest support for the argument"),
    dict(chapter=5, key="sleep-chart", kind="figure", page=110,
         questions=[5], after="questions.", before=None),
    dict(chapter=6, key="vision-hearing-scatter", kind="figure", page=130,
         questions=[5], after="the chart?",
         before="Both vision and hearing decline after age 65."),
    dict(chapter=7, key="name-recognition-table", kind="table", page=148,
         questions=[6, 7, 8], after="table below",
         before="If the researchers’ wanted to see if there was a relationship"),
    dict(chapter=9, key="toy-recall-table", kind="table", page=178,
         questions=[4, 5], after="summarized in the table below.", before=None),
    dict(chapter=9, key="study-method-table", kind="table", page=180,
         questions=[7, 8], after=None,
         before="Which will be higher in the Space Method group?"),
    dict(chapter=10, key="praise-table", kind="table", page=201,
         questions=[4, 5], after="below.",
         before="These results best support the idea that academic achievement"),
    dict(chapter=11, key="extraversion-change-graph", kind="figure", page=227,
         questions=[2], after="6 as measured on a 50-point scale.", before=None),
    dict(chapter=12, key="fish-learning-graph", kind="figure", page=259,
         questions=[2, 3], after=None,
         before="What is a reasonable conclusion based on the information"),
    dict(chapter=13, key="locus-health-scatter", kind="figure", page=291,
         questions=[3], after="internal locus of control. His findings are shown below.",
         before="Based on the graph and your knowledge of psychology, which"),
    dict(chapter=13, key="free-throw-table", kind="table", page=295,
         questions=[13, 14], after="games.",
         before="What might explain the phenomenon noticed by Coach Price?"),
    dict(chapter=14, key="upr-swb-graph", kind="figure", page=310,
         questions=[3, 4], after="The data she has collected is graphed below.", before=None),
    dict(chapter=14, key="culture-personality-table", kind="table", page=311,
         questions=[5, 6, 7],
         after="Use the information below to answer questions 5–7.",
         before="According to the data, individualistic and collectivist cultures differ most in"),
    dict(chapter=15, key="emotion-recognition-table", kind="table", page=332,
         questions=[6, 7], after="data from the study is presented below.",
         before="Which of the following is an appropriate conclusion to draw"),
    dict(chapter=16, key="health-center-graph", kind="figure", page=343,
         questions=[3, 4, 5], after="Jaime collects the data shown in the graph below.",
         before="The increased percentage of students seeking help during the"),
    dict(chapter=16, key="swb-table", kind="table", page=344,
         questions=[6, 7], after="appear in the table below.", before=None),
    dict(chapter=16, key="happiness-traits-table", kind="table", page=345,
         questions=[8], after="characteristics and happiness.", before=None),
    dict(chapter=16, key="journal-happiness-scatter", kind="figure", page=346,
         questions=[9, 10, 11], after="journals, and creates the graph below.",
         before="Based on the data in the graph, which can Ms. Jenson"),
    dict(chapter=17, key="perspective-graph", kind="figure", page=371,
         questions=[4, 5, 6], after=None,
         before="From the data, Luisa will be able to calculate the"),
    dict(chapter=18, key="therapy-table", kind="table", page=394,
         questions=[4, 5, 6],
         after="ratings, divided by condition, are seen in the table below.",
         before="Which conclusion is best supported by the data?"),
]

# The PDF parser also captures table cells as part of the shared context.
# Since the cropped table is displayed separately, cut the context at the
# sentence that introduces it.
CONTEXT_STOPS = {
    "rem-sleep-graph": "The graph below shows the results of the study.",
    "name-recognition-table": "The data appear in the table below",
    "toy-recall-table": "Their performance is summarized in the table below.",
    "study-method-table": (
        "Matthew decides to compare their performance on the quiz and some of "
        "the data appear in the table below."
    ),
    "praise-table": "The results are displayed in the table below.",
    "free-throw-table": (
        "As evidence, she shows them the table below that includes the free "
        "throw percentages for the starting five players across the last few "
        "practices as opposed to the last few games."
    ),
    "culture-personality-table": "Use the information below to answer questions 5–7.",
    "emotion-recognition-table": "The data from the study is presented below.",
    "swb-table": "his findings appear in the table below.",
    "therapy-table": (
        "Their mean ratings, divided by condition, are seen in the table below."
    ),
}


def render_page(page):
    os.makedirs(ASSET_DIR, exist_ok=True)
    out = os.path.join(ASSET_DIR, f"page{page}.png")
    if os.path.exists(out):
        return out
    subprocess.run([RENDER, PDF_ABS, str(page), ASSET_DIR, "2"], check=True, capture_output=True)
    if not os.path.exists(out):
        raise RuntimeError(f"render did not produce {out}")
    return out


def load_lines():
    rows = defaultdict(list)
    for line in open(LINES, encoding="utf-8"):
        page, _, x, y, w, h, text = line.rstrip("\n").split("\t", 6)
        rows[int(page)].append((float(x), float(y), float(w), float(h), text))
    return rows


def find_line(lines, page, needle):
    hits = [row for row in lines[page] if needle in row[4]]
    if len(hits) != 1:
        raise RuntimeError(
            f"page {page}: expected one line containing {needle!r}, got {len(hits)}"
        )
    return hits[0]


def crop_figure(spec, lines):
    """Crop one figure/table from its source page and return (path, bbox)."""
    page = spec["page"]
    page_path = render_page(page)
    top_pdf = 790.0 if spec["after"] is None else find_line(lines, page, spec["after"])[1] - 8
    if spec["before"] is None:
        bottom_pdf = 36.0
    else:
        _, y, _, h, _ = find_line(lines, page, spec["before"])
        bottom_pdf = y + h + 8
    if top_pdf <= bottom_pdf:
        raise RuntimeError(f"bad crop range for {spec['key']}: {top_pdf} <= {bottom_pdf}")

    image = Image.open(page_path).convert("RGB")
    box = (
        int(50 * RENDER_SCALE),
        int((PAGE_H - top_pdf) * RENDER_SCALE),
        int(562 * RENDER_SCALE),
        int((PAGE_H - bottom_pdf) * RENDER_SCALE),
    )
    crop = image.crop(box)
    bbox = ImageChops.difference(
        crop, Image.new("RGB", crop.size, (255, 255, 255))
    ).getbbox()
    if not bbox:
        raise RuntimeError(f"blank crop for {spec['key']}")

    pad = CROP_PAD
    left = max(0, bbox[0] - pad)
    top = max(0, bbox[1] - pad)
    right = min(crop.width, bbox[2] + pad)
    bottom = min(crop.height, bbox[3] + pad)
    crop = crop.crop((left, top, right, bottom))

    out = os.path.join(ASSET_DIR, f"fig-{spec['key']}.png")
    crop.save(out)
    abs_left = box[0] + left
    abs_top = box[1] + top
    abs_right = box[0] + right
    abs_bottom = box[1] + bottom
    bbox_rel = [
        round(abs_left / image.width, 4),
        round(abs_top / image.height, 4),
        round(abs_right / image.width, 4),
        round(abs_bottom / image.height, 4),
    ]
    rel = os.path.relpath(out, ROOT)
    return rel, bbox_rel


def delete_existing(con):
    paper_ids = [r[0] for r in con.execute(
        "SELECT paper_id FROM papers WHERE paper_id LIKE 'psychology-barrons-2027-ch%-review'"
    )]
    if not paper_ids:
        return
    marks = ",".join("?" for _ in paper_ids)
    qids = [r[0] for r in con.execute(
        f"SELECT question_id FROM questions WHERE paper_id IN ({marks})", paper_ids
    )]
    if qids:
        qmarks = ",".join("?" for _ in qids)
        con.execute(f"DELETE FROM assets WHERE question_id IN ({qmarks})", qids)
        con.execute(f"DELETE FROM options WHERE question_id IN ({qmarks})", qids)
        con.execute(f"DELETE FROM questions WHERE question_id IN ({qmarks})", qids)
    con.execute(f"DELETE FROM paper_sources WHERE paper_id IN ({marks})", paper_ids)
    con.execute(f"DELETE FROM papers WHERE paper_id IN ({marks})", paper_ids)


def main():
    if not os.path.exists(DATA):
        print(f"missing {DATA}; run parse_barron_review_questions.py first", file=sys.stderr)
        return 1
    payload = json.load(open(DATA, encoding="utf-8"))
    line_rows = load_lines()
    figures_by_chapter = defaultdict(dict)
    for fig in FIGURES:
        for number in fig["questions"]:
            if number in figures_by_chapter[fig["chapter"]]:
                raise RuntimeError(f"chapter {fig['chapter']} Q{number} has two figures")
            figures_by_chapter[fig["chapter"]][number] = fig
    figure_cache = {}

    con = sqlite3.connect(DB)
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("BEGIN IMMEDIATE")
    delete_existing(con)

    total_q = total_ans = total_opt = total_assets = 0
    for chapter in payload["chapters"]:
        ch = chapter["chapter"]
        title = chapter["chapter_title"]
        paper_id = chapter["paper_id"]
        questions = chapter["questions"]
        con.execute("""
            INSERT INTO papers
            (paper_id, year, title, chinese_title, subject_id, source_pdf, question_count, paper_type, source_id)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (paper_id, 2027,
              f"Barron's AP Psychology Chapter {ch} Review Questions — {title}",
              f"巴朗 AP 心理学 Chapter {ch} 复习题 · {title}",
              SUBJECT_ID, PDF_REL, len(questions), "unit_practice", SOURCE_ID))
        con.execute("""
            INSERT INTO paper_sources (paper_id, role, path, note)
            VALUES (?,?,?,?)
        """, (paper_id, "book", PDF_REL, f"Chapter {ch} Review Questions and Answer Explanations"))

        chapter_figures = figures_by_chapter.get(ch, {})
        for q in questions:
            number = q["number"]
            qid = f"{paper_id}-{number:03d}"
            answer = q.get("correct_answer")
            answer_text = (q.get("answer_text") or "").strip() or None
            figure = chapter_figures.get(number)
            context = (q.get("context") or "").strip() or None
            if figure and context:
                stop = CONTEXT_STOPS.get(figure["key"])
                if stop:
                    cut = context.find(stop)
                    if cut >= 0:
                        context = context[:cut + len(stop)].strip()
                        if context and context[-1] not in ".!?":
                            context += "."
            con.execute("""
                INSERT INTO questions
                (question_id, paper_id, section, number, stem, context, page_start, page_end,
                 correct_answer, answer_text, subject_id, form, source_file, answer_source, answer_confidence)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,NULL,?,?,?)
            """, (qid, paper_id, "MCQ", number, q["stem"], context,
                  q["page_start"], q["page_end"], answer, answer_text,
                  SUBJECT_ID, PDF_REL,
                  "book_answer" if answer else None, "high" if answer else None))
            total_q += 1
            if answer:
                total_ans += 1
            for order, label in enumerate("ABCD"):
                content = (q["options"].get(label) or "").strip()
                explanation = answer_text if label == answer and answer_text else None
                con.execute("""
                    INSERT INTO options (question_id, label, content, sort_order, is_correct, explanation)
                    VALUES (?,?,?,?,?,?)
                """, (qid, label, content, order, 1 if label == answer else 0, explanation))
                total_opt += 1
            if figure:
                if figure["key"] not in figure_cache:
                    figure_cache[figure["key"]] = crop_figure(figure, line_rows)
                path, bbox = figure_cache[figure["key"]]
                asset_id = f"{paper_id}-q{number:03d}-fig-{figure['key']}"
                con.execute("""
                    INSERT INTO assets (asset_id, question_id, option_label, kind, path, page, bbox)
                    VALUES (?,?,NULL,?,?,?,?)
                """, (asset_id, qid, figure["kind"], path, figure["page"],
                      json.dumps(bbox, ensure_ascii=False)))
                total_assets += 1

    fk = con.execute("PRAGMA foreign_key_check").fetchall()
    if fk:
        con.rollback()
        print("foreign key issues:", fk[:5], file=sys.stderr)
        return 1
    con.commit()

    report = os.path.join(ROOT, "data", "content", "psychology", "reports", "barron_review_import_report.md")
    missing = [(c["chapter"], q["number"]) for c in payload["chapters"]
               for q in c["questions"] if not q.get("correct_answer")]
    lines = [
        "# Barron's AP Psychology 2027 章末 Review Questions 入库报告", "",
        f"- 导入时间：{NOW}", f"- 来源：`{PDF_REL}`",
        f"- 结构：15 个章节，每章 1 份 `unit_practice` 试卷", "",
        "| 项目 | 数量 |", "|---|---:|",
        f"| 章节试卷 | {len(payload['chapters'])} |",
        f"| 题目 | {total_q} |", f"| 有答案/解析 | {total_ans} |",
        f"| 选项 | {total_opt} |", f"| 题图（裁切） | {total_assets} |",
        f"| 唯一题图 | {len({fig['key'] for fig in FIGURES})} |", "",
        "## 校验", "",
        f"- `foreign_key_check`：{'通过' if not fk else fk[:3]}",
        "- 答案与解析来自本书 Answer Explanations；正确选项 `options.explanation` 同步写入",
        f"- 原书未给解析的题：{missing if missing else '无'}（这些题 `correct_answer` 也为 NULL）",
        "- 题图按题目/题组从 PDF 页面裁切，只保留对应图表/表格，不再使用整页截图",
        "- 同一图表/表格可被同组多道题引用；`assets.bbox` 保存相对来源页面的裁切范围",
        "- 选项本身都有文本；图片只用于图表、表格或示意图",
    ]
    open(report, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print(f"imported {len(payload['chapters'])} chapter papers, {total_q} questions, "
          f"{total_ans} with answers, {total_opt} options, {total_assets} figure assets "
          f"({len(figure_cache)} unique crops)")
    print(f"missing answers: {missing}")
    print(f"wrote {report}")
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
