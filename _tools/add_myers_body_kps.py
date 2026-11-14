#!/usr/bin/env python3
"""Add a small curated set of Myers body-only concepts to knowledge_points.

These concepts are taught in the body but are not in the publisher glossary;
they are needed for question linking (scientific attitude elements, Animism,
Overlearning, etc.).
"""
import argparse
import hashlib
import json
import os
import re
import sqlite3
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DB = os.path.join(ROOT, "data", "content", "psychology", "psychology_knowledge.db")
BOOK = "psychology-myers-2024"
PROMPT_VERSION = "myers-body-supplement-v1"

BODY_KPS = [
    {
        "name": "Scientific attitude",
        "section": "psychology-myers-2024-u0-m0-1",
        "page": 89,
        "quote": "The scientific attitude — curiosity + skepticism + humility — prepares us to think harder and smarter.",
        "plain": "curiosity, skepticism, and humility in inquiry",
    },
    {
        "name": "Curiosity",
        "section": "psychology-myers-2024-u0-m0-1",
        "page": 84,
        "quote": "a passion for exploring and understanding without misleading or being misled",
        "plain": "desire to explore and understand",
    },
    {
        "name": "Skepticism",
        "section": "psychology-myers-2024-u0-m0-1",
        "page": 87,
        "quote": "being skeptical but not cynical, open-minded but not gullible",
        "plain": "questioning claims and demanding evidence",
    },
    {
        "name": "Humility",
        "section": "psychology-myers-2024-u0-m0-1",
        "page": 87,
        "quote": "awareness of our vulnerability to error and openness to surprises and new perspectives",
        "plain": "awareness of one's vulnerability to error",
    },
    {
        "name": "Animism",
        "section": "psychology-myers-2024-u3-m3-4",
        "page": 1208,
        "quote": "a belief that inanimate objects are alive or have lifelike feelings and motivations",
        "plain": "believing inanimate objects are alive",
    },
    {
        "name": "Overlearning",
        "section": "psychology-myers-2024-u2-m2-3",
        "page": 794,
        "quote": "Additional rehearsal (overlearning) of verbal information increases retention",
        "plain": "continued rehearsal after material is learned",
    },
    {
        "name": "Vicarious conditioning",
        "section": "psychology-myers-2024-u3-m3-9",
        "page": 1474,
        "quote": "By watching models, we experience vicarious conditioning—vicarious reinforcement or vicarious punishment.",
        "plain": "learning by observing others' reinforcement or punishment",
    },
    {
        "name": "Halo effect",
        "section": "psychology-myers-2024-u4-m4-2",
        "page": 1572,
        "quote": "we may believe beautiful or famous people are especially smart or trustworthy (the halo effect)",
        "plain": "one positive trait colors overall impression",
    },
    {
        "name": "Belongingness",
        "section": "psychology-myers-2024-u4-m4-7b",
        "page": 1903,
        "quote": "the need to build and maintain relationships and to feel part of a group",
        "plain": "need to build relationships and feel included",
    },
    {
        "name": "Tardive dyskinesia",
        "section": "psychology-myers-2024-u5-m5-5d",
        "page": 2463,
        "quote": "a movement disorder related to the regulation of dopamine in the nervous system",
        "plain": "involuntary movements from long-term antipsychotics",
    },
    {
        "name": "Erikson's psychosocial stage theory",
        "section": "psychology-myers-2024-u3-m3-6b",
        "page": 1316,
        "quote": "each stage of life has its own psychosocial task, a crisis that needs resolution",
        "plain": "eight life stages with psychosocial tasks",
    },
]


def norm(value):
    value = (value or "").lower().replace("’", "'")
    value = value.replace("ﬁ", "fi").replace("ﬂ", "fl")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=DB)
    args = ap.parse_args()
    con = sqlite3.connect(args.db)
    con.row_factory = sqlite3.Row
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    added = 0
    for item in BODY_KPS:
        section = con.execute(
            "SELECT section_id FROM sections WHERE section_id=?",
            (item["section"],),
        ).fetchone()
        if not section:
            print("missing section", item["section"], item["name"])
            continue
        exists = con.execute(
            "SELECT 1 FROM knowledge_points WHERE book_id=? AND section_id=? AND name_normalized=?",
            (BOOK, item["section"], norm(item["name"])),
        ).fetchone()
        if exists:
            continue
        quote_hash = hashlib.sha256(norm(item["quote"]).encode("utf-8")).hexdigest()
        kp_id = f"{BOOK}-kp-" + hashlib.sha1(
            (BOOK + item["section"] + norm(item["name"]) + quote_hash).encode("utf-8")
        ).hexdigest()[:16]
        con.execute(
            """
            INSERT INTO knowledge_points
            (kp_id, book_id, section_id, subheading, name, name_normalized,
             definition_quote, definition_type, definition_language, source_page,
             quote_hash, plain_en, plain_word_count, confidence, status,
             prompt_version, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (kp_id, BOOK, item["section"], None, item["name"], norm(item["name"]),
             item["quote"], "explicit", "en", item["page"], quote_hash,
             item["plain"], len(re.findall(r"[A-Za-z0-9']+", item["plain"])),
             0.9, "approved", PROMPT_VERSION, now),
        )
        for alias in {item["name"], re.sub(r"\([^)]*\)", "", item["name"]).strip()}:
            if alias:
                con.execute(
                    "INSERT OR IGNORE INTO kp_aliases"
                    "(kp_id,alias,alias_normalized,source,match_mode)"
                    " VALUES (?,?,?,?,?)",
                    (kp_id, alias, norm(alias), "myers-body", "insensitive"),
                )
        added += 1
    con.commit()
    print("added body KPs:", added)
    print("integrity:", con.execute("PRAGMA integrity_check").fetchone()[0])
    con.close()


if __name__ == "__main__":
    main()
