#!/usr/bin/env python3
"""Merge duplicate canonical concepts created during supporting-concept expansion."""
import argparse
import collections
import os
import re
import shutil
import sqlite3
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DB = os.path.join(ROOT, "data", "content", "psychology", "psychology_knowledge.db")
REPORT = os.path.join(ROOT, "data", "content", "psychology", "reports", "knowledge", "concept_dedupe_report.md")


def norm(value):
    value = (value or "").lower().replace("’", "'")
    value = value.replace("ﬁ", "fi").replace("ﬂ", "fl")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=DB)
    args = ap.parse_args()
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = args.db + f".bak-{stamp}-before-concept-dedupe"
    shutil.copy2(args.db, backup)
    print("backup:", backup)
    con = sqlite3.connect(args.db)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    concepts = con.execute(
        "SELECT cluster_id,canonical_name,canonical_kp_id,weight,weight_tier "
        "FROM concept_clusters"
    ).fetchall()
    groups = collections.defaultdict(list)
    for concept in concepts:
        groups[norm(concept["canonical_name"])].append(concept)

    merged = []
    skipped = []
    for key, items in groups.items():
        if len(items) < 2:
            continue
        names = {item["canonical_name"] for item in items}
        # GRIT (acronym) and grit (trait) are homonyms; keep both.
        if any(name.isupper() for name in names) and any(name.islower() for name in names):
            skipped.append((key, [item["canonical_name"] for item in items], "case/acronym homonym"))
            continue
        cores = [item for item in items if item["weight_tier"] == "core"]
        if len(cores) > 1:
            skipped.append((key, [item["canonical_name"] for item in items], "multiple core concepts"))
            continue
        target = max(items, key=lambda item: (
            1 if item["weight_tier"] == "core" else 0,
            item["weight"] or 0,
        ))
        for item in items:
            if item["cluster_id"] == target["cluster_id"]:
                continue
            # Move members.
            for member in con.execute(
                "SELECT kp_id,relation,confidence,evidence FROM concept_members WHERE cluster_id=?",
                (item["cluster_id"],),
            ):
                con.execute(
                    "INSERT OR IGNORE INTO concept_members"
                    "(cluster_id,kp_id,relation,confidence,evidence) VALUES (?,?,?,?,?)",
                    (target["cluster_id"], member["kp_id"], member["relation"],
                     member["confidence"], member["evidence"]),
                )
            # Move question concept links; INSERT OR IGNORE handles unique keys.
            for link in con.execute(
                "SELECT question_id,relation_type,option_label,confidence,evidence,rationale,created_at "
                "FROM question_concept_links WHERE concept_id=?",
                (item["cluster_id"],),
            ):
                con.execute(
                    "INSERT OR IGNORE INTO question_concept_links"
                    "(question_id,concept_id,relation_type,option_label,confidence,evidence,rationale,created_at)"
                    " VALUES (?,?,?,?,?,?,?,?)",
                    (link["question_id"], target["cluster_id"], link["relation_type"],
                     link["option_label"], link["confidence"], link["evidence"],
                     link["rationale"], link["created_at"]),
                )
            con.execute("DELETE FROM question_concept_links WHERE concept_id=?",
                        (item["cluster_id"],))
            con.execute("DELETE FROM concept_members WHERE cluster_id=?",
                        (item["cluster_id"],))
            con.execute("DELETE FROM concept_clusters WHERE cluster_id=?",
                        (item["cluster_id"],))
            merged.append((item["canonical_name"], target["canonical_name"]))
        count = con.execute(
            "SELECT COUNT(*) FROM concept_members WHERE cluster_id=?",
            (target["cluster_id"],),
        ).fetchone()[0]
        con.execute("UPDATE concept_clusters SET member_count=? WHERE cluster_id=?",
                    (count, target["cluster_id"]))
    con.commit()
    print("merged:", len(merged), "skipped:", len(skipped))
    for row in merged:
        print(" ", row)
    for row in skipped:
        print(" SKIP", row)
    with open(REPORT, "w", encoding="utf-8") as handle:
        handle.write("# 概念去重\n\n")
        handle.write(f"- 合并：{len(merged)}\n")
        handle.write(f"- 跳过：{len(skipped)}\n\n")
        handle.write("## 合并\n\n")
        for source, target in merged:
            handle.write(f"- `{source}` → `{target}`\n")
        handle.write("\n## 跳过\n\n")
        for key, names, reason in skipped:
            handle.write(f"- {names}：{reason}\n")
    print("report:", REPORT)
    con.close()


if __name__ == "__main__":
    main()
