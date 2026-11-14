#!/usr/bin/env python3
"""Batch-run question -> knowledge point linking for every paper.

Each paper is a checkpoint: link_question_kps.py writes at the end of a
paper, and this orchestrator skips papers that are already fully analyzed.
If the process is interrupted, rerun it; completed papers are skipped and
partially analyzed papers are relinked with --force.
"""
import argparse
import os
import shutil
import sqlite3
import subprocess
import sys
import time
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
EXAM_DB = os.path.join(ROOT, "data", "content", "psychology", "psychology_exam.db")
KNOW_DB = os.path.join(ROOT, "data", "content", "psychology", "psychology_knowledge.db")
LINK_SCRIPT = os.path.join(HERE, "link_question_kps.py")
REPORT_DIR = os.path.join(ROOT, "data", "content", "psychology", "reports", "question_analysis")
SUMMARY = os.path.join(ROOT, "data", "content", "psychology", "reports", "question_analysis", "question_analysis_all_report.md")


def mcq_counts():
    con = sqlite3.connect(EXAM_DB)
    counts = {
        row[0]: row[1] for row in con.execute(
            """
            SELECT paper_id, COUNT(*)
            FROM questions
            WHERE section='MCQ'
              AND correct_answer IS NOT NULL AND TRIM(correct_answer) <> ''
            GROUP BY paper_id
            """
        )
    }
    con.close()
    return counts


def analysis_counts():
    con = sqlite3.connect(KNOW_DB)
    counts = {
        row[0]: row[1] for row in con.execute(
            "SELECT paper_id, COUNT(*) FROM question_analysis GROUP BY paper_id"
        )
    }
    con.close()
    return counts


def run_paper(paper_id, mcq, analyzed, workers, report_dir, force_all=False):
    force = force_all
    report = os.path.join(report_dir, f"{paper_id}.md")
    cmd = [
        sys.executable, LINK_SCRIPT,
        "--paper", paper_id,
        "--workers", str(workers),
        "--report", report,
        "--no-backup",
    ]
    if force:
        cmd.append("--force")
    print(
        f"\n=== {paper_id}: {mcq} MCQ, existing {analyzed} "
        f"({'force relink' if force else 'resume/fresh'}) ===",
        flush=True,
    )
    # Largest paper is 378 questions; at 4-6 workers this is well under
    # 10 minutes. A per-paper timeout keeps one flaky paper from blocking
    # the whole batch.
    timeout = max(300, min(600, mcq * 4))
    started = time.time()
    try:
        result = subprocess.run(cmd, timeout=timeout)
        code = result.returncode
    except subprocess.TimeoutExpired:
        print(f"=== {paper_id}: TIMEOUT after {timeout}s ===", flush=True)
        code = "timeout"
    elapsed = time.time() - started
    print(
        f"=== {paper_id}: exit {code} in {elapsed:.1f}s ===",
        flush=True,
    )
    return code, elapsed


def write_summary(mcq, failures):
    con = sqlite3.connect(KNOW_DB)
    con.row_factory = sqlite3.Row
    rows = []
    for paper_id in sorted(mcq):
        total = mcq[paper_id]
        analyzed = con.execute(
            "SELECT COUNT(*) FROM question_analysis WHERE paper_id=?",
            (paper_id,),
        ).fetchone()[0]
        linked = con.execute(
            "SELECT COUNT(*) FROM question_analysis WHERE paper_id=? AND status='linked'",
            (paper_id,),
        ).fetchone()[0]
        needs = con.execute(
            "SELECT COUNT(*) FROM question_analysis WHERE paper_id=? AND status='needs_review'",
            (paper_id,),
        ).fetchone()[0]
        no_match = con.execute(
            "SELECT COUNT(*) FROM question_analysis WHERE paper_id=? AND status='no_match'",
            (paper_id,),
        ).fetchone()[0]
        core_table = (
            "question_concept_links"
            if con.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' "
                "AND name='question_concept_links'"
            ).fetchone()
            else "question_kp_links"
        )
        cores = con.execute(
            f"""
            SELECT COUNT(*)
            FROM {core_table} l
            JOIN question_analysis qa ON qa.question_id = l.question_id
            WHERE qa.paper_id = ? AND l.relation_type = 'core'
            """,
            (paper_id,),
        ).fetchone()[0]
        rows.append((paper_id, total, analyzed, linked, needs, no_match, cores))

    lines = [
        "# 全库题目解析关联报告",
        "",
        f"- 生成时间：{datetime.now().astimezone().isoformat(timespec='seconds')}",
        f"- 试卷数：{len(mcq)}",
        "",
        "| 试卷 | MCQ | 已分析 | linked | needs_review | no_match | core 链接 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    totals = [0, 0, 0, 0, 0, 0]
    for row in rows:
        paper_id, total, analyzed, linked, needs, no_match, cores = row
        totals[0] += total
        totals[1] += analyzed
        totals[2] += linked
        totals[3] += needs
        totals[4] += no_match
        totals[5] += cores
        lines.append(
            f"| `{paper_id}` | {total} | {analyzed} | {linked} | "
            f"{needs} | {no_match} | {cores} |"
        )
    lines.append(
        f"| **合计** | **{totals[0]}** | **{totals[1]}** | **{totals[2]}** | "
        f"**{totals[3]}** | **{totals[4]}** | **{totals[5]}** |"
    )

    flagged = con.execute(
        """
        SELECT paper_id, question_id, status, notes
        FROM question_analysis
        WHERE status IN ('needs_review','no_match')
        ORDER BY paper_id, question_id
        """
    ).fetchall()
    if flagged:
        lines += ["", "## needs_review / no_match", ""]
        for row in flagged:
            note = (row["notes"] or "").replace("\n", " ")[:240]
            lines.append(
                f"- `{row['question_id']}`（{row['status']}）：{note}"
            )

    if failures:
        lines += ["", "## 失败试卷", ""]
        for paper_id, code, elapsed in failures:
            lines.append(f"- `{paper_id}`：exit {code}，{elapsed:.1f}s")

    with open(SUMMARY, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    print("summary:", SUMMARY)
    con.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--paper", action="append", default=[],
                        help="only process these paper ids (repeatable)")
    parser.add_argument("--force-all", action="store_true",
                        help="relink even fully analyzed papers")
    args = parser.parse_args()

    if not os.path.exists(KNOW_DB):
        raise SystemExit(f"missing {KNOW_DB}")
    os.makedirs(REPORT_DIR, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = KNOW_DB + f".bak-{stamp}-before-full-analysis"
    shutil.copy2(KNOW_DB, backup)
    print("backup:", backup, flush=True)

    mcq = mcq_counts()
    analyzed = analysis_counts()
    papers = args.paper or sorted(mcq)
    unknown = [paper for paper in papers if paper not in mcq]
    if unknown:
        raise SystemExit("unknown/no-MCQ papers: " + ", ".join(unknown))

    todo = []
    for paper_id in papers:
        total = mcq[paper_id]
        have = analyzed.get(paper_id, 0)
        if have >= total and not args.force_all:
            print(f"skip {paper_id}: {have}/{total} already analyzed", flush=True)
            continue
        todo.append((paper_id, total, have))

    print(
        f"{len(todo)} papers to process; "
        f"{sum(total for _, total, _ in todo)} questions",
        flush=True,
    )
    started = time.time()
    failures = []
    for paper_id, total, have in todo:
        try:
            code, elapsed = run_paper(
                paper_id, total, have, args.workers, REPORT_DIR,
                force_all=args.force_all,
            )
            if code != 0:
                failures.append((paper_id, code, elapsed))
        except Exception as error:
            print(f"=== {paper_id}: ERROR {error} ===", flush=True)
            failures.append((paper_id, "error", 0.0))

    print(f"\nfinished in {time.time() - started:.1f}s", flush=True)
    if failures:
        print("failures:", failures, flush=True)
    write_summary(mcq, failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
