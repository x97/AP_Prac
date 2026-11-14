#!/usr/bin/env python3
"""Audit the 393 core concepts and apply the reviewed, safe curation.

Modes
-----
default      write the review report/CSV from the current database
--apply      merge reviewed duplicates, normalise names, insert relations
--postcheck  write a short verification report after --apply + weight recompute
"""
import argparse
import collections
import csv
import os
import re
import shutil
import sqlite3
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DB = os.path.join(ROOT, "data", "content", "psychology", "psychology_knowledge.db")
OUT_CSV = os.path.join(ROOT, "data", "content", "psychology", "reports", "knowledge", "concept_audit.csv")
OUT_MD = os.path.join(ROOT, "data", "content", "psychology", "reports", "knowledge", "concept_audit_report.md")
OUT_REL = os.path.join(ROOT, "data", "content", "psychology", "reports", "knowledge", "concept_relation_candidates.csv")
OUT_ACTIONS = os.path.join(ROOT, "data", "content", "psychology", "reports", "knowledge", "concept_audit_actions.md")
OUT_POST = os.path.join(ROOT, "data", "content", "psychology", "reports", "knowledge", "concept_audit_postcheck.md")
OUT_POST_CSV = os.path.join(ROOT, "data", "content", "psychology", "reports", "knowledge", "concept_audit_postcheck.csv")

sys.path.insert(0, HERE)
from concept_curation_data import KEEP_LOWER, MERGES, RENAMES, RELATIONS  # noqa: E402

STOP = {
    "the", "a", "an", "of", "and", "or", "in", "on", "to", "for", "with",
    "by", "from", "as", "at", "is", "are", "be", "that", "this",
}
GENERIC = {
    "correlation", "learning", "motivation", "intelligence", "sensation",
    "perception", "personality", "theory", "concepts", "concept", "memory",
    "behavior", "behaviour", "emotion", "cognition", "language",
    "development", "psychology", "research", "variable", "stimulus",
    "response", "process",
}
REL_LABELS = {
    "broader_narrower": "上下位",
    "part_of": "整体-部分",
    "related_to": "相关",
    "same_name_different_sense": "同名异义",
}


def norm(value):
    value = (value or "").lower().replace("’", "'")
    value = value.replace("ﬁ", "fi").replace("ﬂ", "fl")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def compact(value):
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())


def first_upper(value):
    if value and value[0].islower():
        return value[0].upper() + value[1:]
    return value


def base_name(value):
    return norm(re.sub(r"\s*\([^)]*\)", "", value or ""))


def load_concepts(con):
    rows = con.execute(
        """
        SELECT c.cluster_id, c.canonical_name, c.weight, c.weight_tier,
               c.ap_unit, c.topic, c.member_count, c.canonical_kp_id,
               (SELECT COUNT(*) FROM question_concept_links l
                 WHERE l.concept_id=c.cluster_id AND l.relation_type='core') qcore,
               (SELECT COUNT(*) FROM question_concept_links l
                 WHERE l.concept_id=c.cluster_id AND l.relation_type='supporting') qsup,
               (SELECT COUNT(*) FROM question_concept_links l
                 WHERE l.concept_id=c.cluster_id AND l.relation_type='confusable') qconf,
               (SELECT COUNT(DISTINCT k.book_id)
                  FROM concept_members m JOIN knowledge_points k ON k.kp_id=m.kp_id
                 WHERE m.cluster_id=c.cluster_id) book_count,
               (SELECT GROUP_CONCAT(k.book_id || ':' || k.name, ' | ')
                  FROM concept_members m JOIN knowledge_points k ON k.kp_id=m.kp_id
                 WHERE m.cluster_id=c.cluster_id) members
        FROM concept_clusters c
        ORDER BY c.weight DESC, c.canonical_name
        """
    ).fetchall()
    return [dict(row) for row in rows]


def load_relations(con):
    exists = con.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='concept_relations'"
    ).fetchone()
    if not exists:
        return []
    return [dict(row) for row in con.execute(
        """
        SELECT r.concept_id_a, r.concept_id_b, r.relation_type,
               r.evidence, r.confidence,
               a.canonical_name AS name_a, b.canonical_name AS name_b
        FROM concept_relations r
        JOIN concept_clusters a ON a.cluster_id=r.concept_id_a
        JOIN concept_clusters b ON b.cluster_id=r.concept_id_b
        """
    )]


def resolve_name(concepts, name):
    exact = [row for row in concepts if row["canonical_name"] == name]
    if len(exact) == 1:
        return exact[0]
    folded = [row for row in concepts if norm(row["canonical_name"]) == norm(name)]
    if len(folded) == 1:
        return folded[0]
    if len(folded) > 1:
        raise SystemExit(f"ambiguous concept name: {name!r} -> "
                         f"{[row['canonical_name'] for row in folded]}")
    raise SystemExit(f"missing concept name: {name!r}")


def merge_plan(concepts):
    by_name = {row["canonical_name"]: row for row in concepts}
    plan = []
    skipped = []
    for target_name, source_name, reason in MERGES:
        target = by_name.get(target_name)
        if target is None:
            # A previous pass may already have applied the target rename.
            target = by_name.get(RENAMES.get(target_name, target_name))
        source = by_name.get(source_name)
        if source is None:
            if target is None:
                raise SystemExit(f"merge target missing: {target_name!r}")
            skipped.append((source_name, target["canonical_name"]))
            continue
        if target is None:
            raise SystemExit(f"merge target missing: {target_name!r}")
        plan.append({
            "target": target,
            "source": source,
            "reason": reason,
        })
    if skipped:
        print("already merged:", len(skipped))
    return plan


def rename_plan(concepts, merges):
    merged_sources = {item["source"]["cluster_id"] for item in merges}
    plan = []
    for row in concepts:
        if row["cluster_id"] in merged_sources:
            continue
        old = row["canonical_name"]
        new = old if old in KEEP_LOWER else RENAMES.get(old, first_upper(old))
        if new != old:
            plan.append({"concept": row, "old": old, "new": new})
    # Detect collisions in the post-merge/post-rename namespace.
    by_new = collections.defaultdict(list)
    for row in concepts:
        if row["cluster_id"] in merged_sources:
            continue
        old = row["canonical_name"]
        new = old if old in KEEP_LOWER else RENAMES.get(old, first_upper(old))
        by_new[new].append(old)
    conflicts = {name: names for name, names in by_new.items() if len(names) > 1}
    if conflicts:
        raise SystemExit(f"rename collisions: {conflicts}")
    return plan


def virtual_concepts(concepts, merges, renames):
    """Project the post-merge/post-rename namespace without touching the DB."""
    merged_sources = {item["source"]["cluster_id"] for item in merges}
    rename_by_id = {item["concept"]["cluster_id"]: item["new"] for item in renames}
    out = []
    for row in concepts:
        if row["cluster_id"] in merged_sources:
            continue
        copy = dict(row)
        copy["canonical_name"] = rename_by_id.get(row["cluster_id"], row["canonical_name"])
        out.append(copy)
    return out


def relation_plan(concepts):
    resolved = []
    missing = []
    for domain, a_name, b_name, rel_type, confidence, note in RELATIONS:
        try:
            a = resolve_name(concepts, a_name)
            b = resolve_name(concepts, b_name)
        except SystemExit as exc:
            missing.append(str(exc))
            continue
        resolved.append({
            "domain": domain,
            "a": a,
            "b": b,
            "relation_type": rel_type,
            "confidence": confidence,
            "note": note,
        })
    if missing:
        raise SystemExit("relation names unresolved:\n" + "\n".join(missing))
    return resolved


def homonym_families(concepts):
    groups = collections.defaultdict(list)
    for row in concepts:
        base = base_name(row["canonical_name"])
        if not base:
            continue
        groups[base].append(row)
    return {key: rows for key, rows in groups.items() if len(rows) > 1}


def audit_rows(concepts, relations, merges, renames):
    merge_source = {item["source"]["cluster_id"]: item["target"]["canonical_name"]
                    for item in merges}
    merge_target = {item["target"]["cluster_id"]: item["source"]["canonical_name"]
                    for item in merges}
    merge_ids = set(merge_source) | set(merge_target)
    special_rename_ids = {
        item["concept"]["cluster_id"] for item in renames if item["old"] in RENAMES
    }
    rename_by_id = {item["concept"]["cluster_id"]: item["new"] for item in renames}
    rel_by_a = collections.defaultdict(list)
    rel_by_b = collections.defaultdict(list)
    for rel in relations:
        rel_by_a[rel["a"]["cluster_id"]].append(rel)
        rel_by_b[rel["b"]["cluster_id"]].append(rel)
    homonyms = {
        key: rows for key, rows in homonym_families(concepts).items()
        if not any(row["cluster_id"] in merge_ids for row in rows)
    }
    homonym_ids = {row["cluster_id"] for rows in homonyms.values() for row in rows}

    rows = []
    for row in concepts:
        if row["weight_tier"] != "core":
            continue
        flags = []
        actions = []
        priority = "info"
        name = row["canonical_name"]
        if name[:1].islower():
            flags.append("lowercase")
        if row["cluster_id"] in special_rename_ids:
            flags.append("curated_rename")
            actions.append("rename_special")
            priority = "P1"
        elif name[:1].islower():
            actions.append("rename_case")
            priority = "P2"
        if " and " in f" {name} ":
            flags.append("compound")
            actions.append("review_split")
            priority = "P1"
        if norm(name) in GENERIC:
            flags.append("generic_umbrella")
            if row["qcore"] > 0:
                actions.append("keep_umbrella")
            else:
                actions.append("downgrade_review")
                priority = "P2"
        if row["weight"] >= 70:
            flags.append("high_weight")
        if row["qcore"] == 0:
            flags.append("zero_core_questions")
            if "downgrade_review" not in actions:
                actions.append("curriculum_only")
        if row["weight"] < 60:
            flags.append("low_weight")
        if row["cluster_id"] in homonym_ids:
            flags.append("homonym_family")
            if "rename_special" not in actions:
                actions.append("review_qualifier")
                priority = "P1" if priority == "info" else priority
        if row["cluster_id"] in merge_source:
            flags.append("duplicate_source")
            actions.insert(0, f"merge_into:{merge_source[row['cluster_id']]}")
            priority = "P0"
        if row["cluster_id"] in merge_target:
            flags.append("duplicate_target")
            actions.insert(0, f"keep_after_merge:{merge_target[row['cluster_id']]}")
            priority = "P0"
        if any(rel["relation_type"] == "broader_narrower"
               for rel in rel_by_b.get(row["cluster_id"], [])):
            flags.append("has_broader")
        if any(rel["relation_type"] == "broader_narrower"
               for rel in rel_by_a.get(row["cluster_id"], [])):
            flags.append("has_narrower")
        if any(rel["relation_type"] == "part_of" for rel in rel_by_b.get(row["cluster_id"], [])):
            flags.append("has_whole")
        if any(rel["relation_type"] == "part_of" for rel in rel_by_a.get(row["cluster_id"], [])):
            flags.append("has_part")
        recommendation = ",".join(dict.fromkeys(actions)) or "keep"
        rows.append({
            **row,
            "proposed_name": rename_by_id.get(row["cluster_id"], name),
            "flags": ",".join(dict.fromkeys(flags)),
            "priority": priority,
            "recommendation": recommendation,
            "broader": " | ".join(
                rel["a"]["canonical_name"] for rel in rel_by_b.get(row["cluster_id"], [])
                if rel["relation_type"] == "broader_narrower"
            ),
            "narrower": " | ".join(
                rel["b"]["canonical_name"] for rel in rel_by_a.get(row["cluster_id"], [])
                if rel["relation_type"] == "broader_narrower"
            ),
            "part_of": " | ".join(
                rel["a"]["canonical_name"] for rel in rel_by_b.get(row["cluster_id"], [])
                if rel["relation_type"] == "part_of"
            ),
            "has_parts": " | ".join(
                rel["b"]["canonical_name"] for rel in rel_by_a.get(row["cluster_id"], [])
                if rel["relation_type"] == "part_of"
            ),
            "related": " | ".join(
                rel["a"]["canonical_name"] if rel["b"]["cluster_id"] == row["cluster_id"]
                else rel["b"]["canonical_name"]
                for rel in rel_by_a.get(row["cluster_id"], []) + rel_by_b.get(row["cluster_id"], [])
                if rel["relation_type"] == "related_to"
            ),
        })
    rows.sort(key=lambda item: (-(item["weight"] or 0), item["canonical_name"]))
    return rows, homonyms


def write_csv(rows, path):
    fields = [
        "cluster_id", "canonical_name", "proposed_name", "weight", "weight_tier",
        "ap_unit", "topic", "qcore", "qsup", "qconf", "book_count", "member_count",
        "priority", "flags", "recommendation", "broader", "narrower", "part_of",
        "has_parts", "related", "members",
    ]
    with open(path, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fields})


def write_relation_csv(relations, path):
    fields = ["domain", "relation_type", "a", "b", "confidence", "note",
              "a_id", "b_id"]
    with open(path, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for rel in relations:
            writer.writerow({
                "domain": rel["domain"],
                "relation_type": rel["relation_type"],
                "a": rel["a"]["canonical_name"],
                "b": rel["b"]["canonical_name"],
                "confidence": rel["confidence"],
                "note": rel["note"],
                "a_id": rel["a"]["cluster_id"],
                "b_id": rel["b"]["cluster_id"],
            })


def write_report(rows, homonyms, homonym_total, relations, merges, renames, path):
    core = [row for row in rows if row["weight_tier"] == "core"]
    high = [row for row in core if row["weight"] >= 70]
    low = [row for row in core if row["weight"] < 60]
    zero = [row for row in core if row["qcore"] == 0]
    lowercase = [row for row in core if row["canonical_name"][:1].islower()]
    generic = [row for row in core if "generic_umbrella" in row["flags"]]
    rel_counts = collections.Counter(rel["relation_type"] for rel in relations)
    domain_counts = collections.Counter(rel["domain"] for rel in relations)

    with open(path, "w", encoding="utf-8") as handle:
        handle.write("# 393 个 core 概念复核\n\n")
        handle.write("## 结论摘要\n\n")
        handle.write(f"- core 概念：**{len(core)}**；权重 ≥70：**{len(high)}**；"
                     f"权重 <60：**{len(low)}**。\n")
        handle.write(f"- **63 个 core 概念没有 core 题**（{len(zero)} 个）。"
                     "core tier 是“两本教材都覆盖”的课程核心标记，不等于考试高频；"
                     "不按零 core 题直接降级，避免丢掉跨书覆盖信号。\n")
        handle.write(f"- 命名问题：{len(lowercase)} 个首字母小写；"
                     f"{len(merges)} 组跨章复现/拼写重复；"
                     f"{len(homonyms)} 组真正的同名异义"
                     f"（合并前共 {homonym_total} 组同名族，其中 "
                     f"{homonym_total - len(homonyms)} 组是跨章重复）；"
                     "1 个复合概念 `Amygdala and hippocampus`。\n")
        handle.write(f"- 已整理 **{len(relations)}** 条关系："
                     + "，".join(f"{REL_LABELS[key]} {value}"
                                for key, value in rel_counts.most_common()) + "。\n")
        handle.write("- 高权重概念整体可靠；需要人工注意的是 `Correlation`、"
                     "`Validity`、`Behavioral perspective` 这类上位 umbrella，"
                     "应保留为父概念，而不是降级。\n\n")

        handle.write("## 复核口径\n\n")
        handle.write("- `weight_tier=core`：Barron 与 Myers 两本书都有对应 KP；"
                     "这是课程覆盖标记。\n")
        handle.write("- `weight`：由 core/supporting/confusable 题量、跨书、"
                     "Myers 词表、单元和定义共同决定，反映考试需求。\n")
        handle.write("- 零 core 题但权重 55–60 的 core 概念，多数仍是有教材覆盖的"
                     "课程概念；报告标为 `curriculum_only`，不自动降级。\n\n")

        handle.write("## 高权重 core 概念（权重 ≥70）\n\n")
        handle.write("| 概念 | Unit | 权重 | core题 | confusable | 标记 | 建议 |\n")
        handle.write("|---|---:|---:|---:|---:|---|---|\n")
        for row in high:
            handle.write(f"| {row['canonical_name']} | {row['ap_unit']} | "
                         f"{row['weight']:.1f} | {row['qcore']} | {row['qconf']} | "
                         f"{row['flags'] or '—'} | {row['recommendation']} |\n")
        handle.write("\n")

        handle.write("## 零 core 题的 core 概念\n\n")
        handle.write("这些概念两本书都覆盖，但没有被任何题目标成 core；"
                     "其中不少在 supporting/confusable 中出现。建议保留 core tier，"
                     "在排序和复习优先级上按权重处理。\n\n")
        handle.write("| 概念 | Unit | 权重 | supporting | confusable | 建议 |\n")
        handle.write("|---|---:|---:|---:|---:|---|\n")
        for row in sorted(zero, key=lambda item: (-item["weight"], item["canonical_name"])):
            handle.write(f"| {row['canonical_name']} | {row['ap_unit']} | "
                         f"{row['weight']:.1f} | {row['qsup']} | {row['qconf']} | "
                         f"{row['recommendation']} |\n")
        handle.write("\n")

        handle.write("## 命名规范与重复概念\n\n")
        handle.write("### 首字母小写（建议统一为句首大写）\n\n")
        handle.write("共 " + str(len(lowercase)) + " 个：\n\n")
        for row in sorted(lowercase, key=lambda item: item["canonical_name"].lower()):
            handle.write(f"- `{row['canonical_name']}` → `{row['proposed_name']}`\n")
        handle.write("\n### 需要合并的跨章复现/拼写重复\n\n")
        for item in merges:
            handle.write(f"- `{item['source']['canonical_name']}` → "
                         f"`{item['target']['canonical_name']}`：{item['reason']}\n")
        handle.write("\n### 需要限定词的同名异义\n\n")
        for base, items in sorted(homonyms.items()):
            names = " / ".join(f"`{item['canonical_name']}`" for item in items)
            handle.write(f"- {names}\n")
        handle.write("\n### 特殊改名\n\n")
        for item in renames:
            if item["old"] in RENAMES:
                handle.write(f"- `{item['old']}` → `{item['new']}`\n")
        handle.write("\n")

        handle.write("## 上下位 / 整体-部分 / 相关关系\n\n")
        handle.write("关系按领域分布：\n\n")
        for domain, count in sorted(domain_counts.items()):
            handle.write(f"- {domain}：{count} 条\n")
        handle.write("\n### 高置信度关系（节选）\n\n")
        handle.write("| 领域 | 关系 | A | B | 说明 |\n")
        handle.write("|---|---|---|---|---|\n")
        for rel in relations[:120]:
            handle.write(f"| {rel['domain']} | {REL_LABELS[rel['relation_type']]} | "
                         f"{rel['a']['canonical_name']} | {rel['b']['canonical_name']} | "
                         f"{rel['note']} |\n")
        if len(relations) > 120:
            handle.write(f"\n其余 {len(relations) - 120} 条见 "
                         "`concept_relation_candidates.csv`。\n")
        handle.write("\n")

        handle.write("## 自动候选中的误报（已剔除）\n\n")
        handle.write("- `Behavioral Perspective → CBT`：行为主义视角与 CBT 不是上下位。\n")
        handle.write("- `Stress → PTSD`、`Stress → diathesis-stress model`："
                     "应激与障碍/模型不是上下位。\n")
        handle.write("- `Hypothesis → Facial feedback hypothesis`、"
                     "`Hypothesis → Frustration-aggression hypothesis`："
                     "假设与具体理论不是上下位。\n")
        handle.write("- `achievement tests → Achievement motivation`、"
                     "`intelligence → WAIS`、`Personality → Personality inventories`："
                     "构念与测量工具不是上下位。\n")
        handle.write("- `Personality disorders → Personality inventories`："
                     "障碍与评估工具不是上下位。\n")
        handle.write("- `Discrimination (conditioning) → Discrimination (social)`："
                     "这是同名异义，不是上下位。\n")
        handle.write("- `Cognitive therapy → CBT`：方向反了；正确关系是 "
                     "`CBT → Cognitive therapy`。\n")
        handle.write("- 复数启发式误报：`bias`、`consciousness`、`Cones`、"
                     "`Big Five personality traits` 等不应因词尾 `s` 自动改名。\n")
        handle.write("\n")

        handle.write("## 建议动作\n\n")
        handle.write("1. **P0 合并重复概念**：`Unit X` 后缀的跨章复现概念并入主概念，"
                     "避免同一概念被拆成多条、权重被稀释。\n")
        handle.write("2. **P1 修正同名/复合概念**："
                     "`Amygdala and hippocampus` → `Amygdala`；"
                     "`Blind sight` → `Blindsight`；"
                     "`Smell (or Olfaction)` → `Smell (Olfaction)`；"
                     "Autonomy/Proximity/Similarity/Opponent-process/GRIT 加限定词。\n")
        handle.write("3. **P2 统一首字母大小写**：所有概念名统一为句首大写，"
                     "不改动专有名词和缩写。\n")
        handle.write("4. **保留 umbrella**：`Correlation`、`Validity`、"
                     "`Learning`、`Motivation` 等作为父概念保留；"
                     "其下位关系写入 `concept_relations`。\n")
        handle.write("5. **不按零 core 题降级**：core tier 继续表示跨书覆盖；"
                     "考试优先级用 weight 和关系表表达。\n")


def apply_changes(con, concepts, merges, renames, relations):
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = DB + f".bak-{stamp}-before-concept-audit-apply"
    shutil.copy2(DB, backup)
    print("backup:", backup)
    con.execute("PRAGMA foreign_keys = ON")
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS concept_relations (
            relation_id INTEGER PRIMARY KEY,
            concept_id_a TEXT NOT NULL REFERENCES concept_clusters(cluster_id) ON DELETE CASCADE,
            concept_id_b TEXT NOT NULL REFERENCES concept_clusters(cluster_id) ON DELETE CASCADE,
            relation_type TEXT NOT NULL CHECK (relation_type IN (
                'broader_narrower','part_of','related_to','same_name_different_sense'
            )),
            evidence TEXT,
            confidence REAL,
            created_at TEXT NOT NULL,
            UNIQUE (concept_id_a, concept_id_b, relation_type),
            CHECK (concept_id_a <> concept_id_b)
        )
        """
    )
    con.execute("CREATE INDEX IF NOT EXISTS ix_concept_rel_a ON concept_relations(concept_id_a)")
    con.execute("CREATE INDEX IF NOT EXISTS ix_concept_rel_b ON concept_relations(concept_id_b)")

    merged = []
    for item in merges:
        target_id = item["target"]["cluster_id"]
        source_id = item["source"]["cluster_id"]
        target_name = item["target"]["canonical_name"]
        source_name = item["source"]["canonical_name"]
        con.execute(
            """
            INSERT OR IGNORE INTO concept_members
            (cluster_id,kp_id,relation,confidence,evidence)
            SELECT ?,kp_id,relation,confidence,evidence
            FROM concept_members WHERE cluster_id=?
            """,
            (target_id, source_id),
        )
        con.execute(
            """
            INSERT OR IGNORE INTO question_concept_links
            (question_id,concept_id,relation_type,option_label,confidence,
             evidence,rationale,created_at)
            SELECT question_id,?,relation_type,option_label,confidence,
                   evidence,rationale,created_at
            FROM question_concept_links WHERE concept_id=?
            """,
            (target_id, source_id),
        )
        con.execute("DELETE FROM question_concept_links WHERE concept_id=?", (source_id,))
        con.execute("DELETE FROM concept_members WHERE cluster_id=?", (source_id,))
        con.execute("DELETE FROM concept_clusters WHERE cluster_id=?", (source_id,))
        merged.append((source_name, target_name))

    renamed = []
    for item in renames:
        concept_id = item["concept"]["cluster_id"]
        old = item["old"]
        new = item["new"]
        exists = con.execute(
            "SELECT 1 FROM concept_clusters WHERE subject_id='psychology' "
            "AND canonical_name=? AND cluster_id<>?",
            (new, concept_id),
        ).fetchone()
        if exists:
            raise SystemExit(f"rename collision: {old!r} -> {new!r}")
        con.execute(
            "UPDATE concept_clusters SET canonical_name=? WHERE cluster_id=?",
            (new, concept_id),
        )
        renamed.append((old, new))

    # Re-resolve relations after renames; names in the curation data are the
    # final, normalised names.
    fresh = load_concepts(con)
    relation_rows = relation_plan(fresh)
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    inserted = 0
    for rel in relation_rows:
        cur = con.execute(
            """
            INSERT OR IGNORE INTO concept_relations
            (concept_id_a,concept_id_b,relation_type,evidence,confidence,created_at)
            VALUES (?,?,?,?,?,?)
            """,
            (rel["a"]["cluster_id"], rel["b"]["cluster_id"],
             rel["relation_type"], rel["note"], rel["confidence"], now),
        )
        inserted += cur.rowcount
    con.commit()

    mode = "a" if os.path.exists(OUT_ACTIONS) else "w"
    with open(OUT_ACTIONS, mode, encoding="utf-8") as handle:
        if mode == "a":
            handle.write("\n\n---\n\n")
        handle.write(f"# Core 概念复核执行记录（{stamp}）\n\n")
        handle.write(f"- 备份：`{os.path.basename(backup)}`\n")
        handle.write(f"- 合并重复概念：{len(merged)} 组\n")
        handle.write(f"- 重命名：{len(renamed)} 个\n")
        handle.write(f"- 写入关系：{inserted} 条（计划 {len(relation_rows)} 条）\n\n")
        handle.write("## 合并\n\n")
        for source, target in merged:
            handle.write(f"- `{source}` → `{target}`\n")
        handle.write("\n## 重命名\n\n")
        for old, new in renamed:
            handle.write(f"- `{old}` → `{new}`\n")
        handle.write("\n## 关系类型\n\n")
        counts = collections.Counter(rel["relation_type"] for rel in relation_rows)
        for rel_type, count in counts.most_common():
            handle.write(f"- {REL_LABELS[rel_type]}：{count}\n")
    print(f"merged={len(merged)} renamed={len(renamed)} relations={inserted}")
    print("actions:", OUT_ACTIONS)


def write_postcheck(con, path, csv_path):
    concepts = load_concepts(con)
    core = [row for row in concepts if row["weight_tier"] == "core"]
    lowercase = [row for row in core if row["canonical_name"][:1].islower()]
    compact_groups = collections.defaultdict(list)
    for row in concepts:
        compact_groups[compact(row["canonical_name"])].append(row)
    duplicates = {key: rows for key, rows in compact_groups.items() if len(rows) > 1}
    unit_suffix = [row for row in concepts if "(Unit " in row["canonical_name"]]
    relations = load_relations(con)
    rel_counts = collections.Counter(row["relation_type"] for row in relations)
    write_csv(core, csv_path)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("# Core 概念复核后检查\n\n")
        handle.write(f"- 概念总数：{len(concepts)}\n")
        handle.write(f"- core：{len(core)}\n")
        handle.write(f"- 首字母小写 core：{len(lowercase)}\n")
        handle.write(f"- 归一化后同名重复：{len(duplicates)}\n")
        handle.write(f"- 仍含 `(Unit X)` 的概念：{len(unit_suffix)}\n")
        handle.write(f"- 关系总数：{len(relations)}\n")
        handle.write("- 基线审计 CSV：`concept_audit_baseline.csv`\n")
        handle.write("- 最终审计 CSV：`concept_audit_final.csv`\n")
        for rel_type, count in rel_counts.most_common():
            handle.write(f"- {REL_LABELS[rel_type]}：{count}\n")
        if lowercase:
            handle.write("\n## 仍小写\n\n")
            for row in lowercase:
                handle.write(f"- `{row['canonical_name']}`\n")
        if duplicates:
            handle.write("\n## 仍重复\n\n")
            for _key, rows in duplicates.items():
                handle.write("- " + " / ".join(f"`{row['canonical_name']}`" for row in rows) + "\n")
        if unit_suffix:
            handle.write("\n## 仍含 Unit 后缀\n\n")
            for row in unit_suffix:
                handle.write(f"- `{row['canonical_name']}`\n")
    print("postcheck:", path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=DB)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--postcheck", action="store_true")
    args = parser.parse_args()

    con = sqlite3.connect(args.db)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    if args.postcheck:
        write_postcheck(con, OUT_POST, OUT_POST_CSV)
        con.close()
        return

    concepts = load_concepts(con)
    merges = merge_plan(concepts)
    renames = rename_plan(concepts, merges)
    relations = relation_plan(virtual_concepts(concepts, merges, renames))
    rows, homonyms = audit_rows(concepts, relations, merges, renames)
    homonym_total = len(homonym_families(concepts))

    if args.apply:
        apply_changes(con, concepts, merges, renames, relations)
        con.close()
        return

    write_csv(rows, OUT_CSV)
    write_relation_csv(relations, OUT_REL)
    write_report(rows, homonyms, homonym_total, relations, merges, renames, OUT_MD)
    print("core concepts:", sum(1 for row in rows if row["weight_tier"] == "core"))
    print("merges:", len(merges), "renames:", len(renames), "relations:", len(relations))
    print("wrote:", OUT_CSV)
    print("wrote:", OUT_MD)
    print("wrote:", OUT_REL)
    con.close()


if __name__ == "__main__":
    main()
