"""Parser for AP Classroom question-bank scoring-guide PDFs.

The PDF interleaves questions, options, ``Answer X`` lines, short
explanations, and shared stimuli (a passage, a study description, a graph or
a table).  It is tempting to read one question after another and append every
line after ``Answer`` to the explanation, but that is wrong:

* ``pypdf``'s ``extract_text()`` drops blank lines.  The next question's
  shared stimulus then looks like a continuation of the previous explanation.
* A stimulus can cover several questions (for example Q8-Q10 share Dr.
  Collins's study).  Only attaching the block immediately before a question
  gives the first question the context but leaves Q9/Q10 without it.

This module therefore works on blank-line-delimited *paragraph blocks* from
``pdftotext -layout`` and keeps the explanation, the stimulus, and the
question stem separate.  ``context_groups`` is the explicit stimulus map for
sets that continue over more than one question; the caller supplies it after
inspecting the PDF.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

DROP = (
    re.compile(r"^AP PSYCHOLOGY\s+Scoring Guide\s*$", re.I),
    re.compile(r"^Scoring Guide\s*$", re.I),
    re.compile(r"^Supplemental Practice Exam MCQ\s*$", re.I),
    re.compile(
        r"^Scoring Guide \|\| AP Classroom Resources \|\| AP Psychology "
        r"Practice Exams \|\| - PAGE : \d+ -\s*$",
        re.I,
    ),
    # Bare page numbers.  The CB scoring guide prints these between pages.
    re.compile(r"^\d{1,3}$"),
)

Q = re.compile(r"^\s*(\d{1,3})\.\s*(.*)$")
OPT = re.compile(r"^\s*\(([A-E])\)\s*(.*)$")
BARE_OPT = re.compile(r"^\s*\(([A-E])\)\s*$")
ANS = re.compile(r"^\s*Answer\s+([A-E])\b", re.I)
EXP = re.compile(r"^\s*(Correct|Incorrect)\.", re.I)


def extract_layout_text(pdf_path: str | Path, start_page: int, end_page: int) -> str:
    """Return ``pdftotext -layout`` text for an inclusive page range.

    ``-layout`` preserves the blank lines that mark paragraph boundaries.
    Without those boundaries the next question's stimulus cannot be separated
    from the previous question's explanation.
    """
    command = [
        "pdftotext",
        "-layout",
        "-enc",
        "UTF-8",
        "-f",
        str(start_page),
        "-l",
        str(end_page),
        str(pdf_path),
        "-",
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
    except FileNotFoundError as exc:  # pragma: no cover - environment-specific
        raise RuntimeError(
            "pdftotext is required to parse this PDF. Install poppler "
            "(macOS: brew install poppler; Debian/Ubuntu: apt-get install poppler-utils)."
        ) from exc
    except subprocess.CalledProcessError as exc:  # pragma: no cover
        raise RuntimeError(f"pdftotext failed: {exc.stderr.strip()}") from exc
    return result.stdout


def _is_boilerplate(line: str) -> bool:
    stripped = line.strip()
    return any(pattern.match(stripped) for pattern in DROP)


def _join_lines(parts: list[str]) -> str:
    """Join wrapped lines, keeping hyphenated words together.

    The PDF breaks ``self-actualization`` across lines as ``self-`` /
    ``actualization``.  A plain space join would produce ``self-
    actualization``.
    """
    text = ""
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if not text:
            text = part
        elif text.endswith("-") and part[:1].islower():
            text += part
        else:
            text += " " + part
    return text


def _blocks(text: str) -> list[list[str]]:
    """Split text into blank-line-delimited blocks, dropping headers/footers."""
    blocks: list[list[str]] = []
    current: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if line.strip():
            if not _is_boilerplate(line):
                current.append(line.strip())
        elif current:
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)
    return blocks


def _consume(line: str, question: dict) -> None:
    """Consume one line and remember where it was stored.

    ``pdftotext -layout`` aligns an option label with the *second* line of a
    wrapped option, so it emits::

        (A) The number ... presented stimulus
            The number ... presented
        (B)
            stimulus from its original form

    The line before the bare ``(B)`` belongs to option B, not option A.  The
    ``last_target`` marker lets a bare label take back that line without
    guessing whether it came from the stem or from the previous option.
    """
    bare = BARE_OPT.match(line)
    if bare:
        label = bare.group(1)
        moved = ""
        target = question.get("last_target")
        if target and target[0] == "option":
            parts = question["options"].get(target[1], [])
            if parts:
                moved = parts.pop()
        elif target and target[0] == "stem" and len(question["stem"]) > 1:
            # Never move the numbered question line out of the stem.
            moved = question["stem"].pop()
        question["options"][label] = [moved] if moved else []
        question["option"] = label
        question["last_target"] = ("option", label)
        return

    answer_match = ANS.match(line)
    if answer_match:
        question["answer"] = answer_match.group(1).upper()
        question["last_target"] = None
        return

    option_match = OPT.match(line)
    if option_match:
        label = option_match.group(1)
        question["options"][label] = [option_match.group(2)]
        question["option"] = label
        question["last_target"] = ("option", label)
        return

    if question["answer"] is not None:
        # Everything after the Answer line is the rationale.
        question["explanation"].append(line)
        question["last_target"] = ("explanation",)
        return

    if question["option"]:
        question["options"][question["option"]].append(line)
        question["last_target"] = ("option", question["option"])
    else:
        question["stem"].append(line)
        question["last_target"] = ("stem",)


def _consume_block(lines: list[str], question: dict) -> None:
    """Consume one paragraph block line by line."""
    for line in lines:
        _consume(line, question)


def parse_unit_text(
    text: str,
    context_groups: list[list[int]] | None = None,
) -> tuple[list[dict], list[tuple[int, int]]]:
    """Parse one unit's layout text into question dicts.

    ``context_groups`` is a list such as ``[[8, 9, 10], [19, 20, 21]]``: the
    first number is the question whose preceding stimulus is shared by every
    number in that group.  The parser copies the anchor's context to members
    that do not already have their own context.  This is deliberately explicit;
    guessing whether "this study" continues a previous passage is less reliable
    than writing down the stimulus map once per paper.
    """
    questions: list[dict] = []
    current: dict | None = None
    expected = 1
    gaps: list[tuple[int, int]] = []
    pending_context: list[str] = []

    def finish() -> None:
        nonlocal current
        if current:
            questions.append(current)
            current = None

    for block in _blocks(text):
        match = Q.match(block[0])
        if match:
            number = int(match.group(1))
            if number == expected or expected < number <= expected + 3:
                if number != expected:
                    gaps.append((expected, number))
                finish()
                current = {
                    "number": number,
                    "stem": [match.group(2)],
                    "context": "\n\n".join(pending_context).strip() or None,
                    "options": {},
                    "option": None,
                    "answer": None,
                    "explanation": [],
                    "last_target": None,
                }
                pending_context = []
                expected = number + 1
                _consume_block(block[1:], current)
                continue

        if current is None:
            pending_context.append(_join_lines(block))
            continue

        first = block[0]
        is_option = bool(OPT.match(first))
        is_answer = bool(ANS.match(first))
        is_explanation = bool(EXP.match(first))

        if current["answer"] is None:
            _consume_block(block, current)
        elif is_explanation:
            for line in block:
                current["explanation"].append(line)
        elif is_option or is_answer:
            for line in block:
                _consume(line, current)
        else:
            # A new passage/table/study after the explanation belongs to the
            # next question, never to this question's answer_text.
            pending_context.append(_join_lines(block))

    finish()

    for question in questions:
        question["stem"] = _join_lines(question["stem"])
        question["options"] = {
            label: _join_lines(parts)
            for label, parts in question["options"].items()
        }
        question["answer_text"] = _join_lines(question["explanation"])
        question["explanation"] = question["answer_text"]
        question["expl"] = question["answer_text"]  # backward-compatible key

    if context_groups:
        by_number = {question["number"]: question for question in questions}
        for group in context_groups:
            anchor = by_number.get(group[0])
            if not anchor:
                continue
            context = anchor.get("context") or next(
                (
                    by_number[number].get("context")
                    for number in group
                    if number in by_number and by_number[number].get("context")
                ),
                None,
            )
            if not context:
                continue
            for number in group:
                question = by_number.get(number)
                if question and not question.get("context"):
                    question["context"] = context

    return questions, gaps
