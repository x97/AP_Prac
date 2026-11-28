"""Plan and apply Excel imports for self-authored MCQ questions.

The import writes through the admin content overlay, so the immutable content
Release is never modified. A dedicated paper per subject stores the questions::

    <subject>-self-question-bank   paper_type = self_bank

That paper type is hidden from the student paper list but remains selectable in
the admin question picker and classroom homework builder.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.services import admin_content, admin_overlay
from app.services.effective_content import ensure_effective_content
from app.services.self_question_workbook import ParsedQuestion, normalize_stem

DEFAULT_PAPER_TITLE = "自研题库"
BANK_PAPER_SUFFIX = "-self-question-bank"
BANK_PAPER_TYPE = "self_bank"
MAX_IMPORT_ROWS = 500

ACTION_CREATE = "create"
ACTION_UPDATE = "update"
ACTION_UNCHANGED = "unchanged"


class ImportValidationError(Exception):
    """The workbook parsed, but the import plan contains blocking errors."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("；".join(errors[:3]) or "导入计划有误")


@dataclass
class PlannedQuestion:
    action: str
    question_id: str
    number: int
    data: dict[str, Any]
    parsed: ParsedQuestion


@dataclass
class ImportPlan:
    subject_id: str
    paper_id: str
    paper_title: str
    paper_exists: bool
    paper_type: Optional[str]
    items: list[PlannedQuestion] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def summary(self) -> dict[str, int]:
        return {
            "total": len(self.items),
            "create": sum(1 for item in self.items if item.action == ACTION_CREATE),
            "update": sum(1 for item in self.items if item.action == ACTION_UPDATE),
            "unchanged": sum(
                1 for item in self.items if item.action == ACTION_UNCHANGED
            ),
        }


def id_prefix(subject_id: str) -> str:
    return "psy" if subject_id == "psychology" else subject_id[:4]


def paper_id_for(subject_id: str) -> str:
    return f"{subject_id}{BANK_PAPER_SUFFIX}"


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9._-]+", "-", value.lower()).strip("-._")
    return slug[:48].strip("-._")


def _question_id(question: ParsedQuestion, subject_id: str) -> str:
    prefix = id_prefix(subject_id)
    if question.code:
        token = _slug(question.code)
        if token:
            return f"{prefix}-self-{token}"
        digest = hashlib.sha1(question.code.encode("utf-8")).hexdigest()[:12]
        return f"{prefix}-self-{digest}"
    digest = hashlib.sha1(
        normalize_stem(question.stem).encode("utf-8")
    ).hexdigest()[:12]
    return f"{prefix}-self-{digest}"


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


def _base_release_id(subject_id: str) -> Optional[str]:
    try:
        payload = json.loads(
            (get_settings().resolve_base_content_dir(subject_id) / "release.json")
            .read_text(encoding="utf-8")
        )
        return str(payload.get("release_id") or "")
    except (OSError, json.JSONDecodeError):
        return None


def build_plan(
    db: Session,
    subject_id: str,
    questions: list[ParsedQuestion],
    warnings: Optional[list[str]] = None,
    paper_id: Optional[str] = None,
    paper_title: str = DEFAULT_PAPER_TITLE,
) -> ImportPlan:
    """Match workbook rows against the current effective content.

    Returns a plan even when it contains blocking errors; callers decide
    whether to show them as a preview failure or refuse to apply.
    """
    target_paper_id = paper_id or paper_id_for(subject_id)
    plan = ImportPlan(
        subject_id=subject_id,
        paper_id=target_paper_id,
        paper_title=paper_title,
        paper_exists=False,
        paper_type=None,
        warnings=list(warnings or []),
    )
    if len(questions) > MAX_IMPORT_ROWS:
        plan.errors.append(
            f"单次最多导入 {MAX_IMPORT_ROWS} 道题，当前文件有 {len(questions)} 道"
        )
        return plan

    ensure_effective_content(db, subject_id, force_marker_columns=True)
    paper = admin_content.get_paper(target_paper_id, subject_id=subject_id)
    if paper:
        plan.paper_exists = True
        plan.paper_type = str(paper.get("paper_type") or "")
        if plan.paper_type != BANK_PAPER_TYPE:
            plan.warnings.append(
                f"题库试卷 {target_paper_id} 的类型是 {plan.paper_type}，"
                f"预期是 {BANK_PAPER_TYPE}"
            )

    existing_rows = (
        admin_content.list_questions(target_paper_id, subject_id=subject_id)
        if paper
        else []
    )
    existing_by_id = {str(row["question_id"]): row for row in existing_rows}
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
        if data.get("paper_id") != target_paper_id:
            continue
        code = str(data.get("self_code") or "").strip()
        if code:
            code_to_id[code] = record.entity_id
        overlay_codes[record.entity_id] = code

    next_number = (
        max((int(row["number"]) for row in existing_rows), default=0) + 1
    )
    used_ids: set[str] = set()

    for question in questions:
        question_id: Optional[str] = None

        if question.code and question.code in code_to_id:
            question_id = code_to_id[question.code]
            if question_id not in existing_by_id:
                plan.errors.append(
                    f"第 {question.row_number} 行：自研编号「"
                    f"{question.code}」对应的题目不在题库中"
                )
                continue

        if question_id is None:
            matches = existing_by_stem.get(normalize_stem(question.stem)) or []
            if len(matches) > 1:
                plan.errors.append(
                    f"第 {question.row_number} 行：题库中有多道题干相同的题 "
                    f"({', '.join(matches)})，无法确定更新哪一道"
                )
                continue
            if matches:
                question_id = matches[0]

        if question_id is None:
            candidate = _question_id(question, subject_id)
            if candidate in existing_by_id:
                question_id = candidate

        if question_id is None:
            question_id = _question_id(question, subject_id)
            other = admin_content.get_question(question_id, subject_id=subject_id)
            if other:
                plan.errors.append(
                    f"第 {question.row_number} 行：生成的题目 ID "
                    f"{question_id} 已被其他试卷使用"
                )
                continue

        if question_id in used_ids:
            plan.errors.append(
                f"第 {question.row_number} 行：与前面的行生成了相同的题目 ID "
                f"{question_id}"
            )
            continue
        used_ids.add(question_id)

        if question_id in existing_by_id:
            number = int(existing_by_id[question_id]["number"])
        else:
            number = next_number
            next_number += 1

        data = _question_data(
            question, question_id, number, target_paper_id, subject_id
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
        if unchanged:
            action = ACTION_UNCHANGED
        elif question_id in existing_by_id:
            action = ACTION_UPDATE
        else:
            action = ACTION_CREATE
        plan.items.append(
            PlannedQuestion(
                action=action,
                question_id=question_id,
                number=number,
                data=data,
                parsed=question,
            )
        )

    return plan


def preview_payload(plan: ImportPlan) -> dict[str, Any]:
    rows = []
    for item in plan.items:
        row_warnings = [
            warning
            for warning in plan.warnings
            if warning.startswith(f"第 {item.parsed.row_number} 行：")
        ]
        rows.append(
            {
                "row_number": item.parsed.row_number,
                "question_id": item.question_id,
                "number": item.number,
                "action": item.action,
                "stem": item.parsed.stem,
                "correct_answer": item.parsed.answer,
                "option_count": len(item.parsed.options),
                "self_code": item.parsed.code or None,
                "warnings": row_warnings,
            }
        )
    return {
        "subject_id": plan.subject_id,
        "paper_id": plan.paper_id,
        "paper_title": plan.paper_title,
        "paper_exists": plan.paper_exists,
        "paper_type": plan.paper_type,
        "summary": plan.summary,
        "rows": rows,
        "warnings": plan.warnings,
    }


def apply_plan(
    db: Session,
    admin: Any,
    plan: ImportPlan,
) -> dict[str, Any]:
    """Write the plan through the admin overlay. The caller commits."""
    if plan.errors:
        raise ImportValidationError(plan.errors)

    base_release_id = _base_release_id(plan.subject_id)
    if not plan.paper_exists:
        paper_record = admin_overlay.get_record(
            db, "paper", plan.paper_id, subject_id=plan.subject_id
        )
        if paper_record is None:
            admin_overlay.save_record(
                db,
                admin,
                "paper",
                plan.paper_id,
                admin_overlay.ORIGIN_CREATED,
                {
                    "paper_id": plan.paper_id,
                    "year": datetime.now().year,
                    "title": plan.paper_title,
                    "chinese_title": plan.paper_title,
                    "subject_id": plan.subject_id,
                    "paper_type": BANK_PAPER_TYPE,
                    "question_count": len(plan.items),
                },
                subject_id=plan.subject_id,
                base_release_id=base_release_id,
            )

    for item in plan.items:
        if item.action == ACTION_UNCHANGED:
            continue
        origin = (
            admin_overlay.ORIGIN_CREATED
            if item.action == ACTION_CREATE
            else admin_overlay.ORIGIN_EDITED
        )
        admin_overlay.save_record(
            db,
            admin,
            "question",
            item.question_id,
            origin,
            item.data,
            subject_id=plan.subject_id,
            base_release_id=base_release_id,
        )
    db.flush()
    return {
        "subject_id": plan.subject_id,
        "paper_id": plan.paper_id,
        "paper_title": plan.paper_title,
        "summary": plan.summary,
    }
