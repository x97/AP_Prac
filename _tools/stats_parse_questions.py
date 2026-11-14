#!/usr/bin/env python3
"""Parse Barron's AP Statistics Premium 2027 practice questions.

Papers:
  - Quizzes 1-34 (Unit review; some are MCQ+FRQ, 31-34 are FRQ only)
  - Diagnostic Test (42 MCQ + 4 FRQ)
  - Practice Tests 1-4 (42 MCQ + 4 FRQ each)

Text is read line-by-line with page/bbox metadata. Images are recorded as
page assets but are not cropped here; the import script crops them.

Outputs:
  data/content/statistics/extraction/questions/*.json
  data/content/statistics/extraction/questions_all.json
  data/content/statistics/extraction/reports/parse_report.md
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PDF_REL = "assets/statistics/books/AP Statistics Premium, 2027 - Martin Sternstein.pdf"
PDF_ABS = os.path.join(ROOT, PDF_REL)
OUT_DIR = os.path.join(ROOT, "data", "content", "statistics", "extraction")
Q_DIR = os.path.join(OUT_DIR, "questions")
REPORT = os.path.join(OUT_DIR, "reports", "parse_report.md")

BOOK_ID = "statistics-barrons-2027"
SUBJECT_ID = "statistics"
SOURCE_ID = "statistics-barrons-2027"

QUIZ_UNIT = {**{n: 1 for n in range(1, 9)},
             **{n: 2 for n in range(9, 16)},
             **{n: 3 for n in range(16, 23)},
             **{n: 4 for n in range(23, 29)},
             **{n: 5 for n in range(29, 31)},
             **{n: 6 for n in range(31, 35)}}  # 6 = Final Review (mixed)

NOISE_RE = re.compile(
    r"^(Follow for extended description|SPEND \d+ MINUTES.*|"
    r"DIRECTIONS:.*|Choose the response that best answers.*|"
    r"The questions or incomplete statements that follow.*)$", re.I)
HEADING_RE = re.compile(
    r"^(Multiple-Choice Questions|Free-Response Questions|"
    r"Section I: Questions? .*|Section II: Free-Response.*|"
    r"Answer Explanations|Quiz \d+)$", re.I)
Q_RE = re.compile(r"^(\d{1,2})\.\s*(.*)$")
OPT_RE = re.compile(r"^\(([A-E])\)\s*(.*)$")
CTX_RANGE_RE = re.compile(
    r"^Questions?\s+(\d{1,2})\s*[-–—]\s*(\d{1,2})\s+refer to the following", re.I)
CTX_LEAD_RE = re.compile(
    r"^(Use the following|The following|Questions? \d+.* refer to the following)", re.I)
STOP_MARKERS = ("Answer Explanations", "Section II: Free-Response")


def load_fitz():
    try:
        import fitz  # noqa: F401
    except ImportError:
        sys.path.append("/Users/aa/Library/Python/3.9/lib/python/site-packages")
    import fitz
    return fitz


def clean(s):
    s = s.replace(" ", " ").replace("﻿", "")
    s = s.replace("Follow for extended description", " ")
    return re.sub(r"\s+", " ", s).strip()


def page_items(page):
    """Return sorted line/image events: (kind, y0, x0, payload)."""
    items = []
    d = page.get_text("dict")
    for block in d["blocks"]:
        if block["type"] == 0:
            for line in block["lines"]:
                text = clean("".join(span["text"] for span in line["spans"]))
                if not text:
                    continue
                x0, y0, x1, y1 = line["bbox"]
                items.append(("line", y0, x0, {
                    "text": text, "bbox": [round(v, 1) for v in (x0, y0, x1, y1)]}))
        else:
            x0, y0, x1, y1 = block["bbox"]
            items.append(("image", y0, x0, {
                "bbox": [round(v, 1) for v in (x0, y0, x1, y1)]}))
    items.sort(key=lambda e: (round(e[1], 1), round(e[2], 1)))
    return items


def toc_map(doc):
    toc = doc.get_toc()
    entries = [{"level": lvl, "title": clean(t), "page": pg}
               for lvl, t, pg in toc]

    def next_page(idx, max_level):
        for e in entries[idx + 1:]:
            if e["level"] <= max_level:
                return e["page"]
        return doc.page_count

    quizzes = []
    for i, e in enumerate(entries):
        if e["level"] == 3 and e["title"].startswith("Quiz "):
            n = int(e["title"].split()[1])
            nxt = next((x for x in entries[i + 1:] if x["level"] <= 3), None)
            quizzes.append({"number": n, "page_start": e["page"],
                            "page_end": max(e["page"],
                                            (nxt["page"] if nxt else doc.page_count)),
                            "stop_heading": nxt["title"] if nxt else None})

    parts = {}
    for i, e in enumerate(entries):
        if e["level"] == 2 and e["title"].startswith("Practice Test "):
            n = int(e["title"].split()[-1])
            nxt = next((x["page"] for x in entries[i + 1:] if x["level"] <= 2),
                       doc.page_count)
            parts[n] = {"page_start": e["page"], "page_end": max(e["page"], nxt - 1)}
    return quizzes, parts, entries


DIR_FRAG_RE = re.compile(
    r"^(suggested answers|follow are each followed|answers\. Choose|Choose the response|completions\.|"
    r"graded on|on the correctness|The questions or incomplete statements|"
    r"answers\.$)", re.I)


def clean_context(text):
    parts = [p for p in re.split(r"(?<=[.!?])\s+", text or "")
             if p and not DIR_FRAG_RE.match(p)]
    return clean(" ".join(parts))


def finalize_question(cur, out):
    if not cur:
        return
    # Drop empty trailing options and normalise.
    cur["stem"] = clean(" ".join(cur.pop("stem_parts")))
    cur["context"] = clean_context(clean(" ".join(cur.pop("context_parts"))))
    for label in list(cur["options"]):
        cur["options"][label] = clean(" ".join(cur["options"][label]))
    out.append(cur)



def postprocess_mcq(questions):
    for q in questions:
        q.pop("_last_y", None)
        for im in q.pop("raw_images", []):
            best = None
            for label, boxes in q.get("option_boxes", {}).items():
                for box in boxes:
                    if box["page"] != im["page"]:
                        continue
                    im_cy = (im["bbox"][1] + im["bbox"][3]) / 2
                    bx_cy = (box["bbox"][1] + box["bbox"][3]) / 2
                    dist = abs(im_cy - bx_cy)
                    if best is None or dist < best[0]:
                        best = (dist, label)
            if best and best[0] <= 26:
                q["option_images"].setdefault(best[1], []).append(im)
            else:
                q["figure_images"].append(im)
        # Source typo: some questions label the fourth choice (E).
        if "E" in q["options"] and "D" not in q["options"]:
            q["options"]["D"] = q["options"].pop("E")
            if q.get("option_images", {}).get("E"):
                q["option_images"]["D"] = q["option_images"].pop("E")
            if q.get("option_boxes", {}).get("E"):
                q["option_boxes"]["D"] = q["option_boxes"].pop("E")
        for label in "ABCD":
            q["options"].setdefault(label, "")
            if not q["options"][label] and q["option_images"].get(label):
                q["options"][label] = "[see image]"
        # Fallback: empty choices that are vector formulas / missing text.
        q.setdefault("option_crops", {})
        for label in "ABCD":
            if q["options"].get(label) or q["option_images"].get(label):
                continue
            boxes = q.get("option_boxes", {}).get(label, [])
            if not boxes:
                continue
            box = boxes[0]
            page, bb = box["page"], box["bbox"]
            later = []
            order = "ABCD"
            for nxt in order[order.index(label) + 1:]:
                for b in q.get("option_boxes", {}).get(nxt, []):
                    if b["page"] == page and b["bbox"][1] > bb[1] + 2:
                        later.append(b["bbox"][1])
            y1 = min(later) - 3 if later else min(740.0, bb[3] + 26)
            q["option_crops"][label] = {
                "page": page,
                "bbox": [90.0, max(0.0, bb[1] - 3), 550.0, y1],
            }
            q["options"][label] = "[see image]"

def parse_mcq(doc, start, end, paper_id, start_heading=None):
    """Parse an MCQ section. Returns (questions, last_page)."""
    questions = []
    cur = None
    opt = None
    expected = 1
    ctx_range = None
    ctx_parts = []
    ctx_images = []
    pending_ctx = []
    pending_images = []
    in_body = False
    page = start
    for pn in range(start, end + 1):
        page = pn
        items = page_items(doc[pn - 1])
        if pn == start and start_heading:
            for i, (kind, y, x, payload) in enumerate(items):
                if kind == "line" and (payload["text"] == start_heading
                                        or payload["text"].startswith(start_heading[:18])):
                    items = items[i:]
                    break
        for kind, y, x, payload in items:
            if kind == "image":
                if cur is not None:
                    cur["raw_images"].append(
                        {"page": pn, "bbox": payload["bbox"]})
                else:
                    pending_images.append(
                        {"page": pn, "bbox": payload["bbox"]})
                continue
            text = payload["text"]
            if not text or NOISE_RE.match(text):
                continue
            if (text.startswith("Answer Explanations")
                    or text.startswith("Section II")
                    or text.startswith("Free-Response Question")):
                finalize_question(cur, questions)
                postprocess_mcq(questions)
                return questions, pn
            if text in ("Multiple-Choice Questions", "Section I: Questions 1–42",
                        "Section I: Questions 1-42") or text.startswith("Section I: Questions"):
                in_body = True
                continue
            if (HEADING_RE.match(text)
                    or text.startswith("The answers for this Quiz")
                    or text.startswith("The answers for this quiz")
                    or text.startswith("DIRECTIONS:")):
                continue
            if not in_body:
                if text == "Diagnostic Test" or text.startswith("Practice Test"):
                    continue
                pending_ctx.append(text)
                continue

            # Shared material for a question range.
            m = CTX_RANGE_RE.match(text)
            if m:
                finalize_question(cur, questions)
                cur = None
                opt = None
                ctx_range = (int(m.group(1)), int(m.group(2)))
                ctx_parts = [text]
                ctx_images = pending_images[:]
                pending_images = []
                continue

            qm = Q_RE.match(text)
            if qm:
                num = int(qm.group(1))
                if num == expected and (num <= 99):
                    finalize_question(cur, questions)
                    ctx = ""
                    if ctx_range and ctx_range[0] <= num <= ctx_range[1]:
                        ctx = " ".join(ctx_parts)
                    elif pending_ctx:
                        ctx = " ".join(pending_ctx)
                        pending_ctx = []
                    if ctx_range and ctx_range[0] <= num <= ctx_range[1]:
                        if num == ctx_range[0]:
                            if not ctx_images:
                                ctx_images = pending_images[:]
                            imgs = ctx_images
                        else:
                            imgs = ctx_images
                    else:
                        imgs = pending_images
                        if ctx_range and num > ctx_range[1]:
                            ctx_images = []
                    pending_images = []
                    cur = {
                        "number": num,
                        "section": "MCQ",
                        "stem_parts": [qm.group(2)] if qm.group(2) else [],
                        "context_parts": [ctx] if ctx else [],
                        "options": {},
                        "option_images": {},
                        "option_boxes": {},
                        "raw_images": list(imgs),
                        "figure_images": [],
                        "page_start": pn,
                        "page_end": pn,
                        "_last_y": y,
                    }
                    expected = num + 1
                    opt = None
                    continue

            matches = list(re.finditer(r"\(([A-E])\)", text))
            if matches and cur is not None:
                for j, m in enumerate(matches):
                    label = m.group(1)
                    # The ebook occasionally repeats an option label instead
                    # of advancing (A,B,C,C or A,A,A,A). Move to the next
                    # unused label so choices are not overwritten.
                    if label in cur["options"]:
                        for cand in "ABCD"[ "ABCD".index(label) + 1:]:
                            if cand not in cur["options"]:
                                label = cand
                                break
                    start = m.end()
                    stop = matches[j + 1].start() if j + 1 < len(matches) else len(text)
                    content = text[start:stop].strip()
                    cur["options"][label] = [content] if content else []
                    cur["option_boxes"].setdefault(label, []).append(
                        {"page": pn, "bbox": payload["bbox"]})
                    opt = label
                cur["page_end"] = pn
                cur["_last_y"] = y
                continue

            if cur is not None:
                if opt is not None:
                    cur["options"][opt].append(text)
                else:
                    cur["stem_parts"].append(text)
                cur["page_end"] = pn
                cur["_last_y"] = y
            elif ctx_range:
                ctx_parts.append(text)
            elif in_body and not pending_ctx:
                pending_ctx.append(text)
            elif in_body:
                pending_ctx.append(text)
    finalize_question(cur, questions)
    postprocess_mcq(questions)
    return questions, page


def parse_frq(doc, start, end, paper_id, frq_only=False, stop_heading=None, start_heading=None):
    questions = []
    cur = None
    expected = 1
    pending_images = []
    in_body = frq_only
    for pn in range(start, end + 1):
        items = page_items(doc[pn - 1])
        if pn == start and start_heading:
            for i, (kind, y, x, payload) in enumerate(items):
                if kind == "line" and (payload["text"] == start_heading
                                        or payload["text"].startswith(start_heading[:18])):
                    items = items[i:]
                    break
        for kind, y, x, payload in items:
            if kind == "image":
                if cur is not None:
                    cur["figure_images"].append(
                        {"page": pn, "bbox": payload["bbox"]})
                else:
                    pending_images.append(
                        {"page": pn, "bbox": payload["bbox"]})
                continue
            text = payload["text"]
            if (not text or NOISE_RE.match(text)
                    or text.startswith("The answers for this Quiz")
                    or text.startswith("The answers for this quiz")):
                continue
            if text.startswith("Answer Explanations") or text == "Answers":
                finalize_frq(cur, questions)
                return questions, pn
            if stop_heading and (text == stop_heading
                                 or text.startswith(stop_heading[:22])):
                finalize_frq(cur, questions)
                return questions, pn
            if text in ("Free-Response Questions", "Free-Response Question",
                        "Section II: Free-Response", "Section II"):
                in_body = True
                continue
            if text.startswith("Section II: Free-Response"):
                in_body = True
                continue
            if not in_body:
                if text == "Quiz" or text.startswith("Quiz ") or text.startswith("Practice Test"):
                    continue
                continue
            qm = Q_RE.match(text)
            if qm:
                num = int(qm.group(1))
                if num == expected and num <= 99:
                    finalize_frq(cur, questions)
                    cur = {"number": num, "section": "FRQ",
                           "stem_parts": [qm.group(2)] if qm.group(2) else [],
                           "figure_images": list(pending_images),
                           "page_start": pn, "page_end": pn}
                    pending_images = []
                    expected = num + 1
                    continue
            if cur is not None:
                cur["stem_parts"].append(text)
                cur["page_end"] = pn
    finalize_frq(cur, questions)
    return questions, end


def finalize_frq(cur, out):
    if not cur:
        return
    cur["stem"] = clean(" ".join(cur.pop("stem_parts")))
    out.append(cur)


def parse_answers(doc, start, end, has_mcq=True, quiz_no=None):
    """Return {'MCQ': {n: (letter, text)}, 'FRQ': {n: text}}."""
    lines = []
    for pn in range(start, end + 1):
        for kind, y, x, payload in page_items(doc[pn - 1]):
            if kind == "line":
                lines.append((pn, payload["text"]))
    mcq = {}
    frq = {}
    mode = "MCQ" if has_mcq else "FRQ"
    started = quiz_no is None
    cur_n = None
    buf = []

    def flush():
        nonlocal cur_n, buf
        if cur_n is not None and mode == "MCQ":
            text = clean(" ".join(buf))
            m = re.match(r"^\(([A-E])\)\s*(.*)$", text)
            if m:
                mcq[cur_n] = (m.group(1), m.group(2).strip())
        elif cur_n is not None and mode == "FRQ":
            frq[cur_n] = clean(" ".join(buf))
        cur_n, buf = None, []

    for pn, text in lines:
        if not started:
            if quiz_no is not None and re.match(
                    r"^Quiz\s+%d\s*\(Pages?" % quiz_no, text):
                started = True
                continue
            continue
        if quiz_no is not None and re.match(r"^Quiz\s+\d+\s*\(Pages?", text):
            flush()
            break
        if re.match(r"^Answer Explanations", text):
            if has_mcq:
                mode = "MCQ"
            continue
        if re.match(r"^Section II", text):
            flush()
            mode = "FRQ"
            continue
        if re.match(r"^Section I$", text):
            flush()
            mode = "MCQ"
            continue
        if text == "Multiple-Choice":
            flush()
            mode = "MCQ"
            continue
        if text == "Free-Response Questions":
            flush()
            mode = "FRQ"
            continue
        if mode == "MCQ":
            m = re.match(r"^(\d{1,2})\.\s*\(([A-E])\)\s*(.*)$", text)
            if m:
                flush()
                cur_n = int(m.group(1))
                buf = [f"({m.group(2)}) {m.group(3)}".strip()]
                continue
            if cur_n is not None:
                buf.append(text)
        elif mode == "FRQ":
            m = re.match(r"^(\d{1,2})\.\s*(.*)$", text)
            if m:
                flush()
                cur_n = int(m.group(1))
                buf = [m.group(2)] if m.group(2) else []
                continue
            if cur_n is not None:
                buf.append(text)
    flush()
    # Strip the leading "(L)" from MCQ text.
    mcq = {n: (l, re.sub(r"^\([A-E]\)\s*", "", t).strip())
           for n, (l, t) in mcq.items()}
    return mcq, frq


def answer_block(doc, start, end, quiz_no=None):
    """Extract answer text for a quiz / test, split by MCQ and FRQ."""
    if quiz_no is not None:
        text = "\n".join(doc[p - 1].get_text("text") for p in range(start, end + 1))
        m = re.search(r"(?m)^Quiz\s+%d\s*\(Pages?.*?\)\s*$" % quiz_no, text)
        if not m:
            return {}, {}
    return parse_answers(doc, start, end)


def apply_manual_fixes(papers):
    """Known ebook defects that cannot be recovered from the text layer."""
    for paper in papers:
        if paper["paper_id"] != "statistics-barrons-2027-quiz-23":
            continue
        for q in paper["questions"]:
            if q["section"] != "MCQ" or q["number"] != 5:
                continue
            # The four choices are a single raster image labelled (A)-(D),
            # one row per choice. Split it so each option is usable.
            page = 388
            x0, x1 = 99.8, 512.2
            y0, y1 = 72.0, 375.0
            step = (y1 - y0) / 4.0
            q["options"] = {label: "[see image]" for label in "ABCD"}
            q["option_images"] = {}
            q["option_crops"] = {
                label: {"page": page,
                        "bbox": [x0, y0 + i * step, x1, y0 + (i + 1) * step]}
                for i, label in enumerate("ABCD")}
            # Drop the whole options strip from figures; keep the three
            # population distributions on p387.
            q["figure_images"] = [
                im for im in q.get("figure_images", [])
                if not (im["page"] == page and im["bbox"][1] < 80)
            ]


def main():
    fitz = load_fitz()
    doc = fitz.open(PDF_ABS)
    quizzes, practice, entries = toc_map(doc)
    os.makedirs(Q_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)

    papers = []
    # Quizzes.
    for qz in quizzes:
        n = qz["number"]
        paper_id = f"{BOOK_ID}-quiz-{n:02d}"
        start, end = qz["page_start"], qz["page_end"]
        stop_heading = qz.get("stop_heading")
        # Answer explanations are in the appendix; find the quiz block.
        ans_start = 711
        # Locate the answer heading page for this quiz.
        found_page = None
        for pn in range(711, 773):
            if re.search(r"(?m)^Quiz\s+%d\s*\(Pages?" % n,
                         doc[pn - 1].get_text("text")):
                found_page = pn
                break
        # Answer block ends at the next quiz heading or end of appendix.
        ans_end = 772
        if found_page:
            for pn in range(found_page + 1, 773):
                if re.search(r"(?m)^Quiz\s+\d+\s*\(Pages?", doc[pn - 1].get_text("text")):
                    ans_end = pn
                    break
            else:
                ans_end = 772
        has_mcq = "Multiple-Choice Questions" in "\n".join(
            doc[pn - 1].get_text("text") for pn in range(start, end + 1))
        mcq, frq = [], []
        if has_mcq:
            mcq, _ = parse_mcq(doc, start, end, paper_id, start_heading=f"Quiz {n}")
        # FRQ starts at the "Free-Response Questions" heading, or at the quiz
        # start when the quiz has no MCQ.
        frq_start = start
        for pn in range(start, end + 1):
            if "Free-Response Questions" in doc[pn - 1].get_text("text"):
                frq_start = pn
                break
        frq, _ = parse_frq(doc, frq_start, end, paper_id, frq_only=not has_mcq,
                           stop_heading=stop_heading,
                           start_heading=None if has_mcq else f"Quiz {n}")
        answers_mcq, answers_frq = ({}, {})
        if found_page:
            answers_mcq, answers_frq = parse_answers(doc, found_page, ans_end, has_mcq, n)
        for q in mcq:
            a = answers_mcq.get(q["number"])
            q["correct_answer"] = a[0] if a else None
            q["answer_text"] = a[1] if a else None
        for q in frq:
            q["correct_answer"] = None
            q["answer_text"] = answers_frq.get(q["number"])
        papers.append({
            "paper_id": paper_id,
            "kind": "quiz",
            "number": n,
            "unit_no": QUIZ_UNIT.get(n),
            "title": f"Barron's AP Statistics 2027 Quiz {n} — Unit {QUIZ_UNIT.get(n, 6)}",
            "chinese_title": f"巴朗 AP 统计 2027 Quiz {n}",
            "pdf_page_start": start,
            "pdf_page_end": end,
            "answer_page_start": found_page,
            "answer_page_end": ans_end,
            "has_mcq": has_mcq,
            "questions": mcq + frq,
        })

    # Diagnostic test.
    diag = {"paper_id": f"{BOOK_ID}-diagnostic", "kind": "diagnostic",
            "number": 0, "unit_no": None,
            "title": "Barron's AP Statistics 2027 Diagnostic Test",
            "chinese_title": "巴朗 AP 统计 2027 诊断测试",
            "pdf_page_start": 26, "pdf_page_end": 46,
            "answer_page_start": 47, "answer_page_end": 57,
            "has_mcq": True}
    dmcq, _ = parse_mcq(doc, 26, 43, diag["paper_id"], start_heading="Diagnostic Test")
    dfrq, _ = parse_frq(doc, 43, 46, diag["paper_id"])
    am, af = parse_answers(doc, 47, 57)
    for q in dmcq:
        a = am.get(q["number"])
        q["correct_answer"] = a[0] if a else None
        q["answer_text"] = a[1] if a else None
    for q in dfrq:
        q["correct_answer"] = None
        q["answer_text"] = af.get(q["number"])
    diag["questions"] = dmcq + dfrq
    papers.append(diag)

    # Practice tests.
    pt_names = {1: (549, 570, 571, 588), 2: (589, 606, 607, 618),
                3: (619, 643, 644, 661), 4: (662, 684, 685, 702)}
    for n, (s, qend, as_, aend) in pt_names.items():
        paper_id = f"{BOOK_ID}-pt{n}"
        pmcq, _ = parse_mcq(doc, s, qend, paper_id, start_heading=f"Practice Test {n}")
        pfrq, _ = parse_frq(doc, qend - 1, qend, paper_id)
        # Find Section II page precisely: parse FRQ from the page containing
        # "Section II: Free-Response" in the question range.
        for pn in range(s, qend + 1):
            if "Section II" in doc[pn - 1].get_text("text"):
                pfrq, _ = parse_frq(doc, pn, qend, paper_id,
                                    stop_heading="Answer Explanations")
                break
        am, af = parse_answers(doc, as_, aend)
        for q in pmcq:
            a = am.get(q["number"])
            q["correct_answer"] = a[0] if a else None
            q["answer_text"] = a[1] if a else None
        for q in pfrq:
            q["correct_answer"] = None
            q["answer_text"] = af.get(q["number"])
        papers.append({
            "paper_id": paper_id, "kind": "practice_test", "number": n,
            "unit_no": None,
            "title": f"Barron's AP Statistics 2027 Practice Test {n}",
            "chinese_title": f"巴朗 AP 统计 2027 模拟卷 {n}",
            "pdf_page_start": s, "pdf_page_end": qend,
            "answer_page_start": as_, "answer_page_end": aend,
            "has_mcq": True, "questions": pmcq + pfrq,
        })

    apply_manual_fixes(papers)

    # Fill IDs, context, and image attachment metadata.
    for paper in papers:
        seq = 0
        for q in paper["questions"]:
            seq += 1
            q["question_id"] = f"{paper['paper_id']}-{seq:03d}"
            q.setdefault("context", "")
            q.setdefault("answer_text", None)
            q["source_pages"] = [q["page_start"], q["page_end"]]
            q.pop("_last_y", None)
            q.setdefault("option_images", {})
            q.setdefault("figure_images", [])
        paper["question_count"] = len(paper["questions"])
        paper["mcq_count"] = sum(1 for q in paper["questions"] if q["section"] == "MCQ")
        paper["frq_count"] = sum(1 for q in paper["questions"] if q["section"] == "FRQ")
        with open(os.path.join(Q_DIR, paper["paper_id"] + ".json"), "w",
                  encoding="utf-8") as f:
            json.dump(paper, f, ensure_ascii=False, indent=1)

    with open(os.path.join(OUT_DIR, "questions_all.json"), "w", encoding="utf-8") as f:
        json.dump({"pdf": PDF_REL, "papers": papers}, f, ensure_ascii=False, indent=1)

    # Report.
    lines = ["# Barron's AP Statistics 2027 题目解析报告", "",
             f"- PDF: `{PDF_REL}`", f"- 试卷数: {len(papers)}", ""]
    lines += ["| paper_id | type | pages | MCQ | FRQ | MCQ answers | FRQ answers |",
              "|---|---|---:|---:|---:|---:|---:|"]
    for p in papers:
        mcq = [q for q in p["questions"] if q["section"] == "MCQ"]
        frq = [q for q in p["questions"] if q["section"] == "FRQ"]
        lines.append(f"| {p['paper_id']} | {p['kind']} | {p['pdf_page_start']}-{p['pdf_page_end']} "
                     f"| {len(mcq)} | {len(frq)} | "
                     f"{sum(1 for q in mcq if q['correct_answer'])} | "
                     f"{sum(1 for q in frq if q['answer_text'])} |")
    lines += ["", "## 缺答案 MCQ", ""]
    for p in papers:
        miss = [q["number"] for q in p["questions"]
                if q["section"] == "MCQ" and not q["correct_answer"]]
        if miss:
            lines.append(f"- {p['paper_id']}: {miss}")
    lines += ["", "## 缺解析 FRQ", ""]
    for p in papers:
        miss = [q["number"] for q in p["questions"]
                if q["section"] == "FRQ" and not q["answer_text"]]
        if miss:
            lines.append(f"- {p['paper_id']}: {miss}")
    open(REPORT, "w", encoding="utf-8").write("\n".join(lines) + "\n")

    total = sum(len(p["questions"]) for p in papers)
    print(f"papers={len(papers)} questions={total}")
    for p in papers:
        print(f"  {p['paper_id']:<42} MCQ {p['mcq_count']:>3} FRQ {p['frq_count']:>2} "
              f"p{p['pdf_page_start']}-{p['pdf_page_end']}")
    print("wrote", OUT_DIR)


if __name__ == "__main__":
    main()
