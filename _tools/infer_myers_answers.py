#!/usr/bin/env python3
"""Infer answers for Myers MCQs; the student edition has no answer key.

Answers are written with answer_source='ai_inferred' and
answer_confidence='medium'.  They must not be presented as official answers.
"""
import argparse
import json
import os
import re
import sqlite3
import sys
import time
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DB = os.path.join(ROOT, "data", "content", "psychology", "psychology_exam.db")
REPORT = os.path.join(ROOT, "data", "content", "psychology", "extraction", "myers", "myers_answer_report.md")
sys.path.insert(0, HERE)
import link_question_kps as linker  # noqa: E402


def parse_array(text):
    raw = (text or "").strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.I)
    raw = re.sub(r"\s*```$", "", raw)
    start, end = raw.find("["), raw.rfind("]")
    if start < 0 or end < start:
        raise ValueError("no JSON array")
    payload = re.sub(r",\s*([}\]])", r"\1", raw[start:end + 1])
    return json.loads(payload, strict=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=DB)
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--model", default="deepseek-flash[1m]")
    args = parser.parse_args()

    con = sqlite3.connect(args.db)
    con.row_factory = sqlite3.Row
    where = "q.paper_id LIKE 'psychology-myers-2024-%' AND q.section='MCQ'"
    if not args.force:
        where += " AND (q.correct_answer IS NULL OR q.correct_answer='')"
    questions = con.execute(
        f"SELECT q.* FROM questions q WHERE {where} ORDER BY q.paper_id, q.number"
    ).fetchall()
    if args.limit:
        questions = questions[:args.limit]
    print("questions:", len(questions))
    if not questions:
        return 0

    stats = {"answered": 0, "failed": 0, "buckets": {}}
    failures = []
    for start in range(0, len(questions), args.batch_size):
        batch = questions[start:start + args.batch_size]
        prompt = (
            "Choose the best answer (A-D) for each AP Psychology MCQ. "
            "Return ONLY a JSON array like "
            '[{"id":"...","answer":"B","confidence":0.85,"reason":"..."}].'
            "\n\n"
        )
        for index, q in enumerate(batch, 1):
            options = con.execute(
                "SELECT label, content FROM options WHERE question_id=? "
                "ORDER BY sort_order", (q["question_id"],)
            ).fetchall()
            prompt += (
                f"Item {index} id={q['question_id']}\n"
                f"Context: {(q['context'] or '')[:700]}\n"
                f"Stem: {q['stem']}\n"
                + "\n".join(f"{o['label']}. {o['content']}" for o in options)
                + "\n\n"
            )
        print(f"batch {start // args.batch_size + 1}: {len(batch)}", flush=True)
        try:
            text, usage = linker.call_api(
                "You are an AP Psychology exam solver. Return only JSON.",
                prompt, args.model, 4000, 60, 2,
            )
            data = parse_array(text)
        except Exception as error:
            print("  ERROR", error, flush=True)
            stats["failed"] += len(batch)
            failures.extend(q["question_id"] for q in batch)
            continue
        by_id = {row.get("id"): row for row in data if isinstance(row, dict)}
        for q in batch:
            row = by_id.get(q["question_id"])
            if not row:
                failures.append(q["question_id"])
                stats["failed"] += 1
                continue
            answer = str(row.get("answer") or "").strip().upper()[:1]
            valid = {
                option["label"] for option in con.execute(
                    "SELECT label FROM options WHERE question_id=?",
                    (q["question_id"],),
                )
            }
            if answer not in valid:
                failures.append(q["question_id"])
                stats["failed"] += 1
                continue
            confidence = row.get("confidence")
            con.execute(
                "UPDATE questions SET correct_answer=?, answer_source=?, "
                "answer_confidence=? WHERE question_id=?",
                (answer, "ai_inferred", "medium", q["question_id"]),
            )
            con.execute(
                "UPDATE options SET is_correct=CASE WHEN label=? THEN 1 ELSE 0 END "
                "WHERE question_id=?",
                (answer, q["question_id"]),
            )
            con.commit()
            stats["answered"] += 1
            stats["buckets"][answer] = stats["buckets"].get(answer, 0) + 1
        print("  answered so far:", stats["answered"], "failed:", stats["failed"],
              flush=True)
        time.sleep(0.2)

    con.close()
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    with open(REPORT, "w", encoding="utf-8") as handle:
        handle.write("# Myers 4e MCQ 答案推断报告\n\n")
        handle.write(f"- 生成时间：{datetime.now().isoformat(timespec='seconds')}\n")
        handle.write(f"- 题数：{stats['answered']} / {len(questions)}\n")
        handle.write(f"- 失败：{stats['failed']}\n")
        handle.write(f"- 答案分布：{stats['buckets']}\n")
        handle.write("- 来源：`ai_inferred`，**不是官方答案**；仅用于题目浏览和知识点关联。\n")
        if failures:
            handle.write("\n## 未完成\n\n")
            for qid in failures:
                handle.write(f"- `{qid}`\n")
    print("answered:", stats["answered"], "failed:", stats["failed"])
    print("report:", REPORT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
