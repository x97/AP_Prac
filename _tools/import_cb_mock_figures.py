#!/usr/bin/env python3
"""Attach figures/tables for the CB Supplemental Practice Exam MCQ.

The paper has six source figures/tables, but ten questions reference them:

* Q8, Q10       -> height/weight graph on p758 (embedded image)
* Q16           -> card image on p762 (embedded image)
* Q22           -> attachment-style bar graph on p766 (embedded image)
* Q35, Q37      -> wins graph on p772 (embedded image)
* Q42           -> study-time table on p775 (text table; Q42 is on p776)
* Q65, Q66, Q67 -> job-success table on p786 (text table; Q66/Q67 are on p787)

Each source is rendered once and the same file path is attached to every
question in its group.  This avoids both failure modes seen in the first
import: a question pointing at a page that does not contain its stimulus
(Q10 -> p759, Q42 -> p776, Q66/Q67 -> p787), and duplicate copies of one
shared graph/table.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path

import fitz
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DB = os.path.join(ROOT, "data", "content", "psychology", "psychology_exam.db")
PDF = os.path.join(ROOT, "assets", "psychology", "papers", "cb", "26026_CB题库.pdf")
OUTDIR = os.path.join(ROOT, "assets", "psychology", "images", "cb2026")
PAPER_ID = "psychology-cb-2026-mock-1"
QID_PREFIX = "psychology-cb26-mock1-"
SCALE = 3

# `bbox` is in PDF points (612 x 792 page), not rendered pixels.  It covers
# the table title/headers and all rows, but not the question text.
FIGURES = [
    {
        "questions": [8, 10],
        "page": 758,
        "kind": "figure",
        "mode": "image",
        "description": "Height and Weight of Participants",
    },
    {
        "questions": [16],
        "page": 762,
        "kind": "figure",
        "mode": "image",
        "description": "Card used in the blind-spot demonstration",
    },
    {
        "questions": [22],
        "page": 766,
        "kind": "figure",
        "mode": "image",
        "description": "Level of Emotional Instability by Attachment Style",
    },
    {
        "questions": [35, 37],
        "page": 772,
        "kind": "figure",
        "mode": "image",
        "description": "Number of Wins as a Function of Sport and Game Location",
    },
    {
        "questions": [42],
        "page": 775,
        "kind": "table",
        "mode": "crop",
        "bbox": (185, 525, 430, 715),
        "description": "Study time by sticker group",
    },
    {
        "questions": [65, 66, 67],
        "page": 786,
        "kind": "table",
        "mode": "crop",
        "bbox": (130, 310, 480, 600),
        "description": "Student GPAs, Engineering Aptitude Scores, and Job Success Ratings",
    },
]


def trim(image: Image.Image) -> Image.Image:
    gray = image.convert("L").filter(ImageFilter.MedianFilter(3))
    inverted = gray.point(lambda p: 255 if p < 200 else 0)
    bbox = inverted.getbbox()
    if bbox:
        pad = 4
        image = image.crop(
            (
                max(0, bbox[0] - pad),
                max(0, bbox[1] - pad),
                min(image.width, bbox[2] + pad),
                min(image.height, bbox[3] + pad),
            )
        )
    return image


def render_page(page: fitz.Page) -> Image.Image:
    pix = page.get_pixmap(matrix=fitz.Matrix(SCALE, SCALE), alpha=False)
    return Image.frombytes("RGB", [pix.width, pix.height], pix.samples)


def image_source_rect(page: fitz.Page) -> fitz.Rect | None:
    """Union of embedded images, plus a short title/caption block.

    Some graphs have their title as a separate text block just below the
    raster image.  Expand by a small margin, then include only short,
    non-question text blocks.  Question/option/answer blocks cap the
    expansion so Q16 does not include its first question line.
    """
    rects: list[fitz.Rect] = []
    for image in page.get_images(full=True):
        try:
            rects.append(page.get_image_bbox(image))
        except (ValueError, RuntimeError):
            continue
    if not rects:
        return None

    union = fitz.Rect(
        min(rect.x0 for rect in rects),
        min(rect.y0 for rect in rects),
        max(rect.x1 for rect in rects),
        max(rect.y1 for rect in rects),
    )
    expanded = fitz.Rect(union.x0 - 5, union.y0 - 10, union.x1 + 5, union.y1 + 30)

    for block in page.get_text("blocks"):
        x0, y0, x1, y1, text, *_rest = block
        text = " ".join(text.split())
        if not text:
            continue
        block_rect = fitz.Rect(x0, y0, x1, y1)
        forbidden = (
            text[0].isdigit()
            or text.startswith("(")
            or text.startswith("Answer")
            or text.startswith("Correct")
            or text.startswith("Incorrect")
        )
        if forbidden:
            if block_rect.y0 >= union.y1:
                expanded.y1 = min(expanded.y1, block_rect.y0 - 2)
            elif block_rect.y1 <= union.y0:
                expanded.y0 = max(expanded.y0, block_rect.y1 + 2)
        elif len(text) < 120 and block_rect.intersects(expanded):
            expanded |= block_rect

    return fitz.Rect(
        max(0, expanded.x0),
        max(0, expanded.y0),
        min(page.rect.width, expanded.x1),
        min(page.rect.height, expanded.y1),
    )


def crop_rect(image: Image.Image, page: fitz.Page, rect: fitz.Rect) -> Image.Image:
    scale_x = image.width / page.rect.width
    scale_y = image.height / page.rect.height
    return image.crop(
        (
            int(rect.x0 * scale_x),
            int(rect.y0 * scale_y),
            int(rect.x1 * scale_x),
            int(rect.y1 * scale_y),
        )
    )


def normalized_bbox(page: fitz.Page, rect: fitz.Rect) -> list[float]:
    return [
        round(rect.x0 / page.rect.width, 4),
        round(rect.y0 / page.rect.height, 4),
        round(rect.x1 / page.rect.width, 4),
        round(rect.y1 / page.rect.height, 4),
    ]


def asset_id(kind: str, number: int, page_no: int) -> str:
    prefix = {"figure": "fig", "table": "table", "page": "page"}[kind]
    return f"psychology-cb26-mock1-{prefix}-{number:04d}-p{page_no}"


def main() -> int:
    os.makedirs(OUTDIR, exist_ok=True)
    for old in Path(OUTDIR).glob("mock1-q*.png"):
        old.unlink()

    con = sqlite3.connect(DB)
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("DELETE FROM assets WHERE asset_id LIKE 'psychology-cb26-mock1-%'")

    written: dict[tuple[int, str], str] = {}
    asset_rows = 0
    with fitz.open(PDF) as doc:
        for spec in FIGURES:
            page_no = int(spec["page"])
            page = doc[page_no - 1]
            image = render_page(page)

            if spec["mode"] == "image":
                rect = image_source_rect(page)
                if rect is None:
                    print(
                        f"no embedded image on p{page_no}; using full page",
                        file=sys.stderr,
                    )
                    rect = page.rect
                    kind = "page"
                else:
                    kind = "figure"
            elif spec["mode"] == "crop":
                rect = fitz.Rect(*spec["bbox"])
                kind = str(spec["kind"])
            else:
                rect = page.rect
                kind = "page"

            image = crop_rect(image, page, rect)
            if kind != "page":
                image = trim(image)
            if image.width > 1600:
                image = image.resize(
                    (1600, int(image.height * 1600 / image.width)),
                    Image.LANCZOS,
                )

            suffix = {"figure": "fig", "table": "table", "page": "page"}[kind]
            first_number = int(spec["questions"][0])
            path = os.path.join(
                OUTDIR, f"mock1-q{first_number:04d}-{suffix}-p{page_no}.png"
            )
            key = (page_no, kind)
            if key in written:
                path = written[key]
            else:
                image.save(path, optimize=True)
                written[key] = path

            bbox = (
                json.dumps(normalized_bbox(page, rect))
                if kind != "page"
                else None
            )
            for number in spec["questions"]:
                qid = f"{QID_PREFIX}{number:04d}"
                if not con.execute(
                    "SELECT 1 FROM questions WHERE question_id=?", (qid,)
                ).fetchone():
                    print(f"missing question {qid}", file=sys.stderr)
                    continue
                con.execute(
                    "INSERT INTO assets "
                    "(asset_id, question_id, option_label, kind, path, page, bbox, description) "
                    "VALUES (?,?,?,?,?,?,?,?)",
                    (
                        asset_id(kind, number, page_no),
                        qid,
                        None,
                        kind,
                        os.path.relpath(path, ROOT),
                        page_no,
                        bbox,
                        spec.get("description"),
                    ),
                )
                asset_rows += 1
                print(f"{qid}: {kind} <- p{page_no} ({os.path.basename(path)})")

    con.commit()
    print(f"\nfiles: {len(written)}")
    print(f"asset rows: {asset_rows}")
    print(
        "questions covered:",
        con.execute(
            "SELECT COUNT(DISTINCT question_id) FROM assets "
            "WHERE asset_id LIKE 'psychology-cb26-mock1-%'"
        ).fetchone()[0],
    )
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
