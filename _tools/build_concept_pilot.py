#!/usr/bin/env python3
"""Build a 300–400 concept pilot from the Barron/Myers KP matches.

Layer 1 stays in knowledge_points.  This script creates the canonical
concept layer (concept_clusters + concept_members) and assigns every KP a
0–100 weight and a tier (core / supporting).

Weight is intentionally explainable:
  base 10
  + 25 both books
  + 30 * sqrt(core_question_count / 38)
  +  5 * sqrt(supporting_question_count / 29)
  +  5 * sqrt(confusable_question_count / 44)
  + 10 if the concept has a Myers glossary KP
  +  5 if it belongs to AP Unit 0–5
  +  5 if the canonical source has a definition
"""
import argparse
import collections
import csv
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
COMPARE = os.path.join(ROOT, "data", "content", "psychology", "extraction", "myers", "myers_vs_barrons.csv")
OUT = os.path.join(ROOT, "data", "content", "psychology", "reports", "knowledge", "concept_pilot_report.md")
CONCEPT_CSV = os.path.join(ROOT, "data", "content", "psychology", "reports", "knowledge", "concept_pilot.csv")
WEIGHT_CSV = os.path.join(ROOT, "data", "content", "psychology", "reports", "knowledge", "kp_weights.csv")

MYERS_BOOK = "psychology-myers-2024"
BARRON_BOOK = "psychology-barrons-2027"
MAX_CORE = 38
MAX_SUPPORT = 29
MAX_CONF = 44

SENSE_LABELS = {
    ("accommodation", "1"): "Accommodation (sensory)",
    ("accommodation", "3"): "Accommodation (developmental)",
    ("discrimination", "3"): "Discrimination (conditioning)",
    ("discrimination", "4"): "Discrimination (social)",
    ("psychoanalysis", "4"): "Psychoanalysis (theory)",
    ("psychoanalysis", "5"): "Psychoanalysis (therapy)",
}


def norm_name(value):
    value = (value or "").lower().replace("’", "'")
    value = value.replace("ﬁ", "fi").replace("ﬂ", "fl")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def sha1(value):
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:16]


def add_column(con, table, column, ddl):
    names = {row[1] for row in con.execute(f"PRAGMA table_info({table})")}
    if column not in names:
        con.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


def ensure_schema(con):
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS concept_members (
            cluster_id TEXT NOT NULL REFERENCES concept_clusters(cluster_id) ON DELETE CASCADE,
            kp_id TEXT NOT NULL REFERENCES knowledge_points(kp_id) ON DELETE CASCADE,
            relation TEXT NOT NULL CHECK (relation IN ('exact','broad','narrow','related')),
            confidence REAL,
            evidence TEXT,
            PRIMARY KEY (cluster_id, kp_id)
        )
        """
    )
    con.execute("CREATE INDEX IF NOT EXISTS ix_concept_members_kp ON concept_members(kp_id)")
    for column, ddl in [
        ("ap_unit", "TEXT"), ("topic", "TEXT"),
        ("status", "TEXT DEFAULT 'candidate'"),
        ("weight", "REAL DEFAULT 0"),
        ("weight_tier", "TEXT"),
        ("member_count", "INTEGER DEFAULT 0"),
    ]:
        add_column(con, "concept_clusters", column, ddl)
    for column, ddl in [
        ("weight", "REAL DEFAULT 0"),
        ("weight_tier", "TEXT"),
        ("weight_reason", "TEXT"),
    ]:
        add_column(con, "knowledge_points", column, ddl)


def load_barron(con):
    rows = con.execute(
        """
        SELECT k.kp_id, k.name, k.section_id, s.path,
               k.definition_quote, k.plain_en
        FROM knowledge_points k
        JOIN sections s ON s.section_id = k.section_id
        WHERE k.book_id=?
        """,
        (BARRON_BOOK,),
    ).fetchall()
    out = {}
    for row in rows:
        match = re.search(r"Unit\s+(\d+)", row["path"] or "")
        out[row["kp_id"]] = {
            "kp_id": row["kp_id"],
            "name": row["name"],
            "section_id": row["section_id"],
            "path": row["path"] or "",
            "unit": match.group(1) if match else None,
            "definition": row["definition_quote"] or "",
            "plain_en": row["plain_en"] or "",
        }
    return out


def myers_section_id(row):
    unit = row["unit"]
    module = row["module"]
    return f"{MYERS_BOOK}-u{unit}-m{module.replace('.', '-')}"


def load_myers_kps(con):
    rows = con.execute(
        """
        SELECT kp_id, name, name_normalized, section_id
        FROM knowledge_points WHERE book_id=?
        """,
        (MYERS_BOOK,),
    ).fetchall()
    by_key = {}
    for row in rows:
        by_key[(row["section_id"], row["name_normalized"])] = row["kp_id"]
    return by_key


def question_counts(con):
    counts = collections.defaultdict(lambda: collections.Counter())
    for row in con.execute(
        "SELECT kp_id, relation_type, COUNT(*) n FROM question_kp_links GROUP BY kp_id, relation_type"
    ):
        counts[row["kp_id"]][row["relation_type"]] = row["n"]
    return counts


def weight_for(cross_book, qcore, qsup, qconf, myers_glossary, ap_unit, has_definition):
    return round(min(100.0,
        10.0
        + (25.0 if cross_book else 0.0)
        + 30.0 * (max(0, qcore) / MAX_CORE) ** 0.5
        + 5.0 * (max(0, qsup) / MAX_SUPPORT) ** 0.5
        + 5.0 * (max(0, qconf) / MAX_CONF) ** 0.5
        + (10.0 if myers_glossary else 0.0)
        + (5.0 if ap_unit else 0.0)
        + (5.0 if has_definition else 0.0)
    ), 2)


def tier_for(weight):
    if weight >= 65:
        return "core"
    if weight >= 50:
        return "supporting"
    return "micro"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=DB)
    parser.add_argument("--compare", default=COMPARE)
    parser.add_argument("--out", default=OUT)
    parser.add_argument("--no-backup", action="store_true")
    args = parser.parse_args()

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    if not args.no_backup:
        backup = args.db + f".bak-{stamp}-before-concept-pilot"
        shutil.copy2(args.db, backup)
        print("backup:", backup)

    con = sqlite3.connect(args.db)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    ensure_schema(con)

    barron = load_barron(con)
    myers = load_myers_kps(con)
    qcounts = question_counts(con)

    with open(args.compare, encoding="utf-8-sig") as handle:
        rows = [row for row in csv.DictReader(handle) if row["barron_kp_id"]]
    print("matched Myers rows:", len(rows))

    groups = collections.defaultdict(list)
    for row in rows:
        groups[row["barron_kp_id"]].append(row)

    # Psychoanalysis has two Myers senses but only one Barron KP. Split the
    # theory sense into its own single-book concept so the definitions do not
    # get conflated.
    split_groups = []
    for barron_id, members in groups.items():
        senses = {member["sense"] for member in members if member["sense"]}
        if len(members) > 1 and len(senses) > 1:
            barron_info = barron.get(barron_id)
            for member in members:
                keep_barron = (
                    barron_info and str(barron_info["unit"]) == str(member["unit"])
                )
                split_groups.append(
                    (barron_id if keep_barron else None, barron_info if keep_barron else None,
                     [member])
                )
        else:
            split_groups.append((barron_id, barron.get(barron_id), members))

    name_counts = collections.Counter()
    for _barron_id, barron_info, _members in split_groups:
        if barron_info:
            name_counts[barron_info["name"]] += 1

    concepts = []
    used_names = set()
    for barron_id, barron_info, members in split_groups:
        myers_units = [member["unit"] for member in members]
        unit = barron_info["unit"] if barron_info else myers_units[0]
        base_name = barron_info["name"] if barron_info else members[0]["term"]
        canonical = None
        if len(members) == 1 and members[0]["sense"]:
            canonical = SENSE_LABELS.get((base_name.lower(), unit))
        if not canonical and name_counts[base_name] > 1:
            canonical = SENSE_LABELS.get((base_name.lower(), unit))
        if not canonical:
            canonical = base_name
        if canonical in used_names:
            canonical = f"{canonical} (Unit {unit})"
        used_names.add(canonical)

        myers_kp_ids = []
        for member in members:
            section_id = myers_section_id(member)
            kp_id = myers.get((section_id, norm_name(member["term"])))
            if kp_id:
                myers_kp_ids.append((kp_id, member))
        canonical_kp_id = barron_id or (myers_kp_ids[0][0] if myers_kp_ids else None)
        cross_book = bool(barron_info and myers_kp_ids)
        has_definition = bool(
            (barron_info and barron_info["definition"]) or
            (myers_kp_ids and True)
        )
        myers_glossary = bool(myers_kp_ids)
        q = collections.Counter()
        if barron_info:
            q.update(qcounts.get(barron_id, {}))
        weight = weight_for(
            cross_book, q["core"], q["supporting"], q["confusable"],
            myers_glossary, unit in {"0", "1", "2", "3", "4", "5"},
            has_definition,
        )
        concept_id = "psy-concept-" + sha1(f"{canonical}|{unit or ''}")
        concepts.append({
            "cluster_id": concept_id,
            "canonical_name": canonical,
            "canonical_kp_id": canonical_kp_id,
            "unit": unit,
            "topic": (barron_info["path"].split(">")[-1].strip()
                      if barron_info else members[0].get("module")),
            "status": "approved" if cross_book else "needs_review",
            "weight": weight,
            "tier": "core" if cross_book else "supporting",
            "cross_book": cross_book,
            "myers_glossary": myers_glossary,
            "qcore": q["core"],
            "qsup": q["supporting"],
            "qconf": q["confusable"],
            "barron_id": barron_id,
            "myers": myers_kp_ids,
            "members": members,
        })

    con.execute("DELETE FROM concept_members")
    con.execute("DELETE FROM concept_clusters WHERE cluster_id LIKE 'psy-concept-%'")
    for concept in concepts:
        con.execute(
            """
            INSERT INTO concept_clusters
            (cluster_id, subject_id, canonical_name, canonical_kp_id, description,
             ap_unit, topic, status, weight, weight_tier, member_count)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                concept["cluster_id"], "psychology", concept["canonical_name"],
                concept["canonical_kp_id"], None, concept["unit"], concept["topic"],
                concept["status"], concept["weight"], concept["tier"],
                1 + len(concept["myers"]),
            ),
        )
        if concept["barron_id"]:
            con.execute(
                """
                INSERT INTO concept_members
                (cluster_id, kp_id, relation, confidence, evidence)
                VALUES (?,?,?,?,?)
                """,
                (concept["cluster_id"], concept["barron_id"], "exact", 1.0,
                 "Barron canonical source"),
            )
        for kp_id, member in concept["myers"]:
            relation = "related" if member.get("match_method") == "core_token_subset" else "exact"
            con.execute(
                """
                INSERT INTO concept_members
                (cluster_id, kp_id, relation, confidence, evidence)
                VALUES (?,?,?,?,?)
                """,
                (concept["cluster_id"], kp_id, relation,
                 float(member.get("match_score") or 0) or None,
                 member.get("match_method") or "matched"),
            )

    # Weight every KP. KPs in the pilot inherit the concept weight; the
    # canonical source gets a small bump, and unmatched KPs get an individual
    # weight from cross-book/body/question signals.
    member_weight = {}
    member_tier = {}
    for concept in concepts:
        member_weight[concept["barron_id"]] = concept["weight"]
        member_tier[concept["barron_id"]] = concept["tier"]
        for kp_id, _member in concept["myers"]:
            member_weight[kp_id] = concept["weight"]
            member_tier[kp_id] = concept["tier"]

    kp_meta = {}
    for row in con.execute(
        """
        SELECT k.kp_id, k.book_id, k.name, k.section_id, s.path
        FROM knowledge_points k
        JOIN sections s ON s.section_id = k.section_id
        """
    ):
        match = re.search(r"Unit\s+(\d+)", row["path"] or "")
        kp_meta[row["kp_id"]] = {
            "book_id": row["book_id"],
            "name": row["name"],
            "name_norm": norm_name(row["name"]),
            "unit": match.group(1) if match else "EM",
        }

    # Barron has some duplicate KPs with the same name/unit (e.g. Mere
    # exposure effect). They should inherit the concept weight instead of
    # falling back to the low unmatched weight.
    name_unit_concept = {}
    name_concepts = collections.defaultdict(dict)
    for concept in concepts:
        member_ids = ([concept["barron_id"]] if concept["barron_id"] else []) + [
            kp_id for kp_id, _member in concept["myers"]
        ]
        for kp_id in member_ids:
            meta = kp_meta.get(kp_id)
            if not meta:
                continue
            key = (meta["name_norm"], meta["unit"])
            current = name_unit_concept.get(key)
            if current is None or concept["weight"] > current[0]:
                name_unit_concept[key] = (
                    concept["weight"], concept["tier"], concept["canonical_name"]
                )
            name_concepts[meta["name_norm"]][concept["cluster_id"]] = (
                concept["weight"], concept["tier"], concept["canonical_name"]
            )

    for kp_id, meta in kp_meta.items():
        if kp_id in member_weight:
            weight = min(100.0, member_weight[kp_id] + 2.0)
            tier = member_tier.get(kp_id, "supporting")
            reason = {"source": "concept_member", "concept_tier": tier}
        else:
            inherited = name_unit_concept.get((meta["name_norm"], meta["unit"]))
            options = name_concepts.get(meta["name_norm"], {})
            if not inherited and len(options) == 1:
                inherited = next(iter(options.values()))
            if inherited:
                weight, tier, concept_name = inherited
                reason = {"source": "same_name_duplicate",
                          "concept": concept_name}
            else:
                q = qcounts.get(kp_id, collections.Counter())
                is_myers = meta["book_id"] == MYERS_BOOK
                weight = weight_for(
                    False, q["core"], q["supporting"], q["confusable"],
                    is_myers, True, True,
                )
                tier = "supporting"
                reason = {"source": "individual", "book": meta["book_id"]}
        con.execute(
            "UPDATE knowledge_points SET weight=?, weight_tier=?, weight_reason=? WHERE kp_id=?",
            (round(weight, 2), tier, json.dumps(reason, ensure_ascii=False), kp_id),
        )

    con.commit()
    integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
    fk = con.execute("PRAGMA foreign_key_check").fetchall()
    print(f"concepts: {len(concepts)}; integrity={integrity}; fk={'OK' if not fk else fk[:3]}")

    tiers = collections.Counter(concept["tier"] for concept in concepts)
    kp_tiers = collections.Counter(
        row[0] for row in con.execute(
            "SELECT weight_tier FROM knowledge_points WHERE book_id IN (?,?)",
            (BARRON_BOOK, MYERS_BOOK),
        )
    )
    top = sorted(concepts, key=lambda concept: -concept["weight"])
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        handle.write("# 核心概念 pilot（Barron × Myers）\n\n")
        handle.write(f"- 规范概念：{len(concepts)}\n")
        handle.write(f"- Tier 分布：{dict(tiers)}\n")
        handle.write(f"- 概念权重 ≥70：{sum(1 for c in concepts if c['weight'] >= 70)}；"
                     f"≥65：{sum(1 for c in concepts if c['weight'] >= 65)}\n")
        handle.write(f"- KP 权重分布（两本书）：{dict(kp_tiers)}\n")
        handle.write(f"- 权重公式：base 10 + both books 25 + core 题目 30√ + "
                     f"supporting 5√ + confusable 5√ + Myers glossary 10 + "
                     f"AP Unit 5 + definition 5\n")
        handle.write(f"- 校验：integrity={integrity}，foreign_key="
                     f"{'OK' if not fk else 'FAIL'}\n\n")
        handle.write("## 权重最高的 60 个概念\n\n")
        handle.write("| # | 概念 | Unit | 权重 | Tier | core题 | 来源 |\n")
        handle.write("|---:|---|---:|---:|---|---:|---|\n")
        for index, concept in enumerate(top[:60], 1):
            sources = ("B+M" if concept["cross_book"] else
                       ("M" if concept["myers"] else "B"))
            handle.write(
                f"| {index} | {concept['canonical_name']} | {concept['unit']} | "
                f"{concept['weight']:.1f} | {concept['tier']} | "
                f"{concept['qcore']} | {sources} |\n"
            )
        handle.write("\n## 权重最低的 30 个 pilot 概念\n\n")
        for concept in sorted(concepts, key=lambda item: item["weight"])[:30]:
            handle.write(
                f"- {concept['canonical_name']}（Unit {concept['unit']}，"
                f"{concept['weight']:.1f}，{concept['tier']}）\n"
            )
    with open(CONCEPT_CSV, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "cluster_id", "canonical_name", "unit", "topic", "weight",
            "tier", "qcore", "qsup", "qconf", "cross_book",
            "barron_kp_id", "myers_kp_ids",
        ])
        writer.writeheader()
        for concept in sorted(concepts, key=lambda item: -item["weight"]):
            writer.writerow({
                "cluster_id": concept["cluster_id"],
                "canonical_name": concept["canonical_name"],
                "unit": concept["unit"],
                "topic": concept["topic"] or "",
                "weight": concept["weight"],
                "tier": concept["tier"],
                "qcore": concept["qcore"],
                "qsup": concept["qsup"],
                "qconf": concept["qconf"],
                "cross_book": int(concept["cross_book"]),
                "barron_kp_id": concept["barron_id"] or "",
                "myers_kp_ids": ",".join(kp_id for kp_id, _member in concept["myers"]),
            })
    with open(WEIGHT_CSV, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["kp_id", "book_id", "name", "weight", "weight_tier", "weight_reason"])
        for row in con.execute(
            "SELECT kp_id, book_id, name, weight, weight_tier, weight_reason "
            "FROM knowledge_points ORDER BY weight DESC, book_id, name"
        ):
            writer.writerow(list(row))
    print("report:", args.out)
    print("concept csv:", CONCEPT_CSV)
    print("weight csv:", WEIGHT_CSV)
    con.close()


if __name__ == "__main__":
    main()
