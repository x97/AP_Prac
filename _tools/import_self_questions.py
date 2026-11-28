#!/usr/bin/env python3
"""Import self-authored MCQ questions from an Excel workbook.

Questions are stored in the app-side admin content overlay, so the immutable
Release is never modified and no database migration is required.

The workbook uses the template produced by
``_tools/make_self_question_template.py``:

    题干 | 选项A | 选项B | 选项C | 选项D | 选项E | 正确答案 | 解析 | 自研编号

Imported questions belong to one container paper per subject
(``<subject>-self-question-bank``) whose paper_type is ``unit_practice``.
That type is not shown in the student paper list, but the bank is selectable
in the admin question picker and can be used in classroom homework / study
plans.

Usage:
  .venv/bin/python _tools/import_self_questions.py \
    --input data/exports/自研题.xlsx --subject psychology --dry-run
  .venv/bin/python _tools/import_self_questions.py \
    --input data/exports/自研题.xlsx

If ``--subject`` is omitted in an interactive terminal, the importer asks the
admin to choose an enabled subject before reading the workbook. In a
non-interactive environment ``--subject`` is required.

Production (run inside the API container, where DATABASE_URL is set):
  python /tmp/import_self_questions.py --input /tmp/自研题.xlsx \
    --subject psychology
"""

from __future__ import annotations

import argparse
import sys
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

from app.core.db import SessionLocal
from app.services import subject_catalog
from app.services.effective_content import ensure_effective_content
from app.services.self_question_import import (
    DEFAULT_PAPER_TITLE,
    ImportValidationError,
    apply_plan,
    build_plan,
    id_prefix,
    paper_id_for,
)
from app.services.self_question_workbook import read_questions
from app.users.models import AdminUser
from sqlalchemy import select


def _choose_subject(
    configured: str | None,
    available: list[dict[str, Any]],
) -> dict[str, Any]:
    """Resolve the subject before reading or importing the workbook."""
    if not available:
        raise SystemExit("没有已启用的科目，无法导入")

    if configured:
        for item in available:
            if item["subject_id"] == configured:
                return item
        choices = "、".join(
            f"{item['name_zh']}（{item['subject_id']}）" for item in available
        )
        raise SystemExit(
            f"科目「{configured}」未启用或不存在。可选科目：{choices}"
        )

    if not sys.stdin.isatty():
        choices = "\n".join(
            f"  --subject {item['subject_id']}  # {item['name_zh']}"
            for item in available
        )
        raise SystemExit(
            "请先用 --subject 选择科目（非交互环境不会自动选择）：\n" + choices
        )

    print("请选择要导入的科目：")
    for index, item in enumerate(available, start=1):
        print(f"  {index}. {item['name_zh']} ({item['subject_id']})")
    while True:
        raw = input(f"输入序号 1-{len(available)}：").strip()
        if not raw.isdigit() or not 1 <= int(raw) <= len(available):
            print("序号无效，请重新输入。")
            continue
        chosen = available[int(raw) - 1]
        confirm = input(
            f"确认导入到「{chosen['name_zh']}」？[Y/n] "
        ).strip().lower()
        if confirm in ("", "y", "yes"):
            return chosen
        print("已取消，请重新选择。")


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
    parser.add_argument(
        "--subject",
        default=None,
        help="科目 ID；不填则先交互选择。",
    )
    parser.add_argument(
        "--paper-id",
        default=None,
        help="默认 <subject>-self-question-bank",
    )
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

    subject = _choose_subject(
        args.subject, subject_catalog.enabled_subject_payloads()
    )
    subject_id = str(subject["subject_id"])
    paper_id = args.paper_id or paper_id_for(subject_id)
    print(f"科目: {subject['name_zh']} ({subject_id})")

    questions, errors, warnings = read_questions(input_path)
    if errors:
        _print_messages("Excel 校验未通过", errors)
        return 1
    if not questions:
        print("没有可导入的题目", file=sys.stderr)
        return 1

    with SessionLocal() as db:
        admin = None
        if args.admin_email:
            admin = db.scalar(
                select(AdminUser).where(AdminUser.email == args.admin_email)
            )
            if admin is None:
                print(f"管理员账号不存在: {args.admin_email}", file=sys.stderr)
                return 1

        plan = build_plan(
            db,
            subject_id,
            questions,
            warnings,
            paper_id=paper_id,
            paper_title=args.paper_title,
        )
        _print_messages("提示", plan.warnings)
        if plan.errors:
            _print_messages("导入计划有误", plan.errors)
            return 1

        summary = plan.summary
        print(f"workbook: {input_path}")
        print(f"题目: {len(questions)} 行")
        print(f"题库: {paper_id} ({'已存在' if plan.paper_exists else '将创建'})")
        print(
            f"计划: 新增 {summary['create']}，更新 {summary['update']}，"
            f"无变化 {summary['unchanged']}"
        )

        if args.dry_run:
            print("dry run: 未写入数据库")
            return 0

        try:
            apply_plan(db, admin, plan)
        except ImportValidationError as exc:
            _print_messages("导入计划有误", exc.errors)
            return 1
        db.commit()
        ensure_effective_content(db, subject_id, force_marker_columns=True)
        print(
            f"已导入：新增 {summary['create']}，更新 {summary['update']}，"
            f"无变化 {summary['unchanged']}"
        )
        print(
            "后台查看：内容 → 题目；课堂作业 → 从题库选择题目时，"
            f"来源选「自研题」或搜索 {id_prefix(subject_id)}-self"
        )
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
