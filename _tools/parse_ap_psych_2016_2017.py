#!/usr/bin/env python3
"""Parse the released 2016 and 2017 AP Psychology exams (dry run).

This script intentionally does not write to psychology_exam.db. It produces
reviewable JSON, cropped figure/option assets, and a Markdown QA report for
each paper.

2016 has a text layer and is parsed with PyMuPDF. 2017 is image-only on the
released PDF, so the MCQ pages are rendered at 400 dpi and read with macOS
Vision OCR. The OCR output is checked against the printed answer key and the
question-descriptor table; every manual correction is listed in the report.

Usage:
    python3 _tools/parse_ap_psych_2016_2017.py
    python3 _tools/parse_ap_psych_2016_2017.py --ocr-dir /tmp/ap2017_mcq400_ocr

The optional --ocr-dir expects JSON files named 17.json .. 31.json produced by
_tools/vision_ocr.swift. If omitted, the script compiles the helper and OCRs
the pages itself (macOS only).
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import tempfile
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Optional

import fitz

ROOT = Path(__file__).resolve().parents[1]
EXTRACTION_DIR = ROOT / "data/content/psychology/extraction"
REPORT_DIR = ROOT / "data/content/psychology/reports"
IMAGE_ROOT = ROOT / "assets/psychology/images"
VISION_SWIFT = ROOT / "_tools/vision_ocr.swift"

PAGE_2016 = (603.3599853515625, 774.0)
PAGE_2017 = (594.9600219726562, 841.9199829101562)

ANSWER_SOURCE = "source_pdf_answer_key"
ANSWER_TEXT_2016 = "source_provided_verified_against_descriptor_key"
ANSWER_TEXT_2017 = "source_provided_manually_transcribed"

# ---------------------------------------------------------------------------
# 2016
# ---------------------------------------------------------------------------

PDF_2016 = ROOT / "assets/psychology/papers/2016/2016.pdf"
PAPER_ID_2016 = "psychology-ap-2016"
SOURCE_ID_2016 = "psychology-ap-2016-pdf"
MCQ_PAGES_2016 = range(15, 30)  # 0-based; PDF pages 16-30
ANSWER_KEY_PAGE_2016 = 51  # 0-based; PDF page 52
DESCRIPTOR_PAGES_2016 = (62, 63, 64)  # 0-based; PDF pages 63-65

# Context printed above the question number, reconstructed from the PDF's
# figure alt text. The alt text is source-provided, not generated.
FIG_2016_Q31 = (
    "The figure shows a bar graph with the horizontal axis labeled Exposure to "
    "Media Violence and the left vertical axis labeled Aggressive Behavior, in "
    "percent. There are three sets of two bars each, labeled Low, Medium, and "
    "High from left to right. The key indicates that one bar in each set "
    "represents elementary school girls, and the other bar in each set "
    "represents elementary school boys. The bars are as follows, from left to "
    "right. All numbers are approximate.\n"
    "Low exposure: elementary school girls, 22 percent; elementary school boys, "
    "50 percent.\n"
    "Medium exposure: elementary school girls, 30 percent; elementary school "
    "boys, 58 percent.\n"
    "High exposure: elementary school girls, 61 percent; elementary school boys, "
    "80 percent."
)
FIG_2016_Q64 = (
    "The figure shows a diagram of a presynaptic neuron toward the top of the "
    "figure and a postsynaptic neuron toward the bottom of the figure. The "
    "outside layer of the presynaptic neuron is labeled A. There are four "
    "circles containing black dots in the presynaptic neuron. One of these "
    "circles is labeled B. Toward the bottom of the presynaptic neuron, there "
    "are two sets of short, thick black lines that extend across the outside "
    "layer of the neuron. Inside the thick black lines are a few black dots. "
    "One set of black lines is labeled C. The bottom of the presynaptic neuron "
    "also has two areas where the outside layer circles in to the neuron. "
    "Inside these areas are several black dots. The area between the "
    "presynaptic neuron and the postsynaptic neuron is filled with more black "
    "dots; this area is labeled D. The top of the postsynaptic neuron has 5 "
    "small black boxes that extend across the outside layer of the neuron and "
    "have semicircular spaces at the top, which are approximately the size of "
    "the black dots. Two of these black boxes are labeled E."
)
FIG_2016_Q69 = (
    "The figure is an ambiguous image that can be perceived as either a duck or "
    "a rabbit."
)
FIG_2016_Q83 = (
    "The figure shows a scatterplot with the horizontal axis labeled "
    "Self-reported Sleep and the vertical axis labeled Happiness Scores. There "
    "are evenly spaced tick marks along each axis, numbered from zero through "
    "60. The points are arranged roughly in a cluster from the bottom left to "
    "the top right of the scatterplot."
)

CONTEXT_2016 = {
    # The figure descriptions in the PDF are accessibility alt text, not
    # printed question context. Keep only the printed lead-in for 64-65.
    64: "Questions 64-65 are based on the following.",
    65: "Questions 64-65 are based on the following.",
}

CORRECTIONS_2016 = {
    11: {
        "stem": (
            "What is the correct chronological order of the following "
            "perspectives of psychology, from past to present?\n"
            "I. Behaviorism\n"
            "II. Psychoanalysis\n"
            "III. Structuralism\n"
            "IV. Humanism"
        )
    },
    59: {"A": "Phenylketonuria (PKU)"},
    64: {"stem": "In the figure above, where do selective serotonin reuptake inhibitors (SSRIs) have their initial effect?"},
}

ASSETS_2016: dict[int, list[dict[str, Any]]] = {
    31: [
        {
            "asset_id": "psychology-2016-mcq-031-fig-1",
            "kind": "figure",
            "option_label": None,
            "page": 20,
            "rect": (66.0, 39.0, 270.0, 230.0),
            "filename": "q31_media_violence_bar_graph.png",
            "description": FIG_2016_Q31,
            "alt_text": "Bar graph of aggressive behavior by media-violence exposure and gender.",
        }
    ],
    64: [
        {
            "asset_id": "psychology-2016-mcq-064-fig-1",
            "kind": "figure",
            "option_label": None,
            "page": 24,
            "rect": (54.0, 64.0, 282.0, 371.0),
            "filename": "q64_65_neuron_synapse_diagram.png",
            "description": FIG_2016_Q64,
            "alt_text": "Diagram of a presynaptic neuron, synaptic gap, and postsynaptic neuron labeled A-E.",
        }
    ],
    65: [
        {
            "asset_id": "psychology-2016-mcq-065-fig-1",
            "kind": "figure",
            "option_label": None,
            "page": 24,
            "rect": (54.0, 64.0, 282.0, 371.0),
            "filename": "q64_65_neuron_synapse_diagram.png",
            "description": FIG_2016_Q64,
            "alt_text": "Diagram of a presynaptic neuron, synaptic gap, and postsynaptic neuron labeled A-E.",
        }
    ],
    69: [
        {
            "asset_id": "psychology-2016-mcq-069-fig-1",
            "kind": "figure",
            "option_label": None,
            "page": 25,
            "rect": (99.0, 39.0, 237.0, 137.0),
            "filename": "q69_duck_rabbit_illusion.png",
            "description": FIG_2016_Q69,
            "alt_text": "Ambiguous duck-rabbit line drawing.",
        }
    ],
    83: [
        {
            "asset_id": "psychology-2016-mcq-083-fig-1",
            "kind": "figure",
            "option_label": None,
            "page": 27,
            "rect": (331.0, 39.0, 558.0, 223.0),
            "filename": "q83_sleep_happiness_scatterplot.png",
            "description": FIG_2016_Q83,
            "alt_text": "Scatterplot of self-reported sleep and happiness scores.",
        }
    ],
}

# ---------------------------------------------------------------------------
# 2017
# ---------------------------------------------------------------------------

PDF_2017 = ROOT / "assets/psychology/papers/2017/2017.pdf"
PAPER_ID_2017 = "psychology-ap-2017"
SOURCE_ID_2017 = "psychology-ap-2017-pdf"
MCQ_PAGES_2017 = range(17, 32)  # 1-based PDF pages 17-31
ANSWER_KEY_PAGE_2017 = 53  # 1-based PDF page 53

# The answer-key heading is readable by OCR, but the table body is not. The
# letters below were read from page 53 and cross-checked against the Key column
# of the Question Descriptors table (pages 66-68).
ANSWER_2017_RAW = """
A C A C D A A E E C
D B E A D B E D A E
B B A A E D E B B A
B B B A C C A B B B
B E E D B E E D B B
A D E C E D C C E D
C B B C A E D B A A
D B E C E D A B B B
D D C A E D C B C B
E A B A B E B A A D
"""
ANSWER_2017 = {
    index: letter
    for index, letter in enumerate(ANSWER_2017_RAW.split(), start=1)
}

CONTEXT_2017 = {
    # Figure-only questions rely on the cropped image; do not duplicate the
    # image as a text description in the question context.
    11: (
        "Questions 11-12 refer to the following.\n\n"
        "3  4  5  5  7  7  7  8  8  10\n\n"
        "Ten participants in a treatment group were asked to rate their "
        "feelings of self worth on a scale of one to ten, with a value of ten "
        "indicating a very positive feeling of self-worth. The data for the "
        "participants are above."
    ),
    12: (
        "Questions 11-12 refer to the following.\n\n"
        "3  4  5  5  7  7  7  8  8  10\n\n"
        "Ten participants in a treatment group were asked to rate their "
        "feelings of self worth on a scale of one to ten, with a value of ten "
        "indicating a very positive feeling of self-worth. The data for the "
        "participants are above."
    ),
    96: (
        "Questions 96-97 are based on the following.\n\n"
        "A psychologist designed a study to test the effects of cell phone use "
        "on driving safety. Participants were randomly assigned either to drive "
        "an automobile simulator while talking to a friend on a cell phone or to "
        "drive a simulator without talking on a phone."
    ),
    97: (
        "Questions 96-97 are based on the following.\n\n"
        "A psychologist designed a study to test the effects of cell phone use "
        "on driving safety. Participants were randomly assigned either to drive "
        "an automobile simulator while talking to a friend on a cell phone or to "
        "drive a simulator without talking on a phone."
    ),
}

# OCR fixes where Vision dropped or mangled a whole line. Each entry is called
# out in the report; none of these change the printed question text.
CORRECTIONS_2017: dict[int, dict[str, Any]] = {
    15: {
        "B": (
            "a decrease in depth perception in illusions results from regular "
            "exposure to linear perspective"
        )
    },
    26: {"stem": "Which of the following conditions most often results from having an extra copy of chromosome 21?"},
    31: {
        "A": "punishment",
        "C": "negative reinforcement",
        "D": "differential reinforcement",
    },
    43: {
        "options": {
            "A": "See scatterplot A.",
            "B": "See scatterplot B.",
            "C": "See scatterplot C.",
            "D": "See scatterplot D.",
            "E": "See scatterplot E.",
        }
    },
    48: {"E": "Self-serving bias"},
    63: {
        "stem": (
            "Five-year-old Mary watches while her teacher pours equal amounts of "
            "water into two similar glasses. The liquid from one of the glasses "
            "is then poured into a tall, thin container, and Mary is asked which "
            "contains more—the original glass or the tall, thin container. She "
            "says the tall, thin container contains more liquid. According to "
            "Jean Piaget, this example illustrates a lack of"
        )
    },
    66: {"C": "Wish fulfillment"},
    74: {
        "C": "Conversion disorder",
        "D": "Tardive dyskinesia",
    },
    77: {
        "D": (
            "There is no statistically significant relationship between IQ "
            "scores and creativity."
        )
    },
    82: {"B": "proactive interference"},
    80: {"E": "Social loafing"},
    91: {
        "options": {
            "A": "specific phobia .. schizophrenia spectrum and other psychotic disorders",
            "B": "major depressive .. personality disorders",
            "C": "obsessive-compulsive .. depressive disorders",
            "D": "conversion .. personality disorders",
            "E": "posttraumatic stress .. trauma- and stressor-related disorders",
        }
    },
    92: {
        "options": {
            "A": "See graph A.",
            "B": "See graph B.",
            "C": "See graph C.",
            "D": "See graph D.",
            "E": "See graph E.",
        }
    },
    97: {
        "stem": "In the study, cell phone use can be described as",
        "options": {
            "A": "a dependent variable",
            "B": "an independent variable",
            "C": "a confounding variable",
            "D": "a random variable",
            "E": "an operational definition",
        },
    },
}

ASSETS_2017: dict[int, list[dict[str, Any]]] = {
    8: [
        {
            "asset_id": "psychology-2017-mcq-008-fig-1",
            "kind": "figure",
            "option_label": None,
            "page": 18,
            "rect": (70.0, 105.0, 282.0, 250.0),
            "filename": "q08_circle_slash_pattern.png",
            "description": (
                "A scattered array of circles and slashes. Some circles have a "
                "slash through them; others do not."
            ),
            "alt_text": "Scattered circles and slash marks used in a cancellation task.",
        }
    ],
    9: [
        {
            "asset_id": "psychology-2017-mcq-009-fig-1",
            "kind": "figure",
            "option_label": None,
            "page": 18,
            "rect": (318.0, 95.0, 532.0, 312.0),
            "filename": "q09_group_opinion_before_after.png",
            "description": (
                "Two opinion scales, before and after group discussion, with "
                "Group 1 and Group 2 positions marked."
            ),
            "alt_text": "Opinion-scale diagrams for two groups before and after discussion.",
        }
    ],
    22: [
        {
            "asset_id": "psychology-2017-mcq-022-fig-1",
            "kind": "figure",
            "option_label": None,
            "page": 20,
            "rect": (318.0, 318.0, 532.0, 558.0),
            "filename": "q22_maze_errors_line_graph.png",
            "description": (
                "Line graph of average number of errors over days for three "
                "groups. Group A had no food reward; Group B was regularly "
                "rewarded; Group C had no food reward until day 11."
            ),
            "alt_text": "Line graph of maze errors for three reward groups.",
        }
    ],
    43: [
        {
            "asset_id": "psychology-2017-mcq-043-option-a",
            "kind": "option",
            "option_label": "A",
            "page": 23,
            "rect": (322.0, 132.0, 532.0, 186.0),
            "filename": "q43_option_a.png",
            "description": "Scatterplot with points rising from lower left to upper right in a tight linear pattern.",
            "alt_text": "Scatterplot A, a strong positive linear pattern.",
        },
        {
            "asset_id": "psychology-2017-mcq-043-option-b",
            "kind": "option",
            "option_label": "B",
            "page": 23,
            "rect": (322.0, 188.0, 532.0, 252.0),
            "filename": "q43_option_b.png",
            "description": "Scatterplot with points widely scattered and no clear direction.",
            "alt_text": "Scatterplot B, a weak or absent relationship.",
        },
        {
            "asset_id": "psychology-2017-mcq-043-option-c",
            "kind": "option",
            "option_label": "C",
            "page": 23,
            "rect": (322.0, 256.0, 532.0, 320.0),
            "filename": "q43_option_c.png",
            "description": "Scatterplot with points widely scattered and no clear direction.",
            "alt_text": "Scatterplot C, a weak or absent relationship.",
        },
        {
            "asset_id": "psychology-2017-mcq-043-option-d",
            "kind": "option",
            "option_label": "D",
            "page": 23,
            "rect": (322.0, 324.0, 532.0, 388.0),
            "filename": "q43_option_d.png",
            "description": "Scatterplot with points trending downward from upper left to lower right.",
            "alt_text": "Scatterplot D, a negative relationship.",
        },
        {
            "asset_id": "psychology-2017-mcq-043-option-e",
            "kind": "option",
            "option_label": "E",
            "page": 23,
            "rect": (322.0, 386.0, 532.0, 458.0),
            "filename": "q43_option_e.png",
            "description": "Scatterplot with points trending steeply downward from upper left to lower right in a tight linear pattern.",
            "alt_text": "Scatterplot E, a strong negative linear pattern.",
        },
    ],
    49: [
        {
            "asset_id": "psychology-2017-mcq-049-fig-1",
            "kind": "figure",
            "option_label": None,
            "page": 24,
            "rect": (318.0, 105.0, 532.0, 235.0),
            "filename": "q49_xo_grid.png",
            "description": "A grid of X and O symbols arranged in four rows and six columns.",
            "alt_text": "Grid of alternating X and O symbols.",
        }
    ],
    67: [
        {
            "asset_id": "psychology-2017-mcq-067-fig-1",
            "kind": "figure",
            "option_label": None,
            "page": 27,
            "rect": (60.0, 80.0, 272.0, 206.0),
            "filename": "q67_normal_distribution.png",
            "description": (
                "A normal curve over mathematics achievement scores, with tick "
                "marks at 40, 50, 60, 70, 80, 90, and 100."
            ),
            "alt_text": "Normal distribution curve for mathematics achievement scores.",
        }
    ],
    92: [
        {
            "asset_id": "psychology-2017-mcq-092-option-a",
            "kind": "option",
            "option_label": "A",
            "page": 30,
            "rect": (58.0, 164.0, 242.0, 242.0),
            "filename": "q92_option_a.png",
            "description": "A curve that drops steeply and then levels off.",
            "alt_text": "Graph A: steep initial drop followed by a plateau.",
        },
        {
            "asset_id": "psychology-2017-mcq-092-option-b",
            "kind": "option",
            "option_label": "B",
            "page": 30,
            "rect": (58.0, 250.0, 242.0, 330.0),
            "filename": "q92_option_b.png",
            "description": "An inverted U-shaped curve.",
            "alt_text": "Graph B: inverted U-shaped curve.",
        },
        {
            "asset_id": "psychology-2017-mcq-092-option-c",
            "kind": "option",
            "option_label": "C",
            "page": 30,
            "rect": (58.0, 330.0, 242.0, 414.0),
            "filename": "q92_option_c.png",
            "description": "A flat horizontal line.",
            "alt_text": "Graph C: flat horizontal line.",
        },
        {
            "asset_id": "psychology-2017-mcq-092-option-d",
            "kind": "option",
            "option_label": "D",
            "page": 30,
            "rect": (58.0, 416.0, 242.0, 502.0),
            "filename": "q92_option_d.png",
            "description": "A bell-shaped curve.",
            "alt_text": "Graph D: bell-shaped curve.",
        },
        {
            "asset_id": "psychology-2017-mcq-092-option-e",
            "kind": "option",
            "option_label": "E",
            "page": 30,
            "rect": (58.0, 500.0, 242.0, 592.0),
            "filename": "q92_option_e.png",
            "description": "A curve with two peaks.",
            "alt_text": "Graph E: curve with two peaks.",
        },
    ],
}

# Question Descriptors and Performance Data, transcribed from PDF pages 66-68.
# Format: number|topic|key|percent_correct. The key is cross-checked against
# ANSWER_2017 below.
DESCRIPTORS_2017_RAW = """
1|Treatment of Psychological Disorders|A|84
2|Motivation and Emotion|C|69
3|Biological Bases of Behavior|A|39
4|Methods|C|52
5|States of Consciousness|D|69
6|Developmental Psychology|A|61
7|Sensation and Perception|A|77
8|Biological Bases of Behavior|E|61
9|Social Psychology|E|61
10|Biological Bases of Behavior|C|50
11|Methods|D|98
12|Methods|B|86
13|History and Approaches|E|50
14|Social Psychology|A|72
15|Sensation and Perception|D|27
16|Motivation and Emotion|B|72
17|Personality|E|55
18|Biological Bases of Behavior|D|45
19|Testing and Individual Differences|A|71
20|Abnormal Psychology|E|60
21|Social Psychology|B|79
22|Learning|B|23
23|Treatment of Psychological Disorders|A|45
24|Methods|A|49
25|Biological Bases of Behavior|E|62
26|Biological Bases of Behavior|D|87
27|Treatment of Psychological Disorders|E|81
28|Developmental Psychology|B|46
29|Personality|B|74
30|Social Psychology|A|75
31|Learning|B|78
32|Developmental Psychology|B|46
33|Cognition|B|46
34|Cognition|A|75
35|Social Psychology|C|87
36|Motivation and Emotion|C|57
37|Developmental Psychology|A|72
38|Motivation and Emotion|B|91
39|Biological Bases of Behavior|B|79
40|Treatment of Psychological Disorders|B|79
41|Social Psychology|B|84
42|Motivation and Emotion|E|76
43|Methods|E|86
44|Motivation and Emotion|D|53
45|Biological Bases of Behavior|B|90
46|Motivation and Emotion|E|50
47|Cognition|E|57
48|Personality|D|63
49|Sensation and Perception|B|70
50|Developmental Psychology|B|77
51|Social Psychology|A|71
52|Abnormal Psychology|D|56
53|History and Approaches|E|72
54|Biological Bases of Behavior|C|53
55|Social Psychology|E|94
56|Methods|D|74
57|Personality|C|62
58|Social Psychology|C|82
59|Methods|E|64
60|Abnormal Psychology|D|80
61|Learning|C|78
62|Developmental Psychology|B|93
63|Developmental Psychology|B|64
64|Sensation and Perception|C|42
65|Abnormal Psychology|A|75
66|States of Consciousness|E|42
67|Testing and Individual Differences|D|48
68|Testing and Individual Differences|B|79
69|Testing and Individual Differences|A|76
70|Learning|A|72
71|States of Consciousness|D|64
72|Biological Bases of Behavior|B|88
73|Learning|E|49
74|Abnormal Psychology|C|55
75|Methods|E|73
76|Learning|D|79
77|Testing and Individual Differences|A|51
78|Sensation and Perception|B|75
79|Cognition|B|32
80|Social Psychology|B|84
81|Personality|D|55
82|Cognition|D|52
83|Learning|C|63
84|Personality|A|74
85|Treatment of Psychological Disorders|E|68
86|Cognition|D|58
87|Sensation and Perception|C|95
88|Developmental Psychology|B|77
89|History and Approaches|C|28
90|Testing and Individual Differences|B|81
91|Abnormal Psychology|E|77
92|Cognition|A|70
93|Sensation and Perception|B|40
94|Cognition|A|53
95|Cognition|B|67
96|Methods|E|69
97|Methods|B|80
98|Cognition|A|56
99|Learning|A|67
100|Abnormal Psychology|D|54
"""


def _parse_descriptors(raw: str) -> dict[int, dict[str, Any]]:
    rows: dict[int, dict[str, Any]] = {}
    for line in raw.strip().splitlines():
        if not line.strip():
            continue
        number, topic, key, percent = line.strip().split("|")
        rows[int(number)] = {
            "topic": topic,
            "key": key,
            "percent_correct": int(percent),
        }
    return rows


DESCRIPTORS_2017 = _parse_descriptors(DESCRIPTORS_2017_RAW)


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------


def normalize_text(text: str) -> str:
    text = text.replace(" ", " ").replace("­", "")
    text = text.replace("\r", "\n")
    # Join hyphenated words that were split at a line boundary.
    text = re.sub(r"(?<=[A-Za-z])-[ \t]+(?=[a-z])", "-", text)
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    return " ".join(line for line in lines if line).strip()


def strip_running_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = re.split(r"\bEND OF SECTION I\b", text)[0]
    text = re.sub(
        r"\s*(?:Unauthorized copying or reuse of"
        r"(?:\s+any part of this page is illegal\.?)?"
        r"|GO ON TO THE NEXT PAGE\.?"
        r"|Jnauthorized copying or reuse.*"
        r"|ly part of this page is illegi.*)\s*$",
        "",
        text,
        flags=re.IGNORECASE,
    )
    return text.strip()


def is_running_line(text: str) -> bool:
    if text in {"PSYCHOLOGY", "SECTION I"}:
        return True
    return bool(
        re.match(
            r"^(?:Time[—\-]|100 Questions|Directions:|Unauthorized|any part of|"
            r"GO ON TO THE NEXT PAGE|Jnauthorized|ly part of|-\d+-)$",
            text,
        )
    )


def page_size_for(year: int) -> tuple[float, float]:
    return PAGE_2016 if year == 2016 else PAGE_2017


# ---------------------------------------------------------------------------
# 2016 extraction
# ---------------------------------------------------------------------------


def extract_2016_lines(doc: fitz.Document) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    for page_index in MCQ_PAGES_2016:
        page = doc[page_index]
        for block in page.get_text("dict")["blocks"]:
            if block.get("type") != 0:
                continue
            for line in block["lines"]:
                text = "".join(span["text"] for span in line["spans"]).strip()
                if not text or is_running_line(text):
                    continue
                x0, y0, _, _ = line["bbox"]
                if y0 > 720:
                    continue
                lines.append(
                    {
                        "page": page_index + 1,
                        "col": "L" if x0 < 300 else "R",
                        "x": x0,
                        "y": y0,
                        "text": text,
                    }
                )
    lines.sort(key=lambda row: (row["page"], row["col"], row["y"], row["x"]))
    return lines


def parse_2016_mcq(doc: fitz.Document) -> list[dict[str, Any]]:
    lines = extract_2016_lines(doc)
    question_re = re.compile(r"^(\d{1,3})\.\s*(.*)$")
    option_re = re.compile(r"^\(([A-E])\)\s*(.*)$")

    raw: list[dict[str, Any]] = []
    current: Optional[dict[str, Any]] = None
    for line in lines:
        text = line["text"]
        match = question_re.match(text)
        if match and 1 <= int(match.group(1)) <= 100:
            if current:
                raw.append(current)
            current = {
                "number": int(match.group(1)),
                "page": line["page"],
                "col": line["col"],
                "stem": [match.group(2)],
                "options": [],
            }
            continue
        if current is None:
            continue
        option_match = option_re.match(text)
        if (
            option_match
            and line["page"] == current["page"]
            and line["col"] == current["col"]
        ):
            current["options"].append(
                {
                    "label": option_match.group(1),
                    "text": [option_match.group(2)],
                    "page": line["page"],
                    "col": line["col"],
                    "y": line["y"],
                }
            )
            continue
        if current["options"]:
            option = current["options"][-1]
            if (
                line["page"] == option["page"]
                and line["col"] == option["col"]
                and option["y"] - line["y"] < 24
            ):
                option["text"].append(text)
                option["y"] = line["y"]
        elif line["page"] == current["page"] and line["col"] == current["col"]:
            current["stem"].append(text)
    if current:
        raw.append(current)

    if len(raw) != 100:
        raise ValueError(f"2016: expected 100 MCQs, got {len(raw)}")
    if [q["number"] for q in raw] != list(range(1, 101)):
        raise ValueError("2016: question numbers are not exactly 1..100")

    questions: list[dict[str, Any]] = []
    for item in raw:
        number = item["number"]
        labels = [option["label"] for option in item["options"]]
        if labels != list("ABCDE"):
            raise ValueError(f"2016 Q{number}: option labels are {labels}")
        stem = strip_running_text(normalize_text(" ".join(item["stem"])))
        correction = CORRECTIONS_2016.get(number, {})
        stem = correction.get("stem", stem)
        options = []
        for option in item["options"]:
            label = option["label"]
            content = strip_running_text(normalize_text(" ".join(option["text"])))
            content = correction.get(label, content)
            options.append(content)
        questions.append(
            {
                "number": number,
                "page_start": min(item["page"], *(o["page"] for o in item["options"])),
                "page_end": max(item["page"], *(o["page"] for o in item["options"])),
                "stem": stem,
                "options": options,
                "context": CONTEXT_2016.get(number),
            }
        )
    return questions


def parse_2016_answer_key(doc: fitz.Document) -> dict[int, str]:
    text = doc[ANSWER_KEY_PAGE_2016].get_text()
    answers = {
        int(number): letter
        for number, letter in re.findall(r"Question\s+(\d+):\s*([A-E])", text)
    }
    if len(answers) != 100:
        raise ValueError(f"2016: expected 100 answer-key rows, got {len(answers)}")
    return answers


def parse_2016_descriptors(doc: fitz.Document) -> dict[int, dict[str, Any]]:
    rows: dict[int, dict[str, Any]] = {}
    for page_index in DESCRIPTOR_PAGES_2016:
        lines = [
            line.strip()
            for line in doc[page_index].get_text().split("\n")
            if line.strip()
        ]
        index = 0
        while index + 3 < len(lines):
            if (
                re.fullmatch(r"\d{1,3}", lines[index])
                and re.fullmatch(r"[A-E]", lines[index + 2])
                and re.fullmatch(r"\d{1,3}", lines[index + 3])
                and not re.fullmatch(r"\d+", lines[index + 1])
            ):
                number = int(lines[index])
                if 1 <= number <= 100:
                    rows[number] = {
                        "topic": lines[index + 1],
                        "key": lines[index + 2],
                        "percent_correct": int(lines[index + 3]),
                    }
                    index += 4
                    continue
            index += 1
    if len(rows) != 100:
        raise ValueError(f"2016: expected 100 descriptor rows, got {len(rows)}")
    return rows


# ---------------------------------------------------------------------------
# 2017 OCR
# ---------------------------------------------------------------------------


def _compile_vision_helper() -> Path:
    target = Path(tempfile.gettempdir()) / "ap_psych_vision_ocr"
    if target.exists() and target.stat().st_mtime >= VISION_SWIFT.stat().st_mtime:
        return target
    if shutil.which("swiftc") is None:
        raise RuntimeError(
            "swiftc is required for 2017 OCR on macOS; "
            "or pass --ocr-dir with precomputed JSON files."
        )
    subprocess.run(
        ["swiftc", str(VISION_SWIFT), "-o", str(target)],
        check=True,
        capture_output=True,
    )
    return target


def _ocr_page(pdf: Path, page_number: int, cache_dir: Path) -> list[dict[str, Any]]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{page_number:02d}.json"
    if cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))
    helper = _compile_vision_helper()
    doc = fitz.open(pdf)
    try:
        page = doc[page_number - 1]
        png_path = cache_dir / f"{page_number:02d}.png"
        pix = page.get_pixmap(dpi=400)
        pix.save(str(png_path))
    finally:
        doc.close()
    result = subprocess.run(
        [str(helper), str(png_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    cache_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    return payload


def load_2017_ocr(
    pdf: Path, ocr_dir: Optional[Path]
) -> dict[int, list[dict[str, Any]]]:
    cache_dir = Path(tempfile.gettempdir()) / "ap_psych_2017_ocr_400"
    pages: dict[int, list[dict[str, Any]]] = {}
    for page_number in MCQ_PAGES_2017:
        if ocr_dir:
            path = ocr_dir / f"{page_number:02d}.json"
            if not path.exists():
                raise FileNotFoundError(path)
            pages[page_number] = json.loads(path.read_text(encoding="utf-8"))
        else:
            pages[page_number] = _ocr_page(pdf, page_number, cache_dir)
    return pages


def parse_2017_mcq(ocr_pages: dict[int, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    for page_number, observations in ocr_pages.items():
        for column, low, high in (("L", 0.0, 0.5), ("R", 0.5, 1.0)):
            selected = [
                obs
                for obs in observations
                if low <= float(obs["x"]) < high
            ]
            selected.sort(key=lambda obs: (-float(obs["y"]), float(obs["x"])))
            for obs in selected:
                text = str(obs.get("text") or "").strip()
                if not text or is_running_line(text):
                    continue
                lines.append(
                    {
                        "page": page_number,
                        "col": column,
                        "x": float(obs["x"]),
                        "y": float(obs["y"]),
                        "text": text,
                    }
                )

    question_re = re.compile(r"^(\d{1,3})[.)]\s*(.*)$")
    option_re = re.compile(r"^\(([A-E])\)\s*(.*)$")
    raw: list[dict[str, Any]] = []
    current: Optional[dict[str, Any]] = None
    for line in lines:
        text = line["text"]
        match = question_re.match(text)
        if match and 1 <= int(match.group(1)) <= 100:
            if current:
                raw.append(current)
            current = {
                "number": int(match.group(1)),
                "page": line["page"],
                "col": line["col"],
                "stem": [match.group(2)],
                "options": [],
            }
            continue
        if current is None:
            continue
        option_match = option_re.match(text)
        if (
            option_match
            and line["page"] == current["page"]
            and line["col"] == current["col"]
        ):
            current["options"].append(
                {
                    "label": option_match.group(1),
                    "text": [option_match.group(2)],
                    "page": line["page"],
                    "col": line["col"],
                    "y": line["y"],
                }
            )
            continue
        if current["options"]:
            option = current["options"][-1]
            if (
                line["page"] == option["page"]
                and line["col"] == option["col"]
                and option["y"] - line["y"] <= 0.025
            ):
                option["text"].append(text)
                option["y"] = line["y"]
        elif line["page"] == current["page"] and line["col"] == current["col"]:
            current["stem"].append(text)
    if current:
        raw.append(current)

    if len(raw) != 100:
        raise ValueError(f"2017: expected 100 MCQs, got {len(raw)}")
    if [q["number"] for q in raw] != list(range(1, 101)):
        raise ValueError("2017: question numbers are not exactly 1..100")

    questions: list[dict[str, Any]] = []
    for item in raw:
        number = item["number"]
        stem = strip_running_text(normalize_text(" ".join(item["stem"])))
        options = {
            option["label"]: strip_running_text(
                normalize_text(" ".join(option["text"]))
            )
            for option in item["options"]
        }
        correction = CORRECTIONS_2017.get(number, {})
        stem = correction.get("stem", stem)
        if "options" in correction:
            options = dict(correction["options"])
        else:
            for label, content in correction.items():
                if label in "ABCDE":
                    options[label] = content
        if number == 13:
            stem = stem.replace("motives-I", "motives—I")
        if number == 63:
            stem = correction["stem"]
        missing = [label for label in "ABCDE" if not options.get(label)]
        if missing:
            raise ValueError(f"2017 Q{number}: missing options {missing}")
        option_pages = [option["page"] for option in item["options"]] or [item["page"]]
        questions.append(
            {
                "number": number,
                "page_start": min(item["page"], *option_pages),
                "page_end": max(item["page"], *option_pages),
                "stem": stem,
                "options": [options[label] for label in "ABCDE"],
                "context": CONTEXT_2017.get(number),
            }
        )
    return questions


# ---------------------------------------------------------------------------
# Assets
# ---------------------------------------------------------------------------


def crop_assets(
    doc: fitz.Document,
    specs: dict[int, list[dict[str, Any]]],
    year: int,
) -> None:
    asset_dir = IMAGE_ROOT / f"ap{year}"
    asset_dir.mkdir(parents=True, exist_ok=True)
    wanted = {
        spec["filename"]: spec
        for question_specs in specs.values()
        for spec in question_specs
    }
    pdf_mtime = Path(doc.name).stat().st_mtime
    for filename, spec in wanted.items():
        output = asset_dir / filename
        if output.exists() and output.stat().st_mtime >= pdf_mtime:
            continue
        page = doc[spec["page"] - 1]
        pix = page.get_pixmap(clip=fitz.Rect(*spec["rect"]), dpi=300)
        pix.save(str(output))


def build_assets(
    specs: dict[int, list[dict[str, Any]]], year: int
) -> dict[int, list[dict[str, Any]]]:
    page_width, page_height = page_size_for(year)
    assets_by_question: dict[int, list[dict[str, Any]]] = {}
    for number, question_specs in specs.items():
        rows = []
        for spec in question_specs:
            x0, y0, x1, y1 = spec["rect"]
            rows.append(
                {
                    "asset_id": spec["asset_id"],
                    "kind": spec["kind"],
                    "option_label": spec["option_label"],
                    "path": str(
                        (
                            IMAGE_ROOT
                            / f"ap{year}"
                            / spec["filename"]
                        ).relative_to(ROOT)
                    ),
                    "page": spec["page"],
                    "bbox": [
                        round(x0 / page_width, 5),
                        round(y0 / page_height, 5),
                        round(x1 / page_width, 5),
                        round(y1 / page_height, 5),
                    ],
                    "description": spec["description"],
                    "alt_text": spec["alt_text"],
                }
            )
        assets_by_question[number] = rows
    return assets_by_question


# ---------------------------------------------------------------------------
# FRQ data
# ---------------------------------------------------------------------------

GENERAL_2016_Q1 = """1. Answers must be presented in sentences, and sentences must be cogent enough for the student’s meaning to come through. Spelling and grammatical mistakes do not reduce a student’s score, but spelling must be close enough that the reader is convinced of the word.
2. Do not score students' notes made on the question section of the booklet. Score only what has been written in the blanks provided in the booklet.
3. Definitions alone will not score, but they may be used to enhance the application.
4. Within a point, a student will not be penalized for misinformation unless it directly contradicts correct information that would otherwise have scored a point. A correct application with incorrect definition is not considered a direct contradiction and should score the point.
5. Rubric examples provided for each point are not to be considered exhaustive.
6. A student can score points only if the student clearly conveys what part of the question is being answered. It is possible to infer the part of the question being answered if it is consistent with the order of the question.
7. The appropriate context of each section (A and B) must be explicitly established or related back to the prompt of the question."""

GENERAL_2016_Q2 = """1. Answers must be presented in sentences, and sentences must be cogent enough for the student’s meaning to come through. Spelling and grammatical mistakes do not reduce a student’s score, but spelling must be close enough that the reader is convinced of the word.
2. Do not score students' notes made on the question section of the booklet. Score only what has been written in the blanks provided in the booklet.
3. Definitions alone will not score, but they may be used to enhance the application.
4. Within a particular point, a student will not be penalized for misinformation unless it directly contradicts correct information that would otherwise have scored a point. A correct application with incorrect definition is not considered a direct contradiction and should score the point.
5. Rubric examples provided for each point are not to be considered exhaustive.
6. A student can score points only if the student clearly conveys what part of the question is being answered. It is possible to infer the part of the question being answered if it is consistent with the order of the question.
7. The appropriate context of each section (A, B, C) must be explicitly established or related back to the prompt of the question."""

GENERAL_2017_Q1 = """1. Answers must be presented in sentences, and sentences must be cogent enough for the meaning of the response to come through. Spelling and grammatical mistakes do not reduce the score of a response, but spelling must be close enough that the reader is convinced of the word.
2. Do not score any notes made on the question section of the booklet. Score only what has been written in the blanks provided in the booklet.
3. Definitions alone will not score, but they may be used to enhance the application.
4. Within a point, a student will not be penalized for misinformation unless it directly contradicts correct information that would otherwise have scored a point. A correct application with incorrect definition is not considered a direct contradiction and should score the point.
5. Rubric examples provided for each point are not to be considered exhaustive.
6. Responses that simply parrot or repeat the terms from the question will not score.
7. A response can score point only if it clearly conveys what part of the question is being answered. It is possible to infer what part of the question is being answered if it is consistent with the order of the question."""

GENERAL_2017_Q2 = GENERAL_2017_Q1 + """
8. To score, each concept must be discussed in the context of Kent's deciding to either keep or return the money."""

PROMPT_2016_Q1 = """1. Researchers investigated whether introducing a good-luck-related superstition would improve the performance of participants attempting to hit a golf ball into a hole (Damisch, Stoberock, & Mussweiler, 2010). Participants in the study were randomly assigned to one of two groups. Those in the first group were told, “Here is your ball. So far it has turned out to be a lucky ball.” Those in the second group were told, “This is the ball everyone has used so far.” Participants then made ten attempts to hit the ball into the hole. The researchers measured the number of successful attempts, and they found that the mean difference between the two groups was statistically significant. The researchers theorized that the superstitious beliefs produced higher levels of self-efficacy, which led to improved performance.

Part A
Identify the design feature that makes the study experimental rather than correlational.
Explain what it means to say that there is a statistically significant difference between the two groups.
Explain how a superstitious belief might be related to a higher level of self-efficacy.

Part B
Many people engage in superstitious behavior, such as wearing lucky socks, in the belief that the superstitious behavior will lead to improved performance. Explain how each of the following may lead to the development or maintenance of superstitious beliefs or behaviors.
• Illusory correlation
• Positive reinforcement
• External locus of control
• Episodic memory"""

PROMPT_2016_Q2 = """2. Part A
The vast majority of students in a prestigious engineering program are men. Some professors in the program hope to recruit and admit more women. How might each of the following hinder their decision-making process to accept more women?
• Representativeness heuristic
• Belief perseverance
• Group polarization

Part B
The program has an entrance exam that has been used for many years, but now the professors are considering eliminating it. How might each of the following affect the decision to eliminate the exam?
• Stereotype threat
• Predictive validity

Part C
The professors decide to start a summer internship for female high school students, which they hope will promote interest in their engineering program. How might each of the following be used in the internship to help recruit more female students?
• Extrinsic motivation
• Modeling"""

PROMPT_2017_Q1 = """1. Rachel is an excellent high school student who earns high grades in challenging classes. She has recently been hired as a part-time lab assistant at a medical clinic. She is concerned that the job will affect her school performance.

Part A
Provide a specific example that clearly illustrates how each of the following would inhibit Rachel's success at her new job.
• Stereotype threat
• Adrenal glands
• Lack of REM sleep

Part B
Provide a specific example that clearly illustrates how each of the following would enhance her performance as a student with a challenging academic schedule.
• Distributed practice
• Reciprocal determinism
• Self-efficacy"""

PROMPT_2017_Q2 = """2. Thirty-year-old Kent found a bag containing several thousand dollars in a park. He is discussing with his family whether to give the money to the appropriate authorities or to keep the money.
Explain how each of the following psychological concepts could influence Kent's decision-making process.
• Prefrontal cortex
• Postconventional moral reasoning
• Antisocial personality disorder
• Evolutionary psychology
• Cognitive dissonance
• Incentive theory
• Groupthink"""


def part(
    number: int,
    title: str,
    group: str,
    criteria: str,
    *,
    positive: Iterable[str] = (),
    negative: Iterable[str] = (),
    notes: str = "",
    rules: str = "",
) -> dict[str, Any]:
    return {
        "part_id": f"point-{number}",
        "label": f"Point {number}",
        "title": title,
        "group": group,
        "max_points": 1,
        "criteria": criteria,
        "decision_rules": rules,
        "examples_positive": list(positive),
        "examples_negative": list(negative),
        "notes": notes,
        "sort_order": number,
    }


FRQ_2016 = {
    1: {
        "prompt": PROMPT_2016_Q1,
        "page": 34,
        "total_points": 7,
        "general": GENERAL_2016_Q1,
        "parts": [
            part(
                1,
                "Experimental design",
                "A",
                "The response identifies a design feature that makes the study experimental: participants were randomly assigned to one of two conditions, or the independent variable was manipulated. A complete description of the manipulation procedure scores even if the word “manipulation” is not used.",
                positive=[
                    "Participants were randomly assigned to the “Lucky Ball Group” or the other group.",
                    "The experimental group, the one receiving the treatment, was told they had the lucky ball.",
                    "The control group was not told that their ball had any lucky properties.",
                ],
                negative=[
                    "Random selection and random sampling do not score.",
                    "Simply stating that there was a control group does not score.",
                ],
            ),
            part(
                2,
                "Statistical significance",
                "A",
                "The difference between the groups is less likely to be due to chance, random variation, coincidence, or Type I error; or it is more likely to be due to manipulation of the independent variable.",
                positive=[
                    "The researchers were 95% sure that the independent variable caused the difference between the groups.",
                    "The difference was not due to chance.",
                ],
                negative=["Using p < .05 alone does not score."],
            ),
            part(
                3,
                "Superstitious belief and self-efficacy",
                "A",
                "Superstitious beliefs boost one’s belief that they can master a task or increase their personal skill level or capability. The increased confidence must reside within the person, not be ascribed to the ball.",
                positive=[
                    "Believing that one had the lucky ball led to greater certainty that they would get more balls into the hole.",
                ],
                negative=[
                    "Self-esteem definitions alone do not score.",
                    "“Self-fulfilling prophecy” alone does not score.",
                    "References only to improved performance do not score.",
                ],
            ),
            part(
                4,
                "Illusory correlation",
                "B",
                "The response must mention that a relationship is perceived and that the relationship is noncontingent, coincidental, false, or occurring by chance.",
                positive=[
                    "Jordan wears purple socks to a game and has a great game, then incorrectly assumes the socks caused the success.",
                ],
            ),
            part(
                5,
                "Positive reinforcement",
                "B",
                "The response must reference performing a random/superstitious behavior, a desirable stimulus or outcome following that behavior, and an increased likelihood of the behavior occurring in the future.",
                positive=[
                    "I wore my purple socks and my team won; now I wear my purple socks for every game.",
                ],
                negative=[
                    "Strengthening the superstitious belief alone does not score; the behavior must be strengthened.",
                ],
            ),
            part(
                6,
                "External locus of control",
                "B",
                "External circumstances—such as a powerful entity, chance, or luck—are believed to influence a logically unrelated result. Locus of control may be treated as a state or a trait.",
                positive=[
                    "Believing that lucky socks caused a good grade reflects an external locus of control.",
                ],
                negative=[
                    "Stating “external” alone without identifying a source of control does not score.",
                ],
            ),
            part(
                7,
                "Episodic memory",
                "B",
                "The response must reference an individual’s memory, recall, or remembering of a specific personal event and connect it to superstitious beliefs or behaviors.",
                positive=[
                    "You recall only the baseball games in which you hit home runs while wearing purple socks, so you wear them for every game.",
                ],
            ),
        ],
    },
    2: {
        "prompt": PROMPT_2016_Q2,
        "page": 42,
        "total_points": 7,
        "general": GENERAL_2016_Q2,
        "parts": [
            part(
                1,
                "Representativeness heuristic",
                "A",
                "The response explains how a prototypical or stereotypical categorization hinders the professors’ decision to admit more women: more engineers are male, men have characteristics of an engineer, or women lack those characteristics.",
                positive=[
                    "Women do not fit the prototype or stereotype of an engineer held by the admissions committee, so admission is harder.",
                ],
                negative=["Only describing the availability heuristic does not score."],
            ),
            part(
                2,
                "Belief perseverance",
                "A",
                "The response must include an existing belief, evidence to the contrary, maintenance of the original belief, and hindrance of the decision to admit more women.",
                positive=[
                    "If the professors believe men are more competent engineers, they adhere to that belief even when disconfirming data show women are equally likely to succeed.",
                ],
            ),
            part(
                3,
                "Group polarization",
                "A",
                "After discussion, the group consensus—not an individual’s view—becomes more extreme, and this hinders the professors’ decision to admit more women.",
                positive=[
                    "If the professors believe men are more competent, discussion makes the group’s conviction stronger and reduces women’s chances of admission.",
                ],
                negative=[
                    "Conformity or persuasion alone does not score.",
                    "A subgroup merely switching sides does not score.",
                    "Examples that relate only to groupthink do not score.",
                ],
            ),
            part(
                4,
                "Stereotype threat",
                "B",
                "The response must address knowledge of a negative cultural stereotype that lowers expectations about ability, the resulting impairment of performance, and the impact on the decision to eliminate the exam.",
                positive=[
                    "Female applicants know the cultural assumption that men make better engineers, become anxious, and score lower; the professors then discontinue the exam.",
                ],
            ),
            part(
                5,
                "Predictive validity",
                "B",
                "The response must show that a useful test is correlated with later performance on what it was designed to measure, and relate the direction of that relationship to the decision to keep or eliminate the exam.",
                positive=[
                    "Students who score well on the admissions exam also do well in coursework, so the committee keeps the exam.",
                    "Students who score poorly on the exam do well in the program, so the committee discontinues the exam.",
                ],
                notes="High predictive validity contributes to keeping the exam; low predictive validity contributes to eliminating it.",
            ),
            part(
                6,
                "Extrinsic motivation",
                "C",
                "An outside influence—a reward, reinforcement, or incentive—increases the recruitment of women into the program or internship.",
                positive=[
                    "A scholarship offered to all female students who complete the summer internship motivates more women to enroll.",
                ],
                negative=[
                    "The word “external” or “extrinsic” alone, without a reward or incentive linked to recruitment, does not score.",
                ],
            ),
            part(
                7,
                "Modeling",
                "C",
                "The response must describe observing a behavior or a description of a behavior, acting in a similar manner by imitating or mimicking it, and increased female enrollment or interest.",
                positive=[
                    "Female engineers serve as mentors in the internship, giving high school students a role model to emulate and increasing their interest in engineering.",
                ],
                notes="Joining the program or demonstrating interest fulfills both the imitation and increased-interest elements.",
            ),
        ],
    },
}

FRQ_2017 = {
    1: {
        "prompt": PROMPT_2017_Q1,
        "page": 35,
        "total_points": 6,
        "general": GENERAL_2017_Q1,
        "parts": [
            part(
                1,
                "Stereotype threat",
                "A",
                "Rachel’s job performance may be inhibited if she is confronted with or aware of stereotypical beliefs that the job is difficult for a specified population or category to which she belongs (gender, age, or ethnicity).",
                positive=[
                    "If Rachel is told high school students are not mature enough for a medical setting, she may question her ability and make mistakes.",
                    "Because Rachel knows more men work in medicine, she may think she is not as good as male lab assistants and decide to quit.",
                ],
                negative=["Examples of discrimination or stereotypes alone do not score."],
                notes="Part A responses must refer to inhibiting job performance, not school performance, for points 1-3.",
            ),
            part(
                2,
                "Adrenal glands",
                "A",
                "Adrenal gland activity could inhibit Rachel’s performance: if she becomes too aroused or not aroused enough, her performance is impaired by nervousness, anxiety, or stress.",
                positive=[
                    "Rachel’s anxiety causes her adrenal glands to release hormones, heightening arousal and making concentration harder.",
                    "If her adrenal glands do not secrete enough noradrenaline, she may lack the alertness needed for the job.",
                ],
                notes="Students do not have to specify a hormone.",
            ),
            part(
                3,
                "Lack of REM sleep",
                "A",
                "REM sleep is key for forming and consolidating new memories. Without REM sleep, Rachel has trouble processing and recalling information important for job performance.",
                positive=[
                    "Without REM sleep, Rachel has difficulty processing what she learned and makes mistakes at work.",
                ],
                notes="The impairment should not be attributed to sleep deprivation alone.",
            ),
            part(
                4,
                "Distributed practice",
                "B",
                "The response indicates studying that is spaced or spread over multiple time periods and enhances school or job performance.",
                positive=[
                    "Rachel studied the material a little bit each day during the semester.",
                    "Rachel studies in intervals, which helps her remember the material better.",
                ],
                negative=[
                    "Studying over a long period of time without spacing does not score.",
                    "Grouping or chunking without spaced practice does not score.",
                    "“Spaced out” or “spread out” without multiple time periods does not score.",
                ],
            ),
            part(
                5,
                "Reciprocal determinism",
                "B",
                "The response must include all three elements—personal factors, behaviors, and environmental setting—and indicate enhanced school or job performance.",
                positive=[
                    "Because Rachel is conscientious, she organizes her study time efficiently, works longer at the clinic, and learns procedures more quickly.",
                    "Rachel is an extravert, seeks out teachers for help, and improves her understanding.",
                ],
            ),
            part(
                6,
                "Self-efficacy",
                "B",
                "The response must reflect a belief, knowledge, or expectancy in one’s ability to perform a behavior or task, and connect that belief to success at school or work.",
                positive=[
                    "Rachel knows she can balance school and work, which leads to greater success.",
                    "Rachel believes she can learn anything, so she masters tasks quickly in the lab.",
                ],
                negative=[
                    "Self-confidence, efficiency, self-esteem, or internal locus of control without reference to a belief does not score.",
                ],
            ),
        ],
    },
    2: {
        "prompt": PROMPT_2017_Q2,
        "page": 43,
        "total_points": 7,
        "general": GENERAL_2017_Q2,
        "parts": [
            part(
                1,
                "Prefrontal cortex",
                "Q2",
                "The response describes at least one prefrontal cortex function (planning, reasoning, decision making, judgment, attention, empathy) and ties it to Kent’s situation.",
                positive=[
                    "By deciding to keep the money, Kent is using his prefrontal cortex, which is used for decision making.",
                ],
                negative=[
                    "A definition alone, such as “the prefrontal cortex is the ability to make good decisions,” does not score.",
                    "If decision making is used, the function and application must be distinct; a non-brain area responsible for decision making does not score.",
                ],
            ),
            part(
                2,
                "Postconventional moral reasoning",
                "Q2",
                "The response explains that this stage reflects universal or abstract ethical principles, such as the greater good or justice, rather than simply following rules or avoiding punishment and rewards.",
                positive=[
                    "He is able to think about this ethical dilemma abstractly and keeps the money.",
                ],
            ),
            part(
                3,
                "Antisocial personality disorder",
                "Q2",
                "The response explains that someone with this disorder has increased impulsivity and hedonism, or lacks guilt, empathy, or regard for the rights of others, and describes how the presence or absence of ASPD affects Kent’s decision.",
                positive=[
                    "Keith, Kent’s brother, has ASPD and lacks empathy, and convinces Kent not to return the money.",
                ],
                negative=[
                    "“Because Kent is shy, he will not tell the police” does not score.",
                ],
            ),
            part(
                4,
                "Evolutionary psychology",
                "Q2",
                "The response explains that the behavior was evolutionarily selected in previous generations, or contributes to survival of the species, including passing on genes or increasing offspring survival.",
                positive=[
                    "If Kent’s family is poor, he keeps the money to help ensure the family survives.",
                    "Kent gives back the money because his ancestors were moral and he has that gene.",
                ],
                negative=[
                    "“Survival of the fittest” leading Kent to keep money to buy food does not score.",
                    "“Humans change over time” or selfishness alone does not score.",
                ],
                notes="Responses that include reciprocal helping do score.",
            ),
            part(
                5,
                "Cognitive dissonance",
                "Q2",
                "The response explains both the discrepancy between thoughts and/or behaviors and the anxiety, discomfort, or uneasiness that comes from that discrepancy.",
                positive=[
                    "Kent felt stress because he knew he should give back the money but also knew he could really use it for college.",
                ],
                negative=[
                    "Describing the discrepancy alone does not score.",
                    "Family disappointment without the dissonance experience does not score.",
                ],
            ),
            part(
                6,
                "Incentive theory",
                "Q2",
                "Extrinsic or external rewards have a direct impact on behavior. The incentive may favor keeping or returning the money, but it must be something other than the found money itself.",
                positive=[
                    "Suzy tells Kent she will go on a date with him if he keeps the money, so he keeps it.",
                    "Because the authorities have not offered a finder’s fee, Kent does not return the money.",
                ],
                negative=[
                    "“Due to incentive theory, Kent keeps the money as a reward” does not score.",
                ],
            ),
            part(
                7,
                "Groupthink",
                "Q2",
                "Kent’s decision making is impaired or affected because the family discussion is driven by maintaining consensus or group harmony rather than critical or rational thinking. Attempts to avoid groupthink also score.",
                positive=[
                    "Kent wants to make a good decision, but everyone seems to agree rather than think logically.",
                    "Kent asks family members to give honest opinions even if they get mad, because he wants the best decision.",
                ],
                negative=[
                    "The family simply agreeing that Kent should keep the money does not score.",
                    "Conformity alone does not score.",
                ],
            ),
        ],
    },
}


def build_frq(
    year: int, source_dir: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    source = FRQ_2016 if year == 2016 else FRQ_2017
    paper_id = PAPER_ID_2016 if year == 2016 else PAPER_ID_2017
    questions = []
    rubrics = []
    for number, item in source.items():
        question_id = f"{paper_id}-frq-{number:03d}"
        questions.append(
            {
                "question_id": question_id,
                "section": "FRQ",
                "number": number,
                "display_number": number,
                "question_type": "FRQ",
                "stem": item["prompt"],
                "context": None,
                "page_start": item["page"],
                "page_end": item["page"],
                "correct_answer": None,
                "answer_text": None,
                "answer_source": None,
                "answer_confidence": None,
                "options": [],
                "assets": [],
                "status": "ready",
                "notes": [
                    f"Prompt transcribed from {source_dir}.",
                    "Rubric parts were structured from the official scoring guidelines; no rubric points were invented.",
                ],
            }
        )
        parts = []
        for rubric_part in item["parts"]:
            parts.append({**rubric_part, "part_id": f"{question_id}-{rubric_part['part_id']}"})
        rubrics.append(
            {
                "rubric_id": f"{question_id}-rubric",
                "question_id": question_id,
                "total_points": item["total_points"],
                "format": "legacy_points",
                "general_considerations": item["general"],
                "parts": parts,
                "source": "source_pdf_scoring_guidelines",
                "notes": ["Official scoring guidelines; points are 0/1."],
            }
        )
    return questions, rubrics


# ---------------------------------------------------------------------------
# Assembly / QA
# ---------------------------------------------------------------------------


def build_question_rows(
    year: int,
    parsed: list[dict[str, Any]],
    answers: dict[int, str],
    descriptors: dict[int, dict[str, Any]],
    assets_by_question: dict[int, list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], list[str]]:
    paper_id = PAPER_ID_2016 if year == 2016 else PAPER_ID_2017
    warnings: list[str] = []
    rows = []
    for item in parsed:
        number = item["number"]
        answer = answers.get(number)
        if answer is None:
            raise ValueError(f"{year} Q{number}: no answer key")
        descriptor = descriptors.get(number, {})
        if descriptor.get("key") and descriptor["key"] != answer:
            warnings.append(
                f"Q{number}: answer key {answer} != descriptor key {descriptor['key']}"
            )
        options = []
        for index, label in enumerate("ABCDE"):
            content = item["options"][index]
            is_correct = label == answer
            options.append(
                {
                    "label": label,
                    "content": content,
                    "sort_order": index + 1,
                    "is_correct": is_correct,
                    "explanation": None,
                    "ai_explanation": None,
                    "figure_alt": None,
                }
            )
        row = {
            "question_id": f"{paper_id}-mcq-{number:03d}",
            "section": "MCQ",
            "number": number,
            "display_number": number,
            "stem": item["stem"],
            "context": item["context"],
            "page_start": item["page_start"],
            "page_end": item["page_end"],
            "correct_answer": answer,
            "answer_text": None,
            "answer_source": ANSWER_SOURCE,
            "answer_confidence": ANSWER_TEXT_2016 if year == 2016 else ANSWER_TEXT_2017,
            "options": options,
            "assets": assets_by_question.get(number, []),
            "status": "ready",
            "notes": [
                "No explanation is printed in the source; options.explanation remains NULL."
            ],
        }
        if descriptor:
            row["source_topic"] = descriptor["topic"]
            row["source_percent_correct"] = descriptor["percent_correct"]
        if year == 2017:
            row["notes"].append(
                "Text produced by macOS Vision OCR at 400 dpi and reviewed against the page image."
            )
            if number in {43, 92}:
                row["notes"].append("Options are image-only; option text points to the cropped image.")
        rows.append(row)
    return rows, warnings


def make_qa(
    year: int,
    questions: list[dict[str, Any]],
    rubrics: list[dict[str, Any]],
    descriptor_key_mismatches: list[str],
    manual_corrections: list[str],
    ocr_used: bool,
) -> dict[str, Any]:
    mcqs = [q for q in questions if q["section"] == "MCQ"]
    option_counts = Counter(len(q["options"]) for q in mcqs)
    answer_distribution = Counter(q["correct_answer"] for q in mcqs)
    empty_options = [
        {"number": q["number"], "labels": [o["label"] for o in q["options"] if not o["content"].strip()]}
        for q in mcqs
        if any(not o["content"].strip() for o in q["options"])
    ]
    answers_not_in_options = [
        q["number"]
        for q in mcqs
        if q["correct_answer"] not in {o["label"] for o in q["options"]}
    ]
    figure_questions = sorted(
        {q["number"] for q in mcqs if any(a["kind"] == "figure" for a in q["assets"])}
    )
    option_image_questions = sorted(
        {q["number"] for q in mcqs if any(a["kind"] == "option" for a in q["assets"])}
    )
    asset_count = sum(len(q["assets"]) for q in mcqs)
    unique_asset_files = len({a["path"] for q in mcqs for a in q["assets"]})
    cross_page = [
        {"number": q["number"], "pages": [q["page_start"], q["page_end"]]}
        for q in mcqs
        if q["page_start"] != q["page_end"]
    ]
    return {
        "mcq_count": len(mcqs),
        "frq_count": len([q for q in questions if q["section"] == "FRQ"]),
        "option_count_distribution": {str(k): v for k, v in sorted(option_counts.items())},
        "answer_distribution": dict(sorted(answer_distribution.items())),
        "missing_question_numbers": [
            n for n in range(1, 101) if n not in {q["number"] for q in mcqs}
        ],
        "empty_stems": [q["number"] for q in mcqs if not q["stem"].strip()],
        "empty_options": empty_options,
        "answers_not_in_options": answers_not_in_options,
        "descriptor_key_mismatches": descriptor_key_mismatches,
        "cross_page_questions": cross_page,
        "figure_questions": figure_questions,
        "option_image_questions": option_image_questions,
        "asset_count": asset_count,
        "unique_asset_files": unique_asset_files,
        "frq_rubric_count": len(rubrics),
        "rubric_part_count": sum(len(r["parts"]) for r in rubrics),
        "ocr_used": ocr_used,
        "manual_corrections": manual_corrections,
        "known_limitations": (
            [
                "2017 text is OCR-derived; all pages were reviewed against rendered page images, but residual OCR typos are possible.",
                "The 2017 answer key table was manually transcribed because Vision OCR did not read its body.",
                "Q43 and Q92 options are image-only; option text is a placeholder pointing to the cropped image.",
            ]
            if year == 2017
            else [
                "Q64 and Q65 share one neuron diagram asset.",
                "Figure-only questions use cropped images; PDF accessibility alt text is not inserted into question context.",
            ]
        ),
    }


def write_report(
    year: int,
    paper: dict[str, Any],
    questions: list[dict[str, Any]],
    qa: dict[str, Any],
    json_path: Path,
    report_path: Path,
) -> None:
    lines = [
        f"# {paper['title']} — extraction report",
        "",
        f"- Generated: {datetime.now().astimezone().isoformat(timespec='seconds')}",
        f"- Source PDF: `{paper['source_file']}`",
        f"- JSON: `{json_path.relative_to(ROOT)}`",
        "- Database writes: **none** (dry run)",
        "",
        "## Summary",
        "",
        f"- MCQ: {qa['mcq_count']}",
        f"- FRQ: {qa['frq_count']}",
        f"- Options per MCQ: {qa['option_count_distribution']}",
        f"- Answer distribution: {qa['answer_distribution']}",
        f"- Rubrics: {qa['frq_rubric_count']} ({qa['rubric_part_count']} rubric parts)",
        f"- Assets: {qa['asset_count']} (figures on {len(qa['figure_questions'])} questions; option images on {len(qa['option_image_questions'])} questions)",
        f"- Option-image questions: {qa['option_image_questions']}",
        f"- OCR used: {'yes' if qa['ocr_used'] else 'no'}",
        "",
        "## Checks",
        "",
        f"- Missing MCQ numbers: {qa['missing_question_numbers'] or 'none'}",
        f"- Empty stems: {qa['empty_stems'] or 'none'}",
        f"- Empty options: {qa['empty_options'] or 'none'}",
        f"- Answers not in options: {qa['answers_not_in_options'] or 'none'}",
        f"- Answer/descriptor mismatches: {qa['descriptor_key_mismatches'] or 'none'}",
        f"- Cross-page questions: {qa['cross_page_questions'] or 'none'}",
        "",
        "## Figure questions",
        "",
        ", ".join(str(n) for n in qa["figure_questions"]) or "none",
        "",
        "## Manual corrections / review notes",
        "",
    ]
    if qa["manual_corrections"]:
        lines.extend(f"- {item}" for item in qa["manual_corrections"])
    else:
        lines.append("- None.")
    lines.extend(["", "## Known limitations", ""])
    lines.extend(f"- {item}" for item in qa["known_limitations"])
    lines.extend(
        [
            "",
            "## Verification",
            "",
            "```bash",
            f"python3 -m json.tool {json_path.relative_to(ROOT)} > /dev/null",
            "```",
            "",
            "The JSON was generated without writing to `psychology_exam.db` or any Release.",
            "",
        ]
    )
    report_path.write_text("\n".join(lines), encoding="utf-8")


def build_paper(year: int, ocr_dir: Optional[Path]) -> dict[str, Any]:
    if year == 2016:
        pdf = PDF_2016
        paper_id = PAPER_ID_2016
        source_id = SOURCE_ID_2016
        title = "AP Psychology 2016 (100 MCQs + 2 FRQs)"
        chinese_title = "2016 年 AP 心理学（100 道选择题 + 2 道主观题）"
        source_file = "assets/psychology/papers/2016/2016.pdf"
        doc = fitz.open(pdf)
        parsed = parse_2016_mcq(doc)
        answers = parse_2016_answer_key(doc)
        descriptors = parse_2016_descriptors(doc)
        assets_by_question = build_assets(ASSETS_2016, year)
        crop_assets(doc, ASSETS_2016, year)
        doc.close()
        ocr_used = False
        manual_corrections = [
            "Q11: restored the I-IV list to separate lines for readability.",
            "Q59(A): normalized “P K U” to “(PKU)”.",
            "Q64: normalized “S S R I s” to “SSRIs”.",
            "Q99(E): removed trailing “END OF SECTION I” instructions.",
            "Q72/Q83: rejoined line-broken hyphenated words.",
        ]
    else:
        pdf = PDF_2017
        paper_id = PAPER_ID_2017
        source_id = SOURCE_ID_2017
        title = "AP Psychology 2017 (100 MCQs + 2 FRQs)"
        chinese_title = "2017 年 AP 心理学（100 道选择题 + 2 道主观题）"
        source_file = "assets/psychology/papers/2017/2017.pdf"
        ocr_pages = load_2017_ocr(pdf, ocr_dir)
        parsed = parse_2017_mcq(ocr_pages)
        answers = ANSWER_2017
        descriptors = DESCRIPTORS_2017
        doc = fitz.open(pdf)
        assets_by_question = build_assets(ASSETS_2017, year)
        crop_assets(doc, ASSETS_2017, year)
        doc.close()
        ocr_used = True
        manual_corrections = [
            "Q15(B): restored the dropped line “perspective”.",
            "Q26: removed the space in “chromosome 21 ?”.",
            "Q31(A/C/D): restored “punishment”, “negative reinforcement”, and “differential reinforcement”.",
            "Q43: options are image-only; text is a placeholder pointing to the cropped scatterplot.",
            "Q48(E): removed trailing running-footer text.",
            "Q63: corrected OCR “According t Jean … lack o” to “According to Jean … lack of”.",
            "Q66(C): removed the spurious trailing “|”.",
            "Q74(C/D): restored “Conversion disorder” and “Tardive dyskinesia”.",
            "Q77(D): restored the dropped word “creativity”.",
            "Q80(E): restored “Social loafing”.",
            "Q82(B): corrected “interterence” to “interference”.",
            "Q91: normalized the printed “..” separators and punctuation.",
            "Q92: options are image-only; text is a placeholder pointing to the cropped graph.",
            "Q97: restored the five answer choices from the page image.",
            "Q13: normalized the dash in “motives—I”.",
        ]

    questions_mcq, descriptor_mismatches = build_question_rows(
        year, parsed, answers, descriptors, assets_by_question
    )
    frq_questions, rubrics = build_frq(year, source_file)
    questions = questions_mcq + frq_questions
    qa = make_qa(
        year,
        questions,
        rubrics,
        descriptor_mismatches,
        manual_corrections,
        ocr_used,
    )

    paper = {
        "paper_id": paper_id,
        "year": year,
        "title": title,
        "chinese_title": chinese_title,
        "subject_id": "psychology",
        "source_id": source_id,
        "paper_type": "real_exam",
        "source_file": source_file,
        "question_count": len(questions),
        "import_ready": False,
        "mcq_import_ready": True,
        "frq_import_ready": True,
        "blocking_issues": [
            "Dry run only: no database import has been performed.",
        ],
        "notes": [
            "MCQ answers come from the released PDF answer key.",
            "No MCQ explanations are printed in the source; options.explanation remains NULL.",
            "FRQ prompts and rubric parts come from the released PDF scoring guidelines.",
        ],
    }
    return {
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().date().isoformat(),
        "paper": paper,
        "questions": questions,
        "frq_rubrics": rubrics,
        "qa": qa,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--year",
        choices=["2016", "2017", "all"],
        default="all",
        help="paper to parse",
    )
    parser.add_argument(
        "--ocr-dir",
        type=Path,
        default=None,
        help="directory with 17.json..31.json OCR output for 2017",
    )
    args = parser.parse_args()

    EXTRACTION_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    years = [2016, 2017] if args.year == "all" else [int(args.year)]
    for year in years:
        payload = build_paper(year, args.ocr_dir)
        paper = payload["paper"]
        json_path = EXTRACTION_DIR / f"psychology-ap-{year}.json"
        report_path = REPORT_DIR / f"psychology-ap-{year}_report.md"
        json_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        write_report(
            year,
            paper,
            payload["questions"],
            payload["qa"],
            json_path,
            report_path,
        )
        print(
            f"{year}: {payload['qa']['mcq_count']} MCQ, "
            f"{payload['qa']['frq_count']} FRQ, "
            f"{payload['qa']['asset_count']} assets -> {json_path}"
        )


if __name__ == "__main__":
    main()
