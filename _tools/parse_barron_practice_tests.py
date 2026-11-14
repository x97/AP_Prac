#!/usr/bin/env python3
"""Parse the three Barron's AP Psychology 2027 practice tests.

Inputs:
- data/content/psychology/extraction/book_text/pt_line_boxes.tsv (page/line/x/y/text from PDFKit)
- data/content/psychology/extraction/book_text/practice_tests.txt (page text, for FRQ/source material)

Output: data/content/psychology/extraction/barron2027_practice_tests.json
"""
import argparse
import json
import os
import re
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LINE_BOXES = os.path.join(ROOT, "data", "content", "psychology", "extraction", "book_text", "pt_line_boxes.tsv")
PAGE_TEXT = os.path.join(ROOT, "data", "content", "psychology", "extraction", "book_text", "practice_tests.txt")
OUT = os.path.join(ROOT, "data", "content", "psychology", "extraction", "barron2027_practice_tests.json")
PDF_NAME = "assets/psychology/books/AP Psychology Premium, 2027 - Allyson J. Weseley & Robert McEntarffer.pdf"

TESTS = [
    {"test": 1, "paper_id": "psychology-barrons-2027-pt1", "mcq": (433, 460), "frq": (461, 475), "ans": (476, 487), "frq_ans": (487, 495)},
    {"test": 2, "paper_id": "psychology-barrons-2027-pt2", "mcq": (496, 522), "frq": (523, 538), "ans": (539, 554), "frq_ans": (554, 562)},
    {"test": 3, "paper_id": "psychology-barrons-2027-pt3", "mcq": (563, 588), "frq": (589, 601), "ans": (602, 618), "frq_ans": (618, 627)},
]

QRE = re.compile(r"^(\d{1,3})\.\s*(.*)$")
OPTRE = re.compile(r"^\(?([A-D])\)\s*(.*)$")
NOISE = re.compile(
    r"^(GO ON TO THE NEXT PAGE\.?|STOP\b|Practice Test \d|Section I:|Section II:|"
    r"Answer Explanations|AP Psychology|©|Barron|[-–— ]*\d+[-–— ]*)$", re.I
)
LEAD1 = re.compile(r"Questions?\s+(\d{1,3})\s*(?:through|and|to|[-–])\s*(\d{1,3})\s+refer to the following\.?", re.I)
LEAD2 = re.compile(r"Use the following information to answer questions?\s+(\d{1,3})\s*(?:and|through|[-–])\s*(\d{1,3})\.?", re.I)
LEAD_ANY = re.compile(
    r"(Questions?\s+\d{1,3}\s*(?:through|and|to|[-–])\s*\d{1,3}\s+refer to the following\.?|"
    r"Use the following information to answer questions?\s+\d{1,3}\s*(?:and|through|[-–])\s*\d{1,3}\.)", re.I
)
ANS_RE = re.compile(r"^(\d{1,3})\.\s*\(([A-D])\)\s*(.*)$")


def load_rows():
    rows = defaultdict(list)
    for line in open(LINE_BOXES, encoding="utf-8"):
        p, ln, x, y, w, h, t = line.rstrip("\n").split("\t", 6)
        rows[int(p)].append((int(ln), float(x), float(y), float(w), float(h), t))
    return rows


def visual_lines(rows, page):
    items = sorted(rows.get(page, []), key=lambda r: (-r[2], r[1]))
    groups = []
    for r in items:
        if groups and abs(r[2] - groups[-1][0][2]) <= 2.5:
            groups[-1].append(r)
        else:
            groups.append([r])
    return [(g[0][2], " ".join(r[5] for r in sorted(g, key=lambda r: r[1]))) for g in groups]


def lead_range(text):
    for pat in (LEAD1, LEAD2):
        m = pat.search(text)
        if m:
            return int(m.group(1)), int(m.group(2))
    return None


def parse_mcq(rows, start_page, end_page):
    questions = []
    cur = None
    opt = None
    expected = 1
    ctx_lines = []
    ctx_range = None

    def finish():
        nonlocal cur, opt
        if cur:
            if opt is not None:
                cur["options"][opt] = cur["options"].get(opt, "").strip()
            cur["stem"] = " ".join(cur["stem"]).strip()
            for key in "ABCD":
                cur["options"].setdefault(key, "")
            questions.append(cur)
        cur = None
        opt = None

    def start_ctx(rng):
        nonlocal ctx_lines, ctx_range
        ctx_range = rng
        ctx_lines = []

    def consume(line, page):
        nonlocal cur, opt, expected, ctx_range, ctx_lines
        s = line.strip()
        if not s or NOISE.match(s):
            return
        lm = LEAD_ANY.search(s)
        if lm and lm.start() > 0:
            prefix = s[:lm.start()].strip()
            if prefix:
                consume(prefix, page)
            finish()
            start_ctx(lead_range(lm.group(1)))
            return
        if lm:
            finish()
            start_ctx(lead_range(lm.group(1)))
            return
        m = QRE.match(s)
        if m:
            num = int(m.group(1))
            if num == expected or (expected < num <= expected + 2 and num <= 75):
                finish()
                expected = num + 1
                ctx = ""
                if ctx_range and ctx_range[0] <= num <= ctx_range[1]:
                    ctx = " ".join(ctx_lines).strip()
                elif ctx_range and num > ctx_range[1]:
                    ctx_range = None
                    ctx_lines = []
                cur = {
                    "number": num,
                    "stem": [m.group(2).strip()] if m.group(2).strip() else [],
                    "options": {},
                    "context": ctx,
                    "page_start": page,
                    "page_end": page,
                }
                return
        parts = re.split(r"(?=\([A-D]\)\s)", s)
        if len(parts) > 1 and all(OPTRE.match(x.strip()) for x in parts if x.strip()):
            if cur:
                for part in parts:
                    part = part.strip()
                    if not part:
                        continue
                    mo = OPTRE.match(part)
                    if mo:
                        opt = mo.group(1)
                        cur["options"][opt] = (cur["options"].get(opt, "") + " " + mo.group(2)).strip()
                cur["page_end"] = page
            return
        mo = OPTRE.match(s)
        if mo and cur:
            opt = mo.group(1)
            cur["options"][opt] = (cur["options"].get(opt, "") + " " + mo.group(2)).strip()
            cur["page_end"] = page
            return
        if cur:
            if opt is not None:
                cur["options"][opt] = (cur["options"].get(opt, "") + " " + s).strip()
            else:
                cur["stem"].append(s)
            cur["page_end"] = page
        elif ctx_range:
            ctx_lines.append(s)

    for page in range(start_page, end_page + 1):
        for _, line in visual_lines(rows, page):
            consume(line, page)
    finish()
    return questions


def parse_answers(rows, start_page, end_page):
    answers = {}
    cur = None
    buf = []

    def finish():
        nonlocal cur, buf
        if cur:
            answers[cur[0]] = {"answer": cur[1], "explanation": " ".join(buf).strip()}
        cur = None
        buf = []

    for page in range(start_page, end_page + 1):
        for _, line in visual_lines(rows, page):
            s = line.strip()
            if not s:
                continue
            if s.startswith("Section II"):
                finish()
                return answers
            m = ANS_RE.match(s)
            if m:
                finish()
                cur = (int(m.group(1)), m.group(2))
                buf = [m.group(3).strip()] if m.group(3).strip() else []
                continue
            if cur:
                buf.append(s)
    finish()
    return answers


def page_text_map():
    text = open(PAGE_TEXT, encoding="utf-8").read()
    parts = re.split(r"=== PAGE (\d+) ===\n", text)
    return {int(parts[i]): parts[i + 1] for i in range(1, len(parts), 2)}


def clean_text(text):
    text = re.sub(r"=== PAGE \d+ ===\n?", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_pages(pages, start, end):
    return clean_text("".join(f"=== PAGE {p} ===\n{pages.get(p, '')}" for p in range(start, end + 1)))


def heading_page(pages, start_page, end_page, pattern):
    rx = re.compile(pattern, re.I)
    for p in range(start_page, end_page + 1):
        if rx.search(pages.get(p, "")):
            return p
    return start_page


def parse_frq_questions(pages, start_page, end_page):
    text = split_pages(pages, start_page, end_page)
    headings = list(re.finditer(r"Question\s+([12]):\s*(Article Analysis Question \(AAQ\)|Evidence-Based Question \(EBQ\))", text))
    if len(headings) < 2:
        raise RuntimeError(f"FRQ headings not found in pages {start_page}-{end_page}: {len(headings)}")
    out = []
    for i, m in enumerate(headings):
        begin = m.start()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
        body = text[begin:end].strip()
        pattern = (r"Question\s+" + m.group(1) + r":\s*" +
                   ("Article Analysis Question" if "AAQ" in m.group(2) else "Evidence-Based Question"))
        page_start = heading_page(pages, start_page, end_page, pattern)
        out.append({
            "number": int(m.group(1)),
            "kind": "AAQ" if "AAQ" in m.group(2) else "EBQ",
            "stem": body,
            "page_start": page_start,
        })
    # The first question ends where the second begins (they often share a page).
    for i, q in enumerate(out):
        if i + 1 < len(out):
            q["page_end"] = out[i + 1]["page_start"]
        else:
            q["page_end"] = end_page
    return out


def parse_frq_answers(pages, start_page, end_page):
    text = split_pages(pages, start_page, end_page)
    headings = list(re.finditer(r"Question\s+([12]):\s*(Article Analysis Question \(AAQ\)|Evidence-Based Question \(EBQ\))", text))
    if len(headings) < 2:
        raise RuntimeError(f"FRQ answer headings not found in pages {start_page}-{end_page}: {len(headings)}")
    out = []
    for i, m in enumerate(headings):
        begin = m.start()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
        body = text[begin:end].strip()
        parts = parse_frq_parts(body)
        total = sum(p["max_points"] for p in parts)
        out.append({
            "number": int(m.group(1)),
            "kind": "AAQ" if "AAQ" in m.group(2) else "EBQ",
            "answer_text": body,
            "parts": parts,
            "total_points": total,
        })
    return out


def parse_frq_parts(body):
    # Part headings: Part (A), Part A, Part B (i), Part C (ii), ...
    pat = re.compile(r"(?m)^\s*Part\s*(?:\(([A-F])\)|([A-F])(?:\s*\((i|ii)\))?)\s*$", re.I)
    matches = list(pat.finditer(body))
    parts = []
    for i, m in enumerate(matches):
        letter = (m.group(1) or m.group(2)).upper()
        sub = m.group(3)
        label = letter + (f"({sub})" if sub else "")
        begin = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        chunk = body[begin:end].strip()
        # Split prompt / sample / scoring guide
        sample_m = re.search(r"Sample Student (?:Answer|Response)", chunk, re.I)
        guide_m = re.search(r"Scoring Guide", chunk, re.I)
        if sample_m:
            prompt = chunk[:sample_m.start()].strip()
            rest = chunk[sample_m.end():]
        else:
            prompt = chunk
            rest = ""
        if guide_m and sample_m:
            sample = rest[:guide_m.start() - sample_m.end()].strip()
            criteria = rest[guide_m.end() - sample_m.end():].strip()
        elif guide_m:
            before = chunk[:guide_m.start()].strip()
            # Some AAQ parts omit the "Sample Student Answer" heading.
            # The first sentence is the prompt; the remainder is the sample response.
            sm = re.match(r"(.+?[.?!])\s+(.*)", before, re.S)
            if sm:
                prompt, sample = sm.group(1), sm.group(2)
            else:
                prompt, sample = before, ""
            criteria = chunk[guide_m.end():].strip()
        else:
            sample = ""
            criteria = rest.strip()
        # Clean obvious extraction artifacts from prompt.
        prompt = re.sub(r"\bconcept\.\s*", "", prompt).strip()
        prompt = re.sub(r"\s+", " ", prompt)
        prompt = prompt.replace("computer- authored", "computer-authored")
        prompt = re.sub(
            r"Explain how the evidence supports your claim using a psychological\s+"
            r"Explain how the evidence", "Explain how the evidence", prompt
        )
        # Max points: take the largest explicit "N points" mention, cap at 2.
        nums = [int(x) for x in re.findall(r"(\d+)\s+points?", criteria, re.I)]
        max_points = max(nums) if nums else 1
        max_points = min(max_points, 2)
        parts.append({
            "label": label,
            "title": prompt,
            "max_points": max_points,
            "criteria": criteria,
            "sample_answer": sample,
        })
    return parts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()
    rows = load_rows()
    pages = page_text_map()
    payload = {"pdf": PDF_NAME, "tests": []}
    for spec in TESTS:
        questions = parse_mcq(rows, *spec["mcq"])
        answers = parse_answers(rows, *spec["ans"])
        for q in questions:
            a = answers.get(q["number"])
            q["correct_answer"] = a["answer"] if a else None
            q["answer_text"] = a["explanation"] if a else ""
            # graph-option placeholders
            if not any(q["options"].get(k, "").strip() for k in "ABCD"):
                for k in "ABCD":
                    # For a multi-page graph-option question, A is usually on the
                    # first page and B-D on the following page.
                    pg = q["page_start"] if q["page_start"] == q["page_end"] or k == "A" else q["page_end"]
                    q["options"][k] = f"(graph {k}; see PDF p.{pg})"
            q["section"] = "MCQ"
        frq_q = parse_frq_questions(pages, *spec["frq"])
        frq_a = parse_frq_answers(pages, *spec["frq_ans"])
        for i, q in enumerate(frq_q):
            a = frq_a[i] if i < len(frq_a) else None
            q["section"] = "FRQ"
            q["correct_answer"] = None
            q["answer_text"] = a["answer_text"] if a else ""
            q["rubric"] = {
                "total_points": a["total_points"] if a else None,
                "parts": a["parts"] if a else [],
            }
        payload["tests"].append({
            "test": spec["test"],
            "paper_id": spec["paper_id"],
            "mcq": questions,
            "frq": frq_q,
        })
    json.dump(payload, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for t in payload["tests"]:
        print(f"Test {t['test']}: {len(t['mcq'])} MCQ, {len(t['frq'])} FRQ, "
              f"answers {sum(1 for q in t['mcq'] if q['correct_answer'])}")
        for f in t["frq"]:
            print(f"  FRQ{f['number']} {f['kind']}: parts={len(f['rubric']['parts'])} total={f['rubric']['total_points']}")
    print("wrote", args.out)


if __name__ == "__main__":
    main()
