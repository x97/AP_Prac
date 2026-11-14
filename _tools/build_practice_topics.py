#!/usr/bin/env python3
"""Build Unit -> CED topic -> question mappings in a staging/release exam DB.

Unit membership comes from practice_groups/paper_question_map, never from
concept_clusters.ap_unit. Topic assignment uses core/supporting/confusable
concept links and the curated config in config/practice_topics/psychology.json.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TOPICS = ROOT / "config" / "practice_topics" / "psychology.json"
DEFAULT_EXCLUSIONS = ROOT / "config" / "content_exclusions" / "psychology.json"

SCHEMA = """
CREATE TABLE IF NOT EXISTS practice_topics (
    topic_id TEXT PRIMARY KEY,
    group_id TEXT NOT NULL,
    unit_id TEXT NOT NULL,
    code TEXT NOT NULL,
    title_zh TEXT NOT NULL,
    title_en TEXT NOT NULL,
    kind TEXT NOT NULL,
    sort_order INTEGER NOT NULL,
    question_count INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS practice_topic_questions (
    topic_id TEXT NOT NULL,
    question_id TEXT NOT NULL,
    is_primary INTEGER NOT NULL DEFAULT 1,
    sort_order INTEGER NOT NULL,
    PRIMARY KEY (topic_id, question_id)
);
CREATE TABLE IF NOT EXISTS practice_topic_concepts (
    topic_id TEXT NOT NULL,
    concept_id TEXT NOT NULL,
    weight REAL NOT NULL,
    sort_order INTEGER NOT NULL,
    PRIMARY KEY (topic_id, concept_id)
);
CREATE TABLE IF NOT EXISTS question_exclusions (
    question_id TEXT PRIMARY KEY,
    reason TEXT NOT NULL,
    note TEXT
);
CREATE TABLE IF NOT EXISTS question_display (
    question_id TEXT PRIMARY KEY,
    display_number INTEGER NOT NULL,
    note TEXT
);
CREATE INDEX IF NOT EXISTS idx_ptq_topic ON practice_topic_questions(topic_id, sort_order);
CREATE INDEX IF NOT EXISTS idx_ptq_question ON practice_topic_questions(question_id);
CREATE INDEX IF NOT EXISTS idx_ptc_topic ON practice_topic_concepts(topic_id, sort_order);
"""


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def chunked(values: list[str], size: int = 500):
    for i in range(0, len(values), size):
        yield values[i : i + size]


def in_clause(values: list[str]) -> tuple[str, list[str]]:
    return ",".join("?" for _ in values), values


def build_topic_defs(cfg: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    units: dict[str, list[dict[str, Any]]] = {}
    for unit in cfg["units"]:
        group_id = unit["group_id"]
        unit_id = unit["unit_id"]
        defs = []
        for i, topic in enumerate(unit["topics"]):
            defs.append(
                {
                    "topic_id": f"{group_id}:{topic['code']}",
                    "group_id": group_id,
                    "unit_id": unit_id,
                    "code": topic["code"],
                    "title_zh": topic["title_zh"],
                    "title_en": topic["title_en"],
                    "kind": topic.get("kind", "ced"),
                    "sort_order": i + 1,
                    "match_topics": [m.lower() for m in topic.get("match_topics", [])],
                    "match_keywords": [
                        k.lower() for k in topic.get("match_keywords", [])
                    ],
                }
            )
        units[unit_id] = defs
    return units


def match_topic(concept: dict[str, Any], topic: dict[str, Any]) -> int:
    """Return a match score: 4 exact topic, 3 topic prefix, 2 keyword, 0 none."""
    concept_topic = (concept.get("topic") or "").strip().lower()
    canonical = (concept.get("canonical_name") or "").strip().lower()
    for m in topic["match_topics"]:
        if concept_topic == m:
            return 4
        if concept_topic.startswith(m):
            return 3
    if any(k in canonical for k in topic["match_keywords"]):
        return 2
    return 0


def assign_question(
    links: list[dict[str, Any]],
    concepts: dict[str, dict[str, Any]],
    topics: list[dict[str, Any]],
    sort_order: int,
    fallback: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    """Pick one primary topic. Returns (topic, reason)."""
    best: tuple[Any, ...] | None = None
    best_topic: dict[str, Any] | None = None
    best_reason = ""
    for link in links:
        concept = concepts.get(link["concept_id"])
        if not concept:
            continue
        relation = link.get("relation_type") or ""
        relation_priority = {"core": 3, "supporting": 2, "confusable": 1}.get(
            relation, 0
        )
        if relation_priority == 0:
            continue
        ap_unit = str(concept.get("ap_unit") or "").strip()
        is_methods_concept = ap_unit in {"0", "EM"}
        confidence = float(link.get("confidence") or 0.0)
        weight = float(concept.get("weight") or 0.0)

        for topic in topics:
            is_methods_topic = topic["kind"] == "methods"
            if is_methods_concept:
                if not is_methods_topic:
                    continue
                score = 4
                reason = f"methods:{concept.get('canonical_name')}"
            else:
                if is_methods_topic:
                    continue
                score = match_topic(concept, topic)
                if score == 0:
                    continue
                reason = f"topic:{concept.get('topic')}|{concept.get('canonical_name')}"
            candidate = (
                relation_priority,
                0 if not is_methods_topic else 1,
                score,
                confidence,
                weight,
                -sort_order,
            )
            if best is None or candidate > best:
                best = candidate
                best_topic = topic
                best_reason = reason
    if best_topic is not None:
        return best_topic, best_reason

    # No concept match: prefer methods if the question has any methods concept,
    # otherwise put it in the unit's "other" bucket.
    if any(
        str((concepts.get(l["concept_id"]) or {}).get("ap_unit") or "") in {"0", "EM"}
        for l in links
    ):
        for topic in topics:
            if topic["kind"] == "methods":
                return topic, "methods:fallback"
    return fallback, "other:fallback"


def build(
    exam_db: Path,
    knowledge_db: Path,
    topics_path: Path,
    exclusions_path: Path,
    dry_run: bool = False,
    subject_id: str = "psychology",
) -> int:
    cfg = load_json(topics_path)
    exclusions = load_json(exclusions_path).get("exclusions", [])
    units = build_topic_defs(cfg)

    conn = sqlite3.connect(str(exam_db))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    if not dry_run:
        conn.executescript(SCHEMA)

    kconn = sqlite3.connect(f"file:{knowledge_db}?mode=ro", uri=True)
    kconn.row_factory = sqlite3.Row
    kconn.execute("PRAGMA query_only = ON")

    # Seed exclusions only when writing.
    excluded = {e["question_id"] for e in exclusions}
    if not dry_run:
        conn.executemany(
            "INSERT OR REPLACE INTO question_exclusions(question_id, reason, note) VALUES (?, ?, ?)",
            [(e["question_id"], e["reason"], e.get("note", "")) for e in exclusions],
        )

    groups = conn.execute(
        """
        SELECT group_id, unit_id, bundle_paper_id
        FROM practice_groups
        WHERE subject_id = ? AND status = 'active'
        ORDER BY CAST(unit_id AS INTEGER), unit_id
        """,
        (subject_id,),
    ).fetchall()
    if not groups:
        print(f"No active {subject_id} practice_groups found", file=sys.stderr)
        conn.close()
        kconn.close()
        return 1

    all_topic_rows: list[tuple[Any, ...]] = []
    all_question_rows: list[tuple[Any, ...]] = []
    all_concept_rows: list[tuple[Any, ...]] = []
    report: list[dict[str, Any]] = []

    for group in groups:
        group_id = group["group_id"]
        unit_id = str(group["unit_id"])
        bundle_id = group["bundle_paper_id"]
        if not bundle_id:
            print(f"WARN: {group_id} has no bundle_paper_id", file=sys.stderr)
            continue
        topic_defs = list(units.get(unit_id, []))
        if not topic_defs:
            print(f"WARN: no topic config for unit {unit_id}", file=sys.stderr)
            continue
        fallback = {
            "topic_id": f"{group_id}:{unit_id}.OT",
            "group_id": group_id,
            "unit_id": unit_id,
            "code": f"{unit_id}.OT",
            "title_zh": "综合/其他",
            "title_en": "Other",
            "kind": "other",
            "sort_order": 999,
            "match_topics": [],
            "match_keywords": [],
        }
        all_topics = topic_defs + [fallback]

        rows = conn.execute(
            "SELECT question_id, sort_order FROM paper_question_map WHERE paper_id=? ORDER BY sort_order",
            (bundle_id,),
        ).fetchall()
        if not rows:
            print(
                f"WARN: bundle {bundle_id} has no paper_question_map rows",
                file=sys.stderr,
            )
            continue
        question_ids = [
            r["question_id"] for r in rows if r["question_id"] not in excluded
        ]
        sort_by_q = {r["question_id"]: int(r["sort_order"]) for r in rows}
        if not question_ids:
            continue

        # Concept links for the included questions.
        placeholders, params = in_clause(question_ids)
        link_rows = kconn.execute(
            f"""
            SELECT question_id, concept_id, relation_type, confidence
            FROM question_concept_links
            WHERE question_id IN ({placeholders})
              AND relation_type IN ('core', 'supporting', 'confusable')
            """,
            params,
        ).fetchall()
        links_by_q: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for r in link_rows:
            links_by_q[r["question_id"]].append(dict(r))
        concept_ids = sorted({r["concept_id"] for r in link_rows})
        concepts: dict[str, dict[str, Any]] = {}
        if concept_ids:
            placeholders, params = in_clause(concept_ids)
            for r in kconn.execute(
                f"""
                SELECT cluster_id, canonical_name, topic, ap_unit, weight
                FROM concept_clusters
                WHERE subject_id=? AND cluster_id IN ({placeholders})
                """,
                (subject_id, *params),
            ):
                concepts[r["cluster_id"]] = dict(r)

        topic_questions: dict[str, list[tuple[int, str]]] = defaultdict(list)
        topic_concept_weights: dict[str, dict[str, float]] = defaultdict(dict)
        other_count = 0
        for qid in question_ids:
            topic, _reason = assign_question(
                links_by_q.get(qid, []),
                concepts,
                topic_defs,
                sort_by_q[qid],
                fallback,
            )
            if topic["kind"] == "other":
                other_count += 1
            topic_questions[topic["topic_id"]].append((sort_by_q[qid], qid))
            for link in links_by_q.get(qid, []):
                c = concepts.get(link["concept_id"])
                if not c:
                    continue
                topic_concept_weights[topic["topic_id"]][link["concept_id"]] = max(
                    topic_concept_weights[topic["topic_id"]].get(
                        link["concept_id"], 0.0
                    ),
                    float(c.get("weight") or 0.0),
                )

        for topic in all_topics:
            qrows = topic_questions.get(topic["topic_id"], [])
            if topic["kind"] == "other" and not qrows:
                continue
            count = len(qrows)
            all_topic_rows.append(
                (
                    topic["topic_id"],
                    group_id,
                    unit_id,
                    topic["code"],
                    topic["title_zh"],
                    topic["title_en"],
                    topic["kind"],
                    topic["sort_order"],
                    count,
                )
            )
            for sort_order, qid in sorted(qrows):
                all_question_rows.append((topic["topic_id"], qid, 1, sort_order))
            top_concepts = sorted(
                topic_concept_weights.get(topic["topic_id"], {}).items(),
                key=lambda kv: (-kv[1], kv[0]),
            )[:20]
            for i, (cid, weight) in enumerate(top_concepts, start=1):
                all_concept_rows.append((topic["topic_id"], cid, weight, i))

        report.append(
            {
                "group_id": group_id,
                "bundle_id": bundle_id,
                "included": len(question_ids),
                "excluded": len(rows) - len(question_ids),
                "other": other_count,
                "topics": {
                    t["code"]: len(topic_questions.get(t["topic_id"], []))
                    for t in all_topics
                },
            }
        )

    # question_display for paper-level questions (bundle display uses sort_order).
    display_rows = []
    for row in conn.execute(
        """
        SELECT question_id, section, number, form, paper_id
        FROM questions
        WHERE subject_id=?
          AND paper_id IN (
            SELECT paper_id FROM papers
            WHERE subject_id=? AND paper_type IN ('real_exam','mock_exam','unit_practice')
          )
        ORDER BY paper_id, section, number
        """,
        (subject_id, subject_id),
    ):
        number = int(row["number"] or 0)
        display = number
        note = None
        if row["section"] == "FRQ" and row["form"] == "Set 2" and number >= 3:
            display = number - 2
            note = "Set 2 display-local"
        display_rows.append((row["question_id"], display, note))

    if dry_run:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        print(
            f"Would write {len(all_topic_rows)} topics, {len(all_question_rows)} topic-question rows, {len(display_rows)} display rows"
        )
        conn.close()
        kconn.close()
        return 0

    conn.execute("DELETE FROM practice_topic_questions")
    conn.execute("DELETE FROM practice_topic_concepts")
    conn.execute("DELETE FROM practice_topics")
    conn.execute("DELETE FROM question_display")
    conn.executemany(
        "INSERT INTO practice_topics(topic_id, group_id, unit_id, code, title_zh, title_en, kind, sort_order, question_count) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        all_topic_rows,
    )
    conn.executemany(
        "INSERT INTO practice_topic_questions(topic_id, question_id, is_primary, sort_order) VALUES (?, ?, ?, ?)",
        all_question_rows,
    )
    conn.executemany(
        "INSERT INTO practice_topic_concepts(topic_id, concept_id, weight, sort_order) VALUES (?, ?, ?, ?)",
        all_concept_rows,
    )
    conn.executemany(
        "INSERT INTO question_display(question_id, display_number, note) VALUES (?, ?, ?)",
        display_rows,
    )
    conn.commit()
    conn.close()
    kconn.close()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(
        f"Wrote {len(all_topic_rows)} topics, {len(all_question_rows)} topic-question rows, "
        f"{len(all_concept_rows)} topic-concept rows, {len(display_rows)} display rows"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exam-db", required=True, type=Path)
    parser.add_argument("--knowledge-db", required=True, type=Path)
    parser.add_argument("--topics", type=Path, default=None)
    parser.add_argument("--exclusions", type=Path, default=None)
    parser.add_argument("--subject", default="psychology")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    for p in (args.exam_db, args.knowledge_db):
        if not p.exists():
            print(f"not found: {p}", file=sys.stderr)
            return 2
    return build(
        args.exam_db,
        args.knowledge_db,
        args.topics,
        args.exclusions,
        args.dry_run,
        args.subject,
    )


if __name__ == "__main__":
    raise SystemExit(main())
