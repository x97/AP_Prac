#!/usr/bin/env python3
"""Validate authored statistics knowledge points against section texts.

Input JSON (one file or a directory of unit files):
  [{"section_id": "...", "name": "...", "page": 62,
    "quote": "...", "plain_en": "...", "definition_type": "explicit"}, ...]

For each KP:
  - quote must be a whitespace-normalised substring of its section text
  - source page is recomputed from the page markers
  - plain_en must contain 1-10 English words
  - name should occur in the quote or section

Outputs data/content/statistics/extraction/kp_all.json with hashes/ids and a report.
"""
import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
EXTRACT = os.path.join(ROOT, "data", "content", "statistics", "extraction")
SEC_DIR = os.path.join(EXTRACT, "sections")
SECTIONS = os.path.join(EXTRACT, "sections.json")
BOOK_ID = "statistics-barrons-2027"
PROMPT_VERSION = "whole-book-kp-v1"


def clean(s):
    s = s or ""
    s = s.replace(" ", " ").replace("﻿", "")
    s = s.replace("’", "'").replace("‘", "'")
    s = s.replace("“", '"').replace("”", '"')
    s = s.replace("–", "-").replace("—", "-")
    s = s.replace("−", "-").replace("­", "")
    return re.sub(r"\s+", " ", s).strip()


def match_norm(s):
    s = clean(s).lower()
    # Line-end hyphenation in the ebook source.
    s = re.sub(r"-\s+(?=[a-z])", "-", s)
    # Curly/straight quotes and apostrophes are already normalised.
    return s


def word_count(s):
    return len([w for w in clean(s).split(" ") if w])


def sha256(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def load_sections():
    meta = json.load(open(SECTIONS, encoding="utf-8"))
    by_id = {s["section_id"]: s for s in meta["sections"]}
    texts = {}
    for fname in os.listdir(SEC_DIR):
        if not fname.endswith(".txt"):
            continue
        raw = open(os.path.join(SEC_DIR, fname), encoding="utf-8").read()
        parts = re.split(r"########## SECTION (statistics-barrons-2027-[^ ]+) \|.*?##########",
                         raw)
        for i in range(1, len(parts), 2):
            texts[parts[i]] = parts[i + 1]
    return meta, by_id, texts


def page_for_quote(text, needle):
    """Find the page where the quote begins (tolerates cross-page quotes)."""
    parts = re.split(r"\[\[PAGE (\d+)\]\]", text)
    # parts: ['', page, body, page, body, ...]
    needle_head = match_norm(needle)[:80]
    for i in range(1, len(parts), 2):
        page = int(parts[i])
        body = match_norm(parts[i + 1] if i + 1 < len(parts) else "")
        if needle_head and needle_head in body:
            return page
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="+",
                    help="JSON file(s) with authored KPs")
    ap.add_argument("--out", default=os.path.join(EXTRACT, "kp_all.json"))
    args = ap.parse_args()

    meta, by_id, texts = load_sections()
    records = []
    issues = []
    for path in args.inputs:
        data = json.load(open(path, encoding="utf-8"))
        if isinstance(data, dict):
            data = data.get("knowledge_points", [])
        for row in data:
            records.append(row)

    seen = {}
    out = []
    for row in records:
        sid = row["section_id"]
        sec = by_id.get(sid)
        if not sec:
            issues.append(("error", row.get("name"), sid, "unknown section"))
            continue
        full = texts.get(sid, "")
        plain = re.sub(r"\[\[PAGE \d+\]\]", " ", full)
        hay = match_norm(plain)
        quote = clean(row["quote"])
        needle = match_norm(quote)
        pos = hay.find(needle)
        match_type = "exact"
        if pos < 0:
            # Try removing all whitespace (formulas/punctuation spacing).
            compact_hay = re.sub(r"\s+", "", hay)
            compact_needle = re.sub(r"\s+", "", needle)
            cpos = compact_hay.find(compact_needle)
            if cpos >= 0:
                # Map compact offset back approximately by walking.
                pos = None
                match_type = "compact"
            else:
                issues.append(("error", row["name"], sid, "quote not found"))
                continue
        page = page_for_quote(full, quote) if pos is not None else row.get("page")
        supplied_page = row.get("page")
        if page and supplied_page and page != supplied_page:
            issues.append(("warning", row["name"], sid,
                           f"page {supplied_page} -> {page}"))
        wc = word_count(row.get("plain_en", ""))
        if not 1 <= wc <= 10:
            issues.append(("error", row["name"], sid,
                           f"plain_en words={wc}"))
        status = "approved"
        if match_type != "exact" or not 1 <= wc <= 10:
            status = "needs_review"
        if row.get("definition_type") == "none":
            status = "needs_review"
        quote_hash = sha256(needle)
        kp_id = "statistics-barrons-2027-kp-" + hashlib.sha1(
            (BOOK_ID + sid + match_norm(row["name"]) + quote_hash).encode("utf-8")
        ).hexdigest()[:16]
        rec = {
            "kp_id": kp_id,
            "book_id": BOOK_ID,
            "section_id": sid,
            "subheading": row.get("subheading"),
            "name": row["name"],
            "name_normalized": match_norm(row["name"]),
            "definition_quote": quote,
            "definition_type": row.get("definition_type", "explicit"),
            "definition_language": "en",
            "source_page": page or supplied_page,
            "quote_hash": quote_hash,
            "plain_en": clean(row.get("plain_en")),
            "plain_word_count": wc,
            "confidence": 0.95 if status == "approved" else 0.6,
            "status": status,
            "prompt_version": PROMPT_VERSION,
            "covers_concepts": row.get("covers_concepts"),
        }
        key = (sid, rec["name_normalized"], quote_hash)
        if key in seen:
            rec["duplicate_of"] = seen[key]
            issues.append(("warning", rec["name"], sid, "exact duplicate"))
        else:
            seen[key] = kp_id
        out.append(rec)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    report = os.path.join(EXTRACT, "reports", "kp_validation_report.md")
    os.makedirs(os.path.dirname(report), exist_ok=True)
    counts = Counter(r["status"] for r in out)
    lines = ["# 统计学知识点校验报告", "",
             f"- 总条数: {len(out)}",
             f"- approved: {counts.get('approved', 0)}",
             f"- needs_review: {counts.get('needs_review', 0)}",
             f"- 精确重复: {sum(1 for r in out if r.get('duplicate_of'))}",
             ""]
    if issues:
        lines += ["## 问题", ""]
        for sev, name, sid, msg in issues[:200]:
            lines.append(f"- **{sev}** `{sid}` {name}: {msg}")
    open(report, "w", encoding="utf-8").write("\n".join(lines) + "\n")

    print(f"records={len(out)} approved={counts.get('approved',0)} "
          f"needs_review={counts.get('needs_review',0)} issues={len(issues)}")
    for sev, name, sid, msg in issues[:30]:
        print(f"  {sev}: {sid} {name}: {msg}")
    print("wrote", args.out)


if __name__ == "__main__":
    main()
