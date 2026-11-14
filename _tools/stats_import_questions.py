#!/usr/bin/env python3
"""Import Barron's AP Statistics 2027 practice questions into psychology_exam.db."""
import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SUBJECT_DIR = os.path.join(ROOT, "data", "content", "statistics")
DB = os.path.join(SUBJECT_DIR, "statistics_exam.db")
EXTRACT = os.path.join(ROOT, "data", "content", "statistics", "extraction")
DATA = os.path.join(EXTRACT, "questions_all.json")
PDF_REL = "assets/statistics/books/AP Statistics Premium, 2027 - Martin Sternstein.pdf"
PDF_ABS = os.path.join(ROOT, PDF_REL)
ASSET_DIR = os.path.join(ROOT, "assets", "statistics", "images", "stats2027")
REPORT = os.path.join(EXTRACT, "reports", "question_import_report.md")

BOOK_ID = "statistics-barrons-2027"
SUBJECT_ID = "statistics"
SOURCE_ID = "statistics-barrons-2027"
NOW = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
PAGE_W, PAGE_H = 612.0, 792.0


def load_fitz():
    try:
        import fitz
    except ImportError:
        import sys
        sys.path.append("/Users/aa/Library/Python/3.9/lib/python/site-packages")
        import fitz
    return fitz


def clean(s):
    s = s or ""
    s = s.replace(" ", " ").replace("﻿", "")
    s = s.replace("’", "'").replace("‘", "'")
    s = s.replace("“", '"').replace("”", '"')
    s = s.replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", s).strip()


def norm(s):
    return re.sub(r"\s+", " ", clean(s).lower())


def fingerprint(stem, options=None):
    text = norm(stem)
    if options:
        text += "|" + norm(" ".join(f"{k}:{v}" for k, v in sorted(options.items())))
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def trim_asset(path):
    try:
        from PIL import Image, ImageChops
        im = Image.open(path).convert("RGB")
        bg = Image.new("RGB", im.size, (255, 255, 255))
        box = ImageChops.difference(im, bg).getbbox()
        if not box:
            os.remove(path)
            return False
        if box != (0, 0, im.width, im.height):
            im.crop(box).save(path)
        return True
    except Exception:
        return os.path.exists(path) and os.path.getsize(path) > 100


def crop(doc, page_no, bbox, out_path, pad=3.0, scale=2.0):
    import fitz
    page = doc[page_no - 1]
    x0, y0, x1, y1 = bbox
    x0 = max(0.0, x0 - pad)
    y0 = max(0.0, y0 - pad)
    x1 = min(PAGE_W, x1 + pad)
    y1 = min(PAGE_H, y1 + pad)
    if x1 - x0 < 3 or y1 - y0 < 3:
        return None
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale),
                          clip=fitz.Rect(x0, y0, x1, y1), alpha=False)
    pix.save(out_path)
    if not trim_asset(out_path):
        return None
    return [round(x0 / PAGE_W, 4), round(y0 / PAGE_H, 4),
            round(x1 / PAGE_W, 4), round(y1 / PAGE_H, 4)]


def cached_path(out, asset_cache):
    """Return a content-hashed path so shared figures reuse one file."""
    import hashlib
    h = hashlib.sha1(open(out, "rb").read()).hexdigest()
    if h in asset_cache:
        if os.path.exists(out):
            os.remove(out)
        return asset_cache[h]
    base, ext = os.path.splitext(out)
    final = os.path.join(os.path.dirname(out), "sha1-" + h[:16] + ext)
    if os.path.exists(out) and out != final:
        os.replace(out, final)
    asset_cache[h] = final
    return final


def ensure_subject(con):
    con.execute("""
        INSERT OR IGNORE INTO subjects (subject_id, name, name_zh)
        VALUES (?,?,?)
    """, (SUBJECT_ID, "AP Statistics", "AP 统计学"))


def delete_existing(con):
    paper_ids = [r[0] for r in con.execute(
        "SELECT paper_id FROM papers WHERE subject_id=?", (SUBJECT_ID,))]
    if not paper_ids:
        return
    marks = ",".join("?" for _ in paper_ids)
    qids = [r[0] for r in con.execute(
        f"SELECT question_id FROM questions WHERE paper_id IN ({marks})", paper_ids)]
    if qids:
        qm = ",".join("?" for _ in qids)
        con.execute(f"DELETE FROM assets WHERE question_id IN ({qm})", qids)
        con.execute(f"DELETE FROM options WHERE question_id IN ({qm})", qids)
        con.execute(f"DELETE FROM frq_rubrics WHERE question_id IN ({qm})", qids)
        con.execute(f"DELETE FROM question_sources WHERE question_id IN ({qm})", qids)
        con.execute(f"DELETE FROM questions WHERE question_id IN ({qm})", qids)
    con.execute(f"DELETE FROM paper_sources WHERE paper_id IN ({marks})", paper_ids)
    con.execute(f"DELETE FROM paper_book_sources WHERE paper_id IN ({marks})", paper_ids)
    con.execute(f"DELETE FROM papers WHERE paper_id IN ({marks})", paper_ids)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=DB)
    ap.add_argument("--no-backup", action="store_true")
    args = ap.parse_args()
    fitz = load_fitz()
    doc = fitz.open(PDF_ABS)
    payload = json.load(open(DATA, encoding="utf-8"))

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    if not args.no_backup:
        backup = args.db + f".bak-{stamp}-before-stats-questions"
        shutil.copy2(args.db, backup)
        print("backup:", backup)

    if os.path.isdir(ASSET_DIR):
        shutil.rmtree(ASSET_DIR)
    os.makedirs(ASSET_DIR, exist_ok=True)
    asset_cache = {}

    con = sqlite3.connect(args.db)
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("BEGIN IMMEDIATE")
    try:
        ensure_subject(con)
        con.execute("""
            INSERT OR REPLACE INTO content_sources
            (source_id, kind, title, chinese_title, edition, target_year,
             file_path, imported_at, subject_id, book_id)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (SOURCE_ID, "review_book", "Barron's AP Statistics Premium, 2027",
              "巴朗 AP 统计学 2027", "2027", 2027, PDF_REL, NOW,
              SUBJECT_ID, BOOK_ID))
        delete_existing(con)

        total_q = total_opts = total_assets = 0
        missing_mcq = []
        missing_frq = []
        no_text_expl = []
        missing_choices = []
        for paper in payload["papers"]:
            pid = paper["paper_id"]
            ptype = "unit_practice" if paper["kind"] == "quiz" else "mock_exam"
            con.execute("""
                INSERT INTO papers
                (paper_id, year, title, chinese_title, subject_id, source_pdf,
                 question_count, paper_type, source_id)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (pid, 2027, paper["title"], paper["chinese_title"],
                  SUBJECT_ID, PDF_REL, len(paper["questions"]), ptype, SOURCE_ID))
            con.execute("""
                INSERT INTO paper_sources (paper_id, role, path, note)
                VALUES (?,?,?,?)
            """, (pid, "book", PDF_REL,
                  f"{paper['kind']} pages {paper['pdf_page_start']}-{paper['pdf_page_end']}"))
            con.execute("""
                INSERT INTO paper_book_sources (paper_id, book_id, role, note)
                VALUES (?,?,?,?)
            """, (pid, BOOK_ID, "main", "derived from book quiz/test"))

            for q in paper["questions"]:
                qid = q["question_id"]
                options = q.get("options", {})
                correct = q.get("correct_answer")
                answer_text = q.get("answer_text") or None
                if q["section"] == "MCQ" and not correct:
                    missing_mcq.append((pid, q["number"]))
                if q["section"] == "FRQ" and not answer_text:
                    missing_frq.append((pid, q["number"]))
                if q["section"] == "MCQ" and correct and not answer_text:
                    no_text_expl.append((pid, q["number"]))
                con.execute("""
                    INSERT INTO questions
                    (question_id, paper_id, section, number, stem, context,
                     page_start, page_end, correct_answer, answer_text,
                     subject_id, form, source_file, answer_source,
                     answer_confidence, question_fingerprint)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (qid, pid, q["section"], q["number"], q["stem"],
                      q.get("context") or None, q["page_start"], q["page_end"],
                      correct, answer_text, SUBJECT_ID,
                      f"Quiz {paper['number']}" if paper["kind"] == "quiz"
                      else ("Diagnostic Test" if paper["kind"] == "diagnostic"
                            else f"Practice Test {paper['number']}"),
                      PDF_REL,
                      "book_answer" if (correct or answer_text) else None,
                      "high" if (correct or answer_text) else None,
                      fingerprint(q["stem"], options if options else None)))
                total_q += 1

                if q["section"] == "MCQ":
                    for order, label in enumerate("ABCD"):
                        content = (options.get(label) or "").strip()
                        if not content:
                            content = "[source missing choices]"
                            missing_choices.append((pid, q["number"], label))
                        explanation = answer_text if label == correct else None
                        con.execute("""
                            INSERT INTO options
                            (question_id, label, content, sort_order, is_correct, explanation)
                            VALUES (?,?,?,?,?,?)
                        """, (qid, label, content, order,
                              1 if label == correct else 0, explanation))
                        total_opts += 1

                # Option images / vector option crops.
                for label, imgs in (q.get("option_images") or {}).items():
                    for k, im in enumerate(imgs, 1):
                        out = os.path.join(ASSET_DIR, pid,
                                           f"{qid}-opt-{label}-{k}.png")
                        os.makedirs(os.path.dirname(out), exist_ok=True)
                        rel_bbox = crop(doc, im["page"], im["bbox"], out)
                        if not rel_bbox:
                            continue
                        final = cached_path(out, asset_cache)
                        con.execute("""
                            INSERT INTO assets
                            (asset_id, question_id, option_label, kind, path, page, bbox)
                            VALUES (?,?,?,?,?,?,?)
                        """, (f"{qid}-opt-{label}-{k}", qid, label, "option",
                              os.path.relpath(final, ROOT), im["page"],
                              json.dumps(rel_bbox)))
                        total_assets += 1
                for label, spec in (q.get("option_crops") or {}).items():
                    out = os.path.join(ASSET_DIR, pid,
                                       f"{qid}-opt-{label}-crop.png")
                    os.makedirs(os.path.dirname(out), exist_ok=True)
                    rel_bbox = crop(doc, spec["page"], spec["bbox"], out)
                    if not rel_bbox:
                        continue
                    final = cached_path(out, asset_cache)
                    con.execute("""
                        INSERT INTO assets
                        (asset_id, question_id, option_label, kind, path, page, bbox)
                        VALUES (?,?,?,?,?,?,?)
                    """, (f"{qid}-opt-{label}-crop", qid, label, "option",
                          os.path.relpath(final, ROOT), spec["page"],
                          json.dumps(rel_bbox)))
                    total_assets += 1

                # Figures.
                for k, im in enumerate(q.get("figure_images") or [], 1):
                    out = os.path.join(ASSET_DIR, pid,
                                       f"{qid}-fig-{k}.png")
                    os.makedirs(os.path.dirname(out), exist_ok=True)
                    rel_bbox = crop(doc, im["page"], im["bbox"], out)
                    if not rel_bbox:
                        continue
                    final = cached_path(out, asset_cache)
                    con.execute("""
                        INSERT INTO assets
                        (asset_id, question_id, option_label, kind, path, page, bbox)
                        VALUES (?,?,NULL,?,?,?,?)
                    """, (f"{qid}-fig-{k}", qid, "figure",
                          os.path.relpath(final, ROOT), im["page"],
                          json.dumps(rel_bbox)))
                    total_assets += 1

                con.execute("""
                    INSERT INTO question_sources
                    (question_id, book_id, section_id, page_start, page_end,
                     figure_ref, role, note)
                    VALUES (?,?,NULL,?,?,NULL,'question',?)
                """, (qid, BOOK_ID, q["page_start"], q["page_end"],
                      f"{paper['kind']} question"))

        fk = con.execute("PRAGMA foreign_key_check").fetchall()
        if fk:
            con.rollback()
            raise SystemExit(f"foreign key issues: {fk[:5]}")
        con.commit()
    except Exception:
        con.rollback()
        raise

    integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
    paper_count = con.execute(
        "SELECT COUNT(*) FROM papers WHERE subject_id=?", (SUBJECT_ID,)).fetchone()[0]
    q_count = con.execute(
        "SELECT COUNT(*) FROM questions WHERE subject_id=?", (SUBJECT_ID,)).fetchone()[0]
    # Note: psychology_exam.db subject table has no subject_id on questions? It does.
    opt_count = con.execute("""
        SELECT COUNT(*) FROM options o JOIN questions q ON o.question_id=q.question_id
        WHERE q.subject_id=?
    """, (SUBJECT_ID,)).fetchone()[0]

    lines = ["# Barron's AP Statistics 2027 题目入库报告", "",
             f"- 入库时间：{NOW}", f"- 来源：`{PDF_REL}`",
             f"- 试卷：{paper_count}；题目：{q_count}；选项：{opt_count}；题图素材：{total_assets}", "",
             "| 项目 | 数量 |", "|---|---:|",
             f"| 试卷 | {paper_count} |",
             f"| 题目 | {q_count} |",
             f"| 选项 | {opt_count} |",
             f"| 素材（裁切） | {total_assets} |", "",
             "## 缺答案 / 待复核", "",
             f"- 缺答案 MCQ：{missing_mcq if missing_mcq else '无'}",
             f"- 有答案但原书无文字解析（公式/图片）：{no_text_expl if no_text_expl else '无'}",
             f"- 缺解析 FRQ：{missing_frq if missing_frq else '无'}",
             f"- 源文件选项缺失：{missing_choices if missing_choices else '无'}",
             "",
             "## 校验", "",
             f"- `foreign_key_check`：通过",
             f"- `integrity_check`：{integrity}",
             "- 答案与解析来自本书 Answer Explanations；MCQ 正确选项同步写入 `options.explanation`。",
             "- 题图/公式图按题目或选项从来源页面裁切，不使用整页截图。",
             "- 教材练习卷 `paper_type='unit_practice'`；诊断卷与 4 套模拟卷 `paper_type='mock_exam'`。",
             "- FRQ 仅保存题干与模型解答，原书没有正式评分点表的部分不伪造 `frq_rubrics`。"]
    open(REPORT, "w", encoding="utf-8").write("\n".join(lines) + "\n")

    print(f"papers={paper_count} questions={q_count} options={opt_count} assets={total_assets} integrity={integrity}")
    print(f"missing_mcq={missing_mcq}")
    print(f"missing_frq={missing_frq}")
    print(f"missing_choices={len(missing_choices)}")
    print("wrote", REPORT)
    con.close()


if __name__ == "__main__":
    main()
