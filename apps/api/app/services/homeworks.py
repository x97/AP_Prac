from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.content.store import ContentStore
from app.core.errors import AppError
from app.users.models import (
    ClassroomHomework,
    ClassroomHomeworkQuestion,
    QuestionStar,
    StudyPlan,
    StudyPlanItem,
    StudyPlanTask,
)

MAX_HOMEWORK_QUESTIONS = 300


def _topic_lookup(store: ContentStore) -> dict[str, dict[str, Any]]:
    return {str(row["topic_id"]): row for row in store.list_all_topics()}


def _unit_lookup(store: ContentStore) -> dict[str, dict[str, Any]]:
    return {str(row["unit_id"]): row for row in store.list_groups()}


def _validated_questions(
    store: ContentStore, question_ids: list[str]
) -> list[dict[str, Any]]:
    ids = [str(qid).strip() for qid in question_ids if str(qid).strip()]
    if not ids:
        raise AppError(400, "QUESTIONS_REQUIRED", "至少选择一道题目")
    if len(ids) > MAX_HOMEWORK_QUESTIONS:
        raise AppError(400, "TOO_MANY_QUESTIONS", f"每份课堂作业最多 {MAX_HOMEWORK_QUESTIONS} 题")
    if len(set(ids)) != len(ids):
        raise AppError(400, "DUPLICATE_QUESTIONS", "题目不能重复")
    existing = store.get_questions(ids, include_answers=False)
    missing = [qid for qid in ids if qid not in existing]
    if missing:
        raise AppError(400, "QUESTION_NOT_FOUND", f"{len(missing)} 道题目不在当前题库")
    non_mcq = [
        qid
        for qid in ids
        if (existing[qid].get("section") or "").upper() != "MCQ"
    ]
    if non_mcq:
        raise AppError(400, "QUESTION_TYPE_UNSUPPORTED", "课堂作业目前只支持选择题")
    return [
        {
            "question_id": qid,
            "section": existing[qid].get("section") or "MCQ",
            "paper_id": existing[qid].get("paper_id"),
        }
        for qid in ids
    ]


def _resolve_taxonomy(
    store: ContentStore, unit_id: Optional[str], topic_id: Optional[str]
) -> dict[str, Any]:
    topics = _topic_lookup(store)
    units = _unit_lookup(store)
    if not topic_id or topic_id not in topics:
        raise AppError(400, "TOPIC_REQUIRED", "请选择章节")
    topic = topics[topic_id]
    resolved_unit = str(topic["unit_id"])
    if unit_id and str(unit_id) != resolved_unit:
        raise AppError(400, "TOPIC_UNIT_MISMATCH", "章节不属于所选单元")
    group = next(
        (row for row in store.list_groups() if str(row["group_id"]) == str(topic["group_id"])),
        None,
    )
    unit = units.get(resolved_unit)
    return {
        "unit_id": resolved_unit,
        "unit_title": (unit or {}).get("title") or f"Unit {resolved_unit}",
        "topic_id": str(topic["topic_id"]),
        "topic_code": topic.get("code"),
        "topic_title": topic.get("title_zh") or topic.get("title_en") or "",
        "group_id": str(topic["group_id"]),
        "group_title": (group or {}).get("title"),
    }


def _set_questions(
    db: Session, homework: ClassroomHomework, questions: list[dict[str, Any]]
) -> None:
    db.execute(
        ClassroomHomeworkQuestion.__table__.delete().where(
            ClassroomHomeworkQuestion.homework_id == homework.id
        )
    )
    for index, question in enumerate(questions):
        db.add(
            ClassroomHomeworkQuestion(
                homework_id=homework.id,
                question_id=question["question_id"],
                sort_order=index,
                section=question.get("section") or "MCQ",
            )
        )
    homework.question_count = len(questions)


def _set_taxonomy(homework: ClassroomHomework, taxonomy: dict[str, Any]) -> None:
    homework.unit_id = taxonomy["unit_id"]
    homework.unit_title = taxonomy["unit_title"]
    homework.topic_id = taxonomy["topic_id"]
    homework.topic_code = taxonomy["topic_code"]
    homework.topic_title = taxonomy["topic_title"]


def _rebuild_pending_task_snapshots(
    db: Session, homework: ClassroomHomework
) -> None:
    tasks = db.scalars(
        select(StudyPlanTask).where(
            StudyPlanTask.homework_id == homework.id,
            StudyPlanTask.status == "pending",
            StudyPlanTask.cancelled_at.is_(None),
        )
    ).all()
    for task in tasks:
        if task.practice_session_id:
            continue
        task.homework_version = homework.version
        task.homework_title = homework.title
        task.note = homework.note or ""
        task.unit_id = homework.unit_id
        task.unit_title = homework.unit_title
        task.topic_id = homework.topic_id
        task.topic_title = homework.topic_title
        task.question_count = homework.question_count


def list_homeworks(
    db: Session,
    store: ContentStore,
    *,
    subject_id: str,
    q: Optional[str] = None,
    unit_id: Optional[str] = None,
    topic_id: Optional[str] = None,
    status: str = "active",
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    clauses = [ClassroomHomework.subject_id == subject_id]
    if status and status != "all":
        clauses.append(ClassroomHomework.status == status)
    if unit_id:
        clauses.append(ClassroomHomework.unit_id == str(unit_id))
    if topic_id:
        clauses.append(ClassroomHomework.topic_id == topic_id)
    if q:
        needle = f"%{q.strip()}%"
        clauses.append(
            or_(ClassroomHomework.title.ilike(needle), ClassroomHomework.note.ilike(needle))
        )
    total = db.scalar(
        select(func.count(ClassroomHomework.id)).where(*clauses)
    ) or 0
    rows = db.scalars(
        select(ClassroomHomework)
        .where(*clauses)
        .order_by(ClassroomHomework.updated_at.desc(), ClassroomHomework.created_at.desc())
        .limit(max(1, min(limit, 200)))
        .offset(max(0, offset))
    ).all()
    ids = [row.id for row in rows]
    usage: dict[str, int] = {}
    plan_titles: dict[str, list[str]] = {}
    if ids:
        usage_rows = db.execute(
            select(StudyPlanItem.homework_id, func.count(func.distinct(StudyPlanItem.plan_id)))
            .where(StudyPlanItem.homework_id.in_(ids))
            .group_by(StudyPlanItem.homework_id)
        ).all()
        usage = {row[0]: int(row[1]) for row in usage_rows}
        title_rows = db.execute(
            select(StudyPlanItem.homework_id, StudyPlan.title)
            .join(StudyPlan, StudyPlan.id == StudyPlanItem.plan_id)
            .where(StudyPlanItem.homework_id.in_(ids))
            .distinct()
        ).all()
        for homework_id, title in title_rows:
            plan_titles.setdefault(homework_id, []).append(title)
    items = []
    for row in rows:
        item = _homework_payload(row)
        item["used_in_plans"] = usage.get(row.id, 0)
        item["plan_titles"] = plan_titles.get(row.id, [])[:5]
        items.append(item)
    return {"homeworks": items, "total": int(total), "limit": limit, "offset": offset}


def _homework_payload(homework: ClassroomHomework) -> dict[str, Any]:
    return {
        "id": homework.id,
        "subject_id": homework.subject_id,
        "title": homework.title,
        "note": homework.note or "",
        "unit_id": homework.unit_id,
        "unit_title": homework.unit_title,
        "topic_id": homework.topic_id,
        "topic_code": homework.topic_code,
        "topic_title": homework.topic_title,
        "question_count": homework.question_count,
        "status": homework.status,
        "version": homework.version,
        "content_release_id": homework.content_release_id,
        "created_at": homework.created_at,
        "updated_at": homework.updated_at,
    }


def _question_rows(db: Session, homework_id: str) -> list[dict[str, Any]]:
    rows = db.execute(
        select(
            ClassroomHomeworkQuestion.question_id,
            ClassroomHomeworkQuestion.sort_order,
            ClassroomHomeworkQuestion.section,
        )
        .where(ClassroomHomeworkQuestion.homework_id == homework_id)
        .order_by(ClassroomHomeworkQuestion.sort_order)
    ).all()
    return [dict(row._mapping) for row in rows]


def get_homework(
    db: Session, store: ContentStore, homework_id: str, subject_id: str
) -> dict[str, Any]:
    homework = db.get(ClassroomHomework, homework_id)
    if homework is None or homework.subject_id != subject_id:
        raise AppError(404, "HOMEWORK_NOT_FOUND", "课堂作业不存在")
    rows = _question_rows(db, homework.id)
    ids = [row["question_id"] for row in rows]
    details = store.get_questions(ids, include_answers=True)
    stars = {
        row.question_id: row.stars
        for row in db.scalars(
            select(QuestionStar).where(
                QuestionStar.subject_id == subject_id,
                QuestionStar.question_id.in_(ids),
            )
        ).all()
    } if ids else {}
    questions = []
    for row in rows:
        detail = details.get(row["question_id"])
        if not detail:
            questions.append(
                {
                    "question_id": row["question_id"],
                    "sort_order": row["sort_order"],
                    "section": row["section"],
                    "missing": True,
                }
            )
            continue
        questions.append(
            {
                **detail,
                "sort_order": row["sort_order"],
                "section": row["section"],
                "stars": stars.get(row["question_id"]),
                "missing": False,
            }
        )
    payload = _homework_payload(homework)
    payload["questions"] = questions
    payload["used_in_plans"] = db.scalar(
        select(func.count(func.distinct(StudyPlanItem.plan_id))).where(
            StudyPlanItem.homework_id == homework.id
        )
    ) or 0
    payload["plan_titles"] = [
        row[0]
        for row in db.execute(
            select(StudyPlan.title)
            .join(StudyPlanItem, StudyPlanItem.plan_id == StudyPlan.id)
            .where(StudyPlanItem.homework_id == homework.id)
            .distinct()
        ).all()
    ][:10]
    return payload


def create_homework(
    db: Session,
    store: ContentStore,
    *,
    subject_id: str,
    title: str,
    note: Optional[str],
    unit_id: Optional[str],
    topic_id: Optional[str],
    question_ids: list[str],
    created_by: Optional[str],
) -> dict[str, Any]:
    title = (title or "").strip()
    if not title or len(title) > 200:
        raise AppError(400, "TITLE_INVALID", "标题长度需在 1–200 字之间")
    if note and len(note) > 5000:
        raise AppError(400, "NOTE_TOO_LONG", "备注最多 5000 字")
    taxonomy = _resolve_taxonomy(store, unit_id, topic_id)
    questions = _validated_questions(store, question_ids)
    homework = ClassroomHomework(
        subject_id=subject_id,
        title=title,
        note=note or "",
        unit_id=taxonomy["unit_id"],
        unit_title=taxonomy["unit_title"],
        topic_id=taxonomy["topic_id"],
        topic_code=taxonomy["topic_code"],
        topic_title=taxonomy["topic_title"],
        question_count=len(questions),
        status="active",
        version=1,
        content_release_id=store.release_id,
        created_by=created_by,
    )
    db.add(homework)
    db.flush()
    _set_questions(db, homework, questions)
    db.commit()
    return get_homework(db, store, homework.id, subject_id)


def update_homework(
    db: Session,
    store: ContentStore,
    homework_id: str,
    *,
    subject_id: str,
    title: Optional[str] = None,
    note: Optional[str] = None,
    unit_id: Optional[str] = None,
    topic_id: Optional[str] = None,
    question_ids: Optional[list[str]] = None,
) -> dict[str, Any]:
    homework = db.get(ClassroomHomework, homework_id)
    if homework is None or homework.subject_id != subject_id:
        raise AppError(404, "HOMEWORK_NOT_FOUND", "课堂作业不存在")
    if title is not None:
        title = title.strip()
        if not title or len(title) > 200:
            raise AppError(400, "TITLE_INVALID", "标题长度需在 1–200 字之间")
        homework.title = title
    if note is not None:
        if len(note) > 5000:
            raise AppError(400, "NOTE_TOO_LONG", "备注最多 5000 字")
        homework.note = note
    if unit_id is not None or topic_id is not None:
        taxonomy = _resolve_taxonomy(store, unit_id, topic_id or homework.topic_id)
        _set_taxonomy(homework, taxonomy)
    if question_ids is not None:
        questions = _validated_questions(store, question_ids)
        _set_questions(db, homework, questions)
    homework.version += 1
    homework.content_release_id = store.release_id
    _rebuild_pending_task_snapshots(db, homework)
    db.commit()
    return get_homework(db, store, homework.id, subject_id)


def duplicate_homework(
    db: Session, store: ContentStore, homework_id: str, subject_id: str, created_by: Optional[str]
) -> dict[str, Any]:
    homework = db.get(ClassroomHomework, homework_id)
    if homework is None or homework.subject_id != subject_id:
        raise AppError(404, "HOMEWORK_NOT_FOUND", "课堂作业不存在")
    ids = [row["question_id"] for row in _question_rows(db, homework.id)]
    return create_homework(
        db,
        store,
        subject_id=subject_id,
        title=f"{homework.title}（副本）"[:200],
        note=homework.note or "",
        unit_id=homework.unit_id,
        topic_id=homework.topic_id,
        question_ids=ids,
        created_by=created_by,
    )


def delete_homework(db: Session, homework_id: str, subject_id: str) -> dict[str, Any]:
    homework = db.get(ClassroomHomework, homework_id)
    if homework is None or homework.subject_id != subject_id:
        raise AppError(404, "HOMEWORK_NOT_FOUND", "课堂作业不存在")
    used = db.scalar(
        select(func.count(StudyPlanItem.id)).where(StudyPlanItem.homework_id == homework.id)
    ) or 0
    used_tasks = db.scalar(
        select(func.count(StudyPlanTask.id)).where(
            StudyPlanTask.homework_id == homework.id
        )
    ) or 0
    if used or used_tasks:
        raise AppError(409, "HOMEWORK_IN_USE", "课堂作业已被学习计划引用，请先移除")
    db.execute(
        ClassroomHomeworkQuestion.__table__.delete().where(
            ClassroomHomeworkQuestion.homework_id == homework.id
        )
    )
    db.delete(homework)
    db.commit()
    return {"id": homework_id, "deleted": True}


def taxonomy(store: ContentStore) -> dict[str, Any]:
    units = store.list_groups()
    topics = store.list_all_topics()
    topics_by_unit: dict[str, list[dict[str, Any]]] = {}
    for topic in topics:
        topics_by_unit.setdefault(str(topic["unit_id"]), []).append(topic)
    return {
        "units": [
            {
                "unit_id": str(unit["unit_id"]),
                "title": unit.get("title") or f"Unit {unit['unit_id']}",
                "title_en": unit.get("title_en"),
                "topics": topics_by_unit.get(str(unit["unit_id"]), []),
            }
            for unit in units
        ],
        "topics": topics,
    }
