#!/usr/bin/env python3
"""Validate prompt registry, frontmatter and cross-references."""
import os
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("PyYAML is required: python3 -m pip install pyyaml", file=sys.stderr)
    raise SystemExit(2)

ROOT = Path(__file__).resolve().parent.parent
PROMPTS = ROOT / "prompts"
REGISTRY = PROMPTS / "registry.yaml"
STATUSES = {"draft", "active", "deprecated", "archived"}
KINDS = {"extraction", "integration", "linking", "ingestion", "generation", "orchestration"}
OLD_ROOT_FILES = [
    "全书一次性知识点抽取提示语.md",
    "多本教材知识点处理提示语.md",
    "题目知识点生成提示语.md",
    "PDF题目解析入库提示语.md",
    "AI解析生成提示语.md",
    "数据Agent处理规范.md",
    "题目解析关联提示语.md",
]
SKIP_REF_SCAN = {"README.md", "CHANGELOG.md"}


def fail(message):
    print(f"ERROR: {message}")
    return 1


def main():
    errors = 0
    if not REGISTRY.exists():
        return fail(f"missing registry: {REGISTRY}")

    registry = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    entries = registry.get("prompts") or []
    print(f"registry: {len(entries)} prompts")

    by_id = {}
    by_file = {}
    for entry in entries:
        pid = entry.get("id")
        rel = entry.get("file")
        if not pid or not rel:
            errors += fail(f"entry missing id/file: {entry}")
            continue
        if pid in by_id:
            errors += fail(f"duplicate id: {pid}")
        if rel in by_file:
            errors += fail(f"duplicate file: {rel}")
        by_id[pid] = entry
        by_file[rel] = entry

        fp = PROMPTS / rel
        if not fp.exists():
            errors += fail(f"file missing: {fp}")
            continue
        text = fp.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            errors += fail(f"missing frontmatter: {fp}")
            continue
        try:
            meta = yaml.safe_load(text.split("---\n", 2)[1]) or {}
        except yaml.YAMLError as exc:
            errors += fail(f"bad frontmatter {fp}: {exc}")
            continue

        for key in ("id", "title", "version", "status", "kind", "updated",
                    "inputs", "outputs"):
            if key not in meta:
                errors += fail(f"{fp}: missing frontmatter field {key}")
        if meta.get("id") != pid:
            errors += fail(f"{fp}: id {meta.get('id')!r} != registry {pid!r}")
        if meta.get("version") != entry.get("version"):
            errors += fail(f"{fp}: version {meta.get('version')!r} != registry {entry.get('version')!r}")
        if meta.get("status") not in STATUSES:
            errors += fail(f"{fp}: bad status {meta.get('status')!r}")
        if meta.get("kind") not in KINDS:
            errors += fail(f"{fp}: bad kind {meta.get('kind')!r}")
        if meta.get("status") == "deprecated" and not meta.get("superseded_by"):
            errors += fail(f"{fp}: deprecated without superseded_by")
        if meta.get("superseded_by") and meta["superseded_by"] not in by_id:
            # by_id is not fully built yet; checked after the loop
            pass

    # Dependency and supersede checks after all IDs are known.
    for pid, entry in by_id.items():
        for dep in entry.get("depends_on") or []:
            if dep not in by_id:
                errors += fail(f"{pid}: unknown dependency {dep!r}")
        for used in entry.get("used_by") or []:
            if used not in by_id:
                errors += fail(f"{pid}: unknown used_by {used!r}")
        superseded = entry.get("superseded_by")
        if superseded and superseded not in by_id:
            errors += fail(f"{pid}: unknown superseded_by {superseded!r}")

    # Every markdown prompt file (except docs/template/legacy README) is registered.
    for fp in sorted(PROMPTS.rglob("*.md")):
        rel = fp.relative_to(PROMPTS).as_posix()
        if rel in {"README.md", "CHANGELOG.md", "_template.md"} or fp.name == "README.md":
            continue
        if rel not in by_file:
            errors += fail(f"unregistered prompt file: {fp}")

    # Old root prompt files must not exist.
    for name in OLD_ROOT_FILES:
        if (ROOT / name).exists():
            errors += fail(f"legacy root prompt still exists: {name}")

    # Active prompt docs should not reference old root filenames.
    for fp in sorted(PROMPTS.rglob("*.md")):
        if fp.name in SKIP_REF_SCAN:
            continue
        text = fp.read_text(encoding="utf-8")
        for old in OLD_ROOT_FILES:
            if re.search(rf"(?<![`\w]){re.escape(old)}(?![`\w])", text):
                errors += fail(f"{fp}: references old root filename {old}")

    if errors:
        print(f"FAILED: {errors} error(s)")
        return 1
    print("OK: registry, frontmatter, dependencies and references are consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
