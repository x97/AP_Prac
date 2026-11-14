"""Load subject-level content source configuration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config" / "subjects"


def load_subject(subject_id: str) -> dict[str, Any]:
    path = CONFIG_DIR / f"{subject_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"subject config not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("subject_id") != subject_id:
        raise ValueError(f"subject_id mismatch in {path}")
    return payload


def enabled_subjects() -> list[dict[str, Any]]:
    subjects = []
    for path in sorted(CONFIG_DIR.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("enabled"):
            subjects.append(payload)
    return subjects


def source_paths(config: dict[str, Any]) -> dict[str, Path]:
    source = ROOT / config["source_dir"]
    return {
        "source_dir": source,
        "exam_db": source / config["exam_db"],
        "knowledge_db": source / config["knowledge_db"],
        "asset_root": ROOT / config["asset_root"],
        "exam_config": ROOT / config["exam_config"],
        "practice_topics": ROOT / config["practice_topics"],
        "exclusions": ROOT / config["exclusions"],
    }
