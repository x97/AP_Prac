#!/usr/bin/env python3
"""Validate a content release before activation.

Usage:
  python3 _tools/validate_content_release.py --release data/releases/<id>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def check(self, condition: bool, msg: str) -> None:
        if not condition:
            self.error(msg)


def connect_ro(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only = ON")
    return conn


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def scalar(conn: sqlite3.Connection, sql: str, params: tuple[Any, ...] = ()) -> int:
    row = conn.execute(sql, params).fetchone()
    return int(row[0] or 0)


def validate(release: Path) -> Report:
    r = Report()
    exam_path = release / "exam.db"
    knowledge_path = release / "knowledge.db"
    manifest_path = release / "assets-manifest.json"
    release_path = release / "release.json"

    for p in (exam_path, knowledge_path, manifest_path, release_path):
        if not p.exists():
            r.error(f"missing {p.name}")
            return r

    exam = connect_ro(exam_path)
    know = connect_ro(knowledge_path)

    # SQLite integrity.
    r.check(exam.execute("PRAGMA integrity_check").fetchone()[0] == "ok", "exam.db integrity_check failed")
    r.check(not exam.execute("PRAGMA foreign_key_check").fetchall(), "exam.db foreign_key_check failed")
    r.check(know.execute("PRAGMA integrity_check").fetchone()[0] == "ok", "knowledge.db integrity_check failed")

    # Subject isolation and core counts.
    r.check(scalar(exam, "SELECT COUNT(*) FROM papers WHERE subject_id='psychology'") == 39, "psychology paper count != 39")
    r.check(scalar(exam, "SELECT COUNT(*) FROM questions WHERE subject_id='psychology'") == 3155, "psychology question count != 3155")
    r.check(scalar(exam, "SELECT COUNT(*) FROM questions WHERE subject_id='psychology' AND section='MCQ'") == 3127, "psychology MCQ count != 3127")
    r.check(scalar(exam, "SELECT COUNT(*) FROM questions WHERE subject_id='psychology' AND section='FRQ'") == 28, "psychology FRQ count != 28")
    r.check(scalar(know, "SELECT COUNT(*) FROM concept_clusters WHERE subject_id='psychology'") == 1105, "psychology concept count != 1105")
    r.check(scalar(know, "SELECT COUNT(*) FROM knowledge_points WHERE book_id LIKE 'psychology-%'") == 1538, "psychology KP count != 1538")

    # Exclusions.
    excluded = {
        row["question_id"]
        for row in exam.execute("SELECT question_id FROM question_exclusions")
    }
    if not excluded:
        r.error("question_exclusions is empty")
    r.check(len(excluded) >= 4, "expected at least the 4 missing-answer exclusions")

    # Practice groups / topics.
    groups = exam.execute(
        "SELECT group_id, unit_id, bundle_paper_id FROM practice_groups WHERE subject_id='psychology' AND status='active'"
    ).fetchall()
    r.check(len(groups) == 5, f"expected 5 active practice groups, got {len(groups)}")
    topic_kinds = {
        row["kind"]: row["n"]
        for row in exam.execute("SELECT kind, COUNT(*) n FROM practice_topics GROUP BY kind")
    }
    r.check(topic_kinds.get("ced", 0) == 35, f"expected 35 CED topics, got {topic_kinds.get('ced', 0)}")
    r.check(topic_kinds.get("methods", 0) == 5, f"expected 5 methods topics, got {topic_kinds.get('methods', 0)}")
    r.check(topic_kinds.get("other", 0) <= 5, f"expected <=5 other topics, got {topic_kinds.get('other', 0)}")

    # Topic coverage: all included bundle questions have exactly one primary topic.
    for group in groups:
        gid = group["group_id"]
        bundle = group["bundle_paper_id"]
        if not bundle:
            r.error(f"{gid}: no bundle_paper_id")
            continue
        map_ids = {
            row["question_id"]
            for row in exam.execute(
                "SELECT question_id FROM paper_question_map WHERE paper_id=?", (bundle,)
            )
        }
        included = map_ids - excluded
        assigned = {
            row["question_id"]
            for row in exam.execute(
                """
                SELECT DISTINCT ptq.question_id
                FROM practice_topic_questions ptq
                JOIN practice_topics pt ON pt.topic_id = ptq.topic_id
                WHERE pt.group_id=? AND ptq.is_primary=1
                """,
                (gid,),
            )
        }
        r.check(included == assigned, f"{gid}: topic coverage mismatch ({len(included)} included, {len(assigned)} assigned)")
        r.check(not (assigned & excluded), f"{gid}: excluded questions present in practice topics")
        # Bundle order must be contiguous 1..N.
        sort_orders = [
            int(row["sort_order"])
            for row in exam.execute(
                "SELECT sort_order FROM paper_question_map WHERE paper_id=? ORDER BY sort_order",
                (bundle,),
            )
        ]
        r.check(sort_orders == list(range(1, len(sort_orders) + 1)), f"{bundle}: sort_order is not contiguous 1..N")
        dup_numbers = scalar(
            exam,
            "SELECT COUNT(*) FROM (SELECT number FROM paper_question_map WHERE paper_id=? GROUP BY number HAVING COUNT(*)>1)",
            (bundle,),
        )
        if dup_numbers:
            r.warn(f"{bundle}: {dup_numbers} duplicate paper_question_map.number values (expected; use sort_order)")

    # MCQ integrity for included questions (all real/mock + practice topic questions).
    included_mcq = """
        SELECT DISTINCT q.question_id
        FROM questions q
        WHERE q.subject_id='psychology' AND q.section='MCQ'
          AND (
            q.paper_id IN (SELECT paper_id FROM papers WHERE subject_id='psychology' AND paper_type IN ('real_exam','mock_exam'))
            OR q.question_id IN (SELECT question_id FROM practice_topic_questions)
          )
          AND q.question_id NOT IN (SELECT question_id FROM question_exclusions)
    """
    bad_options = exam.execute(
        f"""
        SELECT q.question_id,
               COUNT(o.label) n_opts,
               SUM(CASE WHEN o.is_correct=1 THEN 1 ELSE 0 END) n_correct,
               SUM(CASE WHEN o.content IS NULL OR trim(o.content)='' THEN 1 ELSE 0 END) n_empty
        FROM questions q LEFT JOIN options o ON o.question_id=q.question_id
        WHERE q.question_id IN ({included_mcq})
        GROUP BY q.question_id
        HAVING n_opts NOT IN (4,5) OR n_correct<>1 OR n_empty<>0
        """
    ).fetchall()
    for row in bad_options:
        r.error(
            f"{row['question_id']}: options={row['n_opts']} correct={row['n_correct']} empty={row['n_empty']}"
        )

    # Exam configs.
    config_rows = exam.execute("SELECT * FROM paper_exam_configs").fetchall()
    r.check(len(config_rows) == 14, f"expected 14 paper_exam_configs, got {len(config_rows)}")
    for cfg in config_rows:
        pid = cfg["paper_id"]
        actual_mcq = scalar(
            exam,
            "SELECT COUNT(*) FROM questions WHERE paper_id=? AND subject_id='psychology' AND section='MCQ'",
            (pid,),
        )
        actual_frq = scalar(
            exam,
            "SELECT COUNT(*) FROM questions WHERE paper_id=? AND subject_id='psychology' AND section='FRQ'",
            (pid,),
        )
        r.check(actual_mcq == cfg["mcq_count"], f"{pid}: MCQ {actual_mcq} != config {cfg['mcq_count']}")
        forms = json.loads(cfg["frq_forms"]) if cfg["frq_forms"] else []
        expected_frq = cfg["frq_count"] * len(forms) if forms else cfg["frq_count"]
        r.check(actual_frq == expected_frq, f"{pid}: FRQ {actual_frq} != config {expected_frq}")
        if pid == "psychology-ap-2018":
            r.check(cfg["frq_rubric_complete"] == 0, "2018 paper must flag frq_rubric_complete=0")

    # FRQ rubrics.
    for row in exam.execute(
        """
        SELECT fr.rubric_id, fr.question_id, fr.total_points, fr.format,
               SUM(rp.max_points) sum_parts, COUNT(rp.part_id) parts
        FROM frq_rubrics fr LEFT JOIN rubric_parts rp ON rp.rubric_id=fr.rubric_id
        GROUP BY fr.rubric_id
        """
    ):
        r.check(row["parts"] > 0, f"{row['rubric_id']}: no rubric parts")
        r.check(row["sum_parts"] == row["total_points"], f"{row['rubric_id']}: parts sum != total_points")
    # criteria JSON only for non-Barron formats.
    for row in exam.execute(
        """
        SELECT rp.part_id, rp.criteria, fr.format
        FROM rubric_parts rp JOIN frq_rubrics fr ON fr.rubric_id=rp.rubric_id
        WHERE fr.format <> 'barron_parts'
        """
    ):
        try:
            json.loads(row["criteria"])
        except Exception:
            r.error(f"{row['part_id']}: criteria is not valid JSON for format {row['format']}")

    # question_display coverage.
    missing_display = scalar(
        exam,
        """
        SELECT COUNT(*) FROM questions q
        WHERE q.subject_id='psychology'
          AND q.paper_id IN (SELECT paper_id FROM papers WHERE subject_id='psychology' AND paper_type IN ('real_exam','mock_exam','unit_practice'))
          AND NOT EXISTS (SELECT 1 FROM question_display d WHERE d.question_id=q.question_id)
        """,
    )
    r.check(missing_display == 0, f"{missing_display} questions missing question_display")

    # Assets: only referenced unique paths, exactly covered by the manifest.
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    asset_paths = {
        row["path"]
        for row in exam.execute(
            """
            SELECT DISTINCT a.path FROM assets a JOIN questions q ON q.question_id=a.question_id
            WHERE q.subject_id='psychology'
            """
        )
    }
    for path in asset_paths:
        local = release / path
        if not local.exists():
            r.error(f"missing asset file: {path}")
        if path not in manifest:
            r.error(f"asset not in manifest: {path}")
    r.check(len(asset_paths) > 0, "no psychology asset paths")
    r.check(set(manifest) == asset_paths, f"manifest keys != referenced asset paths ({len(manifest)} vs {len(asset_paths)})")

    # Pronunciation audio is kept in a separate manifest so the image asset
    # manifest remains exactly the set referenced by the exam DB.
    has_pronunciations = bool(
        know.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' "
            "AND name='concept_pronunciations'"
        ).fetchone()
    )
    pronunciation_count = 0
    if has_pronunciations:
        pronunciation_count = scalar(
            know,
            "SELECT COUNT(*) FROM concept_pronunciations p "
            "JOIN concept_clusters c ON c.cluster_id=p.cluster_id "
            "WHERE c.subject_id='psychology' AND p.audio_path IS NOT NULL",
        )
        r.check(
            pronunciation_count == 1105,
            f"expected 1105 pronunciation rows, got {pronunciation_count}",
        )
        empty_ipa = scalar(
            know,
            "SELECT COUNT(*) FROM concept_pronunciations "
            "WHERE TRIM(COALESCE(ipa, '')) = ''",
        )
        r.check(empty_ipa == 0, f"{empty_ipa} pronunciation rows have empty IPA")
        pron_manifest_path = release / "pronunciation-manifest.json"
        r.check(pron_manifest_path.exists(), "missing pronunciation-manifest.json")
        if pron_manifest_path.exists():
            pron_manifest = json.loads(pron_manifest_path.read_text(encoding="utf-8"))
            pron_paths = {
                row["audio_path"]
                for row in know.execute(
                    "SELECT p.audio_path FROM concept_pronunciations p "
                    "JOIN concept_clusters c ON c.cluster_id=p.cluster_id "
                    "WHERE c.subject_id='psychology' AND p.audio_path IS NOT NULL"
                )
            }
            r.check(
                set(pron_manifest) == pron_paths,
                "pronunciation manifest keys != referenced audio paths "
                f"({len(pron_manifest)} vs {len(pron_paths)})",
            )
            for path, item in pron_manifest.items():
                local = release / path
                if not local.exists():
                    r.error(f"missing pronunciation audio: {path}")
                elif local.stat().st_size == 0:
                    r.error(f"empty pronunciation audio: {path}")
                elif item.get("sha256") and item["sha256"] != sha256(local):
                    r.error(f"pronunciation audio sha256 mismatch: {path}")
    else:
        r.warn("concept_pronunciations table is absent (legacy Release)")

    # release.json counts/checksums.
    rel = json.loads(release_path.read_text(encoding="utf-8"))
    counts = rel.get("counts", {})
    total_questions = scalar(exam, "SELECT COUNT(*) FROM questions")
    total_mcqs = scalar(exam, "SELECT COUNT(*) FROM questions WHERE section='MCQ'")
    total_frqs = scalar(exam, "SELECT COUNT(*) FROM questions WHERE section='FRQ'")
    r.check(counts.get("questions") == total_questions, "release.json question count mismatch")
    r.check(counts.get("mcqs") == total_mcqs, "release.json MCQ count mismatch")
    r.check(counts.get("frqs") == total_frqs, "release.json FRQ count mismatch")
    if has_pronunciations:
        r.check(
            rel.get("pronunciations") == pronunciation_count,
            "release.json pronunciation count mismatch",
        )
        pron_checksum = (rel.get("checksums") or {}).get(
            "pronunciation-manifest.json"
        )
        if pron_checksum:
            r.check(
                pron_checksum
                == "sha256:" + sha256(release / "pronunciation-manifest.json"),
                "release.json checksum mismatch for pronunciation-manifest.json",
            )

    subjects = rel.get("subjects")
    if subjects is None:
        subjects = [rel.get("subject_id") or "psychology"]
    subjects = [str(item) for item in subjects]
    counts_by_subject = rel.get("counts_by_subject") or {}
    for subject_id in subjects:
        subject_questions = scalar(
            exam, "SELECT COUNT(*) FROM questions WHERE subject_id=?", (subject_id,)
        )
        subject_papers = scalar(
            exam, "SELECT COUNT(*) FROM papers WHERE subject_id=?", (subject_id,)
        )
        r.check(subject_questions > 0, f"{subject_id}: no questions in release")
        r.check(subject_papers > 0, f"{subject_id}: no papers in release")
        expected = counts_by_subject.get(subject_id)
        if expected is not None:
            r.check(
                expected.get("questions") == subject_questions,
                f"{subject_id}: counts_by_subject question count mismatch",
            )
    if subjects != ["psychology"]:
        r.warn(
            "merged multi-subject release: only psychology-specific content "
            "invariants are currently validated"
        )
    for name in ("exam.db", "knowledge.db"):
        expected = (rel.get("checksums") or {}).get(name, "")
        actual = "sha256:" + sha256(release / name)
        r.check(expected == actual, f"release.json checksum mismatch for {name}")

    exam.close()
    know.close()
    return r


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", required=True, type=Path)
    args = parser.parse_args()
    report = validate(args.release)
    for w in report.warnings:
        print(f"WARN: {w}")
    for e in report.errors:
        print(f"ERROR: {e}", file=sys.stderr)
    if report.errors:
        print(f"FAILED: {len(report.errors)} errors, {len(report.warnings)} warnings", file=sys.stderr)
        return 1
    print(f"OK: release valid ({len(report.warnings)} warnings)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
