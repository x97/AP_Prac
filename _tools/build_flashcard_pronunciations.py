#!/usr/bin/env python3
"""Generate IPA and Kokoro audio for every official flashcard term.

The generated files are content assets:

  assets/psychology/audio/terms/<slug>-<hash>.mp3

Metadata is stored in ``concept_pronunciations`` in the psychology knowledge
DB. The release builder copies the referenced files into a Release and writes
``pronunciation-manifest.json``.

This script intentionally runs with Python 3.12 from the temporary Kokoro
environment:

  /tmp/kokoro_venv312/bin/python _tools/build_flashcard_pronunciations.py \
    --model /tmp/kokoro_models/kokoro-v1.0.onnx \
    --voices /tmp/kokoro_models/voices-v1.0.bin

It is resumable: existing audio files and IPA rows are reused unless
``--force`` is passed.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sqlite3
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import espeakng_loader
import lameenc
import numpy as np
from kokoro_onnx import Kokoro
from phonemizer.backend import EspeakBackend
from phonemizer.backend.espeak.wrapper import EspeakWrapper

try:
    import eng_to_ipa as cmu_ipa
except ImportError:  # pragma: no cover - optional tooling dependency
    cmu_ipa = None

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data/content/psychology/psychology_knowledge.db"
DEFAULT_MODEL = Path("/tmp/kokoro_models/kokoro-v1.0.onnx")
DEFAULT_VOICES = Path("/tmp/kokoro_models/voices-v1.0.bin")
DEFAULT_OUT = ROOT / "assets/psychology/audio/terms"
AUDIO_PREFIX = "assets/psychology/audio/terms"
BITRATE_KBPS = 64

SCHEMA = """
CREATE TABLE IF NOT EXISTS concept_pronunciations (
    cluster_id       TEXT PRIMARY KEY,
    term             TEXT NOT NULL,
    ipa              TEXT NOT NULL,
    audio_path       TEXT,
    audio_sha256     TEXT,
    duration_ms      INTEGER,
    sample_rate      INTEGER,
    bitrate_kbps     INTEGER,
    voice            TEXT,
    speed            REAL,
    engine           TEXT,
    updated_at       TEXT NOT NULL,
    FOREIGN KEY (cluster_id) REFERENCES concept_clusters(cluster_id)
        ON DELETE CASCADE
)
"""

INDEX = """
CREATE INDEX IF NOT EXISTS idx_concept_pronunciations_audio
    ON concept_pronunciations(audio_path)
"""


def utcnow_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def slug(text: str) -> str:
    text = text.lower().replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "term"


def clean_ipa(value: str) -> str:
    return " ".join(str(value or "").replace("\n", " ").split())


IPA_OVERRIDES = {
    "Type A": "taɪp eɪ",
    "Type B": "taɪp biː",
}


def prefer_cmu_ipa(term: str, espeak_value: str) -> str:
    """Use the CMU dictionary when every word is known, else eSpeak NG.

    The CMU output is closer to the IPA students see in dictionaries. eSpeak
    remains the fallback because it covers specialized and hyphenated terms
    that are missing from CMUdict, and it is the phonemizer Kokoro uses.
    """
    if term in IPA_OVERRIDES:
        return IPA_OVERRIDES[term]
    if cmu_ipa is not None:
        normalized = term.replace("’", "'").replace("‘", "'")
        candidates = (
            normalized,
            normalized.replace("-", " ").replace("/", " "),
        )
        for candidate in candidates:
            try:
                cmu_value = clean_ipa(cmu_ipa.convert(candidate))
                if cmu_value and "*" not in cmu_value:
                    return cmu_value.replace("ʧ", "tʃ").replace("ʤ", "dʒ")
            except Exception:  # noqa: BLE001, S110 - fallback is intentional
                continue
    return (
        clean_ipa(espeak_value)
        .replace("ᵻ", "ɪ")
        .replace("ɐ", "ə")
        .replace("ɚɹ", "ɚ")
        .replace("ɜɹ", "ɝ")
    )


def audio_filename(term: str, voice: str, speed: float) -> str:
    digest = hashlib.sha256(
        f"{voice}|{speed:.3f}|{term.casefold()}".encode()
    ).hexdigest()
    return f"{slug(term)[:48]}-{digest[:12]}.mp3"


def encode_mp3(samples: np.ndarray, sample_rate: int) -> bytes:
    """Normalize to the preview's -1 dB headroom, then encode mono MP3."""
    samples = np.asarray(samples, dtype=np.float32).reshape(-1)
    peak = float(np.max(np.abs(samples))) if samples.size else 0.0
    if peak > 0:
        samples = samples / peak * 0.9
    pcm = np.clip(samples * 32767.0, -32768, 32767).astype("<i2")
    encoder = lameenc.Encoder()
    encoder.set_bit_rate(BITRATE_KBPS)
    encoder.set_in_sample_rate(int(sample_rate))
    encoder.set_channels(1)
    encoder.set_quality(2)
    return bytes(encoder.encode(pcm.tobytes()) + encoder.flush())


def synthesize(
    kokoro: Kokoro, term: str, voice: str, speed: float
) -> tuple[bytes, int, int]:
    samples, sample_rate = kokoro.create(
        term,
        voice=voice,
        speed=speed,
        lang="en-us",
    )
    samples = np.asarray(samples, dtype=np.float32).reshape(-1)
    duration_ms = round(len(samples) / int(sample_rate) * 1000)
    return encode_mp3(samples, int(sample_rate)), int(sample_rate), duration_ms


def text_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_terms(db: sqlite3.Connection, limit: int | None) -> list[sqlite3.Row]:
    sql = """
        SELECT cluster_id, canonical_name, weight
        FROM concept_clusters
        WHERE subject_id='psychology'
          AND canonical_kp_id IS NOT NULL
          AND TRIM(COALESCE(canonical_name, '')) != ''
        ORDER BY weight DESC, canonical_name
    """
    rows = db.execute(sql).fetchall()
    deduped: list[sqlite3.Row] = []
    seen: set[str] = set()
    for row in rows:
        key = " ".join(str(row["canonical_name"]).casefold().split())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    if limit:
        deduped = deduped[:limit]
    return deduped


def upsert_row(
    db: sqlite3.Connection,
    *,
    cluster_id: str,
    term: str,
    ipa: str,
    audio_path: str | None,
    audio_sha256: str | None,
    duration_ms: int | None,
    sample_rate: int | None,
    voice: str,
    speed: float,
) -> None:
    db.execute(
        """
        INSERT INTO concept_pronunciations (
            cluster_id, term, ipa, audio_path, audio_sha256, duration_ms,
            sample_rate, bitrate_kbps, voice, speed, engine, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'kokoro-onnx', ?)
        ON CONFLICT(cluster_id) DO UPDATE SET
            term=excluded.term,
            ipa=excluded.ipa,
            audio_path=excluded.audio_path,
            audio_sha256=excluded.audio_sha256,
            duration_ms=excluded.duration_ms,
            sample_rate=excluded.sample_rate,
            bitrate_kbps=excluded.bitrate_kbps,
            voice=excluded.voice,
            speed=excluded.speed,
            engine=excluded.engine,
            updated_at=excluded.updated_at
        """,
        (
            cluster_id,
            term,
            ipa,
            audio_path,
            audio_sha256,
            duration_ms,
            sample_rate,
            BITRATE_KBPS,
            voice,
            speed,
            utcnow_iso(),
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--voices", type=Path, default=DEFAULT_VOICES)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--voice", default="af_heart")
    parser.add_argument("--speed", type=float, default=0.9)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--ipa-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.db.exists():
        print(f"knowledge DB not found: {args.db}", file=sys.stderr)
        return 2
    if not args.model.exists() or not args.voices.exists():
        print("Kokoro model/voices files not found", file=sys.stderr)
        return 2

    db = sqlite3.connect(str(args.db))
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    db.execute(SCHEMA)
    db.execute(INDEX)
    db.commit()

    terms = load_terms(db, args.limit)
    if not terms:
        print("no official terms found", file=sys.stderr)
        return 2
    print(f"terms: {len(terms)} · voice: {args.voice} · speed: {args.speed}")

    # Generate IPA in one espeak-ng batch. It is fast and keeps the
    # pronunciation notation consistent with Kokoro's own phonemizer.
    EspeakWrapper.set_data_path(espeakng_loader.get_data_path())
    EspeakWrapper.set_library(espeakng_loader.get_library_path())
    backend = EspeakBackend(
        language="en-us", preserve_punctuation=False, with_stress=True
    )
    texts = [str(row["canonical_name"]) for row in terms]
    ipa_values = backend.phonemize(texts, strip=True)
    if len(ipa_values) != len(texts):
        print("espeak-ng returned an unexpected IPA count", file=sys.stderr)
        return 2
    ipas = [
        prefer_cmu_ipa(text, value)
        for text, value in zip(texts, ipa_values)
    ]

    existing = {
        row["cluster_id"]: row
        for row in db.execute(
            """
            SELECT cluster_id, ipa, audio_path, audio_sha256, duration_ms,
                   sample_rate
            FROM concept_pronunciations
            """
        )
    }

    if args.dry_run:
        for row, ipa in zip(terms, ipas):
            print(f"{row['canonical_name']}\t/{ipa}/")
        return 0

    args.out.mkdir(parents=True, exist_ok=True)
    kokoro = None if args.ipa_only else Kokoro(str(args.model), str(args.voices))
    started = time.monotonic()
    generated = 0
    reused = 0

    for index, (row, ipa) in enumerate(zip(terms, ipas), start=1):
        cluster_id = str(row["cluster_id"])
        term = str(row["canonical_name"])
        previous = existing.get(cluster_id)
        previous_path = str(previous["audio_path"] or "") if previous else ""
        previous_file = ROOT / previous_path if previous_path else None
        needs_audio = (
            not args.ipa_only
            and (
                args.force
                or not previous
                or not previous_path
                or previous_file is None
                or not previous_file.is_file()
            )
        )

        if needs_audio:
            assert kokoro is not None
            filename = audio_filename(term, args.voice, args.speed)
            rel_path = f"{AUDIO_PREFIX}/{filename}"
            target = ROOT / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            data, sample_rate, duration_ms = synthesize(
                kokoro, term, args.voice, args.speed
            )
            temp = target.with_suffix(".mp3.tmp")
            temp.write_bytes(data)
            temp.replace(target)
            digest = text_hash(data)
            generated += 1
        elif previous_path and previous_file and previous_file.is_file():
            rel_path = previous_path
            target = previous_file
            digest = str(previous["audio_sha256"] or text_hash(target.read_bytes()))
            duration_ms = int(previous["duration_ms"] or 0)
            sample_rate = int(previous["sample_rate"] or 24000)
            reused += 1
        else:
            rel_path = None
            target = None
            digest = None
            duration_ms = None
            sample_rate = None

        upsert_row(
            db,
            cluster_id=cluster_id,
            term=term,
            ipa=ipa,
            audio_path=rel_path,
            audio_sha256=digest,
            duration_ms=duration_ms,
            sample_rate=sample_rate,
            voice=args.voice,
            speed=args.speed,
        )
        if index % 10 == 0 or index == len(terms):
            db.commit()
            elapsed = max(0.001, time.monotonic() - started)
            rate = index / elapsed
            eta = (len(terms) - index) / rate if rate else 0
            size_kb = (
                target.stat().st_size / 1024
                if target is not None and target.exists()
                else 0
            )
            print(
                f"[{index:04d}/{len(terms)}] {term} · /{ipa}/ · "
                f"{duration_ms}ms · {size_kb:.1f} KB · "
                f"{rate:.2f} terms/s · ETA {eta / 60:.1f} min",
                flush=True,
            )

    db.commit()
    audio_files = int(
        db.execute(
            "SELECT COUNT(*) FROM concept_pronunciations WHERE audio_path IS NOT NULL"
        ).fetchone()[0]
    )
    report = {
        "generated_at": utcnow_iso(),
        "engine": "kokoro-onnx",
        "voice": args.voice,
        "speed": args.speed,
        "bitrate_kbps": BITRATE_KBPS,
        "terms": len(terms),
        "audio_files": audio_files,
        "generated": generated,
        "reused": reused,
        "audio_dir": AUDIO_PREFIX,
        "ipa_library": "CMUdict (eng-to-ipa) with phonemizer + espeak-ng fallback",
    }
    report_path = ROOT / "data/content/psychology/reports/flashcard_pronunciations.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    csv_path = report_path.with_suffix(".csv")
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["term", "ipa", "duration_ms", "audio_path", "voice", "speed"]
        )
        for row in db.execute(
            """
            SELECT p.term, p.ipa, p.duration_ms, p.audio_path, p.voice, p.speed
            FROM concept_pronunciations p
            JOIN concept_clusters c ON c.cluster_id=p.cluster_id
            WHERE c.subject_id='psychology'
            ORDER BY c.weight DESC, p.term
            """
        ):
            writer.writerow(
                [
                    row["term"],
                    f"/{row['ipa']}/",
                    row["duration_ms"],
                    row["audio_path"],
                    row["voice"],
                    row["speed"],
                ]
            )
    print(f"done: generated={generated} reused={reused} report={report_path}")
    db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
