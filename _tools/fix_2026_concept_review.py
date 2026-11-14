#!/usr/bin/env python3
"""Manual review overrides for three 2026 concept links.

The automated linker is otherwise accepted. These overrides correct concepts
that were visibly mismatched or only partially matched:

  * Q65: Vygotsky's sociocultural theory, not ecological systems theory.
  * Q69: limited sample -> representative sample/generalizability, not the
    two broad "population/random sampling" cores.
  * Q21: model itself marked needs_review, but the cognitive-dissonance core
    and distractors were manually confirmed.

The script updates both question_concept_links (primary) and the legacy
question_kp_links mirror.
"""

from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data/content/psychology/psychology_knowledge.db"
PAPER_ID = "psychology-ap-2026"

Q65 = "psychology-2026-mcq-065"
Q69 = "psychology-2026-mcq-069"
Q21 = "psychology-2026-mcq-021"

SOCIAL_CULTURAL_CLUSTER = "psy-support-012512d5a73f2605"
SOCIAL_CULTURAL_KP = "psychology-barrons-2027-kp-e6341ef63e45ca1b"
ECOLOGICAL_CLUSTER = "psy-concept-fc3790392bd5c6dc"
ECOLOGICAL_KP = None
REPRESENTATIVE_CLUSTER = "psy-support-d55d0168ef67ac07"
REPRESENTATIVE_KP = "psychology-barrons-2027-kp-8c677600dba5afaa"
POPULATION_CLUSTER = "psy-concept-3e0bd990a3b67d73"
RANDOM_SAMPLING_CLUSTER = "psy-support-9208e1f59f3955f8"


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def canonical_kp(conn: sqlite3.Connection, cluster_id: str) -> str:
    row = conn.execute(
        "SELECT canonical_kp_id FROM concept_clusters WHERE cluster_id=?",
        (cluster_id,),
    ).fetchone()
    if not row or not row[0]:
        raise ValueError(f"no canonical_kp_id for {cluster_id}")
    return row[0]


def main() -> int:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = DB.with_name(f"{DB.name}.bak-{stamp}-concept-review-2026")
    shutil.copy2(DB, backup)
    print(f"backup: {backup}")

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    now = now_iso()
    try:
        conn.execute("BEGIN IMMEDIATE")

        # Q65: replace the wrong ecological-systems core with sociocultural.
        conn.execute(
            "DELETE FROM question_concept_links WHERE question_id=? AND concept_id=?",
            (Q65, ECOLOGICAL_CLUSTER),
        )
        conn.execute(
            """
            INSERT INTO question_concept_links
              (question_id, concept_id, relation_type, option_label, confidence,
               evidence, rationale, created_at)
            VALUES (?, ?, 'core', NULL, 0.9, ?, ?, ?)
            ON CONFLICT(question_id, concept_id, relation_type, IFNULL(option_label,''))
            DO UPDATE SET confidence=excluded.confidence, evidence=excluded.evidence,
                          rationale=excluded.rationale, created_at=excluded.created_at
            """,
            (
                Q65,
                SOCIAL_CULTURAL_CLUSTER,
                "Vygotsky’s theory of cognitive development",
                "The correct answer is Vygotsky's sociocultural theory, not "
                "ecological systems theory.",
                now,
            ),
        )
        conn.execute(
            "DELETE FROM question_kp_links WHERE question_id=? AND kp_id=? AND relation_type='core'",
            (Q65, "psychology-barrons-2027-kp-62e437f26193c4b1"),
        )
        conn.execute(
            """
            INSERT INTO question_kp_links
              (question_id, kp_id, relation_type, option_label, confidence,
               evidence, rationale, created_at)
            VALUES (?, ?, 'core', NULL, 0.9, ?, ?, ?)
            ON CONFLICT(question_id, kp_id, relation_type, IFNULL(option_label,''))
            DO UPDATE SET confidence=excluded.confidence, evidence=excluded.evidence,
                          rationale=excluded.rationale, created_at=excluded.created_at
            """,
            (
                Q65,
                SOCIAL_CULTURAL_KP,
                "Vygotsky’s theory of cognitive development",
                "Manual review: sociocultural theory is the tested concept.",
                now,
            ),
        )

        # Q69: representative sample is the core; population/random sampling
        # are supporting context.
        conn.execute(
            "UPDATE question_concept_links SET relation_type='supporting', confidence=0.6 "
            "WHERE question_id=? AND concept_id IN (?, ?) AND relation_type='core'",
            (Q69, POPULATION_CLUSTER, RANDOM_SAMPLING_CLUSTER),
        )
        conn.execute(
            "UPDATE question_concept_links SET relation_type='core', confidence=0.9, "
            "evidence=?, rationale=? "
            "WHERE question_id=? AND concept_id=?",
            (
                "The sample is limited to Missouri high school students.",
                "A non-representative, geographically limited sample weakens "
                "generalizability.",
                Q69,
                REPRESENTATIVE_CLUSTER,
            ),
        )
        conn.execute(
            "UPDATE question_kp_links SET relation_type='supporting', confidence=0.6 "
            "WHERE question_id=? AND relation_type='core' AND kp_id IN "
            "(SELECT canonical_kp_id FROM concept_clusters WHERE cluster_id IN (?, ?))",
            (Q69, POPULATION_CLUSTER, RANDOM_SAMPLING_CLUSTER),
        )
        conn.execute(
            """
            INSERT INTO question_kp_links
              (question_id, kp_id, relation_type, option_label, confidence,
               evidence, rationale, created_at)
            VALUES (?, ?, 'core', NULL, 0.9, ?, ?, ?)
            ON CONFLICT(question_id, kp_id, relation_type, IFNULL(option_label,''))
            DO UPDATE SET confidence=excluded.confidence, evidence=excluded.evidence,
                          rationale=excluded.rationale, created_at=excluded.created_at
            """,
            (
                Q69,
                REPRESENTATIVE_KP,
                "The sample is limited to Missouri high school students.",
                "Manual review: limited sample -> representative sample.",
                now,
            ),
        )

        # Q21: manual confirmation of a good core/confusable set.
        conn.execute(
            "UPDATE question_analysis SET status='linked', notes=?, updated_at=? "
            "WHERE question_id=?",
            (
                "Manual review confirmed cognitive dissonance as core; "
                "deindividuation, conformity, and reaction formation are confusables.",
                now,
                Q21,
            ),
        )

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    # Verification.
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    q65 = conn.execute(
        "SELECT c.canonical_name FROM question_concept_links l "
        "JOIN concept_clusters c ON c.cluster_id=l.concept_id "
        "WHERE l.question_id=? AND l.relation_type='core'",
        (Q65,),
    ).fetchall()
    q69 = conn.execute(
        "SELECT c.canonical_name,l.relation_type FROM question_concept_links l "
        "JOIN concept_clusters c ON c.cluster_id=l.concept_id "
        "WHERE l.question_id=? AND c.cluster_id IN (?,?,?) ORDER BY l.relation_type",
        (Q69, REPRESENTATIVE_CLUSTER, POPULATION_CLUSTER, RANDOM_SAMPLING_CLUSTER),
    ).fetchall()
    q21 = conn.execute(
        "SELECT status FROM question_analysis WHERE question_id=?", (Q21,)
    ).fetchone()
    if [r["canonical_name"] for r in q65] != ["Social-Cultural (or Sociocultural) Perspective"]:
        raise ValueError(f"Q65 review failed: {q65}")
    if not any(
        r["canonical_name"] == "Representative sample" and r["relation_type"] == "core"
        for r in q69
    ):
        raise ValueError(f"Q69 review failed: {q69}")
    if q21["status"] != "linked":
        raise ValueError(f"Q21 status failed: {q21}")
    if conn.execute("PRAGMA foreign_key_check").fetchall():
        raise ValueError("foreign_key_check failed")
    if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        raise ValueError("integrity_check failed")
    conn.close()
    print("concept review overrides committed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
