#!/usr/bin/env python3
"""Link Myers MCQ papers to the canonical concept layer.

Reuses the proven KP linker prompt/validation.  Each canonical concept is
represented by its canonical KP, so the model selects concept keys; results
are written to question_concept_links and (for the current quiz UI) to
question_kp_links using the canonical KP.
"""
import argparse
import collections
import json
import os
import sqlite3
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
EXAM_DB = os.path.join(ROOT, "data", "content", "psychology", "psychology_exam.db")
KNOW_DB = os.path.join(ROOT, "data", "content", "psychology", "psychology_knowledge.db")
REPORT = os.path.join(ROOT, "data", "content", "psychology", "extraction", "myers", "myers_concept_link_report.md")
sys.path.insert(0, HERE)
import link_question_kps as linker  # noqa: E402

PAPERS = [
    "psychology-myers-2024-u0",
    "psychology-myers-2024-u1",
    "psychology-myers-2024-u2",
    "psychology-myers-2024-u3",
    "psychology-myers-2024-u4",
    "psychology-myers-2024-u5",
    "psychology-myers-2024-mock-1",
]


def load_concepts(know):
    rows = know.execute(
        """
        SELECT c.cluster_id, c.canonical_name, c.canonical_kp_id,
               c.ap_unit, c.topic, c.weight, c.weight_tier,
               k.name, k.plain_en, k.definition_quote
        FROM concept_clusters c
        JOIN knowledge_points k ON k.kp_id=c.canonical_kp_id
        ORDER BY c.weight DESC
        """
    ).fetchall()
    kps = []
    aliases = collections.defaultdict(list)
    concept_of_kp = {}
    for row in rows:
        kp_id = row["canonical_kp_id"]
        topic = row["topic"] or row["name"]
        kps.append({
            "kp_id": kp_id,
            "name": row["canonical_name"],
            "plain_en": row["plain_en"] or "",
            "definition_quote": row["definition_quote"] or "",
            "section_heading": topic,
            "section_path": f"Unit {row['ap_unit']} > {topic}",
        })
        concept_of_kp[kp_id] = row["cluster_id"]
        aliases[kp_id].append({
            "alias": row["canonical_name"],
            "match_mode": "insensitive",
        })
        aliases[kp_id].append({
            "alias": row["name"],
            "match_mode": "insensitive",
        })
    # Add all member names/aliases as candidate surface forms.
    for row in know.execute(
        """
        SELECT m.cluster_id, m.kp_id, k.name
        FROM concept_members m
        JOIN knowledge_points k ON k.kp_id=m.kp_id
        """
    ):
        canonical = know.execute(
            "SELECT canonical_kp_id FROM concept_clusters WHERE cluster_id=?",
            (row["cluster_id"],),
        ).fetchone()
        if not canonical or not canonical["canonical_kp_id"]:
            continue
        kp_id = canonical["canonical_kp_id"]
        aliases[kp_id].append({"alias": row["name"], "match_mode": "insensitive"})
    for row in know.execute("SELECT kp_id, alias, match_mode FROM kp_aliases"):
        if row["kp_id"] in concept_of_kp:
            aliases[row["kp_id"]].append({
                "alias": row["alias"], "match_mode": row["match_mode"] or "insensitive",
            })
    # Deduplicate aliases.
    for kp_id, values in aliases.items():
        seen = set()
        deduped = []
        for value in values:
            key = linker.norm(value["alias"])
            if not key or key in seen:
                continue
            seen.add(key)
            deduped.append(value)
        aliases[kp_id] = deduped
    return kps, dict(aliases), concept_of_kp


def write_result(exam, know, paper_id, q, result, concept_of_kp, now):
    status = result["status"]
    notes = result.get("notes") or ""
    know.execute(
        "INSERT OR REPLACE INTO question_analysis"
        "(question_id,paper_id,status,model,prompt_version,notes,updated_at)"
        " VALUES (?,?,?,?,?,?,?)",
        (q["question_id"], paper_id, status, "deepseek-flash[1m]",
         "myers-concept-link-v1", notes, now),
    )
    for relation, key in (("core", "core"), ("supporting", "supporting"),
                          ("confusable", "confusables")):
        for entry in result.get(key, []):
            kp_id = entry["kp_id"]
            concept_id = concept_of_kp.get(kp_id)
            if not concept_id:
                continue
            know.execute(
                "INSERT OR IGNORE INTO question_concept_links"
                "(question_id,concept_id,relation_type,option_label,confidence,"
                " evidence,rationale,created_at) VALUES (?,?,?,?,?,?,?,?)",
                (q["question_id"], concept_id, relation,
                 entry.get("option_label"), entry.get("confidence"),
                 entry.get("evidence"), entry.get("reason"), now),
            )
            # Legacy KP table keeps the current quiz UI working.
            know.execute(
                "INSERT OR IGNORE INTO question_kp_links"
                "(question_id,kp_id,relation_type,option_label,confidence,"
                " evidence,rationale,created_at) VALUES (?,?,?,?,?,?,?,?)",
                (q["question_id"], kp_id, relation,
                 entry.get("option_label"), entry.get("confidence"),
                 entry.get("evidence"), entry.get("reason"), now),
            )
    for kw in result.get("keywords", []):
        know.execute(
            "INSERT OR IGNORE INTO question_keywords"
            "(question_id,surface,normalized,kp_id,role,location,"
            " option_label,confidence,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (q["question_id"], kw["surface"], kw["normalized"], kw.get("kp_id"),
             kw.get("role") or "mentioned", kw.get("location") or "stem",
             kw.get("option_label"), kw.get("confidence"), now),
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper", action="append", default=[])
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--model", default="deepseek-flash[1m]")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    exam = sqlite3.connect(EXAM_DB)
    exam.row_factory = sqlite3.Row
    know = sqlite3.connect(KNOW_DB)
    know.row_factory = sqlite3.Row
    kps, aliases, concept_of_kp = load_concepts(know)
    print("concepts:", len(kps))
    bm25_docs, bm25_idf = linker.build_bm25(kps, aliases)

    papers = args.paper or PAPERS
    report_rows = []
    for paper_id in papers:
        if not args.force:
            existing = know.execute(
                "SELECT COUNT(*) FROM question_analysis WHERE paper_id=?",
                (paper_id,),
            ).fetchone()[0]
            if existing:
                print("skip", paper_id, "already", existing)
                continue
        if args.force:
            qids = [row[0] for row in exam.execute(
                "SELECT question_id FROM questions WHERE paper_id=?", (paper_id,)
            )]
            if qids:
                marks = ",".join("?" for _ in qids)
                know.execute(f"DELETE FROM question_concept_links WHERE question_id IN ({marks})", qids)
                know.execute(f"DELETE FROM question_kp_links WHERE question_id IN ({marks})", qids)
                know.execute(f"DELETE FROM question_keywords WHERE question_id IN ({marks})", qids)
                know.execute(f"DELETE FROM question_analysis WHERE question_id IN ({marks})", qids)
                know.commit()
        questions = linker.load_questions(exam, paper_id)
        questions = [q for q in questions if q.get("correct_label")]
        if args.limit:
            questions = questions[:args.limit]
        scope, scope_kind = linker.infer_scope(paper_id)
        print(f"{paper_id}: {len(questions)} questions; scope={scope}")
        results, errors = {}, []
        started = time.time()
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {
                pool.submit(
                    linker.link_one, q, kps, aliases, scope, scope_kind,
                    bm25_docs, bm25_idf, args.model, 8000, 60, 2,
                ): q for q in questions
            }
            done = 0
            for future in as_completed(futures):
                q = futures[future]
                done += 1
                try:
                    result = future.result()
                    results[q["question_id"]] = result
                    print(f"[{done}/{len(questions)}] Q{q['number']} "
                          f"{result['status']} core={len(result['core'])} "
                          f"kw={len(result['keywords'])}", flush=True)
                except Exception as error:
                    errors.append((q["question_id"], str(error)))
                    print(f"[{done}/{len(questions)}] Q{q['number']} ERROR {error}",
                          flush=True)
        now = datetime.now().astimezone().isoformat(timespec="seconds")
        for q in questions:
            result = results.get(q["question_id"])
            if result:
                write_result(exam, know, paper_id, q, result, concept_of_kp, now)
        know.commit()
        report_rows.append((paper_id, len(questions), len(results), len(errors),
                            time.time() - started))
        print("paper done", paper_id, "linked", len(results), "errors", len(errors))

    with open(REPORT, "w", encoding="utf-8") as handle:
        handle.write("# Myers 概念层关联报告\n\n")
        handle.write("| Paper | 题数 | 成功 | 失败 | 秒 |\n")
        handle.write("|---|---:|---:|---:|---:|\n")
        for row in report_rows:
            handle.write(f"| `{row[0]}` | {row[1]} | {row[2]} | {row[3]} | {row[4]:.1f} |\n")
        handle.write("\n- Prompt: `myers-concept-link-v1`\n")
        handle.write("- 候选：规范概念（含 supporting），"
                     "题目单元优先；mock 用 BM25 全库候选。\n")
    print("report:", REPORT)
    exam.close()
    know.close()


if __name__ == "__main__":
    main()
