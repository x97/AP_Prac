#!/usr/bin/env python3
"""Parse the 2026 AP Psychology PDF into reviewable JSON + cropped assets.

This is intentionally a source-specific parser, not a generic PDF importer.
It does not write to psychology_exam.db. The first delivery is a dry run:
JSON, a QA report, and cropped figures/tables only.

Usage:
    python3 _tools/parse_ap_psych_2026.py
"""

from __future__ import annotations

import json
import re
import statistics
from collections import Counter
from pathlib import Path
from typing import Any

import fitz
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "assets/psychology/papers/2026/2026 AP心理学.pdf"
JSON_OUT = ROOT / "data/content/psychology/extraction/psychology-ap-2026.json"
REPORT_OUT = ROOT / "data/content/psychology/reports/psychology-ap-2026_report.md"
ASSET_DIR = ROOT / "assets/psychology/images/ap2026"

PAPER_ID = "psychology-ap-2026"
SOURCE_ID = "psychology-ap-2026-pdf"
SUBJECT_ID = "psychology"
PAGE_W = 595.92
PAGE_H = 842.88

MCQ_PAGES = range(0, 29)   # PDF pages 1-29
FRQ_PAGES = range(29, 49)  # PDF pages 30-49

PAGE_HEADERS = {"AP Psychology", "Section I", "Section II"}

# Question-specific context anchors. Everything before this anchor is the
# readable scenario/lead-in; the chart/table itself is cropped as an asset
# instead of being duplicated as text.
CONTEXT_CUTOFF: dict[int, tuple[int, float]] = {
    9: (3, 160.0),
    18: (7, 262.0),
    31: (12, 168.0),
    53: (20, 238.0),
    60: (22, 333.0),
    61: (23, 152.0),
    62: (24, 152.0),
    66: (25, 292.0),
    72: (27, 263.0),
    73: (28, 263.0),
    74: (29, 263.0),
}

# Crops use PDF point coordinates. Each generated file is listed here so the
# JSON, report, and future DB import all refer to the same immutable crop.
SHARED_ASSET_DESCRIPTIONS = {
    "q72_74_offers_to_help_chart.png": (
        "The data for the 2 bars are as follows: Email Addresses Visible: "
        "12 participants; Email Addresses Not Visible: 18 participants."
    ),
}

ASSET_SPECS: dict[int, list[dict[str, Any]]] = {
    9: [
        {
            "asset_id": "psychology-2026-mcq-009-fig-1",
            "kind": "figure",
            "option_label": None,
            "page": 3,
            "rect": (28.0, 112.0, 280.0, 354.0),
            "filename": "q09_figure_1_first_test.png",
            "description": (
                "Figure 1. Distribution of Learned Helplessness Scores, First Test — "
                "The Number of Participants data for the 9 bars are as follows: "
                "2: 2 participants; 3: 1 participant; 4: 2 participants; "
                "7: 1 participant; 8: 2 participants; 9: 1 participant; "
                "10: 2 participants; 11: 2 participants; 12: 2 participants."
            ),
            "alt_text": "Figure 1. Distribution of learned helplessness scores, first test.",
        },
        {
            "asset_id": "psychology-2026-mcq-009-fig-2",
            "kind": "figure",
            "option_label": None,
            "page": 3,
            "rect": (28.0, 565.0, 280.0, 812.0),
            "filename": "q09_figure_2_retest.png",
            "description": (
                "Figure 2. Distribution of Learned Helplessness Scores, Retest — "
                "The Number of Participants data for the 10 bars are as follows: "
                "2: 1 participant; 3: 1 participant; 4: 1 participant; "
                "5: 1 participant; 6: 3 participants; 7: 3 participants; "
                "8: 2 participants; 9: 1 participant; 10: 1 participant; "
                "11: 1 participant."
            ),
            "alt_text": "Figure 2. Distribution of learned helplessness scores, retest.",
        }
    ],
    18: [
        {
            "asset_id": "psychology-2026-mcq-018-fig-1",
            "kind": "figure",
            "option_label": None,
            "page": 7,
            "rect": (27.0, 250.0, 282.0, 474.0),
            "filename": "q18_attitude_before_after_mural.png",
            "description": (
                "For each data category, the following bars are shown: AHS students’ "
                "attitude toward BHS students; BHS students’ attitude toward AHS students. "
                "All values are approximate.\n\n"
                "The Mean Attitude Score data for the 2 categories are as follows:\n"
                "Before Painting Mural: AHS students’ attitude toward BHS students: 2.3; "
                "BHS students’ attitude toward AHS students: 3.1.\n"
                "After Painting Mural: AHS students’ attitude toward BHS students: 8.5; "
                "BHS students’ attitude toward AHS students: 3.0."
            ),
            "alt_text": "Bar graph of mean attitude scores before and after painting the mural.",
        }
    ],
    31: [
        {
            "asset_id": "psychology-2026-mcq-031-fig-1",
            "kind": "figure",
            "option_label": None,
            "page": 12,
            "rect": (20.0, 155.0, 282.0, 378.0),
            "filename": "q31_hypnosis_anxiety_scatterplot.png",
            "description": (
                "The graph has 35 data points. The data points are in a linear pattern "
                "trending down from left to right."
            ),
            "alt_text": "Scatterplot of hypnosis session length and anxiety rating.",
        }
    ],
    46: [
        {
            "asset_id": "psychology-2026-mcq-046-option-a",
            "kind": "option",
            "option_label": "A",
            "page": 17,
            "rect": (286.0, 120.0, 572.0, 294.0),
            "filename": "q46_option_a.png",
            "description": (
                "All values are approximate. The Mean Score data for the 2 bars are as "
                "follows: Mindset: 26; Academic Behaviors: 14."
            ),
            "alt_text": "Bar graph: Mindset 26, Academic Behaviors 14.",
        },
        {
            "asset_id": "psychology-2026-mcq-046-option-b",
            "kind": "option",
            "option_label": "B",
            "page": 17,
            "rect": (286.0, 396.0, 572.0, 571.0),
            "filename": "q46_option_b.png",
            "description": (
                "All values are approximate. The Mean Score data for the 2 bars are as "
                "follows: Mindset: 14; Academic Behaviors: 26."
            ),
            "alt_text": "Bar graph: Mindset 14, Academic Behaviors 26.",
        },
        {
            "asset_id": "psychology-2026-mcq-046-option-c",
            "kind": "option",
            "option_label": "C",
            "page": 17,
            "rect": (286.0, 676.0, 572.0, 841.0),
            "filename": "q46_option_c.png",
            "description": (
                "The scatterplot has 17 data points. The data points are widely distributed "
                "with no particular pattern."
            ),
            "alt_text": "Scatterplot with 17 widely distributed data points.",
        },
        {
            "asset_id": "psychology-2026-mcq-046-option-d",
            "kind": "option",
            "option_label": "D",
            "page": 18,
            "rect": (286.0, 84.0, 572.0, 260.0),
            "filename": "q46_option_d.png",
            "description": (
                "The scatterplot has 15 data points. The data points are in a linear pattern "
                "trending up from left to right."
            ),
            "alt_text": "Scatterplot with 15 data points in a linear upward pattern.",
        },
    ],
    53: [
        {
            "asset_id": "psychology-2026-mcq-053-table-1",
            "kind": "table",
            "option_label": None,
            "page": 20,
            "rect": (27.0, 232.0, 282.0, 452.0),
            "filename": "q53_group_demographics_and_completion_time.png",
            "alt_text": "Table 1 group demographics and Table 2 mean completion times.",
        }
    ],
    60: [
        {
            "asset_id": "psychology-2026-mcq-060-table-1",
            "kind": "table",
            "option_label": None,
            "page": 22,
            "rect": (27.0, 325.0, 282.0, 612.0),
            "filename": "q60_62_withdrawal_symptom_table.png",
            "alt_text": "Table of withdrawal-symptom severity ratings at 24, 48, and 96 hours.",
        }
    ],
    61: [
        {
            "asset_id": "psychology-2026-mcq-061-table-1",
            "kind": "table",
            "option_label": None,
            "page": 22,
            "rect": (27.0, 325.0, 282.0, 612.0),
            "filename": "q60_62_withdrawal_symptom_table.png",
            "alt_text": "Table of withdrawal-symptom severity ratings at 24, 48, and 96 hours.",
        }
    ],
    62: [
        {
            "asset_id": "psychology-2026-mcq-062-table-1",
            "kind": "table",
            "option_label": None,
            "page": 22,
            "rect": (27.0, 325.0, 282.0, 612.0),
            "filename": "q60_62_withdrawal_symptom_table.png",
            "alt_text": "Table of withdrawal-symptom severity ratings at 24, 48, and 96 hours.",
        }
    ],
    66: [
        {
            "asset_id": "psychology-2026-mcq-066-fig-1",
            "kind": "figure",
            "option_label": None,
            "page": 25,
            "rect": (15.0, 275.0, 282.0, 447.0),
            "filename": "q66_mental_health_curves.png",
            "description": (
                "For the first normal curve: the curve is a solid graph line; the peak of "
                "the curve is at the line between Languishing and Moderate Mental Health. "
                "For the second normal curve: the curve is a dashed graph line; the curve "
                "is shifted to the right of the first curve such that the peak is in the "
                "center of the Moderate Mental Health section."
            ),
            "alt_text": "Normal curves showing a shift toward well-being after intervention.",
        }
    ],
    72: [
        {
            "asset_id": "psychology-2026-mcq-072-fig-1",
            "kind": "figure",
            "option_label": None,
            "page": 27,
            "rect": (15.0, 250.0, 282.0, 489.0),
            "filename": "q72_74_offers_to_help_chart.png",
            "description": (
                "The data for the 2 bars are as follows: Email Addresses Visible: "
                "12 participants; Email Addresses Not Visible: 18 participants."
            ),
            "alt_text": "Bar graph of offers to help with and without visible email addresses.",
        }
    ],
    73: [
        {
            "asset_id": "psychology-2026-mcq-073-fig-1",
            "kind": "figure",
            "option_label": None,
            "page": 27,
            "rect": (15.0, 250.0, 282.0, 489.0),
            "filename": "q72_74_offers_to_help_chart.png",
            "alt_text": "Bar graph of offers to help with and without visible email addresses.",
        }
    ],
    74: [
        {
            "asset_id": "psychology-2026-mcq-074-fig-1",
            "kind": "figure",
            "option_label": None,
            "page": 27,
            "rect": (15.0, 250.0, 282.0, 489.0),
            "filename": "q72_74_offers_to_help_chart.png",
            "alt_text": "Bar graph of offers to help with and without visible email addresses.",
        }
    ],
}


def block_text(block: dict[str, Any]) -> str:
    lines: list[str] = []
    for line in block.get("lines", []):
        text = "".join(span.get("text", "") for span in line.get("spans", []))
        lines.append(text)
    return "\n".join(lines)


def normalize(text: str) -> str:
    text = text.replace(" ", " ").replace("­", "")
    text = text.replace("-\n", "-")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    return " ".join(line for line in lines if line).strip()


def join_blocks(blocks: list[dict[str, Any]]) -> str:
    parts = [normalize(block["text"]) for block in blocks]
    return "\n\n".join(part for part in parts if part)


def load_blocks(doc: fitz.Document) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for page_index in range(len(doc)):
        page = doc[page_index]
        for block in page.get_text("dict")["blocks"]:
            if block.get("type") != 0:
                continue
            text = block_text(block)
            if not text.strip():
                continue
            rect = block["bbox"]
            blocks.append(
                {
                    "page": page_index + 1,
                    "x0": rect[0],
                    "y0": rect[1],
                    "x1": rect[2],
                    "y1": rect[3],
                    "text": text,
                }
            )
    blocks.sort(key=lambda item: (item["page"], item["y0"], item["x0"]))
    return blocks


def is_page_header(text: str) -> bool:
    return normalize(text) in PAGE_HEADERS


def header_info(text: str) -> tuple[int, str] | None:
    joined = normalize(text)
    match = re.match(r"Question\s+(\d+)\s*正确答案[：:]\s*([A-E])", joined)
    if not match:
        return None
    return int(match.group(1)), match.group(2)


def option_info(block: dict[str, Any]) -> tuple[str, str] | None:
    lines = [line.strip() for line in block["text"].split("\n")]
    if not lines:
        return None
    first = lines[0].strip()
    if first in set("ABCDE") and len(first) == 1:
        return first, normalize("\n".join(lines[1:]))
    match = re.match(r"^([A-E])[.)]\s*(.*)$", first, re.S)
    if match:
        rest = [match.group(2)] + lines[1:]
        return match.group(1), normalize("\n".join(rest))
    return None


def split_single_column(blocks: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split a one-column question into stem and context at the question sentence."""
    if not blocks:
        return [], []
    for index in range(len(blocks) - 1, -1, -1):
        text = blocks[index]["text"]
        match = re.search(
            r"(?is)((?:Which of the following|What|How|Why|When|Where|Who)\b[^?]*\?)\s*$",
            text,
        )
        if match and match.start() > 0:
            prefix = text[: match.start()].strip()
            suffix = match.group(1).strip()
            context = blocks[:index]
            if prefix:
                context = context + [{**blocks[index], "text": prefix}]
            stem = [{**blocks[index], "text": suffix}]
            return stem, context
        if match and match.start() == 0:
            return [blocks[index]], blocks[:index]
    return blocks, []


def apply_context_cutoff(blocks: list[dict[str, Any]], number: int) -> list[dict[str, Any]]:
    cutoff = CONTEXT_CUTOFF.get(number)
    if not cutoff:
        return blocks
    page, y = cutoff
    return [block for block in blocks if (block["page"], block["y0"]) < (page, y)]


def parse_mcq(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    headers: list[tuple[int, int, str]] = []
    for index, block in enumerate(blocks):
        if block["page"] > 29:
            continue
        info = header_info(block["text"])
        if info:
            headers.append((index, info[0], info[1]))

    questions: list[dict[str, Any]] = []
    for position, (start, number, answer) in enumerate(headers):
        end = headers[position + 1][0] if position + 1 < len(headers) else len(blocks)
        segment = [
            block
            for block in blocks[start + 1 : end]
            if block["page"] <= 29 and not is_page_header(block["text"])
        ]
        option_rows: list[dict[str, Any]] = []
        for index, block in enumerate(segment):
            parsed = option_info(block)
            if parsed:
                option_rows.append(
                    {"label": parsed[0], "rest": parsed[1], "index": index, "block": block}
                )

        if len(option_rows) != 4:
            raise ValueError(f"Q{number}: expected 4 options, got {len(option_rows)}")
        labels = [row["label"] for row in option_rows]
        if labels != list("ABCD"):
            raise ValueError(f"Q{number}: unexpected option labels {labels}")

        first_option_index = option_rows[0]["index"]
        right_has_options = any(row["block"]["x0"] >= 285 for row in option_rows)
        if right_has_options:
            stem_blocks = [
                block
                for block in segment[:first_option_index]
                if block["x0"] >= 285
            ]
            context_blocks = [block for block in segment if block["x0"] < 285]
        else:
            stem_blocks, context_blocks = split_single_column(segment[:first_option_index])

        context_blocks = apply_context_cutoff(context_blocks, number)
        stem = join_blocks(stem_blocks)
        context = join_blocks(context_blocks)

        options: list[dict[str, Any]] = []
        for row_index, row in enumerate(option_rows):
            next_index = (
                option_rows[row_index + 1]["index"]
                if row_index + 1 < len(option_rows)
                else len(segment)
            )
            extra: list[str] = []
            if not row["rest"]:
                for block in segment[row["index"] + 1 : next_index]:
                    same_column = (
                        block["x0"] >= 285 if right_has_options else block["x0"] < 285
                    )
                    if same_column and normalize(block["text"]):
                        extra.append(normalize(block["text"]))
            content = row["rest"] or " ".join(extra)
            if number == 46:
                content = f"See graph {row['label']}."
            options.append(
                {
                    "label": row["label"],
                    "content": content,
                    "sort_order": "ABCD".index(row["label"]) + 1,
                    "is_correct": row["label"] == answer,
                    "explanation": None,
                    "ai_explanation": None,
                    "figure_alt": " ".join(extra) if number == 46 else None,
                }
            )

        assets: list[dict[str, Any]] = []
        for spec in ASSET_SPECS.get(number, []):
            asset = {
                "asset_id": spec["asset_id"],
                "kind": spec["kind"],
                "option_label": spec["option_label"],
                "path": str(
                    (ASSET_DIR / spec["filename"]).relative_to(ROOT)
                ),
                "page": spec["page"],
                "bbox": [
                    round(spec["rect"][0] / PAGE_W, 5),
                    round(spec["rect"][1] / PAGE_H, 5),
                    round(spec["rect"][2] / PAGE_W, 5),
                    round(spec["rect"][3] / PAGE_H, 5),
                ],
                "alt_text": spec.get("alt_text"),
                "description": spec.get("description")
                or SHARED_ASSET_DESCRIPTIONS.get(spec["filename"]),
            }
            assets.append(asset)

        page_start = min(block["page"] for block in segment)
        page_end = max(block["page"] for block in segment)
        questions.append(
            {
                "question_id": f"psychology-2026-mcq-{number:03d}",
                "section": "MCQ",
                "number": number,
                "display_number": number,
                "stem": stem,
                "context": context or None,
                "page_start": page_start,
                "page_end": page_end,
                "correct_answer": answer,
                "answer_text": None,
                "answer_source": "source_pdf_answer_key",
                "answer_confidence": "source_provided_not_independently_verified",
                "options": options,
                "assets": assets,
                "status": "ready",
                "notes": [
                    "正确答案 taken from the PDF answer annotation.",
                    "No explanation is printed in the source; options.explanation remains NULL.",
                ],
            }
        )

    if len(questions) != 75:
        raise ValueError(f"expected 75 MCQ questions, got {len(questions)}")
    return questions


def right_blocks(blocks: list[dict[str, Any]], page: int) -> list[dict[str, Any]]:
    return [
        block
        for block in blocks
        if block["page"] == page and block["x0"] >= 285 and not is_page_header(block["text"])
    ]


def left_blocks(blocks: list[dict[str, Any]], page: int) -> list[dict[str, Any]]:
    return [
        block
        for block in blocks
        if block["page"] == page and block["x0"] < 285 and not is_page_header(block["text"])
    ]


def get_block(blocks: list[dict[str, Any]], prefix: str) -> dict[str, Any]:
    for block in blocks:
        if normalize(block["text"]).startswith(prefix):
            return block
    raise KeyError(prefix)


Q1_TABLE_1 = """Table 1. Type of Twin Pair
Type of Twin Pair | Number of Pairs
Monozygotic (identical) | 78
Dizygotic (nonidentical) | 31"""

Q1_TABLE_2 = """Table 2. Gender of Twin Pair
Gender | Monozygotic (identical) | Dizygotic (nonidentical)
Male twin pairs | 26 | 8
Female twin pairs | 50 | 12
Mixed-gender twin pairs | 0 | 13"""

Q1_TABLE_3 = """Table 3. Race/Ethnicity of Twin Pair
Race/Ethnicity | Number of Twin Pairs
White | 58
Hispanic | 28
Asian | 15
African American | 5
American Indian | 2
Pacific Islander | 1"""

Q1_TABLE_4 = """Table 4. Median Pain Thresholds and Sensitivities Across All Twin Pairs
Pain Test | Pre-Medication Phase | During Saltwater Infusion (Placebo) | During Opioid Medication Infusion
Heat pain threshold | 48.4°C/119.12°F | 48.5°C/119.3°F | 49.6°C/121.3°F
Cold pain threshold | 8.1 seconds | 8.0 seconds | 14.3 seconds
Cold pain tolerance | 16.2 seconds | 15.6 seconds | 31.2 seconds"""


def q1_source(blocks: list[dict[str, Any]]) -> str:
    page30 = left_blocks(blocks, 30)
    page31 = left_blocks(blocks, 31)
    page32 = left_blocks(blocks, 32)

    intro_heading = normalize(get_block(page30, "Introduction")["text"])
    intro = normalize(get_block(page30, "In this study")["text"])
    participants_heading = normalize(get_block(page30, "Participants")["text"])
    participants_a = normalize(get_block(page30, "The study took place")["text"])
    participants_b = normalize(get_block(page30, "including monozygotic")["text"])

    before_agree = normalize(get_block(page31, "Before agreeing")["text"])
    method_heading = normalize(get_block(page31, "Method")["text"])
    method_1 = normalize(get_block(page31, "Researchers conducted")["text"])
    method_2 = normalize(get_block(page31, "The study consisted")["text"])
    method_3 = normalize(get_block(page31, "During the pre-medication phase")["text"])
    method_4 = normalize(get_block(page31, "To assess heat pain")["text"])
    method_5 = normalize(get_block(page31, "To assess cold pain")["text"])
    method_6 = normalize(get_block(page31, "During the infusion phase")["text"])
    results_heading = normalize(get_block(page31, "Results and Discussion")["text"])
    results_1 = normalize(get_block(page31, "During the pre-medication phase, the median")["text"])

    results_2 = normalize(get_block(page32, "During the opioid medication infusion")["text"])
    results_3 = normalize(get_block(page32, "The participants’ reported pain")["text"])
    genetics = normalize(get_block(page32, "Because identical twins")["text"])
    citation = normalize(get_block(page32, "Angst, M. S.")["text"])

    parts = [
        intro_heading,
        intro,
        participants_heading,
        f"{participants_a} {participants_b}",
        Q1_TABLE_1,
        Q1_TABLE_2,
        Q1_TABLE_3,
        before_agree,
        method_heading,
        method_1,
        method_2,
        method_3,
        method_4,
        method_5,
        method_6,
        results_heading,
        results_1,
        results_2,
        results_3,
        Q1_TABLE_4,
        genetics,
        citation,
    ]
    return "\n\n".join(part for part in parts if part)


def parse_q1(blocks: list[dict[str, Any]]) -> dict[str, Any]:
    instruction = normalize(
        get_block(right_blocks(blocks, 30), "Your response to the question")["text"]
    )
    prompts: dict[str, str] = {}
    responses: dict[str, str] = {}
    for label, page in zip("ABCDEF", [30, 33, 36, 39, 42, 45]):
        page_right = right_blocks(blocks, page)
        prompt_blocks = [
            block
            for block in page_right
            if block["y0"] >= 90 and block["x0"] >= 300
        ]
        if not prompt_blocks:
            raise ValueError(f"Q1{label}: no prompt blocks")
        prompt_end = max(block["y1"] for block in prompt_blocks)
        response_blocks = [
            block
            for block in page_right
            if block["x0"] <= 295 and block["y0"] > prompt_end
        ]
        prompts[label] = " ".join(
            normalize(block["text"]) for block in prompt_blocks if normalize(block["text"])
        )
        responses[label] = join_blocks(response_blocks)
        if not responses[label]:
            raise ValueError(f"Q1{label}: no sample response")

    stem_parts = [
        "Using the source provided, respond to all parts of the question.",
        instruction,
        *[prompts[label] for label in "ABCDEF"],
    ]
    answer_parts = [
        "Sample responses from the source PDF. These are not official scoring guidelines.",
        *[responses[label] for label in "ABCDEF"],
    ]
    return {
        "question_id": "psychology-2026-frq-001",
        "section": "FRQ",
        "number": 1,
        "display_number": 1,
        "question_type": "AAQ",
        "stem": "\n\n".join(part for part in stem_parts if part),
        "context": q1_source(blocks),
        "page_start": 30,
        "page_end": 47,
        "correct_answer": None,
        "answer_text": "\n\n".join(answer_parts),
        "answer_source": "source_pdf_sample_response",
        "answer_confidence": "sample_response_only_no_rubric",
        "options": [],
        "assets": [],
        "frq_parts": [prompts[label] for label in "ABCDEF"],
        "frq_part_pages": {"A": 30, "B": 33, "C": 36, "D": 39, "E": 42, "F": 45},
        "frq_sample_response_pages": {"A": 30, "B": 33, "C": 36, "D": 39, "E": 42, "F": 45},
        "source_pages": [30, 32],
        "status": "ready_with_sample_responses_no_rubric",
        "notes": [
            "The PDF repeats the full source material for each part (1a-1f).",
            "Only sample responses are provided; no scoring guidelines or rubric points are included.",
            "Tables 1-4 were reconstructed as text from the PDF; values were checked against the rendered table.",
            "Footnote markers 1-3 appear in the source, but the footnote text is not included in this PDF.",
        ],
    }


def format_ebq_prompt(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\bii\.", "\nii.", text)
    text = re.sub(r"^([A-C])\.\s*i\.", r"\1.\ni.", text)
    return text


def parse_q2(blocks: list[dict[str, Any]]) -> dict[str, Any]:
    page48_left = [
        block
        for block in left_blocks(blocks, 48)
        if block["y0"] < 250 and not normalize(block["text"]).startswith("Question")
    ]
    instructions = join_blocks(page48_left)
    instructions = instructions.replace(
        "Parenthetical Citation:\n\nFor example", "Parenthetical Citation: For example"
    )

    page48_right = right_blocks(blocks, 48)
    page49_right = right_blocks(blocks, 49)
    global_question = normalize(get_block(page48_right, "Using the sources provided")["text"])
    a_prompt = " ".join(
        normalize(block["text"])
        for block in page48_right
        if 78 <= block["y0"] <= 110 and block["x0"] >= 300
    )
    b_prompt_blocks = [
        block
        for block in page48_right
        if 360 <= block["y0"] <= 490 and block["x0"] >= 300
    ]
    c_prompt_blocks = [
        block
        for block in page49_right
        if 75 <= block["y0"] <= 220 and block["x0"] >= 300
    ]
    b_prompt = format_ebq_prompt(join_blocks(b_prompt_blocks))
    c_prompt = format_ebq_prompt(join_blocks(c_prompt_blocks))

    a_response = join_blocks(
        [block for block in page48_right if 115 <= block["y0"] <= 170 and block["x0"] <= 295]
    )
    b_response = join_blocks(
        [block for block in page48_right if block["y0"] >= 495 and block["x0"] <= 295]
    )
    c_response = join_blocks(
        [block for block in page49_right if block["y0"] >= 225 and block["x0"] <= 295]
    )
    for label, text in zip("ABC", [a_response, b_response, c_response]):
        if not text:
            raise ValueError(f"Q2{label}: no sample response")

    stem = "\n\n".join(
        part
        for part in [instructions, global_question, a_prompt, b_prompt, c_prompt]
        if part
    )
    answer_text = "\n\n".join(
        [
            "Sample responses from the source PDF. These are not official scoring guidelines.",
            a_response,
            b_response,
            c_response,
        ]
    )
    return {
        "question_id": "psychology-2026-frq-002",
        "section": "FRQ",
        "number": 2,
        "display_number": 2,
        "question_type": "EBQ",
        "stem": stem,
        "context": None,
        "page_start": 48,
        "page_end": 49,
        "correct_answer": None,
        "answer_text": answer_text,
        "answer_source": "source_pdf_sample_response",
        "answer_confidence": "sample_response_only_no_rubric_missing_sources",
        "options": [],
        "assets": [],
        "frq_parts": [a_prompt, b_prompt, c_prompt],
        "frq_part_pages": {"A": 48, "B": 48, "C": 49},
        "frq_sample_response_pages": {"A": 48, "B": 48, "C": 49},
        "source_pages": [],
        "status": "blocked_missing_sources",
        "notes": [
            "Sources 1-3 are referenced by the question and sample responses but are NOT present in this PDF.",
            "Q2 cannot be answered as a standalone question until the three sources are supplied.",
            "No scoring guidelines or rubric points are included.",
        ],
    }


def crop_asset(doc: fitz.Document, spec: dict[str, Any]) -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    output = ASSET_DIR / spec["filename"]
    if "parts" not in spec:
        rect = fitz.Rect(*spec["rect"])
        pix = doc[spec["page"] - 1].get_pixmap(
            matrix=fitz.Matrix(2, 2), clip=rect, alpha=False
        )
        pix.save(output)
        return

    images: list[Image.Image] = []
    for page, rect in spec["parts"]:
        pix = doc[page - 1].get_pixmap(
            matrix=fitz.Matrix(2, 2), clip=fitz.Rect(*rect), alpha=False
        )
        images.append(Image.frombytes("RGB", [pix.width, pix.height], pix.samples))
    if spec.get("combine") == "vertical":
        width = max(image.width for image in images)
        gap = 20
        height = sum(image.height for image in images) + gap * (len(images) - 1)
        combined = Image.new("RGB", (width, height), "white")
        offset = 0
        for image in images:
            combined.paste(image, (0, offset))
            offset += image.height + gap
        combined.save(output)
    else:
        raise ValueError(f"unsupported combine mode for {spec['filename']}")


def build_qa(
    mcq: list[dict[str, Any]],
    frq: list[dict[str, Any]],
    doc: fitz.Document,
) -> dict[str, Any]:
    option_counts = Counter(len(question["options"]) for question in mcq)
    answer_counts = Counter(question["correct_answer"] for question in mcq)
    cross_page = [
        {
            "number": question["number"],
            "pages": [question["page_start"], question["page_end"]],
        }
        for question in mcq
        if question["page_start"] != question["page_end"]
    ]
    empty_stems = [q["number"] for q in mcq if not q["stem"]]
    empty_options = [
        {"number": q["number"], "labels": [o["label"] for o in q["options"] if not o["content"]]}
        for q in mcq
        if any(not option["content"] for option in q["options"])
    ]
    answers_not_in_options = [
        q["number"]
        for q in mcq
        if q["correct_answer"] not in {option["label"] for option in q["options"]}
    ]
    figure_questions = sorted(
        q["number"] for q in mcq if q["assets"]
    )
    option_image_questions = sorted(
        q["number"]
        for q in mcq
        if any(asset["kind"] == "option" for asset in q["assets"])
    )
    explanation_count = sum(
        1
        for q in mcq
        for option in q["options"]
        if option.get("explanation")
    )
    return {
        "pdf_pages": len(doc),
        "mcq_pages": [1, 29],
        "frq_pages": [30, 49],
        "mcq_count": len(mcq),
        "frq_count": len(frq),
        "option_count_distribution": dict(sorted(option_counts.items())),
        "answer_distribution": dict(sorted(answer_counts.items())),
        "cross_page_questions": cross_page,
        "empty_stems": empty_stems,
        "empty_options": empty_options,
        "answers_not_in_options": answers_not_in_options,
        "explanation_count": explanation_count,
        "figure_questions": figure_questions,
        "option_image_questions": option_image_questions,
        "asset_count": sum(len(q["assets"]) for q in mcq),
        "unique_asset_files": len({a["path"] for q in mcq for a in q["assets"]}),
        "frq_rubric_count": 0,
        "frq_sample_response_questions": [q["number"] for q in frq if q["answer_text"]],
        "import_ready": False,
        "mcq_import_ready": True,
        "frq_import_ready": False,
        "blocking_issues": [
            "Q2 Sources 1-3 are missing from the PDF.",
            "FRQ scoring guidelines and rubric parts are missing from the PDF.",
        ],
        "q2_sources_present": False,
        "table_context_duplication": [],
        "warnings": [
            "The PDF prints answer letters (正确答案) but no MCQ explanations.",
            "The PDF prints sample FRQ responses but no scoring guidelines or rubric points.",
            "Q2's Sources 1-3 are not included in this PDF.",
            "The answer key is treated as source-provided, not independently verified as official.",
            "Q1 source tables 1-4 were reconstructed as text; values were visually checked.",
            "Q9, Q18, Q31, Q46, Q53, Q60-Q62, Q66, and Q72-Q74 have cropped figure/table assets.",
            "Q46 options are image-only; option text is a placeholder pointing to the image.",
        ],
    }


def write_report(
    paper: dict[str, Any],
    mcq: list[dict[str, Any]],
    frq: list[dict[str, Any]],
    qa: dict[str, Any],
) -> None:
    REPORT_OUT.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append("# 2026 AP Psychology PDF 解析报告")
    lines.append("")
    lines.append("## 结构地图")
    lines.append("")
    lines.append(f"- 源文件：`{paper['source_file']}`")
    lines.append(f"- PDF 页数：{qa['pdf_pages']}；有文本层；A4；双栏题目区 + 单栏直接题混合。")
    lines.append("- Section I（MCQ）：PDF 第 1–29 页，共 75 题；每题 4 个选项 A–D；答案字母直接印在题号行。")
    lines.append("- Section II（FRQ）：PDF 第 30–49 页，共 2 题；Q1 为 AAQ 六部分（A–F），Q2 为 EBQ 三部分（A–C）。")
    lines.append("- Q1 的源材料在每个子问页面重复出现；Q2 的 Sources 1–3 不在本 PDF 中。")
    lines.append("- 图表/表格题：Q9、Q18、Q31、Q46、Q53、Q60、Q61、Q62、Q66、Q72、Q73、Q74。")
    lines.append("")
    lines.append("## 数量与完整性")
    lines.append("")
    lines.append("| 项目 | 结果 |")
    lines.append("|---|---:|")
    lines.append(f"| MCQ | {qa['mcq_count']} |")
    lines.append(f"| FRQ | {qa['frq_count']} |")
    lines.append(f"| MCQ 选项数分布 | {qa['option_count_distribution']} |")
    lines.append(f"| 答案分布 | {qa['answer_distribution']} |")
    lines.append(f"| 有解析的选项 | {qa['explanation_count']} |")
    lines.append(f"| 题图/表格引用 | {qa['asset_count']} |")
    lines.append(f"| 唯一裁切文件 | {qa['unique_asset_files']} |")
    lines.append(f"| FRQ rubric | {qa['frq_rubric_count']} |")
    lines.append("")
    lines.append("## 入库状态")
    lines.append("")
    lines.append("- `import_ready = false`")
    lines.append("- `mcq_import_ready = true`")
    lines.append("- `frq_import_ready = false`")
    for issue in qa["blocking_issues"]:
        lines.append(f"- 阻塞项：{issue}")
    lines.append("")
    lines.append("## 跨页题")
    lines.append("")
    if qa["cross_page_questions"]:
        for item in qa["cross_page_questions"]:
            lines.append(f"- Q{item['number']}：PDF p{item['pages'][0]}–p{item['pages'][1]}")
    else:
        lines.append("- 无")
    lines.append("")
    lines.append("## 图表/表格裁切")
    lines.append("")
    for question in mcq:
        if not question["assets"]:
            continue
        labels = ", ".join(
            f"{asset['kind']}{' ' + asset['option_label'] if asset['option_label'] else ''}"
            for asset in question["assets"]
        )
        lines.append(
            f"- Q{question['number']}：{labels}；"
            f"`{question['assets'][0]['path']}`"
        )
    lines.append("")
    lines.append("## FRQ")
    lines.append("")
    for question in frq:
        lines.append(f"### Q{question['number']} ({question['question_type']})")
        lines.append("")
        lines.append(f"- 页码：p{question['page_start']}–p{question['page_end']}")
        lines.append(f"- 子问：{len(question['frq_parts'])} 个")
        lines.append(f"- 参考答案：已提取 sample response")
        lines.append("- 评分标准：源 PDF 未提供，`frq_rubrics` 为空")
        if question["number"] == 2:
            lines.append("- **缺源材料：Sources 1–3 不在本 PDF 中，Q2 目前不能独立作答。**")
        lines.append("")
    lines.append("## 异常与待复核")
    lines.append("")
    for warning in qa["warnings"]:
        lines.append(f"- {warning}")
    lines.append("")
    lines.append("## 产物")
    lines.append("")
    lines.append(f"- JSON：`{JSON_OUT.relative_to(ROOT)}`")
    lines.append(f"- 裁图目录：`{ASSET_DIR.relative_to(ROOT)}`")
    lines.append(f"- 解析脚本：`_tools/parse_ap_psych_2026.py`")
    lines.append("")
    lines.append("## 未执行")
    lines.append("")
    lines.append("- 未写入 `data/content/psychology/psychology_exam.db`。")
    lines.append("- 未构建或激活新的 content Release。")
    lines.append("- 未生成 AI 解析。")
    REPORT_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    doc = fitz.open(PDF)
    blocks = load_blocks(doc)
    mcq = parse_mcq(blocks)
    frq = [parse_q1(blocks), parse_q2(blocks)]
    for spec in ASSET_SPECS.values():
        for asset in spec:
            crop_asset(doc, asset)
    qa = build_qa(mcq, frq, doc)

    paper = {
        "paper_id": PAPER_ID,
        "year": 2026,
        "title": "AP Psychology 2026 (75 MCQs + 2 FRQs)",
        "chinese_title": "2026 年 AP 心理学（75 道选择题 + 2 道主观题）",
        "subject_id": SUBJECT_ID,
        "source_id": SOURCE_ID,
        "paper_type": "real_exam",
        "source_file": str(PDF.relative_to(ROOT)),
        "question_count": len(mcq) + len(frq),
        "import_ready": False,
        "mcq_import_ready": True,
        "frq_import_ready": False,
        "blocking_issues": [
            "Q2 Sources 1-3 are missing from the PDF.",
            "FRQ scoring guidelines and rubric parts are missing from the PDF.",
        ],
        "notes": [
            "Paper type is real_exam per the ingestion request; the PDF itself does not state an official administration.",
            "The PDF contains the MCQ answer letters and FRQ sample responses; it does not contain MCQs explanations or FRQ rubrics.",
        ],
    }
    payload = {
        "schema_version": 1,
        "generated_at": "2026-11-01",
        "paper": paper,
        "questions": mcq + frq,
        "frq_rubrics": [],
        "qa": qa,
    }
    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    write_report(paper, mcq, frq, qa)

    print(f"wrote {JSON_OUT}")
    print(f"wrote {REPORT_OUT}")
    print(f"assets: {qa['unique_asset_files']} files in {ASSET_DIR}")
    print(
        f"MCQ={qa['mcq_count']} FRQ={qa['frq_count']} "
        f"options={qa['option_count_distribution']} answers={qa['answer_distribution']}"
    )
    print(f"cross-page: {qa['cross_page_questions']}")
    print(f"warnings: {len(qa['warnings'])}")


if __name__ == "__main__":
    main()
