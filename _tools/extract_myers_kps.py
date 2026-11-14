#!/usr/bin/env python3
"""Extract Myers' AP Psychology glossary terms into the whole-book KP shape.

Source: Myers' Psychology for the AP Course, 4th ed. (BFW, 2024).
The English Glossary/Glosario is the publisher's AP vocabulary list; each
entry has a verbatim definition.  Module headings come from the body, and
the unit-review key-term lists give a high-confidence unit assignment.

This script only produces review artifacts (JSON/CSV/report).  Importing
into psychology_knowledge.db is handled by import_myers_kps.py.
"""
import argparse
import collections
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEFAULT_PDF = os.path.join(ROOT, "assets/psychology/books/教材1--Myers.pdf")
OUT_DIR = os.path.join(ROOT, "data", "content", "psychology", "extraction", "myers")
PROMPT_VERSION = "whole-book-kp-v1"

LIGATURES = {
    "ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi", "ﬄ": "ffl",
    "’": "'", "‘": "'", "“": '"', "”": '"',
    "–": "-", "—": "-",
}


def clean_text(value):
    value = value or ""
    for src, dst in LIGATURES.items():
        value = value.replace(src, dst)
    value = re.sub(r"-\s+(?=[a-z])", "-", value)
    return re.sub(r"\s+", " ", value).strip()


def norm(value):
    value = clean_text(value).lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def core_name(value):
    value = re.sub(r"\[[^\]]*\]", " ", value or "")
    value = re.sub(r"\([^)]*\)", " ", value)
    value = re.sub(r"\b(the|a|an|of|and|or|for|in|on|to)\b", " ", value, flags=re.I)
    return norm(value)


def sha256(value):
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest()


def run(cmd):
    subprocess.run(cmd, check=True)


def page_lines(pages, page_no):
    return [line.strip() for line in pages[page_no - 1].splitlines() if line.strip()]


def extract_pages(pdf, cache_dir):
    os.makedirs(cache_dir, exist_ok=True)
    text_path = os.path.join(cache_dir, "myers.txt")
    if not os.path.exists(text_path):
        run(["pdftotext", pdf, text_path])
    with open(text_path, encoding="utf-8", errors="replace") as handle:
        return handle.read().split("\f")


def glossary_range(pages):
    start = end = None
    for i, page in enumerate(pages, 1):
        lines = page_lines(pages, i)
        if not lines:
            continue
        if lines[0] == "Glossary":
            start = i
        if lines[0].startswith("Glossary / Glosario"):
            end = i - 1
            break
    if not start or not end:
        raise SystemExit("could not locate English glossary in PDF")
    return start, end


def extract_glossary(pdf, first_page, last_page, cache_dir):
    xml_path = os.path.join(cache_dir, "myers_glossary.xml")
    if not os.path.exists(xml_path):
        stem = os.path.join(cache_dir, "myers_glossary")
        run(["pdftohtml", "-xml", "-hidden", "-f", str(first_page),
             "-l", str(last_page), pdf, stem])
    root = ET.parse(xml_path).getroot()
    entries = []
    current = None
    for page in root.findall("page"):
        page_no = int(page.get("number"))
        texts = []
        for node in page.findall("text"):
            text = "".join(node.itertext()).strip()
            if not text:
                continue
            top = float(node.get("top") or 0)
            left = float(node.get("left") or 0)
            if top > 1100:  # page footer
                continue
            texts.append((top, left, text, node.get("font"),
                          node.find("b") is not None))
        texts.sort(key=lambda row: (row[0], row[1]))
        for top, left, text, font, bold in texts:
            # Glossary entry labels are bold 17pt text at the left margin.
            if bold and font == "2" and left < 150:
                current = {
                    "term": clean_text(text),
                    "definition_parts": [],
                    "glossary_page": page_no,
                }
                entries.append(current)
            elif current is not None:
                current["definition_parts"].append(text)
    for entry in entries:
        entry["definition"] = clean_text(" ".join(entry.pop("definition_parts")))

    # pdftotext -layout preserves the reading order of inline italics
    # (e.g. "below (hypo) the thalamus") and does not lose ft ligatures.
    layout_path = os.path.join(cache_dir, "myers_glossary_layout.txt")
    if not os.path.exists(layout_path):
        run(["pdftotext", "-layout", "-f", str(first_page), "-l",
             str(last_page), pdf, layout_path])
    with open(layout_path, encoding="utf-8", errors="replace") as handle:
        layout_pages = handle.read().split("\f")
    blocks_text = []
    for page in layout_pages:
        lines = [line for line in page.splitlines()
                 if not re.fullmatch(r"\s*\d{1,4}\s*", line)]
        while lines and not lines[-1].strip():
            lines.pop()
        blocks_text.extend(lines)
        blocks_text.append("")
    blocks = [block.strip() for block in
              re.split(r"\n\s*\n", "\n".join(blocks_text)) if block.strip()]
    if blocks and blocks[0].startswith("Glossary"):
        first_lines = blocks.pop(0).splitlines()
        remainder = "\n".join(first_lines[1:]).strip()
        if remainder:
            blocks.insert(0, remainder)

    def term_matches(candidate, expected):
        return (norm(candidate) == norm(expected) or
                core_name(candidate) == core_name(expected))

    index = 0
    layout_entries = []
    for block in blocks:
        lines = block.splitlines()
        candidate = lines[0].strip()
        definition = " ".join(line.strip() for line in lines[1:]).strip()
        matched = None
        for offset in range(index, min(index + 3, len(entries))):
            if term_matches(candidate, entries[offset]["term"]):
                matched = offset
                break
        if matched is not None:
            while index < matched:
                layout_entries.append(None)
                index += 1
            layout_entries.append((clean_text(candidate),
                                   clean_text(definition)))
            index = matched + 1
        elif layout_entries:
            # A page-break continuation of the previous definition.
            previous = layout_entries[-1]
            if previous:
                term, old = previous
                layout_entries[-1] = (
                    term, clean_text(old + " " + block)
                )
        else:
            layout_entries.append(None)
    while len(layout_entries) < len(entries):
        layout_entries.append(None)
    for entry, layout in zip(entries, layout_entries):
        if layout and layout[1]:
            entry["term"] = layout[0] or entry["term"]
            entry["definition"] = layout[1]
    return entries


def parse_modules(pages):
    candidates = []
    for page_no, page in enumerate(pages, 1):
        lines = page_lines(pages, page_no)
        if not lines:
            continue
        match = re.match(
            r"^Module\s+((?:\d+\.\d+[a-z]?)|(?:EM\.\d+))\s*(.*)$", lines[0]
        )
        if not match or "REVIEW" in lines[0]:
            continue
        code = match.group(1)
        title_parts = [match.group(2)] if match.group(2) else []
        for line in lines[1:]:
            if line.startswith("Learning Target") or line.startswith("Module "):
                break
            if re.fullmatch(r"\d+", line):
                break
            title_parts.append(line)
        title = re.sub(r"\s+", " ", " ".join(title_parts)).strip()
        candidates.append({"code": code, "title": title, "start": page_no})
    # Drop body cross-references such as "Module 2.8 explored ...": real
    # module pages have a Learning Target block within the next few lines.
    real = []
    for item in candidates:
        lines = page_lines(pages, item["start"])
        joined = " ".join(lines[:12])
        if "Learning Target" not in joined:
            continue
        real.append(item)
    # A bare 2.8 next to 2.8a/2.8b/2.8c/2.8d is a cross-reference.
    bases = {re.sub(r"[a-z]$", "", item["code"]) for item in real}
    real = [item for item in real
            if not (item["code"] in bases and
                    any(other["code"] != item["code"] and
                        other["code"].startswith(item["code"]) and
                        re.search(r"[a-z]$", other["code"]) for other in real))]
    for index, item in enumerate(real):
        item["end"] = real[index + 1]["start"] - 1 if index + 1 < len(real) else 2600
        item["unit"] = "EM" if item["code"].startswith("EM.") else item["code"].split(".")[0]
        item["section_id"] = f"psychology-myers-2024-u{item['unit']}-m{item['code'].replace('.', '-')}"
    return real


UNIT_TITLES = {
    "0": ("AN INTRODUCTION TO PSYCHOLOGICAL SCIENCE", "Science Practices: Research Methods and Data Interpretation"),
    "1": ("BIOLOGICAL BASES OF BEHAVIOR", "Biological Bases of Behavior"),
    "2": ("COGNITION", "Cognition"),
    "3": ("DEVELOPMENT AND LEARNING", "Development and Learning"),
    "4": ("SOCIAL PSYCHOLOGY AND PERSONALITY", "Social Psychology and Personality"),
    "5": ("MENTAL AND PHYSICAL HEALTH", "Mental and Physical Health"),
    "EM": ("ENRICHMENT MODULES", "Enrichment Modules"),
}

# Three glossary entries combine two distinct concepts.  Keep each sense
# as its own KP, matching how the book teaches them in different units.
SENSE_SPLITS = {
    "accommodation": [("sensation", "1"), ("developmental", "3")],
    "discrimination": [("classical_conditioning", "3"), ("social", "4")],
    "psychoanalysis": [("theory", "4"), ("technique", "5")],
}

TERM_FIXES = {
    "GRIT_1": "GRIT",
    "instinctive dri": "instinctive drift",
}


def unit_review_terms(pages, glossary_terms):
    """Return {unit: set(normalized term)} from Unit N Review key-term lists."""
    norm_terms = {norm(term) for term in glossary_terms}
    by_unit = collections.defaultdict(set)
    starts = []
    for page_no, page in enumerate(pages, 1):
        match = re.search(r"Unit\s+([0-5])\s+Review", page)
        if match and "Key Terms" in page:
            starts.append((page_no, match.group(1)))
    for index, (page_no, unit) in enumerate(starts):
        end = starts[index + 1][0] - 1 if index + 1 < len(starts) else page_no + 30
        text = "\n".join(pages[p - 1] for p in range(page_no, end + 1))
        if "Key Terms and Contributors to" in text:
            text = text.split("Key Terms and Contributors to", 1)[1]
        text = re.split(r"Unit\s+\d\s+AP® Practice", text)[0]
        for line in text.splitlines():
            candidate = clean_text(line)
            candidate_norm = norm(candidate)
            if candidate_norm in norm_terms:
                by_unit[unit].add(candidate_norm)
    return by_unit


def module_for_page(modules, page_no):
    for module in modules:
        if module["start"] <= page_no <= module["end"]:
            return module
    return None


def find_snippet(definition, page_texts, allowed_pages):
    words = re.findall(r"[a-z0-9']+", norm(definition))
    for start in (0, 3, 6):
        snippet = " ".join(words[start:start + 12])
        if len(snippet) < 25:
            continue
        for page_no in allowed_pages:
            if snippet in page_texts.get(page_no, ""):
                return page_no
    return None


def count_term(term, page_texts, allowed_pages, page_module):
    base = norm(term)
    variants = {base}
    if "(" in term:
        variants.add(norm(re.sub(r"\([^)]*\)", " ", term)))
    variants = {value for value in variants if value}
    patterns = [
        re.compile(r"(?<![a-z])" + re.escape(value) + r"(?![a-z])")
        for value in variants
    ]
    counts = collections.Counter()
    first = {}
    for page_no in allowed_pages:
        module = page_module.get(page_no)
        if not module:
            continue
        text = page_texts.get(page_no, "")
        for pattern in patterns:
            found = pattern.findall(text)
            if found:
                counts[module["section_id"]] += len(found)
                first.setdefault(module["section_id"], page_no)
    return counts, first


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", default=DEFAULT_PDF)
    parser.add_argument("--out-dir", default=OUT_DIR)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    cache_dir = os.path.join(args.out_dir, "cache")
    pages = extract_pages(args.pdf, cache_dir)
    glossary_start, glossary_end = glossary_range(pages)
    print(f"glossary PDF pages: {glossary_start}-{glossary_end}")
    entries = extract_glossary(args.pdf, glossary_start, glossary_end, cache_dir)
    for entry in entries:
        entry["term"] = clean_text(re.sub(r"\[[^\]]*\]", " ", entry["term"]))
        entry["term"] = TERM_FIXES.get(entry["term"], entry["term"])
    # Publisher glossary has two exact duplicate concepts:
    # - "effect" repeats the placebo-effect definition; keep "placebo effect".
    # - "character strengths and virtues" repeats the 24-strengths entry.
    merged = []
    strengths = next((entry for entry in entries
                      if entry["term"] == "24 character strengths and virtues"), None)
    for entry in entries:
        term = entry["term"]
        if term == "effect":
            continue
        if term == "character strengths and virtues":
            if strengths is not None:
                strengths.setdefault("extra_aliases", []).append(term)
            continue
        merged.append(entry)
    entries = merged
    print("glossary entries:", len(entries))

    modules = parse_modules(pages)
    print("modules:", len(modules))
    by_unit = unit_review_terms(pages, [entry["term"] for entry in entries])
    print("unit review term coverage:",
          {unit: len(values) for unit, values in sorted(by_unit.items())})

    page_module = {}
    pages_by_unit = collections.defaultdict(list)
    for module in modules:
        for page_no in range(module["start"], module["end"] + 1):
            page_module[page_no] = module
            pages_by_unit[module["unit"]].append(page_no)
    body_pages = sorted(page_module)
    page_texts = {i: norm(page) for i, page in enumerate(pages, 1)}
    module_by_id = {module["section_id"]: module for module in modules}

    work_entries = []
    for entry in entries:
        if entry["term"] in SENSE_SPLITS and "(2)" in entry["definition"]:
            first, second = entry["definition"].split("(2)", 1)
            first = re.sub(r"^\(1\)\s*", "", first).strip()
            for (label, unit), definition in zip(
                SENSE_SPLITS[entry["term"]], (first, second.strip())
            ):
                item = dict(entry)
                item["definition"] = definition
                item["sense"] = label
                item["forced_unit"] = unit
                work_entries.append(item)
        else:
            item = dict(entry)
            item["sense"] = None
            item["forced_unit"] = None
            work_entries.append(item)

    for entry in work_entries:
        term = entry["term"]
        term_norm = norm(term)
        if entry["forced_unit"]:
            units = [entry["forced_unit"]]
        else:
            units = [unit for unit, values in by_unit.items()
                     if term_norm in values]
        allowed_units = set(units)
        allowed_modules = [module for module in modules
                           if not allowed_units or module["unit"] in allowed_units]
        if allowed_units:
            allowed_pages = sorted({
                page_no for unit in allowed_units
                for page_no in pages_by_unit.get(unit, [])
            })
        else:
            allowed_pages = body_pages
        page_no = find_snippet(entry["definition"], page_texts, allowed_pages)
        if page_no:
            module = page_module.get(page_no)
            method = "definition_snippet"
            confidence = 0.9
        else:
            counts, first_pages = count_term(
                term, page_texts, allowed_pages, page_module
            )
            if counts:
                section_id, _count = counts.most_common(1)[0]
                page_no = first_pages[section_id]
                module = module_by_id[section_id]
                method = "term_frequency"
                confidence = 0.6
            elif allowed_modules:
                if entry["sense"]:
                    # Prefer a module whose title matches the sense label.
                    keyword = {
                        "sensation": "sensation",
                        "developmental": "cognitive development",
                        "classical_conditioning": "classical conditioning",
                        "social": "attribution",
                        "theory": "psychodynamic",
                        "technique": "treatment",
                    }.get(entry["sense"], "")
                    matches = [m for m in allowed_modules
                               if keyword and keyword in m["title"].lower()]
                    module = (matches or allowed_modules)[0]
                else:
                    module = allowed_modules[0]
                page_no = module["start"]
                method = "unit_fallback"
                confidence = 0.3
            else:
                module = None
                page_no = None
                method = "unmapped"
                confidence = 0.1
        if not units and module:
            units = [module["unit"]]
        entry.update({
            "units": units,
            "unit": module["unit"] if module else (units[0] if units else None),
            "module_code": module["code"] if module else None,
            "module_title": module["title"] if module else None,
            "section_id": module["section_id"] if module else None,
            "mapping_method": method,
            "mapping_confidence": confidence,
            "body_page": page_no,
            "source_page": entry["glossary_page"],
            "definition_type": "glossary",
            "quote_hash": sha256(norm(entry["definition"])),
            "confidence": confidence,
        })
        entry["aliases"] = sorted({
            term,
            re.sub(r"\([^)]*\)", "", term).strip(),
        } - {""})

    entries = work_entries

    if args.limit:
        entries = entries[:args.limit]

    entries_path = os.path.join(args.out_dir, "myers_glossary.json")
    if os.path.exists(entries_path):
        with open(entries_path, encoding="utf-8") as handle:
            old_entries = json.load(handle)
        old_plain = {
            sha256(norm(old["definition"])): old for old in old_entries
            if old.get("plain_en")
        }
        for entry in entries:
            old = old_plain.get(sha256(norm(entry["definition"])))
            if old:
                entry["plain_en"] = old.get("plain_en")
                entry["plain_word_count"] = old.get("plain_word_count")
                entry["status"] = old.get("status")

    modules_path = os.path.join(args.out_dir, "myers_modules.json")
    with open(modules_path, "w", encoding="utf-8") as handle:
        json.dump(modules, handle, ensure_ascii=False, indent=2)
    with open(entries_path, "w", encoding="utf-8") as handle:
        json.dump(entries, handle, ensure_ascii=False, indent=2)

    csv_path = os.path.join(args.out_dir, "myers_glossary.csv")
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "term", "sense", "definition", "units", "unit", "module_code",
            "module_title", "section_id", "mapping_method",
            "mapping_confidence", "source_page", "body_page", "plain_en",
        ])
        writer.writeheader()
        for entry in entries:
            writer.writerow({
                "term": entry["term"],
                "sense": entry.get("sense") or "",
                "definition": entry["definition"],
                "units": ",".join(entry["units"]),
                "unit": entry["unit"] or "",
                "module_code": entry["module_code"] or "",
                "module_title": entry["module_title"] or "",
                "section_id": entry["section_id"] or "",
                "mapping_method": entry["mapping_method"],
                "mapping_confidence": entry["mapping_confidence"],
                "source_page": entry["source_page"],
                "body_page": entry["body_page"] or "",
                "plain_en": entry.get("plain_en") or "",
            })

    methods = collections.Counter(entry["mapping_method"] for entry in entries)
    units = collections.Counter(entry["unit"] for entry in entries)
    report_path = os.path.join(args.out_dir, "myers_extraction_report.md")
    with open(report_path, "w", encoding="utf-8") as handle:
        handle.write("# Myers AP Psychology 4e — 知识点抽取报告\n\n")
        handle.write(f"- Prompt: `{PROMPT_VERSION}`\n")
        handle.write(f"- PDF: `{os.path.basename(args.pdf)}`\n")
        handle.write(f"- Glossary pages: PDF {glossary_start}–{glossary_end}\n")
        handle.write(f"- Glossary terms: {len(entries)}\n")
        handle.write(f"- English short glosses: {sum(1 for entry in entries if entry.get('plain_en'))}\n")
        handle.write(f"- Modules: {len(modules)}\n")
        with_kp = {entry["module_code"] for entry in entries if entry.get("module_code")}
        zero_modules = [module["code"] for module in modules
                        if module["code"] not in with_kp]
        handle.write(f"- Modules without glossary KPs: "
                     f"{', '.join(zero_modules) if zero_modules else '—'}\n\n")
        handle.write("## 模块映射\n\n| 方法 | 题数 |\n|---|---:|\n")
        for method, count in methods.most_common():
            handle.write(f"| {method} | {count} |\n")
        handle.write("\n## 单元分布\n\n| Unit | 题数 |\n|---|---:|\n")
        for unit, count in sorted(units.items(), key=lambda row: str(row[0])):
            handle.write(f"| {unit} | {count} |\n")
        handle.write("\n## 模块清单\n\n| Unit | Module | 标题 | 起始页 | 结束页 |\n")
        handle.write("|---|---|---|---:|---:|\n")
        for module in modules:
            handle.write(
                f"| {module['unit']} | {module['code']} | {module['title']} | "
                f"{module['start']} | {module['end']} |\n"
            )
    print("wrote:", entries_path)
    print("wrote:", modules_path)
    print("wrote:", csv_path)
    print("wrote:", report_path)
    print("mapping methods:", dict(methods))
    print("units:", dict(units))


if __name__ == "__main__":
    main()
