#!/usr/bin/env python3
"""Generate AI answer explanations for MCQ correct options.

Writes ``options.ai_explanation`` only.  ``options.explanation`` keeps its
original meaning (source-book / official explanation) and is never touched.

The explanation is generated from the question stem/context, all options and
the verified correct answer.  It is stored on the correct option only.  The
quiz page labels it as AI-generated, separate from the book explanation.

Usage:
    export ANTHROPIC_API_KEY=...        # or ANTHROPIC_AUTH_TOKEN
    python3 _tools/generate_ai_explanations.py --paper psychology-ap-2019 --dry-run --limit 3
    python3 _tools/generate_ai_explanations.py --paper psychology-ap-2019 --limit 5
    python3 _tools/generate_ai_explanations.py --paper psychology-ap-2019
    python3 _tools/generate_ai_explanations.py --paper psychology-ap-2019 --force

The run is idempotent: questions whose correct option already has a
non-empty ``ai_explanation`` are skipped unless ``--force`` is passed.
Generated text is exported under the subject source directory before the
database is updated, and a coverage report is written there too:

    data/content/<subject>/extraction/
    data/content/<subject>/reports/ai_explanation_report.md

Use ``--subject <subject_id>`` to choose the configured subject; the script
defaults to psychology. ``--db`` overrides the resolved source database.
"""
import argparse
import json
import os
import re
import shutil
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from subject_config import load_subject, source_paths

DEFAULT_API_BASE = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
DEFAULT_MODEL = os.environ.get(
    "ANTHROPIC_MODEL",
    os.environ.get("CLAUDE_MODEL", "claude-sonnet-5-5"),
)
API_KEY = os.environ.get("ANTHROPIC_AUTH_TOKEN") or os.environ.get("ANTHROPIC_API_KEY")

SYSTEM_PROMPT = """You are an experienced AP Psychology teacher writing answer explanations for a practice question bank. You will receive multiple-choice questions, their options, and the verified correct answer.

For each question, write a concise explanation (2-4 sentences, roughly 40-90 words) of why the correct answer is correct.

Rules:
- Use standard AP Psychology terminology and reasoning. Explain the concept rather than merely restating the option.
- Ground the explanation in the question's scenario and in the given correct answer. Never contradict the given answer.
- Do not invent studies, statistics, names, or details that are not in the question. General textbook definitions are allowed.
- Do not mention an answer key, a book, or that the answer was supplied.
- Do not use markdown, bullet points, headings, or code fences.
- Refer to concepts by name; do not answer with a bare option letter.
- Keep the explanation self-contained for a student who has just seen the question.
- If a distractor is especially tempting, you may briefly say why it does not fit, but focus on the correct answer.
- Return only the requested output, with no commentary before or after it.
"""

LANGUAGE_INSTRUCTIONS = {
    "en": "Write the explanation in English.",
    "zh": "Write the explanation in Simplified Chinese. Keep AP Psychology terms in English, with a Chinese gloss on first use.",
    "bilingual": "Write the explanation first in English, then add a concise Simplified Chinese translation.",
}


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def clean_text(value):
    value = (value or "").replace(" ", " ")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n\s*\n+", "\n\n", value)
    return value.strip()


def clean_explanation(value):
    text = clean_text(str(value or ""))
    text = re.sub(r"^```(?:json|markdown|text)?\s*", "", text, flags=re.I)
    text = re.sub(r"\s*```$", "", text)
    text = re.sub(r"^\s*(?:Explanation|Answer|Response)\s*[:\-]\s*", "", text, flags=re.I)
    text = text.strip().strip('"').strip("'").strip()
    text = re.sub(r"\s+", " ", text).strip()
    return text


def validate_explanation(text):
    """Return an error message, or None when the text looks acceptable."""
    if not text:
        return "empty explanation"
    words = len(re.findall(r"[A-Za-z0-9一-鿿]+", text))
    if len(text) < 80:
        return f"too short ({len(text)} chars)"
    if len(text) > 1800:
        return f"too long ({len(text)} chars)"
    if words < 20:
        return f"too few words ({words})"
    if words > 260:
        return f"too many words ({words})"
    if re.search(r"\bas an ai\b|\blanguage model\b|\bi cannot\b", text, re.I):
        return "contains meta/AI disclaimer"
    return None


def load_items(con, papers, only_without_book, force, limit,
               skip_option_images=True, skip_figures=False):
    """Load MCQ questions and group their options."""
    asset_rows = con.execute(
        "SELECT question_id, option_label FROM assets"
    ).fetchall()
    option_image_qids = {
        row["question_id"] for row in asset_rows if row["option_label"]
    }
    figure_qids = {
        row["question_id"] for row in asset_rows if not row["option_label"]
    }

    sql = """
        SELECT q.question_id, q.paper_id, q.number, q.stem, q.context,
               q.correct_answer,
               o.label, o.content, o.sort_order,
               o.explanation, o.ai_explanation
        FROM questions q
        JOIN options o ON o.question_id = q.question_id
        WHERE q.section = 'MCQ'
          AND q.correct_answer IS NOT NULL
          AND TRIM(q.correct_answer) <> ''
        ORDER BY q.paper_id, q.number, o.sort_order
    """
    rows = con.execute(sql).fetchall()
    grouped = {}
    for row in rows:
        qid = row["question_id"]
        item = grouped.get(qid)
        if item is None:
            item = grouped[qid] = {
                "question_id": qid,
                "paper_id": row["paper_id"],
                "number": row["number"],
                "stem": row["stem"],
                "context": row["context"] or "",
                "answer": (row["correct_answer"] or "").strip().upper(),
                "options": [],
                "has_option_image": qid in option_image_qids,
                "has_figure": qid in figure_qids,
            }
        option = {
            "label": (row["label"] or "").strip().upper(),
            "content": row["content"],
            "sort_order": row["sort_order"],
            "explanation": row["explanation"] or "",
            "ai_explanation": row["ai_explanation"] or "",
        }
        item["options"].append(option)

    paper_set = set(papers)
    items, skipped_existing, skipped_book, skipped_invalid = [], 0, 0, []
    skipped_option_image, skipped_figure = [], []
    for item in grouped.values():
        if paper_set and item["paper_id"] not in paper_set:
            continue
        correct = next(
            (o for o in item["options"] if o["label"] == item["answer"]),
            None,
        )
        if correct is None:
            skipped_invalid.append(item["question_id"])
            continue
        if not force and clean_text(correct["ai_explanation"]):
            skipped_existing += 1
            continue
        if only_without_book and clean_text(correct["explanation"]):
            skipped_book += 1
            continue
        if item["has_option_image"] and skip_option_images:
            skipped_option_image.append(item["question_id"])
            continue
        if item["has_figure"] and skip_figures:
            skipped_figure.append(item["question_id"])
            continue
        item["answer_content"] = correct["content"]
        item["options"].sort(key=lambda o: (o["sort_order"] is None, o["sort_order"], o["label"]))
        items.append(item)

    items.sort(key=lambda i: (i["paper_id"], i["number"]))
    if limit is not None:
        items = items[:limit]
    return items, {
        "skipped_existing": skipped_existing,
        "skipped_book": skipped_book,
        "skipped_invalid": skipped_invalid,
        "skipped_option_image": skipped_option_image,
        "skipped_figure": skipped_figure,
    }


def question_block(item, index=None):
    head = f"Question ID: {item['question_id']}"
    if index is not None:
        head = f"=== QUESTION {index} · {item['question_id']} ==="
    lines = [head, f"Question: {clean_text(item['stem'])}"]
    if clean_text(item["context"]):
        lines.append(f"Context: {clean_text(item['context'])}")
    lines.append("Options:")
    for option in item["options"]:
        lines.append(f"{option['label']}. {clean_text(option['content'])}")
    lines.append(f"Correct answer: {item['answer']}. {clean_text(item['answer_content'])}")
    return "\n".join(lines)


def build_batch_prompt(items, language):
    intro = (
        f"Write one explanation for each of the {len(items)} AP Psychology "
        "multiple-choice questions below.\n"
        f"{LANGUAGE_INSTRUCTIONS[language]}\n"
        "Return ONLY a JSON object with this exact shape (no code fences):\n"
        '{"explanations":[{"question_id":"...","explanation":"..."}]}\n'
        "Include every question exactly once and copy each question_id verbatim."
    )
    blocks = [question_block(item, i + 1) for i, item in enumerate(items)]
    return intro + "\n\n" + "\n\n".join(blocks)


def build_single_prompt(item, language):
    return (
        "Write the explanation for the AP Psychology multiple-choice question "
        "below.\n"
        f"{LANGUAGE_INSTRUCTIONS[language]}\n"
        "Return only the explanation text (2-4 sentences), with no JSON, "
        "markdown, labels or commentary.\n\n"
        + question_block(item)
    )


def call_api(prompt, model, max_tokens, timeout, retries):
    if not API_KEY:
        raise RuntimeError(
            "missing API key: set ANTHROPIC_AUTH_TOKEN or ANTHROPIC_API_KEY"
        )
    base = (DEFAULT_API_BASE or "https://api.anthropic.com").rstrip("/")
    url = base + "/v1/messages"
    body = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": 0.2,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": prompt}],
    }
    payload = json.dumps(body).encode("utf-8")
    headers = {
        "content-type": "application/json",
        "anthropic-version": "2023-06-01",
        "x-api-key": API_KEY,
        "authorization": "Bearer " + API_KEY,
    }
    last_error = None
    for attempt in range(retries + 1):
        request = urllib.request.Request(url, data=payload, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                data = json.load(response)
            text = "".join(
                block.get("text", "")
                for block in data.get("content", [])
                if block.get("type", "text") == "text"
            )
            usage = data.get("usage") or {}
            return text, usage
        except urllib.error.HTTPError as error:
            detail = ""
            try:
                detail = error.read().decode("utf-8", "replace")[:600]
            except Exception:
                pass
            last_error = RuntimeError(f"HTTP {error.code}: {detail}")
            if error.code in (408, 409, 429, 500, 502, 503, 504) and attempt < retries:
                time.sleep(2 ** attempt)
                continue
            raise last_error
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            last_error = RuntimeError(f"network error: {error}")
            if attempt < retries:
                time.sleep(2 ** attempt)
                continue
            raise last_error
    raise last_error or RuntimeError("API call failed")


def parse_batch_response(text):
    raw = (text or "").strip()
    if not raw:
        raise ValueError("empty API response")
    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.I)
    raw = re.sub(r"\s*```$", "", raw)
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end < start:
        start, end = raw.find("["), raw.rfind("]")
    if start < 0 or end < start:
        raise ValueError("response contains no JSON object/array")
    data = json.loads(raw[start:end + 1])
    if isinstance(data, dict):
        entries = data.get("explanations") or data.get("items") or data.get("results")
    else:
        entries = data
    if not isinstance(entries, list):
        raise ValueError("JSON has no explanations list")
    out = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        qid = entry.get("question_id") or entry.get("questionId") or entry.get("id")
        text = entry.get("explanation") or entry.get("text") or entry.get("answer")
        if qid and text:
            out[str(qid).strip()] = clean_explanation(text)
    return out


def parse_single_response(text):
    raw = (text or "").strip()
    if not raw:
        raise ValueError("empty API response")
    if raw.lstrip().startswith(("{", "[")):
        try:
            parsed = parse_batch_response(raw)
            if parsed:
                return next(iter(parsed.values()))
        except Exception:
            pass
    return clean_explanation(raw)


def generate_one(item, model, max_tokens, timeout, retries, language):
    """Generate one explanation, with one validation retry."""
    last_error = "unknown error"
    for attempt in range(2):
        text, usage = call_api(
            build_single_prompt(item, language), model, max_tokens, timeout, retries
        )
        explanation = parse_single_response(text)
        error = validate_explanation(explanation)
        if error is None:
            return explanation, usage
        last_error = error
        if attempt == 0:
            item = dict(item)
            item["stem"] = (
                item["stem"]
                + "\n\n(Reminder: write a complete 2-4 sentence explanation of "
                "the concept and why it fits the scenario; do not return a "
                "fragment.)"
            )
    raise ValueError(f"validation failed: {last_error}")


def generate_batch(batch, model, max_tokens, timeout, retries, language):
    results, errors = {}, []
    usage_total = {"input_tokens": 0, "output_tokens": 0}

    parsed = {}
    batch_error = None
    try:
        text, usage = call_api(
            build_batch_prompt(batch, language), model, max_tokens, timeout, retries
        )
        for key in usage_total:
            usage_total[key] += int(usage.get(key) or 0)
        parsed = parse_batch_response(text)
    except Exception as error:
        batch_error = str(error)

    for item in batch:
        qid = item["question_id"]
        explanation = parsed.get(qid)
        error = validate_explanation(explanation) if explanation else "missing from batch response"
        if error is None:
            results[qid] = explanation
        else:
            # Fall back to an individual request for this question.
            try:
                explanation, usage = generate_one(
                    item, model, max_tokens, timeout, retries, language
                )
                for key in usage_total:
                    usage_total[key] += int(usage.get(key) or 0)
                results[qid] = explanation
            except Exception as single_error:
                errors.append({
                    "question_id": qid,
                    "paper_id": item["paper_id"],
                    "error": f"{error}; fallback: {single_error}",
                    **({"batch_error": batch_error} if batch_error else {}),
                })
    return results, errors, usage_total


def ensure_ai_column(con):
    columns = {row[1] for row in con.execute("PRAGMA table_info(options)")}
    if "ai_explanation" not in columns:
        raise SystemExit(
            "options.ai_explanation is missing; run:\n"
            "  ALTER TABLE options ADD COLUMN ai_explanation TEXT;"
        )


def write_export(path, records, errors, run):
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    payload = {
        "generated_at": run["generated_at"],
        "model": run["model"],
        "language": run["language"],
        "papers": run["papers"],
        "count": len(records),
        "usage": run["usage"],
        "items": records,
        "errors": errors,
    }
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    return path


def write_report(con, papers, run, errors, report_path):
    paper_set = set(papers) if papers else None
    rows = con.execute(
        """
        SELECT q.paper_id,
               COUNT(DISTINCT q.question_id) AS mcq,
               COUNT(DISTINCT CASE
                 WHEN o.is_correct = 1
                  AND o.explanation IS NOT NULL
                  AND TRIM(o.explanation) <> ''
                 THEN q.question_id END) AS book_explained,
               COUNT(DISTINCT CASE
                 WHEN o.is_correct = 1
                  AND o.ai_explanation IS NOT NULL
                  AND TRIM(o.ai_explanation) <> ''
                 THEN q.question_id END) AS ai_explained,
               COUNT(DISTINCT CASE
                 WHEN o.is_correct = 1
                  AND o.ai_explanation IS NOT NULL
                  AND TRIM(o.ai_explanation) <> ''
                  AND q.question_id IN (
                    SELECT question_id FROM assets WHERE option_label IS NULL
                  )
                 THEN q.question_id END) AS ai_with_figure,
               COUNT(DISTINCT CASE
                 WHEN o.is_correct = 1
                  AND (
                    TRIM(COALESCE(o.explanation, '')) <> ''
                    OR TRIM(COALESCE(o.ai_explanation, '')) <> ''
                  )
                 THEN q.question_id END) AS covered
        FROM questions q
        LEFT JOIN options o ON o.question_id = q.question_id
        WHERE q.section = 'MCQ'
          AND q.correct_answer IS NOT NULL
          AND TRIM(q.correct_answer) <> ''
        GROUP BY q.paper_id
        ORDER BY q.paper_id
        """
    ).fetchall()
    if paper_set:
        rows = [row for row in rows if row["paper_id"] in paper_set]
    total = {"mcq": 0, "book": 0, "ai": 0, "fig": 0, "covered": 0}
    for row in rows:
        total["mcq"] += row["mcq"]
        total["book"] += row["book_explained"]
        total["ai"] += row["ai_explained"]
        total["fig"] += row["ai_with_figure"]
        total["covered"] += row["covered"]
    coverage_pct = (
        round(total["ai"] / total["mcq"] * 100, 1) if total["mcq"] else 0
    )
    lines = [
        "# AI 答案解析覆盖报告",
        "",
        f"- 生成时间：{run['generated_at']}",
        f"- 模型：`{run['model']}`",
        f"- 语言：`{run['language']}`",
        f"- 当前 AI 覆盖：{total['ai']} / {total['mcq']} 道 MCQ（{coverage_pct}%）；"
        f"缺任何解析 {total['mcq'] - total['covered']} 道",
        f"- 本次运行生成：{run['generated']} 题；失败：{len(errors)} 题；"
        f"跳过已有 AI {run['skipped_existing']} 题、原书解析 {run['skipped_book']} 题",
        "",
        "> AI 解析由模型根据题干、选项和**已核对的正确答案**生成，"
        "不是官方或原书解析，不能替代 `options.explanation`。"
        "刷题页会把两者分开显示，并标注“AI 生成解析”。",
        "> “其中含图题”表示题目/选项带图表素材；当前生成只发送文字，"
        "图表本身没有送给模型，这部分解析建议人工复核。",
        "",
        "| 试卷 | MCQ | 原书解析 | AI 解析 | 其中含图题 | 缺任何解析 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        mcq, book, ai = row["mcq"], row["book_explained"], row["ai_explained"]
        fig, covered = row["ai_with_figure"], row["covered"]
        lines.append(
            f"| `{row['paper_id']}` | {mcq} | {book} | {ai} | {fig} | {mcq - covered} |"
        )
    lines.append(
        f"| **合计** | **{total['mcq']}** | **{total['book']}** | "
        f"**{total['ai']}** | **{total['fig']}** | "
        f"**{total['mcq'] - total['covered']}** |"
    )
    skipped_option_image = run.get("skipped_option_image") or []
    if skipped_option_image:
        lines += [
            "",
            "## 未生成：选项本身是图片",
            "",
            "以下题目的选项是图片，文字里没有选项内容，未调用模型，建议人工补：",
            "",
        ]
        lines += [f"- `{qid}`" for qid in skipped_option_image]
    if errors:
        lines += ["", "## 失败清单", ""]
        for error in errors:
            lines.append(f"- `{error['question_id']}`：{error['error']}")
    lines += [
        "",
        "## 复跑命令",
        "",
        "```bash",
        "# 单套卷 / 全部未生成 AI 解析的题",
        "python3 _tools/generate_ai_explanations.py --subject <subject_id> --paper <paper_id>",
        "python3 _tools/generate_ai_explanations.py --subject <subject_id> --all --skip-book-explained",
        "```",
        "",
    ]
    directory = os.path.dirname(report_path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
    return report_path


def main():
    parser = argparse.ArgumentParser(
        description="Generate AI explanations for MCQ correct options."
    )
    parser.add_argument("--paper", action="append", default=[], help="paper_id (repeatable)")
    parser.add_argument("--all", action="store_true", help="process every paper")
    parser.add_argument("--limit", type=int, help="process at most N questions")
    parser.add_argument("--force", action="store_true", help="regenerate existing AI explanations")
    parser.add_argument(
        "--skip-book-explained",
        action="store_true",
        help="skip questions that already have a source-book explanation",
    )
    parser.add_argument(
        "--include-option-images",
        action="store_true",
        help="also process questions whose options are images (default: skip)",
    )
    parser.add_argument(
        "--skip-figures",
        action="store_true",
        help="skip questions that have a question-level figure/table asset",
    )
    parser.add_argument("--dry-run", action="store_true", help="print prompts, do not call the API or write")
    parser.add_argument("--batch-size", type=int, default=5)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--language", choices=sorted(LANGUAGE_INSTRUCTIONS), default="en")
    parser.add_argument("--max-tokens", type=int, default=3000)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--retries", type=int, default=4)
    parser.add_argument("--subject", default="psychology", help="subject_id from config/subjects/")
    parser.add_argument("--db", help="override the subject exam database path")
    parser.add_argument("--export-dir", help="override the intermediate JSON directory")
    parser.add_argument("--out-json", help="intermediate JSON path")
    parser.add_argument("--no-backup", action="store_true", help="skip the pre-write DB backup")
    parser.add_argument("--report", help="coverage report path")
    args = parser.parse_args()

    if args.all and args.paper:
        parser.error("use either --paper or --all, not both")
    if not args.all and not args.paper:
        parser.error("one of --paper or --all is required")
    if args.batch_size < 1 or args.workers < 1:
        parser.error("--batch-size and --workers must be positive")

    subject_config = load_subject(args.subject)
    paths = source_paths(subject_config)
    db_path = Path(args.db).expanduser().resolve() if args.db else paths["exam_db"]
    export_dir = (
        Path(args.export_dir).expanduser().resolve()
        if args.export_dir
        else paths["source_dir"] / "extraction"
    )
    report_path = (
        Path(args.report).expanduser().resolve()
        if args.report
        else paths["source_dir"] / "reports" / "ai_explanation_report.md"
    )
    if not db_path.exists():
        raise SystemExit(f"subject exam database not found: {db_path}")
    print(f"subject: {args.subject}")
    print("database:", db_path)

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    ensure_ai_column(con)

    if args.paper:
        known = {row[0] for row in con.execute("SELECT paper_id FROM papers")}
        unknown = [paper for paper in args.paper if paper not in known]
        if unknown:
            raise SystemExit("unknown paper_id: " + ", ".join(unknown))

    items, skipped = load_items(
        con,
        args.paper,
        args.skip_book_explained,
        args.force,
        args.limit,
        skip_option_images=not args.include_option_images,
        skip_figures=args.skip_figures,
    )
    print(
        f"loaded {len(items)} questions to generate "
        f"(skipped: existing ai={skipped['skipped_existing']}, "
        f"book-explained={skipped['skipped_book']}, "
        f"missing correct option={len(skipped['skipped_invalid'])}, "
        f"option-image={len(skipped['skipped_option_image'])}, "
        f"figure={len(skipped['skipped_figure'])})"
    )
    if skipped["skipped_invalid"]:
        print("warning: no option row matching correct_answer for:", ", ".join(skipped["skipped_invalid"][:10]))
    if skipped["skipped_option_image"]:
        print("skipped option-image questions:", ", ".join(skipped["skipped_option_image"][:10]))
    if not items:
        print("nothing to generate")
        run = {
            "generated_at": now_iso(),
            "model": args.model,
            "language": args.language,
            "papers": sorted(args.paper) if args.paper else ["*"],
            "usage": {"input_tokens": 0, "output_tokens": 0},
            "generated": 0,
            "skipped_existing": skipped["skipped_existing"],
            "skipped_book": skipped["skipped_book"],
            "skipped_option_image": skipped["skipped_option_image"],
        }
        report_path = write_report(
            con, args.paper, run, [], str(report_path)
        )
        con.close()
        print("report:", report_path)
        return 0

    if args.dry_run:
        for start in range(0, len(items), args.batch_size):
            print("\n" + "=" * 78)
            print(build_batch_prompt(items[start:start + args.batch_size], args.language))
        print(f"\ndry run: {len(items)} questions, would use "
              f"{max(1, (len(items) + args.batch_size - 1) // args.batch_size)} batch request(s)")
        con.close()
        return 0

    batches = [
        items[start:start + args.batch_size]
        for start in range(0, len(items), args.batch_size)
    ]
    generated, errors = {}, []
    usage_total = {"input_tokens": 0, "output_tokens": 0}
    started = time.time()

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(
                generate_batch,
                batch,
                args.model,
                args.max_tokens,
                args.timeout,
                args.retries,
                args.language,
            ): batch
            for batch in batches
        }
        done = 0
        for future in as_completed(futures):
            batch = futures[future]
            done += 1
            try:
                results, batch_errors, usage = future.result()
            except Exception as error:
                results, batch_errors = {}, [
                    {
                        "question_id": item["question_id"],
                        "paper_id": item["paper_id"],
                        "error": str(error),
                    }
                    for item in batch
                ]
                usage = {}
            generated.update(results)
            errors.extend(batch_errors)
            for key in usage_total:
                usage_total[key] += int((usage or {}).get(key) or 0)
            print(
                f"[{done}/{len(batches)}] {len(results)}/{len(batch)} ok"
                + (f", {len(batch_errors)} failed" if batch_errors else ""),
                flush=True,
            )

    by_id = {item["question_id"]: item for item in items}
    records = []
    for qid in sorted(generated, key=lambda q: (by_id[q]["paper_id"], by_id[q]["number"])):
        item = by_id[qid]
        records.append({
            "question_id": qid,
            "paper_id": item["paper_id"],
            "number": item["number"],
            "answer_label": item["answer"],
            "answer_content": clean_text(item["answer_content"]),
            "explanation": generated[qid],
            "has_figure": item["has_figure"],
        })

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    papers = sorted(args.paper) if args.paper else []
    slug = "-".join(papers) if papers else "all"
    out_json = args.out_json or str(
        export_dir / f"ai_explanations_{slug}.json"
    )
    run = {
        "generated_at": now_iso(),
        "model": args.model,
        "language": args.language,
        "papers": papers or ["*"],
        "usage": usage_total,
        "generated": len(records),
        "skipped_existing": skipped["skipped_existing"],
        "skipped_book": skipped["skipped_book"],
        "skipped_option_image": skipped["skipped_option_image"],
    }
    export_path = write_export(out_json, records, errors, run)

    print(
        f"generated {len(records)} explanations, {len(errors)} failed, "
        f"tokens in/out = {usage_total['input_tokens']}/{usage_total['output_tokens']}, "
        f"{time.time() - started:.1f}s"
    )
    print("export:", export_path)

    if not records:
        con.close()
        print("no records to write; database unchanged")
        return 1 if errors else 0

    if not args.no_backup:
        backup = f"{db_path}.bak-{stamp}-ai-explanation"
        shutil.copy2(db_path, backup)
        print("backup:", backup)

    con.execute("PRAGMA foreign_keys = ON")
    updated = 0
    with con:
        for record in records:
            cursor = con.execute(
                "UPDATE options SET ai_explanation = ? "
                "WHERE question_id = ? AND label = ?",
                (record["explanation"], record["question_id"], record["answer_label"]),
            )
            if cursor.rowcount != 1:
                print(
                    f"warning: update matched {cursor.rowcount} rows for "
                    f"{record['question_id']} {record['answer_label']}",
                    file=sys.stderr,
                )
                errors.append({
                    "question_id": record["question_id"],
                    "paper_id": record["paper_id"],
                    "error": f"UPDATE matched {cursor.rowcount} rows",
                })
            else:
                updated += 1

    integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
    fk = con.execute("PRAGMA foreign_key_check").fetchall()
    print(
        f"database updated: {updated}/{len(records)} rows; "
        f"integrity={integrity}; foreign_key_check={'OK' if not fk else fk[:5]}"
    )

    report_path = write_report(con, papers, run, errors, str(report_path))
    con.close()
    print("report:", report_path)

    return 0 if integrity == "ok" and not fk and updated == len(records) else 1


if __name__ == "__main__":
    sys.exit(main())
