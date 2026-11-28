#!/usr/bin/env python3
"""Import self-authored MCQ questions from an Excel workbook.

Questions are stored in the app-side admin content overlay, so the immutable
Release is never modified and no database migration is required.

The workbook uses the template produced by
``_tools/make_self_question_template.py``:

    题干 | 选项A | 选项B | 选项C | 选项D | 选项E | 正确答案 | 解析 | 自研编号

Imported questions belong to one container paper ("自研题库") whose paper_type
is ``unit_practice``. That type is not shown in the student paper list, but the
bank is selectable in the admin question picker and can be used in classroom
homework / study plans.

Usage:
  .venv/bin/python _tools/import_self_questions.py \
    --input data/exports/自研题.xlsx --dry-run
  .venv/bin/python _tools/import_self_questions.py \
    --input data/exports/自研题.xlsx

Production (run inside the API container, where DATABASE_URL is set):
  python /tmp/import_self_questions.py --input /tmp/自研题.xlsx
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
API_ROOT = ROOT / "apps" / "api"
if not (API_ROOT / "app").is_dir() and (Path("/app") / "app").is_dir():
    # The API container copies this script to /tmp; app code lives in /app.
    API_ROOT = Path("/app")
for candidate in (API_ROOT, HERE):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.services import admin_content, admin_overlay
from app.services.effective_content import ensure_effective_content
from app.users.models import AdminUser
from self_question_workbook import (
    ParsedQuestion,
    normalize_stem,
    read_questions,
)
from sqlalchemy import select

SUBJECT_ID = "psychology"
DEFAULT_PAPER_ID = "psychology-self-question-bank"
DEFAULT_PAPER_TITLE = "自研题库"
BANK_PAPER_TYPE = "unit_practice"


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9._-]+", "-", value.lower()).strip("-._")
    return slug[:48].strip("-._")


def _question_id(question: ParsedQuestion) -> str:
    """Derive a stable, readable id from the optional self code or the stem."""
    if question.code:
        token = _slug(question.code)
        if token:
            return f"psy-self-{token}"
        digest = hashlib.sha1(question.code.encode("utf-8")).hexdigest()[:12]
        return f"psy-self-{digest}"
    digest = hashlib.sha1(
        normalize_stem(question.stem).encode("utf-8")
    ).hexdigest()[:12]
    return f"psy-self-{digest}"


def _options(question: ParsedQuestion) -> list[dict[str, Any]]:
    return [
        {
            "label": label,
            "content": content,
            "sort_order": index,
            "is_correct": label == question.answer,
            "explanation": None,
            "ai_explanation": None,
        }
        for index, (label, content) in enumerate(question.options, start=1)
    ]


def _question_data(
    question: ParsedQuestion,
    question_id: str,
    number: int,
    paper_id: str,
    subject_id: str,
) -> dict[str, Any]:
    return {
        "question_id": question_id,
        "paper_id": paper_id,
        "section": "MCQ",
        "number": number,
        "form": None,
        "stem": question.stem,
        "context": "",
        "correct_answer": question.answer,
        "answer_text": question.explanation,
        "answer_source": "self",
        "answer_confidence": "self",
        "subject_id": subject_id,
        "options": _options(question),
        "self_code": question.code or None,
        "display_number": number,
    }


def _matches(existing: dict[str, Any], data: dict[str, Any]) -> bool:
    if (existing.get("stem") or "") != data["stem"]:
        return False
    if (existing.get("correct_answer") or "") != data["correct_answer"]:
        return False
    if (existing.get("answer_text") or "") != data["answer_text"]:
        return False
    left = sorted(
        existing.get("options") or [],
        key=lambda option: (option.get("sort_order") or 0, option.get("label") or ""),
    )
    right = sorted(
        data["options"],
        key=lambda option: (option["sort_order"], option["label"]),
    )
    if len(left) != len(right):
        return False
    for current, wanted in zip(left, right):
        if (current.get("label") or "") != wanted["label"]:
            return False
        if (current.get("content") or "") != wanted["content"]:
            return False
        if bool(current.get("is_correct")) != wanted["is_correct"]:
            return False
    return True


def _base_release_id(subject_id: str) -> str | None:
    try:
        payload = json.loads(
            (get_settings().resolve_base_content_dir(subject_id) / "release.json")
            .read_text(encoding="utf-8")
        )
        return str(payload.get("release_id") or "")
    except (OSError, json.JSONDecodeError):
        return None


def _print_messages(title: str, messages: list[str], limit: int = 30) -> None:
    if not messages:
        return
    print(f"{title} ({len(messages)})", file=sys.stderr)
    for message in messages[:limit]:
        print(f"  - {message}", file=sys.stderr)
    if len(messages) > limit:
        print(f"  ... 还有 {len(messages) - limit} 条", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--subject", default=SUBJECT_ID)
    parser.add_argument("--paper-id", default=DEFAULT_PAPER_ID)
    parser.add_argument("--paper-title", default=DEFAULT_PAPER_TITLE)
    parser.add_argument(
        "--admin-email",
        default=None,
        help="Admin user recorded as the creator (optional).",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    input_path = args.input.resolve()
    if not input_path.exists():
        parser.error(f"input not found: {input_path}")

    questions, errors, warnings = read_questions(input_path)
    if errors:
        _print_messages("Excel 校验未通过", errors)
        return 1
    _print_messages("提示", warnings)
    if not questions:
        print("没有可导入的题目", file=sys.stderr)
        return 1

    subject_id = args.subject
    paper_id = args.paper_id
    base_release_id = _base_release_id(subject_id)

    with SessionLocal() as db:
        admin = None
        if args.admin_email:
            admin = db.scalar(
                select(AdminUser).where(AdminUser.email == args.admin_email)
            )
            if admin is None:
                print(
                    f"管理员账号不存在: {args.admin_email}", file=sys.stderr
                )
                return 1

        ensure_effective_content(db, subject_id, force_marker_columns=True)
        paper = admin_content.get_paper(paper_id, subject_id=subject_id)
        if paper and paper.get("paper_type") != BANK_PAPER_TYPE:
            print(
                f"提示：题库试卷 {paper_id} 的类型是 {paper.get('paper_type')}，"
                f"预期是 {BANK_PAPER_TYPE}",
                file=sys.stderr,
            )

        existing_rows = (
            admin_content.list_questions(paper_id, subject_id=subject_id)
            if paper
            else []
        )
        existing_by_id = {
            str(row["question_id"]): row for row in existing_rows
        }
        existing_by_stem: dict[str, list[str]] = {}
        for row in existing_rows:
            key = normalize_stem(row.get("stem") or "")
            existing_by_stem.setdefault(key, []).append(str(row["question_id"]))

        records = admin_overlay.load_records(db, subject_id)
        code_to_id: dict[str, str] = {}
        overlay_codes: dict[str, str] = {}
        for record in records:
            if record.entity_type != "question":
                continue
            data = record.data or {}
            if data.get("paper_id") != paper_id:
                continue
            code = str(data.get("self_code") or "").strip()
            if code:
                code_to_id[code] = record.entity_id
            overlay_codes[record.entity_id] = code

        next_number = max(
            (int(row["number"]) for row in existing_rows), default=0
        ) + 1
        used_ids: set[str] = set()
        planned: list[tuple[str, str, dict[str, Any], bool]] = []
        plan_errors: list[str] = []

        for question in questions:
            question_id: str | None = None

            if question.code and question.code in code_to_id:
                question_id = code_to_id[question.code]
                if question_id not in existing_by_id:
                    plan_errors.append(
                        f"第 {question.row_number} 行：自研编号「"
                        f"{question.code}」对应的题目不在题库中"
                    )
                    continue

            if question_id is None:
                matches = existing_by_stem.get(
                    normalize_stem(question.stem)
                ) or []
                if len(matches) > 1:
                    plan_errors.append(
                        f"第 {question.row_number} 行：题库中有多道题干相同的题 "
                        f"({', '.join(matches)})，无法确定更新哪一道"
                    )
                    continue
                if matches:
                    question_id = matches[0]

            if question_id is None:
                candidate = _question_id(question)
                if candidate in existing_by_id:
                    question_id = candidate

            if question_id is None:
                question_id = _question_id(question)
                other = admin_content.get_question(
                    question_id, subject_id=subject_id
                )
                if other:
                    plan_errors.append(
                        f"第 {question.row_number} 行：生成的题目 ID "
                        f"{question_id} 已被其他试卷使用"
                    )
                    continue

            if question_id in used_ids:
                plan_errors.append(
                    f"第 {question.row_number} 行：与前面的行生成了相同的题目 ID "
                    f"{question_id}"
                )
                continue
            used_ids.add(question_id)

            if question_id in existing_by_id:
                number = int(existing_by_id[question_id]["number"])
                origin = admin_overlay.ORIGIN_EDITED
            else:
                number = next_number
                next_number += 1
                origin = admin_overlay.ORIGIN_CREATED

            data = _question_data(
                question, question_id, number, paper_id, subject_id
            )
            current = (
                admin_content.get_question(question_id, subject_id=subject_id)
                if question_id in existing_by_id
                else None
            )
            unchanged = bool(
                current
                and _matches(current, data)
                and overlay_codes.get(question_id, "") == question.code
            )
            planned.append((origin, question_id, data, unchanged))

        if plan_errors:
            _print_messages("导入计划有误", plan_errors)
            return 1

        creates = sum(
            1
            for item in planned
            if not item[3] and item[0] == admin_overlay.ORIGIN_CREATED
        )
        updates = sum(
            1
            for item in planned
            if not item[3] and item[0] == admin_overlay.ORIGIN_EDITED
        )
        unchanged_count = sum(1 for item in planned if item[3])

        print(f"workbook: {input_path}")
        print(f"题目: {len(questions)} 行")
        print(f"题库: {paper_id} ({'已存在' if paper else '将创建'})")
        print(
            f"计划: 新增 {creates}，更新 {updates}，无变化 {unchanged_count}"
        )

        if args.dry_run:
            print("dry run: 未写入数据库")
            return 0

        if paper is None:
            paper_record = admin_overlay.get_record(
                db, "paper", paper_id, subject_id=subject_id
            )
            if paper_record is None:
                admin_overlay.save_record(
                    db,
                    admin,
                    "paper",
                    paper_id,
                    admin_overlay.ORIGIN_CREATED,
                    {
                        "paper_id": paper_id,
                        "year": datetime.now().year,
                        "title": args.paper_title,
                        "chinese_title": args.paper_title,
                        "subject_id": subject_id,
                        "paper_type": BANK_PAPER_TYPE,
                        "question_count": len(planned),
                    },
                    subject_id=subject_id,
                    base_release_id=base_release_id,
                )

        for origin, question_id, data, unchanged in planned:
            if unchanged:
                continue
            admin_overlay.save_record(
                db,
                admin,
                "question",
                question_id,
                origin,
                data,
                subject_id=subject_id,
                base_release_id=base_release_id,
            )

        db.commit()
        ensure_effective_content(db, subject_id, force_marker_columns=True)
        print(
            f"已导入：新增 {creates}，更新 {updates}，无变化 {unchanged_count}"
        )
        print(
            "后台查看：内容 → 题目；课堂作业 → 从题库选择题目时，"
            "来源选「章节练习」或搜索 psy-self"
        )
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
