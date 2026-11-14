#!/usr/bin/env python3
"""Populate kp_aliases with safe surface forms for keyword matching.

Aliases come from three sources:
  1. rule:  the KP name, the name without parentheses, parenthetical
            alternatives, acronyms, and simple hyphen/slash variants.
  2. manual: a small reviewed dictionary for the pilot chapter (Ch11)
            and a few high-value AP Psychology variants.
  3. acronyms are marked case_sensitive so DID/CNS/CR do not match
     ordinary lowercase words such as "did".

Run after migrate_question_analysis.py (which adds kp_aliases.match_mode).
"""
import argparse
import os
import re
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DB = os.path.join(ROOT, "data", "content", "psychology", "psychology_knowledge.db")

# Reviewed variants that rules cannot derive safely.
# Keyed by knowledge_points.name_normalized.
MANUAL_ALIASES = {
    "longitudinal research": [
        "longitudinal", "longitudinal study", "longitudinal design",
    ],
    "cross sectional research": [
        "cross-sectional", "cross sectional", "cross-sectional study",
        "cross-sectional design", "cross sectional study", "cross sectional design",
    ],
    "informed consent": [
        "parental consent", "parental permission", "assent",
    ],
    "institutional review board irb": [
        "IRB", "review board",
    ],
    "rooting reflex": ["rooting"],
    "motor development": [
        "gross motor skills", "fine motor skills", "motor skills",
    ],
    "critical period": ["critical period"],
    "fluid intelligence": ["fluid intelligence"],
    "crystallized intelligence": ["crystallized intelligence"],
    "egocentric": ["egocentrism", "egocentricity"],
    "telegraphic speech": ["telegraphic speech", "telegraphic"],
    "babbling stage": ["babbling"],
    "overgeneralization": [
        "overgeneralization", "overgeneralization errors",
        "overregularization", "overregularization errors",
    ],
    "microsystem": ["microsystem"],
    "secure attachment": ["secure attachment", "securely attached"],
    "psychosocial stage theory": [
        "Erikson's psychosocial theory", "Erikson's stages", "psychosocial theory",
    ],
    "stage theories": ["stage theory", "Piaget's stages", "Piagetian stages"],
    "ecological systems theory": [
        "Bronfenbrenner's ecological model", "ecological model", "Bronfenbrenner",
    ],
}


def normalize(value):
    value = (value or "").lower().replace("’", "'").replace("‘", "'")
    value = re.sub(r"[^a-z0-9' ]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def is_acronym(value):
    token = value.strip().strip("()[],.;:")
    return bool(token) and token.isupper() and len(token) <= 6


def add(out, value, source, case_sensitive=None):
    value = (value or "").strip(" ,.;:()[]")
    norm = normalize(value)
    # Full KP names such as IQ, EQ, Id, g must survive; parenthetical
    # alternatives still need at least two characters.
    min_len = 1 if source == "rule:full" else 2
    if len(norm) < min_len:
        return
    if case_sensitive is None:
        case_sensitive = is_acronym(value)
    if norm not in out or (case_sensitive and not out[norm][1]):
        out[norm] = (value, case_sensitive, source)


def rule_variants(name):
    out = {}
    add(out, name, "rule:full")
    base = re.sub(r"\s*\([^)]*\)", "", name).strip()
    add(out, base, "rule:base")

    for match in re.finditer(r"\(([^)]*)\)", name):
        inside = match.group(1).strip()
        prefix = name[:match.start()].strip()
        suffix = name[match.end():].strip()

        or_match = re.match(r"or\s+(.+)", inside, re.I)
        if or_match:
            alt = or_match.group(1).strip()
            if suffix:
                add(out, f"{prefix} {suffix}", "rule:or")
                add(out, f"{alt} {suffix}", "rule:or")
            else:
                add(out, prefix, "rule:or")
                add(out, alt, "rule:or")
            continue

        for part in re.split(r"\s+or\s+|/|,", inside):
            part = part.strip()
            if not part:
                continue
            case = is_acronym(part)
            add(out, part, "rule:paren", case_sensitive=case)
            if suffix and case:
                add(out, f"{part} {suffix}", "rule:acronym", case_sensitive=True)
        if suffix:
            add(out, f"{base} {suffix}", "rule:base_suffix")

    # hyphen / slash variants of the base form
    variants = {name, base}
    for form in list(variants):
        if "-" in form:
            add(out, form.replace("-", " "), "rule:hyphen")
        if "/" in form:
            add(out, form.replace("/", " "), "rule:slash")
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--report", default=None)
    args = parser.parse_args()

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    columns = {row[1] for row in con.execute("PRAGMA table_info(kp_aliases)")}
    if "match_mode" not in columns:
        raise SystemExit("kp_aliases.match_mode missing; run migrate_question_analysis.py first")

    kps = con.execute(
        "SELECT kp_id, name, name_normalized FROM knowledge_points "
        "WHERE status='approved' ORDER BY name"
    ).fetchall()
    existing = {
        (row["kp_id"], row["alias_normalized"])
        for row in con.execute("SELECT kp_id, alias_normalized FROM kp_aliases")
    }

    rows = []
    per_kp = {}
    for kp in kps:
        variants = rule_variants(kp["name"])
        for alias in MANUAL_ALIASES.get(kp["name_normalized"], []):
            add(variants, alias, "manual:ch11")
        per_kp[kp["kp_id"]] = variants
        for norm, (alias, case_sensitive, source) in variants.items():
            key = (kp["kp_id"], norm)
            if key in existing:
                continue
            rows.append((
                kp["kp_id"], alias, norm, source,
                "case_sensitive" if case_sensitive else "insensitive",
            ))

    # Ambiguity report: one normalized alias pointing at several KPs.
    alias_to_kps = {}
    for kp_id, variants in per_kp.items():
        for norm in variants:
            alias_to_kps.setdefault(norm, []).append(kp_id)
    ambiguous = {
        norm: ids for norm, ids in alias_to_kps.items() if len(set(ids)) > 1
    }

    print(f"knowledge points: {len(kps)}")
    print(f"new aliases: {len(rows)}")
    print(f"ambiguous normalized aliases: {len(ambiguous)}")
    print("examples of ambiguous aliases:")
    for norm, ids in sorted(ambiguous.items())[:20]:
        names = [
            con.execute(
                "SELECT name FROM knowledge_points WHERE kp_id=?", (kid,)
            ).fetchone()[0]
            for kid in sorted(set(ids))
        ]
        print(f"  {norm!r} -> {', '.join(names)}")

    # Show the pilot chapter aliases for review.
    print("\nmanual alias samples:")
    for kp in kps:
        if kp["name_normalized"] in MANUAL_ALIASES:
            forms = sorted(per_kp[kp["kp_id"]])
            print(f"  {kp['name']}: {', '.join(forms[:8])}")

    if args.dry_run:
        con.close()
        return 0

    with con:
        con.executemany(
            "INSERT OR IGNORE INTO kp_aliases"
            "(kp_id, alias, alias_normalized, source, match_mode) "
            "VALUES (?,?,?,?,?)",
            rows,
        )
    integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
    print("\ninserted; integrity_check:", integrity)
    print("kp_aliases total:", con.execute("SELECT COUNT(*) FROM kp_aliases").fetchone()[0])
    con.close()
    return 0 if integrity == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
