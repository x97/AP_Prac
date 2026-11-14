#!/usr/bin/env python3
"""Add book-family / source-provenance fields and tables.

This is a deliberately additive migration:
  psychology_knowledge.db:
    books.book_family_id
    books.status
  psychology_exam.db:
    content_sources.book_id
    paper_book_sources
    question_sources

It does not delete or rewrite existing rows.  Re-running is safe.
"""
import argparse
import json
import os
import re
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
EXAM_DB = ROOT / "data" / "content" / "psychology" / "psychology_exam.db"
KNOW_DB = ROOT / "data" / "content" / "psychology" / "psychology_knowledge.db"
REPORT = ROOT / "data" / "content" / "psychology" / "reports" / "knowledge" / "source_provenance_migration_report.md"

# Current edition families.  Future editions of the same book should reuse
# the family id, e.g. psychology-barrons-2028 -> psychology-barrons-ap-psychology.
FAMILY_BY_BOOK = {
    "psychology-barrons-2027": "psychology-barrons-ap-psychology",
    "psychology-myers-2024": "psychology-myers-ap-psychology",
}


def slug(value):
    value = (value or "").lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "unknown"


def family_for(book_id, subject_id, publisher, title):
    if book_id in FAMILY_BY_BOOK:
        return FAMILY_BY_BOOK[book_id]
    # Stable fallback: strip a trailing year from the book id.
    base = re.sub(r"-(?:19|20)\d{2}$", "", book_id or "")
    if base and base != book_id:
        return base
    return f"{subject_id}-{slug(publisher)}-{slug(title)}"


def column_names(con, table):
    return {row[1] for row in con.execute(f"PRAGMA table_info({table})")}


def add_column(con, table, column, ddl):
    if column not in column_names(con, table):
        con.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
        return True
    return False


def ensure_knowledge_schema(con):
    added = []
    if add_column(con, "books", "book_family_id", "TEXT"):
        added.append("books.book_family_id")
    if add_column(con, "books", "status", "TEXT DEFAULT 'active'"):
        added.append("books.status")
    con.execute("CREATE INDEX IF NOT EXISTS idx_books_family ON books(book_family_id)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_books_lifecycle ON books(status)")
    return added


def ensure_exam_schema(con):
    added = []
    if add_column(con, "content_sources", "book_id", "TEXT"):
        added.append("content_sources.book_id")
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS paper_book_sources (
            paper_id TEXT NOT NULL REFERENCES papers(paper_id) ON DELETE CASCADE,
            book_id  TEXT NOT NULL,
            role     TEXT NOT NULL DEFAULT 'main',
            note     TEXT,
            PRIMARY KEY (paper_id, book_id, role)
        )
        """
    )
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS question_sources (
            source_link_id INTEGER PRIMARY KEY,
            question_id TEXT NOT NULL REFERENCES questions(question_id) ON DELETE CASCADE,
            book_id     TEXT NOT NULL,
            section_id  TEXT,
            page_start  INTEGER,
            page_end    INTEGER,
            figure_ref  TEXT,
            role        TEXT NOT NULL DEFAULT 'question',
            note        TEXT
        )
        """
    )
    con.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_question_sources
        ON question_sources(question_id, book_id, role,
                            IFNULL(page_start,-1), IFNULL(page_end,-1))
        """
    )
    con.execute("CREATE INDEX IF NOT EXISTS idx_qsource_book ON question_sources(book_id)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_qsource_q ON question_sources(question_id)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_pbooks_book ON paper_book_sources(book_id)")
    return added


def apply_knowledge(con):
    updated = 0
    rows = con.execute(
        "SELECT book_id,subject_id,publisher,title,edition,year FROM books"
    ).fetchall()
    for row in rows:
        family = family_for(row["book_id"], row["subject_id"],
                            row["publisher"], row["title"])
        con.execute(
            "UPDATE books SET book_family_id=?, status=COALESCE(status,'active') "
            "WHERE book_id=?",
            (family, row["book_id"]),
        )
        updated += 1
    return updated


def apply_exam(con, know):
    # Map content source -> book by matching source_id to a knowledge book_id.
    book_ids = {row[0] for row in know.execute("SELECT book_id FROM books")}
    source_rows = con.execute(
        "SELECT source_id FROM content_sources ORDER BY source_id"
    ).fetchall()
    source_to_book = {}
    for row in source_rows:
        source_id = row["source_id"]
        if source_id in book_ids:
            source_to_book[source_id] = source_id
            con.execute(
                "UPDATE content_sources SET book_id=? WHERE source_id=?",
                (source_id, source_id),
            )
        else:
            con.execute(
                "UPDATE content_sources SET book_id=NULL WHERE source_id=?",
                (source_id,),
            )

    paper_rows = con.execute(
        """
        SELECT p.paper_id, cs.book_id
        FROM papers p
        JOIN content_sources cs ON cs.source_id=p.source_id
        WHERE cs.book_id IS NOT NULL
        ORDER BY p.paper_id
        """
    ).fetchall()
    for row in paper_rows:
        con.execute(
            "INSERT OR IGNORE INTO paper_book_sources(paper_id,book_id,role,note) "
            "VALUES (?,?,?,?)",
            (row["paper_id"], row["book_id"], "main",
             "derived from papers.source_id -> content_sources.book_id"),
        )

    question_rows = con.execute(
        """
        SELECT q.question_id, cs.book_id, q.page_start, q.page_end
        FROM questions q
        JOIN papers p ON p.paper_id=q.paper_id
        JOIN content_sources cs ON cs.source_id=p.source_id
        WHERE cs.book_id IS NOT NULL
        ORDER BY q.question_id
        """
    ).fetchall()
    for row in question_rows:
        con.execute(
            """
            INSERT OR IGNORE INTO question_sources
            (question_id,book_id,section_id,page_start,page_end,figure_ref,role,note)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            (row["question_id"], row["book_id"], None,
             row["page_start"], row["page_end"], None, "question",
             "derived from paper source"),
        )
    return source_to_book, len(paper_rows), len(question_rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-backup", action="store_true")
    args = parser.parse_args()

    know = sqlite3.connect(KNOW_DB)
    know.row_factory = sqlite3.Row
    exam = sqlite3.connect(EXAM_DB)
    exam.row_factory = sqlite3.Row
    know.execute("PRAGMA foreign_keys=ON")
    exam.execute("PRAGMA foreign_keys=ON")

    print("knowledge schema additions:",
          ensure_knowledge_schema(know) if not args.dry_run else "dry-run")
    print("exam schema additions:",
          ensure_exam_schema(exam) if not args.dry_run else "dry-run")
    if args.dry_run:
        books = know.execute("SELECT COUNT(*) FROM books").fetchone()[0]
        papers = exam.execute(
            "SELECT COUNT(*) FROM papers WHERE source_id IN "
            "(SELECT source_id FROM content_sources)"
        ).fetchone()[0]
        questions = exam.execute(
            "SELECT COUNT(*) FROM questions q JOIN papers p ON p.paper_id=q.paper_id "
            "WHERE p.source_id IN (SELECT source_id FROM content_sources)"
        ).fetchone()[0]
        print(f"dry-run: books={books}, papers_with_source={papers}, questions={questions}")
        know.close()
        exam.close()
        return 0

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    if not args.no_backup:
        for path in (KNOW_DB, EXAM_DB):
            backup = path.with_name(path.name + f".bak-{stamp}-before-source-provenance")
            shutil.copy2(path, backup)
            print("backup:", backup)

    with know:
        books_updated = apply_knowledge(know)
    with exam:
        source_to_book, paper_count, question_count = apply_exam(exam, know)

    know_integrity = know.execute("PRAGMA integrity_check").fetchone()[0]
    know_fk = know.execute("PRAGMA foreign_key_check").fetchall()
    exam_integrity = exam.execute("PRAGMA integrity_check").fetchone()[0]
    exam_fk = exam.execute("PRAGMA foreign_key_check").fetchall()

    report = [
        "# 来源追溯 / book_family 迁移报告",
        "",
        f"- 时间：{datetime.now().astimezone().isoformat(timespec='seconds')}",
        f"- `psychology_knowledge.db` integrity：{know_integrity}",
        f"- `psychology_knowledge.db` foreign_key_check：{'OK' if not know_fk else 'FAIL'}",
        f"- `psychology_exam.db` integrity：{exam_integrity}",
        f"- `psychology_exam.db` foreign_key_check：{'OK' if not exam_fk else 'FAIL'}",
        f"- books 更新：{books_updated}",
        f"- content_sources 映射到 book：{len(source_to_book)}",
        f"- paper_book_sources：{paper_count}",
        f"- question_sources：{question_count}",
        "",
        "## Books",
        "",
        "| book_id | book_family_id | status | edition |",
        "|---|---|---|---|",
    ]
    for row in know.execute(
        "SELECT book_id,book_family_id,status,edition FROM books ORDER BY book_id"
    ):
        report.append(f"| `{row['book_id']}` | `{row['book_family_id']}` | "
                      f"`{row['status']}` | `{row['edition']}` |")
    report += [
        "",
        "## 映射",
        "",
        "| source_id | book_id |",
        "|---|---|",
    ]
    for source_id, book_id in sorted(source_to_book.items()):
        report.append(f"| `{source_id}` | `{book_id}` |")
    report += [
        "",
        "## 说明",
        "",
        "- `books.book_family_id` 用于教材换版：同一教材的 2027/2028 属于同一 family。",
        "- `books.status` 当前全部为 `active`；旧版可改为 `archived`。",
        "- `paper_book_sources` 记录试卷来自哪本教材；`question_sources` 记录题目来自哪本教材/页码。",
        "- `content_sources.book_id` 是逻辑引用，跨库不建外键。",
        "- 现有 `paper_sources` 仍然表示“试卷 → 源文件”，不要与 `paper_book_sources` 混淆。",
    ]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(report) + "\n", encoding="utf-8")
    print("report:", REPORT)
    print(f"books={books_updated} sources={len(source_to_book)} "
          f"papers={paper_count} questions={question_count}")
    print("integrity:", know_integrity, exam_integrity,
          "fk:", "OK" if not know_fk and not exam_fk else "FAIL")
    know.close()
    exam.close()
    return 0 if know_integrity == "ok" and exam_integrity == "ok" and not know_fk and not exam_fk else 1


if __name__ == "__main__":
    raise SystemExit(main())
