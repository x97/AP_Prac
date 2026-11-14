#!/usr/bin/env python3
"""Build read-only unit mind maps from 心理学思维导图.pdf.

The PDF is a set of XMind-style maps. Each map is drawn with thin polylines
whose endpoints touch the label boxes. This script reconstructs the parent /
child tree from those endpoints, removes descriptive sentences that are not
knowledge points, and resolves labels to concepts in the current content
Release.

Output is a static JSON shipped with the API. It is not written into a
Release or into the content DB. Concept IDs are resolved at request time by
canonical name so a new Release can be activated without rebuilding this file.

Usage:
  python3 _tools/build_mindmaps.py --dry-run
  python3 _tools/build_mindmaps.py --write
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sqlite3
import sys
import unicodedata
from collections import defaultdict, deque
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path

import fitz

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PDF = REPO_ROOT / "心理学思维导图.pdf"
DEFAULT_KB = REPO_ROOT / "data" / "releases" / "current" / "knowledge.db"
DEFAULT_OUT = REPO_ROOT / "apps" / "api" / "app" / "content" / "data" / "psychology-mindmaps.json"
DEFAULT_REPORT = REPO_ROOT / "data" / "content" / "psychology" / "reports" / "mindmap_pdf_audit.md"

LIGATURES = {
    "ﬂ": "fl", "ﬁ": "fi", "ﬀ": "ff", "ﬃ": "ffi", "ﬄ": "ffl",
    "ﬅ": "ft", "ﬆ": "st", "ː": "fl",
}
# The PDF's embedded subset font drops the "fi" glyph in a few strings and
# inserts a space instead. These are the observed broken forms, not guesses.
TEXT_FIXES = {
    "De nition": "Definition",
    "de nition": "definition",
    "Con rmation": "Confirmation",
    "con rmation": "confirmation",
    "gure-ground": "figure-ground",
    "Self-ful lling": "Self-fulfilling",
    "self-ful lling": "self-fulfilling",
    "loa ng": "loafing",
    "implict": "implicit",
    "procedrual": "procedural",
    "structual": "structural",
    "reaserch": "research",
    "Devided": "Divided",
    "Represtnattiveness": "Representativeness",
    "Appercaption": "Apperception",
    "Ecoding": "Encoding",
    "specic": "specific",
    "xed": "fixed",
    "Inuence": "Influence",
    "In uence": "Influence",
    "Activetion": "Activation",
    "sonabulism": "Somnambulism",
    "Permistic": "Pessimistic",
    "Reex": "Reflex",
    "Re ex": "Reflex",
    "Absolutethreshold": "Absolute threshold",
    "DifferenceThreshold": "Difference threshold",
    "Dividedattention": "Divided attention",
    "Selectiveattention": "Selective attention",
}


def clean_label(raw: str) -> str:
    text = raw.replace("­", "").replace("​", "")
    for src, dst in LIGATURES.items():
        text = text.replace(src, dst)
    # The PDF has bilingual labels. Keep Latin text and ordinary punctuation;
    # CJK and broken GBK glyphs are not needed for the English map.
    text = "".join(ch if (ord(ch) < 128 or ch in "’‘“”–—") else " " for ch in text)
    text = " ".join(text.split())
    for src, dst in TEXT_FIXES.items():
        text = text.replace(src, dst)
    # Drop empty parentheses left after removing Chinese glosses.
    text = re.sub(r"\(\s*[;；,，\s]*\)", "", text)
    text = re.sub(r"\s+([,.;:])", r"\1", text)
    text = text.strip(" ;,，；")
    # Repair unbalanced opening parentheses caused by line clipping.
    if text.count("(") == text.count(")") + 1 and len(text) <= 48:
        text += ")"
    return text.strip()


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if ord(ch) < 128)
    text = text.lower().replace("’", "'")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def bbox_dist(point: tuple[float, float], bbox: tuple[float, float, float, float]) -> float:
    x, y = point
    x0, y0, x1, y1 = bbox
    return math.hypot(max(x0 - x, 0, x - x1), max(y0 - y, 0, y - y1))


@dataclass
class Label:
    text: str
    bbox: tuple[float, float, float, float]
    size: float
    fonts: list[str]
    bold: bool
    semi: bool


@dataclass
class TreeNode:
    label: str
    source: str = ""
    concept: str | None = None
    concept_score: float = 0.0
    supplement: dict | None = None
    children: list["TreeNode"] = field(default_factory=list)

    def count(self) -> int:
        return 1 + sum(child.count() for child in self.children)

    def walk(self):
        yield self
        for child in self.children:
            yield from child.walk()


def extract_labels(page: fitz.Page) -> list[Label]:
    labels: list[Label] = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            if not spans:
                continue
            text = clean_label("".join(span["text"] for span in spans))
            if not text:
                continue
            fonts = sorted({span["font"] for span in spans})
            size = max(span["size"] for span in spans)
            x0, y0, x1, y1 = line["bbox"]
            if y1 < 75 or y0 > 790 or size > 30:
                continue
            if not any(f.startswith(("Montserrat", "MicrosoftYaHei", "Arial")) for f in fonts):
                continue
            if re.fullmatch(r"\d+", text):
                continue
            labels.append(
                Label(
                    text=text,
                    bbox=(round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2)),
                    size=round(size, 2),
                    fonts=fonts,
                    bold=any(f.endswith("-Bold") for f in fonts),
                    semi=any(f.endswith("-SemiBold") for f in fonts),
                )
            )
    return merge_bold(labels)


def merge_bold(labels: list[Label]) -> list[Label]:
    """Merge a two-line root title such as 'Interaction of Heredity / and Environment'."""
    bolds = sorted((label for label in labels if label.bold), key=lambda l: (l.bbox[1], l.bbox[0]))
    others = [label for label in labels if not label.bold]
    if not bolds:
        return labels
    groups: list[list[Label]] = []
    for label in bolds:
        for group in groups:
            last = group[-1]
            gap = label.bbox[1] - last.bbox[3]
            overlap = min(last.bbox[2], label.bbox[2]) - max(last.bbox[0], label.bbox[0])
            if abs(last.size - label.size) < 0.4 and gap < max(2.0, last.size * 0.8) and overlap > 0:
                group.append(label)
                break
        else:
            groups.append([label])
    merged: list[Label] = []
    for group in groups:
        if len(group) == 1:
            merged.append(group[0])
            continue
        x0 = min(label.bbox[0] for label in group)
        y0 = min(label.bbox[1] for label in group)
        x1 = max(label.bbox[2] for label in group)
        y1 = max(label.bbox[3] for label in group)
        merged.append(
            Label(
                text=" ".join(label.text for label in group),
                bbox=(x0, y0, x1, y1),
                size=group[0].size,
                fonts=group[0].fonts,
                bold=True,
                semi=False,
            )
        )
    return merged + others


def extract_edges(page: fitz.Page, labels: list[Label], tol: float = 12.0) -> list[tuple[int, int]]:
    edges: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    for drawing in page.get_drawings():
        color = drawing["color"]
        if not color:
            continue
        # The map connectors are a light blue-grey. Other drawings are logo,
        # rules, or the large watermark.
        if not (abs(color[0] - 0.615) < 0.06 and abs(color[1] - 0.692) < 0.06 and abs(color[2] - 0.76) < 0.06):
            continue
        if (drawing.get("width") or 0) > 0.8:
            continue
        points: list[tuple[float, float]] = []
        for item in drawing["items"]:
            if item[0] == "l":
                points.extend([item[1], item[2]])
            elif item[0] == "c":
                points.extend([item[1], item[4]])
            elif item[0] == "re":
                rect = item[1]
                points.extend([(rect.x0, rect.y0), (rect.x1, rect.y1)])
        if len(points) < 2:
            continue
        clean_points: list[tuple[float, float]] = []
        for point in points:
            rounded = (round(point[0], 2), round(point[1], 2))
            if not clean_points or clean_points[-1] != rounded:
                clean_points.append(rounded)
        if len(clean_points) < 2:
            continue
        first, last = clean_points[0], clean_points[-1]

        def nearest(point):
            best = None
            for index, label in enumerate(labels):
                dist = bbox_dist(point, label.bbox)
                if best is None or dist < best[0]:
                    best = (dist, index)
            return best

        a, b = nearest(first), nearest(last)
        if not a or not b or a[0] > tol or b[0] > tol or a[1] == b[1]:
            continue
        edge = tuple(sorted((a[1], b[1])))
        if edge in seen:
            continue
        seen.add(edge)
        edges.append(edge)
    return edges


def build_tree(labels: list[Label], edges: list[tuple[int, int]], root_index: int):
    adjacency: dict[int, set[int]] = defaultdict(set)
    for a, b in edges:
        adjacency[a].add(b)
        adjacency[b].add(a)
    parent: dict[int, int | None] = {root_index: None}
    order = [root_index]
    queue = deque([root_index])
    while queue:
        node = queue.popleft()
        for child in sorted(adjacency[node], key=lambda i: labels[i].bbox[1]):
            if child in parent:
                continue
            parent[child] = node
            order.append(child)
            queue.append(child)
    children: dict[int, list[int]] = defaultdict(list)
    for child, p in parent.items():
        if p is not None:
            children[p].append(child)
    for child_list in children.values():
        child_list.sort(key=lambda i: labels[i].bbox[1])
    return parent, children, order


GENERIC_BRANCHES = {
    "definition", "function", "measurement", "phenomenon", "basic principles",
    "theories", "theory", "types", "type", "process", "factors", "approaches",
    "structure", "features", "effects", "examples", "principles", "stage",
    "stages", "sleep theories", "dream theories", "sleep disorders",
    "theories of auditory", "theories of color vision", "the structure of the ear",
    "structure of the eye", "tools for examining brain", "neural cells",
    "susceptibility", "diagnosis", "approaches",
}


DROP_LABELS = {
    "cognitive effects",
    "remember things to be done",
    "duration short less than 1 sec",
    "capacity large",
    "duration 1 min",
    "capacity 7 2",
    "duration long",
    "capacity unlimited",
    "biology based",
    "knowledge based",
    "generational changes",
    "pavlovs dogs",
}


def description_like(text: str) -> bool:
    text = text.strip()
    if not text:
        return True
    if re.fullmatch(r"\d+\s*(min|minutes?)", text, re.I):
        return True
    if len(text) > 55:
        return True
    if re.search(r"[.,;:]$", text):
        return True
    words = text.split()
    if len(words) > 7:
        return True
    if re.match(r"^(The|A|An|This|These|It|When|While|Because|If|Research|Studies|People|Our|Their|Its)\b", text, re.I) and len(words) >= 4:
        return True
    if re.search(r"\b(is|are|was|were|has|have|can|will|would|should|called|that|which|when|while|because)\b", text, re.I) and len(words) >= 4:
        return True
    if re.search(r"\b(of the|to the|in the|from the|by the|with the|on the|at the)\b", text, re.I) and len(words) >= 4:
        return True
    if text[0].islower() and len(words) >= 6:
        return True
    return False


def fragment_like(text: str) -> bool:
    """True for sentence fragments from the PDF, not knowledge-point labels.

    The PDF stores definitions as extra leaf labels next to a node. They have
    the same font as concepts, so length / grammar is the only reliable signal.
    Matched concepts are exempted by prune().
    """
    text = text.strip()
    if not text:
        return True
    if len(text) > 42:
        return True
    words = text.split()
    if len(words) >= 8:
        return True
    if "," in text and len(words) >= 3:
        return True
    if re.search(r"\b(and|or|with|for|in|to|of|from|by|than|when|that|which|while)\s*$", text, re.I):
        return True
    if re.match(
        r"^(The|A|An|This|These|It|When|While|Because|If|People|Research|Studies|"
        r"Include|Causes|Misfortune|Help|Expense|Control|Memory for|Mental illness|"
        r"Front of|Followed|Disturbed|Better than)\b",
        text,
        re.I,
    ) and len(words) >= 3:
        return True
    if re.search(r"\b(is|are|was|were|has|have|can|will|would|should|called)\b", text, re.I) and len(words) >= 3:
        return True
    if text[0].islower() and len(words) >= 4:
        return True
    return False


def title_case_label(text: str) -> str:
    if text.islower():
        return text[:1].upper() + text[1:]
    return text


DISPLAY_OVERRIDES = {
    "stage": "Sleep Stages",
    "sleep theories": "Sleep Theories",
    "dream theories": "Dream Theories",
    "sleep disorders": "Sleep Disorders",
    "body sense": "Body Senses",
    "lobe": "Lobes",
    "neural cells": "Neural Cells",
    "system that receives and sends messages": "Neuron Structure",
    "the neural firing impulse": "Neural Firing",
    "influence of drugs on neural firing": "Drugs & Neural Firing",
    "the spinal cord reflex": "Spinal Cord Reflex",
    "tools for examining brain": "Tools for Examining the Brain",
    "the structure of the ear": "Structure of the Ear",
    "concepts related to visual sensation": "Visual Sensation",
    "theories of auditory": "Theories of Auditory",
    "vision process": "Vision Process",
    "structure of the eye": "Structure of the Eye",
    "sympathetic": "Sympathetic Nervous System",
    "parasympathetic": "Parasympathetic Nervous System",
    "rem": "REM Sleep",
    "stage1": "Stage 1",
    "stage2": "Stage 2",
    "stage3 4": "Stage 3/4",
    "stage3/4": "Stage 3/4",
    "stage5": "Stage 5",
    "sleep deprivation": "Sleep Deprivation",
    "pain sense": "Pain Sense",
    "touch sense": "Touch Sense",
    "gustation": "Gustation",
    "smell": "Smell",
    "auditory": "Auditory",
    "vision": "Vision",
    "measurement": "Measurement",
    "phenomenon": "Phenomenon",
    "basic principles": "Basic Principles",
    "gestalt principles": "Gestalt Principles",
    "constancies": "Constancies",
    "visual perception": "Visual Perception",
    "attention": "Attention",
    "selected attention": "Selective Attention",
    "divided attention": "Divided Attention",
    "problem solving": "Problem Solving",
    "decision making": "Decision Making",
    "creativity": "Creativity",
    "memory models": "Memory Models",
    "levels of processing model": "Levels of Processing",
    "multi store information processing model": "Multi-Store Model",
    "encoding": "Encoding",
    "storage": "Storage",
    "retrieval": "Retrieval",
    "forgetting": "Forgetting",
    "enhancing retrieval": "Enhancing Retrieval",
    "with retrieval cue or not": "Recall & Recognition",
    "why we forget": "Why We Forget",
    "the ebbinghaus forgetting curve": "Ebbinghaus Forgetting Curve",
    "intelligence": "Intelligence",
    "theory": "Theories",
    "belief about intelligence": "Beliefs About Intelligence",
    "effect": "Effects",
    "psychological test": "Psychological Tests",
    "themes and methods": "Themes & Methods",
    "physical development": "Physical Development",
    "cognitive development": "Cognitive Development",
    "language": "Language",
    "gender and sexual orientation": "Gender & Sexual Orientation",
    "social- emotional development": "Social-Emotional Development",
    "classical conditioning": "Classical Conditioning",
    "operant conditioning": "Operant Conditioning",
    "social, cognitive, and neurological factors": "Social, Cognitive & Neurological Factors",
    "personality": "Personality",
    "attribution": "Attribution",
    "attitude": "Attitude",
    "motivation": "Motivation",
    "emotion": "Emotion",
    "psychology in social situation": "Psychology in Social Situations",
    "stress": "Stress",
    "disorders": "Disorders",
    "treatment": "Treatment",
}


# Explicit cross-walk for labels whose meaning is clear but does not fuzzy-match
# the canonical concept name. Keys are normalized PDF labels. A value of None
# means "keep as a label but do not resolve to a concept".
ALIASES: dict[str, str | None] = {
    # Unit 1
    "nature vs nurture": "Nature-nurture issue",
    "evolutionary perspective": "Evolutionary psychology",
    "reticular activating system ras": "Reticular formation",
    "lesioning studies": "Lesioning",
    "primary motor cortex": "Motor cortex",
    "sensory system afferent": "Sensory neurons (afferent neurons)",
    "motor system efferent": "Motor neurons (efferent neurons)",
    "sympathetic": "Sympathetic nervous system",
    "parasympathetic": "Parasympathetic nervous system",
    "absolute threshold": "Threshold",
    "difference threshold": "Threshold",
    "gate theory": "Gate control theory",
    "corti": "Cochlea",
    "theta low frequency and voltage": "Theta waves",
    "occasionally appear sleep spindles": "Sleep spindles",
    "slow wave sleep": "Delta sleep",
    "appear dream": "REM sleep",
    "rem": "REM sleep",
    "effect of sleep deprivation on cognitive": "Sleep deprived",
    "restorative theory": "Restoration of resources",
    "consolidation theory": "Consolidation theory of dreams",
    "activation synthesis theory": "Activation-synthesis theory of dreaming",
    "somnambulism": "Somnambulism (sleepwalking)",
    "dishabituation": "Sensory habituation",
    "identical monozygotic": "Identical twins (monozygotic twins)",
    "fraternal dizygotic": "Fraternal (dizygotic) twins",
    "left vs right functions": "Hemispheric specialization (brain lateralization)",
    "neural volleying theory": None,
    # Unit 2
    "bottom up processing": "Bottom-up processing",
    "top down processing": "Top-down processing",
    "figure ground illusion": "Figure-ground",
    "selected attention": "Selective attention",
    "divided attention": "Divided attention",
    "cocktail party effect": "Cocktail-party effect",
    "inattentional blindness": "Inattentional blindness",
    "change blindness": "Change blindness",
    "retinal disparity": "Retinal disparity",
    "visual cliff experiment": "Visual cliff",
    "monocular depth": "Monocular depth cues",
    "binocular depth": "Binocular depth cues",
    "availability heuristics": "Availability heuristic",
    "representativeness heuristics": "Representativeness heuristic",
    "functional fixedness": "Functional fixedness",
    "confirmation bias": "Confirmation bias",
    "belief perseverance": "Belief perseverance",
    "hindsight bias": "Hindsight bias",
    "gambler s fallacy": "Gambler's fallacy",
    "sunk cost fallacy": "Sunk-cost fallacy",
    "mental set": "Mental set",
    "convergent thinking": "Convergent thinking",
    "divergent thinking": "Divergent thinking",
    "prototype theory": "Prototype theory",
    "schema theory": "Schema theory",
    "assimilation": "Assimilation",
    "accommodation": "Accommodation",
    "algorithms": "Algorithm",
    "heuristic": "Heuristic",
    "priming": "Priming",
    "framing": "Framing",
    "declarative memory explicit memory": "Declarative memory",
    "nondeclarative memory implict memory": "Nondeclarative memory",
    "procedrual memory": "Procedural memory",
    "prospective memory": "Prospective memory",
    "retrospective memory": "Retrospective memory",
    "multi store information processing model": "Multi-store model",
    "levels of processing model": "Levels of processing model",
    "sensory memory": "Sensory memory",
    "short term memory": "Short-term memory",
    "long term memory": "Long-term memory",
    "shallow structual encoding": "Shallow encoding",
    "intermediate phonemic encoding": "Intermediate encoding",
    "deep semantic encoding": "Deep encoding",
    "mnemonic device": "Mnemonic",
    "serial position effect": "Serial position effect",
    "primacy effect": "Primacy effect",
    "recency effect": "Recency effect",
    "distributed practice": "Distributed practice",
    "chunking": "Chunking",
    "spacing effect distributional practice": "Spacing effect",
    "localized neural circuits": "Localized neural circuits",
    "long term potentiation ltp": "Long-term potentiation",
    "autobiographical memory": "Autobiographical memory",
    "infantile amnesia": "Infantile amnesia",
    "alzheimer s disease": "Alzheimer's disease",
    "with retrieval cue or not": "Recall",
    "recall": "Recall",
    "recognition": "Recognition",
    "context dependent memory": "Context-dependent memory",
    "mood congruent memory": "Mood-congruent memory",
    "state dependent memory": "State-dependent memory",
    "testing effect": "Testing effect",
    "metacognition": "Metacognition",
    "the ebbinghaus forgetting curve": "Ebbinghaus forgetting curve",
    "nonsense syllables": "Nonsense syllables",
    "retention": "Retention",
    "savings scores": "Savings score",
    "encoding failure theory": "Encoding failure",
    "interference theory": "Interference",
    "retroactive interference": "Retroactive interference",
    "proactive interference": "Proactive interference",
    "decay theory": "Decay",
    "tip of the tongue phenomenon": "Tip-of-the-tongue phenomenon",
    "repression": "Repression",
    "the misinformation effect": "Misinformation effect",
    "source monitoring source amnesia": "Source amnesia",
    "constructive memory": "Constructive memory",
    "imagination ination": "Imagination",
    "spearman s g factor": "Spearman's g factor",
    "gardners multiple intelligences": "Gardner's multiple intelligences",
    "crystallized fluid intelligence": "Crystallized intelligence",
    "fixed mindset": "Fixed mindset",
    "growth mindset": "Growth mindset",
    "alfred binet": "Alfred Binet",
    "david wechsler deviation iq scores": "David Wechsler",
    "the flynn effect": "Flynn effect",
    "stereotype threat lift": "Stereotype threat",
    "aptitude test": "Aptitude test",
    "achievement test": "Achievement test",
    "standardization": "Standardization",
    "test norms": "Test norms",
    "percentile score": "Percentile score",
    "reliability": "Reliability",
    "test retest reliability": "Test-retest reliability",
    "split half reliability": "Split-half reliability",
    "validity": "Validity",
    "construct validity": "Construct validity",
    "predictive validity": "Predictive validity",
    # Cross-unit / false-match guards
    "unconditioned stimulus ucs": "Unconditioned stimulus (US or UCS)",
    "unconditioned response ucr": "Unconditioned response (UR or UCR)",
    "conscious": None,
    "retrospective memory": None,
    "recall recognition": None,
    "internal": "Internal locus of control",
    "external": "External locus of control",
    "manic depressive disorder": None,
    "personality disorder": None,
    "stereotype prejudice discrimination": None,
    "stage3 4": "Delta sleep",
    "stimulus discrimination": "Discrimination (conditioning)",
    "higher order learning": "Higher-order conditioning",
    "one trial learning": "Taste aversion",
    "garcia s aversion": "Garcia effect",
    "garcias aversion": "Garcia effect",
    "fifixed ratio": "Fixed-ratio (FR) schedule",
    "fixed ratio": "Fixed-ratio (FR) schedule",
    "fifixed interval": "Fixed-interval (FI) schedule",
    "fixed interval": "Fixed-interval (FI) schedule",
    "variable ratio": "Variable-ratio (VR) schedule",
    "variable interval": "Variable-interval (VI) schedule",
    "social norm": "Norms",
    "rotter s locus of control theory": "Locus of control",
    "just world hypothesis": "Just-world phenomenon",
    "relative deprivation": "Relative deprivation theory",
    "social comparison": None,
    "upward": "Upward social comparison",
    "downward": "Downward social comparison",
    "attribution theory": "Attribution theory",
    "social reciprocity norm": "Norms of reciprocity",
    "shallow structural encoding": "Shallowly encoded",
    "deep semantic encoding": "Deeply encoded",
    "encoding failure theory": "Encoding failure",
    "spearman s g factor": "General intelligence (g)",
    "spearmans g factor": "General intelligence (g)",
    "gardners multiple intelligences": "Multiple intelligences",
    "david wechsler": "Wechsler Adult Intelligence Scale (WAIS)",
}



class MindMapPage:
    def __init__(self, pdf: fitz.Document, pageno: int, tol: float = 12.0):
        self.pageno = pageno
        self.page = pdf[pageno - 1]
        self.labels = extract_labels(self.page)
        self.edges = extract_edges(self.page, self.labels, tol=tol)
        roots = [i for i, label in enumerate(self.labels) if label.bold]
        if not roots:
            raise RuntimeError(f"page {pageno}: no bold root label")
        self.root = max(roots, key=lambda i: self.labels[i].size)
        self.parent, self.children, self.order = build_tree(self.labels, self.edges, self.root)

    def find_path(self, path: list[str]) -> int | None:
        """Find a node by an exact root-to-node label path.

        If two siblings share a label (for example the two "Theories" nodes
        under Personality), both are tried; the first subtree that reaches the
        requested leaf wins.
        """

        def rec(node: int, parts: list[str]) -> int | None:
            if not parts:
                return node
            if norm(self.labels[node].text) != norm(parts[0]):
                return None
            if len(parts) == 1:
                return node
            for child in self.children[node]:
                if norm(self.labels[child].text) == norm(parts[1]):
                    found = rec(child, parts[1:])
                    if found is not None:
                        return found
            return None

        return rec(self.root, path)


def node_from_page(
    page: MindMapPage,
    index: int,
    concepts: list[dict],
    stats: dict,
) -> TreeNode:
    source_label = page.labels[index].text
    display = DISPLAY_OVERRIDES.get(norm(source_label)) or title_case_label(source_label)
    matched, score = match_concept(source_label, concepts)
    node = TreeNode(
        label=display,
        source=f"p{page.pageno}:{source_label}",
    )
    if matched and score >= 0.86:
        node.concept = matched["name"]
        node.concept_score = round(score, 2)
    for child_index in page.children[index]:
        node.children.append(node_from_page(page, child_index, concepts, stats))
    return node


def prune(node: TreeNode) -> TreeNode | None:
    """Drop descriptive leaves and empty generic branch labels."""
    node.children = [child for child in (prune(c) for c in node.children) if child is not None]
    if node.children:
        return node
    if node.concept or node.supplement:
        return node
    key = norm(node.label)
    if key in DROP_LABELS:
        return None
    if key in GENERIC_BRANCHES:
        return None
    if fragment_like(node.label) or description_like(node.label):
        return None
    return node


@dataclass
class RootSpec:
    page: int
    path: list[str]
    display: str | None = None


@dataclass
class TopicSpec:
    code: str
    title: str
    roots: list[RootSpec]
    include: list[str] | None = None
    exclude: list[str] | None = None


UNIT_TITLES = {
    "1": "Biological Bases of Behavior",
    "2": "Cognition",
    "3": "Development and Learning",
    "4": "Social Psychology and Personality",
    "5": "Mental and Physical Health",
}

PAGE_TOL = {41: 16.0, 50: 8.0}

TOPIC_SPECS: dict[str, list[TopicSpec]] = {
    "1": [
        TopicSpec("1.1", "Interaction of Heredity and Environment", [RootSpec(15, ["Interaction of Heredity and Environment"], "Heredity & Environment")]),
        TopicSpec("1.2", "Overview of the Nervous System", [
            RootSpec(14, ["UNIT 1", "Nervous System and the Neuron", "Nervous System"], "Nervous System"),
            RootSpec(14, ["UNIT 1", "The Endocrine System"], "Endocrine System"),
        ]),
        TopicSpec("1.3", "The Neuron and Neural Firing", [RootSpec(17, ["Nervous System and the Neuron", "Neuron"], "Neuron & Neural Firing")]),
        TopicSpec("1.4", "The Brain", [RootSpec(18, ["Brain"], "Brain")]),
        TopicSpec("1.5", "Sleep", [RootSpec(14, ["UNIT 1", "Sleep and Dreaming"], "Sleep & Dreaming")]),
        TopicSpec("1.6", "Sensation", [RootSpec(20, ["Sensation"], "Sensation")]),
    ],
    "2": [
        TopicSpec("2.1", "Perception", [RootSpec(24, ["Perception"], "Perception")]),
        TopicSpec("2.2", "Thinking, Problem-Solving, Judgments, and Decision-Making", [RootSpec(25, ["Problem Solving"], "Problem Solving")]),
        TopicSpec("2.3", "Introduction to Memory", [RootSpec(26, ["Memory", "Introduction"], "Introduction")]),
        TopicSpec("2.4", "Encoding Memories", [RootSpec(26, ["Memory", "Encoding"], "Encoding")]),
        TopicSpec("2.5", "Storing Memories", [RootSpec(26, ["Memory", "Storage"], "Storage")]),
        TopicSpec("2.6", "Retrieving Memories", [RootSpec(26, ["Memory", "Retrieval"], "Retrieval")]),
        TopicSpec("2.7", "Forgetting and Other Memory Challenges", [RootSpec(26, ["Memory", "Forgetting"], "Forgetting")]),
        TopicSpec("2.8", "Intelligence and Achievement", [RootSpec(27, ["Intelligence"], "Intelligence")]),
    ],
    "3": [
        TopicSpec("3.1", "Themes and Methods in Developmental Psychology", [RootSpec(32, ["Development", "Themes and methods"], "Themes & Methods")]),
        TopicSpec("3.2", "Physical Development Across the Lifespan", [RootSpec(32, ["Development", "Physical Development"], "Physical Development")]),
        TopicSpec("3.3", "Gender and Sexual Orientation", [RootSpec(32, ["Development", "Gender and Sexual Orientation"], "Gender & Sexual Orientation")]),
        TopicSpec("3.4", "Cognitive Development Across the Lifespan", [RootSpec(32, ["Development", "Cognitive Development"], "Cognitive Development")]),
        TopicSpec("3.5", "Communication and Language Development", [RootSpec(32, ["Development", "Language"], "Language")]),
        TopicSpec("3.6", "Social-Emotional Development Across the Lifespan", [RootSpec(32, ["Development", "Social- emotional Development"], "Social-Emotional Development")]),
        TopicSpec("3.7", "Classical Conditioning", [RootSpec(33, ["Classical conditioning"], "Classical Conditioning")]),
        TopicSpec("3.8", "Operant Conditioning", [RootSpec(34, ["Operant conditioning"], "Operant Conditioning")]),
        TopicSpec("3.9", "Social, Cognitive, and Neurological Factors in Learning", [RootSpec(35, ["Social, Cognitive, and Neurological Factors in Learning"], "Social, Cognitive & Neurological Factors")]),
    ],
    "4": [
        TopicSpec("4.1", "Attribution Theory and Person Perception", [RootSpec(40, ["Attribution"], "Attribution")]),
        TopicSpec("4.2", "Attitude Formation and Attitude Change", [RootSpec(41, ["Attitude"], "Attitude")]),
        TopicSpec("4.3", "Psychology of Social Situations", [RootSpec(42, ["Psychology in social situation"], "Psychology in Social Situations")]),
        TopicSpec("4.4", "Psychodynamic and Humanistic Theories of Personality", [
            RootSpec(43, ["Personality", "Theories", "Psychodynamic"], "Psychodynamic"),
            RootSpec(43, ["Personality", "Theories", "Humanistic"], "Humanistic"),
        ]),
        TopicSpec("4.5", "Social-Cognitive and Trait Theories of Personality", [
            RootSpec(43, ["Personality", "Theories", "Bandura’s Social Cognitive Theory"], "Social-Cognitive"),
            RootSpec(43, ["Personality", "Theories", "Trait Theories"], "Trait Theories"),
        ]),
        TopicSpec("4.6", "Motivation", [RootSpec(44, ["Motivation"], "Motivation")]),
        TopicSpec("4.7", "Emotion", [RootSpec(45, ["Emotion"], "Emotion")]),
    ],
    "5": [
        TopicSpec("5.1", "Introduction to Health Psychology", [RootSpec(51, ["Stress"], "Stress & Health")], exclude=["Positive Psychology"]),
        TopicSpec("5.2", "Positive Psychology", [RootSpec(51, ["Stress", "Positive Psychology"], "Positive Psychology")]),
        TopicSpec("5.3", "Explaining and Classifying Psychological Disorders", [RootSpec(49, ["UNIT 5", "Disorders"], "Disorders: Diagnosis & Approaches")], include=["Diagnosis", "Approaches"]),
        TopicSpec("5.4", "Selection of Categories of Psychological Disorders", [RootSpec(52, ["Disorders"], "Disorders: Categories")], exclude=["Diagnosis"]),
        TopicSpec("5.5", "Treatment of Psychological Disorders", [RootSpec(53, ["Treatment"], "Treatment")]),
    ],
}


# ---------------------------------------------------------------------------
# Curated Unit 1 trees
#
# The PDF map is a good skeleton but its tiny labels contain clipped
# descriptions, duplicate labels and a few missing concepts. Unit 1 is the
# free preview and the flagship map, so its trees are curated from the PDF
# hierarchy + the knowledge DB + the standard AP Psychology scope. Every
# concept name below is validated against the current Unit 1 concept table;
# if a concept is not in the DB it stays as an English label only.


@dataclass
class CuratedNode:
    label: str
    concept: str | None = None
    children: list["CuratedNode"] = field(default_factory=list)


def C(label: str, *children: CuratedNode, concept: str | None = None) -> CuratedNode:
    return CuratedNode(label=label, concept=concept, children=list(children))


def K(label: str, concept: str, *children: CuratedNode) -> CuratedNode:
    return CuratedNode(label=label, concept=concept, children=list(children))


CURATED_TOPICS: dict[str, list[CuratedNode]] = {
    "2.5": [
        K("Memory Consolidation", "Memory consolidation"),
        K("Long-Term Potentiation", "Long-term potentiation"),
        C("Brain Structures",
          K("Hippocampus", "Hippocampus"),
          C("Cerebellum"),
          C("Amygdala")),
        K("Explicit Memory", "Explicit memory",
          K("Episodic Memory", "Episodic memory"),
          K("Semantic Memory", "Semantic memory")),
        K("Implicit Memory", "Implicit memory",
          K("Procedural Memory", "Procedural memory")),
        C("Storage Problems",
          K("Anterograde Amnesia", "Anterograde amnesia"),
          K("Retrograde Amnesia", "Retrograde amnesia")),
    ],
    "2.6": [
        C("Recall & Recognition",
          K("Recall", "Recall"),
          K("Recognition", "Recognition")),
        K("Retrieval Cues", "Retrieval cues",
          C("Context-Dependent Memory"),
          K("State-Dependent Memory", "State-dependent memory"),
          K("Mood-Congruent Memory", "Mood-congruent memory")),
        C("Enhancing Retrieval",
          K("Testing Effect", "Testing effect"),
          K("Spacing Effect", "Spacing effect"),
          K("Interleaving", "Interleaving")),
        C("Memory Distortion",
          K("Tip-of-the-Tongue Phenomenon", "Tip-of-the-tongue phenomenon"),
          K("Flashbulb Memory", "Flashbulb memory"),
          K("Encoding Specificity", "Encoding specificity principle")),
        C("Metacognition"),
    ],
    "3.1": [
        K("Nature vs Nurture", "Nature versus nurture"),
        C("Continuity vs Discontinuity"),
        C("Stability vs Change"),
        C("Research Designs",
          K("Cross-Sectional Research", "Cross-sectional research"),
          K("Longitudinal Research", "Longitudinal research"),
          C("Naturalistic Observation"),
          C("Meta-Analysis")),
        K("Developmental Psychology", "Developmental psychology"),
        C("Ethics & Bias",
          C("Experimenter Bias"),
          C("Informed Consent"),
          C("Confidentiality")),
    ],
    "3.3": [
        C("Sex vs Gender",
          K("Sex", "Sex"),
          K("Gender", "Gender")),
        K("Gender Identity", "Gender identity"),
        K("Gender Roles", "Gender roles"),
        C("Gender Stereotypes"),
        K("Gender Schema Theory", "Gender schema theory"),
        K("Social-Cognitive Theory", "Social-cognitive theory"),
        C("Biological Influences",
          K("Biopsychological Theory", "Biopsychological (Neuropsychological) Theory"),
          K("Primary Sex Characteristics", "Primary sex characteristics"),
          K("Secondary Sex Characteristics", "Secondary sex characteristics")),
        C("Sexual Orientation"),
    ],
    "3.4": [
        C("Piaget",
          C("Schema Theory"),
          K("Assimilation", "Assimilation"),
          K("Accommodation", "Accommodation (developmental)"),
          C("Piaget's Stages",
            K("Sensorimotor Stage", "Sensorimotor stage"),
            K("Preoperational Stage", "Preoperational stage"),
            K("Concrete Operational Stage", "Concrete operational stage"),
            K("Formal Operational Stage", "Formal operational stage")),
          K("Object Permanence", "Object permanence"),
          K("Conservation", "Conservation"),
          K("Egocentrism", "Egocentric"),
          K("Theory of Mind", "Theory of mind")),
        C("Vygotsky",
          K("Zone of Proximal Development", "Zone of proximal development"),
          K("Scaffolding", "Scaffold")),
        C("Language & Thought"),
        C("Fluid vs Crystallized Intelligence"),
        C("Dementia"),
    ],
    "4.2": [
        C("Attitude Formation",
          K("Attitude", "Attitude"),
          K("Implicit Attitude", "Implicit attitude")),
        C("Attitude Change",
          K("Cognitive Dissonance", "Cognitive dissonance theory"),
          K("Persuasion", "Persuasion",
            K("Central Route", "Central route to persuasion"),
            K("Peripheral Route", "Peripheral route persuasion")),
          K("Elaboration Likelihood Model", "Elaboration likelihood model")),
        C("Bias & Prejudice",
          C("Stereotype / Prejudice / Discrimination"),
          K("Just-World Phenomenon", "Just-world phenomenon"),
          K("In-Group / Out-Group Bias", "In-group bias"),
          K("Belief Perseverance", "Belief perseverance"),
          K("Confirmation Bias", "Confirmation bias")),
        K("Self-Fulfilling Prophecy", "Self-fulfilling prophecy"),
    ],
    "4.5": [
        K("Bandura's Social-Cognitive Theory", "Social-cognitive theory",
          K("Observational Learning", "Observational learning"),
          K("Reciprocal Determinism", "Reciprocal determinism"),
          K("Self-Efficacy", "Self-efficacy"),
          K("Self-Esteem", "Self-esteem")),
        K("Locus of Control", "Locus of control",
          K("Internal Locus of Control", "Internal locus of control"),
          K("External Locus of Control", "External locus of control")),
        C("Trait Theories",
          K("Factor Analysis", "Factor analysis"),
          K("Big Five", "Big Five personality traits",
            C("Openness"),
            C("Conscientiousness"),
            C("Extraversion"),
            C("Agreeableness"),
            C("Neuroticism")),
          K("Personality Inventories", "Personality inventories")),
        C("Person-Situation Controversy"),
    ],
    "5.2": [
        K("Positive Psychology", "Positive psychology"),
        K("Subjective Well-Being", "Subjective well-being"),
        K("Character Strengths", "Character strengths"),
        K("Gratitude", "Gratitude"),
        K("Post-Traumatic Growth", "Post-traumatic growth"),
        K("Mindfulness", "Mindfulness meditation"),
        K("Well-Being", "Well-being"),
    ],
    "2.2": [
        C("Theories",
          K("Prototype Theory", "Prototype"),
          K("Schema Theory", "Schema",
            C("Assimilation"),
            C("Accommodation"))),
        C("Problem Solving",
          K("Algorithms", "Algorithm"),
          K("Heuristics", "Heuristic",
            K("Availability Heuristic", "Availability heuristic"),
            K("Representativeness Heuristic", "Representativeness heuristic"))),
        C("Obstacles",
          K("Functional Fixedness", "Functional fixedness"),
          K("Mental Set", "Mental set")),
        C("Decision Making & Judgment",
          K("Framing", "Framing"),
          C("Hindsight Bias"),
          K("Confirmation Bias", "Confirmation bias"),
          K("Belief Perseverance", "Belief perseverance"),
          K("Gambler's Fallacy", "Gambler’s fallacy"),
          K("Sunk-Cost Fallacy", "Sunk-cost fallacy"),
          C("Priming")),
        K("Creativity", "Creativity",
          K("Convergent Thinking", "Convergent thinking"),
          K("Divergent Thinking", "Divergent thinking")),
    ],
    "3.2": [
        C("Prenatal Development",
          K("Teratogens", "Teratogens"),
          K("Fetal Alcohol Syndrome", "Fetal alcohol syndrome (FAS)"),
          K("Critical Period", "Critical period")),
        C("Infancy",
          K("Reflexes", "Reflexes",
            K("Rooting Reflex", "Rooting reflex"),
            K("Sucking Reflex", "Sucking reflex"),
            K("Grasping Reflex", "Grasping reflex"),
            K("Babinski Reflex", "Babinski reflex"),
            K("Moro Reflex", "Moro reflex")),
          K("Motor Development", "Motor development",
            C("Gross to Fine"),
            C("Head to Foot")),
          K("Imprinting", "Imprinting")),
        C("Adolescence",
          K("Puberty", "Puberty"),
          K("Primary Sex Characteristics", "Primary sex characteristics"),
          K("Secondary Sex Characteristics", "Secondary sex characteristics"),
          K("Menarche", "Menarche"),
          K("Spermarche", "Spermarche")),
        C("Adulthood",
          K("Menopause", "Menopause"),
          C("Hormonal Changes"),
          C("Hearing & Vision Decline"),
          C("Dementia")),
    ],
    "3.6": [
        K("Ecological Systems Theory", "Ecological systems theory",
          K("Microsystem", "Microsystem"),
          K("Mesosystem", "Mesosystem"),
          K("Exosystem", "Exosystem"),
          K("Macrosystem", "Macrosystem"),
          K("Chronosystem", "Chronosystem")),
        C("Parenting Styles",
          K("Authoritarian", "Authoritarian parents"),
          K("Permissive", "Permissive parents"),
          K("Authoritative", "Authoritative parents"),
          C("Neglectful")),
        K("Attachment", "Attachment",
          K("Harlow & Contact Comfort", "Contact comfort"),
          K("Strange Situation", "Strange situation"),
          K("Secure Attachment", "Secure attachment"),
          K("Avoidant Attachment", "Avoidant attachment"),
          K("Anxious / Ambivalent Attachment", "Anxious/ambivalent attachment"),
          C("Disorganized Attachment")),
        K("Temperament", "Temperament"),
        C("Play",
          C("Pretend Play"),
          C("Parallel Play")),
        C("Adolescent Development",
          K("Adolescent Egocentrism", "Adolescent egocentrism"),
          K("Imaginary Audience", "Imaginary audience"),
          C("Identity Statuses (Marcia)"),
          K("Erikson's Psychosocial Stages", "Erikson's psychosocial stage theory")),
        C("Adverse Childhood Experiences (ACEs)"),
    ],
    "3.9": [
        K("Latent Learning", "Latent learning",
          K("Cognitive Maps", "Cognitive map")),
        K("Observational Learning", "Observational learning",
          K("Modeling", "Modeling"),
          K("Mirror Neurons", "Mirror neurons"),
          K("Vicarious Conditioning", "Vicarious conditioning")),
        K("Insight Learning", "Insight learning"),
        K("Cognitive Learning", "Cognitive learning"),
        C("Self-Efficacy"),
    ],
    "4.4": [
        K("Psychodynamic", "Psychodynamic theories",
          K("Freud's Structure of Personality", "Psychoanalysis (theory)",
            K("Id", "Id"),
            K("Ego", "Ego"),
            K("Superego", "Superego")),
          C("Levels of Awareness",
            C("Conscious"),
            C("Preconscious"),
            K("Unconscious", "Unconscious")),
          K("Anxiety & Defense Mechanisms", "Defense mechanisms",
            K("Repression", "Repression"),
            K("Projection", "Projection"),
            K("Reaction Formation", "Reaction Formation"),
            K("Rationalization", "Rationalization"),
            K("Denial", "Denial"),
            K("Displacement", "Displacement"),
            K("Sublimation", "Sublimation")),
          C("Psychosexual Stages"),
          K("Projective Tests", "Projective tests",
            K("Rorschach Inkblot", "Rorschach inkblot test"),
            K("Thematic Apperception Test (TAT)", "Thematic apperception test (TAT)"))),
        C("Humanistic",
          K("Rogers's Person-Centered Theory", "Person-centered therapy",
            K("Self-Concept", "Self-concept"),
            C("Incongruence"),
            K("Unconditional Positive Regard", "Unconditional positive regard")),
          K("Self-Actualization", "Self-actualization")),
    ],
    "5.3": [
        C("Defining Abnormality",
          C("Deviance"),
          C("Personal Distress"),
          C("Maladaptive Behavior")),
        K("Diagnosis", "Diagnostic and Statistical Manual of Mental Disorders (DSM)",
          K("DSM-5-TR", "DSM-5-TR"),
          K("Diathesis-Stress Model", "Diathesis-stress model")),
        C("Theoretical Approaches",
          K("Psychodynamic", "Psychodynamic therapy"),
          K("Humanistic", "Humanistic therapies"),
          K("Cognitive", "Cognitive therapy"),
          K("Evolutionary", "Evolutionary (or Darwinian) Perspective"),
          C("Sociocultural"),
          C("Biological")),
        C("Classification",
          K("Categories of Disorders", "Categories of Disorders")),
    ],
    "5.4": [
        K("Schizophrenia Spectrum", "Schizophrenia spectrum disorders",
          K("Schizophrenia", "Schizophrenia"),
          K("Delusions", "Delusions"),
          K("Hallucinations", "Hallucinations"),
          K("Positive Symptoms", "Positive symptoms"),
          K("Negative Symptoms", "Negative symptoms"),
          C("Etiology",
            C("Genetic Vulnerability"),
            C("Neurochemical Factors"),
            C("Neurodevelopmental Hypothesis"),
            C("Expressed Emotion"))),
        C("Mood Disorders",
          K("Major Depressive Disorder", "Major depressive disorder"),
          K("Persistent Depressive Disorder", "Persistent depressive disorder"),
          K("Bipolar I Disorder", "Bipolar I disorder"),
          K("Bipolar II Disorder", "Bipolar II disorder"),
          K("Mania", "Mania"),
          K("Hypomania", "Hypomania"),
          C("Etiology",
            C("Genetic Factors"),
            C("Neurochemical Factors"),
            C("Cognitive Factors"))),
        K("Anxiety Disorders", "Anxiety disorders",
          K("Generalized Anxiety Disorder (GAD)", "Generalized anxiety disorder (GAD)"),
          K("Panic Disorder", "Panic disorder"),
          K("Specific Phobia", "Specific phobia"),
          K("Social Anxiety Disorder", "Social anxiety disorder"),
          K("Agoraphobia", "Agoraphobia"),
          C("Etiology",
            C("Biological Factors"),
            C("Conditioning & Learning"),
            C("Cognitive Factors"),
            C("Stress"))),
        K("Obsessive-Compulsive Disorder (OCD)", "Obsessive-compulsive disorder (OCD)",
          C("Obsessions"),
          C("Compulsions"),
          K("Hoarding Disorder", "Hoarding disorder")),
        K("Dissociative Disorders", "Dissociative disorders",
          K("Dissociative Amnesia", "Dissociative amnesia"),
          C("Dissociative Fugue"),
          K("Dissociative Identity Disorder (DID)", "Dissociative identity disorder (DID)")),
        K("Post-Traumatic Stress Disorder (PTSD)", "Post-traumatic stress disorder (PTSD)"),
        C("Eating Disorders",
          K("Anorexia Nervosa", "Anorexia nervosa"),
          K("Bulimia Nervosa", "Bulimia"),
          K("Binge-Eating Disorder", "Binge-eating disorder"),
          C("Etiology")),
        C("Personality Disorders",
          K("Antisocial Personality Disorder", "Antisocial personality disorder"),
          K("Borderline Personality Disorder", "Borderline personality disorder"),
          K("Narcissistic Personality Disorder", "Narcissistic personality disorder"),
          C("Histrionic Personality Disorder")),
        K("Neurodevelopmental Disorders", "Neurodevelopmental disorders",
          K("ADHD", "Attention-deficit/hyperactivity disorder (ADHD)"),
          K("Autism Spectrum Disorder", "Autism spectrum disorder")),
    ],
    "5.5": [
        K("Insight Therapies", "Insight therapies",
          K("Psychoanalysis", "Psychoanalysis (therapy)",
            K("Free Association", "Free association"),
            K("Interpretation", "Interpretation"),
            K("Resistance", "Resistance"),
            K("Transference", "Transference")),
          K("Humanistic Therapy", "Humanistic therapies",
            K("Person-Centered Therapy", "Person-centered therapy"),
            K("Active Listening", "Active listening"),
            K("Unconditional Positive Regard", "Unconditional positive regard")),
          K("Group Therapy", "Group therapy"),
          K("Family Therapy", "Family therapy")),
        K("Behavior Therapies", "Behavior therapy",
          K("Systematic Desensitization", "Systematic desensitization"),
          K("Exposure Therapies", "Exposure therapies"),
          K("Aversion Therapy", "Aversive therapy"),
          K("Token Economy", "Token economy")),
        C("Cognitive Therapies",
          K("Cognitive Therapy", "Cognitive therapy"),
          K("Rational-Emotive Behavior Therapy (REBT)", "Rational emotive behavior therapy (REBT)"),
          K("Cognitive Behavioral Therapy (CBT)", "Cognitive behavioral therapy (CBT)")),
        K("Biomedical Therapies", "Biomedical model",
          K("Antipsychotic Drugs", "Antipsychotic drugs"),
          K("Antidepressant Drugs", "Antidepressant drugs"),
          K("Antianxiety Drugs", "Antianxiety drugs"),
          K("Electroconvulsive Therapy (ECT)", "Electroconvulsive therapy (ECT)")),
        K("Eclectic Therapy", "Eclectic therapy"),
    ],
}


# Definitions for real curriculum terms that the current knowledge DB does not
# cover (or covers only in another Unit). These are deliberately short,
# textbook-level explanations. `review_status=draft` means they should be
# checked against the 2027 textbook before high-stakes use.
RENAMES: dict[tuple[str, str, str, str], str] = {
    ("3", "3.2", "motor development", "gross to fine"): "Gross-to-Fine Direction",
    ("3", "3.2", "motor development", "head to foot"): "Head-to-Foot Direction",
    ("3", "3.8", "reinforcement", "positive"): "Positive Reinforcement",
    ("3", "3.8", "reinforcement", "negative"): "Negative Reinforcement",
    ("3", "3.8", "punishment", "positive"): "Positive Punishment",
    ("3", "3.8", "punishment", "negative"): "Negative Punishment",
    ("4", "4.1", "explanatory style", "optimistic"): "Optimistic Explanatory Style",
    ("4", "4.1", "explanatory style", "pessimistic"): "Pessimistic Explanatory Style",
    ("4", "4.3", "social influence theory", "informational"): "Informational Social Influence",
    ("4", "4.3", "social influence theory", "social"): "Normative Social Influence",
    ("4", "4.7", "broaden and build theory", "positive negative emotions"): "Positive and Negative Emotions",
    ("4", "4.7", "theories", "universal evolutionary theories primary"): "Universal/Evolutionary Theories of Emotion",
    ("5", "5.1", "stressor", "motivating eustress"): "Eustress",
    ("5", "5.1", "stressor", "debilitating distress"): "Distress",
    ("5", "5.1", "general adaptation syndrome gas", "alarm"): "Alarm Reaction",
    ("5", "5.3", "theoretical approaches", "evolutionary"): "Evolutionary Perspective",
    ("5", "5.3", "theoretical approaches", "sociocultural"): "Sociocultural Perspective",
    ("5", "5.3", "theoretical approaches", "biological"): "Biological Perspective",
}


def rename_nodes(node: TreeNode, unit: str, topic_code: str, parent_label: str | None = None) -> None:
    key = (unit, topic_code, norm(parent_label or ""), norm(node.label))
    if key in RENAMES:
        node.label = RENAMES[key]
    for child in node.children:
        rename_nodes(child, unit, topic_code, node.label)


SUPPLEMENTS: dict[tuple[str, str], dict] = {
    # Unit 1
    ("1", "family studies"): {
        "definition": "Research that compares relatives to estimate how much a trait is influenced by shared genes and shared environment.",
    },
    ("1", "adoption studies"): {
        "definition": "Research comparing adopted children with their biological and adoptive relatives to separate genetic from environmental influences.",
    },
    ("1", "adaptation"): {
        "definition": "An inherited or learned characteristic that increases an organism's chances of survival and reproduction.",
    },
    ("1", "survival reproduction"): {
        "name": "Survival & Reproduction",
        "definition": "The evolutionary outcomes favored by natural selection: living long enough to reproduce and passing genes to the next generation.",
    },
    ("1", "eugenics"): {
        "definition": "The discredited attempt to improve a population's genetic quality through selective breeding or reproduction policies.",
    },
    ("1", "brain"): {
        "definition": "The organ of the central nervous system that integrates sensory information, coordinates behavior, and supports cognition.",
    },
    ("1", "glands"): {
        "definition": "Organs that secrete hormones into the bloodstream.",
    },
    ("1", "pituitary gland"): {
        "definition": "The 'master gland' at the base of the brain that releases hormones controlling growth, reproduction, and other endocrine glands.",
    },
    ("1", "adrenaline epinephrine"): {
        "name": "Adrenaline / Epinephrine",
        "definition": "A hormone and neurotransmitter released by the adrenal glands that increases arousal and supports the fight-or-flight response.",
    },
    ("1", "leptin ghrelin"): {
        "name": "Leptin & Ghrelin",
        "definition": "Appetite-regulating hormones: leptin signals satiety, while ghrelin signals hunger.",
    },
    ("1", "melatonin"): {
        "definition": "A hormone secreted by the pineal gland that helps regulate the sleep-wake cycle and circadian rhythm.",
    },
    ("1", "oxytocin"): {
        "definition": "A hormone associated with bonding, trust, childbirth, and social affiliation.",
    },
    ("1", "homeostasis"): {
        "definition": "The body's tendency to maintain a stable internal state around a set point.",
    },
    ("1", "repolarization"): {
        "definition": "The phase of an action potential in which the neuron's membrane potential returns toward its resting negative charge.",
    },
    ("1", "refractory period"): {
        "definition": "A brief period after an action potential when a neuron cannot fire again or is harder to excite.",
    },
    ("1", "hippocampus"): {
        "definition": "A limbic-system structure important for forming new explicit memories and for spatial navigation.",
    },
    ("1", "visual cortex"): {
        "definition": "The occipital-lobe area that processes visual features such as edges, color, and motion.",
    },
    ("1", "auditory cortex"): {
        "definition": "The temporal-lobe area that processes sound and supports hearing.",
    },
    ("1", "rewarding center"): {
        "definition": "A brain circuit, including limbic and dopamine pathways, that produces reinforcement and pleasure.",
    },
    ("1", "younger brains are more malleable"): {
        "definition": "The developing brain shows greater neuroplasticity, making it more adaptable to experience and injury than the adult brain.",
    },
    ("1", "long term potentiation ltp"): {
        "name": "Long-Term Potentiation (LTP)",
        "definition": "A lasting increase in synaptic strength after repeated stimulation, considered a cellular basis of learning and memory.",
    },
    ("1", "brain stimulation"): {
        "definition": "Research or clinical techniques that apply electrical or magnetic stimulation to brain regions to study or alter function.",
    },
    ("1", "adaptive theory"): {
        "definition": "The theory that sleep evolved because it provided survival advantages, such as conserving energy and avoiding danger.",
    },
    ("1", "difference threshold"): {
        "definition": "The smallest detectable difference between two stimuli, also called the just-noticeable difference.",
    },
    ("1", "light adaptation"): {
        "definition": "The process by which the eyes adjust to bright light, reducing sensitivity and shifting from rods to cones.",
    },
    ("1", "dark adaptation"): {
        "definition": "The process by which the eyes adjust to dim light, increasing sensitivity as rods take over.",
    },
    ("1", "external ear"): {
        "definition": "The outer part of the ear, including the pinna and ear canal, that collects and directs sound waves.",
    },
    ("1", "basilar membrane"): {
        "definition": "The membrane inside the cochlea that vibrates in response to sound and supports hair cells that transduce pitch.",
    },
    ("1", "volley theory"): {
        "definition": "A pitch theory proposing that groups of auditory neurons fire in alternating volleys to encode frequencies higher than any single neuron can follow.",
    },
    # Unit 2.2
    ("2", "assimilation"): {
        "definition": "Interpreting new experiences in terms of existing schemas or mental frameworks.",
    },
    ("2", "accommodation"): {
        "definition": "Changing an existing schema or creating a new one to fit new information.",
    },
    ("2", "hindsight bias"): {
        "definition": "The tendency to believe, after learning an outcome, that one would have foreseen it; the 'I-knew-it-all-along' effect.",
    },
    ("2", "priming"): {
        "definition": "The activation of a prior stimulus or memory that influences later perception, thinking, or behavior, often outside awareness.",
    },
    ("2", "divided attention"): {
        "definition": "The attempt to process two or more streams of information at the same time, often with reduced performance on at least one task.",
    },
    ("2", "context effect"): {
        "definition": "The influence of surrounding context or setting on perception, memory, or interpretation.",
    },
    ("2", "apparent movement"): {
        "definition": "The illusion that a stationary object is moving, or that movement occurs between separated stimuli, as in the phi phenomenon.",
    },
    ("2", "pictorial depth cues"): {
        "definition": "Monocular cues in a flat image—such as linear perspective, relative size, and overlap—that create an impression of depth.",
    },
    ("2", "constancies"): {
        "definition": "Perceptual constancies are the tendency to perceive objects as stable in size, shape, brightness, or color despite changes in the retinal image.",
    },
    ("2", "proximity"): {
        "definition": "A Gestalt grouping principle: stimuli near one another tend to be perceived as belonging together.",
    },
    ("2", "similarity"): {
        "definition": "A Gestalt grouping principle: stimuli that look alike tend to be grouped together.",
    },
    ("2", "figure ground illusion"): {
        "definition": "A perceptual illusion in which the distinction between the main object (figure) and its background (ground) becomes ambiguous or reversible.",
    },
    ("2", "retrospective memory"): {
        "definition": "Memory for information or events from the past, such as facts, experiences, or prior actions.",
    },
    ("2", "intermediate phonemic encoding"): {
        "definition": "Encoding based on the sound of information, such as repeating or rehearsing words by how they sound.",
    },
    ("2", "distributed practice"): {
        "definition": "Spacing study or practice across multiple sessions over time, which usually improves long-term retention compared with massed practice.",
    },
    ("2", "cerebellum"): {
        "definition": "A hindbrain structure important for balance, coordination, and motor learning.",
    },
    ("2", "amygdala"): {
        "definition": "A limbic-system structure involved in emotion, especially fear learning and emotional salience.",
    },
    ("2", "context dependent memory"): {
        "definition": "Memory that is better recalled when the retrieval context matches the encoding context.",
    },
    ("2", "metacognition"): {
        "definition": "Thinking about one's own thinking; monitoring and regulating cognitive processes.",
    },
    ("2", "nonsense syllables"): {
        "definition": "Meaningless consonant-vowel-consonant strings used by Ebbinghaus to study learning and forgetting without prior associations.",
    },
    ("2", "retention"): {
        "definition": "The amount of learned material that can be recalled or recognized after a delay.",
    },
    ("2", "savings scores"): {
        "definition": "Ebbinghaus's measure of retention based on how much faster relearning is compared with original learning.",
    },
    ("2", "repression"): {
        "definition": "A defense mechanism in which anxiety-provoking thoughts or memories are pushed out of conscious awareness.",
    },
    ("2", "imagination inflation"): {
        "definition": "The finding that imagining an event can increase confidence that it actually occurred.",
    },
    ("2", "giftedness"): {
        "definition": "Exceptional intellectual ability, often defined by high IQ or outstanding performance in a domain.",
    },
    ("2", "hereditary genius"): {
        "definition": "Galton's idea that eminence runs in families and is strongly influenced by heredity.",
    },
    ("2", "alfred binet"): {
        "definition": "French psychologist who developed an early intelligence test to identify children needing educational support.",
    },
    ("2", "deviation iq scores"): {
        "definition": "IQ scores based on how far a person's score deviates from the age-group average, expressed with a standard deviation.",
    },
    ("2", "mental retardation"): {
        "name": "Intellectual Disability",
        "definition": "A condition involving significantly below-average intellectual functioning and limitations in adaptive behavior; the modern term is intellectual disability.",
    },
    ("2", "reaction range"): {
        "definition": "The idea that genotype sets a range of possible phenotypes, with environment determining where within that range a person develops.",
    },
    ("2", "test norms"): {
        "definition": "Performance standards based on a representative sample, used to interpret test scores.",
    },
    ("2", "criterion related validity"): {
        "definition": "The degree to which test scores predict or correlate with a relevant external criterion.",
    },
    ("2", "encoding failure theory"): {
        "definition": "The explanation that forgetting occurs because information was never successfully encoded into long-term memory.",
    },
    # Unit 3
    ("3", "continuity vs discontinuity"): {"definition": "The developmental issue of whether development is gradual and continuous or occurs in distinct stages."},
    ("3", "stability vs change"): {"definition": "The developmental issue of whether traits remain stable across the lifespan or change with age and experience."},
    ("3", "naturalistic observation"): {"definition": "Observing behavior in naturally occurring settings without manipulating variables."},
    ("3", "meta analysis"): {"name": "Meta-Analysis", "definition": "A statistical technique that combines results from many studies to estimate an overall effect."},
    ("3", "experimenter bias"): {"definition": "Researcher expectations influencing the results or the behavior of participants."},
    ("3", "informed consent"): {"definition": "Participants receive enough information to decide voluntarily whether to take part in research."},
    ("3", "confidentiality"): {"definition": "Researchers protect participants' identity and data from unauthorized disclosure."},
    ("3", "gross to fine direction"): {"name": "Gross-to-Fine Direction", "definition": "Motor development proceeds from large, gross movements to precise, fine movements."},
    ("3", "head to foot direction"): {"name": "Head-to-Foot Direction", "definition": "Motor development proceeds from the head and upper body toward the lower body."},
    ("3", "hormonal changes"): {"definition": "Age-related shifts in hormone levels that affect physical, reproductive, and emotional development."},
    ("3", "hearing vision decline"): {"name": "Hearing & Vision Decline", "definition": "Normal aging changes that reduce sensory acuity, especially high-frequency hearing and near vision."},
    ("3", "dementia"): {"definition": "A progressive cognitive decline affecting memory, reasoning, language, and daily functioning."},
    ("3", "gender stereotypes"): {"definition": "Widely held beliefs about the traits and behaviors considered appropriate for men and women."},
    ("3", "sexual orientation"): {"definition": "A person's enduring pattern of emotional, romantic, or sexual attraction."},
    ("3", "schema theory"): {"definition": "The idea that people organize knowledge into mental frameworks (schemas) that guide interpretation and memory."},
    ("3", "language thought"): {"name": "Language & Thought", "definition": "The relationship between language and cognition, including claims that language shapes thought."},
    ("3", "fluid vs crystallized intelligence"): {"name": "Fluid vs Crystallized Intelligence", "definition": "Fluid intelligence is reasoning and solving new problems; crystallized intelligence is accumulated knowledge and skills."},
    ("3", "nonverbal gesture"): {"definition": "Communication through body movements, facial expressions, posture, and gestures rather than words."},
    ("3", "cooing"): {"definition": "Early infant vowel-like sounds produced before canonical babbling."},
    ("3", "babbling"): {"definition": "Repetitive consonant-vowel sounds in infancy that precede first words."},
    ("3", "neglectful"): {"name": "Neglectful Parenting", "definition": "A parenting style low in warmth and low in control, in which caregivers are relatively uninvolved."},
    ("3", "disorganized attachment"): {"definition": "Inconsistent or contradictory attachment behavior, often associated with frightening or unpredictable caregiving."},
    ("3", "pretend play"): {"definition": "Symbolic play in which children act out roles, scenarios, or imaginary situations."},
    ("3", "parallel play"): {"definition": "Children play side by side with similar toys but with little direct interaction."},
    ("3", "adolescent egocentrism"): {"definition": "Heightened self-consciousness and difficulty distinguishing one's own perspective from others'."},
    ("3", "identity statuses marcia"): {"name": "Identity Statuses (Marcia)", "definition": "Four identity statuses—diffusion, foreclosure, moratorium, and achievement—based on exploration and commitment."},
    ("3", "adverse childhood experiences aces"): {"name": "Adverse Childhood Experiences (ACEs)", "definition": "Potentially traumatic childhood events associated with later psychological and physical health risk."},
    ("3", "positive reinforcement"): {"definition": "Increasing a behavior by adding a desirable consequence after it occurs."},
    ("3", "negative reinforcement"): {"definition": "Increasing a behavior by removing or avoiding an unpleasant consequence."},
    ("3", "positive punishment"): {"definition": "Decreasing a behavior by adding an unpleasant consequence."},
    ("3", "negative punishment"): {"definition": "Decreasing a behavior by removing a desirable consequence."},
    ("3", "illusory correlation"): {"definition": "Perceiving a relationship between variables that does not exist or is weaker than believed."},
    ("3", "learned helplessness"): {"definition": "Passivity and reduced effort after repeated exposure to uncontrollable failure."},
    ("3", "self efficacy"): {"name": "Self-Efficacy", "definition": "Belief in one's ability to succeed at a specific task or in a particular situation."},
    # Unit 4
    ("4", "attributions"): {"definition": "Explanations people construct for the causes of events and behavior."},
    ("4", "optimistic explanatory style"): {"definition": "Explaining negative events with external, temporary, and specific causes."},
    ("4", "pessimistic explanatory style"): {"definition": "Explaining negative events with internal, stable, and global causes."},
    ("4", "culture and attributional tendencies"): {"definition": "Cultural differences in attribution, such as individualistic cultures favoring dispositional explanations."},
    ("4", "stereotype prejudice discrimination"): {"name": "Stereotypes, Prejudice & Discrimination", "definition": "Stereotypes are beliefs, prejudice is negative attitude, and discrimination is unequal behavior toward a group."},
    ("4", "belief perseverance"): {"definition": "Clinging to a belief even after the evidence supporting it has been discredited."},
    ("4", "confirmation bias"): {"definition": "Seeking or interpreting information in ways that support existing beliefs."},
    ("4", "informational social influence"): {"definition": "Conformity because one believes others have accurate information."},
    ("4", "normative social influence"): {"definition": "Conformity to gain social approval or avoid rejection."},
    ("4", "compliance"): {"definition": "Changing behavior in response to a direct request, without necessarily changing private beliefs."},
    ("4", "social inhibition"): {"definition": "Reduced performance or expressiveness when others are present."},
    ("4", "milgrams experiment"): {"name": "Milgram's Experiment", "definition": "An obedience study in which participants followed authority instructions to administer apparently painful shocks."},
    ("4", "prisoner s dilemma"): {"name": "Prisoner's Dilemma", "definition": "A social trap in which individual self-interest produces a worse joint outcome."},
    ("4", "multiculturalism"): {"definition": "Recognizing and maintaining multiple cultural identities within a society or person."},
    ("4", "conscious"): {"definition": "The level of awareness that includes current thoughts, perceptions, and feelings."},
    ("4", "preconscious"): {"definition": "Information outside current awareness that can be brought into consciousness easily."},
    ("4", "psychosexual stages"): {"definition": "Freud's oral, anal, phallic, latency, and genital stages of personality development."},
    ("4", "incongruence"): {"definition": "A mismatch between one's real self and ideal self, which Rogers saw as a source of distress."},
    ("4", "unconditional positive regard"): {"definition": "Acceptance and valuing of a person without conditions or contingencies."},
    ("4", "observational learning"): {"definition": "Learning by watching the behavior and consequences of models."},
    ("4", "factor analysis"): {"definition": "A statistical method for identifying clusters of items or traits that correlate."},
    ("4", "openness"): {"definition": "Big Five trait reflecting imagination, curiosity, and openness to new experience."},
    ("4", "conscientiousness"): {"definition": "Big Five trait reflecting organization, responsibility, and self-discipline."},
    ("4", "extraversion"): {"definition": "Big Five trait reflecting sociability, assertiveness, and positive emotionality."},
    ("4", "agreeableness"): {"definition": "Big Five trait reflecting cooperation, trust, and concern for others."},
    ("4", "neuroticism"): {"definition": "Big Five trait reflecting emotional instability and proneness to negative affect."},
    ("4", "person situation controversy"): {"definition": "The debate over whether personality traits or situational factors better predict behavior."},
    ("4", "approach approach"): {"name": "Approach-Approach", "definition": "A conflict between two desirable options."},
    ("4", "avoidance avoidance"): {"name": "Avoidance-Avoidance", "definition": "A conflict between two undesirable options."},
    ("4", "avoidance approach"): {"name": "Avoidance-Approach", "definition": "A conflict involving a single option with both desirable and undesirable features."},
    ("4", "thrill and adventure seeking tas"): {"name": "Thrill and Adventure Seeking (TAS)", "definition": "Sensation-seeking facet involving attraction to risky, exciting activities."},
    ("4", "experience seeking es"): {"name": "Experience Seeking (ES)", "definition": "Sensation-seeking facet involving novelty and unconventional experiences."},
    ("4", "disinhibition ds"): {"name": "Disinhibition (DS)", "definition": "Sensation-seeking facet involving reduced restraint and enjoyment of losing inhibitions."},
    ("4", "boredom susceptibility bs"): {"name": "Boredom Susceptibility (BS)", "definition": "Sensation-seeking facet involving intolerance of repetitive or boring situations."},
    ("4", "incentive theories"): {"definition": "Theories that motivation is driven by external rewards, punishments, and incentives."},
    ("4", "amygdala"): {"definition": "A limbic-system structure involved in emotion, especially fear learning and emotional salience."},
    ("4", "sympathetic nervous system"): {"definition": "The branch of the autonomic nervous system that prepares the body for fight-or-flight."},
    ("4", "schachter two factor theory"): {"name": "Schachter Two-Factor Theory", "definition": "Emotion results from physiological arousal plus a cognitive label for that arousal."},
    ("4", "richard lazaruss appraisal theory"): {"name": "Lazarus's Appraisal Theory", "definition": "Emotion depends on cognitive appraisal of an event's meaning and significance."},
    ("4", "positive and negative emotions"): {"definition": "Positive emotions tend to broaden thinking and build resources; negative emotions tend to narrow attention and support specific responses."},
    ("4", "universal evolutionary theories of emotion"): {"name": "Universal/Evolutionary Theories of Emotion", "definition": "The view that certain basic emotions are innate and universally recognizable because they had adaptive value."},
    # Unit 5
    ("5", "eustress"): {"definition": "Positive or motivating stress that can improve performance and growth."},
    ("5", "distress"): {"definition": "Negative stress that feels overwhelming and can impair health and performance."},
    ("5", "alarm reaction"): {"definition": "The first stage of the general adaptation syndrome, when the body mobilizes resources to meet a stressor."},
    ("5", "deviance"): {"definition": "Behavior that violates social norms or expectations and is one criterion of abnormality."},
    ("5", "personal distress"): {"definition": "Subjective suffering or impairment that is one criterion of abnormal behavior."},
    ("5", "maladaptive behavior"): {"definition": "Behavior that interferes with everyday functioning and well-being."},
    ("5", "evolutionary perspective"): {"definition": "Explaining behavior through the adaptive value of traits selected over evolutionary history."},
    ("5", "sociocultural perspective"): {"definition": "Explaining behavior through social and cultural context, norms, and group membership."},
    ("5", "biological perspective"): {"definition": "Explaining behavior through genetics, brain structure, neurotransmitters, and physiology."},
    ("5", "categories of disorders"): {"definition": "DSM categories group disorders by shared symptoms, course, and clinical features."},
    ("5", "genetic vulnerability"): {"definition": "Inherited predisposition that increases risk for a disorder."},
    ("5", "genetic factors"): {"definition": "Inherited influences that contribute to risk for a disorder."},
    ("5", "neurochemical factors"): {"definition": "Differences in neurotransmitter activity or brain chemistry associated with a disorder."},
    ("5", "neurodevelopmental hypothesis"): {"definition": "The idea that schizophrenia results in part from disrupted brain development early in life."},
    ("5", "expressed emotion"): {"definition": "Family criticism, hostility, or emotional overinvolvement associated with relapse risk."},
    ("5", "cognitive factors"): {"definition": "Maladaptive beliefs, appraisals, and thinking patterns that contribute to a disorder."},
    ("5", "biological factors"): {"definition": "Genetic, neurological, or physiological influences on a disorder."},
    ("5", "conditioning learning"): {"name": "Conditioning & Learning", "definition": "Classical and operant learning processes that can create or maintain fear and avoidance."},
    ("5", "stress"): {"definition": "Psychological and physiological strain produced by demanding or threatening events."},
    ("5", "obsessions"): {"definition": "Intrusive, unwanted thoughts, images, or urges that cause distress."},
    ("5", "compulsions"): {"definition": "Repetitive behaviors or mental acts performed to reduce distress or prevent a feared outcome."},
    ("5", "dissociative fugue"): {"definition": "Sudden travel away from home with confusion about identity, often following stress or trauma."},
    ("5", "etiology"): {"definition": "The causes and maintaining factors that explain how a disorder develops."},
    ("5", "histrionic personality disorder"): {"definition": "A personality disorder marked by attention-seeking, dramatic behavior, and shallow emotions."},
}


def supplement_spec(unit: str, label: str) -> dict | None:
    return SUPPLEMENTS.get((str(unit), norm(label)))


def supplement_payload(unit: str, topic_code: str, label: str): 
    spec = supplement_spec(unit, label)
    if not spec:
        return None
    slug = norm(label).replace(" ", "-")[:40]
    digest = hashlib.sha1(f"{unit}:{topic_code}:{norm(label)}".encode()).hexdigest()[:8]
    return {
        "id": f"psy-supp-{unit}-{slug}-{digest}",
        "name": spec.get("name", label),
        "definition": spec["definition"],
        "source": "ai_supplement",
        "review_status": "draft",
        "topic_code": topic_code,
    }


def apply_supplements(node: TreeNode, unit: str, topic_code: str) -> None:
    if node.concept is None and not node.supplement and not node.children:
        spec = supplement_payload(unit, topic_code, node.label)
        if spec:
            node.supplement = spec
    for child in node.children:
        apply_supplements(child, unit, topic_code)


def load_concepts(kb_path: Path, unit: str) -> list[dict]:
    conn = sqlite3.connect(f"file:{kb_path}?mode=ro", uri=True)
    rows = conn.execute(
        "SELECT cluster_id, canonical_name, ap_unit, topic, weight_tier, weight "
        "FROM concept_clusters WHERE ap_unit=? ORDER BY canonical_name",
        (unit,),
    ).fetchall()
    conn.close()
    return [
        {
            "id": row[0],
            "name": row[1],
            "topic": row[3],
            "tier": row[4],
            "weight": row[5],
            "norm": norm(row[1]),
        }
        for row in rows
    ]


def match_concept(text: str, concepts: list[dict]) -> tuple[dict | None, float]:
    key = norm(text)
    if not key:
        return None, 0.0
    if key in ALIASES:
        target_name = ALIASES[key]
        if target_name is None:
            return None, 0.0
        target = norm(target_name)
    else:
        target = key
    by_norm = {c["norm"]: c for c in concepts}
    if target in by_norm:
        return by_norm[target], 1.0
    # Compare with parentheticals removed, but never allow a single short
    # token to match a longer compound name ("brain" -> "Forebrain").
    a = re.sub(r"\([^)]*\)", "", target).strip()
    if " " not in a and len(a) < 8:
        return None, 0.0
    best: tuple[dict | None, float] = (None, 0.0)
    for concept in concepts:
        b = re.sub(r"\([^)]*\)", "", concept["norm"]).strip()
        if a == b and a:
            score = 0.99
        else:
            score = SequenceMatcher(None, a, b).ratio()
        if score > best[1]:
            best = (concept, score)
    return best



CURATED_UNIT1: dict[str, list[CuratedNode]] = {
    "1.1": [
        C("Behavioral Genetics",
          K("Genes", "Genes"),
          K("DNA", "DNA"),
          K("Genome", "Genome"),
          K("Epigenetics", "Epigenetics"),
          K("Behavior Genetics", "Behavior genetics"),
          K("Genetic Predisposition", "Genetic predisposition"),
          K("Mutation", "Mutation"),
          K("Chromosomal Abnormalities", "Chromosomal abnormality")),
        C("Nature & Nurture",
          K("Nature-Nurture Issue", "Nature-nurture issue"),
          K("Heredity", "Heredity"),
          K("Environment", "Environment"),
          K("Interaction", "Interaction")),
        C("Twin & Family Studies",
          C("Family Studies"),
          C("Twin Studies",
            K("Identical (Monozygotic) Twins", "Identical twins (monozygotic twins)"),
            K("Fraternal (Dizygotic) Twins", "Fraternal (dizygotic) twins")),
          C("Adoption Studies")),
        K("Evolutionary Psychology", "Evolutionary psychology",
          K("Natural Selection", "Natural selection"),
          C("Adaptation"),
          C("Survival & Reproduction")),
        C("Eugenics"),
    ],
    "1.2": [
        K("Nervous System", "Nervous system",
          K("Central Nervous System", "Central nervous system (CNS)",
            C("Brain"),
            K("Spinal Cord", "Spinal cord"),
            K("Interneurons", "Interneurons (association neurons)")),
          K("Peripheral Nervous System", "Peripheral nervous system (PNS)",
            K("Somatic Nervous System", "Somatic nervous system",
              K("Sensory (Afferent) Neurons", "Sensory neurons (afferent neurons)"),
              K("Motor (Efferent) Neurons", "Motor neurons (efferent neurons)")),
            K("Autonomic Nervous System", "Autonomic nervous system",
              K("Sympathetic Nervous System", "Sympathetic nervous system",
                K("Fight-or-Flight Response", "Fight-or-flight response")),
              K("Parasympathetic Nervous System", "Parasympathetic nervous system"))),
          K("Reflex Arcs", "Reflex arcs")),
        K("Endocrine System", "Endocrine system",
          C("Glands",
            C("Pituitary Gland"),
            K("Adrenal Glands", "Adrenal glands"),
            K("Ovaries & Testes", "Ovaries and testes")),
          K("Hormones", "Hormones",
            C("Adrenaline / Epinephrine"),
            C("Leptin & Ghrelin"),
            C("Melatonin"),
            C("Oxytocin")),
          C("Homeostasis")),
    ],
    "1.3": [
        C("Neuron Structure",
          K("Dendrites", "Dendrites"),
          K("Axon", "Axon"),
          K("Axon Terminals", "Terminal buttons"),
          K("Myelin Sheath", "Myelin sheath",
            K("Glial Cells", "Glial cells (glia)")),
          K("Soma (Cell Body)", "Cell body (soma)")),
        C("Neural Firing",
          C("Electrical Signal",
            K("Resting Potential", "Resting potential"),
            K("Action Potential", "Action potential"),
            K("Depolarization", "Depolarization"),
            C("Repolarization"),
            K("All-or-None Principle", "All-or-none principle"),
            K("Threshold", "Threshold"),
            C("Refractory Period")),
          C("Chemical Signal",
            K("Synaptic Cleft", "Synapse"),
            K("Neurotransmitters", "Neurotransmitters",
              K("Excitatory", "Excitatory neurotransmitters"),
              K("Inhibitory", "Inhibitory neurotransmitters")))),
        K("Psychoactive Drugs", "Psychoactive drugs",
          K("Depressants", "Depressants"),
          K("Hallucinogens", "Hallucinogens"),
          K("Agonists", "Agonists"),
          K("Antagonists", "Antagonists"),
          K("Reuptake Inhibitors (SSRIs)", "Selective serotonin reuptake inhibitor"),
          K("Stimulants", "Stimulants"),
          K("Drug Dependence", "Physical dependence"),
          K("Tolerance", "Tolerance"),
          K("Withdrawal", "Withdrawal symptoms")),
    ],
    "1.4": [
        K("Hindbrain", "Hindbrain",
          K("Brainstem", "Brainstem",
            K("Midbrain", "Midbrain"),
            K("Pons", "Pons"),
            K("Medulla", "Medulla")),
          K("Cerebellum", "Cerebellum")),
        K("Limbic System", "Limbic system",
          K("Thalamus", "Thalamus"),
          K("Hypothalamus", "Hypothalamus"),
          C("Pituitary Gland"),
          C("Hippocampus"),
          K("Amygdala", "Amygdala")),
        C("Cerebral Cortex",
          K("Frontal Lobe", "Frontal lobes",
            K("Prefrontal Cortex", "Prefrontal cortex"),
            K("Primary Motor Cortex", "Motor cortex"),
            K("Broca's Area", "Broca’s area")),
          K("Parietal Lobe", "Parietal lobes",
            K("Somatosensory Cortex", "Somatosensory cortex")),
          K("Occipital Lobe", "Occipital lobes",
            C("Visual Cortex")),
          K("Temporal Lobe", "Temporal lobes",
            C("Auditory Cortex"),
            K("Wernicke's Area", "Wernicke’s area"))),
        C("Other Structures",
          K("Corpus Callosum", "Corpus callosum"),
          K("Reticular Activating System", "Reticular formation"),
          C("Rewarding Center"),
          K("Split-Brain Patients", "Split-brain patients"),
          C("Cerebral Hemispheres",
            K("Left vs Right Functions", "Hemispheric specialization (brain lateralization)"))),
        K("Neuroplasticity", "Neuroplasticity",
          C("Younger Brains Are More Malleable"),
          C("Long-Term Potentiation (LTP)"),
          K("Neurogenesis", "Neurogenesis"),
          K("Pruning", "Pruning")),
        C("Tools for Examining the Brain",
          K("Lesioning", "Lesioning"),
          C("Brain Stimulation"),
          K("Electroencephalogram (EEG)", "Electroencephalogram (EEG)"),
          K("Magnetic Resonance Imaging (MRI)", "Magnetic resonance imaging (MRI)"),
          K("Functional MRI (fMRI)", "Functional MRI (fMRI)"),
          K("CAT / CT Scan", "Computerized axial tomography (CAT or CT) scan"),
          K("PET Scan", "Positron emission tomography (PET) scan")),
    ],
    "1.5": [
        K("Consciousness", "Consciousness",
          K("Circadian Rhythm", "Circadian rhythm"),
          K("Sleep Cycle", "Sleep cycle")),
        K("NREM Sleep", "NREM sleep",
          K("Stage 1: Theta Waves", "Theta waves"),
          K("Stage 2: Sleep Spindles", "Sleep spindles"),
          K("Stage 3/4: Delta Sleep", "Delta sleep")),
        K("REM Sleep", "REM sleep",
          K("Dreams", "Dreams")),
        C("Sleep Theories",
          C("Adaptive Theory"),
          K("Restorative Theory", "Restoration of resources")),
        C("Dream Theories",
          K("Consolidation Theory", "Consolidation theory of dreams"),
          K("Activation-Synthesis Theory", "Activation-synthesis theory of dreaming")),
        C("Sleep Disorders",
          K("Insomnia", "Insomnia"),
          K("Narcolepsy", "Narcolepsy"),
          K("Sleep Apnea", "Sleep apnea"),
          K("REM Sleep Behavior Disorder", "REM sleep behavior disorder"),
          K("Somnambulism", "Somnambulism (sleepwalking)"),
          K("Night Terrors", "Night terrors")),
        K("Sleep Deprivation", "Sleep deprived",
          K("REM Rebound", "REM rebound")),
    ],
    "1.6": [
        C("Basic Concepts",
          K("Sensation", "Sensation"),
          K("Perception", "Perception"),
          K("Transduction", "Transduction"),
          K("Sensory Receptors", "Sensory receptors"),
          K("Absolute Threshold", "Threshold"),
          C("Difference Threshold"),
          K("Sensory Adaptation", "Sensory adaptation"),
          K("Habituation & Dishabituation", "Sensory habituation"),
          K("Synesthesia", "Synesthesia")),
        K("Vision", "Vision",
          C("Structure of the Eye",
            K("Cornea", "Cornea"),
            K("Pupil", "Pupil"),
            K("Lens", "Lens"),
            K("Retina", "Retina"),
            K("Rods", "Rods"),
            K("Cones", "Cones"),
            K("Fovea", "Fovea"),
            K("Optic Nerve", "Optic nerve"),
            K("Optic Chiasm", "Optic chiasm"),
            K("Blind Spot", "Blind spot")),
          C("Visual Processing",
            K("Feature Detectors", "Feature detectors"),
            C("Visual Cortex")),
          C("Color Vision",
            K("Trichromatic Theory", "Young-Helmholtz trichromatic (three-color) theory"),
            K("Opponent-Process Theory", "Opponent-process theory (color vision)")),
          C("Light & Dark Adaptation",
            C("Light Adaptation"),
            C("Dark Adaptation"))),
        K("Audition", "Audition",
          C("Structure of the Ear",
            C("External Ear"),
            K("Middle Ear", "Middle ear"),
            K("Inner Ear", "Inner ear"),
            K("Cochlea", "Cochlea"),
            C("Basilar Membrane")),
          C("Pitch Theories",
            K("Place Theory", "Place theory"),
            K("Frequency Theory", "Frequency theory"),
            C("Volley Theory")),
          C("Hearing Loss",
            K("Conduction Deafness", "Conduction deafness"),
            K("Sensorineural Hearing Loss", "Sensorineural hearing loss"))),
        C("Chemical Senses",
          K("Gustation", "Gustation",
            K("Taste Buds", "Taste buds"),
            K("Five Basic Tastes", "Five different types of tastes")),
          K("Olfaction", "Smell (Olfaction)",
            K("Olfactory Bulb", "Olfactory bulb"))),
        C("Body Senses",
          C("Touch & Pain",
            K("Gate Control Theory", "Gate control theory")),
          K("Vestibular Sense", "Vestibular sense"),
          K("Kinesthetic Sense", "Kinesthetic sense (kinesthesis)")),
    ],
}


def filter_tree(node: TreeNode, include: list[str] | None, exclude: list[str] | None) -> TreeNode:
    if include is not None:
        wanted = {norm(item) for item in include}
        node.children = [child for child in node.children if norm(child.label) in wanted or norm(child.source.split(":", 1)[-1]) in wanted]
    if exclude is not None:
        unwanted = {norm(item) for item in exclude}
        node.children = [child for child in node.children if norm(child.label) not in unwanted and norm(child.source.split(":", 1)[-1]) not in unwanted]
        for child in node.children:
            filter_tree(child, None, exclude)
    return node


def tree_to_json(node: TreeNode) -> dict:
    out: dict = {"label": node.label}
    if node.concept:
        out["concept"] = node.concept
    if node.supplement:
        out["supplement"] = node.supplement
    if node.children:
        out["children"] = [tree_to_json(child) for child in node.children]
    return out


def splice_fragments(node: TreeNode) -> TreeNode:
    """Remove sentence-fragment parents and keep their real children.

    A few PDF connectors attach a definition line as if it were the parent of
    the next concept (for example "Control over events ... > Internal"). The
    definition is not a knowledge point, so its children move up one level.
    """
    new_children: list[TreeNode] = []
    for child in node.children:
        child = splice_fragments(child)
        if child.children and not child.concept and fragment_like(child.label):
            new_children.extend(child.children)
        else:
            new_children.append(child)
    node.children = new_children
    return node


def merge_siblings(node: TreeNode) -> TreeNode:
    """Merge duplicate branch labels such as the two "Phenomenon" branches."""
    merged: list[TreeNode] = []
    by_label: dict[str, TreeNode] = {}
    for child in node.children:
        child = merge_siblings(child)
        key = norm(child.label)
        if not child.concept and not child.children:
            key = f"leaf:{key}"
        if key in by_label and not child.concept:
            by_label[key].children.extend(child.children)
        else:
            by_label[key] = child
            merged.append(child)
    node.children = merged
    return node


def unit_of_topic(code: str) -> str:
    return code.split(".")[0]


def build_topic(spec: TopicSpec, pages: dict[int, MindMapPage], concepts: list[dict], report: list[str]) -> dict | None:
    curated = CURATED_UNIT1.get(spec.code) or CURATED_TOPICS.get(spec.code)
    if curated:
        known = {c["name"] for c in concepts}
        missing: list[str] = []
        def convert(node: CuratedNode) -> TreeNode:
            concept = node.concept
            if concept and concept not in known:
                missing.append(concept)
                concept = None
            return TreeNode(
                label=node.label,
                concept=concept,
                children=[convert(child) for child in node.children],
            )
        children = [convert(node) for node in curated]
        root = TreeNode(label=spec.title, children=children)
        rename_nodes(root, unit_of_topic(spec.code), spec.code)
        apply_supplements(root, unit_of_topic(spec.code), spec.code)
        nodes = list(root.walk())[1:]
        matched = sum(1 for node in nodes if node.concept or node.supplement)
        if missing:
            report.append(f"- curated concepts not found in Unit 1 DB: {', '.join(sorted(set(missing)))}")
        return {
            "label": spec.title,
            "node_count": len(nodes),
            "matched_count": matched,
            "children": [tree_to_json(child) for child in root.children],
        }
    branches: list[TreeNode] = []
    for root_spec in spec.roots:
        page = pages.get(root_spec.page)
        if page is None:
            report.append(f"- `{spec.code}`: page {root_spec.page} missing")
            continue
        index = page.find_path(root_spec.path)
        if index is None:
            report.append(f"- `{spec.code}`: path not found: {' > '.join(root_spec.path)} (p{root_spec.page})")
            continue
        node = node_from_page(page, index, concepts, {})
        node = prune(node)
        if node is None:
            report.append(f"- `{spec.code}`: pruned empty root: {' > '.join(root_spec.path)} (p{root_spec.page})")
            continue
        if root_spec.display:
            node.label = root_spec.display
        branches.append(node)
    if not branches:
        return None
    # A single branch that has the same title as the topic would render a
    # duplicate root. Splice its children instead.
    if len(branches) == 1 and norm(branches[0].label) == norm(spec.title):
        branch = branches[0]
        children = branch.children
        if not children:
            children = [TreeNode(label=branch.label, concept=branch.concept)]
    else:
        children = branches
    root = TreeNode(label=spec.title, children=children)
    root = filter_tree(root, spec.include, spec.exclude)
    # filter_tree may change child labels; re-prune in case an include filter
    # removed all children from a generic branch.
    pruned_children = []
    for child in root.children:
        child = prune(child)
        if child is not None:
            pruned_children.append(child)
    root.children = pruned_children
    root = merge_siblings(splice_fragments(root))
    rename_nodes(root, unit_of_topic(spec.code), spec.code)
    apply_supplements(root, unit_of_topic(spec.code), spec.code)
    if not root.children:
        report.append(f"- `{spec.code}`: no nodes after pruning")
        return None
    nodes = list(root.walk())[1:]
    matched = sum(1 for node in nodes if node.concept or node.supplement)
    return {
        "label": spec.title,
        "node_count": len(nodes),
        "matched_count": matched,
        "children": [tree_to_json(child) for child in root.children],
    }


def collect_unmatched(node: dict, out: list[str], path: list[str]):
    label = node.get("label", "")
    if not node.get("concept") and not node.get("supplement") and not node.get("children"):
        out.append(" > ".join(path + [label]))
    for child in node.get("children", []):
        collect_unmatched(child, out, path + [label])


def build(pdf_path: Path, kb_path: Path) -> tuple[dict, str]:
    pdf = fitz.open(pdf_path)
    units: dict[str, dict] = {}
    report: list[str] = [
        "# PDF mind map audit",
        "",
        f"- Source: `{pdf_path.name}`",
        f"- Knowledge DB: `{kb_path}`",
        "- Parser: vector connector endpoints -> label boxes; bold root; BFS tree.",
        "- Unit 1 trees are curated from the PDF hierarchy + Unit 1 knowledge DB + the standard AP scope. Unit 2–5 use parsed trees with description cleanup.",
        "- Unmatched labels stay in the JSON as English-only, non-clickable labels. They are not fabricated concepts.",
        "- This script writes only the JSON and this report; it does not write a Release or the content DB.",
        "",
    ]
    for unit, specs in TOPIC_SPECS.items():
        concepts = load_concepts(kb_path, unit)
        pages: dict[int, MindMapPage] = {}
        for spec in specs:
            for root in spec.roots:
                if root.page in pages:
                    continue
                try:
                    pages[root.page] = MindMapPage(pdf, root.page, tol=PAGE_TOL.get(root.page, 12.0))
                except Exception as exc:  # pragma: no cover - diagnostic path
                    report.append(f"- page {root.page}: {exc}")
        unit_out: dict = {"title": UNIT_TITLES[unit], "topics": {}}
        report.append(f"## Unit {unit} — {UNIT_TITLES[unit]}")
        report.append("")
        report.append("| Topic | Source | Nodes | Matched |")
        report.append("|---|---|---:|---:|")
        for spec in specs:
            topic_report: list[str] = []
            tree = build_topic(spec, pages, concepts, topic_report)
            if tree is None:
                report.extend(topic_report)
                report.append("")
                continue
            unit_out["topics"][spec.code] = tree
            sources = ", ".join(f"p{root.page}" for root in spec.roots)
            report.append(f"| {spec.code} {spec.title} | {sources} | {tree['node_count']} | {tree['matched_count']} |")
            for line in topic_report:
                report.append(line)
            unmatched: list[str] = []
            for child in tree["children"]:
                collect_unmatched(child, unmatched, [])
            if unmatched:
                report.append("")
                report.append(f"Unmatched labels in {spec.code} (kept as non-clickable labels):")
                for item in unmatched:
                    report.append(f"- {item}")
            report.append("")
        units[unit] = unit_out
    payload = {
        "schema_version": 1,
        "source": {
            "file": pdf_path.name,
            "parser": "vector-connectors-v1",
            "units": {unit: [f"p{root.page}" for spec in specs for root in spec.roots] for unit, specs in TOPIC_SPECS.items()},
        },
        "units": units,
    }
    return payload, "\n".join(report).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    parser.add_argument("--kb", type=Path, default=DEFAULT_KB)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--write", action="store_true", help="write JSON and report")
    parser.add_argument("--dry-run", action="store_true", help="parse and print summary only")
    args = parser.parse_args()
    if not args.pdf.exists():
        print(f"PDF not found: {args.pdf}", file=sys.stderr)
        return 2
    if not args.kb.exists():
        print(f"Knowledge DB not found: {args.kb}", file=sys.stderr)
        return 2
    payload, report = build(args.pdf, args.kb)
    counts = []
    for unit, data in payload["units"].items():
        for code, topic in data["topics"].items():
            counts.append((code, topic["node_count"], topic["matched_count"]))
    print(f"units: {len(payload['units'])}; topics: {len(counts)}")
    for code, nodes, matched in counts:
        print(f"  {code:5s} nodes={nodes:3d} matched={matched:3d}")
    print("\n" + report[:4000])
    if args.write:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(report, encoding="utf-8")
        print(f"\nWrote {args.out}")
        print(f"Wrote {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
