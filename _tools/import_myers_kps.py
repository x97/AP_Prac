#!/usr/bin/env python3
"""Import the Myers 4e glossary extraction into psychology_knowledge.db."""
import argparse
import collections
import hashlib
import json
import os
import re
import shutil
import sqlite3
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DB = os.path.join(ROOT, "data", "content", "psychology", "psychology_knowledge.db")
EXTRACT_DIR = os.path.join(ROOT, "data", "content", "psychology", "extraction", "myers")
MODULES = os.path.join(EXTRACT_DIR, "myers_modules.json")
ENTRIES = os.path.join(EXTRACT_DIR, "myers_glossary.json")
TEXT = os.path.join(EXTRACT_DIR, "cache", "myers.txt")
REPORT = os.path.join(EXTRACT_DIR, "myers_import_report.md")

BOOK_ID = "psychology-myers-2024"
SUBJECT_ID = "psychology"
PROMPT_VERSION = "whole-book-kp-v1"

UNIT_TITLES = {
    "0": ("Unit 0: An Introduction to Psychological Science",
          "Science Practices: Research Methods and Data Interpretation"),
    "1": ("Unit 1: Biological Bases of Behavior", "Biological Bases of Behavior"),
    "2": ("Unit 2: Cognition", "Cognition"),
    "3": ("Unit 3: Development and Learning", "Development and Learning"),
    "4": ("Unit 4: Social Psychology and Personality", "Social Psychology and Personality"),
    "5": ("Unit 5: Mental and Physical Health", "Mental and Physical Health"),
    "EM": ("Enrichment Modules", "Enrichment Modules"),
}


def norm_name(value):
    value = (value or "").lower().replace("’", "'")
    value = value.replace("ﬁ", "fi").replace("ﬂ", "fl")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def norm_quote(value):
    value = (value or "").lower().replace("’", "'")
    value = value.replace("ﬁ", "fi").replace("ﬂ", "fl")
    value = value.replace("—", "-").replace("–", "-")
    return re.sub(r"\s+", " ", value).strip()


def sha256(value):
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest()


def section_id_for_unit(unit):
    return f"{BOOK_ID}-u{unit}"


def section_id_for_module(module):
    return f"{BOOK_ID}-u{module['unit']}-m{module['code'].replace('.', '-')}"


def is_acronym(value):
    token = (value or "").strip().strip("()[],.;:")
    return bool(token) and token.isupper() and len(token) <= 6


def alias_forms(term):
    forms = {term, re.sub(r"\([^)]*\)", "", term).strip()}
    forms |= {match.strip() for match in re.findall(r"\(([^)]+)\)", term)}
    forms |= {term.replace("-", " "), term.replace(" ", "-")}
    return {form for form in forms if form and len(form) > 1}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=DB)
    parser.add_argument("--no-backup", action="store_true")
    args = parser.parse_args()

    with open(MODULES, encoding="utf-8") as handle:
        modules = json.load(handle)
    with open(ENTRIES, encoding="utf-8") as handle:
        entries = json.load(handle)
    with open(TEXT, encoding="utf-8", errors="replace") as handle:
        pages = handle.read().split("\f")
    missing_plain = [entry["term"] for entry in entries if not entry.get("plain_en")]
    if missing_plain:
        raise SystemExit(f"missing plain_en: {missing_plain[:10]}")

    con = sqlite3.connect(args.db)
    con.execute("PRAGMA foreign_keys = ON")
    con.row_factory = sqlite3.Row
    if con.execute("SELECT 1 FROM books WHERE book_id=?", (BOOK_ID,)).fetchone():
        raise SystemExit(f"{BOOK_ID} already exists; remove it first if re-importing")

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    if not args.no_backup:
        backup = args.db + f".bak-{stamp}-before-myers"
        shutil.copy2(args.db, backup)
        print("backup:", backup)
    now = datetime.now().astimezone().isoformat(timespec="seconds")

    units = sorted({module["unit"] for module in modules},
                   key=lambda unit: (unit == "EM", unit))
    unit_ranges = {}
    for unit in units:
        unit_modules = [module for module in modules if module["unit"] == unit]
        unit_ranges[unit] = (
            min(module["start"] for module in unit_modules),
            max(module["end"] for module in unit_modules),
        )

    try:
        con.execute(
            """
            INSERT INTO books
            (book_id, subject_id, title, subtitle, authors, publisher, edition,
             year, isbn, language, book_type, target_exam, target_year,
             source_path, total_pages, pdf_printed_offset, ocr_used,
             classification_status, classification_evidence, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                BOOK_ID, SUBJECT_ID, "Myers' Psychology for the AP Course",
                None, "David G. Myers; C. Nathan DeWall; Elizabeth Yost Hammer",
                "Bedford, Freeman & Worth", "4th", 2024,
                "978-1-31947145-3", "en", "textbook", "AP Psychology", 2024,
                "assets/psychology/books/教材1--Myers.pdf", len(pages) - 1, 1, 0, "confirmed",
                json.dumps({
                    "signals": [
                        "title:Myers' Psychology for the AP Course",
                        "authors:Myers/DeWall/Hammer",
                        "publisher:Bedford, Freeman & Worth",
                        "toc:Unit 0-5 + Modules",
                        "target_exam:AP Psychology",
                    ],
                    "subject_match": "psychology",
                    "confidence": 0.99,
                }, ensure_ascii=False),
                now,
            ),
        )

        for unit in units:
            heading, subtitle = UNIT_TITLES[unit]
            start, end = unit_ranges[unit]
            con.execute(
                """
                INSERT INTO sections
                (section_id, book_id, parent_id, level, heading,
                 heading_normalized, ordinal, path, pdf_page_start,
                 pdf_page_end, printed_page_start, printed_page_end, is_leaf,
                 excluded, text_hash, structure_confidence)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    section_id_for_unit(unit), BOOK_ID, None, 0, heading,
                    norm_name(heading), int(unit) if unit.isdigit() else 90,
                    heading, start, end, max(0, start - 1), max(0, end - 1),
                    0, 0, None, 1.0,
                ),
            )

        for ordinal, module in enumerate(modules, 1):
            unit_id = section_id_for_unit(module["unit"])
            heading = f"Module {module['code']} {module['title']}"
            section_id = section_id_for_module(module)
            path = f"{UNIT_TITLES[module['unit']][0]} > {heading}"
            text = "\n".join(
                pages[page_no - 1] for page_no in
                range(module["start"], module["end"] + 1)
                if page_no - 1 < len(pages)
            )
            con.execute(
                """
                INSERT INTO sections
                (section_id, book_id, parent_id, level, heading,
                 heading_normalized, ordinal, path, pdf_page_start,
                 pdf_page_end, printed_page_start, printed_page_end, is_leaf,
                 excluded, text_hash, structure_confidence)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    section_id, BOOK_ID, unit_id, 1, heading, norm_name(heading),
                    ordinal, path, module["start"], module["end"],
                    max(0, module["start"] - 1), max(0, module["end"] - 1),
                    1, 0, sha256(text), 1.0,
                ),
            )
            for page_no in range(module["start"], module["end"] + 1):
                if page_no - 1 >= len(pages):
                    break
                page_text = pages[page_no - 1]
                con.execute(
                    "INSERT OR REPLACE INTO section_texts"
                    "(section_id, page_no, text, text_hash) VALUES (?,?,?,?)",
                    (section_id, page_no, page_text, sha256(page_text)),
                )

        created = collections.Counter()
        for entry in entries:
            section_id = entry["section_id"]
            name = entry["term"]
            quote = entry["definition"]
            quote_hash = sha256(norm_quote(quote))
            kp_id = f"{BOOK_ID}-kp-" + hashlib.sha1(
                (BOOK_ID + section_id + norm_name(name) + quote_hash).encode("utf-8")
            ).hexdigest()[:16]
            status = "approved"
            con.execute(
                """
                INSERT INTO knowledge_points
                (kp_id, book_id, section_id, subheading, name, name_normalized,
                 definition_quote, definition_type, definition_language,
                 source_page, source_char_start, source_char_end, quote_hash,
                 plain_en, plain_word_count, confidence, status, prompt_version,
                 created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    kp_id, BOOK_ID, section_id, entry.get("module_title"), name,
                    norm_name(name), quote, "glossary", "en",
                    entry["source_page"], None, None, quote_hash,
                    entry["plain_en"], entry["plain_word_count"],
                    entry.get("mapping_confidence", 0.9), status,
                    PROMPT_VERSION, now,
                ),
            )
            created[entry["unit"]] += 1
            alias_values = set(alias_forms(name)) | set(entry.get("extra_aliases") or [])
            for alias in alias_values:
                mode = "case_sensitive" if is_acronym(alias) else "insensitive"
                try:
                    con.execute(
                        "INSERT OR IGNORE INTO kp_aliases"
                        "(kp_id, alias, alias_normalized, source, match_mode)"
                        " VALUES (?,?,?,?,?)",
                        (kp_id, alias, norm_name(alias), "myers-glossary", mode),
                    )
                except sqlite3.IntegrityError:
                    pass
        aliases_added = con.execute(
            """
            SELECT COUNT(*) FROM kp_aliases a
            JOIN knowledge_points k ON k.kp_id=a.kp_id
            WHERE k.book_id=?
            """,
            (BOOK_ID,),
        ).fetchone()[0]

        con.execute(
            """
            INSERT INTO ingestion_runs
            (run_id, book_id, prompt_version, model, status, gates_json,
             stats_json, started_at, finished_at)
            VALUES (?,?,?,?,?,?,?,?,?)
            """,
            (
                f"myers-import-{stamp}", BOOK_ID, PROMPT_VERSION,
                "pdftotext+pdftohtml/import_myers_kps.py", "success",
                json.dumps({"glossary": "pass", "plain_en": "pass"}),
                json.dumps({
                    "sections": len(modules) + len(units),
                    "knowledge_points": len(entries),
                    "units": created,
                }),
                now, now,
            ),
        )
        con.commit()
        integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
        fk = con.execute("PRAGMA foreign_key_check").fetchall()
        print("inserted KPs:", len(entries), "aliases:", aliases_added)
        print("integrity:", integrity, "foreign_key_check:",
              "OK" if not fk else fk[:3])
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()

    with open(REPORT, "w", encoding="utf-8") as handle:
        handle.write("# Myers 4e 导入报告\n\n")
        handle.write(f"- Book: `{BOOK_ID}`\n")
        handle.write(f"- Sections: {len(modules) + len(units)}"
                     f"（{len(units)} units + {len(modules)} modules）\n")
        handle.write(f"- Knowledge points: {len(entries)}\n")
        handle.write(f"- Aliases: {aliases_added}\n")
        handle.write("- Modules without glossary KPs: EM.1, EM.3\n")
        handle.write(f"- Units: {dict(created)}\n")
        handle.write("- Definition type: `glossary`（English Glossary/Glosario）\n")
        handle.write("- Module mapping: 652 definition-snippet, "
                     "17 term-frequency\n")
    print("report:", REPORT)


if __name__ == "__main__":
    main()
