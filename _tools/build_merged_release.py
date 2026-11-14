#!/usr/bin/env python3
"""Build one merged content Release from enabled subject source databases.

Source layout:
  data/content/<subject>/<subject>_exam.db
  data/content/<subject>/<subject>_knowledge.db

Output:
  data/releases/content-YYYYMMDD-HHMMSS/
    exam.db
    knowledge.db
    assets/
    assets-manifest.json
    release.json
    exclusions.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import build_exam_configs
import build_practice_topics
import subject_config
import validate_content_release

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "data" / "releases"
LOOKUP_TABLES = {"subjects", "paper_types", "subject_aliases"}
EXCLUDED_MERGE_TABLES = {"sqlite_sequence"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def backup_sqlite(src: Path, dst: Path) -> None:
    source = sqlite3.connect(f"file:{src}?mode=ro", uri=True)
    target = sqlite3.connect(str(dst))
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()


def table_names(conn: sqlite3.Connection) -> list[str]:
    return [
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        if row[0] not in EXCLUDED_MERGE_TABLES
    ]


def columns(conn: sqlite3.Connection, table: str) -> list[str]:
    if "." in table:
        schema, name = table.split(".", 1)
        return [row[1] for row in conn.execute(f"PRAGMA {schema}.table_info({name})")]
    return [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]


def merge_db(merged: Path, source: Path) -> None:
    conn = sqlite3.connect(str(merged))
    conn.execute("PRAGMA foreign_keys=OFF")
    conn.execute("ATTACH DATABASE ? AS src", (str(source),))
    source_tables = {
        row[0]
        for row in conn.execute("SELECT name FROM src.sqlite_master WHERE type='table'")
        if row[0] not in EXCLUDED_MERGE_TABLES
    }
    for table in table_names(conn):
        if table not in source_tables:
            continue
        common = [
            column
            for column in columns(conn, table)
            if column in columns(conn, f"src.{table}")
        ]
        if not common:
            continue
        columns_sql = ", ".join(common)
        mode = "INSERT OR IGNORE" if table in LOOKUP_TABLES else "INSERT"
        conn.execute(
            f"{mode} INTO {table} ({columns_sql}) SELECT {columns_sql} FROM src.{table}"
        )
    conn.commit()
    conn.execute("DETACH DATABASE src")
    conn.close()


def subject_counts(
    exam: sqlite3.Connection, know: sqlite3.Connection, subject: str
) -> dict[str, int]:
    def one(conn: sqlite3.Connection, sql: str, params: tuple[Any, ...] = ()) -> int:
        row = conn.execute(sql, params).fetchone()
        return int(row[0] or 0)

    return {
        "papers": one(
            exam, "SELECT COUNT(*) FROM papers WHERE subject_id=?", (subject,)
        ),
        "questions": one(
            exam, "SELECT COUNT(*) FROM questions WHERE subject_id=?", (subject,)
        ),
        "mcqs": one(
            exam,
            "SELECT COUNT(*) FROM questions WHERE subject_id=? AND section='MCQ'",
            (subject,),
        ),
        "frqs": one(
            exam,
            "SELECT COUNT(*) FROM questions WHERE subject_id=? AND section='FRQ'",
            (subject,),
        ),
        "concepts": one(
            know, "SELECT COUNT(*) FROM concept_clusters WHERE subject_id=?", (subject,)
        ),
        "kps": one(
            know,
            "SELECT COUNT(*) FROM knowledge_points kp JOIN books b ON b.book_id=kp.book_id "
            "WHERE b.subject_id=?",
            (subject,),
        ),
        "practice_groups": one(
            exam,
            "SELECT COUNT(*) FROM practice_groups WHERE subject_id=? AND status='active'",
            (subject,),
        ),
    }


def build_manifest(asset_paths: list[str], release_root: Path) -> dict[str, Any]:
    manifest: dict[str, Any] = {}
    for rel in sorted(set(asset_paths)):
        path = release_root / rel
        if not path.is_file():
            raise FileNotFoundError(f"asset missing in release: {rel}")
        mime, _ = mimetypes.guess_type(path.name)
        manifest[rel] = {
            "path": rel,
            "sha256": sha256(path),
            "size": path.stat().st_size,
            "mime": mime or "application/octet-stream",
        }
    return manifest


def build(
    release_id: str,
    out_dir: Path,
    subjects: list[dict[str, Any]],
    dry_run: bool = False,
) -> int:
    if not subjects:
        print("No enabled subjects", file=sys.stderr)
        return 2
    staging = out_dir / ".staging" / release_id
    final = out_dir / release_id
    if final.exists() or staging.exists():
        print(f"release or staging already exists: {release_id}", file=sys.stderr)
        return 2
    staging.mkdir(parents=True)
    subject_staging = staging / ".subjects"
    subject_staging.mkdir()

    prepared: list[tuple[dict[str, Any], Path, Path]] = []
    for config in subjects:
        subject = config["subject_id"]
        paths = subject_config.source_paths(config)
        if not paths["exam_db"].exists() or not paths["knowledge_db"].exists():
            print(f"source DB missing for {subject}", file=sys.stderr)
            return 2
        work = subject_staging / subject
        work.mkdir()
        exam = work / "exam.db"
        know = work / "knowledge.db"
        backup_sqlite(paths["exam_db"], exam)
        backup_sqlite(paths["knowledge_db"], know)
        rc = build_exam_configs.build(
            exam, paths["exam_config"], dry_run=False, subject_id=subject
        )
        if rc:
            return rc
        rc = build_practice_topics.build(
            exam,
            know,
            paths["practice_topics"],
            paths["exclusions"],
            dry_run=False,
            subject_id=subject,
        )
        if rc:
            return rc
        prepared.append((config, exam, know))

    _first_config, first_exam, first_know = prepared[0]
    merged_exam = staging / "exam.db"
    merged_know = staging / "knowledge.db"
    shutil.copy2(first_exam, merged_exam)
    shutil.copy2(first_know, merged_know)
    for _config, exam, know in prepared[1:]:
        merge_db(merged_exam, exam)
        merge_db(merged_know, know)

    conn = sqlite3.connect(str(merged_exam))
    conn.row_factory = sqlite3.Row
    kconn = sqlite3.connect(str(merged_know))
    kconn.row_factory = sqlite3.Row
    per_subject = {
        config["subject_id"]: subject_counts(conn, kconn, config["subject_id"])
        for config, _, _ in prepared
    }
    subjects_ids = [config["subject_id"] for config, _, _ in prepared]

    asset_rows = conn.execute(
        f"""
        SELECT DISTINCT a.path
        FROM assets a
        JOIN questions q ON q.question_id=a.question_id
        WHERE q.subject_id IN ({",".join("?" for _ in subjects_ids)})
        ORDER BY a.path
        """,
        subjects_ids,
    ).fetchall()
    asset_paths = [row[0] for row in asset_rows]
    pronunciation_rows: list[sqlite3.Row] = []
    if kconn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' "
        "AND name='concept_pronunciations'"
    ).fetchone():
        pronunciation_rows = kconn.execute(
            """
            SELECT p.cluster_id, p.term, p.ipa, p.audio_path, p.audio_sha256,
                   p.duration_ms, p.sample_rate, p.bitrate_kbps, p.voice, p.speed,
                   p.engine
            FROM concept_pronunciations p
            JOIN concept_clusters c ON c.cluster_id=p.cluster_id
            WHERE c.subject_id IN ({})
            ORDER BY p.cluster_id
            """.format(",".join("?" for _ in subjects_ids)),
            subjects_ids,
        ).fetchall()
    conn.close()
    kconn.close()

    for rel in asset_paths:
        src = ROOT / rel
        if not src.is_file():
            print(f"missing source asset: {src}", file=sys.stderr)
            return 2
        dst = staging / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    manifest = build_manifest(asset_paths, staging)
    (staging / "assets-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    pronunciation_manifest: dict[str, Any] = {}
    for row in pronunciation_rows:
        rel = str(row["audio_path"] or "")
        if not rel:
            continue
        src = ROOT / rel
        if not src.is_file():
            print(f"missing pronunciation audio: {src}", file=sys.stderr)
            return 2
        dst = staging / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        mime, _ = mimetypes.guess_type(src.name)
        pronunciation_manifest[rel] = {
            "path": rel,
            "sha256": row["audio_sha256"] or sha256(src),
            "size": src.stat().st_size,
            "mime": mime or "audio/mpeg",
            "cluster_id": row["cluster_id"],
            "term": row["term"],
            "ipa": row["ipa"],
            "duration_ms": row["duration_ms"],
            "sample_rate": row["sample_rate"],
            "bitrate_kbps": row["bitrate_kbps"],
            "voice": row["voice"],
            "speed": row["speed"],
            "engine": row["engine"],
        }
    (staging / "pronunciation-manifest.json").write_text(
        json.dumps(pronunciation_manifest, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    exclusions = {}
    for config, _, _ in prepared:
        path = subject_config.source_paths(config)["exclusions"]
        if path.exists():
            exclusions[config["subject_id"]] = json.loads(
                path.read_text(encoding="utf-8")
            )
    (staging / "exclusions.json").write_text(
        json.dumps(exclusions, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    exam = sqlite3.connect(f"file:{merged_exam}?mode=ro", uri=True)
    know = sqlite3.connect(f"file:{merged_know}?mode=ro", uri=True)
    tot = {
        key: sum(item[key] for item in per_subject.values())
        for key in next(iter(per_subject.values()))
    }
    exam.close()
    know.close()

    release_json = {
        "release_id": release_id,
        "subjects": subjects_ids,
        "schema_version": 1,
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source": "merged-subject-sources",
        "counts_by_subject": per_subject,
        "counts": tot,
        "pronunciations": len(pronunciation_manifest),
        "checksums": {
            "exam.db": "sha256:" + sha256(merged_exam),
            "knowledge.db": "sha256:" + sha256(merged_know),
            "assets-manifest.json": "sha256:"
            + sha256(staging / "assets-manifest.json"),
            "pronunciation-manifest.json": "sha256:"
            + sha256(staging / "pronunciation-manifest.json"),
        },
    }
    (staging / "release.json").write_text(
        json.dumps(release_json, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    report = validate_content_release.validate(staging)
    for warning in report.warnings:
        print(f"WARN: {warning}")
    for error in report.errors:
        print(f"ERROR: {error}", file=sys.stderr)
    if report.errors:
        print(f"validation failed; staging kept at {staging}", file=sys.stderr)
        return 1

    if dry_run:
        print(f"dry-run OK; staging kept at {staging}")
        return 0
    shutil.rmtree(staging / ".subjects", ignore_errors=True)
    staging.rename(final)
    print(f"merged release built: {final}")
    print(json.dumps(per_subject, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-id", default=None)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    subjects = subject_config.enabled_subjects()
    release_id = (
        args.release_id or f"content-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    )
    if not subjects:
        print("No enabled subject configs", file=sys.stderr)
        return 2
    return build(release_id, args.output_dir, subjects, args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
