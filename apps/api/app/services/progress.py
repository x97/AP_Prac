from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Iterable, Optional
from zoneinfo import ZoneInfo

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.content.store import ContentStore
from app.core.time import utcnow
from app.users.models import (
    Attempt,
    PracticeSession,
    PracticeSessionQuestion,
    UserDailyStat,
    UserQuestionStat,
    WrongQuestion,
)

SHANGHAI = ZoneInfo("Asia/Shanghai")


def local_day(now: Optional[datetime] = None) -> date:
    return (now or utcnow()).astimezone(SHANGHAI).date()


def _chunks(values: list[str], size: int = 500) -> Iterable[list[str]]:
    for i in range(0, len(values), size):
        yield values[i : i + size]


def stats_for_questions(
    db: Session, user_id: str, question_ids: list[str]
) -> dict[str, UserQuestionStat]:
    out: dict[str, UserQuestionStat] = {}
    for chunk in _chunks(question_ids):
        for row in db.scalars(
            select(UserQuestionStat).where(
                UserQuestionStat.user_id == user_id,
                UserQuestionStat.question_id.in_(chunk),
            )
        ):
            out[row.question_id] = row
    return out


def aggregate(db: Session, user_id: str, question_ids: list[str]) -> dict[str, int]:
    stats = stats_for_questions(db, user_id, question_ids)
    answered = len(stats)
    correct = sum(1 for s in stats.values() if s.last_is_correct is True)
    return {"total": len(question_ids), "answered": answered, "correct": correct}


def record_answer(
    db: Session,
    store: ContentStore,
    user_id: str,
    question_id: str,
    is_correct: bool,
) -> None:
    context = store.question_context(question_id)
    unit_id = context.get("unit_id")
    topic_id = context.get("topic_id")
    now = utcnow()

    wq = db.get(WrongQuestion, (user_id, question_id))
    if not is_correct:
        if not wq:
            wq = WrongQuestion(
                user_id=user_id,
                question_id=question_id,
                wrong_count=0,
                correct_streak=0,
                mastery="learning",
                content_release_id=store.release_id,
            )
            db.add(wq)
        wq.unit_id = unit_id
        wq.primary_topic_id = topic_id
        wq.content_release_id = store.release_id
        wq.wrong_count += 1
        wq.correct_streak = 0
        wq.mastery = "reviewing" if wq.mastery == "mastered" else "learning"
        wq.mastered_at = None
        wq.last_wrong_at = now
        wq.updated_at = now
    elif wq:
        wq.unit_id = unit_id
        wq.primary_topic_id = topic_id
        wq.content_release_id = store.release_id
        wq.correct_streak += 1
        wq.mastery = "mastered" if wq.correct_streak >= 2 else "reviewing"
        if wq.mastery == "mastered":
            wq.mastered_at = now
        wq.updated_at = now

    stat = db.get(UserQuestionStat, (user_id, question_id))
    if not stat:
        stat = UserQuestionStat(
            user_id=user_id,
            question_id=question_id,
            attempts=0,
            correct_count=0,
            content_release_id=store.release_id,
        )
        db.add(stat)
    stat.unit_id = unit_id
    stat.primary_topic_id = topic_id
    stat.content_release_id = store.release_id
    stat.attempts += 1
    stat.last_is_correct = is_correct
    stat.last_answered_at = now
    if is_correct:
        stat.correct_count += 1
        stat.last_correct_at = now

    day = local_day(now)
    daily = db.get(UserDailyStat, (user_id, day))
    if daily is None:
        # submit_section calls this once per answered question in one
        # transaction; a pending row may not be visible to Session.get yet.
        daily = next(
            (
                obj
                for obj in db.new
                if isinstance(obj, UserDailyStat)
                and obj.user_id == user_id
                and obj.day == day
            ),
            None,
        )
    if daily is None:
        daily = UserDailyStat(user_id=user_id, day=day, answered=0, correct=0)
        db.add(daily)
    daily.answered += 1
    if is_correct:
        daily.correct += 1


def streak_days(db: Session, user_id: str) -> int:
    days = [
        row.day
        for row in db.scalars(
            select(UserDailyStat)
            .where(UserDailyStat.user_id == user_id)
            .order_by(UserDailyStat.day.desc())
            .limit(60)
        )
    ]
    if not days:
        return 0
    today = local_day()
    expected = today if days[0] == today else today - timedelta(days=1)
    count = 0
    for day in days:
        if day == expected:
            count += 1
            expected -= timedelta(days=1)
        elif day < expected:
            break
    return count


def unit_progress(db: Session, store: ContentStore, user_id: str) -> list[dict[str, Any]]:
    out = []
    for group in store.list_groups():
        ids = store.question_ids_for_group(group["group_id"])
        agg = aggregate(db, user_id, ids)
        out.append(
            {
                **group,
                **agg,
                "accuracy": round(agg["correct"] / agg["answered"], 3) if agg["answered"] else None,
            }
        )
    return out


def _session_question_stats(
    db: Session, session_ids: list[str]
) -> dict[str, dict[str, Optional[int]]]:
    if not session_ids:
        return {}
    rows = db.execute(
        select(
            PracticeSessionQuestion.session_id,
            func.count().label("total"),
            func.count(PracticeSessionQuestion.answered_at).label("answered"),
            func.sum(case((PracticeSessionQuestion.is_correct.is_(True), 1), else_=0)).label(
                "correct"
            ),
            func.min(
                case(
                    (
                        PracticeSessionQuestion.answered_at.is_(None),
                        PracticeSessionQuestion.sort_order,
                    ),
                    else_=None,
                )
            ).label("next_sort"),
        )
        .where(PracticeSessionQuestion.session_id.in_(session_ids))
        .group_by(PracticeSessionQuestion.session_id)
    ).all()
    return {
        row.session_id: {
            "total": int(row.total or 0),
            "answered": int(row.answered or 0),
            "correct": int(row.correct or 0),
            "next_sort": int(row.next_sort) if row.next_sort is not None else None,
        }
        for row in rows
    }


def _topic_current_sessions(
    db: Session, user_id: str, topic_ids: list[str]
) -> dict[str, dict[str, Any]]:
    if not topic_ids:
        return {}
    sessions = list(
        db.scalars(
            select(PracticeSession)
            .where(
                PracticeSession.user_id == user_id,
                PracticeSession.source == "topic",
                PracticeSession.topic_id.in_(topic_ids),
            )
            .order_by(PracticeSession.updated_at.desc())
        )
    )
    latest: dict[str, PracticeSession] = {}
    active: dict[str, PracticeSession] = {}
    for session in sessions:
        if session.topic_id is None:
            continue
        if session.topic_id not in latest:
            latest[session.topic_id] = session
        if session.status == "in_progress" and session.topic_id not in active:
            active[session.topic_id] = session

    chosen = {topic_id: active.get(topic_id) or latest.get(topic_id) for topic_id in topic_ids}
    stats = _session_question_stats(db, [s.id for s in chosen.values() if s])
    out: dict[str, dict[str, Any]] = {}
    for topic_id, session in chosen.items():
        if not session:
            continue
        stat = stats.get(session.id, {})
        total = int(stat.get("total") or session.total or 0)
        answered = int(stat.get("answered") or 0)
        next_sort = stat.get("next_sort")
        out[topic_id] = {
            "id": session.id,
            "status": session.status,
            "answered": answered,
            "total": total,
            "correct": int(stat.get("correct") or 0),
            "next_index": (int(next_sort) - 1) if next_sort is not None else max(0, total - 1),
            "score": session.score,
            "updated_at": session.updated_at,
            "submitted_at": session.submitted_at,
        }
    return out


def topic_progress(
    db: Session, store: ContentStore, user_id: str, group_id: str
) -> list[dict[str, Any]]:
    topics = store.list_topics(group_id)
    qmap = store.topic_question_map(group_id)
    current = _topic_current_sessions(db, user_id, [t["topic_id"] for t in topics])
    out = []
    for topic in topics:
        ids = qmap.get(topic["topic_id"], [])
        agg = aggregate(db, user_id, ids)
        out.append(
            {
                **topic,
                "total": agg["total"],
                "answered": agg["answered"],
                "correct": agg["correct"],
                "accuracy": round(agg["correct"] / agg["answered"], 3) if agg["answered"] else None,
                "current_session": current.get(topic["topic_id"]),
            }
        )
    return out


def _practice_titles(
    store: ContentStore, group_id: Optional[str], topic_id: Optional[str]
) -> dict[str, Any]:
    group = store.get_group(group_id) if group_id else None
    topic = store.get_topic(topic_id) if topic_id else None
    return {
        "group_title": group.get("title") if group else None,
        "group_title_en": group.get("title_en") if group else None,
        "topic_title_zh": topic.get("title_zh") if topic else None,
        "topic_title_en": topic.get("title_en") if topic else None,
        "topic_code": topic.get("code") if topic else None,
    }


def _attempt_titles(store: ContentStore, paper_id: str) -> dict[str, Any]:
    paper = store.get_paper(paper_id) or {}
    return {
        "paper_title": paper.get("title") or paper.get("chinese_title"),
        "paper_title_en": paper.get("title"),
        "paper_year": paper.get("year"),
        "paper_type": paper.get("paper_type"),
    }


def _practice_counts(db: Session, session_id: str) -> dict[str, int]:
    row = db.execute(
        select(
            func.count(),
            func.count(PracticeSessionQuestion.answered_at),
            func.sum(case((PracticeSessionQuestion.is_correct.is_(True), 1), else_=0)),
        ).where(PracticeSessionQuestion.session_id == session_id)
    ).one()
    return {
        "total_questions": int(row[0] or 0),
        "answered": int(row[1] or 0),
        "correct": int(row[2] or 0),
    }


def activity_days(
    db: Session, user_id: str, days: int = 365
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    today = local_day()
    start = today - timedelta(days=days - 1)
    rows = db.scalars(
        select(UserDailyStat)
        .where(
            UserDailyStat.user_id == user_id,
            UserDailyStat.day >= start,
            UserDailyStat.day <= today,
        )
        .order_by(UserDailyStat.day)
    )
    by_day = {row.day: row for row in rows}
    out: list[dict[str, Any]] = []
    total_answered = 0
    active_days = 0
    for offset in range(days):
        day = start + timedelta(days=offset)
        row = by_day.get(day)
        answered = int(row.answered) if row else 0
        correct = int(row.correct) if row else 0
        total_answered += answered
        if answered:
            active_days += 1
        out.append({"day": day.isoformat(), "answered": answered, "correct": correct})
    return out, {
        "days": days,
        "active_days": active_days,
        "total_answered": total_answered,
    }


def dashboard(db: Session, store: ContentStore, user_id: str) -> dict[str, Any]:
    # Local import avoids a module cycle: exam_engine also imports progress.
    from app.services.exam_engine import finalize_expired_for_user

    finalize_expired_for_user(db, store, user_id)
    total = (
        db.scalar(
            select(func.count())
            .select_from(UserQuestionStat)
            .where(
                UserQuestionStat.user_id == user_id,
                UserQuestionStat.primary_topic_id.is_not(None),
            )
        )
        or 0
    )
    correct = (
        db.scalar(
            select(func.count())
            .select_from(UserQuestionStat)
            .where(
                UserQuestionStat.user_id == user_id,
                UserQuestionStat.primary_topic_id.is_not(None),
                UserQuestionStat.last_is_correct.is_(True),
            )
        )
        or 0
    )
    units = unit_progress(db, store, user_id)

    continue_item = None
    practice = db.scalar(
        select(PracticeSession)
        .where(
            PracticeSession.user_id == user_id,
            PracticeSession.status == "in_progress",
            PracticeSession.source != "homework",
        )
        .order_by(PracticeSession.updated_at.desc())
        .limit(1)
    )
    attempt = db.scalar(
        select(Attempt)
        .where(
            Attempt.user_id == user_id,
            Attempt.status.in_(["in_progress", "awaiting_self_grade"]),
        )
        .order_by(Attempt.updated_at.desc())
        .limit(1)
    )
    candidates = []
    if practice:
        counts = _practice_counts(db, practice.id)
        candidates.append(
            {
                "type": "practice",
                "id": practice.id,
                "source": practice.source,
                "group_id": practice.group_id,
                "topic_id": practice.topic_id,
                "status": practice.status,
                "score": practice.score,
                "total": practice.total,
                "updated_at": practice.updated_at,
                **_practice_titles(store, practice.group_id, practice.topic_id),
                **counts,
            }
        )
    if attempt:
        candidates.append(
            {
                "type": "attempt",
                "id": attempt.id,
                "paper_id": attempt.paper_id,
                "mode": attempt.mode,
                "frq_form": attempt.frq_form,
                "status": attempt.status,
                "mcq_score": attempt.mcq_score,
                "mcq_total": attempt.mcq_total,
                "updated_at": attempt.updated_at,
                **_attempt_titles(store, attempt.paper_id),
            }
        )
    if candidates:
        continue_item = max(candidates, key=lambda x: x["updated_at"])

    recent: list[dict[str, Any]] = []
    for row in db.scalars(
        select(PracticeSession)
        .where(PracticeSession.user_id == user_id)
        .order_by(PracticeSession.created_at.desc())
        .limit(5)
    ):
        counts = _practice_counts(db, row.id)
        recent.append(
            {
                "type": "practice",
                "id": row.id,
                "source": row.source,
                "group_id": row.group_id,
                "topic_id": row.topic_id,
                "status": row.status,
                "score": row.score,
                "total": row.total,
                "created_at": row.created_at,
                **_practice_titles(store, row.group_id, row.topic_id),
                **counts,
            }
        )
    for row in db.scalars(
        select(Attempt)
        .where(Attempt.user_id == user_id)
        .order_by(Attempt.created_at.desc())
        .limit(5)
    ):
        recent.append(
            {
                "type": "attempt",
                "id": row.id,
                "paper_id": row.paper_id,
                "mode": row.mode,
                "frq_form": row.frq_form,
                "status": row.status,
                "mcq_score": row.mcq_score,
                "mcq_total": row.mcq_total,
                "frq_score": row.frq_score,
                "frq_total": row.frq_total,
                "created_at": row.created_at,
                **_attempt_titles(store, row.paper_id),
            }
        )
    recent.sort(key=lambda x: x["created_at"], reverse=True)

    activity, activity_summary = activity_days(db, user_id)
    return {
        "overview": {
            "answered": total,
            "correct": correct,
            "accuracy": round(correct / total, 3) if total else None,
            "streak_days": streak_days(db, user_id),
        },
        "activity": activity,
        "activity_summary": activity_summary,
        "units": units,
        "continue": continue_item,
        "recent": recent[:5],
    }
