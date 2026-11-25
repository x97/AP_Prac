from __future__ import annotations

import random
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.schemas import PracticeAnswerRequest, PracticeSessionCreate
from app.content.store import ContentStore
from app.core.errors import AppError
from app.core.time import utcnow
from app.services import entitlements
from app.services.progress import record_answer
from app.users.models import (
    Bookmark,
    PracticeSession,
    PracticeSessionQuestion,
    StudyPlanTask,
    User,
    WrongQuestion,
)


def _valid_group_ids(store: ContentStore) -> set[str]:
    return {g["group_id"] for g in store.list_groups()}


def _all_practice_ids(store: ContentStore, group_id: Optional[str] = None) -> set[str]:
    if group_id:
        return set(store.question_ids_for_group(group_id))
    out: set[str] = set()
    for group in store.list_groups():
        out.update(store.question_ids_for_group(group["group_id"]))
    return out


def _in_progress_query(user_id: str, source: str, group_id: Optional[str], topic_id: Optional[str]):
    stmt = select(PracticeSession).where(
        PracticeSession.user_id == user_id,
        PracticeSession.status == "in_progress",
        PracticeSession.source == source,
    )
    if source == "topic":
        stmt = stmt.where(PracticeSession.topic_id == topic_id)
    elif source == "unit":
        stmt = stmt.where(PracticeSession.group_id == group_id)
    elif group_id:
        stmt = stmt.where(PracticeSession.group_id == group_id)
    else:
        stmt = stmt.where(PracticeSession.group_id.is_(None))
    return stmt


def _abandon_in_progress(db: Session, stmt) -> None:
    for session in db.scalars(stmt):
        if session.status == "in_progress":
            session.status = "abandoned"
            session.submitted_at = utcnow()


def _wrong_candidates(
    db: Session, store: ContentStore, user_id: str, group_id: Optional[str] = None
) -> list[str]:
    excluded = store.exclusions
    candidates = list(
        db.scalars(
            select(WrongQuestion.question_id)
            .where(
                WrongQuestion.user_id == user_id,
                WrongQuestion.mastery != "mastered",
            )
            .order_by(WrongQuestion.last_wrong_at.desc())
        )
    )
    candidates = [qid for qid in dict.fromkeys(candidates) if qid not in excluded]
    if group_id:
        allowed = set(store.question_ids_for_group(group_id))
        candidates = [qid for qid in candidates if qid in allowed]
    # Real-exam wrong questions are not in practice topics; keep only those
    # that still exist in the current content release.
    existing_questions = store.get_questions(candidates, include_answers=False)
    return [qid for qid in candidates if qid in existing_questions]


def _sync_wrong_session(
    db: Session,
    store: ContentStore,
    session: PracticeSession,
    candidates: list[str],
) -> None:
    """Make the live wrong-question paper match the current wrong book.

    Existing rows keep their order and answers; newly wrong questions are
    appended; mastered questions are removed. This makes the paper dynamic.
    """
    rows = _session_rows(db, session.id)
    allowed = set(candidates)
    keep = [row for row in rows if row.question_id in allowed]
    keep_ids = {row.question_id for row in keep}
    for row in rows:
        if row.question_id not in allowed:
            db.delete(row)
    for index, row in enumerate(keep, start=1):
        row.sort_order = index
    next_order = len(keep) + 1
    for qid in candidates:
        if qid in keep_ids:
            continue
        db.add(
            PracticeSessionQuestion(
                session_id=session.id,
                question_id=qid,
                sort_order=next_order,
            )
        )
        next_order += 1
    total = len(keep) + sum(1 for qid in candidates if qid not in keep_ids)
    session.total = total
    db.flush()
    if total == 0:
        session.status = "submitted"
        session.submitted_at = utcnow()
        session.score = 0
        return
    _maybe_complete(db, session)


def _sync_if_wrong(db: Session, store: ContentStore, session: PracticeSession) -> None:
    if session.source == "wrong" and session.status == "in_progress":
        _sync_wrong_session(
            db,
            store,
            session,
            _wrong_candidates(db, store, session.user_id, session.group_id),
        )
        db.commit()


def create_session(
    db: Session,
    store: ContentStore,
    user: User,
    body: PracticeSessionCreate,
) -> dict[str, Any]:
    group_id = body.group_id
    topic_id = body.topic_id
    if body.source == "topic":
        if not topic_id:
            raise AppError(400, "TOPIC_REQUIRED", "请选择 topic")
        topic = store.get_topic(topic_id)
        if not topic:
            raise AppError(404, "TOPIC_NOT_FOUND", "Topic 不存在")
        group_id = topic["group_id"]
    elif body.source == "unit":
        if not group_id or group_id not in _valid_group_ids(store):
            raise AppError(400, "GROUP_REQUIRED", "请选择单元")
    elif body.source in ("wrong", "bookmark"):
        if group_id and group_id not in _valid_group_ids(store):
            raise AppError(400, "GROUP_INVALID", "单元不存在")
    else:
        raise AppError(400, "SOURCE_INVALID", "练习来源不正确")

    if group_id:
        entitlements.assert_group_access(db, user.id, store, group_id)

    scope = _in_progress_query(user.id, body.source, group_id, topic_id)
    existing = db.scalar(scope.order_by(PracticeSession.updated_at.desc()).limit(1))
    if existing and existing.content_release_id != store.release_id:
        existing.status = "abandoned"
        existing.submitted_at = utcnow()
        existing = None
    if existing and not body.restart:
        if existing.source == "wrong":
            _sync_if_wrong(db, store, existing)
            if existing.status == "in_progress":
                return session_payload(db, store, existing)
            # The live paper was completed by the sync; fall through to a new one.
            existing = None
        else:
            return session_payload(db, store, existing)
    if existing or body.restart:
        _abandon_in_progress(db, scope)
        db.flush()

    excluded = store.exclusions

    if body.source == "topic":
        candidates = store.question_ids_for_topic(topic_id or "")
        candidates = [qid for qid in candidates if qid not in excluded]
    elif body.source == "unit":
        candidates = store.question_ids_for_group(group_id or "")
        candidates = [qid for qid in candidates if qid not in excluded]
    elif body.source == "wrong":
        candidates = _wrong_candidates(db, store, user.id, group_id)
    else:
        candidates = list(
            db.scalars(
                select(Bookmark.question_id)
                .where(Bookmark.user_id == user.id)
                .order_by(Bookmark.created_at.desc())
            )
        )
        candidates = [qid for qid in dict.fromkeys(candidates) if qid not in excluded]
        if group_id:
            allowed = set(store.question_ids_for_group(group_id))
            candidates = [qid for qid in candidates if qid in allowed]
        existing_questions = store.get_questions(candidates, include_answers=False)
        candidates = [qid for qid in candidates if qid in existing_questions]

    if not candidates:
        raise AppError(409, "NO_QUESTIONS", "没有可练习的题目")

    if body.source in ("topic", "unit", "wrong"):
        # 章节/单元/错题卷保留整组题目；错题卷按最近答错时间排序。
        chosen = candidates
    else:
        count = min(body.count, 50, len(candidates))
        chosen = random.sample(candidates, count)

    session = PracticeSession(
        user_id=user.id,
        source=body.source,
        group_id=group_id,
        topic_id=topic_id if body.source == "topic" else None,
        status="in_progress",
        total=len(chosen),
        content_release_id=store.release_id,
    )
    db.add(session)
    db.flush()
    for i, qid in enumerate(chosen, start=1):
        db.add(PracticeSessionQuestion(session_id=session.id, question_id=qid, sort_order=i))
    db.commit()
    db.refresh(session)
    return session_payload(db, store, session)


def _get_session(db: Session, user: User, session_id: str) -> PracticeSession:
    session = db.get(PracticeSession, session_id)
    if not session or session.user_id != user.id:
        raise AppError(404, "SESSION_NOT_FOUND", "练习不存在")
    return session


def _session_rows(db: Session, session_id: str) -> list[PracticeSessionQuestion]:
    return list(
        db.scalars(
            select(PracticeSessionQuestion)
            .where(PracticeSessionQuestion.session_id == session_id)
            .order_by(PracticeSessionQuestion.sort_order)
        )
    )


def session_payload(
    db: Session, store: ContentStore, session: PracticeSession, include_all_feedback: bool = False
) -> dict[str, Any]:
    rows = _session_rows(db, session.id)
    ids = [r.question_id for r in rows]
    display = {row.question_id: index for index, row in enumerate(rows, start=1)}
    questions = store.get_questions(ids, include_answers=False, display_numbers=display)
    items = []
    answered = 0
    correct = 0
    for row in rows:
        q = questions.get(row.question_id)
        if not q:
            continue
        item = dict(q)
        item["selected_label"] = row.selected_label
        item["is_correct"] = row.is_correct
        item["flagged"] = bool(row.flagged)
        item["answered_at"] = row.answered_at
        if row.answered_at:
            answered += 1
            if row.is_correct:
                correct += 1
            item["feedback"] = store.get_feedback(row.question_id)
        items.append(item)
    next_index = next(
        (i for i, row in enumerate(rows) if not row.answered_at), max(0, len(rows) - 1)
    )
    topic_concepts = store.get_topic_concepts(session.topic_id) if session.topic_id else []
    payload = {
        "session": {
            "id": session.id,
            "source": session.source,
            "group_id": session.group_id,
            "topic_id": session.topic_id,
            "status": session.status,
            "score": session.score,
            "total": session.total,
            "answered": answered,
            "total_questions": len(items),
            "next_index": next_index,
            "started_at": session.started_at,
            "submitted_at": session.submitted_at,
        },
        "questions": items,
        "topic_concepts": topic_concepts,
        "progress": {
            "answered": answered,
            "correct": correct,
            "total": len(items),
            "accuracy": round(correct / answered, 3) if answered else None,
        },
    }
    if session.source == "homework":
        task = db.scalar(
            select(StudyPlanTask).where(
                StudyPlanTask.practice_session_id == session.id
            )
        )
        if task is not None:
            next_task = db.scalar(
                select(StudyPlanTask)
                .where(
                    StudyPlanTask.assignment_id == task.assignment_id,
                    StudyPlanTask.status == "pending",
                    StudyPlanTask.cancelled_at.is_(None),
                )
                .order_by(StudyPlanTask.day_index, StudyPlanTask.sort_order)
                .limit(1)
            )
            payload["homework"] = {
                "task_id": task.id,
                "assignment_id": task.assignment_id,
                "plan_title": task.plan_title,
                "plan_color": task.plan_color,
                "task_title": task.item_title,
                "study_date": task.study_date.isoformat(),
                "task_completed": task.status == "completed",
                "next_task": (
                    {
                        "id": next_task.id,
                        "title": next_task.item_title,
                        "study_date": next_task.study_date.isoformat(),
                    }
                    if next_task is not None
                    else None
                ),
            }
    return payload


def get_session(db: Session, store: ContentStore, user: User, session_id: str) -> dict[str, Any]:
    session = _get_session(db, user, session_id)
    _sync_if_wrong(db, store, session)
    return session_payload(db, store, session)


def topic_context_for_question(
    db: Session,
    store: ContentStore,
    user: User,
    session_id: str,
    question_id: str,
) -> dict[str, Any]:
    """Topic concepts for the current question.

    Topic practice has one session-level topic. Wrong/bookmark/unit practice can
    mix questions from several units, so the rail has to follow the question
    rather than the session.
    """
    session = _get_session(db, user, session_id)
    row = db.get(PracticeSessionQuestion, (session.id, question_id))
    if not row:
        raise AppError(404, "QUESTION_NOT_IN_SESSION", "题目不属于当前练习")

    context = store.question_context(question_id)
    inferred = not bool(context.get("topic_id"))
    topic = store.topic_for_question(question_id)
    if not topic and session.topic_id:
        topic = store.get_topic(session.topic_id)
    if not topic:
        return {"topic": None, "concepts": [], "inferred": inferred}

    return {
        "topic": topic,
        "concepts": store.get_topic_concepts(topic["topic_id"]),
        "inferred": inferred,
    }


def _maybe_complete(db: Session, session: PracticeSession) -> bool:
    if session.status != "in_progress":
        if session.status == "submitted" and session.source == "homework":
            from app.services import study_plans

            study_plans.sync_task_progress(db, session)
        return session.status == "submitted"
    rows = _session_rows(db, session.id)
    if rows and all(row.answered_at for row in rows):
        session.status = "submitted"
        session.submitted_at = utcnow()
        session.score = sum(1 for row in rows if row.is_correct)
        session.total = len(rows)
        if session.source == "homework":
            from app.services import study_plans

            study_plans.sync_task_progress(db, session)
        return True
    return False


def _save_answer(
    db: Session,
    store: ContentStore,
    session: PracticeSession,
    row: PracticeSessionQuestion,
    selected_label: str,
) -> dict[str, Any]:
    if row.answered_at:
        feedback = store.get_feedback(row.question_id)
        return {
            "question_id": row.question_id,
            "selected_label": row.selected_label,
            "is_correct": row.is_correct,
            "already_answered": True,
            "feedback": feedback,
        }
    feedback = store.get_feedback(row.question_id)
    labels = {o["label"] for o in feedback["options"]}
    label = selected_label.strip().upper()
    if label not in labels:
        raise AppError(400, "OPTION_INVALID", "选项不存在")
    selected = next(o for o in feedback["options"] if o["label"] == label)
    is_correct = bool(selected.get("is_correct"))
    row.selected_label = label
    row.is_correct = is_correct
    row.answered_at = utcnow()
    session.updated_at = utcnow()
    record_answer(db, store, session.user_id, row.question_id, is_correct)
    return {
        "question_id": row.question_id,
        "selected_label": label,
        "is_correct": is_correct,
        "already_answered": False,
        "feedback": feedback,
    }


def answer_question(
    db: Session,
    store: ContentStore,
    user: User,
    session_id: str,
    body: PracticeAnswerRequest,
) -> dict[str, Any]:
    session = _get_session(db, user, session_id)
    if session.status != "in_progress":
        raise AppError(409, "SESSION_FINISHED", "练习已结束")
    row = db.get(PracticeSessionQuestion, (session.id, body.question_id))
    if not row:
        raise AppError(404, "QUESTION_NOT_IN_SESSION", "题目不在本次练习中")
    result = _save_answer(db, store, session, row, body.selected_label)
    completed = _maybe_complete(db, session)
    db.commit()
    result["completed"] = completed
    result["session_status"] = session.status
    result["score"] = session.score
    result["total"] = session.total
    return result


def flag_question(
    db: Session, user: User, session_id: str, question_id: str, flagged: bool
) -> dict[str, Any]:
    session = _get_session(db, user, session_id)
    row = db.get(PracticeSessionQuestion, (session.id, question_id))
    if not row:
        raise AppError(404, "QUESTION_NOT_IN_SESSION", "题目不在本次练习中")
    row.flagged = flagged
    session.updated_at = utcnow()
    db.commit()
    return {"question_id": question_id, "flagged": flagged}


def flush_answers(
    db: Session,
    store: ContentStore,
    user: User,
    session_id: str,
    answers: list[PracticeAnswerRequest],
) -> dict[str, Any]:
    session = _get_session(db, user, session_id)
    if session.status != "in_progress":
        return {"saved": 0, "finished": True}
    saved = 0
    for body in answers:
        row = db.get(PracticeSessionQuestion, (session.id, body.question_id))
        if not row or row.answered_at:
            continue
        try:
            _save_answer(db, store, session, row, body.selected_label)
            saved += 1
        except AppError:
            continue
    completed = _maybe_complete(db, session) if saved else False
    if saved:
        db.commit()
    return {
        "saved": saved,
        "completed": completed,
        "session_status": session.status,
        "score": session.score,
        "total": session.total,
    }


def submit_session(db: Session, user: User, session_id: str) -> dict[str, Any]:
    session = _get_session(db, user, session_id)
    if session.status == "submitted":
        return {
            "session": {
                "id": session.id,
                "status": session.status,
                "score": session.score,
                "total": session.total,
            }
        }
    rows = _session_rows(db, session.id)
    total = len(rows)
    answered = sum(1 for r in rows if r.answered_at)
    correct = sum(1 for r in rows if r.is_correct)
    if session.source == "homework" and answered < total:
        raise AppError(409, "HOMEWORK_INCOMPLETE", "请完成全部题目后再提交")
    session.status = "submitted"
    session.submitted_at = utcnow()
    session.score = correct
    session.total = total
    if session.source == "homework":
        from app.services import study_plans

        study_plans.sync_task_progress(db, session)
    db.commit()
    return {
        "session": {
            "id": session.id,
            "status": session.status,
            "score": correct,
            "total": total,
            "answered": answered,
            "accuracy": round(correct / answered, 3) if answered else None,
            "completion": round(answered / total, 3) if total else None,
        }
    }


def abandon_session(db: Session, user: User, session_id: str) -> dict[str, Any]:
    session = _get_session(db, user, session_id)
    if session.status == "in_progress":
        session.status = "abandoned"
        session.submitted_at = utcnow()
        db.commit()
    return {"session": {"id": session.id, "status": session.status}}


def review_session(db: Session, store: ContentStore, user: User, session_id: str) -> dict[str, Any]:
    session = _get_session(db, user, session_id)
    _sync_if_wrong(db, store, session)
    return session_payload(db, store, session, include_all_feedback=True)
