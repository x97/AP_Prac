#!/usr/bin/env python3
"""Link MCQ questions to knowledge points, keywords and confusables.

Pilot target: one Barron chapter (default Ch11).  The script:

  1. loads questions from psychology_exam.db and KPs/aliases from psychology_knowledge.db;
  2. retrieves a candidate set (all KPs in the paper's chapter plus
     lexical/alias matches from other chapters);
  3. asks the model to choose 1-2 core KPs from the correct answer,
     optional supporting KPs, distractor confusables, and keywords;
  4. validates every returned candidate/key/evidence;
  5. writes question_analysis / question_kp_links / question_keywords.

The exam DB stays exam-only; question ids in psychology_knowledge.db are logical
references and there is no cross-database foreign key.

Usage:
    python3 _tools/link_question_kps.py --paper psychology-barrons-2027-ch11-review --dry-run --limit 3
    python3 _tools/link_question_kps.py --paper psychology-barrons-2027-ch11-review
    python3 _tools/link_question_kps.py --paper psychology-barrons-2027-ch11-review --force
"""
import argparse
import http.client
import json
import math
import os
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
EXAM_DB = os.path.join(ROOT, "data", "content", "psychology", "psychology_exam.db")
KNOW_DB = os.path.join(ROOT, "data", "content", "psychology", "psychology_knowledge.db")
EXPORT_DIR = os.path.join(ROOT, "data", "content", "psychology", "extraction")
DEFAULT_REPORT = os.path.join(ROOT, "data", "content", "psychology", "reports", "question_analysis", "question_analysis_report.md")

DEFAULT_API_BASE = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
DEFAULT_MODEL = os.environ.get(
    "ANTHROPIC_MODEL", os.environ.get("CLAUDE_MODEL", "claude-sonnet-5-5")
)
API_KEY = os.environ.get("ANTHROPIC_AUTH_TOKEN") or os.environ.get("ANTHROPIC_API_KEY")
PROMPT_VERSION = "question-kp-link-v1"

SYSTEM_PROMPT = """You are an AP Psychology assessment analyst. You link a multiple-choice question to a controlled knowledge base and extract keywords.

Definitions:
- A keyword is a term or concept phrase that actually appears in the question text. Mentioning a term does not mean it is tested.
- A core knowledge point is the concept a student must understand to choose the correct answer. Derive it from the correct answer. One core is normal; two at most.
- A supporting knowledge point is optional and helps explain the answer.
- A confusable concept is a near-miss concept from a wrong option, not merely any concept mentioned there. It must be in the same narrow domain as the core (another research design, another correlation type, another stage, another ethics principle, etc.). If a wrong option is unrelated or only loosely related, omit it. Empty confusables is a valid answer.

Hard rules:
- Never make a term that appears only in a distractor the core knowledge point.
- Use only the candidate keys shown (C01, C02, ...). Never invent a key or a knowledge point.
- Core evidence must be a quote from the question stem, context, or correct option. The source explanation may help you understand the item, but do not quote it as core evidence.
- Keywords must appear verbatim in the question text (stem, context, or an option). Do not turn explanation-only terms into keywords.
- Keywords should be concept terms or short concept phrases, not concrete examples or full option sentences. If a phrase describes an example, omit it or use role "mentioned".
- Distractor keywords belong in confusables and/or keywords with role "distractor" and the wrong option letter.
- If no candidate fits, return status "no_match" with an empty core list. Do not force a match.
- Return only the JSON object, with no code fences or commentary.
"""

CANDIDATE_WEIGHTS = {
    "correct_option": 12.0,
    "stem": 8.0,
    "context": 5.0,
    "explanation": 6.0,
    "option": 1.5,
}


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def norm(value):
    value = (value or "").lower().replace("’", "'").replace("‘", "'")
    value = re.sub(r"[^a-z0-9' ]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def compact(value):
    return re.sub(r"\s+", " ", value or "").strip()


def contains(text, surface, case_sensitive=False):
    if not text or not surface:
        return False
    flags = 0 if case_sensitive else re.I
    pattern = r"(?<![A-Za-z0-9])" + re.escape(surface) + r"(?![A-Za-z0-9])"
    return re.search(pattern, text, flags) is not None


def infer_scope(paper_id, explicit=None):
    """Infer the chapter/unit filter from the paper id."""
    if explicit:
        kind = "unit" if explicit.lower().startswith("unit") else "chapter"
        return explicit, kind
    match = re.search(r"-ch(\d+)-", paper_id)
    if match:
        return f"Chapter {match.group(1)}", "chapter"
    match = re.search(r"-u(\d+)$", paper_id)
    if match:
        return f"Unit {match.group(1)}", "unit"
    return None, None


DOMAIN_STOP = {
    "unit", "chapter", "psychology", "overview", "development",
    "developmental", "and", "the", "of", "in", "to", "a",
}


def domain_tokens(path):
    # Use chapter + subheading only. The unit name is too broad (for example
    # "Social Psychology, Personality, Motivation, and Emotion") and makes
    # unrelated KPs look like same-domain confusables.
    parts = [part.strip() for part in (path or "").split(">") if part.strip()]
    text = " > ".join(parts[-2:])
    text = re.sub(r"[^a-z0-9 ]+", " ", text.lower())
    return set(text.split()) - DOMAIN_STOP


def same_domain(kp_a, kp_b):
    """Heuristic: two KPs share a subheading/domain token."""
    return bool(
        domain_tokens(kp_a["section_path"]) & domain_tokens(kp_b["section_path"])
    )


def section_label(path, in_scope=False, scope_kind=None):
    parts = [part.strip() for part in (path or "").split(">") if part.strip()]
    if not parts:
        return ""
    if in_scope and scope_kind == "chapter" and parts[-1].lower() not in ("overview", "summary"):
        return parts[-1]
    if len(parts) >= 2:
        return " > ".join(parts[-2:])
    return parts[-1]


def load_questions(con, paper_id):
    rows = con.execute(
        """
        SELECT q.question_id, q.paper_id, q.number, q.stem, q.context,
               q.correct_answer, q.answer_text,
               o.content AS correct_content, o.explanation
        FROM questions q
        JOIN options o ON o.question_id=q.question_id AND o.label=q.correct_answer
        WHERE q.paper_id=? AND q.section='MCQ'
          AND q.correct_answer IS NOT NULL AND TRIM(q.correct_answer)<>''
        ORDER BY q.number
        """,
        (paper_id,),
    ).fetchall()
    if not rows:
        raise SystemExit(f"no MCQ questions with answers for {paper_id}")

    qids = [row["question_id"] for row in rows]
    marks = ",".join("?" for _ in qids)
    options = {}
    for row in con.execute(
        f"SELECT question_id,label,content,sort_order,is_correct,explanation "
        f"FROM options WHERE question_id IN ({marks}) ORDER BY sort_order",
        qids,
    ):
        options.setdefault(row["question_id"], []).append(dict(row))

    questions = []
    for row in rows:
        item = dict(row)
        item["options"] = options.get(row["question_id"], [])
        item["correct_label"] = (row["correct_answer"] or "").strip().upper()
        questions.append(item)
    return questions


def load_knowledge(con):
    kps = [
        dict(row) for row in con.execute(
            """
            SELECT k.kp_id, k.name, k.name_normalized, k.plain_en,
                   k.definition_quote, k.section_id,
                   s.path AS section_path, s.heading AS section_heading
            FROM knowledge_points k
            JOIN sections s ON s.section_id=k.section_id
            WHERE k.status='approved'
            ORDER BY k.name
            """
        )
    ]
    aliases = {}
    for row in con.execute(
        "SELECT kp_id, alias, alias_normalized, match_mode FROM kp_aliases"
    ):
        aliases.setdefault(row["kp_id"], []).append(dict(row))
    return kps, aliases


def kp_forms(kp, aliases):
    forms = []
    seen = set()

    def add(surface, case_sensitive, source):
        normalized = norm(surface)
        if len(normalized) < 3 or normalized in seen:
            return
        seen.add(normalized)
        forms.append((surface, case_sensitive, source))

    add(kp["name"], False, "name")
    for alias in aliases.get(kp["kp_id"], []):
        add(
            alias["alias"],
            alias["match_mode"] == "case_sensitive",
            "alias",
        )
    return forms


STOPWORDS = {
    "the", "a", "an", "of", "in", "to", "and", "or", "is", "are", "was",
    "were", "be", "been", "being", "that", "this", "these", "those", "for",
    "with", "on", "at", "by", "from", "as", "it", "its", "their", "his",
    "her", "he", "she", "they", "we", "you", "i", "not", "no", "if", "then",
    "than", "which", "who", "whom", "whose", "what", "when", "where", "why",
    "how", "can", "could", "should", "would", "may", "might", "will", "do",
    "does", "did", "have", "has", "had", "more", "most", "less", "least",
    "such", "also", "into", "about", "over", "under", "between", "during",
    "after", "before", "while", "because", "but", "so", "only", "very",
    "much", "many", "some", "any", "all", "both", "each", "other", "another",
    "same", "different", "first", "second", "third", "using", "used", "use",
}


def stem_token(token):
    token = token.lower()
    for suffix in ("ically", "ism", "ing", "edly", "ed", "es", "s"):
        if len(token) > len(suffix) + 3 and token.endswith(suffix):
            return token[:-len(suffix)]
    return token


def tokenize(text):
    tokens = re.findall(r"[a-z0-9']+", (text or "").lower())
    return [
        stem_token(token) for token in tokens
        if len(token) >= 2 and token not in STOPWORDS
    ]


def build_bm25(kps, aliases):
    """Local BM25 index over KP name, aliases, plain definition and section."""
    docs = []
    df = Counter()
    for kp in kps:
        alias_text = " ".join(
            alias["alias"] for alias in aliases.get(kp["kp_id"], [])
        )
        text = " ".join([
            kp.get("name") or "", kp.get("name") or "",
            alias_text, alias_text,
            kp.get("plain_en") or "", kp.get("plain_en") or "",
            kp.get("definition_quote") or "",
            kp.get("section_heading") or "",
            kp.get("section_path") or "",
        ])
        tf = Counter(tokenize(text))
        docs.append(tf)
        for token in tf:
            df[token] += 1
    total = max(len(kps), 1)
    idf = {
        token: math.log((total + 1) / (count + 1)) + 1.0
        for token, count in df.items()
    }
    return docs, idf


def bm25_score(query_tokens, tf, idf):
    score = 0.0
    for token in set(query_tokens):
        count = tf.get(token)
        if count:
            score += idf.get(token, 1.0) * (count / (count + 1.2))
    return score


def candidate_set(question, kps, aliases, scope, scope_kind, bm25_docs, bm25_idf):
    texts = {
        "stem": question.get("stem") or "",
        "context": question.get("context") or "",
        "correct_option": question.get("correct_content") or "",
        "explanation": question.get("explanation") or "",
        "option": " ".join(
            (opt.get("content") or "") for opt in question.get("options", [])
        ),
    }
    query_text = " ".join([
        texts["stem"], texts["stem"],
        texts["context"],
        texts["correct_option"], texts["correct_option"], texts["correct_option"],
        texts["explanation"], texts["explanation"],
        texts["option"],
    ])
    query_tokens = tokenize(query_text)
    scored = []
    for index, kp in enumerate(kps):
        in_scope = bool(scope and scope.lower() in (kp["section_path"] or "").lower())
        score = 0.0
        fields = set()
        matched_surfaces = []
        for surface, case_sensitive, source in kp_forms(kp, aliases):
            for field, text in texts.items():
                if not text:
                    continue
                if contains(text, surface, case_sensitive):
                    score += CANDIDATE_WEIGHTS[field] * (
                        1 + min(len(norm(surface)), 50) / 50
                    )
                    fields.add(field)
                    matched_surfaces.append(surface)
                    break  # one field is enough for this surface
        bm25 = bm25_score(query_tokens, bm25_docs[index], bm25_idf)
        score += bm25
        if in_scope:
            score += 3.0
        if score > 0 or in_scope:
            scored.append({
                "kp": kp,
                "score": score,
                "bm25": bm25,
                "fields": fields,
                "surfaces": matched_surfaces[:4],
                "forms": kp_forms(kp, aliases),
                "in_scope": in_scope,
            })

    scope_items = [item for item in scored if item["in_scope"]]
    other_items = sorted(
        (item for item in scored if not item["in_scope"]),
        key=lambda item: item["score"],
        reverse=True,
    )

    if scope_kind == "chapter":
        candidates = scope_items + other_items[:25]
    elif scope_kind == "unit":
        # Unit pools can exceed 170 KPs. Keep the three most relevant
        # subheadings in full, then the strongest remaining unit KPs.
        by_heading = {}
        for item in scope_items:
            heading = item["kp"].get("section_heading") or ""
            by_heading.setdefault(heading, []).append(item)
        ranked_headings = sorted(
            by_heading.values(),
            key=lambda items: max(
                (item["score"] - 3.0) for item in items
            ),
            reverse=True,
        )[:3]
        selected, seen = [], set()
        for heading_items in ranked_headings:
            for item in sorted(
                heading_items, key=lambda x: x["score"], reverse=True
            ):
                if item["kp"]["kp_id"] not in seen:
                    selected.append(item)
                    seen.add(item["kp"]["kp_id"])
        for item in sorted(scope_items, key=lambda x: x["score"], reverse=True):
            if len(selected) >= 90:
                break
            if item["kp"]["kp_id"] not in seen:
                selected.append(item)
                seen.add(item["kp"]["kp_id"])
        candidates = selected[:90] + other_items[:20]
    else:
        candidates = other_items[:60]

    candidates.sort(key=lambda item: (item["score"], item["kp"]["name"]), reverse=True)
    for index, item in enumerate(candidates, 1):
        item["key"] = f"C{index:02d}"
    return candidates


def candidate_prompt_lines(candidates, scope_kind):
    lines = []
    for item in candidates:
        kp = item["kp"]
        lines.append(
            f"[{item['key']}] {kp['name']} — {kp['plain_en'] or ''} — "
            f"{section_label(kp['section_path'], item['in_scope'], scope_kind)}"
        )
    return "\n".join(lines)


def build_prompt(question, candidates, scope_kind):
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
        "Candidate knowledge points:",
        candidate_prompt_lines(candidates, scope_kind),
        "",
        "Return exactly this JSON shape:",
        json.dumps({
            "status": "linked",
            "core": [{"kp": "C01", "confidence": 0.95,
                      "evidence": "exact quote from stem, context or correct option"}],
            "supporting": [{"kp": "C02", "confidence": 0.8, "evidence": ""}],
            "confusables": [{"kp": "C03", "option_label": "B",
                             "reason": "why this distractor is tempting"}],
            "keywords": [{
                "surface": "exact text from the question",
                "kp": "C01",
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
        "A keyword may have kp=null when it is a real question term not in the candidate list.",
    ]
    return "\n".join(parts)


def call_api(system, prompt, model, max_tokens, timeout, retries):
    if not API_KEY:
        raise RuntimeError(
            "missing API key: set ANTHROPIC_AUTH_TOKEN or ANTHROPIC_API_KEY"
        )
    base = (DEFAULT_API_BASE or "https://api.anthropic.com").rstrip("/")
    body = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": 0.1,
        "thinking": {"type": "disabled"},
        "system": system,
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
        request = urllib.request.Request(base + "/v1/messages", data=payload, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                data = json.load(response)
            text = "".join(
                block.get("text", "")
                for block in data.get("content", [])
                if block.get("type", "text") == "text"
            )
            return text, data.get("usage") or {}
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
        except (
            urllib.error.URLError,
            TimeoutError,
            OSError,
            http.client.HTTPException,
            json.JSONDecodeError,
        ) as error:
            last_error = RuntimeError(f"network/response error: {error}")
            if attempt < retries:
                time.sleep(2 ** attempt)
                continue
            raise last_error
    raise last_error or RuntimeError("API call failed")


def parse_json(text):
    raw = (text or "").strip()
    if not raw:
        raise ValueError("empty response")
    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.I)
    raw = re.sub(r"\s*```$", "", raw)
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end < start:
        raise ValueError("no JSON object in response")
    payload = raw[start:end + 1]
    # Models occasionally emit trailing commas before } or ], or forget
    # quotes around candidate keys such as "kp": C03.
    payload = re.sub(r",\s*([}\]])", r"\1", payload)
    payload = re.sub(r'("kp"\s*:\s*)(C\d+)\b', r'\1"\2"', payload)
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        # Some models wrap a long evidence/reason string with a literal
        # newline. Python can tolerate control characters inside strings
        # when strict=False, which is preferable to dropping the question.
        data = json.loads(payload, strict=False)
    for key in ("analysis", "result", "data"):
        if isinstance(data, dict) and isinstance(data.get(key), dict):
            data = data[key]
            break
    return data


def resolve_ref(ref, candidates):
    ref = str(ref or "").strip()
    if not ref:
        return None
    by_key = {item["key"].upper(): item for item in candidates}
    by_id = {item["kp"]["kp_id"]: item for item in candidates}
    if ref.upper() in by_key:
        return by_key[ref.upper()]
    if ref in by_id:
        return by_id[ref]
    # tolerate C1 vs C01
    match = re.fullmatch(r"C0*(\d+)", ref, re.I)
    if match:
        padded = f"C{int(match.group(1)):02d}"
        if padded in by_key:
            return by_key[padded]
    return None


def validate_result(question, data, candidates):
    errors = []
    warnings = []
    by_id = {item["kp"]["kp_id"]: item for item in candidates}
    wrong_labels = {
        opt["label"].upper()
        for opt in question["options"]
        if opt["label"].upper() != question["correct_label"]
    }
    option_map = {
        opt["label"].upper(): compact(opt["content"])
        for opt in question["options"]
    }

    status = str(data.get("status") or "linked").strip()
    if status not in ("linked", "needs_review", "no_match"):
        warnings.append(f"unknown status {status!r}; treated as needs_review")
        status = "needs_review"

    core, supporting, confusables, keywords = [], [], [], []

    def add_link(target, raw, kind):
        item = resolve_ref(raw.get("kp"), candidates) if isinstance(raw, dict) else None
        if item is None:
            errors.append(f"{kind}: unknown candidate {raw!r}")
            return
        entry = {
            "kp": item,
            "kp_id": item["kp"]["kp_id"],
            "kp_name": item["kp"]["name"],
            "confidence": raw.get("confidence"),
            "evidence": compact(raw.get("evidence") or ""),
        }
        if kind == "confusable":
            label = str(raw.get("option_label") or "").strip().upper()
            if label not in wrong_labels:
                errors.append(f"confusable: option {label!r} is not a wrong option")
                return
            option_text = option_map[label]
            term_in_option = any(
                contains(option_text, surface, case_sensitive)
                for surface, case_sensitive, _ in item["forms"]
            )
            domain_ok = any(
                same_domain(item["kp"], core_entry["kp"]["kp"])
                for core_entry in core
            )
            same_subheading = any(
                item["kp"].get("section_heading")
                == core_entry["kp"]["kp"].get("section_heading")
                for core_entry in core
            )
            short_option = len(option_text.split()) <= 4
            if not term_in_option and (short_option or not same_subheading):
                warnings.append(
                    f"confusable {item['kp']['name']!r} is not named in option "
                    f"{label!r} and is not in the core subheading; dropped"
                )
                return
            if term_in_option and not (domain_ok or same_subheading):
                warnings.append(
                    f"confusable {item['kp']['name']!r} is in option {label!r} "
                    "but not in the core's narrow domain; dropped"
                )
                return
            entry["option_label"] = label
            entry["reason"] = compact(raw.get("reason") or "")
        elif kind == "supporting":
            term_in_correct = any(
                contains(compact(question.get("correct_content")),
                         surface, case_sensitive)
                for surface, case_sensitive, _ in item["forms"]
            )
            same_subheading = any(
                item["kp"].get("section_heading")
                == core_entry["kp"]["kp"].get("section_heading")
                for core_entry in core
            )
            if not term_in_correct and not same_subheading:
                warnings.append(
                    f"supporting {item['kp']['name']!r} is not in the correct "
                    "option or the core subheading; dropped"
                )
                return
        target.append(entry)

    for raw in data.get("core") or []:
        add_link(core, raw, "core")
    for raw in data.get("supporting") or []:
        add_link(supporting, raw, "supporting")
    for raw in data.get("confusables") or []:
        add_link(confusables, raw, "confusable")

    # Deduplicate links by kp_id (+ option).
    def dedupe(entries):
        out, seen = [], set()
        for entry in entries:
            key = (entry["kp_id"], entry.get("option_label"))
            if key in seen:
                continue
            seen.add(key)
            out.append(entry)
        return out

    core, supporting, confusables = (
        dedupe(core), dedupe(supporting), dedupe(confusables)
    )

    # A concept cannot be both the core and a confusable for the same item.
    core_ids = {entry["kp_id"] for entry in core}
    kept_confusables = []
    for entry in confusables:
        if entry["kp_id"] in core_ids:
            warnings.append(
                f"confusable {entry['kp_name']!r} duplicates a core KP; dropped"
            )
        else:
            kept_confusables.append(entry)
    confusables = kept_confusables

    # A concept already shown as a confusable does not need a second
    # "supporting" card.
    confusable_ids = {entry["kp_id"] for entry in confusables}
    kept_supporting = []
    for entry in supporting:
        if entry["kp_id"] in confusable_ids:
            warnings.append(
                f"supporting {entry['kp_name']!r} duplicates a confusable; dropped"
            )
        else:
            kept_supporting.append(entry)
    supporting = kept_supporting

    if len(core) > 2:
        warnings.append(f"core had {len(core)} items; keeping first 2")
        core = core[:2]
    if status == "linked" and not core:
        warnings.append("linked status with no core; changed to needs_review")
        status = "needs_review"
    if status == "no_match" and core:
        warnings.append("no_match status with core; changed to needs_review")
        status = "needs_review"

    # Core evidence must exist in the item text; explanation is accepted
    # only as a warning source, because it can help with recall.
    stem = compact(question.get("stem"))
    context = compact(question.get("context"))
    correct = compact(question.get("correct_content"))
    explanation = compact(question.get("explanation"))
    for entry in core:
        evidence = entry["evidence"]
        if not evidence:
            warnings.append(f"core {entry['kp']['name']!r}: empty evidence")
            status = "needs_review"
            continue
        evidence_l = evidence.lower()
        in_question = any(
            evidence_l in compact(text).lower()
            for text in (stem, context, correct) if text
        )
        in_explanation = explanation and evidence_l in explanation.lower()
        if not in_question:
            entry["evidence_source"] = "explanation" if in_explanation else "unverified"
            warnings.append(
                f"core {entry['kp_name']!r}: evidence is not an exact quote "
                "from stem/context/correct option"
            )
            status = "needs_review"

    # A core that only matched a wrong option is a distractor, not a core.
    kept_core = []
    for entry in core:
        item = by_id.get(entry["kp_id"])
        if item and item["fields"] and item["fields"] <= {"option"}:
            warnings.append(
                f"core {entry['kp_name']!r}: only matches wrong options; dropped"
            )
        else:
            kept_core.append(entry)
    if len(kept_core) != len(core):
        core = kept_core
        if not core and status == "linked":
            status = "needs_review"

    # Keywords: exact question text only.
    for raw in data.get("keywords") or []:
        if not isinstance(raw, dict):
            continue
        surface = compact(raw.get("surface") or "")
        location = str(raw.get("location") or "stem").strip()
        label = str(raw.get("option_label") or "").strip().upper() or None
        role = str(raw.get("role") or "mentioned").strip()
        if role not in ("core", "supporting", "mentioned", "distractor"):
            role = "mentioned"
        if location not in ("stem", "context", "correct_option", "option"):
            errors.append(f"keyword {surface!r}: bad location {location!r}")
            continue
        if location == "option":
            if label not in option_map:
                errors.append(f"keyword {surface!r}: bad option label {label!r}")
                continue
            target_text = option_map[label]
        elif location == "stem":
            target_text = stem
        elif location == "context":
            target_text = context
        else:
            target_text = correct
        if not surface or not contains(target_text, surface, surface.isupper()):
            errors.append(f"keyword {surface!r}: not found in {location}")
            continue
        word_count = len(re.findall(r"[A-Za-z0-9']+", surface))
        if word_count > 8 or (
            location in ("option", "correct_option")
            and word_count > 4
            and norm(surface) == norm(target_text)
        ):
            warnings.append(
                f"keyword {surface!r}: whole/long option text; dropped"
            )
            continue
        kp_item = resolve_ref(raw.get("kp"), candidates) if raw.get("kp") else None
        if kp_item is not None:
            alias_forms = {norm(surface) for surface, _, _ in kp_item["forms"]}
            if norm(surface) not in alias_forms:
                warnings.append(
                    f"keyword {surface!r}: not a known alias of "
                    f"{kp_item['kp']['name']!r}; stored without a KP"
                )
                kp_item = None
        keywords.append({
            "surface": surface,
            "normalized": norm(surface),
            "kp_id": kp_item["kp"]["kp_id"] if kp_item else None,
            "kp_name": kp_item["kp"]["name"] if kp_item else None,
            "role": role,
            "location": location,
            "option_label": label if location == "option" else None,
            "confidence": raw.get("confidence"),
        })

    # Keep keyword roles aligned with the relation actually stored.
    core_ids = {entry["kp_id"] for entry in core}
    supporting_ids = {entry["kp_id"] for entry in supporting}
    confusable_ids = {entry["kp_id"] for entry in confusables}
    for kw in keywords:
        kp_id = kw["kp_id"]
        if kp_id in core_ids:
            kw["role"] = "core"
        elif kp_id in supporting_ids:
            kw["role"] = "supporting"
        elif kp_id in confusable_ids:
            kw["role"] = "distractor"
        elif kp_id and kw["role"] in ("core", "supporting"):
            kw["role"] = "mentioned"

    notes = compact(data.get("notes") or "")
    return {
        "status": status,
        "core": core,
        "supporting": supporting,
        "confusables": confusables,
        "keywords": keywords,
        "notes": notes,
        "errors": errors,
        "warnings": warnings,
    }


def link_one(question, kps, aliases, scope, scope_kind,
             bm25_docs, bm25_idf, model, max_tokens, timeout, retries):
    candidates = candidate_set(
        question, kps, aliases, scope, scope_kind, bm25_docs, bm25_idf
    )
    prompt = build_prompt(question, candidates, scope_kind)
    text, usage = call_api(
        SYSTEM_PROMPT, prompt, model, max_tokens, timeout, retries
    )
    try:
        data = parse_json(text)
    except Exception as error:
        raise RuntimeError(
            f"{error}; raw={text[:1200]!r}"
        ) from error
    result = validate_result(question, data, candidates)
    result["candidates"] = candidates
    result["prompt"] = prompt
    result["usage"] = usage
    result["raw_response"] = text
    return result


def load_saved_items(exam, know, paper_id):
    """Rebuild export/report items from the saved analysis tables.

    This is the lossless-in-DB view: it drops per-run warnings, but keeps
    the statuses, links, evidence, confusables and keywords that the page
    actually consumes. Used by --export-only to repair incomplete
    per-paper artifacts without spending API calls.
    """
    numbers = {
        row["question_id"]: row["number"]
        for row in exam.execute(
            "SELECT question_id, number FROM questions WHERE paper_id=?",
            (paper_id,),
        )
    }
    items = {}
    for row in know.execute(
        """
        SELECT question_id, status, notes, model, updated_at
        FROM question_analysis
        WHERE paper_id=?
        ORDER BY question_id
        """,
        (paper_id,),
    ):
        items[row["question_id"]] = {
            "question_id": row["question_id"],
            "number": numbers.get(row["question_id"]),
            "status": row["status"],
            "core": [],
            "supporting": [],
            "confusables": [],
            "keywords": [],
            "notes": row["notes"] or "",
            "warnings": [],
            "errors": [],
            "_model": row["model"] or "",
            "_updated_at": row["updated_at"] or "",
        }
    if not items:
        return [], {"generated_at": now_iso(), "model": "", "usage": {}}

    qids = list(items)
    marks = ",".join("?" for _ in qids)
    for row in know.execute(
        f"""
        SELECT l.question_id, l.kp_id, k.name AS kp_name,
               l.relation_type, l.option_label, l.confidence,
               l.evidence, l.rationale
        FROM question_kp_links l
        JOIN knowledge_points k ON k.kp_id = l.kp_id
        WHERE l.question_id IN ({marks})
        ORDER BY l.question_id,
                 CASE l.relation_type
                   WHEN 'core' THEN 0 WHEN 'supporting' THEN 1 ELSE 2 END,
                 l.option_label, l.kp_id
        """,
        qids,
    ):
        item = items[row["question_id"]]
        if row["relation_type"] == "core":
            item["core"].append({
                "kp_id": row["kp_id"],
                "name": row["kp_name"],
                "confidence": row["confidence"],
                "evidence": row["evidence"] or "",
                "evidence_source": "question",
            })
        elif row["relation_type"] == "supporting":
            item["supporting"].append({
                "kp_id": row["kp_id"],
                "name": row["kp_name"],
                "confidence": row["confidence"],
                "evidence": row["evidence"] or "",
            })
        else:
            item["confusables"].append({
                "kp_id": row["kp_id"],
                "name": row["kp_name"],
                "option_label": row["option_label"],
                "reason": row["rationale"] or "",
            })

    for row in know.execute(
        f"""
        SELECT question_id, surface, normalized, kp_id, role, location,
               option_label, confidence
        FROM question_keywords
        WHERE question_id IN ({marks})
        ORDER BY question_id,
                 CASE role WHEN 'core' THEN 0 WHEN 'supporting' THEN 1
                           WHEN 'distractor' THEN 2 ELSE 3 END,
                 surface
        """,
        qids,
    ):
        items[row["question_id"]]["keywords"].append({
            "surface": row["surface"],
            "normalized": row["normalized"],
            "kp_id": row["kp_id"],
            "role": row["role"],
            "location": row["location"],
            "option_label": row["option_label"],
            "confidence": row["confidence"],
        })

    ordered = sorted(
        items.values(),
        key=lambda item: (
            item["number"] if isinstance(item["number"], int) else 10 ** 9,
            item["question_id"],
        ),
    )
    models = sorted({item["_model"] for item in ordered if item["_model"]})
    updated = [item["_updated_at"] for item in ordered if item["_updated_at"]]
    for item in ordered:
        item.pop("_model", None)
        item.pop("_updated_at", None)
    run = {
        "generated_at": max(updated) if updated else now_iso(),
        "model": ", ".join(models),
        "usage": {},
    }
    return ordered, run


def write_export(path, paper_id, run, items, errors):
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
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
        "# 题目解析关联报告",
        "",
        f"- 生成时间：{run['generated_at']}",
        f"- 试卷：`{paper_id}`",
        f"- 模型：`{run['model']}`",
        f"- Prompt：`{PROMPT_VERSION}`",
        f"- 题目：{len(items)}；失败：{len(errors)}",
        "",
        "> 核心知识点按“正确选项倒推”生成；干扰项只进入 confusable。",
        "> 含图题/知识库未收录的题会在备注中标记，不强行绑定不相干知识点。",
        "",
        "| 题号 | 状态 | 核心知识点 | 辅助 | 易混淆 | 关键字 | 备注 |",
        "|---:|---|---|---|---|---|---|",
    ]
    counts = {"linked": 0, "needs_review": 0, "no_match": 0}
    for item in sorted(items, key=lambda x: x["number"]):
        counts[item["status"]] = counts.get(item["status"], 0) + 1
        core = "、".join(e["name"] for e in item["core"]) or "—"
        supporting = "、".join(e["name"] for e in item["supporting"]) or "—"
        confusable = "、".join(
            f"{e['name']}（{e.get('option_label')}）"
            for e in item["confusables"]
        ) or "—"
        keywords = "、".join(
            f"{kw['surface']}" + ("" if kw["kp_id"] else "（未收录）")
            for kw in item["keywords"]
        ) or "—"
        notes = item.get("notes") or ""
        lines.append(
            f"| {item['number']} | {item['status']} | {core} | {supporting} | "
            f"{confusable} | {keywords} | {notes or '—'} |"
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
        f"python3 _tools/link_question_kps.py --paper {paper_id} --force",
        "```",
        "",
    ]
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
    return path


def ensure_tables(con):
    names = {
        row[0] for row in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    required = {"question_analysis", "question_kp_links", "question_keywords"}
    missing = required - names
    if missing:
        raise SystemExit(
            "missing tables: " + ", ".join(sorted(missing))
            + "; run _tools/migrate_question_analysis.py first"
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper", required=True)
    parser.add_argument("--chapter", help="chapter filter, e.g. 'Chapter 11'")
    parser.add_argument("--question-id", action="append", default=[],
                        help="link only this question_id (repeatable)")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--force", action="store_true", help="relink existing questions")
    parser.add_argument("--export-only", action="store_true",
                        help="rebuild JSON/report from saved rows; no API calls")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-tokens", type=int, default=8000)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--out-json", default=None)
    parser.add_argument("--report", default=DEFAULT_REPORT)
    parser.add_argument("--no-backup", action="store_true",
                        help="skip the per-paper knowledge DB backup (batch mode)")
    args = parser.parse_args()

    exam = sqlite3.connect(EXAM_DB)
    exam.row_factory = sqlite3.Row
    know = sqlite3.connect(KNOW_DB)
    know.row_factory = sqlite3.Row
    ensure_tables(know)

    if args.export_only:
        items, run = load_saved_items(exam, know, args.paper)
        if args.question_id:
            wanted = set(args.question_id)
            items = [item for item in items if item["question_id"] in wanted]
        if args.limit is not None:
            items = items[:args.limit]
        if not items:
            print(f"no saved analysis for {args.paper}")
            exam.close()
            know.close()
            return 0
        out_json = args.out_json or os.path.join(
            EXPORT_DIR, f"question_analysis_{args.paper}.json"
        )
        export_path = write_export(out_json, args.paper, run, items, [])
        report_path = write_report(args.report, args.paper, run, items, [])
        print(
            f"exported {len(items)} saved analyses; "
            f"model={run['model'] or '—'}"
        )
        print("export:", export_path)
        print("report:", report_path)
        exam.close()
        know.close()
        return 0

    questions = load_questions(exam, args.paper)
    if args.question_id:
        wanted = set(args.question_id)
        questions = [q for q in questions if q["question_id"] in wanted]

    if not args.force:
        existing = {
            row[0] for row in know.execute(
                "SELECT question_id FROM question_analysis WHERE paper_id=?",
                (args.paper,),
            )
        }
        questions = [q for q in questions if q["question_id"] not in existing]

    if args.limit is not None:
        questions = questions[:args.limit]

    if not questions:
        print("nothing to link")
        exam.close()
        know.close()
        return 0

    kps, aliases = load_knowledge(know)
    bm25_docs, bm25_idf = build_bm25(kps, aliases)
    scope, scope_kind = infer_scope(args.paper, args.chapter)
    print(
        f"{args.paper}: {len(questions)} questions; {len(kps)} KPs; "
        f"{len(aliases)} aliases; scope={scope or '—'} ({scope_kind or 'all'})"
    )

    if args.dry_run:
        for q in questions:
            candidates = candidate_set(
                q, kps, aliases, scope, scope_kind, bm25_docs, bm25_idf
            )
            print("\n" + "=" * 78)
            print(f"Q{q['number']} {q['question_id']}  candidates={len(candidates)}")
            print(candidate_prompt_lines(candidates, scope_kind))
        exam.close()
        know.close()
        return 0

    started = time.time()
    results, errors = {}, []
    usage_total = {"input_tokens": 0, "output_tokens": 0}

    def work(q):
        return q, link_one(
            q, kps, aliases, scope, scope_kind, bm25_docs, bm25_idf,
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

    # Normalize result items for export/report.
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
                    "kp_id": e["kp_id"],
                    "name": e["kp_name"],
                    "confidence": e.get("confidence"),
                    "evidence": e.get("evidence", ""),
                    "evidence_source": e.get("evidence_source", "question"),
                }
                for e in result["core"]
            ],
            "supporting": [
                {
                    "kp_id": e["kp_id"],
                    "name": e["kp_name"],
                    "confidence": e.get("confidence"),
                    "evidence": e.get("evidence", ""),
                }
                for e in result["supporting"]
            ],
            "confusables": [
                {
                    "kp_id": e["kp_id"],
                    "name": e["kp_name"],
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

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run = {
        "generated_at": now_iso(),
        "model": args.model,
        "usage": usage_total,
    }
    out_json = args.out_json or os.path.join(
        EXPORT_DIR, f"question_analysis_{args.paper}.json"
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
        backup = KNOW_DB + f".bak-{stamp}-question-analysis"
        import shutil
        shutil.copy2(KNOW_DB, backup)
        print("backup:", backup)

    # Delete every processed question, including failures, so a failed
    # re-run cannot leave stale links behind.
    processed_qids = [q["question_id"] for q in questions]
    marks = ",".join("?" for _ in processed_qids)
    with know:
        know.execute(f"DELETE FROM question_keywords WHERE question_id IN ({marks})", processed_qids)
        know.execute(f"DELETE FROM question_kp_links WHERE question_id IN ({marks})", processed_qids)
        know.execute(f"DELETE FROM question_analysis WHERE question_id IN ({marks})", processed_qids)
        for item in items:
            know.execute(
                "INSERT INTO question_analysis"
                "(question_id, paper_id, status, model, prompt_version, notes, updated_at) "
                "VALUES (?,?,?,?,?,?,?)",
                (
                    item["question_id"], args.paper, item["status"],
                    args.model, PROMPT_VERSION, item["notes"] or None,
                    run["generated_at"],
                ),
            )
            for entry in item["core"]:
                know.execute(
                    "INSERT INTO question_kp_links"
                    "(question_id, kp_id, relation_type, option_label, confidence, "
                    " evidence, rationale, created_at) VALUES (?,?,?,?,?,?,?,?)",
                    (
                        item["question_id"], entry["kp_id"], "core", None,
                        entry.get("confidence"), entry.get("evidence"),
                        None, run["generated_at"],
                    ),
                )
            for entry in item["supporting"]:
                know.execute(
                    "INSERT INTO question_kp_links"
                    "(question_id, kp_id, relation_type, option_label, confidence, "
                    " evidence, rationale, created_at) VALUES (?,?,?,?,?,?,?,?)",
                    (
                        item["question_id"], entry["kp_id"], "supporting", None,
                        entry.get("confidence"), entry.get("evidence"),
                        None, run["generated_at"],
                    ),
                )
            for entry in item["confusables"]:
                know.execute(
                    "INSERT INTO question_kp_links"
                    "(question_id, kp_id, relation_type, option_label, confidence, "
                    " evidence, rationale, created_at) VALUES (?,?,?,?,?,?,?,?)",
                    (
                        item["question_id"], entry["kp_id"], "confusable",
                        entry.get("option_label"), entry.get("confidence"), None,
                        entry.get("reason"), run["generated_at"],
                    ),
                )
            for kw in item["keywords"]:
                know.execute(
                    "INSERT OR IGNORE INTO question_keywords"
                    "(question_id, surface, normalized, kp_id, role, location, "
                    " option_label, confidence, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                    (
                        item["question_id"], kw["surface"], kw["normalized"],
                        kw["kp_id"], kw["role"], kw["location"],
                        kw["option_label"], kw.get("confidence"),
                        run["generated_at"],
                    ),
                )

    integrity = know.execute("PRAGMA integrity_check").fetchone()[0]
    fk = know.execute("PRAGMA foreign_key_check").fetchall()
    print("integrity_check:", integrity, "foreign_key_check:", "OK" if not fk else fk[:3])

    report_path = write_report(args.report, args.paper, run, items, errors)
    print("report:", report_path)
    exam.close()
    know.close()
    return 0 if integrity == "ok" and not fk and not errors else 1


if __name__ == "__main__":
    sys.exit(main())
