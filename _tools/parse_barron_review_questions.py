#!/usr/bin/env python3
"""Parse Barron's AP Psychology 2027 chapter-end Review Questions.

Inputs:
- data/content/psychology/extraction/book_text/review_line_boxes.tsv (pages 86-397)
Output:
- data/content/psychology/extraction/barron2027_review_questions.json
"""
import argparse
import json
import os
import re
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LINES = os.path.join(ROOT, "data", "content", "psychology", "extraction", "book_text", "review_line_boxes.tsv")
OUT = os.path.join(ROOT, "data", "content", "psychology", "extraction", "barron2027_review_questions.json")
PDF = "assets/psychology/books/AP Psychology Premium, 2027 - Allyson J. Weseley & Robert McEntarffer.pdf"

CHAPTERS = {
    4: ("Biological Bases of Behavior", 1),
    5: ("States of Consciousness", 1),
    6: ("Sensation", 1),
    7: ("Perception", 2),
    8: ("Thinking and Creativity", 2),
    9: ("Memory", 2),
    10: ("Testing and Individual Differences", 2),
    11: ("Developmental Psychology", 3),
    12: ("Learning", 3),
    13: ("Social Psychology", 4),
    14: ("Personality", 4),
    15: ("Motivation and Emotion", 4),
    16: ("Health Psychology", 5),
    17: ("Psychological Disorders", 5),
    18: ("Treatment of Psychological Disorders", 5),
}
REVIEW = {4: 86, 5: 108, 6: 129, 7: 146, 8: 157, 9: 176, 10: 200,
          11: 227, 12: 258, 13: 290, 14: 309, 15: 329, 16: 342, 17: 369, 18: 392}
ANSWER = {4: 91, 5: 111, 6: 131, 7: 149, 8: 160, 9: 183, 10: 202,
          11: 232, 12: 263, 13: 295, 14: 312, 15: 333, 16: 347, 17: 374, 18: 395}
END = {4: 95, 5: 113, 6: 133, 7: 151, 8: 163, 9: 185, 10: 203,
       11: 236, 12: 266, 13: 299, 14: 313, 15: 335, 16: 349, 17: 376, 18: 397}

QRE = re.compile(r"^(\d{1,3})\.\s*(.*)$")
OPTRE = re.compile(r"^\(?([A-D])\)\s*(.*)$")
ANSRE = re.compile(r"^(\d{1,3})\.\s*\(([A-D])\)\s*(.*)$")
NOISE = re.compile(
    r"^(Review Questions|Answer Explanations|GO ON TO THE NEXT PAGE\.?|STOP\b|"
    r"AP Psychology|©|Barron|[-–— ]*\d+[-–— ]*)$", re.I
)
LEAD_ANY = re.compile(
    r"(Questions?\s+\d{1,3}[^.]*?refer to the following\.?|"
    r"Use the (?:following )?(?:information|diagram|graph|table|figure)(?: below)?[^.]*?\.)", re.I
)
LEAD_FRAG = re.compile(
    r"^(Questions?\s+\d{1,3}|Use the (?:following )?(?:information|diagram|graph|table|figure)(?: below)?)", re.I
)
def load_rows():
    rows = defaultdict(list)
    for line in open(LINES, encoding="utf-8"):
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
    m = LEAD_ANY.search(text)
    if not m:
        return None
    nums = [int(x) for x in re.findall(r"\d{1,3}", m.group(0))]
    if len(nums) >= 2:
        return nums[0], nums[-1]
    return None


def parse_questions(rows, start_page, end_page):
    questions = []
    cur = None
    opt = None
    expected = 1
    ctx_lines = []
    ctx_range = None
    started = False

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

    def consume(s, page):
        nonlocal cur, opt, expected, ctx_range, ctx_lines, started
        s = s.strip()
        if not s:
            return None
        if s.lower().startswith("answer explanations"):
            return "STOP"
        if s.lower() == "review questions":
            started = True
            return None
        if not started or NOISE.match(s):
            return None

        lm = LEAD_ANY.search(s)
        if lm and lm.start() > 0:
            prefix = s[:lm.start()].strip()
            if prefix:
                consume(prefix, page)
            lead = s[lm.start():].strip()
            finish()
            ctx_range = lead_range(lead)
            ctx_lines = [lead]
            return None
        if lm:
            lead = s[lm.start():].strip()
            finish()
            ctx_range = lead_range(lead)
            ctx_lines = [lead]
            return None

        m = QRE.match(s)
        if m:
            num = int(m.group(1))
            if num == expected or (expected < num <= expected + 2 and num <= 200):
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
                return None

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
            return None
        mo = OPTRE.match(s)
        if mo and cur:
            opt = mo.group(1)
            cur["options"][opt] = (cur["options"].get(opt, "") + " " + mo.group(2)).strip()
            cur["page_end"] = page
            return None
        if cur:
            if opt is not None:
                cur["options"][opt] = (cur["options"].get(opt, "") + " " + s).strip()
            else:
                cur["stem"].append(s)
            cur["page_end"] = page
        elif ctx_range:
            ctx_lines.append(s)
        return None

    for page in range(start_page, end_page + 1):
        vis = visual_lines(rows, page)
        i = 0
        while i < len(vis):
            s = vis[i][1]
            if LEAD_FRAG.match(s.strip()) and lead_range(s.strip()) is None and i + 1 < len(vis):
                combined = s.strip() + " " + vis[i + 1][1].strip()
                if lead_range(combined):
                    s = combined
                    i += 1
            result = consume(s, page)
            if result == "STOP":
                finish()
                return questions
            i += 1
    finish()
    return questions


def parse_answers(rows, start_page, end_page):
    answers = {}
    cur = None
    buf = []
    started = False

    def finish():
        nonlocal cur, buf
        if cur:
            answers[cur[0]] = {"answer": cur[1], "explanation": " ".join(buf).strip()}
        cur = None
        buf = []

    for page in range(start_page, end_page + 1):
        for _, s in visual_lines(rows, page):
            s = s.strip()
            if not s:
                continue
            if not started:
                if s.lower().startswith("answer explanations"):
                    started = True
                continue
            if re.match(r"^(Chapter|Unit)\s+\d+\b", s):
                finish()
                return answers
            m = ANSRE.match(s)
            if m:
                finish()
                cur = (int(m.group(1)), m.group(2))
                buf = [m.group(3).strip()] if m.group(3).strip() else []
                continue
            if cur:
                buf.append(s)
    finish()
    return answers


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()
    rows = load_rows()
    payload = {"pdf": PDF, "chapters": []}
    for ch in sorted(CHAPTERS):
        title, unit = CHAPTERS[ch]
        qs = parse_questions(rows, REVIEW[ch], ANSWER[ch])
        ans = parse_answers(rows, ANSWER[ch], END[ch])
        for q in qs:
            a = ans.get(q["number"])
            q["correct_answer"] = a["answer"] if a else None
            q["answer_text"] = a["explanation"] if a else ""
            q["section"] = "MCQ"
        payload["chapters"].append({
            "chapter": ch,
            "unit": unit,
            "chapter_title": title,
            "paper_id": f"psychology-barrons-2027-ch{ch}-review",
            "review_page_start": REVIEW[ch],
            "answer_page_start": ANSWER[ch],
            "page_end": END[ch],
            "questions": qs,
        })
    json.dump(payload, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    total = 0
    for c in payload["chapters"]:
        n = len(c["questions"])
        answered = sum(1 for q in c["questions"] if q["correct_answer"])
        total += n
        print(f"Ch{c['chapter']:>2} {c['chapter_title']:<42} Q{n:>2} answers{answered:>2} missing{[q['number'] for q in c['questions'] if not q['correct_answer']]}")
    print("total", total)
    print("wrote", args.out)


if __name__ == "__main__":
    main()
