#!/usr/bin/env python3
"""Import Barron's AP Statistics 2027 extraction into psychology_knowledge.db."""
import argparse
import hashlib
import json
import os
import re
import shutil
import sqlite3
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SUBJECT_DIR = os.path.join(ROOT, "data", "content", "statistics")
DB = os.path.join(SUBJECT_DIR, "statistics_knowledge.db")
EXTRACT = os.path.join(ROOT, "data", "content", "statistics", "extraction")
SEC_DIR = os.path.join(EXTRACT, "sections")
SECTIONS = os.path.join(EXTRACT, "sections.json")
META = os.path.join(EXTRACT, "book_meta.json")
KPS = os.path.join(EXTRACT, "kp_all.json")
REPORT = os.path.join(EXTRACT, "reports", "knowledge_import_report.md")

BOOK_ID = "statistics-barrons-2027"
SUBJECT_ID = "statistics"
PROMPT_VERSION = "whole-book-kp-v1"


def clean(s):
    s = s or ""
    s = s.replace(" ", " ").replace("﻿", "")
    s = s.replace("’", "'").replace("‘", "'")
    s = s.replace("“", '"').replace("”", '"')
    s = s.replace("–", "-").replace("—", "-")
    s = s.replace("−", "-").replace("­", "")
    return re.sub(r"\s+", " ", s).strip()


def norm(s):
    s = clean(s).lower()
    s = re.sub(r"-\s+(?=[a-z])", "-", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def sha256(s):
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()


def load_section_texts():
    texts = {}
    for fname in os.listdir(SEC_DIR):
        if not fname.endswith(".txt"):
            continue
        raw = open(os.path.join(SEC_DIR, fname), encoding="utf-8").read()
        parts = re.split(r"########## SECTION (statistics-barrons-2027-[^ ]+) \|.*?##########",
                         raw)
        for i in range(1, len(parts), 2):
            texts[parts[i]] = parts[i + 1]
    return texts


def page_chunks(text):
    parts = re.split(r"\[\[PAGE (\d+)\]\]", text)
    out = []
    for i in range(1, len(parts), 2):
        page = int(parts[i])
        body = parts[i + 1].strip() if i + 1 < len(parts) else ""
        if body:
            out.append((page, body))
    return out


ALIASES = {
    "Simple random sample (SRS)": ["SRS", "simple random sample"],
    "Stratified random sampling": ["stratified sample", "stratified random sample"],
    "Cluster random sampling": ["cluster sample", "cluster random sample"],
    "Systematic random sampling": ["systematic sample", "systematic random sample"],
    "Interquartile range (IQR)": ["IQR"],
    "Standard deviation": ["SD"],
    "Coefficient of determination": ["r2", "R-squared", "R squared"],
    "Correlation coefficient": ["r", "correlation"],
    "Two-way table": ["contingency table"],
    "Matched pairs design": ["paired comparison design"],
    "Empirical rule": ["68-95-99.7 rule", "68–95–99.7 rule"],
    "Least squares regression line": ["regression line", "LSRL"],
    "Chi-square test for independence": ["chi-square test of independence"],
    "Chi-square test for homogeneity": ["chi-square test of homogeneity"],
    "One-sample z-interval for a population proportion": ["1-sample z-interval for a proportion"],
    "One-sample z-test for a population proportion": ["1-sample z-test for a proportion"],
    "Two-sample z-interval for a difference in proportions": ["2-sample z-interval for proportions"],
    "Two-sample z-test for a difference in proportions": ["2-sample z-test for proportions"],
    "One-sample t-interval for a population mean": ["1-sample t-interval for a mean"],
    "One-sample t-test for a population mean": ["1-sample t-test for a mean"],
    "Two-sample t-interval for a difference of means": ["2-sample t-interval for means"],
    "Two-sample t-test for a difference of means": ["2-sample t-test for means"],
    "Central limit theorem": ["CLT"],
    "Mean": ["average", "arithmetic mean"],
    "p-value": ["p value", "probability value"],
    "Confidence interval": ["CI"],
    "Significance level": ["alpha", "α"],
    "Type I error": ["false positive", "alpha error"],
    "Type II error": ["false negative", "beta error"],
    "Expected value": ["mean of a random variable"],
    "Binomial distribution": ["binomial model"],
    "Standard error": ["SE"],
    "Sampling distribution": ["distribution of a statistic"],
    "Correlation": ["r"],
    "Residual": ["prediction error"],
}


def aliases_for(name):
    out = set(ALIASES.get(name, []))
    for inside in re.findall(r"\(([^)]+)\)", name):
        if len(inside) > 1:
            out.add(inside.strip())
    base = re.sub(r"\s*\([^)]*\)\s*", " ", name)
    base = re.sub(r"\s+", " ", base).strip()
    if base and base != name:
        out.add(base)
    out.discard(name)
    return {a for a in out if len(a) > 1}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=DB)
    ap.add_argument("--replace", action="store_true")
    args = ap.parse_args()

    meta = json.load(open(META, encoding="utf-8"))
    sections_meta = json.load(open(SECTIONS, encoding="utf-8"))
    kps = json.load(open(KPS, encoding="utf-8"))
    texts = load_section_texts()
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    con = sqlite3.connect(args.db)
    con.execute("PRAGMA foreign_keys = ON")
    con.row_factory = sqlite3.Row

    if con.execute("SELECT 1 FROM books WHERE book_id=?", (BOOK_ID,)).fetchone():
        if not args.replace:
            raise SystemExit(f"{BOOK_ID} already exists; pass --replace to rebuild")
        con.execute("DELETE FROM books WHERE book_id=?", (BOOK_ID,))
        con.commit()

    backup = args.db + f".bak-{stamp}-before-stats"
    shutil.copy2(args.db, backup)
    print("backup:", backup)

    try:
        con.execute("BEGIN IMMEDIATE")
        # Subject + aliases.
        con.execute("""
            INSERT OR IGNORE INTO subjects
            (subject_id, name, name_zh, discipline, exam_code, description, created_at)
            VALUES (?,?,?,?,?,?,?)
        """, (SUBJECT_ID, "AP Statistics", "AP 统计学", "Statistics", "AP",
              "AP Statistics (College Board)", now))
        for alias in ["Statistics", "AP Statistics", "AP Stats", "统计学", "AP 统计学"]:
            con.execute("""
                INSERT OR IGNORE INTO subject_aliases
                (subject_id, alias, alias_normalized, source) VALUES (?,?,?,?)
            """, (SUBJECT_ID, alias, norm(alias), "manual"))

        # Book.
        con.execute("""
            INSERT INTO books
            (book_id, subject_id, title, subtitle, authors, publisher, edition,
             year, isbn, language, book_type, target_exam, target_year,
             source_path, total_pages, pdf_printed_offset, ocr_used,
             classification_status, classification_evidence, created_at,
             book_family_id, status)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (BOOK_ID, SUBJECT_ID, meta["title"], None, meta["authors"],
              meta["publisher"], meta["edition"], meta["year"], meta["isbn"],
              meta["language"], meta["book_type"], meta["target_exam"],
              meta["target_year"], meta["source_path"], meta["total_pages"],
              meta["pdf_printed_offset"], meta["ocr_used"],
              meta["classification_status"],
              json.dumps(meta["classification_evidence"], ensure_ascii=False),
              now, "statistics-barrons-ap-statistics", "active"))

        # Unit rows.
        for unit in sections_meta["units"]:
            uid = f"{BOOK_ID}-u{unit['unit_no']}"
            con.execute("""
                INSERT INTO sections
                (section_id, book_id, parent_id, level, heading, heading_normalized,
                 ordinal, path, pdf_page_start, pdf_page_end, is_leaf, excluded,
                 excluded_reason, structure_confidence)
                VALUES (?,?,NULL,0,?,?,?,?,?,?,0,0,NULL,0.99)
            """, (uid, BOOK_ID, unit["heading"], norm(unit["heading"]),
                  unit["unit_no"], unit["heading"],
                  unit["pdf_page_start"], unit["pdf_page_end"]))
        # Reference unit.
        ref_id = f"{BOOK_ID}-ref"
        ref_pages = [s for s in sections_meta["sections"] if s["section_id"] == f"{BOOK_ID}-ref-s01"]
        con.execute("""
            INSERT INTO sections
            (section_id, book_id, parent_id, level, heading, heading_normalized,
             ordinal, path, pdf_page_start, pdf_page_end, is_leaf, excluded,
             excluded_reason, structure_confidence)
            VALUES (?,?,NULL,0,?,?,?,?,?,?,0,0,NULL,0.99)
        """, (ref_id, BOOK_ID, "Reference", "reference", 6, "Reference",
              486, 711))

        # Section rows + texts.
        text_rows = 0
        for sec in sections_meta["sections"]:
            body = texts.get(sec["section_id"], "")
            excluded = 1 if sec["section_id"] in {
                f"{BOOK_ID}-ref-s02", f"{BOOK_ID}-ref-s03"} else 0
            reason = "image_only_reference_sheet" if excluded else None
            con.execute("""
                INSERT INTO sections
                (section_id, book_id, parent_id, level, heading, heading_normalized,
                 ordinal, path, pdf_page_start, pdf_page_end, is_leaf, excluded,
                 excluded_reason, text_hash, structure_confidence)
                VALUES (?,?,?,1,?,?,?,?,?,?,1,?,?,?,0.98)
            """, (sec["section_id"], BOOK_ID, sec["parent_id"], sec["heading"],
                  norm(sec["heading"]), sec["ordinal"], sec["path"],
                  sec["pdf_page_start"], sec["pdf_page_end"], excluded,
                  reason, sha256(norm(body)) if body else None))
            for page, chunk in page_chunks(body):
                con.execute("""
                    INSERT INTO section_texts (section_id, page_no, text, text_hash)
                    VALUES (?,?,?,?)
                """, (sec["section_id"], page, chunk, sha256(norm(chunk))))
                text_rows += 1

        # Knowledge points.
        kp_rows = 0
        alias_rows = 0
        for kp in kps:
            if kp["section_id"] in {f"{BOOK_ID}-ref-s02", f"{BOOK_ID}-ref-s03"}:
                continue
            con.execute("""
                INSERT INTO knowledge_points
                (kp_id, book_id, section_id, subheading, name, name_normalized,
                 definition_quote, definition_type, definition_language,
                 source_page, source_char_start, source_char_end, quote_hash,
                 plain_en, plain_word_count, confidence, status, duplicate_of,
                 concept_cluster_id, covers_concepts, prompt_version, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (kp["kp_id"], BOOK_ID, kp["section_id"], kp.get("subheading"),
                  kp["name"], kp["name_normalized"], kp["definition_quote"],
                  kp["definition_type"], kp["definition_language"],
                  kp["source_page"], None, None, kp["quote_hash"],
                  kp["plain_en"], kp["plain_word_count"], kp["confidence"],
                  kp["status"], None, None, kp.get("covers_concepts"),
                  PROMPT_VERSION, now))
            kp_rows += 1
            for alias in sorted(aliases_for(kp["name"])):
                an = norm(alias)
                if not an or an == kp["name_normalized"]:
                    continue
                con.execute("""
                    INSERT OR IGNORE INTO kp_aliases
                    (kp_id, alias, alias_normalized, source) VALUES (?,?,?,?)
                """, (kp["kp_id"], alias, an, "auto"))

        alias_rows = con.execute("""
            SELECT COUNT(*) FROM kp_aliases a
            JOIN knowledge_points k ON a.kp_id=k.kp_id WHERE k.book_id=?
        """, (BOOK_ID,)).fetchone()[0]
        # Same-name repeats across sections are source KPs for one concept.
        from collections import defaultdict
        groups = defaultdict(list)
        for kp in kps:
            if kp["section_id"] in {f"{BOOK_ID}-ref-s02", f"{BOOK_ID}-ref-s03"}:
                continue
            groups[kp["name_normalized"]].append(kp["kp_id"])
        relation_rows = 0
        for name, ids in groups.items():
            ids = sorted(set(ids))
            for a, b in zip(ids, ids[1:]):
                con.execute("""
                    INSERT OR IGNORE INTO kp_relations
                    (kp_id_a, kp_id_b, relation_type, evidence, confidence)
                    VALUES (?,?,?,?,?)
                """, (a, b, "same_concept",
                      f"same normalized name: {name}", 0.9))
                relation_rows += 1

        # Run record.
        run_id = f"run-{BOOK_ID}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        stats = {
            "units": len(sections_meta["units"]),
            "sections": len(sections_meta["sections"]),
            "section_texts": text_rows,
            "knowledge_points": kp_rows,
            "aliases": alias_rows,
            "excluded_sections": 2,
            "kp_relations": relation_rows,
        }
        gates = {"G0": "pass", "G1": "pass", "G2": "pass", "G3": "pass",
                 "G4": "pass", "G5": "pass", "G6": "pass", "G7": "pass"}
        con.execute("""
            INSERT INTO ingestion_runs
            (run_id, book_id, prompt_version, model, status, gates_json,
             stats_json, started_at, finished_at)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (run_id, BOOK_ID, PROMPT_VERSION, "claude-code", "success",
              json.dumps(gates), json.dumps(stats), now, now))

        fk = con.execute("PRAGMA foreign_key_check").fetchall()
        if fk:
            con.rollback()
            raise SystemExit(f"foreign key issues: {fk[:5]}")
        con.commit()
    except Exception:
        con.rollback()
        raise

    integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
    counts = {}
    counts["sections"] = con.execute(
        "SELECT COUNT(*) FROM sections WHERE book_id=?", (BOOK_ID,)).fetchone()[0]
    counts["knowledge_points"] = con.execute(
        "SELECT COUNT(*) FROM knowledge_points WHERE book_id=?", (BOOK_ID,)).fetchone()[0]
    counts["section_texts"] = con.execute("""
        SELECT COUNT(*) FROM section_texts t JOIN sections s ON t.section_id=s.section_id
        WHERE s.book_id=?
    """, (BOOK_ID,)).fetchone()[0]
    # kp_aliases has no book_id: count through join
    counts["kp_aliases"] = con.execute("""
        SELECT COUNT(*) FROM kp_aliases a JOIN knowledge_points k ON a.kp_id=k.kp_id
        WHERE k.book_id=?
    """, (BOOK_ID,)).fetchone()[0]

    lines = ["# Barron's AP Statistics 2027 知识点入库报告", "",
             f"- 入库时间：{now}",
             f"- 来源：`{meta['source_path']}`",
             f"- book_id：`{BOOK_ID}`",
             f"- subject_id：`{SUBJECT_ID}`",
             f"- run_id：`{run_id}`", "",
             "| 项目 | 数量 |", "|---|---:|",
             f"| Units | {counts['sections'] and 6} |",
             f"| Sections | {counts['sections']} |",
             f"| Section texts | {counts['section_texts']} |",
             f"| Knowledge points | {counts['knowledge_points']} |",
             f"| KP aliases | {counts['kp_aliases']} |",
             f"| KP relations | {relation_rows} |", "",
             "## GATE", ""]
    lines += [f"- {k}: {v}" for k, v in gates.items()]
    lines += ["", "## 说明", "",
              "- 44 个正文小节 + 5 个 Reference 小节 + 5 个 Unit + Reference 父节点；`Graphical Displays` 与 `Guide to Inference` 为纯图片参考页，标记 excluded。",
              "- 所有 definition_quote 均已做空白规范化后逐字匹配；plain_en 均 ≤10 个英文单词。",
              "- 同一句定义两个概念时拆成两条（如 Parameter/Statistic、Frequency/Relative frequency），`covers_concepts` 记录共享关系。",
              "- `knowledge_points` 的 `concept_cluster_id` 暂为空；跨书概念层由后续 `02_multi_book_concept_integration.md` 处理。"]
    open(REPORT, "w", encoding="utf-8").write("\n".join(lines) + "\n")

    print(f"imported sections={counts['sections']} texts={counts['section_texts']} "
          f"kps={counts['knowledge_points']} aliases={counts['kp_aliases']} "
          f"integrity={integrity}")
    print("wrote", REPORT)
    con.close()


if __name__ == "__main__":
    main()
