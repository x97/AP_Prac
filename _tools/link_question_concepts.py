#!/usr/bin/env python3
"""Concept-first MCQ linker.

This is the generic successor to link_question_kps.py for the concept layer.
It keeps the proven candidate/validation helpers from that script, but:

  * candidates are concept_clusters, not source knowledge_points;
  * each concept carries all member names, aliases and source definitions;
  * the model selects concepts (C01...);
  * results are written to question_concept_links;
  * question_kp_links is mirrored only for legacy compatibility;
  * question_keywords gains a concept_id column when available.
"""
import argparse
import collections
import json
import os
import re
import shutil
import sqlite3
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
EXAM_DB = os.path.join(ROOT, "data", "content", "psychology", "psychology_exam.db")
KNOW_DB = os.path.join(ROOT, "data", "content", "psychology", "psychology_knowledge.db")
EXPORT_DIR = os.path.join(ROOT, "data", "content", "psychology", "extraction")
REPORT_DIR = os.path.join(ROOT, "data", "content", "psychology", "reports", "question_analysis")
sys.path.insert(0, HERE)
import link_question_kps as linker  # noqa: E402

PROMPT_VERSION = "question-concept-link-v2"
_PATCH_LOCK = threading.Lock()

CONCEPT_SYSTEM_PROMPT = """You are an AP Psychology assessment analyst. You link a multiple-choice question to a controlled CONCEPT base and extract keywords.

Definitions:
- A keyword is a term or concept phrase that actually appears in the question text. Mentioning a term does not mean it is tested.
- A core concept is the concept a student must understand to choose the correct answer. Derive it from the correct answer. One core is normal; two at most.
- A supporting concept is optional and helps explain the answer.
- A confusable concept is a near-miss concept from a wrong option, not merely any concept mentioned there. It must be in the same narrow domain as the core (another research design, another correlation type, another stage, another ethics principle, etc.). If a wrong option is unrelated or only loosely related, omit it. Empty confusables is a valid answer.

Hard rules:
- Never make a term that appears only in a distractor the core concept.
- Use only the candidate keys shown (C01, C02, ...). Never invent a key or a concept.
- Core evidence must be a quote from the question stem, context, or correct option. The source explanation may help you understand the item, but do not quote it as core evidence.
- Keywords must appear verbatim in the question text (stem, context, or an option).
- Keywords should be concept terms or short concept phrases, not concrete examples or full option sentences.
- If no candidate fits, return status "no_match" with an empty core list. Do not force a match.
- Return only the JSON object, with no code fences or commentary.
"""


def now_iso():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def compact(value):
    return re.sub(r"\s+", " ", value or "").strip()


def concept_forms(concept, _aliases=None):
    return concept.get("forms") or []


def concept_domain(concept):
    return set(concept.get("domain_tokens") or [])


def same_concept_domain(a, b):
    return bool(concept_domain(a) & concept_domain(b))


def ensure_keyword_concept_column(know):
    columns = {row[1] for row in know.execute("PRAGMA table_info(question_keywords)")}
    if "concept_id" not in columns:
        know.execute("ALTER TABLE question_keywords ADD COLUMN concept_id TEXT")
    know.execute(
        "CREATE INDEX IF NOT EXISTS idx_qkw_concept ON question_keywords(concept_id)"
    )


def load_concepts(know):
    book_labels = {}
    for row in know.execute("SELECT book_id,title,year,edition FROM books"):
        book_id = row["book_id"]
        edition = row["edition"] or ""
        year = row["year"] or ""
        label_year = edition if re.fullmatch(r"(?:19|20)\d{2}", edition) else year
        if "barrons" in book_id:
            label = f"Barron {label_year}".strip()
        elif "myers" in book_id:
            label = f"Myers {label_year}".strip()
        else:
            label = (row["title"] or book_id)[:28]
        book_labels[book_id] = label
    rows = know.execute(
        """
        SELECT c.cluster_id, c.canonical_name, c.canonical_kp_id,
               c.ap_unit, c.topic, c.weight, c.weight_tier, c.member_count,
               m.kp_id, k.name AS kp_name, k.plain_en, k.definition_quote,
               k.section_id, s.path AS section_path, s.heading AS section_heading,
               k.book_id, k.weight AS kp_weight
        FROM concept_clusters c
        JOIN concept_members m ON m.cluster_id=c.cluster_id
        JOIN knowledge_points k ON k.kp_id=m.kp_id
        JOIN sections s ON s.section_id=k.section_id
        ORDER BY c.weight DESC, c.canonical_name, k.book_id
        """
    ).fetchall()
    aliases_by_concept = collections.defaultdict(list)
    for row in know.execute(
        """
        SELECT m.cluster_id, a.alias, a.match_mode
        FROM concept_members m
        JOIN kp_aliases a ON a.kp_id=m.kp_id
        """
    ):
        aliases_by_concept[row["cluster_id"]].append({
            "alias": row["alias"],
            "match_mode": row["match_mode"] or "insensitive",
        })

    grouped = collections.OrderedDict()
    for row in rows:
        grouped.setdefault(row["cluster_id"], []).append(dict(row))

    concepts = []
    aliases = {}
    meta = {}
    for concept_id, members in grouped.items():
        first = members[0]
        canonical = next(
            (m for m in members if m["kp_id"] == first["canonical_kp_id"]),
            None,
        )
        primary = canonical or max(members, key=lambda m: (m["kp_weight"] or 0))
        paths = []
        headings = []
        for member in members:
            path = member["section_path"] or ""
            if path and path not in paths:
                paths.append(path)
            heading = member["section_heading"] or ""
            if heading and heading not in headings:
                headings.append(heading)

        forms = []
        seen_forms = set()

        def add_form(surface, source):
            surface = compact(surface)
            normalized = linker.norm(surface)
            if not normalized or normalized in seen_forms:
                return
            # Allow short acronyms / symbols; skip 1-character noise.
            if len(normalized) < 2:
                return
            if len(normalized) < 3 and not (
                surface.isupper() or surface.isdigit() or source == "canonical"
            ):
                return
            seen_forms.add(normalized)
            forms.append((surface, surface.isupper(), source))

        add_form(first["canonical_name"], "canonical")
        for member in members:
            add_form(member["kp_name"], "member")
        for alias in aliases_by_concept.get(concept_id, []):
            add_form(alias["alias"], "alias")

        plain_parts = []
        definition_parts = []
        for member in members:
            if member["plain_en"] and member["plain_en"] not in plain_parts:
                plain_parts.append(member["plain_en"])
            if member["definition_quote"] and member["definition_quote"] not in definition_parts:
                definition_parts.append(member["definition_quote"])
        plain = " / ".join(plain_parts[:2])
        definition = " ".join(definition_parts[:2])
        source_labels = []
        for member in members:
            label = book_labels.get(member["book_id"], member["book_id"])
            if label not in source_labels:
                source_labels.append(label)

        domain_tokens = set()
        for path in paths:
            domain_tokens |= linker.domain_tokens(path)

        pseudo = {
            "kp_id": concept_id,  # pseudo key; maps 1:1 to concept_id
            "concept_id": concept_id,
            "name": first["canonical_name"],
            "plain_en": plain,
            "definition_quote": definition,
            "section_heading": primary["section_heading"] or first["topic"] or "",
            "section_path": " | ".join(paths),
            "primary_path": primary["section_path"] or "",
            "topic": first["topic"] or "",
            "ap_unit": first["ap_unit"],
            "weight": first["weight"] or 0,
            "weight_tier": first["weight_tier"] or "",
            "member_count": first["member_count"] or len(members),
            "canonical_kp_id": first["canonical_kp_id"],
            "member_kp_ids": [m["kp_id"] for m in members],
            "book_labels": source_labels,
            "forms": forms,
            "domain_tokens": domain_tokens,
        }
        concepts.append(pseudo)
        meta[concept_id] = pseudo
        aliases[concept_id] = [
            {"alias": surface, "match_mode": "case_sensitive" if cs else "insensitive"}
            for surface, cs, _source in forms
        ]

    return concepts, aliases, meta


def concept_candidate_prompt_lines(candidates, scope_kind):
    lines = []
    for item in candidates:
        concept = item["kp"]
        labels = "/".join(concept.get("book_labels") or [])
        tier = concept.get("weight_tier") or ""
        weight = concept.get("weight") or 0
        heading = linker.section_label(
            concept.get("primary_path") or concept.get("section_path"),
            item.get("in_scope"), scope_kind,
        )
        meta = f"{weight:.1f} {tier}".strip()
        source = f" [{labels}]" if labels else ""
        definition = compact(concept.get("definition_quote") or "")
        if len(definition) > 160:
            definition = definition[:157] + "..."
        lines.append(
            f"[{item['key']}] {concept['name']} ({meta}){source} — "
            f"{concept.get('plain_en') or ''} — {heading}"
            + (f" — def: {definition}" if definition else "")
        )
    return "\n".join(lines)


def build_concept_prompt(question, candidates, scope_kind):
    options = "\n".join(
        f"{opt['label']}. {compact(opt['content'])}"
        for opt in question["options"]
    )
    parts = [
        f"Question ID: {question['question_id']}",
        f"Question: {compact(question['stem'])}",
    ]
    if compact(question.get("context")):
        parts.append(f"Context: {compact(question['context'])}")
    parts += [
        "Options:",
        options,
        f"Correct answer: {question['correct_label']}. "
        f"{compact(question['correct_content'])}",
    ]
    if compact(question.get("explanation")):
        parts.append(
            "Source explanation (context only; do not use it as core evidence "
            f"or as a source of keywords):\n{compact(question['explanation'])}"
        )
    parts += [
        "",
        "Candidate concepts:",
        concept_candidate_prompt_lines(candidates, scope_kind),
        "",
        "Return exactly this JSON shape:",
        json.dumps({
            "status": "linked",
            "core": [{"concept": "C01", "confidence": 0.95,
                      "evidence": "exact quote from stem, context or correct option"}],
            "supporting": [{"concept": "C02", "confidence": 0.8, "evidence": ""}],
            "confusables": [{"concept": "C03", "option_label": "B",
                             "reason": "why this distractor is tempting"}],
            "keywords": [{
                "surface": "exact text from the question",
                "concept": "C01",
                "role": "core",
                "location": "stem",
                "option_label": None,
            }],
            "notes": "",
        }, ensure_ascii=False, indent=2),
        "status must be linked, needs_review or no_match.",
        "core must have 1-2 items when status is linked, and must be empty for no_match.",
        "keywords location is stem, context, correct_option or option; "
        "when location is option, option_label is required.",
        "A keyword may have concept=null when it is a real question term not in the candidate list.",
    ]
    return "\n".join(parts)


def concept_candidate_set(question, concepts, aliases, scope, scope_kind,
                          bm25_docs, bm25_idf):
    # Reuse the KP linker's candidate scoring, but monkeypatch the concept
    # surface forms and domain comparator for this call.
    with _PATCH_LOCK:
        old_forms, old_domain = linker.kp_forms, linker.same_domain
        linker.kp_forms = concept_forms
        linker.same_domain = same_concept_domain
        try:
            candidates = linker.candidate_set(
                question, concepts, aliases, scope, scope_kind, bm25_docs, bm25_idf
            )
        finally:
            linker.kp_forms, linker.same_domain = old_forms, old_domain

    for item in candidates:
        concept = item["kp"]
        item["score"] += (concept.get("weight") or 0) / 50.0
        if concept.get("weight_tier") == "core":
            item["score"] += 0.5
    candidates.sort(key=lambda item: (item["score"], item["kp"]["name"]), reverse=True)
    candidates = candidates[:80]
    for index, item in enumerate(candidates, 1):
        item["key"] = f"C{index:02d}"
    return candidates


def normalize_model_json(data):
    """Accept concept keys from the concept prompt; validation expects kp."""
    if not isinstance(data, dict):
        return data
    for key in ("core", "supporting", "confusables", "keywords"):
        for item in data.get(key) or []:
            if isinstance(item, dict) and "concept" in item and "kp" not in item:
                item["kp"] = item["concept"]
    return data


def link_one(question, concepts, aliases, scope, scope_kind,
             bm25_docs, bm25_idf, model, max_tokens, timeout, retries):
    candidates = concept_candidate_set(
        question, concepts, aliases, scope, scope_kind, bm25_docs, bm25_idf
    )
    prompt = build_concept_prompt(question, candidates, scope_kind)
    text, usage = linker.call_api(
        CONCEPT_SYSTEM_PROMPT, prompt, model, max_tokens, timeout, retries
    )
    data = normalize_model_json(linker.parse_json(text))
    with _PATCH_LOCK:
        old_forms, old_domain = linker.kp_forms, linker.same_domain
        linker.kp_forms, linker.same_domain = concept_forms, same_concept_domain
        try:
            result = linker.validate_result(question, data, candidates)
        finally:
            linker.kp_forms, linker.same_domain = old_forms, old_domain
    result["candidates"] = candidates
    result["prompt"] = prompt
    result["usage"] = usage
    result["raw_response"] = text
    return result


def write_export(path, paper_id, run, items, errors):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump({
            "generated_at": run["generated_at"],
            "paper_id": paper_id,
            "model": run["model"],
            "prompt_version": PROMPT_VERSION,
            "count": len(items),
            "items": items,
            "errors": errors,
        }, handle, ensure_ascii=False, indent=2)
    return path


def write_report(path, paper_id, run, items, errors):
    lines = [
        "# 题目概念关联报告（概念层）",
        "",
        f"- 生成时间：{run['generated_at']}",
        f"- 试卷：`{paper_id}`",
        f"- 模型：`{run['model']}`",
        f"- Prompt：`{PROMPT_VERSION}`",
        f"- 题目：{len(items)}；失败：{len(errors)}",
        "",
        "> 核心概念按“正确选项倒推”生成；干扰项只进入 confusable。",
        "> 写库目标：`question_concept_links`；`question_kp_links` 仅作 legacy 兼容。",
        "",
        "| 题号 | 状态 | 核心概念 | 辅助 | 易混淆 | 关键字 | 备注 |",
        "|---:|---|---|---|---|---|---|",
    ]
    counts = {"linked": 0, "needs_review": 0, "no_match": 0}
    for item in sorted(items, key=lambda x: x["number"]):
        counts[item["status"]] = counts.get(item["status"], 0) + 1
        core = "、".join(
            f"{e['name']}（{e.get('weight', 0):.1f}）" for e in item["core"]
        ) or "—"
        supporting = "、".join(e["name"] for e in item["supporting"]) or "—"
        confusable = "、".join(
            f"{e['name']}（{e.get('option_label')}）"
            for e in item["confusables"]
        ) or "—"
        keywords = "、".join(
            f"{kw['surface']}" + ("" if (kw.get("concept_id") or kw.get("kp_id")) else "（未收录）")
            for kw in item["keywords"]
        ) or "—"
        lines.append(
            f"| {item['number']} | {item['status']} | {core} | {supporting} | "
            f"{confusable} | {keywords} | {item.get('notes') or '—'} |"
        )
    lines += [
        "",
        "## 覆盖",
        "",
        f"- linked：{counts.get('linked', 0)}",
        f"- needs_review：{counts.get('needs_review', 0)}",
        f"- no_match：{counts.get('no_match', 0)}",
    ]
    checks = []
    for item in sorted(items, key=lambda x: x["number"]):
        for warning in item.get("warnings") or []:
            checks.append(f"- Q{item['number']}（{item['question_id']}）：{warning}")
        for error in item.get("errors") or []:
            checks.append(f"- Q{item['number']}（{item['question_id']}）：校验错误：{error}")
    if checks:
        lines += ["", "## 校验记录", ""] + checks
    if errors:
        lines += ["", "## 失败清单", ""]
        for error in errors:
            lines.append(f"- `{error.get('question_id', '?')}`：{error.get('error')}")
    lines += [
        "",
        "## 复跑命令",
        "",
        "```bash",
        f"python3 _tools/link_question_concepts.py --paper {paper_id} --force",
        "```",
        "",
    ]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
    return path


def ensure_tables(know):
    names = {
        row[0] for row in know.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    required = {"question_analysis", "question_concept_links", "question_keywords"}
    missing = required - names
    if missing:
        raise SystemExit(
            "missing tables: " + ", ".join(sorted(missing))
            + "; run _tools/migrate_question_analysis.py first"
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper", required=True)
    parser.add_argument("--exam-db", default=EXAM_DB)
    parser.add_argument("--know-db", default=KNOW_DB)
    parser.add_argument("--chapter", help="chapter filter, e.g. 'Chapter 11'")
    parser.add_argument("--scope", help="explicit scope string, e.g. 'Unit 1'")
    parser.add_argument("--scope-kind", choices=["chapter", "unit"])
    parser.add_argument("--question-id", action="append", default=[],
                        help="link only this question_id (repeatable)")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--force", action="store_true",
                        help="relink questions that already have concept links")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--model", default=linker.DEFAULT_MODEL)
    parser.add_argument("--max-tokens", type=int, default=8000)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--out-json", default=None)
    parser.add_argument("--report", default=None)
    parser.add_argument("--no-backup", action="store_true")
    parser.add_argument("--no-kp-links", action="store_true",
                        help="do not mirror results into question_kp_links")
    args = parser.parse_args()

    exam = sqlite3.connect(args.exam_db)
    exam.row_factory = sqlite3.Row
    know = sqlite3.connect(args.know_db)
    know.row_factory = sqlite3.Row
    ensure_tables(know)

    questions = linker.load_questions(exam, args.paper)
    if args.question_id:
        wanted = set(args.question_id)
        questions = [q for q in questions if q["question_id"] in wanted]

    qids = [q["question_id"] for q in questions]
    if qids and not args.force:
        marks = ",".join("?" for _ in qids)
        existing = {
            row[0] for row in know.execute(
                f"SELECT DISTINCT question_id FROM question_concept_links "
                f"WHERE question_id IN ({marks}) AND relation_type='core'",
                qids,
            )
        }
        questions = [q for q in questions if q["question_id"] not in existing]

    if args.limit is not None:
        questions = questions[:args.limit]
    if not questions:
        print("nothing to link (all selected questions already have core concepts)")
        exam.close()
        know.close()
        return 0

    concepts, aliases, meta = load_concepts(know)
    bm25_docs, bm25_idf = linker.build_bm25(concepts, aliases)
    if args.scope:
        scope = args.scope
        scope_kind = args.scope_kind or (
            "unit" if scope.lower().startswith("unit") else "chapter"
        )
    else:
        scope, scope_kind = linker.infer_scope(args.paper, args.chapter)
    print(
        f"{args.paper}: {len(questions)} questions; {len(concepts)} concepts; "
        f"scope={scope or '—'} ({scope_kind or 'all'})"
    )

    if args.dry_run:
        for q in questions:
            candidates = concept_candidate_set(
                q, concepts, aliases, scope, scope_kind, bm25_docs, bm25_idf
            )
            print("\n" + "=" * 78)
            print(f"Q{q['number']} {q['question_id']} candidates={len(candidates)}")
            print(concept_candidate_prompt_lines(candidates, scope_kind))
        exam.close()
        know.close()
        return 0

    started = time.time()
    results, errors = {}, []
    usage_total = {"input_tokens": 0, "output_tokens": 0}

    def work(q):
        return q, link_one(
            q, concepts, aliases, scope, scope_kind, bm25_docs, bm25_idf,
            args.model, args.max_tokens, args.timeout, args.retries,
        )

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(work, q): q for q in questions}
        done = 0
        for future in as_completed(futures):
            q = futures[future]
            done += 1
            try:
                _, result = future.result()
                results[q["question_id"]] = result
                for key in usage_total:
                    usage_total[key] += int(result["usage"].get(key) or 0)
                print(
                    f"[{done}/{len(questions)}] Q{q['number']} "
                    f"{result['status']} core={len(result['core'])} "
                    f"kw={len(result['keywords'])}",
                    flush=True,
                )
            except Exception as error:
                errors.append({"question_id": q["question_id"], "error": str(error)})
                print(f"[{done}/{len(questions)}] Q{q['number']} ERROR {error}", flush=True)

    items = []
    for q in questions:
        result = results.get(q["question_id"])
        if not result:
            continue
        item = {
            "question_id": q["question_id"],
            "number": q["number"],
            "status": result["status"],
            "core": [
                {
                    "concept_id": e["kp_id"],
                    "name": e["kp_name"],
                    "weight": meta[e["kp_id"]]["weight"],
                    "weight_tier": meta[e["kp_id"]]["weight_tier"],
                    "confidence": e.get("confidence"),
                    "evidence": e.get("evidence", ""),
                    "evidence_source": e.get("evidence_source", "question"),
                }
                for e in result["core"]
            ],
            "supporting": [
                {
                    "concept_id": e["kp_id"],
                    "name": e["kp_name"],
                    "weight": meta[e["kp_id"]]["weight"],
                    "weight_tier": meta[e["kp_id"]]["weight_tier"],
                    "confidence": e.get("confidence"),
                    "evidence": e.get("evidence", ""),
                }
                for e in result["supporting"]
            ],
            "confusables": [
                {
                    "concept_id": e["kp_id"],
                    "name": e["kp_name"],
                    "weight": meta[e["kp_id"]]["weight"],
                    "weight_tier": meta[e["kp_id"]]["weight_tier"],
                    "option_label": e.get("option_label"),
                    "reason": e.get("reason", ""),
                }
                for e in result["confusables"]
            ],
            "keywords": result["keywords"],
            "notes": result["notes"],
            "warnings": result["warnings"],
            "errors": result["errors"],
        }
        items.append(item)

    run = {
        "generated_at": now_iso(),
        "model": args.model,
        "usage": usage_total,
    }
    custom_db = os.path.abspath(args.know_db) != os.path.abspath(KNOW_DB)
    if args.out_json:
        out_json = args.out_json
    elif custom_db:
        out_json = os.path.join(
            os.path.dirname(os.path.abspath(args.know_db)),
            f"question_concept_links_{args.paper}.json",
        )
    else:
        out_json = os.path.join(
            EXPORT_DIR, f"question_concept_links_{args.paper}.json"
        )
    if args.report:
        report_path = args.report
    elif custom_db:
        report_path = os.path.join(
            os.path.dirname(os.path.abspath(args.know_db)),
            f"{args.paper}_concepts.md",
        )
    else:
        report_path = os.path.join(
            REPORT_DIR, f"{args.paper}_concepts.md"
        )
    export_path = write_export(out_json, args.paper, run, items, errors)
    print(
        f"linked {len(items)} questions; failures={len(errors)}; "
        f"tokens={usage_total['input_tokens']}/{usage_total['output_tokens']}; "
        f"{time.time() - started:.1f}s"
    )
    print("export:", export_path)

    if not items:
        exam.close()
        know.close()
        return 1 if errors else 0

    if not args.no_backup:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = args.know_db + f".bak-{stamp}-question-concept-link"
        shutil.copy2(KNOW_DB, backup)
        print("backup:", backup)

    ensure_keyword_concept_column(know)
    processed_qids = [q["question_id"] for q in questions]
    marks = ",".join("?" for _ in processed_qids)
    with know:
        know.execute(f"DELETE FROM question_concept_links WHERE question_id IN ({marks})",
                     processed_qids)
        know.execute(f"DELETE FROM question_keywords WHERE question_id IN ({marks})",
                     processed_qids)
        know.execute(f"DELETE FROM question_analysis WHERE question_id IN ({marks})",
                     processed_qids)
        if not args.no_kp_links:
            know.execute(f"DELETE FROM question_kp_links WHERE question_id IN ({marks})",
                         processed_qids)

        for item in items:
            know.execute(
                "INSERT INTO question_analysis"
                "(question_id, paper_id, status, model, prompt_version, notes, updated_at) "
                "VALUES (?,?,?,?,?,?,?)",
                (item["question_id"], args.paper, item["status"], args.model,
                 PROMPT_VERSION, item["notes"] or None, run["generated_at"]),
            )
            for relation, key in (("core", "core"), ("supporting", "supporting"),
                                  ("confusable", "confusables")):
                for entry in item[key]:
                    concept_id = entry["concept_id"]
                    canonical_kp_id = meta[concept_id].get("canonical_kp_id")
                    know.execute(
                        "INSERT OR IGNORE INTO question_concept_links"
                        "(question_id,concept_id,relation_type,option_label,confidence,"
                        " evidence,rationale,created_at) VALUES (?,?,?,?,?,?,?,?)",
                        (item["question_id"], concept_id, relation,
                         entry.get("option_label"), entry.get("confidence"),
                         entry.get("evidence"), entry.get("reason"),
                         run["generated_at"]),
                    )
                    if not args.no_kp_links and canonical_kp_id:
                        know.execute(
                            "INSERT OR IGNORE INTO question_kp_links"
                            "(question_id,kp_id,relation_type,option_label,confidence,"
                            " evidence,rationale,created_at) VALUES (?,?,?,?,?,?,?,?)",
                            (item["question_id"], canonical_kp_id, relation,
                             entry.get("option_label"), entry.get("confidence"),
                             entry.get("evidence"), entry.get("reason"),
                             run["generated_at"]),
                        )
            for kw in item["keywords"]:
                concept_id = kw.get("kp_id")
                canonical_kp_id = meta.get(concept_id, {}).get("canonical_kp_id")
                know.execute(
                    "INSERT OR IGNORE INTO question_keywords"
                    "(question_id,surface,normalized,kp_id,concept_id,role,location,"
                    " option_label,confidence,created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (item["question_id"], kw["surface"], kw["normalized"],
                     canonical_kp_id, concept_id, kw.get("role") or "mentioned",
                     kw.get("location") or "stem", kw.get("option_label"),
                     kw.get("confidence"), run["generated_at"]),
                )

    integrity = know.execute("PRAGMA integrity_check").fetchone()[0]
    fk = know.execute("PRAGMA foreign_key_check").fetchall()
    print("integrity_check:", integrity, "foreign_key_check:", "OK" if not fk else fk[:3])

    report_path = write_report(report_path, args.paper, run, items, errors)
    print("report:", report_path)
    exam.close()
    know.close()
    return 0 if integrity == "ok" and not fk and not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
