#!/usr/bin/env python3
"""Deterministic fallback linker for Myers questions after API balance ran out.

Uses exact concept names/aliases in the correct option, stem, context, and
wrong options.  It never calls the API.  Results are marked
prompt_version='concept-lexical-v1' and lower confidence.
"""
import argparse
import collections
import json
import os
import re
import sqlite3
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
EXAM_DB = os.path.join(ROOT, "data", "content", "psychology", "psychology_exam.db")
KNOW_DB = os.path.join(ROOT, "data", "content", "psychology", "psychology_knowledge.db")
REPORT = os.path.join(ROOT, "data", "content", "psychology", "extraction", "myers", "myers_concept_lexical_report.md")

GENERIC = {
    "psychology", "behavior", "effect", "theory", "memory", "learning",
    "emotion", "personality", "intelligence", "development", "cognition",
    "language", "process", "response", "stimulus", "research", "study",
    "variable", "correlation", "experiment", "participants", "test",
}


def norm(value):
    value = (value or "").lower().replace("’", "'")
    value = value.replace("ﬁ", "fi").replace("ﬂ", "fl")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def load_concepts(know):
    concepts = {}
    for row in know.execute(
        """
        SELECT c.cluster_id, c.canonical_name, c.canonical_kp_id,
               c.ap_unit, c.weight, k.name AS canonical_kp_name
        FROM concept_clusters c
        JOIN knowledge_points k ON k.kp_id=c.canonical_kp_id
        """
    ):
        concepts[row["cluster_id"]] = {
            "cluster_id": row["cluster_id"],
            "name": row["canonical_name"],
            "kp_id": row["canonical_kp_id"],
            "unit": row["ap_unit"],
            "weight": row["weight"] or 0,
            "surfaces": {norm(row["canonical_name"]), norm(row["canonical_kp_name"])},
        }
    for row in know.execute(
        """
        SELECT m.cluster_id, k.name
        FROM concept_members m JOIN knowledge_points k ON k.kp_id=m.kp_id
        """
    ):
        if row["cluster_id"] in concepts:
            concepts[row["cluster_id"]]["surfaces"].add(norm(row["name"]))
    for row in know.execute(
        """
        SELECT m.cluster_id, a.alias
        FROM concept_members m JOIN kp_aliases a ON a.kp_id=m.kp_id
        """
    ):
        if row["cluster_id"] in concepts:
            concepts[row["cluster_id"]]["surfaces"].add(norm(row["alias"]))
    surfaces = []
    for concept in concepts.values():
        for surface in concept["surfaces"]:
            if len(surface) >= 3 and surface not in GENERIC:
                surfaces.append((surface, concept))
    # Longest first so "positive reinforcement" wins over "reinforcement".
    surfaces.sort(key=lambda item: -len(item[0]))
    return concepts, surfaces


def find_matches(text, surfaces, unit):
    lowered = f" {norm(text)} "
    found = {}
    for surface, concept in surfaces:
        pattern = r"(?<![a-z0-9])" + re.escape(surface) + r"(?![a-z0-9])"
        if re.search(pattern, lowered):
            score = 8.0 + len(surface) / 10.0 + concept["weight"] / 50.0
            if unit and concept["unit"] == unit:
                score += 1.5
            current = found.get(concept["cluster_id"])
            if current is None or score > current[0]:
                found[concept["cluster_id"]] = (score, surface, concept)
    return list(found.values())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper", action="append", default=[])
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    exam = sqlite3.connect(EXAM_DB)
    exam.row_factory = sqlite3.Row
    know = sqlite3.connect(KNOW_DB)
    know.row_factory = sqlite3.Row
    concepts, surfaces = load_concepts(know)
    print("concepts:", len(concepts), "surfaces:", len(surfaces))

    papers = args.paper or sorted({
        row[0] for row in exam.execute(
            "SELECT DISTINCT paper_id FROM questions "
            "WHERE paper_id LIKE 'psychology-myers-2024-%' AND section='MCQ'"
        )
    })
    rows = []
    for paper_id in papers:
        questions = exam.execute(
            "SELECT * FROM questions WHERE paper_id=? AND section='MCQ' "
            "AND correct_answer IS NOT NULL ORDER BY number", (paper_id,)
        ).fetchall()
        if args.limit:
            questions = questions[:args.limit]
        unit_match = re.search(r"-u(\d+)$", paper_id)
        unit = unit_match.group(1) if unit_match else None
        linked = 0
        for q in questions:
            existing = know.execute(
                "SELECT 1 FROM question_analysis WHERE question_id=?",
                (q["question_id"],),
            ).fetchone()
            if existing:
                continue
            options = exam.execute(
                "SELECT label,content,is_correct FROM options WHERE question_id=? "
                "ORDER BY sort_order", (q["question_id"],)
            ).fetchall()
            correct = next((o for o in options if o["is_correct"]), None)
            if not correct:
                continue
            correct_matches = find_matches(correct["content"], surfaces, unit)
            stem_matches = find_matches(
                f"{q['stem']} {q['context'] or ''}", surfaces, unit
            )
            core = []
            for _score, surface, concept in sorted(
                correct_matches, key=lambda item: -item[0]
            )[:2]:
                core.append({
                    "concept": concept, "surface": surface,
                    "source": "correct_option", "confidence": 0.82,
                    "evidence": correct["content"],
                })
            if not core:
                for _score, surface, concept in sorted(
                    stem_matches, key=lambda item: -item[0]
                )[:2]:
                    core.append({
                        "concept": concept, "surface": surface,
                        "source": "stem", "confidence": 0.58,
                        "evidence": q["stem"],
                    })
            core_ids = {entry["concept"]["cluster_id"] for entry in core}
            confusables = []
            for option in options:
                if option["is_correct"]:
                    continue
                for _score, surface, concept in sorted(
                    find_matches(option["content"], surfaces, unit),
                    key=lambda item: -item[0],
                )[:2]:
                    if concept["cluster_id"] in core_ids:
                        continue
                    confusables.append({
                        "concept": concept, "surface": surface,
                        "option_label": option["label"], "confidence": 0.55,
                        "evidence": option["content"],
                    })
                    break
            supporting = []
            for _score, surface, concept in sorted(
                correct_matches, key=lambda item: -item[0]
            ):
                if concept["cluster_id"] not in core_ids:
                    supporting.append({
                        "concept": concept, "surface": surface,
                        "confidence": 0.5, "evidence": correct["content"],
                    })
                    break
            status = "linked" if core and all(
                entry["source"] == "correct_option" for entry in core
            ) else "needs_review"
            now = datetime.now().astimezone().isoformat(timespec="seconds")
            know.execute(
                "INSERT OR REPLACE INTO question_analysis"
                "(question_id,paper_id,status,model,prompt_version,notes,updated_at)"
                " VALUES (?,?,?,?,?,?,?)",
                (q["question_id"], paper_id, status, "lexical-fallback",
                 "concept-lexical-v1",
                 "API unavailable; deterministic name/alias matching", now),
            )
            for entry in core:
                concept = entry["concept"]
                know.execute(
                    "INSERT OR IGNORE INTO question_concept_links"
                    "(question_id,concept_id,relation_type,option_label,confidence,"
                    " evidence,rationale,created_at) VALUES (?,?,?,?,?,?,?,?)",
                    (q["question_id"], concept["cluster_id"], "core", None,
                     entry["confidence"], entry["evidence"], "lexical match", now),
                )
                know.execute(
                    "INSERT OR IGNORE INTO question_kp_links"
                    "(question_id,kp_id,relation_type,option_label,confidence,"
                    " evidence,rationale,created_at) VALUES (?,?,?,?,?,?,?,?)",
                    (q["question_id"], concept["kp_id"], "core", None,
                     entry["confidence"], entry["evidence"], "lexical match", now),
                )
            for entry in supporting:
                concept = entry["concept"]
                know.execute(
                    "INSERT OR IGNORE INTO question_concept_links"
                    "(question_id,concept_id,relation_type,option_label,confidence,"
                    " evidence,rationale,created_at) VALUES (?,?,?,?,?,?,?,?)",
                    (q["question_id"], concept["cluster_id"], "supporting", None,
                     entry["confidence"], entry["evidence"], "lexical match", now),
                )
                know.execute(
                    "INSERT OR IGNORE INTO question_kp_links"
                    "(question_id,kp_id,relation_type,option_label,confidence,"
                    " evidence,rationale,created_at) VALUES (?,?,?,?,?,?,?,?)",
                    (q["question_id"], concept["kp_id"], "supporting", None,
                     entry["confidence"], entry["evidence"], "lexical match", now),
                )
            for entry in confusables:
                concept = entry["concept"]
                know.execute(
                    "INSERT OR IGNORE INTO question_concept_links"
                    "(question_id,concept_id,relation_type,option_label,confidence,"
                    " evidence,rationale,created_at) VALUES (?,?,?,?,?,?,?,?)",
                    (q["question_id"], concept["cluster_id"], "confusable",
                     entry["option_label"], entry["confidence"],
                     entry["evidence"], "name/alias in wrong option", now),
                )
                know.execute(
                    "INSERT OR IGNORE INTO question_kp_links"
                    "(question_id,kp_id,relation_type,option_label,confidence,"
                    " evidence,rationale,created_at) VALUES (?,?,?,?,?,?,?,?)",
                    (q["question_id"], concept["kp_id"], "confusable",
                     entry["option_label"], entry["confidence"],
                     entry["evidence"], "name/alias in wrong option", now),
                )
            know.commit()
            linked += 1
        rows.append((paper_id, len(questions), linked))
        print("paper", paper_id, "processed", linked)
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    with open(REPORT, "w", encoding="utf-8") as handle:
        handle.write("# Myers 概念关联：确定性回退\n\n")
        handle.write("- API 余额耗尽后使用名称/别名匹配，未调用模型。\n")
        handle.write("- `prompt_version=concept-lexical-v1`，置信度 0.5–0.82。\n\n")
        handle.write("| Paper | MCQ | 新增分析 |\n|---|---:|---:|\n")
        for row in rows:
            handle.write(f"| `{row[0]}` | {row[1]} | {row[2]} |\n")
    print("report:", REPORT)
    know.close()
    exam.close()


if __name__ == "__main__":
    main()
