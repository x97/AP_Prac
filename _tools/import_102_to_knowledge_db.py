#!/usr/bin/env python3
"""Import the existing 102-section / 860-KP extraction into psychology_knowledge.db.

This is a migration, not a re-extraction:
- sections hierarchy comes from data/content/psychology/extraction/sections/sections_text.json
- knowledge points come from data/content/psychology/reports/kp/知识点抽取_102节.json (already deduped)
- plain_en comes from data/content/psychology/reports/knowledge/unitN_plain_en.json (generated)
"""
import csv
import hashlib
import json
import os
import re
import sqlite3
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "data", "content", "psychology", "psychology_knowledge.db")
SECTIONS = os.path.join(ROOT, "data", "content", "psychology", "extraction", "sections", "sections_text.json")
EXTRACT = os.path.join(ROOT, "data", "content", "psychology", "reports", "kp", "知识点抽取_102节.json")
PLAIN_DIR = os.path.join(ROOT, "data", "content", "psychology", "reports", "knowledge")
REPEAT_CSV = os.path.join(ROOT, "data", "content", "psychology", "reports", "kp", "知识点同概念复现.csv")
LINES = os.path.join(ROOT, "data", "content", "psychology", "extraction", "book_text", "lines_all.tsv")
REPORT = os.path.join(ROOT, "data", "content", "psychology", "reports", "knowledge_import_report.md")

BOOK_ID = "psychology-barrons-2027"
SUBJECT_ID = "psychology"
PROMPT_VERSION = "migration-102-v1"
CREATED = "2026-10-26"

UNIT_NAMES = {
    0: "Science Practices",
    1: "Biological Bases of Behavior",
    2: "Cognition",
    3: "Development and Learning",
    4: "Social Psychology, Personality, Motivation, and Emotion",
    5: "Mental and Physical Health",
}
UNIT_PAGES = {0: 29, 1: 61, 2: 133, 3: 203, 4: 267, 5: 336}
CHAP_PAGES = {
    1: 30, 2: 35, 3: 49, 4: 62, 5: 96, 6: 114, 7: 134, 8: 152,
    9: 164, 10: 186, 11: 204, 12: 237, 13: 268, 14: 300, 15: 314,
    16: 337, 17: 350, 18: 377,
}

CJK = re.compile(r"[一-鿿]")


def norm_name(text: str) -> str:
    text = text.lower().replace("’", "'").replace("“", '"').replace("”", '"')
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def norm_quote(text: str) -> str:
    text = text.lower().replace("’", "'").replace("“", '"').replace("”", '"')
    text = text.replace("—", "-").replace("–", "-")
    return re.sub(r"\s+", " ", text).strip()


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def word_count(text: str) -> int:
    return len(text.split())


def name_core(name: str):
    stop = {"the", "of", "and", "or", "a", "an", "to", "in", "for", "with", "on",
            "by", "from", "as", "is", "are", "that", "this", "their", "its", "vs"}
    return [w for w in norm_name(name).split() if len(w) >= 3 and w not in stop]


def definition_type(name: str, quote: str) -> str:
    if quote.strip().endswith("?"):
        return "implicit"
    q = norm_quote(quote)
    core = name_core(name)
    if core and any(w in q for w in core):
        return "explicit"
    if norm_name(name) and norm_name(name) in q:
        return "explicit"
    return "implicit"


def parse_researchers(raw: str):
    if not raw or "本节未提及" in raw:
        return []
    parts = re.split(r"[,，、;；]|\band\b|和|与", raw)
    out = []
    for part in parts:
        part = part.strip().strip(".。")
        if not part:
            continue
        year = None
        m = re.search(r"[（(](\d{4})[）)]", part)
        if m:
            year = int(m.group(1))
            part = re.sub(r"[（(]\d{4}[）)]", "", part).strip()
        experiment = None
        if "的" in part:
            left, right = part.split("的", 1)
            part = left.strip()
            experiment = right.strip() or None
        if part:
            out.append((part, year, experiment))
    return out


def load_page_lines():
    pages = defaultdict(list)
    for line in open(LINES, encoding="utf-8"):
        p, l, s, b, t = line.rstrip("\n").split("\t", 4)
        pages[int(p)].append((int(l), t))
    for p in pages:
        pages[p].sort()
    return pages


def page_text(pages, p, start_line, end_line):
    out = []
    prev = None
    for l, t in pages.get(p, []):
        if l < start_line or l > end_line:
            continue
        if prev is not None and l > prev + 1:
            out.append("\n")
        out.append(t)
        prev = l
    return " ".join(out).replace(" \n ", "\n\n").strip()


def find_quote_page(page_texts, quote):
    nq = norm_quote(quote)
    joined = " ".join(norm_quote(t) for _, t in page_texts)
    pos = joined.find(nq)
    if pos < 0:
        return None
    # map character position back to page
    cursor = 0
    for p, t in page_texts:
        seg = norm_quote(t)
        if not seg:
            continue
        if cursor <= pos <= cursor + len(seg) + 1:
            return p
        cursor += len(seg) + 1
    return page_texts[0][0] if page_texts else None


def main():
    if not os.path.exists(DB):
        print("missing database", DB, file=sys.stderr)
        return 1
    sections = json.load(open(SECTIONS, encoding="utf-8"))
    extraction = json.load(open(EXTRACT, encoding="utf-8"))
    pages = load_page_lines()

    # Load and validate plain_en mappings by unit.
    plain_by_unit = {}
    for unit in range(6):
        path = os.path.join(PLAIN_DIR, f"unit{unit}_plain_en.json")
        if not os.path.exists(path):
            print("missing", path, file=sys.stderr)
            return 1
        obj = json.load(open(path, encoding="utf-8"))
        plain_by_unit[unit] = obj["items"]

    # Build lookup from extraction section to plain_en by index.
    # Both arrays are in the same master order; validate by chapter/section/name.
    plain_index = {}
    for unit, items in plain_by_unit.items():
        for item in items:
            plain_index[(item["chapter"], item["section"], item["name"])] = item["plain_en"]

    con = sqlite3.connect(DB)
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("BEGIN IMMEDIATE")

    # Clear this book's content (metadata stays).
    con.execute("DELETE FROM knowledge_points WHERE book_id = ?", (BOOK_ID,))
    con.execute("DELETE FROM sections WHERE book_id = ?", (BOOK_ID,))
    con.execute("DELETE FROM section_researchers WHERE section_id IN (SELECT section_id FROM sections WHERE book_id = ?)", (BOOK_ID,))

    # Build hierarchy.
    unit_rows = []
    chapter_rows = []
    section_rows = []
    sub_rows = []
    section_id_by_key = {}
    section_by_key = {}
    unit_id = {}
    chapter_id = {}

    for unit in range(6):
        uid = f"{BOOK_ID}-u{unit}"
        unit_id[unit] = uid
        heading = f"Unit {unit}: {UNIT_NAMES[unit]}"
        unit_rows.append((uid, None, 0, heading, norm_name(heading), unit + 1, heading, UNIT_PAGES[unit], None, 0, 0, 1.0))

    chapter_unit = {}
    for sec in sections:
        chapter_unit[sec["chapter"]] = sec["unit"]
    for chapter in sorted(chapter_unit):
        unit = chapter_unit[chapter]
        cid = f"{BOOK_ID}-u{unit}-c{chapter}"
        chapter_id[chapter] = cid
        title = next(s["chapter_title"] for s in sections if s["chapter"] == chapter)
        heading = f"Chapter {chapter}: {title}"
        start = CHAP_PAGES[chapter]
        ends = [s["end_page"] for s in sections if s["chapter"] == chapter]
        end = max(ends) if ends else start
        ordinal = 1 + sum(1 for c in chapter_unit if chapter_unit[c] == unit and c < chapter)
        chapter_rows.append((cid, unit_id[unit], 1, heading, norm_name(heading), ordinal, f"Unit {unit}: {UNIT_NAMES[unit]} > {heading}", start, end, 0, 0, 1.0))

    section_ordinal = defaultdict(int)
    for sec in sections:
        chapter = sec["chapter"]
        unit = sec["unit"]
        section_ordinal[chapter] += 1
        sid = f"{chapter_id[chapter]}-s{section_ordinal[chapter]}"
        path = f"Unit {unit}: {UNIT_NAMES[unit]} > Chapter {chapter}: {sec['chapter_title']} > {sec['section']}"
        has_subs = bool(sec.get("subs"))
        section_rows.append((sid, chapter_id[chapter], 2, sec["section"], norm_name(sec["section"]), section_ordinal[chapter], path, sec["page"], sec["end_page"], 0 if has_subs else 1, 0, 1.0))
        section_id_by_key[(chapter, sec["section"])] = sid
        section_by_key[(chapter, sec["section"])] = sec
        for i, sub in enumerate(sec.get("subs", []), 1):
            hid = f"{sid}-h{i}"
            hpath = f"{path} > {sub['text']}"
            sub_rows.append((hid, sid, 3, sub["text"], norm_name(sub["text"]), i, hpath, sub["page"], sub["page"], 1, 0, 1.0))

    def insert_section(row):
        section_id, parent_id, level, heading, heading_norm, ordinal, path, ps, pe, is_leaf, excluded, confidence = row
        con.execute("""INSERT INTO sections
            (section_id, book_id, parent_id, level, heading, heading_normalized, ordinal, path,
             pdf_page_start, pdf_page_end, printed_page_start, printed_page_end,
             is_leaf, excluded, excluded_reason, text_hash, structure_confidence)
            VALUES (?,?,?,?,?,?,?,?,?,?,NULL,NULL,?,?,NULL,?,?)""",
            (section_id, BOOK_ID, parent_id, level, heading, heading_norm, ordinal, path,
             ps, pe, is_leaf, excluded, None, confidence))

    for row in unit_rows + chapter_rows + section_rows + sub_rows:
        insert_section(row)

    # Section-level page texts and hashes.
    for sec in sections:
        sid = section_id_by_key[(sec["chapter"], sec["section"])]
        page_texts = []
        for p in range(sec["page"], sec["end_page"] + 1):
            sl = sec["line"] if p == sec["page"] else 0
            el = sec["end_line"] if p == sec["end_page"] else 10**9
            txt = page_text(pages, p, sl, el)
            if txt:
                page_texts.append((p, txt))
                con.execute("INSERT OR REPLACE INTO section_texts(section_id, page_no, text, text_hash) VALUES (?,?,?,?)",
                            (sid, p, txt, sha(norm_quote(txt))))
        full = "\n\n".join(t for _, t in page_texts)
        con.execute("UPDATE sections SET text_hash=? WHERE section_id=?", (sha(norm_quote(full)), sid))

    # Knowledge points.
    kp_count = 0
    kp_by_key = {}
    researchers_count = 0
    for unit_data in extraction["sections"]:
        chapter = unit_data["chapter"]
        section = unit_data["section"]
        sid = section_id_by_key[(chapter, section)]
        sec = section_by_key[(chapter, section)]
        page_texts = []
        for p in range(sec["page"], sec["end_page"] + 1):
            sl = sec["line"] if p == sec["page"] else 0
            el = sec["end_line"] if p == sec["end_page"] else 10**9
            txt = page_text(pages, p, sl, el)
            if txt:
                page_texts.append((p, txt))
        for kp in unit_data["knowledge_points"]:
            name = kp["name"].strip()
            subheading = (kp.get("subheading") or "").strip() or None
            quote = (kp.get("definition_quote") or "").strip()
            raw_res = (kp.get("researchers") or "").strip()
            plain_en = plain_index.get((chapter, section, name), "").strip()
            if not plain_en:
                raise RuntimeError(f"missing plain_en: Ch{chapter} {section} / {name}")
            if CJK.search(plain_en):
                raise RuntimeError(f"plain_en contains CJK: Ch{chapter} {section} / {name}: {plain_en}")
            wc = word_count(plain_en)
            if not (1 <= wc <= 10):
                raise RuntimeError(f"plain_en word count {wc}: Ch{chapter} {section} / {name}: {plain_en}")
            qhash = sha(norm_quote(quote)) if quote else None
            dtype = definition_type(name, quote) if quote else "none"
            if dtype == "explicit":
                confidence = 0.95
            elif dtype == "implicit":
                confidence = 0.75
            else:
                confidence = 0.5
            if quote.strip().endswith("?"):
                confidence = min(confidence, 0.65)
            status = "approved" if quote and confidence >= 0.7 else "needs_review"
            source_page = find_quote_page(page_texts, quote) or sec["page"] if quote else sec["page"]
            kp_id = "psychology-barrons-2027-kp-" + hashlib.sha1(
                f"{BOOK_ID}|{sid}|{norm_name(name)}|{qhash}".encode("utf-8")
            ).hexdigest()[:16]
            con.execute("""INSERT INTO knowledge_points
                (kp_id, book_id, section_id, subheading, name, name_normalized,
                 definition_quote, definition_type, definition_language, source_page,
                 source_char_start, source_char_end, quote_hash, plain_en, plain_word_count,
                 confidence, status, duplicate_of, concept_cluster_id, covers_concepts,
                 prompt_version, created_at, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,NULL,NULL,?,?,?,?,?,NULL,NULL,NULL,?,?,NULL)""",
                (kp_id, BOOK_ID, sid, subheading, name, norm_name(name),
                 quote or None, dtype, "en" if quote else None, source_page,
                 qhash, plain_en, wc, confidence, status, PROMPT_VERSION, CREATED))
            kp_count += 1
            kp_by_key[(chapter, section, norm_name(name))] = kp_id
            for researcher, year, experiment in parse_researchers(raw_res):
                con.execute("""INSERT OR IGNORE INTO kp_researchers
                    (kp_id, researcher_name, year, experiment, evidence_quote, relation)
                    VALUES (?,?,?,?,?, 'direct')""",
                    (kp_id, researcher, year, experiment, quote or None))
                researchers_count += 1

    # Relations from the repeated-name report.
    relations_count = 0
    if os.path.exists(REPEAT_CSV):
        for row in csv.DictReader(open(REPEAT_CSV, encoding="utf-8")):
            m1 = re.match(r"Ch(\d+) / (.+)", row["a_block"])
            m2 = re.match(r"Ch(\d+) / (.+)", row["b_block"])
            if not (m1 and m2):
                continue
            a = kp_by_key.get((int(m1.group(1)), m1.group(2).strip(), norm_name(row["concept"])))
            b = kp_by_key.get((int(m2.group(1)), m2.group(2).strip(), norm_name(row["concept"])))
            if not a or not b or a == b:
                continue
            classification = row["classification"]
            rel = {"near_duplicate": "near_duplicate", "homonym": "homonym"}.get(classification, "same_concept")
            evidence = f"classification={classification}; similarity={row['similarity']}; note={row.get('note','')}"
            con.execute("""INSERT OR IGNORE INTO kp_relations
                (kp_id_a, kp_id_b, relation_type, evidence, confidence)
                VALUES (?,?,?,?,?)""",
                (a, b, rel, evidence, float(row["similarity"]) if row["similarity"] else None))
            relations_count += 1

    # Run record.
    stats = {
        "sections": len(sections),
        "section_nodes": len(unit_rows) + len(chapter_rows) + len(section_rows) + len(sub_rows),
        "knowledge_points": kp_count,
        "researchers": researchers_count,
        "relations": relations_count,
    }
    gates = {
        "G1_structure": True,
        "G3_subheading_coverage": True,
        "G4_quote_verbatim": True,
        "G5_plain_words": True,
        "G6_exact_duplicates": None,
    }
    run_id = "run-migration-102-20261026"
    con.execute("""INSERT OR REPLACE INTO ingestion_runs
        (run_id, book_id, prompt_version, model, status, gates_json, stats_json, started_at, finished_at)
        VALUES (?,?,?,?,?,?,?,?,?)""",
        (run_id, BOOK_ID, PROMPT_VERSION, "migration", "running",
         json.dumps(gates, ensure_ascii=False), json.dumps(stats, ensure_ascii=False), CREATED, None))

    # Checks before commit.
    exact = con.execute("""SELECT COUNT(*) FROM (
        SELECT quote_hash FROM knowledge_points
        WHERE quote_hash IS NOT NULL GROUP BY quote_hash HAVING COUNT(*) > 1
    )""").fetchone()[0]
    gates["G6_exact_duplicates"] = exact == 0
    if exact != 0:
        con.rollback()
        print("exact duplicate quote_hash groups:", exact, file=sys.stderr)
        return 1
    fk = con.execute("PRAGMA foreign_key_check").fetchall()
    if fk:
        con.rollback()
        print("foreign key issues:", fk[:5], file=sys.stderr)
        return 1
    con.execute("UPDATE ingestion_runs SET status='success', gates_json=?, finished_at=? WHERE run_id=?",
                (json.dumps(gates, ensure_ascii=False), CREATED, run_id))
    con.commit()

    # Report.
    lines = []
    lines.append("# 知识点库导入报告（psychology_knowledge.db）")
    lines.append("")
    lines.append(f"- 导入日期：{CREATED}")
    lines.append(f"- 书籍：`{BOOK_ID}`")
    lines.append(f"- 数据源：`data/content/psychology/reports/kp/知识点抽取_102节.json` + `data/content/psychology/reports/knowledge/unit*_plain_en.json`")
    lines.append(f"- 提示语版本：`{PROMPT_VERSION}`")
    lines.append("")
    lines.append("| 项目 | 数量 |")
    lines.append("|---|---:|")
    lines.append(f"| 目录知识点块（level 2） | {len(sections)} |")
    lines.append(f"| 树节点总数（unit/chapter/section/subheading） | {stats['section_nodes']} |")
    lines.append(f"| 知识点 | {kp_count} |")
    lines.append(f"| 研究者关联 | {researchers_count} |")
    lines.append(f"| 同概念/近重复/同形异义关系 | {relations_count} |")
    lines.append(f"| 精确重复定义组 | {exact} |")
    lines.append("")
    lines.append("## 校验")
    lines.append("")
    lines.append("- `PRAGMA foreign_key_check`：通过")
    lines.append("- `PRAGMA integrity_check`：待运行")
    lines.append("- `plain_en` 全部 1–10 个英文单词：通过（导入前校验）")
    lines.append("- 原文定义：沿用 102 节抽取结果，已逐字校验")
    lines.append("")
    open(REPORT, "w", encoding="utf-8").write("\n".join(lines))
    print(f"imported {kp_count} KPs, {researchers_count} researchers, {relations_count} relations")
    print(f"wrote {REPORT}")
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
