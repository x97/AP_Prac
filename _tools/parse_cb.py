"""Parser for the AP Classroom question-bank scoring-guide PDF.

The PDF interleaves questions, options, ``Answer X`` lines and short
explanations.  ``parse_unit`` turns a page range into question dicts.
"""
import re

DROP = re.compile(
    r"^(AP PSYCHOLOGY Scoring Guide|Scoring Guide|\d+:\s*[A-Z].*|"
    r"Scoring Guide \|\| AP Classroom.*|\d{1,3})$",
    re.I,
)
Q = re.compile(r"^(\d{1,3})\.\s*(.*)$")
OPT = re.compile(r"^\(([A-D])\)\s*(.*)$")
ANS = re.compile(r"^Answer\s+([A-D])\b", re.I)


def unit_lines(reader, a, b):
    lines = []
    for page in range(a, b + 1):
        text = reader.pages[page - 1].extract_text() or ""
        for line in text.split("\n"):
            line = re.sub(r"\s+", " ", line).strip()
            if line and not DROP.match(line):
                lines.append(line)
    return lines


def parse_unit(reader, a, b):
    """Parse questions from pages ``a``..``b`` (1-based, inclusive)."""
    questions = []
    current = None
    expected = 1
    gaps = []

    for line in unit_lines(reader, a, b):
        match = Q.match(line)
        if match and 1 <= int(match.group(1)) <= 500:
            number = int(match.group(1))
            if number == expected:
                if current:
                    questions.append(current)
                current = {
                    "number": number,
                    "stem": [match.group(2)],
                    "options": {},
                    "option": None,
                    "answer": None,
                    "explanation": [],
                }
                expected += 1
                continue
            if expected < number <= expected + 3:
                gaps.append((expected, number))
                if current:
                    questions.append(current)
                current = {
                    "number": number,
                    "stem": [match.group(2)],
                    "options": {},
                    "option": None,
                    "answer": None,
                    "explanation": [],
                }
                expected = number + 1
                continue

        if current is None:
            continue

        answer_match = ANS.match(line)
        if answer_match:
            current["answer"] = answer_match.group(1).upper()
            continue

        option_match = OPT.match(line)
        if option_match:
            current["options"][option_match.group(1)] = [option_match.group(2)]
            current["option"] = option_match.group(1)
            continue

        if current["answer"] and (
            line.startswith("Correct")
            or line.startswith("Incorrect")
            or current["explanation"]
        ):
            current["explanation"].append(line)
            continue

        if current["option"]:
            current["options"][current["option"]].append(line)
        else:
            current["stem"].append(line)

    if current:
        questions.append(current)

    for question in questions:
        question["stem"] = " ".join(question["stem"]).strip()
        question["options"] = {
            key: " ".join(value).strip()
            for key, value in question["options"].items()
        }
        question["explanation"] = " ".join(question["explanation"]).strip()
        question["expl"] = question["explanation"]  # backward-compatible key

    return questions, gaps
