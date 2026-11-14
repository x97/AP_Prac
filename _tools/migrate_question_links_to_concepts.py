#!/usr/bin/env python3
"""Migrate question_kp_links to question_concept_links.

Existing links point at Barron KPs.  KPs in the 393-concept pilot map
directly via concept_members.  For linked KPs outside the pilot, create
supporting concepts (one per name/unit group) so every existing link can be
represented at the concept layer.
"""
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
REPORT = os.path.join(ROOT, "data", "content", "psychology", "reports", "knowledge", "concept_link_migration_report.md")


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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=DB)
    parser.add_argument("--no-backup", action="store_true")
    args = parser.parse_args()

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    if not args.no_backup:
        backup = args.db + f".bak-{stamp}-before-concept-link-migration"
        shutil.copy2(args.db, backup)
        print("backup:", backup)

    con = sqlite3.connect(args.db)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS question_concept_links (
            link_id INTEGER PRIMARY KEY,
            question_id TEXT NOT NULL,
            concept_id TEXT NOT NULL REFERENCES concept_clusters(cluster_id) ON DELETE CASCADE,
            relation_type TEXT NOT NULL CHECK (relation_type IN ('core','supporting','confusable')),
            option_label TEXT,
            confidence REAL,
            evidence TEXT,
            rationale TEXT,
            created_at TEXT NOT NULL,
            CHECK (relation_type <> 'confusable' OR option_label IS NOT NULL)
        )
        """
    )
    con.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_qconcept "
        "ON question_concept_links(question_id,concept_id,relation_type,IFNULL(option_label,''))"
    )
    con.execute(
        "CREATE INDEX IF NOT EXISTS ix_qconcept_q "
        "ON question_concept_links(question_id,relation_type)"
    )
    con.execute(
        "CREATE INDEX IF NOT EXISTS ix_qconcept_c "
        "ON question_concept_links(concept_id)"
    )

    kp_meta = {}
    for row in con.execute(
        """
        SELECT k.kp_id, k.book_id, k.name, k.name_normalized, k.section_id,
               s.path, k.weight, k.weight_tier, k.definition_quote
        FROM knowledge_points k
        JOIN sections s ON s.section_id = k.section_id
        """
    ):
        match = re.search(r"Unit\s+(\d+)", row["path"] or "")
        kp_meta[row["kp_id"]] = {
            "kp_id": row["kp_id"],
            "book_id": row["book_id"],
            "name": row["name"],
            "name_norm": norm_name(row["name"]),
            "section_id": row["section_id"],
            "path": row["path"] or "",
            "unit": match.group(1) if match else "EM",
            "weight": row["weight"] or 0,
            "weight_tier": row["weight_tier"] or "supporting",
            "definition": row["definition_quote"] or "",
        }

    # Existing concept names and member names.
    concept_names = {}
    member_names = collections.defaultdict(set)
    for row in con.execute(
        """
        SELECT c.cluster_id, c.canonical_name, c.ap_unit, c.weight,
               c.weight_tier, c.canonical_kp_id
        FROM concept_clusters c
        """
    ):
        concept_names[row["canonical_name"]] = row
    for row in con.execute(
        """
        SELECT m.cluster_id, k.name, k.kp_id, s.path
        FROM concept_members m
        JOIN knowledge_points k ON k.kp_id=m.kp_id
        JOIN sections s ON s.section_id=k.section_id
        """
    ):
        match = re.search(r"Unit\s+(\d+)", row["path"] or "")
        member_names[(row["name"], match.group(1) if match else "EM")].add(row["cluster_id"])

    linked_kps = [
        row["kp_id"] for row in con.execute(
            "SELECT DISTINCT kp_id FROM question_kp_links"
        )
    ]
    all_kps = [row["kp_id"] for row in con.execute("SELECT kp_id FROM knowledge_points")]
    mapped_kps = {
        row["kp_id"] for row in con.execute("SELECT kp_id FROM concept_members")
    }
    unmapped = [kp_id for kp_id in all_kps if kp_id not in mapped_kps]
    print("all KPs:", len(all_kps), "linked KPs:", len(linked_kps),
          "unmapped:", len(unmapped))

    # Group unmapped KPs by name/unit; reuse an existing concept when the
    # exact name/unit already exists as a member.
    groups = collections.defaultdict(list)
    reused = 0
    for kp_id in unmapped:
        meta = kp_meta.get(kp_id)
        if not meta:
            continue
        existing = member_names.get((meta["name"], meta["unit"]))
        if existing:
            # Reuse the first matching concept rather than creating a duplicate.
            cluster_id = sorted(existing)[0]
            con.execute(
                "INSERT OR IGNORE INTO concept_members"
                "(cluster_id,kp_id,relation,confidence,evidence) VALUES (?,?,?,?,?)",
                (cluster_id, kp_id, "related", 1.0,
                 "legacy question link; name/unit match"),
            )
            reused += 1
            continue
        key = (meta["name"], meta["unit"])
        groups[key].append(meta)

    created = []
    used_names = set(concept_names)
    for (name, unit), members in groups.items():
        canonical = name
        if canonical in used_names:
            canonical = f"{name} (Unit {unit})"
        suffix = 1
        while canonical in used_names:
            suffix += 1
            canonical = f"{name} (Unit {unit}, {suffix})"
        used_names.add(canonical)
        cluster_id = "psy-support-" + sha1(f"{canonical}|{unit}")
        weight = max((member["weight"] or 0) for member in members)
        con.execute(
            """
            INSERT INTO concept_clusters
            (cluster_id,subject_id,canonical_name,canonical_kp_id,description,
             ap_unit,topic,status,weight,weight_tier,member_count)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """,
            (cluster_id, "psychology", canonical, members[0]["kp_id"],
             None, unit, members[0]["path"].split(">")[-1].strip(),
             "supporting", weight, "supporting", len(members)),
        )
        for member in members:
            con.execute(
                "INSERT OR IGNORE INTO concept_members"
                "(cluster_id,kp_id,relation,confidence,evidence) VALUES (?,?,?,?,?)",
                (cluster_id, member["kp_id"], "exact", 1.0,
                 "supporting concept for legacy question link"),
            )
        created.append((cluster_id, canonical, unit, len(members), weight))

    print("supporting concepts created:", len(created), "reused:", reused)

    # Rebuild the concept link table from the legacy KP links.
    con.execute("DELETE FROM question_concept_links")
    kp_to_concepts = collections.defaultdict(list)
    for row in con.execute("SELECT kp_id, cluster_id FROM concept_members"):
        kp_to_concepts[row["kp_id"]].append(row["cluster_id"])
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    aggregate = {}
    for row in con.execute(
        "SELECT question_id,kp_id,relation_type,option_label,confidence,evidence,rationale "
        "FROM question_kp_links"
    ):
        for concept_id in kp_to_concepts.get(row["kp_id"], []):
            key = (row["question_id"], concept_id, row["relation_type"],
                   row["option_label"])
            entry = aggregate.get(key)
            if entry is None:
                aggregate[key] = {
                    "confidence": row["confidence"] or 0,
                    "evidence": [row["evidence"]] if row["evidence"] else [],
                    "rationale": row["rationale"] or "",
                }
            else:
                entry["confidence"] = max(entry["confidence"], row["confidence"] or 0)
                if row["evidence"] and row["evidence"] not in entry["evidence"]:
                    entry["evidence"].append(row["evidence"])
                if row["rationale"] and not entry["rationale"]:
                    entry["rationale"] = row["rationale"]
    for (question_id, concept_id, relation, option_label), entry in aggregate.items():
        con.execute(
            """
            INSERT OR IGNORE INTO question_concept_links
            (question_id,concept_id,relation_type,option_label,confidence,
             evidence,rationale,created_at)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            (question_id, concept_id, relation, option_label,
             entry["confidence"], " | ".join(entry["evidence"])[:1000],
             entry["rationale"][:1000], now),
        )
    con.commit()

    coverage = con.execute(
        """
        SELECT COUNT(*) links, COUNT(DISTINCT question_id) questions,
               COUNT(DISTINCT concept_id) concepts
        FROM question_concept_links
        """
    ).fetchone()
    integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
    fk = con.execute("PRAGMA foreign_key_check").fetchall()

    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    with open(REPORT, "w", encoding="utf-8") as handle:
        handle.write("# 题目关联迁移到概念层\n\n")
        handle.write(f"- Legacy question_kp_links: 7,370（保留）\n")
        handle.write(f"- all KPs: {len(all_kps)}\n")
        handle.write(f"- linked KPs: {len(linked_kps)}\n")
        handle.write(f"- 已在概念层: {len(all_kps) - len(unmapped)}\n")
        handle.write(f"- 未命中、复用同名概念: {reused}\n")
        handle.write(f"- 新建 supporting 概念: {len(created)}\n")
        handle.write(f"- question_concept_links: {coverage['links']} 条 / "
                     f"{coverage['questions']} 题 / {coverage['concepts']} 概念\n")
        handle.write("- 题目总数校验需在 psychology_exam.db 侧执行；本报告只统计已有概念链接。\n")
        handle.write(f"- integrity: {integrity}\n")
        handle.write(f"- foreign_key_check: {'OK' if not fk else 'FAIL'}\n\n")
        handle.write("## 新建 supporting 概念（前 50）\n\n")
        for cluster_id, name, unit, count, weight in created[:50]:
            handle.write(f"- `{name}`（Unit {unit}，{count} KP，权重 {weight:.1f}）\n")
    print("question_concept_links:", dict(coverage))
    print("integrity:", integrity, "fk:", "OK" if not fk else fk[:3])
    print("report:", REPORT)
    con.close()


if __name__ == "__main__":
    main()
