#!/usr/bin/env python3
"""Attach figures/tables for the CB Supplemental Practice Exam MCQ.

Four pages contain embedded raster images (p758, 762, 766, 772).  Other
question groups depend on vector graphs or text tables; for those we store a
rendered page screenshot so the question is still usable.
"""
import json
import os
import sqlite3
import subprocess
import sys
import tempfile

import pdfplumber
from PIL import Image, ImageFilter
from pypdf import PdfReader

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DB = os.path.join(ROOT, "data", "content", "psychology", "psychology_exam.db")
PDF = os.path.join(ROOT, "assets", "psychology", "papers", "cb", "26026_CB题库.pdf")
OUTDIR = os.path.join(ROOT, "assets", "psychology", "images", "cb2026")
RENDER = os.path.join(HERE, "render")
PAPER_ID = "psychology-cb-2026-mock-1"
QID_PREFIX = "psychology-cb26-mock1-"

# question -> (page, mode); mode image = crop embedded image, page = full page
FIGURES = [
    (8, 758, "image"),
    (10, 759, "page"),
    (16, 762, "image"),
    (22, 766, "image"),
    (35, 772, "image"),
    (37, 772, "image"),   # same graph as Q35
    (42, 776, "page"),
    (65, 786, "page"),
    (66, 787, "page"),
    (67, 787, "page"),
]


def trim(image):
    gray = image.convert("L").filter(ImageFilter.MedianFilter(3))
    inverted = gray.point(lambda p: 255 if p < 200 else 0)
    bbox = inverted.getbbox()
    if bbox:
        pad = 4
        image = image.crop((
            max(0, bbox[0] - pad), max(0, bbox[1] - pad),
            min(image.width, bbox[2] + pad), min(image.height, bbox[3] + pad),
        ))
    return image


def render_page(page_no, outdir, scale=3):
    subprocess.run(
        [RENDER, PDF, str(page_no), outdir, str(scale)],
        check=True, capture_output=True,
    )
    return os.path.join(outdir, f"page{page_no}.png")


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    con = sqlite3.connect(DB)
    con.execute("PRAGMA foreign_keys=ON")
    con.execute(
        "DELETE FROM assets WHERE asset_id LIKE 'psychology-cb26-mock1-%'"
    )

    reader = PdfReader(PDF)
    with pdfplumber.open(PDF) as doc:
        for number, page_no, mode in FIGURES:
            qid = f"{QID_PREFIX}{number:04d}"
            exists = con.execute(
                "SELECT 1 FROM questions WHERE question_id=?", (qid,)
            ).fetchone()
            if not exists:
                print(f"missing question {qid}", file=sys.stderr)
                continue

            page = doc.pages[page_no - 1]
            with tempfile.TemporaryDirectory(prefix="cbmockfig_") as tmp:
                png = render_page(page_no, tmp)
                image = Image.open(png).convert("RGB")
                if mode == "image":
                    images = page.images
                    if not images:
                        print(f"no image on p{page_no}, using full page", file=sys.stderr)
                        mode = "page"
                    else:
                        union = (
                            min(i["x0"] for i in images),
                            min(i["top"] for i in images),
                            max(i["x1"] for i in images),
                            max(i["bottom"] for i in images),
                        )
                        sw = image.width / page.width
                        sh = image.height / page.height
                        image = image.crop((
                            int(union[0] * sw), int(union[1] * sh),
                            int(union[2] * sw), int(union[3] * sh),
                        ))
                        image = trim(image)
                if image.width > 1600:
                    image = image.resize(
                        (1600, int(image.height * 1600 / image.width)),
                        Image.LANCZOS,
                    )

                kind = "figure" if mode == "image" else "page"
                suffix = "fig" if kind == "figure" else "page"
                path = os.path.join(
                    OUTDIR, f"mock1-q{number:04d}-{suffix}-p{page_no}.png"
                )
                image.save(path, optimize=True)

            asset_id = f"psychology-cb26-mock1-{suffix}-{number:04d}-p{page_no}"
            con.execute(
                "INSERT INTO assets (asset_id, question_id, option_label, kind, path, page, bbox) "
                "VALUES (?,?,?,?,?,?,?)",
                (
                    asset_id,
                    qid,
                    None,
                    kind,
                    os.path.relpath(path, ROOT),
                    page_no,
                    None,
                ),
            )
            print(f"{qid}: {kind} <- p{page_no}")

    con.commit()
    print("\nassets:", con.execute(
        "SELECT COUNT(*) FROM assets WHERE asset_id LIKE 'psychology-cb26-mock1-%'"
    ).fetchone()[0])
    print("questions covered:", con.execute(
        "SELECT COUNT(DISTINCT question_id) FROM assets "
        "WHERE asset_id LIKE 'psychology-cb26-mock1-%'"
    ).fetchone()[0])
    con.close()


if __name__ == "__main__":
    main()
