#!/usr/bin/env python3
"""Compare two textbook editions at section / KP / concept level.

Read-only: writes reports and CSVs, never changes the database.

Typical use:
  python3 _tools/edition_diff.py \
    --old-book psychology-barrons-2027 \
    --new-book psychology-barrons-2028
"""
import argparse
import collections
import csv
import json
import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DB = ROOT / "data" / "content" / "psychology" / "psychology_knowledge.db"
EXAM_DB = ROOT / "data" / "content" / "psychology" / "psychology_exam.db"
OUT_ROOT = ROOT / "data" / "content" / "psychology" / "reports" / "knowledge" / "edition_diff"


def norm(value):
    value = (value or "").lower().replace("’", "'")
    value = value.replace("ﬁ", "fi").replace("ﬂ", "fl")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def parent_path(path):
    parts = (path or "").split(" > ")
    return " > ".join(parts[:-1])


def load_book(con, book_id):
    row = con.execute(
        "SELECT book_id,subject_id,title,edition,year,publisher,book_family_id,status "
        "FROM books WHERE book_id=?",
        (book_id,),
    ).fetchone()
    if not row:
        raise SystemExit(f"book not found: {book_id}")
    return dict(row)


def load_sections(con, book_id):
    rows = [
        dict(row) for row in con.execute(
            """
            SELECT section_id,parent_id,level,heading,heading_normalized,
                   ordinal,path,pdf_page_start,pdf_page_end,is_leaf,excluded
            FROM sections WHERE book_id=?
            ORDER BY path,ordinal
            """,
            (book_id,),
        )
    ]
    for row in rows:
        row["path_norm"] = norm(row["path"])
        row["heading_norm"] = norm(row["heading"])
        row["parent_norm"] = norm(parent_path(row["path"]))
        row["parent_ordinal"] = (row["parent_norm"], row["ordinal"])
    return rows


def load_kps(con, book_id):
    rows = [
        dict(row) for row in con.execute(
            """
            SELECT kp_id,section_id,name,name_normalized,definition_quote,
                   quote_hash,definition_type,source_page,status,duplicate_of
            FROM knowledge_points WHERE book_id=?
            ORDER BY section_id,name_normalized
            """,
            (book_id,),
        )
    ]
    for row in rows:
        row["name_norm"] = row["name_normalized"] or norm(row["name"])
        row["quote_hash"] = row["quote_hash"] or ""
    return rows


def unique_map(rows, key):
    out = collections.defaultdict(list)
    for row in rows:
        out[key(row)].append(row)
    return out


def match_sections(old, new):
    used_old, used_new = set(), set()
    pairs = []

    def take(old_row, new_row, status):
        used_old.add(old_row["section_id"])
        used_new.add(new_row["section_id"])
        pairs.append((old_row, new_row, status))

    old_path = unique_map(old, lambda r: r["path_norm"])
    new_path = unique_map(new, lambda r: r["path_norm"])
    for key, items in old_path.items():
        if len(items) == 1 and len(new_path.get(key, [])) == 1:
            a, b = items[0], new_path[key][0]
            take(a, b, "unchanged" if a["heading_norm"] == b["heading_norm"] else "renamed")

    old_heading = unique_map(
        [r for r in old if r["section_id"] not in used_old], lambda r: r["heading_norm"]
    )
    new_heading = unique_map(
        [r for r in new if r["section_id"] not in used_new], lambda r: r["heading_norm"]
    )
    for key, items in old_heading.items():
        if len(items) == 1 and len(new_heading.get(key, [])) == 1:
            a, b = items[0], new_heading[key][0]
            take(a, b, "moved")

    old_pos = unique_map(
        [r for r in old if r["section_id"] not in used_old], lambda r: r["parent_ordinal"]
    )
    new_pos = unique_map(
        [r for r in new if r["section_id"] not in used_new], lambda r: r["parent_ordinal"]
    )
    for key, items in old_pos.items():
        if len(items) == 1 and len(new_pos.get(key, [])) == 1:
            a, b = items[0], new_pos[key][0]
            take(a, b, "renamed")

    old_parent_heading = unique_map(
        [r for r in old if r["section_id"] not in used_old],
        lambda r: (r["parent_norm"], r["heading_norm"]),
    )
    new_parent_heading = unique_map(
        [r for r in new if r["section_id"] not in used_new],
        lambda r: (r["parent_norm"], r["heading_norm"]),
    )
    for key, items in old_parent_heading.items():
        if len(items) == 1 and len(new_parent_heading.get(key, [])) == 1:
            a, b = items[0], new_parent_heading[key][0]
            take(a, b, "moved")

    for row in old:
        if row["section_id"] not in used_old:
            pairs.append((row, None, "removed"))
    for row in new:
        if row["section_id"] not in used_new:
            pairs.append((None, row, "added"))
    return pairs


def match_kps(old_kps, new_kps, section_map):
    used_old, used_new = set(), set()
    pairs = []

    def take(a, b, status):
        used_old.add(a["kp_id"])
        used_new.add(b["kp_id"])
        pairs.append((a, b, status))

    old_exact = unique_map(old_kps, lambda r: (r["name_norm"], r["quote_hash"]))
    new_exact = unique_map(new_kps, lambda r: (r["name_norm"], r["quote_hash"]))
    for key, items in old_exact.items():
        if len(items) == 1 and len(new_exact.get(key, [])) == 1:
            take(items[0], new_exact[key][0], "unchanged")

    old_quote = unique_map(
        [r for r in old_kps if r["kp_id"] not in used_old],
        lambda r: r["quote_hash"],
    )
    new_quote = unique_map(
        [r for r in new_kps if r["kp_id"] not in used_new],
        lambda r: r["quote_hash"],
    )
    for key, items in old_quote.items():
        if key and len(items) == 1 and len(new_quote.get(key, [])) == 1:
            a, b = items[0], new_quote[key][0]
            status = "renamed" if a["name_norm"] != b["name_norm"] else "moved"
            take(a, b, status)

    old_name = unique_map(
        [r for r in old_kps if r["kp_id"] not in used_old], lambda r: r["name_norm"]
    )
    new_name = unique_map(
        [r for r in new_kps if r["kp_id"] not in used_new], lambda r: r["name_norm"]
    )
    for key, items in old_name.items():
        if len(items) == 1 and len(new_name.get(key, [])) == 1:
            a, b = items[0], new_name[key][0]
            status = "unchanged"
            if a["quote_hash"] != b["quote_hash"]:
                status = "definition_changed"
            elif section_map.get(a["section_id"]) != b["section_id"]:
                status = "moved"
            take(a, b, status)

    # Homonyms / duplicated names: match only through the mapped section.
    old_by_section = unique_map(
        [r for r in old_kps if r["kp_id"] not in used_old],
        lambda r: (section_map.get(r["section_id"]), r["name_norm"]),
    )
    new_by_section = unique_map(
        [r for r in new_kps if r["kp_id"] not in used_new],
        lambda r: (r["section_id"], r["name_norm"]),
    )
    for key, items in old_by_section.items():
        if key[0] and len(items) == 1 and len(new_by_section.get(key, [])) == 1:
            a, b = items[0], new_by_section[key][0]
            status = "unchanged" if a["quote_hash"] == b["quote_hash"] else "definition_changed"
            take(a, b, status)

    for row in old_kps:
        if row["kp_id"] not in used_old:
            pairs.append((row, None, "removed"))
    for row in new_kps:
        if row["kp_id"] not in used_new:
            pairs.append((None, row, "added"))
    return pairs


def concept_map(con, book_id):
    return {
        row["kp_id"]: row["cluster_id"]
        for row in con.execute(
            """
            SELECT k.kp_id,
                   COALESCE(m.cluster_id, k.concept_cluster_id) AS cluster_id
            FROM knowledge_points k
            LEFT JOIN concept_members m ON m.kp_id=k.kp_id
            WHERE k.book_id=?
              AND COALESCE(m.cluster_id, k.concept_cluster_id) IS NOT NULL
            """,
            (book_id,),
        )
    }


def concept_names(con, ids):
    ids = [i for i in set(ids) if i]
    if not ids:
        return {}
    marks = ",".join("?" for _ in ids)
    return {
        row["cluster_id"]: row["canonical_name"]
        for row in con.execute(
            f"SELECT cluster_id,canonical_name FROM concept_clusters WHERE cluster_id IN ({marks})",
            ids,
        )
    }


def write_csv(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fields})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--old-book", required=True)
    parser.add_argument("--new-book", required=True)
    parser.add_argument("--db", default=str(DB))
    parser.add_argument("--exam-db", default=str(EXAM_DB))
    parser.add_argument("--out-dir", default=None)
    parser.add_argument("--allow-cross-family", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    con = sqlite3.connect(args.db)
    con.row_factory = sqlite3.Row
    exam = sqlite3.connect(args.exam_db)
    exam.row_factory = sqlite3.Row

    old_book = load_book(con, args.old_book)
    new_book = load_book(con, args.new_book)
    if old_book["book_id"] == new_book["book_id"]:
        raise SystemExit("old and new book must differ")
    old_family = old_book.get("book_family_id")
    new_family = new_book.get("book_family_id")
    if old_family and new_family and old_family != new_family and not args.allow_cross_family:
        raise SystemExit(
            f"different book families: {old_family} vs {new_family}; "
            "use --allow-cross-family only for testing"
        )

    old_sections = load_sections(con, args.old_book)
    new_sections = load_sections(con, args.new_book)
    section_pairs = match_sections(old_sections, new_sections)
    section_map = {
        a["section_id"]: b["section_id"]
        for a, b, status in section_pairs
        if a and b
    }

    old_kps = load_kps(con, args.old_book)
    new_kps = load_kps(con, args.new_book)
    kp_pairs = match_kps(old_kps, new_kps, section_map)

    old_concepts = concept_map(con, args.old_book)
    new_concepts = concept_map(con, args.new_book)
    all_concept_ids = set(old_concepts.values()) | set(new_concepts.values())
    names = concept_names(con, all_concept_ids)

    out_dir = Path(args.out_dir) if args.out_dir else (
        OUT_ROOT / f"{args.old_book}__{args.new_book}"
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    section_rows = []
    for a, b, status in section_pairs:
        section_rows.append({
            "status": status,
            "old_section_id": a["section_id"] if a else "",
            "new_section_id": b["section_id"] if b else "",
            "old_path": a["path"] if a else "",
            "new_path": b["path"] if b else "",
            "old_heading": a["heading"] if a else "",
            "new_heading": b["heading"] if b else "",
            "old_ordinal": a["ordinal"] if a else "",
            "new_ordinal": b["ordinal"] if b else "",
            "old_level": a["level"] if a else "",
            "new_level": b["level"] if b else "",
        })
    write_csv(out_dir / "section_diff.csv", list(section_rows[0]) if section_rows else
              ["status", "old_section_id", "new_section_id", "old_path", "new_path",
               "old_heading", "new_heading", "old_ordinal", "new_ordinal",
               "old_level", "new_level"], section_rows)

    kp_rows = []
    for a, b, status in kp_pairs:
        old_concept = old_concepts.get(a["kp_id"]) if a else None
        new_concept = new_concepts.get(b["kp_id"]) if b else None
        if old_concept and new_concept:
            concept_status = "unchanged" if old_concept == new_concept else "concept_changed"
        elif new_concept:
            concept_status = "new_concept"
        elif old_concept:
            concept_status = "concept_removed"
        else:
            concept_status = "unmapped"
        kp_rows.append({
            "status": status,
            "old_kp_id": a["kp_id"] if a else "",
            "new_kp_id": b["kp_id"] if b else "",
            "old_name": a["name"] if a else "",
            "new_name": b["name"] if b else "",
            "old_section_id": a["section_id"] if a else "",
            "new_section_id": b["section_id"] if b else "",
            "old_quote_hash": a["quote_hash"] if a else "",
            "new_quote_hash": b["quote_hash"] if b else "",
            "old_page": a["source_page"] if a else "",
            "new_page": b["source_page"] if b else "",
            "old_concept_id": old_concept or "",
            "new_concept_id": new_concept or "",
            "old_concept": names.get(old_concept, ""),
            "new_concept": names.get(new_concept, ""),
            "concept_status": concept_status,
        })
    kp_fields = list(kp_rows[0]) if kp_rows else [
        "status", "old_kp_id", "new_kp_id", "old_name", "new_name",
        "old_section_id", "new_section_id", "old_quote_hash", "new_quote_hash",
        "old_page", "new_page", "old_concept_id", "new_concept_id",
        "old_concept", "new_concept", "concept_status",
    ]
    write_csv(out_dir / "kp_diff.csv", kp_fields, kp_rows)
    write_csv(out_dir / "concept_impact.csv",
              ["old_kp_id", "new_kp_id", "status", "old_concept", "new_concept", "concept_status"],
              [{key: row[key] for key in
                ["old_kp_id", "new_kp_id", "status", "old_concept", "new_concept", "concept_status"]}
               for row in kp_rows])

    section_counts = collections.Counter(row["status"] for row in section_rows)
    kp_counts = collections.Counter(row["status"] for row in kp_rows)
    concept_counts = collections.Counter(row["concept_status"] for row in kp_rows)

    paper_rows = [
        dict(row) for row in exam.execute(
            "SELECT paper_id,role FROM paper_book_sources WHERE book_id=? ORDER BY paper_id",
            (args.old_book,),
        )
    ]
    question_count = exam.execute(
        "SELECT COUNT(*) FROM question_sources WHERE book_id=?", (args.old_book,)
    ).fetchone()[0]

    report = [
        "# 教材版本 diff",
        "",
        f"- 生成时间：{datetime.now().astimezone().isoformat(timespec='seconds')}",
        f"- 旧版：`{args.old_book}`（{old_book['title']} / {old_book['edition']}）",
        f"- 新版：`{args.new_book}`（{new_book['title']} / {new_book['edition']}）",
        f"- book_family：`{old_family}` → `{new_family}`",
        f"- sections：{len(old_sections)} → {len(new_sections)}",
        f"- KPs：{len(old_kps)} → {len(new_kps)}",
        f"- 旧版关联试卷：{len(paper_rows)}；题目来源：{question_count}",
        "",
        "## Section diff",
        "",
        "| 状态 | 数量 |",
        "|---|---:|",
    ]
    for status, count in section_counts.most_common():
        report.append(f"| {status} | {count} |")
    report += [
        "",
        "## KP diff",
        "",
        "| 状态 | 数量 |",
        "|---|---:|",
    ]
    for status, count in kp_counts.most_common():
        report.append(f"| {status} | {count} |")
    report += [
        "",
        "## 概念影响",
        "",
        "| 状态 | 数量 |",
        "|---|---:|",
    ]
    for status, count in concept_counts.most_common():
        report.append(f"| {status} | {count} |")
    report += [
        "",
        "## 示例",
        "",
        "### 新增 KP（前 20）",
        "",
    ]
    for row in [r for r in kp_rows if r["status"] == "added"][:20]:
        report.append(f"- `{row['new_name']}`（new_section=`{row['new_section_id']}`）")
    report += ["", "### 删除 KP（前 20）", ""]
    for row in [r for r in kp_rows if r["status"] == "removed"][:20]:
        report.append(f"- `{row['old_name']}`（old_section=`{row['old_section_id']}`）")
    report += ["", "### 定义变化（前 20）", ""]
    for row in [r for r in kp_rows if r["status"] == "definition_changed"][:20]:
        report.append(f"- `{row['old_name']}`（old/new kp=`{row['old_kp_id']}` / `{row['new_kp_id']}`）")
    report += [
        "",
        "## 产物",
        "",
        f"- `{out_dir / 'section_diff.csv'}`",
        f"- `{out_dir / 'kp_diff.csv'}`",
        f"- `{out_dir / 'concept_impact.csv'}`",
    ]
    (out_dir / "edition_diff_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")

    if args.json:
        (out_dir / "edition_diff.json").write_text(
            json.dumps({
                "old_book": old_book,
                "new_book": new_book,
                "section_counts": dict(section_counts),
                "kp_counts": dict(kp_counts),
                "concept_counts": dict(concept_counts),
                "out_dir": str(out_dir),
            }, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    print(f"old={args.old_book} new={args.new_book}")
    print("sections:", dict(section_counts))
    print("kps:", dict(kp_counts))
    print("concepts:", dict(concept_counts))
    print("report:", out_dir / "edition_diff_report.md")
    con.close()
    exam.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
