from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta
from typing import Any, Iterable, Optional

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.content.store import ContentStore
from app.core.errors import AppError
from app.core.time import shanghai_date, utcnow
from app.users.models import (
    ClassroomHomework,
    ClassroomHomeworkQuestion,
    PracticeSession,
    PracticeSessionQuestion,
    StudyPlan,
    StudyPlanAssignment,
    StudyPlanItem,
    StudyPlanTask,
    User,
)

MAX_PLAN_ITEMS = 500
MAX_HOMEWORK_QUESTIONS = 300
MAX_ASSIGNMENT_QUESTIONS = 20_000
MAX_ASSIGN_BATCH = 100
MAX_RANGE_DAYS = 366


# ---------------------------------------------------------------------------
# Scheduling
# ---------------------------------------------------------------------------
def distribute_item_indexes(n: int, d: int) -> list[int]:
    """Map N ordered items onto D inclusive days, evenly and order-preserving.

    The first item lands on day 0; the last item lands on day D-1 for N >= 2.
    For N > D day counts differ by at most one; extras are spread rather than
    clustered at the end.
    """
    if n <= 0 or d <= 0:
        raise ValueError("n and d must be positive")
    if n == 1:
        return [0]
    denom = 2 * (n - 1)
    return [(2 * i * (d - 1) + (n - 1)) // denom for i in range(n)]


def schedule_for_range(
    start_date: date, end_date: date, items: list[dict[str, Any]]
) -> dict[str, Any]:
    days = (end_date - start_date).days + 1
    indexes = distribute_item_indexes(len(items), days)
    by_day: dict[int, list[dict[str, Any]]] = {}
    for item, day_index in zip(items, indexes):
        by_day.setdefault(day_index, []).append(item)
    schedule = []
    for day_index in range(days):
        day_items = by_day.get(day_index, [])
        schedule.append(
            {
                "date": (start_date + timedelta(days=day_index)).isoformat(),
                "day_index": day_index,
                "item_count": len(day_items),
                "items": [
                    {
                        "title": item.get("title") or "",
                        "homework_id": item.get("homework_id"),
                    }
                    for item in day_items
                ],
            }
        )
    task_days = sum(1 for day in schedule if day["item_count"])
    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "total_days": days,
        "task_days": task_days,
        "rest_days": days - task_days,
        "total_items": len(items),
        "max_items_per_day": max((day["item_count"] for day in schedule), default=0),
        "days": schedule,
    }


def validate_range(start_date: date, end_date: date, today: Optional[date] = None) -> int:
    today = today or shanghai_date(utcnow())
    if end_date < start_date:
        raise AppError(400, "DATE_RANGE_INVALID", "结束日期不能早于开始日期")
    days = (end_date - start_date).days + 1
    if days > MAX_RANGE_DAYS:
        raise AppError(400, "DATE_RANGE_TOO_LONG", f"计划最长 {MAX_RANGE_DAYS} 天")
    if end_date < today:
        raise AppError(400, "DATE_RANGE_PAST", "结束日期不能早于今天")
    return days


# ---------------------------------------------------------------------------
# Reads / helpers
# ---------------------------------------------------------------------------
def _current_day_map(db: Session, assignment_ids: Iterable[str]) -> dict[str, int]:
    ids = list(dict.fromkeys(assignment_ids))
    if not ids:
        return {}
    rows = db.execute(
        select(
            StudyPlanTask.assignment_id,
            func.min(StudyPlanTask.day_index),
        )
        .where(
            StudyPlanTask.assignment_id.in_(ids),
            StudyPlanTask.status == "pending",
            StudyPlanTask.cancelled_at.is_(None),
        )
        .group_by(StudyPlanTask.assignment_id)
    ).all()
    return {row[0]: int(row[1]) for row in rows if row[1] is not None}


def _first_pending_tasks(
    db: Session, assignment_ids: Iterable[str]
) -> dict[str, StudyPlanTask]:
    ids = list(dict.fromkeys(assignment_ids))
    if not ids:
        return {}
    rows = db.scalars(
        select(StudyPlanTask)
        .where(
            StudyPlanTask.assignment_id.in_(ids),
            StudyPlanTask.status == "pending",
            StudyPlanTask.cancelled_at.is_(None),
        )
        .order_by(
            StudyPlanTask.assignment_id,
            StudyPlanTask.day_index,
            StudyPlanTask.sort_order,
        )
    ).all()
    first: dict[str, StudyPlanTask] = {}
    for row in rows:
        first.setdefault(row.assignment_id, row)
    return first


def task_state(
    task: StudyPlanTask,
    current_day: Optional[int],
    today: date,
) -> tuple[str, bool, bool]:
    """Return (status, locked, early) for a task."""
    if task.status == "completed":
        return "completed", False, False
    if task.status == "cancelled" or task.cancelled_at is not None:
        return "cancelled", True, False
    locked = current_day is not None and task.day_index > current_day
    if locked:
        return "locked", True, task.study_date > today
    if task.study_date < today:
        return "overdue", False, False
    return "pending", False, task.study_date > today


def _completed_late(task: StudyPlanTask) -> bool:
    if task.status != "completed" or task.completed_at is None:
        return False
    return shanghai_date(task.completed_at) > task.study_date


def _task_summary(
    tasks: list[StudyPlanTask], current_days: dict[str, int], today: date
) -> dict[str, int]:
    summary = {"total": 0, "completed": 0, "pending": 0, "overdue": 0, "locked": 0}
    for task in tasks:
        status, _locked, _early = task_state(
            task, current_days.get(task.assignment_id), today
        )
        if status == "cancelled":
            continue
        summary["total"] += 1
        if status == "completed":
            summary["completed"] += 1
        elif task.status == "pending" and task.study_date < today:
            # Past pending work is overdue even when it is also locked behind
            # an earlier missed day; the day should still stand out.
            summary["overdue"] += 1
        elif status == "locked":
            summary["locked"] += 1
        else:
            summary["pending"] += 1
    return summary


def _month_bounds(month: Optional[str]) -> tuple[str, date, date]:
    today = shanghai_date(utcnow())
    if month:
        try:
            year, month_no = (int(part) for part in month.split("-", 1))
            if not 1 <= month_no <= 12:
                raise ValueError
        except (ValueError, TypeError):
            raise AppError(400, "MONTH_INVALID", "月份格式应为 YYYY-MM")
    else:
        year, month_no = today.year, today.month
    first = date(year, month_no, 1)
    last = date(year, month_no, monthrange(year, month_no)[1])
    return f"{year:04d}-{month_no:02d}", first, last


def _plan_progress(assignment: StudyPlanAssignment) -> dict[str, Any]:
    return {
        "assignment_id": assignment.id,
        "plan_id": assignment.plan_id,
        "title": assignment.plan_title,
        "status": assignment.status,
        "start_date": assignment.start_date.isoformat(),
        "end_date": assignment.end_date.isoformat(),
        "total_items": assignment.total_items,
        "completed_items": assignment.completed_items,
        "total_questions": assignment.total_questions,
        "answered_questions": assignment.answered_questions,
    }


# ---------------------------------------------------------------------------
# Assignment creation
# ---------------------------------------------------------------------------
def plan_items_for_plan(db: Session, plan_id: str) -> list[dict[str, Any]]:
    rows = db.execute(
        select(
            StudyPlanItem.id,
            StudyPlanItem.position,
            StudyPlanItem.title,
            StudyPlanItem.homework_id,
            ClassroomHomework.title.label("homework_title"),
            ClassroomHomework.status.label("homework_status"),
            ClassroomHomework.question_count,
        )
        .join(ClassroomHomework, ClassroomHomework.id == StudyPlanItem.homework_id)
        .where(StudyPlanItem.plan_id == plan_id)
        .order_by(StudyPlanItem.position, StudyPlanItem.created_at)
    ).all()
    return [dict(row._mapping) for row in rows]


def assign_preview(
    db: Session, plan: StudyPlan, start_date: date, end_date: date
) -> dict[str, Any]:
    items = plan_items_for_plan(db, plan.id)
    if not items:
        raise AppError(409, "PLAN_EMPTY", "学习计划还没有学习项")
    if len(items) > MAX_PLAN_ITEMS:
        raise AppError(400, "PLAN_TOO_LARGE", "学习项过多")
    validate_range(start_date, end_date)
    total_questions = sum(int(item.get("question_count") or 0) for item in items)
    if total_questions > MAX_ASSIGNMENT_QUESTIONS:
        raise AppError(400, "ASSIGNMENT_TOO_LARGE", "计划题目总数超过上限")
    return schedule_for_range(start_date, end_date, items)


def _load_homeworks_for_items(
    db: Session, items: list[dict[str, Any]]
) -> dict[str, ClassroomHomework]:
    ids = list({str(item["homework_id"]) for item in items})
    rows = db.scalars(
        select(ClassroomHomework).where(ClassroomHomework.id.in_(ids))
    ).all()
    return {row.id: row for row in rows}


def _materialize_tasks(
    db: Session,
    assignment: StudyPlanAssignment,
    plan: StudyPlan,
    items: list[dict[str, Any]],
    homeworks: dict[str, ClassroomHomework],
    schedule: dict[str, Any],
) -> int:
    from collections import Counter

    day_indexes = distribute_item_indexes(len(items), schedule["total_days"])
    seen_per_day: Counter[int] = Counter()
    total_questions = 0
    for item, day_index in zip(items, day_indexes):
        homework = homeworks[str(item["homework_id"])]
        day_position = seen_per_day[day_index]
        seen_per_day[day_index] += 1
        total_questions += int(homework.question_count or 0)
        db.add(
            StudyPlanTask(
                assignment_id=assignment.id,
                user_id=assignment.user_id,
                plan_id=assignment.plan_id,
                plan_item_id=str(item["id"]),
                homework_id=homework.id,
                day_index=day_index,
                study_date=assignment.start_date + timedelta(days=day_index),
                sort_order=day_position,
                plan_title=plan.title,
                plan_version=plan.version,
                plan_color=plan.color,
                item_title=str(item.get("title") or homework.title),
                homework_version=homework.version,
                homework_title=homework.title,
                note=homework.note or "",
                unit_id=homework.unit_id,
                unit_title=homework.unit_title,
                topic_id=homework.topic_id,
                topic_title=homework.topic_title,
                question_count=int(homework.question_count or 0),
            )
        )
    return total_questions


def create_assignments(
    db: Session,
    *,
    plan: StudyPlan,
    users: list[User],
    start_date: date,
    end_date: date,
    assigned_by: Optional[str],
    note: Optional[str],
    content_release_id: Optional[str],
) -> dict[str, Any]:
    if plan.status != "active":
        raise AppError(409, "PLAN_ARCHIVED", "计划已归档，不能指派")
    if len(users) > MAX_ASSIGN_BATCH:
        raise AppError(400, "ASSIGN_BATCH_TOO_LARGE", f"一次最多指派 {MAX_ASSIGN_BATCH} 名学生")
    items = plan_items_for_plan(db, plan.id)
    if not items:
        raise AppError(409, "PLAN_EMPTY", "学习计划还没有学习项")
    if len(items) > MAX_PLAN_ITEMS:
        raise AppError(400, "PLAN_TOO_LARGE", "学习项过多")
    validate_range(start_date, end_date)
    homeworks = _load_homeworks_for_items(db, items)
    for item in items:
        homework = homeworks.get(str(item["homework_id"]))
        if homework is None or homework.status != "active":
            raise AppError(409, "HOMEWORK_UNAVAILABLE", "计划中包含不可用的课堂作业")
        if not homework.question_count:
            raise AppError(409, "HOMEWORK_EMPTY", "计划中包含没有题目的课堂作业")
    total_questions_per_student = sum(
        int(homeworks[str(item["homework_id"])].question_count or 0) for item in items
    )
    if total_questions_per_student > MAX_ASSIGNMENT_QUESTIONS:
        raise AppError(400, "ASSIGNMENT_TOO_LARGE", "计划题目总数超过上限")

    schedule = schedule_for_range(start_date, end_date, items)
    assigned: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    existing_rows = db.scalars(
        select(StudyPlanAssignment).where(
            StudyPlanAssignment.plan_id == plan.id,
            StudyPlanAssignment.user_id.in_([user.id for user in users]),
            StudyPlanAssignment.status == "active",
        )
    ).all()
    already = {row.user_id for row in existing_rows}

    for user in users:
        if user.id in already:
            skipped.append({"user_id": user.id, "reason": "already_assigned"})
            continue
        if user.merged_into_id:
            skipped.append({"user_id": user.id, "reason": "merged"})
            continue
        if user.status != "active":
            skipped.append({"user_id": user.id, "reason": "inactive"})
            continue
        assignment = StudyPlanAssignment(
            plan_id=plan.id,
            user_id=user.id,
            assigned_by=assigned_by,
            plan_title=plan.title,
            plan_version=plan.version,
            subject_id=plan.subject_id,
            start_date=start_date,
            end_date=end_date,
            status="active",
            active_slot="1",
            total_items=len(items),
            total_questions=total_questions_per_student,
            total_task_days=schedule["task_days"],
            content_release_id=content_release_id,
            note=note,
        )
        db.add(assignment)
        db.flush()
        _materialize_tasks(
            db,
            assignment,
            plan,
            items,
            homeworks,
            schedule,
        )
        assigned.append(
            {
                "assignment_id": assignment.id,
                "user_id": user.id,
                "nickname": user.nickname,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "total_items": len(items),
                "total_questions": total_questions_per_student,
            }
        )
    db.commit()
    return {"assigned": assigned, "skipped": skipped, "schedule": schedule}


# ---------------------------------------------------------------------------
# Student calendar / day detail
# ---------------------------------------------------------------------------
def calendar_month(
    db: Session, user: User, subject_id: str, month: Optional[str]
) -> dict[str, Any]:
    month_key, month_start, month_end = _month_bounds(month)
    today = shanghai_date(utcnow())
    assignments = db.scalars(
        select(StudyPlanAssignment)
        .where(
            StudyPlanAssignment.user_id == user.id,
            StudyPlanAssignment.subject_id == subject_id,
            StudyPlanAssignment.status.in_(("active", "completed")),
        )
        .order_by(StudyPlanAssignment.created_at)
    ).all()
    assignment_ids = [row.id for row in assignments]
    current_days = _current_day_map(db, assignment_ids)
    current_tasks = _first_pending_tasks(db, assignment_ids)

    tasks = db.scalars(
        select(StudyPlanTask)
        .where(
            StudyPlanTask.user_id == user.id,
            StudyPlanTask.plan_id.in_(
                select(StudyPlan.id).where(StudyPlan.subject_id == subject_id)
            ),
            StudyPlanTask.study_date >= month_start,
            StudyPlanTask.study_date <= month_end,
            StudyPlanTask.cancelled_at.is_(None),
        )
        .order_by(StudyPlanTask.study_date, StudyPlanTask.sort_order)
    ).all()

    by_date: dict[str, list[StudyPlanTask]] = {}
    for task in tasks:
        by_date.setdefault(task.study_date.isoformat(), []).append(task)

    days = []
    for date_key, day_tasks in sorted(by_date.items()):
        payload_tasks = []
        for task in day_tasks:
            status, locked, early = task_state(
                task, current_days.get(task.assignment_id), today
            )
            payload_tasks.append(
                {
                    "task_id": task.id,
                    "title": task.item_title,
                    "plan_title": task.plan_title,
                    "color": task.plan_color,
                    "unit_title": task.unit_title,
                    "topic_title": task.topic_title,
                    "question_count": task.question_count,
                    "answered_question_count": task.answered_question_count,
                    "status": status,
                    "locked": locked,
                    "early": early,
                    "overdue": task.status == "pending" and task.study_date < today,
                    "completed_late": _completed_late(task),
                }
            )
        days.append(
            {
                "date": date_key,
                "tasks": payload_tasks,
                "summary": _task_summary(day_tasks, current_days, today),
            }
        )

    plans = []
    color_by_assignment: dict[str, str] = {}
    for task in tasks:
        color_by_assignment.setdefault(task.assignment_id, task.plan_color)
    for assignment in assignments:
        payload = _plan_progress(assignment)
        task = current_tasks.get(assignment.id)
        if task is not None:
            color_by_assignment.setdefault(assignment.id, task.plan_color)
        payload["color"] = color_by_assignment.get(assignment.id, "primary")
        payload["current_task"] = (
            {
                "task_id": task.id,
                "title": task.item_title,
                "study_date": task.study_date.isoformat(),
                "day_index": task.day_index,
            }
            if task
            else None
        )
        plans.append(payload)

    ever = db.scalar(
        select(StudyPlanAssignment.id)
        .where(
            StudyPlanAssignment.user_id == user.id,
            StudyPlanAssignment.subject_id == subject_id,
        )
        .limit(1)
    )
    active_count = sum(1 for row in assignments if row.status == "active")
    overdue = db.execute(
        select(
            func.count(func.distinct(StudyPlanTask.study_date)),
            func.min(StudyPlanTask.study_date),
        ).where(
            StudyPlanTask.user_id == user.id,
            StudyPlanTask.plan_id.in_(
                select(StudyPlan.id).where(StudyPlan.subject_id == subject_id)
            ),
            StudyPlanTask.status == "pending",
            StudyPlanTask.cancelled_at.is_(None),
            StudyPlanTask.study_date < today,
        )
    ).one()
    return {
        "month": month_key,
        "today": today.isoformat(),
        "has_ever_plan": ever is not None,
        "has_active_plan": active_count > 0,
        "active_assignment_count": active_count,
        "plans": plans,
        "days": days,
        "overdue_days": int(overdue[0] or 0),
        "earliest_overdue_date": overdue[1].isoformat() if overdue[1] else None,
    }


def day_detail(db: Session, user: User, subject_id: str, day: date) -> dict[str, Any]:
    today = shanghai_date(utcnow())
    tasks = db.scalars(
        select(StudyPlanTask)
        .where(
            StudyPlanTask.user_id == user.id,
            StudyPlanTask.study_date == day,
            StudyPlanTask.cancelled_at.is_(None),
            StudyPlanTask.plan_id.in_(
                select(StudyPlan.id).where(StudyPlan.subject_id == subject_id)
            ),
        )
        .order_by(StudyPlanTask.sort_order)
    ).all()
    assignment_ids = list({task.assignment_id for task in tasks})
    assignments = {
        row.id: row
        for row in db.scalars(
            select(StudyPlanAssignment).where(
                StudyPlanAssignment.id.in_(assignment_ids)
            )
        ).all()
    }
    current_days = _current_day_map(db, assignment_ids)
    current_tasks = _first_pending_tasks(db, assignment_ids)
    session_ids = [task.practice_session_id for task in tasks if task.practice_session_id]
    sessions = {
        row.id: row
        for row in db.scalars(
            select(PracticeSession).where(PracticeSession.id.in_(session_ids))
        ).all()
    }

    grouped: dict[str, dict[str, Any]] = {}
    for task in tasks:
        assignment = assignments.get(task.assignment_id)
        if assignment is None:
            continue
        status, locked, early = task_state(
            task, current_days.get(task.assignment_id), today
        )
        blocking = current_tasks.get(task.assignment_id)
        locked_reason = None
        if locked and blocking is not None:
            locked_reason = (
                f"完成 {blocking.study_date.month} 月 {blocking.study_date.day} 日的任务后解锁"
            )
        session = sessions.get(task.practice_session_id or "")
        task_payload = {
            "task_id": task.id,
            "title": task.item_title,
            "homework_id": task.homework_id,
            "homework_title": task.homework_title,
            "note": task.note,
            "unit_id": task.unit_id,
            "unit_title": task.unit_title,
            "topic_id": task.topic_id,
            "topic_title": task.topic_title,
            "question_count": task.question_count,
            "unavailable_question_count": task.unavailable_question_count,
            "answered_question_count": task.answered_question_count,
            "correct_count": task.correct_count,
            "status": status,
            "locked": locked,
            "locked_reason": locked_reason,
            "early": early,
            "overdue": task.status == "pending" and task.study_date < today,
            "completed_late": _completed_late(task),
            "session_id": task.practice_session_id,
            "session_status": session.status if session else None,
        }
        group = grouped.setdefault(
            task.assignment_id,
            {
                "assignment_id": task.assignment_id,
                "plan_id": task.plan_id,
                "plan_title": assignment.plan_title,
                "color": task.plan_color,
                "status": assignment.status,
                "start_date": assignment.start_date.isoformat(),
                "end_date": assignment.end_date.isoformat(),
                "tasks": [],
                "summary": {"total": 0, "completed": 0, "pending": 0, "overdue": 0, "locked": 0},
            },
        )
        group["tasks"].append(task_payload)
    for group in grouped.values():
        group_tasks = [task for task in tasks if task.assignment_id == group["assignment_id"]]
        group["summary"] = _task_summary(group_tasks, current_days, today)
    return {
        "date": day.isoformat(),
        "today": today.isoformat(),
        "is_today": day == today,
        "assignments": list(grouped.values()),
    }


# ---------------------------------------------------------------------------
# Start / completion / cancellation
# ---------------------------------------------------------------------------
def _task_for_user(db: Session, user: User, task_id: str) -> StudyPlanTask:
    task = db.get(StudyPlanTask, task_id)
    if task is None or task.user_id != user.id:
        raise AppError(404, "TASK_NOT_FOUND", "任务不存在")
    return task


def _assignment_for_task(db: Session, task: StudyPlanTask) -> StudyPlanAssignment:
    assignment = db.get(StudyPlanAssignment, task.assignment_id)
    if assignment is None or assignment.user_id != task.user_id:
        raise AppError(404, "ASSIGNMENT_NOT_FOUND", "学习计划不存在")
    return assignment


def _assert_startable(
    db: Session, task: StudyPlanTask, assignment: StudyPlanAssignment
) -> None:
    if assignment.status != "active":
        raise AppError(409, "ASSIGNMENT_NOT_ACTIVE", "学习计划已结束")
    if task.cancelled_at is not None or task.status == "cancelled":
        raise AppError(409, "TASK_CANCELLED", "任务已取消")
    current_day = _current_day_map(db, [assignment.id]).get(assignment.id)
    if current_day is not None and task.day_index > current_day:
        raise AppError(403, "TASK_LOCKED", "请先完成前一项任务")


def _homework_question_ids(
    db: Session, store: ContentStore, homework_id: str
) -> tuple[list[str], int]:
    rows = db.execute(
        select(ClassroomHomeworkQuestion.question_id)
        .where(ClassroomHomeworkQuestion.homework_id == homework_id)
        .order_by(ClassroomHomeworkQuestion.sort_order)
    ).scalars().all()
    original = len(rows)
    existing = store.get_questions(list(rows), include_answers=False)
    ids = [
        qid
        for qid in rows
        if qid in existing
        and qid not in store.exclusions
        and (existing[qid].get("section") or "").upper() == "MCQ"
    ]
    return ids, original


def start_task(
    db: Session, store: ContentStore, user: User, task_id: str
) -> dict[str, Any]:
    task = _task_for_user(db, user, task_id)
    assignment = _assignment_for_task(db, task)
    if assignment.subject_id != store.subject_id:
        raise AppError(400, "SUBJECT_MISMATCH", "科目不匹配")
    if task.status == "completed":
        return {
            "task_id": task.id,
            "session_id": task.practice_session_id,
            "status": "completed",
            "created": False,
            "completed": True,
        }
    _assert_startable(db, task, assignment)

    if task.practice_session_id:
        existing = db.get(PracticeSession, task.practice_session_id)
        if (
            existing is not None
            and existing.user_id == user.id
            and existing.status == "in_progress"
            and existing.content_release_id == store.release_id
        ):
            return {
                "task_id": task.id,
                "session_id": existing.id,
                "status": existing.status,
                "created": False,
                "completed": False,
                "question_count": existing.total,
            }
        if existing is not None and existing.status == "in_progress":
            existing.status = "abandoned"
            existing.submitted_at = utcnow()

    ids, original = _homework_question_ids(db, store, task.homework_id)
    if not ids:
        raise AppError(409, "HOMEWORK_CONTENT_UNAVAILABLE", "题目已从题库移除，请联系老师")
    missing = max(0, original - len(ids))
    old_question_count = task.question_count
    task.unavailable_question_count = missing
    task.question_count = len(ids)
    assignment.total_questions = max(
        0, assignment.total_questions + len(ids) - old_question_count
    )

    session = PracticeSession(
        user_id=user.id,
        source="homework",
        group_id=task.homework_id,
        topic_id=None,
        status="in_progress",
        total=len(ids),
        content_release_id=store.release_id,
    )
    db.add(session)
    db.flush()
    for index, question_id in enumerate(ids, start=1):
        db.add(
            PracticeSessionQuestion(
                session_id=session.id,
                question_id=question_id,
                sort_order=index,
            )
        )
    task.practice_session_id = session.id
    task.answered_question_count = 0
    task.correct_count = 0
    db.commit()
    return {
        "task_id": task.id,
        "session_id": session.id,
        "status": session.status,
        "created": True,
        "completed": False,
        "question_count": len(ids),
    }


def sync_task_progress(db: Session, session: PracticeSession) -> Optional[dict[str, Any]]:
    if session.source != "homework":
        return None
    task = db.scalar(
        select(StudyPlanTask).where(StudyPlanTask.practice_session_id == session.id)
    )
    if task is None:
        return None
    if task.cancelled_at is not None or task.status == "cancelled":
        return None

    # The app session uses autoflush=False; make the just-saved answers visible
    # to the aggregate query below.
    db.flush()
    total, answered, correct = db.execute(
        select(
            func.count(PracticeSessionQuestion.question_id),
            func.sum(
                case((PracticeSessionQuestion.answered_at.is_not(None), 1), else_=0)
            ),
            func.sum(
                case((PracticeSessionQuestion.is_correct.is_(True), 1), else_=0)
            ),
        ).where(PracticeSessionQuestion.session_id == session.id)
    ).one()
    total = int(total or 0)
    answered = int(answered or 0)
    correct = int(correct or 0)
    task.answered_question_count = answered
    task.correct_count = correct
    if (
        task.status == "pending"
        and total > 0
        and answered == total
        and session.status == "submitted"
    ):
        task.status = "completed"
        task.completed_at = utcnow()

    db.flush()
    assignment = db.get(StudyPlanAssignment, task.assignment_id)
    if assignment is None:
        return None
    rows = db.execute(
        select(
            func.count(StudyPlanTask.id),
            func.sum(case((StudyPlanTask.status == "completed", 1), else_=0)),
            func.sum(StudyPlanTask.answered_question_count),
            func.sum(StudyPlanTask.question_count),
        ).where(
            StudyPlanTask.assignment_id == assignment.id,
            StudyPlanTask.cancelled_at.is_(None),
        )
    ).one()
    assignment.completed_items = int(rows[1] or 0)
    assignment.answered_questions = int(rows[2] or 0)
    assignment.total_questions = int(rows[3] or 0)
    if (
        assignment.status == "active"
        and assignment.total_items > 0
        and assignment.completed_items >= assignment.total_items
    ):
        assignment.status = "completed"
        assignment.active_slot = None
        assignment.completed_at = utcnow()

    next_task = db.scalar(
        select(StudyPlanTask)
        .where(
            StudyPlanTask.assignment_id == assignment.id,
            StudyPlanTask.status == "pending",
            StudyPlanTask.cancelled_at.is_(None),
        )
        .order_by(StudyPlanTask.day_index, StudyPlanTask.sort_order)
        .limit(1)
    )
    day_tasks = db.scalars(
        select(StudyPlanTask).where(
            StudyPlanTask.assignment_id == assignment.id,
            StudyPlanTask.study_date == task.study_date,
            StudyPlanTask.cancelled_at.is_(None),
        )
    ).all()
    day_completed = bool(day_tasks) and all(
        row.status == "completed" for row in day_tasks
    )
    return {
        "task": {
            "id": task.id,
            "completed": task.status == "completed",
            "answered": answered,
            "total": total,
        },
        "day": {"date": task.study_date.isoformat(), "completed": day_completed},
        "assignment": {
            "completed": assignment.status == "completed",
            "completed_items": assignment.completed_items,
            "total_items": assignment.total_items,
        },
        "next_task": (
            {
                "id": next_task.id,
                "title": next_task.item_title,
                "study_date": next_task.study_date.isoformat(),
                "sort_order": next_task.sort_order,
            }
            if next_task
            else None
        ),
    }


def complete_task(
    db: Session, user: User, task_id: str
) -> dict[str, Any]:
    task = _task_for_user(db, user, task_id)
    assignment = _assignment_for_task(db, task)
    if task.status == "completed":
        return {
            "task": {"id": task.id, "completed": True},
            "day": {"date": task.study_date.isoformat(), "completed": True},
            "assignment": {
                "completed": assignment.status == "completed",
                "completed_items": assignment.completed_items,
                "total_items": assignment.total_items,
            },
            "next_task": None,
        }
    _assert_startable(db, task, assignment)
    if not task.practice_session_id:
        raise AppError(409, "TASK_NOT_STARTED", "请先开始作业")
    session = db.get(PracticeSession, task.practice_session_id)
    if session is None or session.status != "submitted":
        raise AppError(409, "HOMEWORK_INCOMPLETE", "请先完成全部题目")
    result = sync_task_progress(db, session)
    db.commit()
    return result or {}


def cancel_assignment(
    db: Session,
    assignment: StudyPlanAssignment,
    admin_id: Optional[str],
    reason: Optional[str] = None,
) -> dict[str, Any]:
    if assignment.status == "cancelled":
        return {"id": assignment.id, "status": "cancelled", "already": True}
    now = utcnow()
    assignment.status = "cancelled"
    assignment.active_slot = None
    assignment.cancelled_at = now
    assignment.cancelled_by = admin_id
    if reason:
        assignment.note = (
            f"{assignment.note}\n[取消] {reason}" if assignment.note else f"[取消] {reason}"
        )
    tasks = db.scalars(
        select(StudyPlanTask).where(
            StudyPlanTask.assignment_id == assignment.id,
            StudyPlanTask.cancelled_at.is_(None),
        )
    ).all()
    for task in tasks:
        task.cancelled_at = now
        if task.status == "pending":
            task.status = "cancelled"
    db.commit()
    return {"id": assignment.id, "status": "cancelled", "already": False}


# ---------------------------------------------------------------------------
# Admin plan CRUD / progress
# ---------------------------------------------------------------------------
def _plan_payload(plan: StudyPlan) -> dict[str, Any]:
    return {
        "id": plan.id,
        "subject_id": plan.subject_id,
        "title": plan.title,
        "note": plan.note or "",
        "category": plan.category,
        "color": plan.color,
        "status": plan.status,
        "version": plan.version,
        "item_count": plan.item_count,
        "created_at": plan.created_at,
        "updated_at": plan.updated_at,
    }


def list_plans(
    db: Session,
    *,
    subject_id: str,
    q: Optional[str] = None,
    status: str = "active",
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    clauses = [StudyPlan.subject_id == subject_id]
    if status and status != "all":
        clauses.append(StudyPlan.status == status)
    if q:
        needle = f"%{q.strip()}%"
        clauses.append(
            StudyPlan.title.ilike(needle) | StudyPlan.note.ilike(needle)
        )
    total = db.scalar(select(func.count(StudyPlan.id)).where(*clauses)) or 0
    rows = db.scalars(
        select(StudyPlan)
        .where(*clauses)
        .order_by(StudyPlan.updated_at.desc(), StudyPlan.created_at.desc())
        .limit(max(1, min(limit, 200)))
        .offset(max(0, offset))
    ).all()
    ids = [row.id for row in rows]
    active_counts: dict[str, int] = {}
    if ids:
        active_counts = {
            row[0]: int(row[1])
            for row in db.execute(
                select(
                    StudyPlanAssignment.plan_id,
                    func.count(StudyPlanAssignment.id),
                )
                .where(
                    StudyPlanAssignment.plan_id.in_(ids),
                    StudyPlanAssignment.status == "active",
                )
                .group_by(StudyPlanAssignment.plan_id)
            ).all()
        }
    plans = []
    for row in rows:
        payload = _plan_payload(row)
        payload["active_assignment_count"] = active_counts.get(row.id, 0)
        plans.append(payload)
    return {"plans": plans, "total": int(total), "limit": limit, "offset": offset}


def get_plan(db: Session, plan_id: str, subject_id: str) -> dict[str, Any]:
    plan = db.get(StudyPlan, plan_id)
    if plan is None or plan.subject_id != subject_id:
        raise AppError(404, "PLAN_NOT_FOUND", "学习计划不存在")
    items = plan_items_for_plan(db, plan.id)
    payload = _plan_payload(plan)
    payload["items"] = [
        {
            "id": item["id"],
            "position": item["position"],
            "title": item["title"],
            "homework_id": item["homework_id"],
            "homework_title": item["homework_title"],
            "homework_status": item["homework_status"],
            "question_count": item["question_count"],
        }
        for item in items
    ]
    payload["active_assignment_count"] = db.scalar(
        select(func.count(StudyPlanAssignment.id)).where(
            StudyPlanAssignment.plan_id == plan.id,
            StudyPlanAssignment.status == "active",
        )
    ) or 0
    return payload


def create_plan(
    db: Session,
    *,
    subject_id: str,
    title: str,
    note: Optional[str],
    category: Optional[str],
    color: str,
    created_by: Optional[str],
) -> dict[str, Any]:
    title = (title or "").strip()
    if not title or len(title) > 200:
        raise AppError(400, "TITLE_INVALID", "标题长度需在 1–200 字之间")
    plan = StudyPlan(
        subject_id=subject_id,
        title=title,
        note=note or "",
        category=category,
        color=(color or "primary")[:16],
        status="active",
        version=1,
        item_count=0,
        created_by=created_by,
    )
    db.add(plan)
    db.commit()
    return get_plan(db, plan.id, subject_id)


def update_plan(
    db: Session,
    plan_id: str,
    *,
    subject_id: str,
    title: Optional[str] = None,
    note: Optional[str] = None,
    category: Optional[str] = None,
    color: Optional[str] = None,
    status: Optional[str] = None,
) -> dict[str, Any]:
    plan = db.get(StudyPlan, plan_id)
    if plan is None or plan.subject_id != subject_id:
        raise AppError(404, "PLAN_NOT_FOUND", "学习计划不存在")
    if title is not None:
        title = title.strip()
        if not title or len(title) > 200:
            raise AppError(400, "TITLE_INVALID", "标题长度需在 1–200 字之间")
        plan.title = title
    if note is not None:
        plan.note = note
    if category is not None:
        plan.category = category
    if color is not None:
        plan.color = color[:16]
    if status is not None:
        if status not in ("active", "archived"):
            raise AppError(400, "STATUS_INVALID", "计划状态不合法")
        plan.status = status
    plan.version += 1
    tasks = db.scalars(
        select(StudyPlanTask).where(StudyPlanTask.plan_id == plan.id)
    ).all()
    for task in tasks:
        task.plan_title = plan.title
        task.plan_color = plan.color
        task.plan_version = plan.version
    assignments = db.scalars(
        select(StudyPlanAssignment).where(StudyPlanAssignment.plan_id == plan.id)
    ).all()
    for assignment in assignments:
        assignment.plan_title = plan.title
        assignment.plan_version = plan.version
    db.commit()
    return get_plan(db, plan.id, subject_id)


def replace_plan_items(
    db: Session,
    plan_id: str,
    *,
    subject_id: str,
    items: list[dict[str, Any]],
) -> dict[str, Any]:
    plan = db.get(StudyPlan, plan_id)
    if plan is None or plan.subject_id != subject_id:
        raise AppError(404, "PLAN_NOT_FOUND", "学习计划不存在")
    if len(items) > MAX_PLAN_ITEMS:
        raise AppError(400, "PLAN_TOO_LARGE", "学习项过多")
    seen: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for raw in items:
        homework_id = str(raw.get("homework_id") or "").strip()
        if not homework_id:
            raise AppError(400, "HOMEWORK_REQUIRED", "学习项缺少课堂作业")
        if homework_id in seen:
            raise AppError(400, "HOMEWORK_DUPLICATE", "同一课堂作业不能重复加入计划")
        seen.add(homework_id)
        homework = db.get(ClassroomHomework, homework_id)
        if homework is None or homework.subject_id != subject_id:
            raise AppError(404, "HOMEWORK_NOT_FOUND", "课堂作业不存在")
        if homework.status != "active":
            raise AppError(409, "HOMEWORK_ARCHIVED", "课堂作业已归档")
        if not homework.question_count:
            raise AppError(409, "HOMEWORK_EMPTY", "课堂作业没有题目")
        title = str(raw.get("title") or homework.title).strip() or homework.title
        normalized.append(
            {
                "homework_id": homework.id,
                "title": title[:200],
            }
        )
    old_titles = {
        row.homework_id: row.title
        for row in db.scalars(
            select(StudyPlanItem).where(StudyPlanItem.plan_id == plan.id)
        ).all()
    }
    db.execute(
        StudyPlanItem.__table__.delete().where(StudyPlanItem.plan_id == plan.id)
    )
    for position, item in enumerate(normalized):
        db.add(
            StudyPlanItem(
                plan_id=plan.id,
                homework_id=item["homework_id"],
                position=position,
                title=item["title"],
            )
        )
        if old_titles.get(item["homework_id"]) != item["title"]:
            tasks = db.scalars(
                select(StudyPlanTask).where(
                    StudyPlanTask.plan_id == plan.id,
                    StudyPlanTask.homework_id == item["homework_id"],
                    StudyPlanTask.status == "pending",
                    StudyPlanTask.cancelled_at.is_(None),
                )
            ).all()
            for task in tasks:
                task.item_title = item["title"]
    plan.item_count = len(normalized)
    plan.version += 1
    db.commit()
    return get_plan(db, plan.id, subject_id)


def delete_plan(db: Session, plan_id: str, subject_id: str) -> dict[str, Any]:
    plan = db.get(StudyPlan, plan_id)
    if plan is None or plan.subject_id != subject_id:
        raise AppError(404, "PLAN_NOT_FOUND", "学习计划不存在")
    used = db.scalar(
        select(func.count(StudyPlanAssignment.id)).where(
            StudyPlanAssignment.plan_id == plan.id
        )
    ) or 0
    if used:
        raise AppError(409, "PLAN_IN_USE", "计划已有指派记录，不能删除，请改为归档")
    db.execute(StudyPlanItem.__table__.delete().where(StudyPlanItem.plan_id == plan.id))
    db.delete(plan)
    db.commit()
    return {"id": plan_id, "deleted": True}


def _assignment_student_payload(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "nickname": user.nickname,
        "email_masked": _mask_email(user.email),
        "phone_masked": _mask_phone(user.phone),
    }


def _mask_email(value: Optional[str]) -> Optional[str]:
    if not value or "@" not in value:
        return None
    local, domain = value.split("@", 1)
    return f"{local[:1]}***@{domain}"


def _mask_phone(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    return f"{value[:3]}****{value[-4:]}" if len(value) >= 7 else "***"


def list_assignments(
    db: Session,
    *,
    plan_id: Optional[str] = None,
    user_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    clauses = []
    if plan_id:
        clauses.append(StudyPlanAssignment.plan_id == plan_id)
    if user_id:
        clauses.append(StudyPlanAssignment.user_id == user_id)
    if status and status != "all":
        clauses.append(StudyPlanAssignment.status == status)
    total = db.scalar(select(func.count(StudyPlanAssignment.id)).where(*clauses)) or 0
    rows = db.scalars(
        select(StudyPlanAssignment)
        .where(*clauses)
        .order_by(StudyPlanAssignment.created_at.desc())
        .limit(max(1, min(limit, 200)))
        .offset(max(0, offset))
    ).all()
    ids = [row.id for row in rows]
    users = {
        user.id: user
        for user in db.scalars(
            select(User).where(
                User.id.in_([row.user_id for row in rows])
            )
        ).all()
    } if rows else {}
    current_tasks = _first_pending_tasks(db, ids)
    overdue_days: dict[str, int] = {}
    if ids:
        today = shanghai_date(utcnow())
        overdue_days = {
            row[0]: int(row[1])
            for row in db.execute(
                select(
                    StudyPlanTask.assignment_id,
                    func.count(func.distinct(StudyPlanTask.study_date)),
                )
                .where(
                    StudyPlanTask.assignment_id.in_(ids),
                    StudyPlanTask.status == "pending",
                    StudyPlanTask.cancelled_at.is_(None),
                    StudyPlanTask.study_date < today,
                )
                .group_by(StudyPlanTask.assignment_id)
            ).all()
        }
    items = []
    for row in rows:
        user = users.get(row.user_id)
        task = current_tasks.get(row.id)
        item = {
            "id": row.id,
            "plan_id": row.plan_id,
            "plan_title": row.plan_title,
            "subject_id": row.subject_id,
            "student": _assignment_student_payload(user) if user else None,
            "start_date": row.start_date.isoformat(),
            "end_date": row.end_date.isoformat(),
            "status": row.status,
            "total_items": row.total_items,
            "completed_items": row.completed_items,
            "total_questions": row.total_questions,
            "answered_questions": row.answered_questions,
            "overdue_task_days": overdue_days.get(row.id, 0),
            "current_task": (
                {
                    "id": task.id,
                    "title": task.item_title,
                    "study_date": task.study_date.isoformat(),
                }
                if task
                else None
            ),
            "created_at": row.created_at,
        }
        items.append(item)
    return {"assignments": items, "total": int(total), "limit": limit, "offset": offset}


def assignment_detail(db: Session, assignment_id: str) -> dict[str, Any]:
    assignment = db.get(StudyPlanAssignment, assignment_id)
    if assignment is None:
        raise AppError(404, "ASSIGNMENT_NOT_FOUND", "学习计划指派不存在")
    user = db.get(User, assignment.user_id)
    tasks = db.scalars(
        select(StudyPlanTask)
        .where(StudyPlanTask.assignment_id == assignment.id)
        .order_by(StudyPlanTask.day_index, StudyPlanTask.sort_order)
    ).all()
    today = shanghai_date(utcnow())
    return {
        "id": assignment.id,
        "plan_id": assignment.plan_id,
        "plan_title": assignment.plan_title,
        "student": _assignment_student_payload(user) if user else None,
        "start_date": assignment.start_date.isoformat(),
        "end_date": assignment.end_date.isoformat(),
        "status": assignment.status,
        "total_items": assignment.total_items,
        "completed_items": assignment.completed_items,
        "total_questions": assignment.total_questions,
        "answered_questions": assignment.answered_questions,
        "tasks": [
            {
                "id": task.id,
                "title": task.item_title,
                "homework_title": task.homework_title,
                "study_date": task.study_date.isoformat(),
                "day_index": task.day_index,
                "status": task.status,
                "question_count": task.question_count,
                "answered_question_count": task.answered_question_count,
                "correct_count": task.correct_count,
                "overdue": task.status == "pending" and task.study_date < today,
            }
            for task in tasks
        ],
    }
