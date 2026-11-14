#!/usr/bin/env python3
"""LEGACY one-off migration from the pre-2026-10 asset layout.

The ``AP_exam/`` paths below describe the historical source layout and are
kept only so the migration remains reproducible from an old checkout. Do not
use this script for new work.

Move static resources under assets/<subject>/ and update DB paths.

Target layout
-------------
assets/psychology/
  papers/
    2015/2016/.../2025/
    official_frq/2023..2025/
    cb/
  images/
    2018/.../2025/
    barron2027/
    barron2027_review/
    cb2026/
  books/

The migration is dry-run by default; use --apply to move files and update DB.
"""
import argparse
import hashlib
import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
EXAM_DB = ROOT / "data" / "content" / "psychology" / "psychology_exam.db"
KNOW_DB = ROOT / "data" / "content" / "psychology" / "psychology_knowledge.db"
SUBJECT = "psychology"
ASSETS = ROOT / "assets" / SUBJECT
REPORT = ROOT / "data" / "content" / "psychology" / "reports" / "knowledge" / "assets_layout_migration_report.md"

YEAR_DIRS = ["2015", "2016", "2017", "2018", "2019", "2021", "2022", "2023", "2024", "2025"]
OLD_ASSET_DIRS = [
    "2018", "2019", "2021", "2022", "2023", "2024", "2025",
    "barron2027", "barron2027_review", "cb2026",
]
TEXTBOOKS = {
    "AP Psychology Premium, 2027 - Allyson J. Weseley & Robert McEntarffer.pdf",
    "教材1--Myers.pdf",
}


def target_for(old_rel):
    old_rel = old_rel.replace(os.sep, "/")
    if old_rel.startswith("assets/"):
        return f"assets/{SUBJECT}/images/{old_rel[len('assets/'):]}"
    if old_rel in TEXTBOOKS:
        return f"assets/{SUBJECT}/books/{old_rel}"
    if old_rel.startswith("CB/"):
        return f"assets/{SUBJECT}/papers/cb/{Path(old_rel).name}"
    if old_rel.startswith("AP_exam/official_frq/"):
        rel = old_rel[len("AP_exam/official_frq/"):]
        return f"assets/{SUBJECT}/papers/official_frq/{rel}"
    if old_rel == "AP_exam/2019.pdf":
        return f"assets/{SUBJECT}/papers/2019/2019.pdf"
    if old_rel == "AP_exam/2025":
        return f"assets/{SUBJECT}/papers/2025"
    if old_rel.startswith("AP_exam/"):
        rel = old_rel[len("AP_exam/"):]
        return f"assets/{SUBJECT}/papers/{rel}"
    return old_rel


def build_file_plan():
    plan = []
    for name in OLD_ASSET_DIRS:
        base = ROOT / "assets" / name
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file() and path.name != ".DS_Store":
                rel = path.relative_to(ROOT).as_posix()
                plan.append((rel, target_for(rel)))
    for name in YEAR_DIRS:
        base = ROOT / "AP_exam" / name
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file() and path.name != ".DS_Store":
                rel = path.relative_to(ROOT).as_posix()
                plan.append((rel, target_for(rel)))
    frq = ROOT / "AP_exam" / "official_frq"
    if frq.exists():
        for path in sorted(frq.rglob("*")):
            if path.is_file() and path.name != ".DS_Store":
                rel = path.relative_to(ROOT).as_posix()
                plan.append((rel, target_for(rel)))
    cb = ROOT / "CB"
    if cb.exists():
        for path in sorted(cb.rglob("*")):
            if path.is_file() and path.name != ".DS_Store":
                rel = path.relative_to(ROOT).as_posix()
                plan.append((rel, target_for(rel)))
    for name in TEXTBOOKS:
        if (ROOT / name).exists():
            plan.append((name, target_for(name)))
    return plan


def sha1(path):
    h = hashlib.sha1()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def map_db_path(value):
    if not value:
        return value
    value = value.replace(os.sep, "/")
    if value.startswith("assets/psychology/"):
        return value
    return target_for(value)


def update_exam(con):
    changes = []
    for row in con.execute("SELECT asset_id,path FROM assets").fetchall():
        new = map_db_path(row["path"])
        if new != row["path"]:
            con.execute("UPDATE assets SET path=? WHERE asset_id=?", (new, row["asset_id"]))
            changes.append(("assets.path", row["asset_id"], row["path"], new))
    for row in con.execute("SELECT paper_id,role,path FROM paper_sources").fetchall():
        new = map_db_path(row["path"])
        if new != row["path"]:
            con.execute(
                "UPDATE paper_sources SET path=? WHERE paper_id=? AND role=? AND path=?",
                (new, row["paper_id"], row["role"], row["path"]),
            )
            changes.append(("paper_sources.path", f"{row['paper_id']}:{row['role']}", row["path"], new))
    for row in con.execute("SELECT source_id,file_path FROM content_sources").fetchall():
        new = map_db_path(row["file_path"])
        if new != row["file_path"]:
            con.execute("UPDATE content_sources SET file_path=? WHERE source_id=?", (new, row["source_id"]))
            changes.append(("content_sources.file_path", row["source_id"], row["file_path"], new))
    for row in con.execute("SELECT paper_id,source_pdf FROM papers WHERE source_pdf IS NOT NULL").fetchall():
        new = map_db_path(row["source_pdf"])
        if new != row["source_pdf"]:
            con.execute("UPDATE papers SET source_pdf=? WHERE paper_id=?", (new, row["paper_id"]))
            changes.append(("papers.source_pdf", row["paper_id"], row["source_pdf"], new))
    for row in con.execute("SELECT DISTINCT source_file FROM questions WHERE source_file IS NOT NULL").fetchall():
        new = map_db_path(row["source_file"])
        if new != row["source_file"]:
            con.execute("UPDATE questions SET source_file=? WHERE source_file=?", (new, row["source_file"]))
            changes.append(("questions.source_file", row["source_file"], row["source_file"], new))
    return changes


def update_knowledge(con):
    changes = []
    for row in con.execute("SELECT book_id,source_path FROM books").fetchall():
        new = map_db_path(row["source_path"])
        if new != row["source_path"]:
            con.execute("UPDATE books SET source_path=? WHERE book_id=?", (new, row["book_id"]))
            changes.append(("books.source_path", row["book_id"], row["source_path"], new))
    return changes


def check_paths(con, table, column):
    missing = []
    for row in con.execute(f"SELECT {column} AS p FROM {table} WHERE {column} IS NOT NULL AND TRIM({column})<>''"):
        p = row["p"]
        if not (ROOT / p).exists():
            missing.append((table, column, p))
    return missing


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--no-backup", action="store_true")
    args = parser.parse_args()

    plan = build_file_plan()
    print(f"files to move: {len(plan)}")
    for src, dst in plan[:20]:
        print(f"  {src} -> {dst}")
    if len(plan) > 20:
        print(f"  ... {len(plan) - 20} more")

    # Preflight: all sources exist, targets are free or identical.
    errors = []
    for src, dst in plan:
        src_path, dst_path = ROOT / src, ROOT / dst
        if not src_path.exists():
            errors.append(f"missing source: {src}")
        if dst_path.exists():
            if src_path.is_file() and dst_path.is_file() and sha1(src_path) == sha1(dst_path):
                continue
            errors.append(f"target exists: {dst}")
    if errors:
        print("preflight errors:")
        for error in errors[:20]:
            print(" ", error)
        return 1
    if not args.apply:
        print("dry-run only; use --apply")
        return 0

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    if not args.no_backup:
        for path in (EXAM_DB, KNOW_DB):
            backup = path.with_name(path.name + f".bak-{stamp}-before-assets-layout")
            shutil.copy2(path, backup)
            print("backup:", backup)

    moved = []
    try:
        for src, dst in plan:
            src_path, dst_path = ROOT / src, ROOT / dst
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            if dst_path.exists():
                src_path.unlink()
            else:
                shutil.move(str(src_path), str(dst_path))
            moved.append((src, dst))
    except Exception as exc:
        print("move failed, rolling back moved files:", exc)
        for src, dst in reversed(moved):
            src_path, dst_path = ROOT / src, ROOT / dst
            if dst_path.exists() and not src_path.exists():
                src_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(dst_path), str(src_path))
        raise

    exam = sqlite3.connect(EXAM_DB)
    exam.row_factory = sqlite3.Row
    know = sqlite3.connect(KNOW_DB)
    know.row_factory = sqlite3.Row
    with exam:
        exam_changes = update_exam(exam)
    with know:
        know_changes = update_knowledge(know)

    missing = []
    for table, column in [
        ("assets", "path"),
        ("paper_sources", "path"),
        ("content_sources", "file_path"),
        ("papers", "source_pdf"),
        ("questions", "source_file"),
    ]:
        missing.extend(check_paths(exam, table, column))
    for table, column in [("books", "source_path")]:
        missing.extend(check_paths(know, table, column))

    # Remove macOS metadata before checking whether old directories are empty.
    for path in ROOT.rglob(".DS_Store"):
        if ".git" not in path.parts:
            path.unlink(missing_ok=True)

    # Remove empty old directories.
    cleaned = []
    for name in OLD_ASSET_DIRS:
        path = ROOT / "assets" / name
        if path.exists() and not any(path.iterdir()):
            path.rmdir()
            cleaned.append(str(path.relative_to(ROOT)))
    for name in YEAR_DIRS + ["official_frq"]:
        path = ROOT / "AP_exam" / name
        if path.exists() and not any(path.iterdir()):
            path.rmdir()
            cleaned.append(str(path.relative_to(ROOT)))
    for name in ["CB", "AP_exam/2020"]:
        path = ROOT / name
        if path.exists() and path.is_dir() and not any(path.iterdir()):
            path.rmdir()
            cleaned.append(name)
    report = [
        "# 静态资源目录迁移报告",
        "",
        f"- 时间：{datetime.now().astimezone().isoformat(timespec='seconds')}",
        f"- 移动文件：{len(moved)}",
        f"- DB 变更：{len(exam_changes) + len(know_changes)}",
        f"- 缺失路径：{len(missing)}",
        f"- 清理空目录：{len(cleaned)}",
        "",
        "## 目标结构",
        "",
        "```text",
        "assets/psychology/",
        "  papers/       # 真题、官方 FRQ、CB 题库 PDF",
        "  images/       # 题目图片、选项图片、Barron/CB 裁图",
        "  books/        # 教材 PDF",
        "```",
        "",
        "## DB 变更",
        "",
        "| 表.字段 | 记录 | 旧路径 | 新路径 |",
        "|---|---|---|---|",
    ]
    for table_column, key, old, new in exam_changes + know_changes[:200]:
        report.append(f"| `{table_column}` | `{key}` | `{old}` | `{new}` |")
    if len(exam_changes) + len(know_changes) > 200:
        report.append(f"| ... | ... | ... | 其余 {len(exam_changes) + len(know_changes) - 200} 条 |")
    report += ["", "## 缺失路径", ""]
    if missing:
        for table, column, path in missing:
            report.append(f"- `{table}.{column}`：`{path}`")
    else:
        report.append("- 无")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(report) + "\n", encoding="utf-8")

    print(f"moved={len(moved)} db_changes={len(exam_changes) + len(know_changes)} "
          f"missing={len(missing)} cleaned={len(cleaned)}")
    print("report:", REPORT)
    exam.close()
    know.close()
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
