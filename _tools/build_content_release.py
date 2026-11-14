#!/usr/bin/env python3
"""LEGACY: build a single-subject release from the psychology source DBs.

Deprecated for new work. Use ``_tools/build_merged_release.py`` so every
enabled subject is read from ``data/content/<subject>/`` and merged into one
release.

The psychology source DBs are never modified. All derived tables
(paper_exam_configs, practice_topics, question_display, exclusions) are built
inside data/releases/.staging/<release_id>/ and then validated.
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

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "data" / "releases"
EXAM_CONFIG = ROOT / "config" / "exam_formats" / "psychology.json"
TOPIC_CONFIG = ROOT / "config" / "practice_topics" / "psychology.json"
EXCLUSIONS = ROOT / "config" / "content_exclusions" / "psychology.json"

import build_exam_configs  # noqa: E402
import build_practice_topics  # noqa: E402
import validate_content_release  # noqa: E402


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def backup_sqlite(src: Path, dst: Path) -> None:
    source = sqlite3.connect(f"file:{src}?mode=ro", uri=True)
    target = sqlite3.connect(str(dst))
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()


def build_manifest(asset_paths: list[str], release_root: Path) -> dict[str, Any]:
    manifest: dict[str, Any] = {}
    try:
        from PIL import Image  # type: ignore
    except Exception:
        Image = None  # type: ignore
    for rel in sorted(asset_paths):
        path = release_root / rel
        if not path.is_file():
            raise FileNotFoundError(f"asset missing in staging: {rel}")
        mime, _ = mimetypes.guess_type(path.name)
        item: dict[str, Any] = {
            "path": rel,
            "sha256": sha256(path),
            "size": path.stat().st_size,
            "mime": mime or "application/octet-stream",
        }
        if Image is not None:
            try:
                with Image.open(path) as img:
                    item["width"], item["height"] = img.size
            except Exception:
                pass
        manifest[rel] = item
    return manifest


def counts(exam: sqlite3.Connection, know: sqlite3.Connection) -> dict[str, Any]:
    def one(conn: sqlite3.Connection, sql: str, params: tuple[Any, ...] = ()) -> int:
        row = conn.execute(sql, params).fetchone()
        return int(row[0] or 0)

    return {
        "papers": one(exam, "SELECT COUNT(*) FROM papers WHERE subject_id='psychology'"),
        "questions": one(exam, "SELECT COUNT(*) FROM questions WHERE subject_id='psychology'"),
        "mcqs": one(exam, "SELECT COUNT(*) FROM questions WHERE subject_id='psychology' AND section='MCQ'"),
        "frqs": one(exam, "SELECT COUNT(*) FROM questions WHERE subject_id='psychology' AND section='FRQ'"),
        "options": one(exam, "SELECT COUNT(*) FROM options o JOIN questions q ON q.question_id=o.question_id WHERE q.subject_id='psychology'"),
        "concepts": one(know, "SELECT COUNT(*) FROM concept_clusters WHERE subject_id='psychology'"),
        "kps": one(know, "SELECT COUNT(*) FROM knowledge_points WHERE book_id LIKE 'psychology-%'"),
        "practice_groups": one(exam, "SELECT COUNT(*) FROM practice_groups WHERE subject_id='psychology' AND status='active'"),
        "practice_topics": one(exam, "SELECT COUNT(*) FROM practice_topics"),
        "exam_configs": one(exam, "SELECT COUNT(*) FROM paper_exam_configs"),
        "exclusions": one(exam, "SELECT COUNT(*) FROM question_exclusions"),
        "assets": one(exam, "SELECT COUNT(*) FROM assets a JOIN questions q ON q.question_id=a.question_id WHERE q.subject_id='psychology'"),
        "asset_files": one(exam, "SELECT COUNT(DISTINCT a.path) FROM assets a JOIN questions q ON q.question_id=a.question_id WHERE q.subject_id='psychology'"),
    }


def build(
    release_id: str,
    out_dir: Path,
    dry_run: bool = False,
) -> int:
    staging_parent = out_dir / ".staging"
    staging = staging_parent / release_id
    final = out_dir / release_id
    if final.exists():
        print(f"release already exists: {final}", file=sys.stderr)
        return 2
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)

    print(f"staging: {staging}")
    backup_sqlite(ROOT / "data" / "content" / "psychology" / "psychology_exam.db", staging / "exam.db")
    backup_sqlite(ROOT / "data" / "content" / "psychology" / "psychology_knowledge.db", staging / "knowledge.db")

    rc = build_exam_configs.build(staging / "exam.db", EXAM_CONFIG, dry_run=False)
    if rc:
        print("build_exam_configs failed", file=sys.stderr)
        return rc
    rc = build_practice_topics.build(
        staging / "exam.db",
        staging / "knowledge.db",
        TOPIC_CONFIG,
        EXCLUSIONS,
        dry_run=False,
    )
    if rc:
        print("build_practice_topics failed", file=sys.stderr)
        return rc

    # Copy only the 277 unique psychology image files referenced by assets.
    exam = sqlite3.connect(f"file:{staging / 'exam.db'}?mode=ro", uri=True)
    asset_paths = [
        row[0]
        for row in exam.execute(
            """
            SELECT DISTINCT a.path
            FROM assets a JOIN questions q ON q.question_id=a.question_id
            WHERE q.subject_id='psychology'
            ORDER BY a.path
            """
        )
    ]
    exam.close()
    if not asset_paths:
        print("no psychology asset paths found", file=sys.stderr)
        return 2
    for rel in asset_paths:
        src = ROOT / rel
        dst = staging / rel
        if not src.is_file():
            print(f"missing source asset: {src}", file=sys.stderr)
            return 2
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    manifest = build_manifest(asset_paths, staging)
    (staging / "assets-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    know = sqlite3.connect(f"file:{staging / 'knowledge.db'}?mode=ro", uri=True)
    know.row_factory = sqlite3.Row
    pronunciation_manifest: dict[str, Any] = {}
    if know.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' "
        "AND name='concept_pronunciations'"
    ).fetchone():
        for row in know.execute(
            """
            SELECT p.cluster_id, p.term, p.ipa, p.audio_path, p.audio_sha256,
                   p.duration_ms, p.sample_rate, p.bitrate_kbps, p.voice, p.speed,
                   p.engine
            FROM concept_pronunciations p
            JOIN concept_clusters c ON c.cluster_id=p.cluster_id
            WHERE c.subject_id='psychology' AND p.audio_path IS NOT NULL
            ORDER BY p.cluster_id
            """
        ):
            rel = str(row["audio_path"] or "")
            src = ROOT / rel
            if not rel or not src.is_file():
                print(f"missing pronunciation audio: {src}", file=sys.stderr)
                know.close()
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
    know.close()
    (staging / "pronunciation-manifest.json").write_text(
        json.dumps(pronunciation_manifest, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    shutil.copy2(EXCLUSIONS, staging / "exclusions.json")

    exam = sqlite3.connect(f"file:{staging / 'exam.db'}?mode=ro", uri=True)
    know = sqlite3.connect(f"file:{staging / 'knowledge.db'}?mode=ro", uri=True)
    release_counts = counts(exam, know)
    exam.close()
    know.close()

    release_json = {
        "release_id": release_id,
        "subject_id": "psychology",
        "schema_version": 1,
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "counts": release_counts,
        "pronunciations": len(pronunciation_manifest),
        "checksums": {
            "exam.db": "sha256:" + sha256(staging / "exam.db"),
            "knowledge.db": "sha256:" + sha256(staging / "knowledge.db"),
            "assets-manifest.json": "sha256:" + sha256(staging / "assets-manifest.json"),
            "pronunciation-manifest.json": "sha256:"
            + sha256(staging / "pronunciation-manifest.json"),
        },
    }
    (staging / "release.json").write_text(
        json.dumps(release_json, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    report = validate_content_release.validate(staging)
    for w in report.warnings:
        print(f"WARN: {w}")
    for e in report.errors:
        print(f"ERROR: {e}", file=sys.stderr)
    if report.errors:
        print(f"validation failed; staging kept at {staging}", file=sys.stderr)
        return 1

    if dry_run:
        print(f"dry-run OK; staging kept at {staging}")
        return 0

    staging.rename(final)
    print(f"release built: {final}")
    print(json.dumps(release_counts, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-id", default=None)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    release_id = args.release_id or f"psychology-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    return build(release_id, args.output_dir, args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
