#!/usr/bin/env python3
"""Stage 0/1/2 for Barron's AP Statistics Premium 2027.

Builds the book structure map (units, review sections, reference sections) from
the PDF's embedded table of contents, then writes readable section texts with
page markers for knowledge-point extraction.

Outputs (all under data/content/statistics/extraction/):
  book_meta.json
  sections.json
  sections/unit1.txt ... unit5.txt, reference.txt
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PDF_REL = "assets/statistics/books/AP Statistics Premium, 2027 - Martin Sternstein.pdf"
PDF_ABS = os.path.join(ROOT, PDF_REL)
OUT_DIR = os.path.join(ROOT, "data", "content", "statistics", "extraction")
SEC_DIR = os.path.join(OUT_DIR, "sections")

BOOK_ID = "statistics-barrons-2027"
SUBJECT_ID = "statistics"

# Appendix sections we keep as reference knowledge (not quizzes/answers).
REFERENCE_TITLES = {
    "Graphical Displays",
    "Guide to Inference",
    "Templates",
    "Names of Procedures",
}
# Final-review section worth keeping as a decision procedure.
FINAL_REVIEW_KEEP = {"Selecting an Appropriate Inference Procedure"}

NOISE_LINES = {
    "Follow for extended description",
}


def load_fitz():
    try:
        import fitz  # noqa: F401
    except ImportError:
        sys.path.append("/Users/aa/Library/Python/3.9/lib/python/site-packages")
    import fitz
    return fitz


def clean_line(line):
    line = line.replace(" ", " ").replace("﻿", "")
    return re.sub(r"\s+", " ", line).strip()


def dump_page(page):
    """Return cleaned text lines in reading order."""
    lines = []
    for raw in page.get_text("text").splitlines():
        s = clean_line(raw)
        if not s or s in NOISE_LINES:
            continue
        # Drop bare printed page numbers (rare in this ebook, but harmless).
        if re.fullmatch(r"\d{1,3}", s):
            continue
        lines.append(s)
    return lines


def page_text_with_markers(doc, start, end, stop_heading=None, start_heading=None):
    chunks = []
    for pn in range(start, end + 1):
        lines = dump_page(doc[pn - 1])
        if pn == start and start_heading:
            key = start_heading[:24].strip()
            for i, line in enumerate(lines):
                if line == start_heading or line.startswith(key) or start_heading.startswith(line):
                    lines = lines[i:]
                    break
        if pn == end and stop_heading:
            # Cut a section that shares its final page with the next heading.
            for i, line in enumerate(lines):
                if line.startswith(stop_heading):
                    lines = lines[:i]
                    break
        if not lines:
            continue
        chunks.append(f"[[PAGE {pn}]]\n" + "\n".join(lines))
    return "\n\n".join(chunks)


def norm_text(text):
    text = text.replace("’", "'").replace("‘", "'")
    text = text.replace("“", '"').replace("”", '"')
    text = text.replace("–", "-").replace("—", "-")
    text = text.replace("−", "-").replace("­", "")
    text = re.sub(r"-\s*\n\s*(?=[a-z])", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def strip_markers(text):
    return re.sub(r"\[\[PAGE \d+\]\]", " ", text)


def build():
    fitz = load_fitz()
    doc = fitz.open(PDF_ABS)
    toc = doc.get_toc()
    entries = [{"level": lvl, "title": clean_line(title), "page": pg}
               for lvl, title, pg in toc]

    def next_page(idx, max_level):
        for e in entries[idx + 1:]:
            if e["level"] <= max_level:
                return e["page"]
        return doc.page_count

    units = []
    unit_idx = [i for i, e in enumerate(entries)
                if e["level"] == 2 and e["title"].startswith("Unit ")]
    for n, i in enumerate(unit_idx, 1):
        unit = entries[i]
        end = next_page(i, 2) - 1
        units.append({
            "unit_no": n,
            "heading": unit["title"],
            "pdf_page_start": unit["page"],
            "pdf_page_end": end,
            "sections": [],
        })

    sections = []
    for unit in units:
        unit_start = unit["pdf_page_start"]
        unit_end = unit["pdf_page_end"]
        # Level-3 entries that fall inside this unit.
        cand = [e for e in entries
                if e["level"] == 3 and unit_start <= e["page"] <= unit_end]
        for j, e in enumerate(cand, 1):
            title = e["title"]
            if title.startswith("Quiz ") or title == "Summary":
                continue
            end = next_page(entries.index(e), 3)
            # A section cannot run past its unit.
            end = max(e["page"], min(end, unit_end))
            # If the next level-3/2 entry is on the same page, keep a non-empty
            # range; the text extractor will cut at the next heading.
            next_entry = None
            for e2 in entries[entries.index(e) + 1:]:
                if e2["level"] <= 3:
                    next_entry = e2
                    break
            sections.append({
                "section_id": f"{BOOK_ID}-u{unit['unit_no']}-s{j:02d}",
                "book_id": BOOK_ID,
                "parent_id": f"{BOOK_ID}-u{unit['unit_no']}",
                "unit_no": unit["unit_no"],
                "level": 1,
                "heading": title,
                "ordinal": j,
                "path": f"{unit['heading']} > {title}",
                "pdf_page_start": e["page"],
                "pdf_page_end": end,
                "stop_heading": next_entry["title"] if next_entry else None,
                "excluded": 0,
                "excluded_reason": None,
            })

    # Final-review decision procedure + appendix reference sections.
    ref_sections = []
    part3 = [e for e in entries if e["title"] == "Final Review"]
    if part3:
        p3_start = part3[0]["page"]
        p3_end = next_page(entries.index(part3[0]), 1) - 1
        for e in entries:
            if e["level"] == 3 and e["title"] in FINAL_REVIEW_KEEP \
                    and p3_start <= e["page"] <= p3_end:
                ref_sections.append(e)
    appendices = [e for e in entries if e["title"] == "Appendices"]
    if appendices:
        ap_start = appendices[0]["page"]
        ap_end = next_page(entries.index(appendices[0]), 1) - 1
        for e in entries:
            if e["level"] == 3 and e["title"] in REFERENCE_TITLES \
                    and ap_start <= e["page"] <= ap_end:
                ref_sections.append(e)

    ref_sections.sort(key=lambda e: e["page"])
    for j, e in enumerate(ref_sections, 1):
        end = max(e["page"], next_page(entries.index(e), 3))
        nxt = None
        for e2 in entries[entries.index(e) + 1:]:
            if e2["level"] <= 3:
                nxt = e2
                break
        ref_sections[j - 1] = {
            "section_id": f"{BOOK_ID}-ref-s{j:02d}",
            "book_id": BOOK_ID,
            "parent_id": f"{BOOK_ID}-ref",
            "unit_no": 0,
            "level": 1,
            "heading": e["title"],
            "ordinal": j,
            "path": f"Reference > {e['title']}",
            "pdf_page_start": e["page"],
            "pdf_page_end": end,
            "stop_heading": nxt["title"] if nxt else None,
            "excluded": 0,
            "excluded_reason": None,
        }
    sections.extend(ref_sections)

    # Excluded things, recorded for the structure report.
    excluded = []
    for e in entries:
        if e["level"] == 3 and (e["title"].startswith("Quiz ")
                                or e["title"] in {
                                    "Summary", "Answer Explanations",
                                    "Statistical Insights into Social Issues",
                                    "50 Misconceptions",
                                    "50 Common Errors on the AP Exam",
                                    "50 AP Exam Hints, Advice, and Reminders",
                                    "Answer Explanations for Quizzes 1–34",
                                    "AP Scoring Guide",
                                    "Formulas Given on the AP Statistics Exam",
                                    "Table A: Standard Normal Probabilities",
                                    "Table B: t-Distribution Critical Values",
                                    "Table C: χ2 Critical Values",
                                }):
            excluded.append({"heading": e["title"], "pdf_page": e["page"],
                             "reason": "exercise_or_answer_or_advice"})
    for e in entries:
        if e["level"] == 1 and e["title"] in {
                "Title Page", "Acknowledgments", "Copyright", "About the Author",
                "Table of Contents", "How to Use This Book",
                "Barron’s Essential 5", "Exam Overview"}:
            excluded.append({"heading": e["title"], "pdf_page": e["page"],
                             "reason": "front_matter"})

    # Book metadata.
    meta = {
        "book_id": BOOK_ID,
        "subject_id": SUBJECT_ID,
        "title": "AP Statistics Premium, 2027",
        "authors": "Martin Sternstein",
        "publisher": "Barron's Educational Series (Kaplan)",
        "edition": "2027",
        "year": 2026,
        "isbn": "979-8-3497-0157-3",
        "language": "en",
        "book_type": "review_book",
        "target_exam": "AP Statistics",
        "target_year": 2027,
        "source_path": PDF_REL,
        "total_pages": doc.page_count,
        "pdf_printed_offset": 33,
        "ocr_used": 0,
        "classification_status": "confirmed",
        "classification_evidence": {
            "signals": [
                "title:AP Statistics Premium 2027",
                "author:Martin Sternstein",
                "publisher:Barron's",
                "toc:Diagnostic Test + Units 1-5 + Practice Tests 1-4",
                "target_exam:AP Statistics",
                "language:en",
            ],
            "subject_match": SUBJECT_ID,
            "confidence": 0.99,
        },
        "units": [{"unit_no": u["unit_no"], "heading": u["heading"],
                   "pdf_page_start": u["pdf_page_start"],
                   "pdf_page_end": u["pdf_page_end"]} for u in units],
        "reference_parent": {"section_id": f"{BOOK_ID}-ref",
                             "heading": "Reference",
                             "pdf_page_start": ref_sections[0]["pdf_page_start"] if ref_sections else None,
                             "pdf_page_end": ref_sections[-1]["pdf_page_end"] if ref_sections else None},
        "excluded": excluded,
    }

    os.makedirs(SEC_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "book_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    with open(os.path.join(OUT_DIR, "sections.json"), "w", encoding="utf-8") as f:
        json.dump({"units": units, "sections": sections}, f, ensure_ascii=False, indent=1)

    # Per-unit text files.
    files = []
    for unit in units:
        path = os.path.join(SEC_DIR, f"unit{unit['unit_no']}.txt")
        parts = []
        for sec in [s for s in sections if s["unit_no"] == unit["unit_no"]]:
            body = page_text_with_markers(doc, sec["pdf_page_start"],
                                          sec["pdf_page_end"], sec["stop_heading"],
                                          sec["heading"])
            sec["char_count"] = len(strip_markers(body))
            sec["page_count"] = sec["pdf_page_end"] - sec["pdf_page_start"] + 1
            parts.append(f"\n\n########## SECTION {sec['section_id']} | {sec['heading']} | "
                         f"PDF pages {sec['pdf_page_start']}-{sec['pdf_page_end']} ##########\n\n"
                         + body)
        with open(path, "w", encoding="utf-8") as f:
            f.write("".join(parts))
        files.append(path)

    ref_path = os.path.join(SEC_DIR, "reference.txt")
    parts = []
    for sec in ref_sections:
        body = page_text_with_markers(doc, sec["pdf_page_start"],
                                      sec["pdf_page_end"], sec["stop_heading"],
                                      sec["heading"])
        sec["char_count"] = len(strip_markers(body))
        sec["page_count"] = sec["pdf_page_end"] - sec["pdf_page_start"] + 1
        parts.append(f"\n\n########## SECTION {sec['section_id']} | {sec['heading']} | "
                     f"PDF pages {sec['pdf_page_start']}-{sec['pdf_page_end']} ##########\n\n"
                     + body)
    with open(ref_path, "w", encoding="utf-8") as f:
        f.write("".join(parts))
    files.append(ref_path)

    with open(os.path.join(OUT_DIR, "sections.json"), "w", encoding="utf-8") as f:
        json.dump({"units": units, "sections": sections}, f, ensure_ascii=False, indent=1)

    print(f"units: {len(units)}")
    print(f"sections: {len(sections)}")
    for sec in sections:
        print(f"  {sec['section_id']:<44} p{sec['pdf_page_start']:>3}-{sec['pdf_page_end']:<3} "
              f"{sec['char_count']:>7} chars  {sec['heading']}")
    print("wrote", OUT_DIR)
    print("files:", ", ".join(os.path.basename(p) for p in files))


if __name__ == "__main__":
    build()
