from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.content.store import ContentStore
from app.core.errors import AppError
from app.core.security import mask_email, mask_phone
from app.core.time import as_utc, utcnow
from app.users.models import (
    AdminUser,
    PracticeSession,
    PracticeSessionQuestion,
    QaReply,
    QaThread,
    StudyPlan,
    StudyPlanTask,
    User,
)

MAX_QA_CONTENT = 5000


def _clean_content(value: str) -> str:
    content = (value or "").strip()
    if not content:
        raise AppError(400, "QA_CONTENT_REQUIRED", "请填写内容")
    if len(content) > MAX_QA_CONTENT:
        raise AppError(400, "QA_CONTENT_TOO_LONG", "内容最多 5000 字")
    return content


def _session_context(
    db: Session, user: User, session_id: str, question_id: str
) -> tuple[PracticeSession, StudyPlanTask, StudyPlan]:
    session = db.get(PracticeSession, session_id)
    if session is None or session.user_id != user.id:
        raise AppError(404, "SESSION_NOT_FOUND", "练习不存在")
    if session.source != "homework":
        raise AppError(403, "QA_NOT_AVAILABLE", "只有学习日历里的作业支持答疑")
    row = db.get(PracticeSessionQuestion, (session.id, question_id))
    if row is None:
        raise AppError(404, "QUESTION_NOT_IN_SESSION", "题目不在本次练习中")
    task = db.scalar(
        select(StudyPlanTask).where(StudyPlanTask.practice_session_id == session.id)
    )
    if task is None:
        raise AppError(403, "QA_NOT_AVAILABLE", "只有学习日历里的作业支持答疑")
    plan = db.get(StudyPlan, task.plan_id)
    if plan is None:
        raise AppError(404, "PLAN_NOT_FOUND", "学习计划不存在")
    return session, task, plan


def _student_name(user: Optional[User]) -> str:
    if user is None:
        return "匿名同学"
    return user.nickname or "匿名同学"


def _after(left, right) -> bool:
    return left is not None and right is not None and as_utc(left) > as_utc(right)


def _iso(value) -> Optional[str]:
    """Serialize DB datetimes with an explicit UTC offset.

    SQLite drops tzinfo on round-trip; without the offset the browser would
    parse the UTC clock time as local time and show every message 8 hours off
    for China-based students.
    """
    return as_utc(value).isoformat() if value is not None else None


def _reply_payload(reply: QaReply, students: dict[str, User]) -> dict[str, Any]:
    is_teacher = reply.author_type == "teacher"
    student = students.get(reply.student_id or "")
    return {
        "id": reply.id,
        "author_type": reply.author_type,
        "is_teacher": is_teacher,
        "author_name": "老师" if is_teacher else _student_name(student),
        "content": reply.content,
        "created_at": _iso(reply.created_at),
    }


def _load_replies(
    db: Session, thread_ids: list[str]
) -> tuple[dict[str, list[QaReply]], dict[str, User]]:
    if not thread_ids:
        return {}, {}
    replies = db.scalars(
        select(QaReply)
        .where(QaReply.thread_id.in_(thread_ids))
        .order_by(QaReply.thread_id, QaReply.created_at)
    ).all()
    student_ids = {reply.student_id for reply in replies if reply.student_id}
    students = {
        user.id: user
        for user in db.scalars(select(User).where(User.id.in_(student_ids))).all()
    } if student_ids else {}
    grouped: dict[str, list[QaReply]] = {}
    for reply in replies:
        grouped.setdefault(reply.thread_id, []).append(reply)
    return grouped, students


def _thread_payload(
    thread: QaThread,
    replies: list[QaReply],
    students: dict[str, User],
    viewer: User,
) -> dict[str, Any]:
    is_mine = thread.student_id == viewer.id
    teacher_replied = any(reply.author_type == "teacher" for reply in replies)
    last_teacher = max(
        (reply.created_at for reply in replies if reply.author_type == "teacher"),
        default=None,
    )
    unread = bool(
        is_mine
        and last_teacher is not None
        and (thread.student_last_read_at is None or _after(last_teacher, thread.student_last_read_at))
    )
    student = students.get(thread.student_id)
    return {
        "id": thread.id,
        "question_id": thread.question_id,
        "content": thread.content,
        "created_at": _iso(thread.created_at),
        "is_mine": is_mine,
        "student": {"nickname": _student_name(student)},
        "teacher_replied": teacher_replied,
        "unread": unread,
        "replies": [_reply_payload(reply, students) for reply in replies],
    }


def question_threads(
    db: Session, user: User, session_id: str, question_id: str
) -> dict[str, Any]:
    _session, task, plan = _session_context(db, user, session_id, question_id)
    threads = db.scalars(
        select(QaThread)
        .where(
            QaThread.subject_id == plan.subject_id,
            QaThread.question_id == question_id,
        )
        .order_by(QaThread.created_at)
    ).all()
    thread_ids = [thread.id for thread in threads]
    grouped, students = _load_replies(db, thread_ids)
    # Load thread authors too (replies may not include every author).
    author_ids = {thread.student_id for thread in threads}
    if author_ids:
        for author in db.scalars(select(User).where(User.id.in_(author_ids))).all():
            students[author.id] = author
    payload = [
        _thread_payload(thread, grouped.get(thread.id, []), students, user)
        for thread in threads
    ]
    return {
        "task_id": task.id,
        "question_id": question_id,
        "threads": payload,
        "unread": any(item["unread"] for item in payload),
    }


def create_question(
    db: Session,
    store: ContentStore,
    user: User,
    *,
    session_id: str,
    question_id: str,
    content: str,
) -> dict[str, Any]:
    content = _clean_content(content)
    _session, task, plan = _session_context(db, user, session_id, question_id)
    question = store.get_questions([question_id], include_answers=False).get(question_id)
    now = utcnow()
    thread = QaThread(
        subject_id=plan.subject_id,
        question_id=question_id,
        homework_id=task.homework_id,
        plan_title=task.plan_title,
        task_title=task.item_title,
        homework_title=task.homework_title,
        question_stem=(question or {}).get("stem") or "",
        student_id=user.id,
        content=content,
        status="open",
        created_at=now,
        updated_at=now,
        last_reply_at=now,
        last_student_message_at=now,
        student_last_read_at=now,
    )
    db.add(thread)
    db.commit()
    db.refresh(thread)
    return _thread_payload(thread, [], {user.id: user}, user)


def mark_question_read(
    db: Session, user: User, session_id: str, question_id: str
) -> dict[str, Any]:
    _session, _task, plan = _session_context(db, user, session_id, question_id)
    threads = db.scalars(
        select(QaThread).where(
            QaThread.subject_id == plan.subject_id,
            QaThread.question_id == question_id,
            QaThread.student_id == user.id,
        )
    ).all()
    now = utcnow()
    for thread in threads:
        thread.student_last_read_at = now
    db.commit()
    return {"ok": True, "marked": len(threads)}


def student_reply(
    db: Session, user: User, thread_id: str, content: str
) -> dict[str, Any]:
    content = _clean_content(content)
    thread = db.get(QaThread, thread_id)
    if thread is None or thread.student_id != user.id:
        raise AppError(404, "QA_THREAD_NOT_FOUND", "提问不存在")
    now = utcnow()
    reply = QaReply(
        thread_id=thread.id,
        author_type="student",
        student_id=user.id,
        content=content,
        created_at=now,
    )
    db.add(reply)
    thread.last_student_message_at = now
    thread.last_reply_at = now
    thread.updated_at = now
    thread.student_last_read_at = now
    db.commit()
    db.refresh(reply)
    return _reply_payload(reply, {user.id: user})


def my_threads(
    db: Session, user: User, limit: int = 50, offset: int = 0
) -> dict[str, Any]:
    total = db.scalar(
        select(func.count(QaThread.id)).where(QaThread.student_id == user.id)
    ) or 0
    threads = db.scalars(
        select(QaThread)
        .where(QaThread.student_id == user.id)
        .order_by(QaThread.last_reply_at.desc())
        .limit(max(1, min(limit, 100)))
        .offset(max(0, offset))
    ).all()
    thread_ids = [thread.id for thread in threads]
    replies, students = _load_replies(db, thread_ids)
    students[user.id] = user
    items = []
    for thread in threads:
        thread_replies = replies.get(thread.id, [])
        last = thread_replies[-1] if thread_replies else None
        last_teacher = max(
            (reply.created_at for reply in thread_replies if reply.author_type == "teacher"),
            default=None,
        )
        unread = bool(
            last_teacher is not None
            and (
                thread.student_last_read_at is None
                or _after(last_teacher, thread.student_last_read_at)
            )
        )
        items.append(
            {
                "id": thread.id,
                "question_id": thread.question_id,
                "question_stem": thread.question_stem or "",
                "content": thread.content,
                "plan_title": thread.plan_title,
                "task_title": thread.task_title,
                "homework_title": thread.homework_title,
                "created_at": _iso(thread.created_at),
                "last_reply_at": _iso(thread.last_reply_at),
                "last_message": (last.content if last else thread.content),
                "reply_count": len(thread_replies),
                "teacher_replied": last_teacher is not None,
                "unread": unread,
            }
        )
    return {"threads": items, "total": int(total), "limit": limit, "offset": offset}


def thread_detail_student(db: Session, user: User, thread_id: str) -> dict[str, Any]:
    thread = db.get(QaThread, thread_id)
    if thread is None or thread.student_id != user.id:
        raise AppError(404, "QA_THREAD_NOT_FOUND", "提问不存在")
    replies, students = _load_replies(db, [thread.id])
    students[user.id] = user
    now = utcnow()
    thread.student_last_read_at = now
    db.commit()
    payload = _thread_payload(thread, replies.get(thread.id, []), students, user)
    payload.update(
        {
            "question_stem": thread.question_stem or "",
            "plan_title": thread.plan_title,
            "task_title": thread.task_title,
            "homework_title": thread.homework_title,
            "last_reply_at": _iso(thread.last_reply_at),
        }
    )
    return payload


def thread_question(
    db: Session, store: ContentStore, user: User, thread_id: str
) -> dict[str, Any]:
    """Read-only question payload for a student's own Q&A thread.

    Deliberately uses ``include_answers=False`` so opening the preview cannot
    reveal the correct option or explanation.
    """
    thread = db.get(QaThread, thread_id)
    if thread is None or thread.student_id != user.id:
        raise AppError(404, "QA_THREAD_NOT_FOUND", "提问不存在")
    question = store.get_questions(
        [thread.question_id], include_answers=False
    ).get(thread.question_id)
    if question is None:
        raise AppError(404, "QUESTION_NOT_FOUND", "题目已从题库移除")
    return question


def student_unread_count(db: Session, user: User) -> int:
    return int(
        db.scalar(
            select(func.count(QaThread.id)).where(
                QaThread.student_id == user.id,
                QaThread.last_teacher_message_at.is_not(None),
                or_(
                    QaThread.student_last_read_at.is_(None),
                    QaThread.last_teacher_message_at > QaThread.student_last_read_at,
                ),
            )
        )
        or 0
    )


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------
def _admin_thread_payload(
    thread: QaThread,
    replies: list[QaReply],
    students: dict[str, User],
) -> dict[str, Any]:
    student = students.get(thread.student_id)
    last = replies[-1] if replies else None
    return {
        "id": thread.id,
        "subject_id": thread.subject_id,
        "question_id": thread.question_id,
        "question_stem": thread.question_stem or "",
        "content": thread.content,
        "plan_title": thread.plan_title,
        "task_title": thread.task_title,
        "homework_title": thread.homework_title,
        "created_at": _iso(thread.created_at),
        "last_reply_at": _iso(thread.last_reply_at),
        "last_message": (last.content if last else thread.content),
        "reply_count": len(replies),
        "teacher_replied": any(reply.author_type == "teacher" for reply in replies),
        "unread": thread.admin_last_read_at is None
        or _after(thread.last_student_message_at, thread.admin_last_read_at),
        "student": {
            "id": thread.student_id,
            "nickname": student.nickname if student else None,
            "email_masked": mask_email(student.email) if student else None,
            "phone_masked": mask_phone(student.phone) if student else None,
        },
    }


def admin_threads(
    db: Session,
    *,
    subject_id: Optional[str] = None,
    unread_only: bool = False,
    q: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    clauses = []
    if subject_id:
        clauses.append(QaThread.subject_id == subject_id)
    if unread_only:
        clauses.append(
            or_(
                QaThread.admin_last_read_at.is_(None),
                QaThread.last_student_message_at > QaThread.admin_last_read_at,
            )
        )
    join_user = q is not None
    if q:
        needle = f"%{q.strip()}%"
        clauses.append(
            or_(
                QaThread.content.ilike(needle),
                QaThread.question_stem.ilike(needle),
                User.nickname.ilike(needle),
                User.email.ilike(needle),
            )
        )
    stmt = select(QaThread)
    count_stmt = select(func.count(QaThread.id))
    if join_user:
        stmt = stmt.join(User, User.id == QaThread.student_id)
        count_stmt = count_stmt.join(User, User.id == QaThread.student_id)
    if clauses:
        stmt = stmt.where(*clauses)
        count_stmt = count_stmt.where(*clauses)
    total = db.scalar(count_stmt) or 0
    threads = db.scalars(
        stmt.order_by(QaThread.last_reply_at.desc())
        .limit(max(1, min(limit, 100)))
        .offset(max(0, offset))
    ).all()
    thread_ids = [thread.id for thread in threads]
    replies, students = _load_replies(db, thread_ids)
    author_ids = {thread.student_id for thread in threads}
    if author_ids:
        for author in db.scalars(select(User).where(User.id.in_(author_ids))).all():
            students[author.id] = author
    return {
        "threads": [
            _admin_thread_payload(thread, replies.get(thread.id, []), students)
            for thread in threads
        ],
        "total": int(total),
        "limit": limit,
        "offset": offset,
    }


def admin_thread_detail(db: Session, thread_id: str) -> dict[str, Any]:
    thread = db.get(QaThread, thread_id)
    if thread is None:
        raise AppError(404, "QA_THREAD_NOT_FOUND", "提问不存在")
    replies, students = _load_replies(db, [thread.id])
    author = db.get(User, thread.student_id)
    if author is not None:
        students[author.id] = author
    now = utcnow()
    thread.admin_last_read_at = now
    db.commit()
    payload = _admin_thread_payload(thread, replies.get(thread.id, []), students)
    payload["replies"] = [
        _reply_payload(reply, students) for reply in replies.get(thread.id, [])
    ]
    return payload


def admin_reply(
    db: Session, admin: AdminUser, thread_id: str, content: str
) -> dict[str, Any]:
    content = _clean_content(content)
    thread = db.get(QaThread, thread_id)
    if thread is None:
        raise AppError(404, "QA_THREAD_NOT_FOUND", "提问不存在")
    now = utcnow()
    reply = QaReply(
        thread_id=thread.id,
        author_type="teacher",
        admin_id=admin.id,
        content=content,
        created_at=now,
    )
    db.add(reply)
    thread.last_teacher_message_at = now
    thread.last_reply_at = now
    thread.updated_at = now
    thread.admin_last_read_at = now
    db.commit()
    db.refresh(reply)
    return _reply_payload(reply, {})


def admin_unread_count(db: Session) -> int:
    return int(
        db.scalar(
            select(func.count(QaThread.id)).where(
                or_(
                    QaThread.admin_last_read_at.is_(None),
                    QaThread.last_student_message_at > QaThread.admin_last_read_at,
                )
            )
        )
        or 0
    )
