from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.services import admin_content, admin_overlay, effective_content
from app.users.models import AdminUser

SUBJECT_ID = "psychology"


def _ensure_content(db: Session, subject_id: str = SUBJECT_ID) -> None:
    effective_content.ensure_effective_content(
        db, subject_id, force_marker_columns=True
    )


def refresh_content(db: Session, subject_id: str = SUBJECT_ID) -> None:
    try:
        effective_content.ensure_effective_content(
            db, subject_id, force_marker_columns=True
        )
    except Exception as exc:  # noqa: BLE001
        raise AppError(
            503,
            "ADMIN_CONTENT_MATERIALIZE_FAILED",
            "管理员内容已保存，但生成学生端内容失败，请重试",
        ) from exc


def _base_release_id(subject_id: str = SUBJECT_ID) -> Optional[str]:
    try:
        payload = json.loads(
            (get_settings().resolve_base_content_dir(subject_id) / "release.json").read_text(
                encoding="utf-8"
            )
        )
        return str(payload.get("release_id") or "")
    except (OSError, json.JSONDecodeError):
        return None


def _id_prefix(subject_id: str) -> str:
    return "psy" if subject_id == "psychology" else subject_id[:4]


def _save(
    db: Session,
    admin: AdminUser,
    entity_type: str,
    entity_id: str,
    origin: str,
    data: dict[str, Any],
    *,
    subject_id: str = SUBJECT_ID,
) -> None:
    admin_overlay.save_record(
        db,
        admin,
        entity_type,
        entity_id,
        origin,
        data,
        subject_id=subject_id,
        base_release_id=_base_release_id(subject_id),
    )


def _question_data(
    question: dict[str, Any],
    updates: dict[str, Any],
    subject_id: str = SUBJECT_ID,
) -> dict[str, Any]:
    data: dict[str, Any] = {
        "question_id": question["question_id"],
        "paper_id": question["paper_id"],
        "section": question["section"],
        "number": question["number"],
        "form": question.get("form"),
        "stem": question["stem"],
        "context": question.get("context") or "",
        "correct_answer": question.get("correct_answer"),
        "answer_text": question.get("answer_text") or "",
        "answer_source": question.get("answer_source"),
        "answer_confidence": question.get("answer_confidence"),
        "subject_id": subject_id,
        "options": question.get("options") or [],
    }
    for key in (
        "stem",
        "context",
        "answer_text",
        "answer_source",
        "answer_confidence",
        "form",
    ):
        if key in updates:
            data[key] = updates[key]
    if "options" in updates:
        data["options"] = updates["options"]
    return data


def _validate_options(section: str, options: list[dict[str, Any]]) -> str | None:
    if section != "MCQ":
        return None
    if len(options) < 2 or len(options) > 5:
        raise AppError(400, "OPTION_COUNT_INVALID", "选项数量必须在 2 到 5 个之间")
    labels = [str(item.get("label") or "").strip().upper() for item in options]
    if any(not label for label in labels):
        raise AppError(400, "OPTION_LABEL_REQUIRED", "选项标签不能为空")
    if len(set(labels)) != len(labels):
        raise AppError(400, "OPTION_LABEL_DUPLICATE", "选项标签不能重复")
    correct = [label for label, item in zip(labels, options) if bool(item.get("is_correct"))]
    if len(correct) != 1:
        raise AppError(400, "MCQ_CORRECT_COUNT", "MCQ 必须恰好有一个正确选项")
    return correct[0]


def _normalise_options(options: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for index, item in enumerate(options, start=1):
        out.append(
            {
                "label": str(item.get("label") or "").strip().upper(),
                "content": str(item.get("content") or ""),
                "sort_order": index,
                "is_correct": bool(item.get("is_correct")),
                "explanation": item.get("explanation"),
                "ai_explanation": item.get("ai_explanation"),
            }
        )
    return out


def update_question(
    db: Session,
    admin: AdminUser,
    question_id: str,
    updates: dict[str, Any],
    subject_id: str = SUBJECT_ID,
) -> dict[str, Any]:
    _ensure_content(db, subject_id)
    current = admin_content.get_question(question_id, subject_id=subject_id)
    if not current:
        raise AppError(404, "QUESTION_NOT_FOUND", "题目不存在")
    if "options" in updates:
        correct = _validate_options(current["section"], updates["options"])
        updates = {**updates, "options": _normalise_options(updates["options"])}
        if current["section"] == "MCQ":
            updates["correct_answer"] = correct
    data = _question_data(current, updates, subject_id)
    _save(
        db,
        admin,
        "question",
        question_id,
        admin_overlay.ORIGIN_EDITED,
        data,
        subject_id=subject_id,
    )
    db.flush()
    return data


def create_question(
    db: Session,
    admin: AdminUser,
    payload: dict[str, Any],
) -> dict[str, Any]:
    subject_id = str(payload.get("subject_id") or SUBJECT_ID)
    _ensure_content(db, subject_id)
    paper_id = str(payload.get("paper_id") or "").strip()
    paper = admin_content.get_paper(paper_id, subject_id=subject_id)
    if not paper:
        raise AppError(404, "PAPER_NOT_FOUND", "试卷不存在")
    if paper.get("paper_type") in ("practice_bundle", "bundle"):
        raise AppError(
            400,
            "BUNDLE_QUESTION_UNSUPPORTED",
            "练习包是虚拟试卷，请在源试卷或练习 Topic 中维护题目",
        )
    section = str(payload.get("section") or "MCQ").upper()
    if section != "MCQ":
        raise AppError(400, "QUESTION_SECTION_UNSUPPORTED", "后台暂只支持新建 MCQ 题目")
    options = _normalise_options(payload.get("options") or [])
    correct = _validate_options(section, options)
    number = payload.get("number")
    if number is None:
        number = admin_content.next_question_number(paper_id, section, subject_id)
    number = int(number)
    if number < 1:
        raise AppError(400, "QUESTION_NUMBER_INVALID", "题号不合法")
    question_id = f"{_id_prefix(subject_id)}-admin-q-{uuid.uuid4().hex[:12]}"
    data: dict[str, Any] = {
        "question_id": question_id,
        "paper_id": paper_id,
        "section": section,
        "number": number,
        "form": None,
        "stem": str(payload.get("stem") or "").strip(),
        "context": str(payload.get("context") or ""),
        "correct_answer": correct,
        "answer_text": str(payload.get("answer_text") or ""),
        "answer_source": payload.get("answer_source") or "admin",
        "answer_confidence": payload.get("answer_confidence") or "admin",
        "subject_id": subject_id,
        "options": options,
    }
    if not data["stem"]:
        raise AppError(400, "STEM_REQUIRED", "题干不能为空")
    _save(
        db,
        admin,
        "question",
        question_id,
        admin_overlay.ORIGIN_CREATED,
        data,
        subject_id=subject_id,
    )
    db.flush()
    return data


def _concept_data(
    concept: dict[str, Any],
    updates: dict[str, Any],
    subject_id: str = SUBJECT_ID,
) -> dict[str, Any]:
    data = {
        "cluster_id": concept["cluster_id"],
        "subject_id": subject_id,
        "canonical_name": concept.get("canonical_name") or "",
        "canonical_kp_id": concept.get("canonical_kp_id"),
        "description": concept.get("description") or "",
        "ap_unit": concept.get("ap_unit"),
        "topic": concept.get("topic"),
        "status": concept.get("status") or "approved",
        "weight": concept.get("weight") or 0,
        "weight_tier": concept.get("weight_tier"),
        "member_count": concept.get("member_count") or 0,
    }
    for key in ("canonical_name", "description", "ap_unit", "topic", "status", "weight"):
        if key in updates:
            data[key] = updates[key]
    if "definition" in updates:
        data["description"] = str(updates["definition"] or "")
    if "weight_tier" in updates:
        data["weight_tier"] = updates["weight_tier"]
    return data


def create_concept(
    db: Session,
    admin: AdminUser,
    payload: dict[str, Any],
) -> dict[str, Any]:
    subject_id = str(payload.get("subject_id") or SUBJECT_ID)
    _ensure_content(db, subject_id)
    name = str(payload.get("canonical_name") or "").strip()
    if not name:
        raise AppError(400, "CONCEPT_NAME_REQUIRED", "知识点名称不能为空")
    if admin_content.concept_name_taken(name, subject_id=subject_id):
        raise AppError(409, "CONCEPT_NAME_EXISTS", "已存在同名知识点，请先搜索并关联")
    definition = str(payload.get("definition") or "").strip()
    if not definition:
        raise AppError(400, "CONCEPT_DEFINITION_REQUIRED", "请填写知识点释义")
    cluster_id = f"{_id_prefix(subject_id)}-admin-c-{uuid.uuid4().hex[:12]}"
    data = {
        "cluster_id": cluster_id,
        "subject_id": subject_id,
        "canonical_name": name,
        "canonical_kp_id": None,
        "description": definition,
        "ap_unit": str(payload.get("ap_unit") or "").strip() or None,
        "topic": str(payload.get("topic") or "").strip() or None,
        "status": "approved",
        "weight": 0,
        "weight_tier": "admin",
        "member_count": 0,
    }
    _save(
        db,
        admin,
        "concept",
        cluster_id,
        admin_overlay.ORIGIN_CREATED,
        data,
        subject_id=subject_id,
    )
    db.flush()
    return data


def update_concept(
    db: Session,
    admin: AdminUser,
    cluster_id: str,
    updates: dict[str, Any],
    subject_id: str = SUBJECT_ID,
) -> dict[str, Any]:
    _ensure_content(db, subject_id)
    current = admin_content.get_concept(cluster_id, subject_id=subject_id)
    if not current:
        raise AppError(404, "CONCEPT_NOT_FOUND", "概念不存在")
    if "canonical_name" in updates:
        name = str(updates["canonical_name"] or "").strip()
        if not name:
            raise AppError(400, "CONCEPT_NAME_REQUIRED", "知识点名称不能为空")
        if admin_content.concept_name_taken(
            name, exclude_id=cluster_id, subject_id=subject_id
        ):
            raise AppError(409, "CONCEPT_NAME_EXISTS", "已存在同名知识点")
        updates = {**updates, "canonical_name": name}
    data = _concept_data(current, updates, subject_id)
    _save(
        db,
        admin,
        "concept",
        cluster_id,
        admin_overlay.ORIGIN_EDITED,
        data,
        subject_id=subject_id,
    )
    db.flush()
    return data


def update_kp(
    db: Session,
    admin: AdminUser,
    kp_id: str,
    updates: dict[str, Any],
    subject_id: str = SUBJECT_ID,
) -> dict[str, Any]:
    _ensure_content(db, subject_id)
    current = admin_content.get_kp(kp_id, subject_id=subject_id)
    if not current:
        raise AppError(404, "KP_NOT_FOUND", "知识点不存在")
    data = dict(current)
    allowed = {"name", "plain_en", "definition_quote", "subheading", "status", "weight"}
    for key in allowed:
        if key in updates:
            data[key] = updates[key]
    if "name" in updates:
        name = str(updates["name"] or "").strip()
        if not name:
            raise AppError(400, "KP_NAME_REQUIRED", "知识点名称不能为空")
        data["name"] = name
        data["name_normalized"] = name.lower()
    data["updated_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    _save(
        db,
        admin,
        "knowledge_point",
        kp_id,
        admin_overlay.ORIGIN_EDITED,
        data,
        subject_id=subject_id,
    )
    db.flush()
    return data


def update_paper(
    db: Session,
    admin: AdminUser,
    paper_id: str,
    updates: dict[str, Any],
    subject_id: str = SUBJECT_ID,
) -> dict[str, Any]:
    _ensure_content(db, subject_id)
    current = admin_content.get_paper(paper_id, subject_id=subject_id)
    if not current:
        raise AppError(404, "PAPER_NOT_FOUND", "试卷不存在")
    if (
        current.get("paper_type") in ("practice_bundle", "bundle")
        and "paper_type" in updates
        and updates["paper_type"] != current.get("paper_type")
    ):
        raise AppError(
            400,
            "BUNDLE_TYPE_IMMUTABLE",
            "练习包由 paper_question_map 组织，不能改为普通试卷类型",
        )
    data = dict(current)
    for key in ("year", "title", "chinese_title", "paper_type"):
        if key in updates:
            data[key] = updates[key]
    _save(
        db,
        admin,
        "paper",
        paper_id,
        admin_overlay.ORIGIN_EDITED,
        data,
        subject_id=subject_id,
    )
    db.flush()
    return data


def _link_entity_id(
    question_id: str, concept_id: str, relation_type: str, option_label: Optional[str]
) -> str:
    return f"{question_id}|{concept_id}|{relation_type}|{option_label or ''}"


def _validate_link(
    db: Session,
    question_id: str,
    payload: dict[str, Any],
    subject_id: str = SUBJECT_ID,
) -> tuple[str, str, str, Optional[str]]:
    current = admin_content.get_question(question_id, subject_id=subject_id)
    if not current:
        raise AppError(404, "QUESTION_NOT_FOUND", "题目不存在")
    concept_id = str(payload.get("concept_id") or "").strip()
    concept = admin_content.get_concept(concept_id, subject_id=subject_id)
    if not concept:
        raise AppError(404, "CONCEPT_NOT_FOUND", "知识点不存在")
    relation_type = str(payload.get("relation_type") or "core").strip()
    if relation_type not in ("core", "supporting", "confusable"):
        raise AppError(400, "LINK_RELATION_INVALID", "关联类型不合法")
    option_label = str(payload.get("option_label") or "").strip().upper() or None
    if relation_type == "confusable":
        if not option_label:
            raise AppError(400, "LINK_OPTION_REQUIRED", "易混知识点必须选择干扰项")
        labels = {str(item.get("label") or "").upper() for item in current.get("options") or []}
        if labels and option_label not in labels:
            raise AppError(400, "LINK_OPTION_INVALID", "干扰项不存在于该题")
    else:
        option_label = None
    return concept_id, relation_type, option_label, current.get("section")


def _add_link_record(
    db: Session,
    admin: AdminUser,
    question_id: str,
    payload: dict[str, Any],
    subject_id: str = SUBJECT_ID,
) -> None:
    concept_id, relation_type, option_label, _ = _validate_link(
        db, question_id, payload, subject_id
    )
    entity_id = _link_entity_id(question_id, concept_id, relation_type, option_label)
    existing = admin_overlay.get_record(db, "question_concept_link", entity_id)
    origin = (
        admin_overlay.ORIGIN_CREATED
        if existing is None or existing.origin == admin_overlay.ORIGIN_DELETED
        else existing.origin
    )
    _save(
        db,
        admin,
        "question_concept_link",
        entity_id,
        origin,
        {
            "question_id": question_id,
            "concept_id": concept_id,
            "relation_type": relation_type,
            "option_label": option_label,
            "confidence": 1.0,
            "evidence": "admin",
            "rationale": "管理员关联",
            "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        },
        subject_id=subject_id,
    )


def add_question_concept_link(
    db: Session,
    admin: AdminUser,
    question_id: str,
    payload: dict[str, Any],
    subject_id: str = SUBJECT_ID,
) -> dict[str, Any]:
    _ensure_content(db, subject_id)
    _add_link_record(db, admin, question_id, payload, subject_id)
    db.flush()
    return {
        "ok": True,
        "concepts": admin_content.get_question_concepts(
            question_id, subject_id=subject_id
        ),
    }


def delete_question_concept_link(
    db: Session,
    admin: AdminUser,
    question_id: str,
    link_id: int,
    subject_id: str = SUBJECT_ID,
) -> dict[str, Any]:
    _ensure_content(db, subject_id)
    links = admin_content.get_question_concepts(
        question_id, subject_id=subject_id
    )
    target = next((item for item in links if int(item.get("link_id") or 0) == int(link_id)), None)
    if not target:
        raise AppError(404, "LINK_NOT_FOUND", "知识点关联不存在")
    entity_id = _link_entity_id(
        question_id,
        str(target["concept_id"]),
        str(target["relation_type"]),
        target.get("option_label"),
    )
    _save(
        db,
        admin,
        "question_concept_link",
        entity_id,
        admin_overlay.ORIGIN_DELETED,
        {
            "question_id": question_id,
            "concept_id": str(target["concept_id"]),
            "relation_type": str(target["relation_type"]),
            "option_label": target.get("option_label"),
        },
        subject_id=subject_id,
    )
    db.flush()
    return {
        "ok": True,
        "concepts": admin_content.get_question_concepts(
            question_id, subject_id=subject_id
        ),
    }
