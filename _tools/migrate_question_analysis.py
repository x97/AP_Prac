#!/usr/bin/env python3
"""Create question-analysis tables in psychology_knowledge.db.

The exam DB (psychology_exam.db) stays exam-only.  Question ids are logical
references into psychology_exam.db, so there is no cross-database foreign key.

Tables:
  question_analysis    one row per analyzed question
  question_kp_links    question -> core/supporting/confusable knowledge point
  question_keywords    keyword occurrences in the question text

Run once before _tools/link_question_kps.py.
"""
import os
import shutil
import sqlite3
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DB = os.path.join(ROOT, "data", "content", "psychology", "psychology_knowledge.db")

TABLES = {
    "question_analysis": """
        CREATE TABLE IF NOT EXISTS question_analysis (
            question_id    TEXT PRIMARY KEY,
            paper_id       TEXT NOT NULL,
            status         TEXT NOT NULL
                           CHECK (status IN ('linked','needs_review','no_match','skipped')),
            model          TEXT,
            prompt_version TEXT,
            notes          TEXT,
            updated_at     TEXT NOT NULL
        )
    """,
    "question_kp_links": """
        CREATE TABLE IF NOT EXISTS question_kp_links (
            link_id       INTEGER PRIMARY KEY,
            question_id   TEXT NOT NULL,
            kp_id         TEXT NOT NULL
                          REFERENCES knowledge_points(kp_id) ON DELETE CASCADE,
            relation_type TEXT NOT NULL
                          CHECK (relation_type IN ('core','supporting','confusable')),
            option_label  TEXT,
            confidence    REAL,
            evidence      TEXT,
            rationale     TEXT,
            created_at    TEXT NOT NULL,
            CHECK (relation_type <> 'confusable' OR option_label IS NOT NULL)
        )
    """,
    "question_keywords": """
        CREATE TABLE IF NOT EXISTS question_keywords (
            keyword_id   INTEGER PRIMARY KEY,
            question_id  TEXT NOT NULL,
            surface      TEXT NOT NULL,
            normalized   TEXT NOT NULL,
            kp_id        TEXT REFERENCES knowledge_points(kp_id) ON DELETE SET NULL,
            role         TEXT NOT NULL
                         CHECK (role IN ('core','supporting','mentioned','distractor')),
            location     TEXT NOT NULL
                         CHECK (location IN ('stem','context','correct_option','option')),
            option_label TEXT,
            confidence   REAL,
            created_at   TEXT NOT NULL,
            CHECK (location <> 'option' OR option_label IS NOT NULL)
        )
    """,
}

INDEXES = [
    """CREATE UNIQUE INDEX IF NOT EXISTS ux_qkp
       ON question_kp_links(question_id, kp_id, relation_type, IFNULL(option_label,''))""",
    "CREATE INDEX IF NOT EXISTS ix_qkp_q ON question_kp_links(question_id, relation_type)",
    "CREATE INDEX IF NOT EXISTS ix_qkp_kp ON question_kp_links(kp_id)",
    """CREATE UNIQUE INDEX IF NOT EXISTS ux_qkw
       ON question_keywords(question_id, normalized, location,
                            IFNULL(option_label,''), IFNULL(kp_id,''))""",
    "CREATE INDEX IF NOT EXISTS ix_qkw_q ON question_keywords(question_id)",
    "CREATE INDEX IF NOT EXISTS ix_qkw_kp ON question_keywords(kp_id)",
    "CREATE INDEX IF NOT EXISTS ix_qa_paper ON question_analysis(paper_id)",
]


def main() -> int:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = DB + f".bak-{stamp}-pre-question-analysis"
    shutil.copy2(DB, backup)
    print("backup:", backup)

    con = sqlite3.connect(DB)
    con.execute("PRAGMA foreign_keys=ON")

    columns = {row[1] for row in con.execute("PRAGMA table_info(kp_aliases)")}
    if "match_mode" not in columns:
        con.execute(
            "ALTER TABLE kp_aliases ADD COLUMN match_mode TEXT NOT NULL "
            "DEFAULT 'insensitive' "
            "CHECK (match_mode IN ('insensitive','case_sensitive'))"
        )
        print("kp_aliases: added match_mode")
    else:
        print("kp_aliases: match_mode already present")

    with con:
        for name, ddl in TABLES.items():
            con.execute(ddl)
            print("table:", name)
        for ddl in INDEXES:
            con.execute(ddl)

    integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
    fk = con.execute("PRAGMA foreign_key_check").fetchall()
    print("integrity_check:", integrity)
    print("foreign_key_check:", "OK" if not fk else fk[:5])
    print("new tables:", ", ".join(
        row[0] for row in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name IN ('question_analysis','question_kp_links','question_keywords') "
            "ORDER BY name"
        )
    ))
    con.close()
    return 0 if integrity == "ok" and not fk else 1


if __name__ == "__main__":
    sys.exit(main())
