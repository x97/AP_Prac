from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from app.core.config import REPO_ROOT

SUBJECT_CONFIG_DIR = REPO_ROOT / "config" / "subjects"
DEFAULT_SUBJECT_ID = "psychology"


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def all_subject_configs() -> list[dict[str, Any]]:
    if not SUBJECT_CONFIG_DIR.exists():
        return [
            {
                "subject_id": DEFAULT_SUBJECT_ID,
                "name": "AP Psychology",
                "name_zh": "AP 心理学",
                "enabled": True,
            }
        ]
    out = []
    for path in sorted(SUBJECT_CONFIG_DIR.glob("*.json")):
        payload = _read_json(path)
        subject_id = str(payload.get("subject_id") or "").strip()
        if not subject_id:
            continue
        out.append(
            {
                "subject_id": subject_id,
                "name": str(payload.get("name") or subject_id),
                "name_zh": str(payload.get("name_zh") or subject_id),
                "enabled": bool(payload.get("enabled")),
            }
        )
    return out


def get_subject_config(subject_id: str) -> Optional[dict[str, Any]]:
    for item in all_subject_configs():
        if item["subject_id"] == subject_id:
            return item
    return None


def enabled_subject_payloads() -> list[dict[str, Any]]:
    return [item for item in all_subject_configs() if item["enabled"]]


def subject_payloads(include_disabled: bool = False) -> list[dict[str, Any]]:
    items = all_subject_configs()
    if not include_disabled:
        items = [item for item in items if item["enabled"]]
    return [
        {
            "subject_id": item["subject_id"],
            "name": item["name"],
            "name_zh": item["name_zh"],
            "enabled": item["enabled"],
        }
        for item in items
    ]


def default_subject_id() -> str:
    enabled = [item["subject_id"] for item in all_subject_configs() if item["enabled"]]
    return enabled[0] if enabled else DEFAULT_SUBJECT_ID
