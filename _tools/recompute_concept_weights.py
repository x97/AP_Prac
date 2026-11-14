#!/usr/bin/env python3
"""Recompute concept and KP weights from question_concept_links.

cross_book is based on distinct books.book_family_id, so editions of the
same textbook (2027/2028) do not double-count as independent books.
"""
import argparse
import collections
import json
import math
import os
import shutil
import sqlite3
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DB = os.path.join(ROOT, "data", "content", "psychology", "psychology_knowledge.db")
REPORT = os.path.join(ROOT, "data", "content", "psychology", "reports", "knowledge", "concept_weight_report.md")
CONCEPT_CSV = os.path.join(ROOT, "data", "content", "psychology", "reports", "knowledge", "concept_weights_final.csv")
KP_CSV = os.path.join(ROOT, "data", "content", "psychology", "reports", "knowledge", "kp_weights_final.csv")


def weight_for(cross_book, qcore, qsup, qconf, myers, ap_unit, definition,
               max_core, max_sup, max_conf):
    return round(min(100.0,
        10.0
        + (25.0 if cross_book else 0.0)
        + 30.0 * (qcore / max_core) ** 0.5
        + 5.0 * (qsup / max_sup) ** 0.5
        + 5.0 * (qconf / max_conf) ** 0.5
        + (10.0 if myers else 0.0)
        + (5.0 if ap_unit else 0.0)
        + (5.0 if definition else 0.0)
    ), 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=DB)
    ap.add_argument("--no-backup", action="store_true")
    args = ap.parse_args()
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    if not args.no_backup:
        backup = args.db + f".bak-{stamp}-before-weight-recompute"
        shutil.copy2(args.db, backup)
        print("backup:", backup)

    con = sqlite3.connect(args.db)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")

    counts = collections.defaultdict(collections.Counter)
    for row in con.execute(
        "SELECT concept_id, relation_type, COUNT(*) n "
        "FROM question_concept_links GROUP BY concept_id, relation_type"
    ):
        counts[row["concept_id"]][row["relation_type"]] = row["n"]
    max_core = max((c["core"] for c in counts.values()), default=1) or 1
    max_sup = max((c["supporting"] for c in counts.values()), default=1) or 1
    max_conf = max((c["confusable"] for c in counts.values()), default=1) or 1

    concepts = con.execute(
        """
        SELECT c.cluster_id, c.canonical_name, c.canonical_kp_id,
               c.ap_unit, c.weight_tier,
               COUNT(DISTINCT COALESCE(b.book_family_id, k.book_id)) book_families,
               COUNT(DISTINCT k.book_id) book_count,
               COUNT(DISTINCT k.kp_id) member_kps,
               COUNT(DISTINCT CASE WHEN k.book_id LIKE 'psychology-myers-%'
                                   THEN k.kp_id END) myers,
               MAX(CASE WHEN k.kp_id=c.canonical_kp_id
                        AND k.definition_quote IS NOT NULL
                        AND TRIM(k.definition_quote)<>'' THEN 1 ELSE 0 END) has_def
        FROM concept_clusters c
        LEFT JOIN concept_members m ON m.cluster_id=c.cluster_id
        LEFT JOIN knowledge_points k ON k.kp_id=m.kp_id
        LEFT JOIN books b ON b.book_id=k.book_id
        GROUP BY c.cluster_id
        """
    ).fetchall()
    updated = 0
    top = []
    for concept in concepts:
        q = counts.get(concept["cluster_id"], collections.Counter())
        cross = (concept["book_families"] or 0) >= 2
        tier = "core" if cross else "supporting"
        weight = weight_for(
            cross, q["core"], q["supporting"], q["confusable"],
            bool(concept["myers"]), concept["ap_unit"] in {"0", "1", "2", "3", "4", "5"},
            bool(concept["has_def"]), max_core, max_sup, max_conf,
        )
        con.execute(
            "UPDATE concept_clusters SET weight=?, weight_tier=?, member_count=? "
            "WHERE cluster_id=?",
            (weight, tier, concept["member_kps"] or 0, concept["cluster_id"]),
        )
        updated += 1
        top.append((weight, concept["canonical_name"], concept["ap_unit"], tier,
                    q["core"], q["supporting"], q["confusable"]))
        concept_weight = weight
        concept_tier = tier
        con.execute(
            """
            UPDATE knowledge_points SET weight=?, weight_tier=?, weight_reason=?
            WHERE kp_id IN (SELECT kp_id FROM concept_members WHERE cluster_id=?)
            """,
            (concept_weight,
             concept_tier,
             json.dumps({"source": "concept_member", "concept": concept["canonical_name"],
                         "concept_weight": concept_weight,
                         "qcore": q["core"], "qsup": q["supporting"],
                         "qconf": q["confusable"], "tier": concept_tier,
                         "book_families": concept["book_families"],
                         "book_count": concept["book_count"],
                         "member_kps": concept["member_kps"]},
                        ensure_ascii=False),
             concept["cluster_id"]),
        )
        if concept["canonical_kp_id"]:
            con.execute(
                "UPDATE knowledge_points SET weight=MIN(100.0, weight+2.0) WHERE kp_id=?",
                (concept["canonical_kp_id"],),
            )
    con.commit()
    top.sort(key=lambda row: -row[0])
    kp_tiers = collections.Counter(
        row[0] for row in con.execute(
            "SELECT weight_tier FROM knowledge_points"
        )
    )
    integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
    fk = con.execute("PRAGMA foreign_key_check").fetchall()
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    with open(REPORT, "w", encoding="utf-8") as handle:
        handle.write("# 概念 / KP 权重重算\n\n")
        handle.write(f"- 概念：{updated}\n")
        handle.write(f"- KP tier 分布：{dict(kp_tiers)}\n")
        handle.write(f"- 最大题目计数：core={max_core}, supporting={max_sup}, "
                     f"confusable={max_conf}\n")
        handle.write(f"- integrity: {integrity}\n")
        handle.write(f"- foreign_key_check: {'OK' if not fk else 'FAIL'}\n\n")
        handle.write("## 权重最高的 60 个概念\n\n")
        handle.write("| # | 概念 | Unit | 权重 | Tier | core | supporting | confusable |\n")
        handle.write("|---:|---|---:|---:|---|---:|---:|---:|\n")
        for index, row in enumerate(top[:60], 1):
            handle.write(f"| {index} | {row[1]} | {row[2]} | {row[0]:.1f} | "
                         f"{row[3]} | {row[4]} | {row[5]} | {row[6]} |\n")
    import csv
    with open(CONCEPT_CSV, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["cluster_id", "canonical_name", "ap_unit", "weight",
                         "weight_tier", "member_count"])
        for row in con.execute(
            "SELECT cluster_id,canonical_name,ap_unit,weight,weight_tier,member_count "
            "FROM concept_clusters ORDER BY weight DESC"
        ):
            writer.writerow(list(row))
    with open(KP_CSV, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["kp_id", "book_id", "name", "weight", "weight_tier",
                         "weight_reason"])
        for row in con.execute(
            "SELECT kp_id,book_id,name,weight,weight_tier,weight_reason "
            "FROM knowledge_points ORDER BY weight DESC"
        ):
            writer.writerow(list(row))
    print("concepts updated:", updated)
    print("KP tiers:", dict(kp_tiers))
    print("integrity:", integrity, "fk:", "OK" if not fk else fk[:3])
    print("report:", REPORT)
    con.close()


if __name__ == "__main__":
    main()
