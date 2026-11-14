#!/usr/bin/env python3
"""Validate the 102-section knowledge extraction JSON files.

Checks coverage against data/content/psychology/extraction/sections/sections_text.json, verbatim quotes,
subheading coverage, and the 20-character plain-language limit.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECTIONS = os.path.join(ROOT, "data", "content", "psychology", "extraction", "sections", "sections_text.json")
EXTRACT_DIR = os.path.join(ROOT, "data", "content", "psychology", "extraction")
OUT = os.path.join(ROOT, "data", "content", "psychology", "extraction", "validation_report.txt")

HAN = re.compile(r"[一-鿿]")


def squash(text: str) -> str:
    return re.sub(r"\s+", "", text)


def main() -> int:
    master = json.load(open(SECTIONS, encoding="utf-8"))
    expected = {(s["chapter"], s["section"]): s for s in master}
    issues = []
    all_sections = []
    total_kps = 0

    for unit in range(6):
        path = os.path.join(EXTRACT_DIR, f"unit{unit}.json")
        if not os.path.exists(path):
            issues.append(f"unit{unit}: file missing")
            continue
        try:
            data = json.load(open(path, encoding="utf-8"))
        except Exception as exc:
            issues.append(f"unit{unit}: invalid JSON: {exc}")
            continue
        if data.get("unit") != unit:
            issues.append(f"unit{unit}: unit field is {data.get('unit')!r}")
        seen = set()
        for sec in data.get("sections", []):
            key = (sec.get("chapter"), sec.get("section"))
            if key not in expected:
                issues.append(f"unit{unit}: unexpected section {key}")
                continue
            if key in seen:
                issues.append(f"unit{unit}: duplicate section {key}")
            seen.add(key)
            src = expected[key]
            all_sections.append(sec)
            if sec.get("page") != src["page"]:
                issues.append(
                    f"Ch{key[0]} {key[1]}: page {sec.get('page')} != {src['page']}"
                )
            kps = sec.get("knowledge_points") or []
            if not kps:
                issues.append(f"Ch{key[0]} {key[1]}: no knowledge points")
            sub_names = [h["text"] for h in src["subs"]]
            covered = set()
            names = set()
            for i, kp in enumerate(kps, 1):
                total_kps += 1
                label = f"Ch{key[0]} {key[1]} KP{i} ({kp.get('name','?')})"
                name = (kp.get("name") or "").strip()
                sub = (kp.get("subheading") or "").strip()
                quote = (kp.get("definition_quote") or "").strip()
                researchers = (kp.get("researchers") or "").strip()
                plain = (kp.get("plain") or "").strip()
                if not name:
                    issues.append(f"{label}: empty name")
                if name in names:
                    issues.append(f"{label}: duplicate name in section")
                names.add(name)
                if sub and sub not in sub_names:
                    issues.append(f"{label}: subheading {sub!r} not in section")
                if sub:
                    covered.add(sub)
                if not quote:
                    issues.append(f"{label}: empty quote")
                elif squash(quote) not in squash(src["text"]):
                    issues.append(f"{label}: quote not verbatim in section text")
                if not researchers:
                    issues.append(f"{label}: empty researchers")
                if not plain:
                    issues.append(f"{label}: empty plain")
                else:
                    han = len(HAN.findall(plain))
                    if han > 20:
                        issues.append(f"{label}: plain has {han} Chinese chars (>20)")
                    if len(plain) > 40:
                        issues.append(f"{label}: plain is unusually long ({len(plain)} chars)")
            missing_subs = [s for s in sub_names if s not in covered]
            if missing_subs:
                issues.append(
                    f"Ch{key[0]} {key[1]}: subheadings not covered: {missing_subs}"
                )
        # report missing sections for this unit
        unit_expected = [k for k in expected if expected[k]["unit"] == unit]
        for key in unit_expected:
            if key not in seen:
                issues.append(f"unit{unit}: missing section {key}")

    if len(all_sections) != len(expected):
        issues.append(
            f"total sections {len(all_sections)} != expected {len(expected)}"
        )

    lines = [
        f"sections: {len(all_sections)}/{len(expected)}",
        f"knowledge points: {total_kps}",
        f"issues: {len(issues)}",
        "",
    ]
    lines.extend(issues)
    report = "\n".join(lines)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8").write(report + "\n")
    print(report)
    return 0 if not issues else 1


if __name__ == "__main__":
    sys.exit(main())
