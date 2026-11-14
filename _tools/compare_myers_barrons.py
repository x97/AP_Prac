#!/usr/bin/env python3
"""Compare Myers glossary KPs with the existing Barron's KP set."""
import collections
import csv
import difflib
import json
import os
import re
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DB = os.path.join(ROOT, "data", "content", "psychology", "psychology_knowledge.db")
MYERS = os.path.join(ROOT, "data", "content", "psychology", "extraction", "myers", "myers_glossary.json")
OUT = os.path.join(ROOT, "data", "content", "psychology", "extraction", "myers", "myers_vs_barrons.csv")
BARRON_OUT = os.path.join(ROOT, "data", "content", "psychology", "extraction", "myers", "barrons_only.csv")
REPORT = os.path.join(ROOT, "data", "content", "psychology", "extraction", "myers", "myers_vs_barrons.md")

STOP = {"the", "a", "an", "of", "and", "or", "for", "in", "on", "to", "with"}
SYNONYMS = {
    "approach": "perspective",
    "approaches": "perspective",
    "perspectives": "perspective",
    "study": "method",
    "studies": "method",
    "factor": "trait",
    "factors": "trait",
}
GENERIC = {
    "schedule", "response", "theory", "method", "study", "disorder",
    "disorders", "therapy", "therapies", "effect", "phenomenon",
    "principle", "approach", "perspective", "model", "factor", "trait",
    "process", "psychology", "sleep", "system", "memory", "emotion",
    "learning", "behavior", "intelligence", "personality", "motivation",
    "perception", "sensation", "development", "cognition", "language",
    "self",
}
MANUAL_EQUIVALENTS = {
    "24 character strengths and virtues": ["character strengths"],
    "character strengths and virtues": ["character strengths"],
    "all-or-none response": ["all-or-none principle"],
    "amygdala": ["Amygdala and hippocampus"],
    "behavioral approach": ["Behavioral Perspective"],
    "binocular cue": ["binocular depth cues"],
    "biological psychology": ["biopsychology"],
    "biomedical therapy": ["somatic therapies"],
    "biopsychosocial approach": ["Biopsychosocial Perspective"],
    "blindsight": ["Blind sight"],
    "bulimia nervosa": ["bulimia"],
    "case study": ["Case study method"],
    "Cattell-Horn-Carroll (CHC) theory": ["Cattell-Horn-Carroll", "CHC"],
    "conduction hearing loss": ["conduction deafness"],
    "continuous reinforcement schedule": ["continuous reinforcement"],
    "partial (intermittent) reinforcement schedule": ["partial reinforcement"],
    "conditioned reinforcer": ["secondary reinforcer"],
    "eclectic approach": ["Eclectic therapy"],
    "general intelligence (g)": ["general intelligence"],
    "gestalt": ["Gestalt psychology"],
    "intelligence quotient (IQ)": ["IQ"],
    "lobotomy": ["Prefrontal lobotomy"],
    "NREM sleep": ["NREM"],
    "peer reviewers": ["Peer review"],
    "placebo": ["Placebo method"],
    "posttraumatic stress disorder (PTSD)": ["PTSD"],
    "posttraumatic growth": ["post-traumatic growth"],
    "preparedness": ["Biological preparedness"],
    "relearning": ["relearning effect"],
    "REM sleep": ["REM"],
    "survey": ["Survey method"],
    "unconditional positive regard": ["unconditional regard"],
    "variable-ratio schedule": ["variable ratio"],
    "variable-interval schedule": ["variable interval"],
    "fixed-ratio schedule": ["fixed ratio"],
    "fixed-interval schedule": ["fixed interval"],
    "withdrawal": ["Withdrawal symptoms"],
}
CONFLICTS = [
    {"negative", "positive"}, {"acute", "chronic"},
    {"secure", "insecure"}, {"nrem", "rem"},
]


def norm(value):
    value = (value or "").lower().replace("’", "'")
    value = value.replace("ﬁ", "fi").replace("ﬂ", "fl")
    value = re.sub(r"\[[^\]]*\]", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def singular(value):
    parts = value.split()
    if not parts:
        return value
    word = parts[-1]
    if word.endswith("ies") and len(word) > 4:
        word = word[:-3] + "y"
    elif word.endswith("es") and len(word) > 4:
        word = word[:-2]
    elif word.endswith("s") and len(word) > 3:
        word = word[:-1]
    parts[-1] = word
    return " ".join(parts)


def tokens(value):
    value = re.sub(r"\([^)]*\)", " ", value or "")
    words = [word for word in singular(norm(value)).split() if word not in STOP]
    return [SYNONYMS.get(word, word) for word in words]


def forms(value):
    base = norm(value)
    no_paren = norm(re.sub(r"\([^)]*\)", " ", value or ""))
    return {base, singular(base), no_paren, singular(no_paren)} - {""}


def load_myers_body():
    with open(os.path.join(os.path.dirname(MYERS), "myers_modules.json"),
              encoding="utf-8") as handle:
        modules = json.load(handle)
    with open(os.path.join(os.path.dirname(MYERS), "cache", "myers.txt"),
              encoding="utf-8", errors="replace") as handle:
        pages = handle.read().split("\f")
    page_module = {}
    for module in modules:
        for page_no in range(module["start"], module["end"] + 1):
            page_module[page_no] = module
    page_text = {page_no: norm(pages[page_no - 1])
                 for page_no in page_module}
    return modules, page_module, page_text


def term_variants(term, aliases=()):
    values = {term, re.sub(r"\([^)]*\)", " ", term or "")}
    for alias in aliases:
        values.add(alias)
        values.add(re.sub(r"\([^)]*\)", " ", alias or ""))
    out = set()
    for value in values:
        base = norm(value)
        if base:
            out.add(base)
            out.add(singular(base))
    return sorted(out, key=len, reverse=True)


def find_in_pages(term, aliases, page_text, page_module):
    patterns = [
        re.compile(r"(?<![a-z])" + re.escape(value) + r"(?![a-z])")
        for value in term_variants(term, aliases)
    ]
    for page_no in sorted(page_text):
        text = page_text[page_no]
        for pattern in patterns:
            if pattern.search(text):
                module = page_module.get(page_no)
                return page_no, module, sum(
                    len(pattern.findall(text)) for pattern in patterns
                )
    return None, None, 0


def load_barron_text():
    con = sqlite3.connect(DB)
    rows = con.execute(
        """
        SELECT s.section_id, s.path, st.text
        FROM section_texts st
        JOIN sections s ON s.section_id = st.section_id
        WHERE s.book_id='psychology-barrons-2027'
        """
    ).fetchall()
    con.close()
    return " ".join(row[2] or "" for row in rows)


def load_barron():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        """
        SELECT k.kp_id, k.name, k.name_normalized, k.section_id, s.path
        FROM knowledge_points k
        JOIN sections s ON s.section_id = k.section_id
        WHERE k.book_id='psychology-barrons-2027'
        """
    ).fetchall()
    aliases = collections.defaultdict(list)
    for row in con.execute(
        """
        SELECT a.kp_id, a.alias FROM kp_aliases a
        JOIN knowledge_points k ON k.kp_id=a.kp_id
        WHERE k.book_id='psychology-barrons-2027'
        """
    ):
        aliases[row["kp_id"]].append(row["alias"])
    kps = []
    for row in rows:
        path = row["path"] or ""
        match = re.search(r"Unit\s+(\d+)", path)
        kps.append({
            "kp_id": row["kp_id"],
            "name": row["name"],
            "name_normalized": row["name_normalized"],
            "path": path,
            "unit": match.group(1) if match else None,
            "aliases": aliases.get(row["kp_id"], []),
        })
    con.close()
    return kps


def score(myers, kp):
    my_forms = forms(myers["term"])
    my_core = re.sub(r"\([^)]*\)", " ", myers["term"])
    my_tokens = set(tokens(my_core))
    my_core_tokens = my_tokens - GENERIC
    kp_forms = forms(kp["name"])
    for alias in kp["aliases"]:
        kp_forms |= forms(alias)
    kp_tokens = set(tokens(kp["name"]))
    for alias in kp["aliases"]:
        kp_tokens |= set(tokens(alias))
    kp_core_tokens = kp_tokens - GENERIC
    best = 0.0
    method = ""
    equivalents = {norm(value) for value in
                   MANUAL_EQUIVALENTS.get(myers["term"], [])}
    conflict = any(
        (pair & my_core_tokens) and (pair & kp_core_tokens) and
        not pair <= my_core_tokens
        for pair in CONFLICTS
    )
    if my_forms & kp_forms:
        best, method = 1.0, "name_or_alias"
    elif equivalents & kp_forms:
        best, method = 0.98, "manual_equivalent"
    elif (len(my_core_tokens) >= 2 and my_core_tokens <= kp_core_tokens
          and not conflict):
        best, method = 0.95, "core_token_subset"
    else:
        for left in my_forms:
            for right in kp_forms:
                if set(tokens(left)) != set(tokens(right)):
                    continue
                ratio = difflib.SequenceMatcher(None, left, right).ratio()
                if ratio >= 0.97 and ratio > best:
                    best, method = ratio, "fuzzy"
    if (best >= 0.9 and myers.get("unit") and kp.get("unit") and
            str(myers["unit"]) == str(kp["unit"])):
        best += 0.03
    return best, method


def check_listed(text):
    checks = [
        ("Variance", ["variance"]),
        ("Regression to the mean", ["regression to the mean", "regression toward the mean"]),
        ("Operational definition", ["operational definition"]),
        ("Animism", ["animism"]),
        ("Erikson stages", ["erikson", "intimacy versus isolation", "intimacy vs. isolation"]),
        ("Overlearning", ["overlearning"]),
        ("Vicarious conditioning", ["vicarious conditioning"]),
        ("Source amnesia", ["source amnesia"]),
        ("Incentive theory", ["incentive theory", "incentive"]),
        ("Belongingness", ["belongingness", "need to belong"]),
        ("Tardive dyskinesia", ["tardive dyskinesia"]),
        ("Benzodiazepine", ["benzodiazepine"]),
        ("Sleep apnea", ["sleep apnea"]),
        ("Halo effect", ["halo effect"]),
        ("Self-perception", ["self-perception", "self perception"]),
    ]
    lines = []
    for label, needles in checks:
        lines.append((label, needles))
    return lines


def barron_structure():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    chapters = con.execute(
        """
        SELECT heading, path FROM sections
        WHERE book_id='psychology-barrons-2027' AND level=1
        ORDER BY ordinal
        """
    ).fetchall()
    con.close()
    return [dict(row) for row in chapters]


def main():
    with open(MYERS, encoding="utf-8") as handle:
        myers = json.load(handle)
    barron = load_barron()
    modules, page_module, page_text = load_myers_body()
    barron_text = norm(load_barron_text())
    chapters = barron_structure()

    results = []
    matched_barron = set()
    for entry in myers:
        scored = []
        for kp in barron:
            value, method = score(entry, kp)
            if value >= 0.9:
                scored.append((value, method, kp))
        scored.sort(key=lambda row: (-row[0], row[2]["name"]))
        best = scored[0] if scored else None
        if best:
            matched_barron.add(best[2]["kp_id"])
        barron_page, _module, _count = find_in_pages(
            entry["term"], [], page_text, page_module
        )
        results.append({
            "term": entry["term"],
            "sense": entry.get("sense") or "",
            "unit": entry.get("unit") or "",
            "module": entry.get("module_code") or "",
            "plain_en": entry.get("plain_en") or "",
            "definition": entry.get("definition") or "",
            "barron_kp": best[2]["name"] if best else "",
            "barron_kp_id": best[2]["kp_id"] if best else "",
            "match_score": round(best[0], 3) if best else "",
            "match_method": best[1] if best else "",
            "in_barron_body": bool(term_variants(entry["term"]) and any(
                re.search(r"(?<![a-z])" + re.escape(value) + r"(?![a-z])",
                          barron_text)
                for value in term_variants(entry["term"])
            )),
        })

    # Barron-only KPs, with a body-presence check inside Myers.
    barron_only = []
    for kp in barron:
        if kp["kp_id"] in matched_barron:
            continue
        page_no, module, count = find_in_pages(
            kp["name"], kp["aliases"], page_text, page_module
        )
        barron_only.append({
            **kp,
            "in_myers_body": bool(page_no),
            "myers_page": page_no,
            "myers_module": module["code"] if module else "",
            "myers_count": count,
        })

    with open(OUT, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    with open(BARRON_OUT, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "name", "path", "unit", "in_myers_body", "myers_page",
            "myers_module", "myers_count",
        ])
        writer.writeheader()
        for kp in barron_only:
            writer.writerow({
                "name": kp["name"],
                "path": kp["path"],
                "unit": kp["unit"] or "",
                "in_myers_body": int(kp["in_myers_body"]),
                "myers_page": kp["myers_page"] or "",
                "myers_module": kp["myers_module"] or "",
                "myers_count": kp["myers_count"],
            })

    exact = sum(1 for row in results if row["match_method"] == "name_or_alias")
    method_counts = collections.Counter(
        row["match_method"] for row in results if row["barron_kp"]
    )
    matched_total = sum(method_counts.values())
    unmatched = [row for row in results if not row["barron_kp"]]
    myers_only_in_barron_text = [row for row in unmatched if row["in_barron_body"]]
    truly_new = [row for row in unmatched if not row["in_barron_body"]]
    barron_only_in_myers = [kp for kp in barron_only if kp["in_myers_body"]]
    barron_absent = [kp for kp in barron_only if not kp["in_myers_body"]]

    units = ["0", "1", "2", "3", "4", "5", "EM"]
    unit_rows = []
    for unit in units:
        m_rows = [row for row in results if row["unit"] == unit]
        b_rows = [kp for kp in barron if str(kp["unit"]) == unit]
        b_only_rows = [kp for kp in barron_only if str(kp["unit"]) == unit]
        unit_rows.append({
            "unit": unit,
            "myers_all": len(m_rows),
            "myers_matched": sum(1 for row in m_rows if row["barron_kp"]),
            "myers_only": sum(1 for row in m_rows if not row["barron_kp"]),
            "myers_only_in_barron_text": sum(
                1 for row in m_rows
                if not row["barron_kp"] and row["in_barron_body"]
            ),
            "barron_all": len(b_rows),
            "barron_only": len(b_only_rows),
            "barron_only_in_myers": sum(1 for kp in b_only_rows
                                        if kp["in_myers_body"]),
        })

    with open(REPORT, "w", encoding="utf-8") as handle:
        handle.write("# Myers 4e vs Barron's 2027 — 知识点与结构对照\n\n")
        handle.write("## 1. 总量\n\n")
        handle.write(f"- Myers glossary KPs: **{len(myers)}**（原 666 个 glossary 词条，去掉 2 个重复概念，3 个多义词拆成 2 条）\n")
        handle.write(f"- Barron's KPs: **{len(barron)}**\n")
        handle.write(f"- 名称/别名精确匹配: **{exact}**\n")
        other_methods = {
            key: value for key, value in method_counts.items()
            if key != "name_or_alias"
        }
        handle.write(f"- 同义/词元匹配: **{matched_total - exact}** "
                     f"（{other_methods}）\n")
        handle.write(f"- Myers 未匹配词条: **{len(unmatched)}**"
                     f"（按严格词形搜索，其中 {len(myers_only_in_barron_text)} 条"
                     f"在 Barron 正文出现，{len(truly_new)} 条未出现）\n")
        handle.write(f"- Barron's 未被 Myers 匹配: **{len(barron_only)}**"
                     f"（按严格词形搜索，其中 {len(barron_only_in_myers)} 条 "
                     f"Myers 正文出现，{len(barron_absent)} 条未出现）\n\n")

        handle.write("## 2. 按 Unit 对照\n\n")
        handle.write("| Unit | Myers KPs | 已匹配 | Myers-only | Barron 正文提过 | "
                     "Barron KPs | Barron-only | Myers 正文有 |\n")
        handle.write("|---|---:|---:|---:|---:|---:|---:|---:|\n")
        for row in unit_rows:
            handle.write(
                f"| {row['unit']} | {row['myers_all']} | {row['myers_matched']} | "
                f"{row['myers_only']} | {row['myers_only_in_barron_text']} | "
                f"{row['barron_all']} | {row['barron_only']} | "
                f"{row['barron_only_in_myers']} |\n"
            )

        handle.write("\n## 3. Myers 新增/术语化的知识点\n\n")
        handle.write("### 3.1 Barron 正文提过、但 Barron 没有单独 KP（Myers 将其术语化）\n\n")
        for row in myers_only_in_barron_text[:80]:
            handle.write(f"- `{row['term']}`（Unit {row['unit']} / {row['module']}）\n")
        handle.write("\n### 3.2 严格词形搜索未在 Barron 正文出现（可能是新增术语或同义改写，前 100）\n\n")
        for row in truly_new[:100]:
            handle.write(f"- `{row['term']}`（Unit {row['unit']} / {row['module']}）\n")

        handle.write("\n## 4. Barron 有、Myers 未作为 glossary KP 的概念\n\n")
        handle.write("### 4.1 Myers 正文仍然讲到（概念在，只是没进 glossary）\n\n")
        for kp in barron_only_in_myers[:80]:
            handle.write(
                f"- `{kp['name']}`（{kp['path']}）→ Myers "
                f"{kp['myers_module'] or '?'} p.{kp['myers_page']}\n"
            )
        handle.write("\n### 4.2 严格词形搜索未在 Myers 正文出现（可能是 Barron 更细的考点或同义改写，前 100）\n\n")
        for kp in barron_absent[:100]:
            handle.write(f"- `{kp['name']}`（{kp['path']}）\n")

        handle.write("\n## 5. 指定的旧缺口概念\n\n")
        handle.write("| 概念 | Myers glossary | Myers 正文 | Barron KP | Barron 正文 |\n")
        handle.write("|---|---|---|---|---|\n")
        for label, needles in check_listed(None):
            glossary_hits = [
                entry["term"] for entry in myers
                if any(needle in norm(entry["term"]) for needle in needles)
            ]
            page_no, module, count = None, None, 0
            for needle in needles:
                page_no, module, count = find_in_pages(
                    needle, [], page_text, page_module
                )
                if page_no:
                    break
            barron_kp_hits = [
                kp["name"] for kp in barron
                if any(needle in norm(kp["name"]) or
                       any(needle in norm(alias) for alias in kp["aliases"])
                       for needle in needles)
            ]
            barron_body = any(
                re.search(r"(?<![a-z])" + re.escape(needle) + r"(?![a-z])",
                          barron_text)
                for needle in needles
            )
            handle.write(
                f"| {label} | "
                f"{', '.join(glossary_hits[:2]) or '—'} | "
                f"{('是（' + (module['code'] if module else '?') + '，p.' + str(page_no) + '）') if page_no else '—'} | "
                f"{', '.join(barron_kp_hits[:2]) or '—'} | "
                f"{'是' if barron_body else '—'} |\n"
            )

        handle.write("\n## 6. 单元/章节设计\n\n")
        handle.write("| Unit | Myers modules | Barron chapters |\n")
        handle.write("|---|---:|---:|\n")
        barron_by_unit = collections.Counter()
        for chapter in chapters:
            match = re.search(r"Unit\s+(\d+)", chapter["path"])
            if match:
                barron_by_unit[match.group(1)] += 1
        for unit in ["0", "1", "2", "3", "4", "5"]:
            module_count = sum(1 for module in modules if module["unit"] == unit)
            handle.write(f"| {unit} | {module_count} | {barron_by_unit.get(unit, 0)} |\n")
        handle.write(f"| EM | {sum(1 for module in modules if module['unit'] == 'EM')} | 0 |\n")
        handle.write("\n**Myers Unit 0 modules:**\n\n")
        for module in modules:
            if module["unit"] == "0":
                handle.write(f"- Module {module['code']} {module['title']}\n")
        handle.write("\n**Barron Unit 0 chapters:**\n\n")
        for chapter in chapters:
            if re.search(r"Unit\s+0", chapter["path"]):
                handle.write(f"- {chapter['heading']}\n")

    print("wrote:", OUT)
    print("wrote:", BARRON_OUT)
    print("wrote:", REPORT)
    print("myers", len(myers), "barron", len(barron),
          "exact", exact, "matched", matched_total,
          "methods", dict(method_counts),
          "myers_unmatched", len(unmatched),
          "myers_only_in_barron_text", len(myers_only_in_barron_text),
          "truly_new", len(truly_new),
          "barron_only", len(barron_only),
          "barron_only_in_myers", len(barron_only_in_myers),
          "barron_absent", len(barron_absent))
    print("unit rows:")
    for row in unit_rows:
        print(" ", row)


if __name__ == "__main__":
    main()
