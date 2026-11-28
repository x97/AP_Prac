#!/usr/bin/env python3
"""Generate the Excel template for self-authored MCQ questions.

Usage:
  .venv/bin/python _tools/make_self_question_template.py
  .venv/bin/python _tools/make_self_question_template.py --output /tmp/自研题模板.xlsx
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
API_ROOT = ROOT / "apps" / "api"
if not (API_ROOT / "app").is_dir() and (Path("/app") / "app").is_dir():
    API_ROOT = Path("/app")
for candidate in (API_ROOT, HERE):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from app.services.self_question_workbook import write_template

DEFAULT_OUTPUT = ROOT / "data" / "exports" / "自研题导入模板.xlsx"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    output = args.output.resolve()
    write_template(output)
    print(f"template written: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
