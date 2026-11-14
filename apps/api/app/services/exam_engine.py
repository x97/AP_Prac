from __future__ import annotations

from datetime import timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.schemas import AttemptAnswerItem, AttemptCreate, FrqScoreItem
from app.content.store import ContentStore
from app.core.errors import AppError
from app.core.time import as_utc, utcnow
from app.services import entitlements
from app.services.progress import record_answer
from app.users.models import (
    Attempt,
    AttemptAnswer,
    AttemptFrqScore,
    AttemptQuestion,
    AttemptSection,
    AttemptSectionPause,
    User,
)

GRACE_SECONDS = 120


def _get_attempt(db: Session, user: User, attempt_id: str) -> Attempt:
    attempt = db.get(Attempt, attempt_id)
    if not attempt or attempt.user_id != user.id:
        raise AppError(404, "ATTEMPT_NOT_FOUND", "考试不存在")
    return attempt


def _get_section(db: Session, attempt_id: str, section: str) -> AttemptSection:
    row = db.scalar(
        select(AttemptSection).where(
            AttemptSection.attempt_id == attempt_id, AttemptSection.section == section
        )
    )
    if not row:
        raise AppError(404, "SECTION_NOT_FOUND", "考试 section 不存在")
    return row


def _pause_row(db: Session, attempt_id: str, section: str) -> AttemptSectionPause | None:
    return db.get(AttemptSectionPause, (attempt_id, section))


def _clear_pauses(db: Session, attempt_id: str) -> None:
    for row in db.scalars(
        select(AttemptSectionPause).where(AttemptSectionPause.attempt_id == attempt_id)
    ):
        db.delete(row)


def _questions(db: Session, attempt_id: str, section: str) -> list[AttemptQuestion]:
    return list(
        db.scalars(
            select(AttemptQuestion)
            .where(AttemptQuestion.attempt_id == attempt_id, AttemptQuestion.section == section)
            .order_by(AttemptQuestion.sort_order)
        )
    )


def _answers(db: Session, attempt_id: str) -> dict[str, AttemptAnswer]:
    return {
        row.question_id: row
        for row in db.scalars(select(AttemptAnswer).where(AttemptAnswer.attempt_id == attempt_id))
    }


def _remaining_ms(expires_at, now) -> int:  # noqa: ANN001
    return max(0, int((as_utc(expires_at) - now).total_seconds() * 1000))


def _finalize_if_expired(db: Session, store: ContentStore, user: User, attempt: Attempt) -> None:
    if attempt.status != "in_progress":
        return
    section = _get_section(db, attempt.id, attempt.current_section or "mcq")
    if section.status != "active" or section.expires_at is None:
        return
    if _pause_row(db, attempt.id, section.section):
        return
    now = utcnow()
    if now > as_utc(section.expires_at) + timedelta(seconds=GRACE_SECONDS):
        submit_section(db, store, user, attempt.id, section.section, auto=True)


def finalize_expired_for_user(db: Session, store: ContentStore, user_id: str) -> None:
    user = db.get(User, user_id)
    if not user:
        return
    attempts = list(
        db.scalars(
            select(Attempt).where(
                Attempt.user_id == user_id,
                Attempt.status == "in_progress",
            )
        )
    )
    for attempt in attempts:
        _finalize_if_expired(db, store, user, attempt)


def finalize_expired_for_paper(db: Session, store: ContentStore, user: User, paper_id: str) -> None:
    attempts = list(
        db.scalars(
            select(Attempt).where(
                Attempt.user_id == user.id,
                Attempt.paper_id == paper_id,
                Attempt.status == "in_progress",
            )
        )
    )
    for attempt in attempts:
        _finalize_if_expired(db, store, user, attempt)


def _abandon(db: Session, attempt: Attempt) -> None:
    if attempt.status not in ("in_progress", "awaiting_self_grade"):
        return
    now = utcnow()
    attempt.status = "abandoned"
    attempt.submitted_at = now
    for section in db.scalars(
        select(AttemptSection).where(AttemptSection.attempt_id == attempt.id)
    ):
        if section.status == "active":
            section.status = "submitted"
            section.submitted_at = now
            section.finalized_reason = "abandoned"
    _clear_pauses(db, attempt.id)


def _state_payload(db: Session, store: ContentStore, attempt: Attempt) -> dict[str, Any]:
    section_name = attempt.current_section or "mcq"
    section = _get_section(db, attempt.id, section_name)
    qrows = _questions(db, attempt.id, section_name)
    ids = [q.question_id for q in qrows]
    display = {q.question_id: q.display_number for q in qrows}
    questions = (
        store.get_questions(ids, include_answers=False, display_numbers=display)
        if section.status != "not_started"
        else {}
    )
    answers = _answers(db, attempt.id)
    now = utcnow()
    pause = _pause_row(db, attempt.id, section_name)
    paused = bool(pause) and section.status == "active"
    if paused and pause is not None:
        remaining_ms = int(pause.remaining_ms)
    elif section.expires_at:
        remaining_ms = _remaining_ms(section.expires_at, now)
    else:
        remaining_ms = None
    return {
        "attempt": {
            "id": attempt.id,
            "paper_id": attempt.paper_id,
            "mode": attempt.mode,
            "frq_form": attempt.frq_form,
            "status": attempt.status,
            "current_section": attempt.current_section,
            "mcq_score": attempt.mcq_score,
            "mcq_total": attempt.mcq_total,
            "frq_score": attempt.frq_score,
            "frq_total": attempt.frq_total,
        },
        "section": {
            "name": section.section,
            "status": section.status,
            "started_at": section.started_at,
            "expires_at": section.expires_at,
            "submitted_at": section.submitted_at,
            "finalized_reason": section.finalized_reason,
            "score": section.score,
            "total": section.total,
            "paused": paused,
        },
        "can_start": section.status == "not_started",
        "paused": paused,
        "server_time": now,
        "remaining_ms": remaining_ms,
        "questions": [questions[qid] for qid in ids if qid in questions],
        "answers": [
            {
                "question_id": a.question_id,
                "selected_label": a.selected_label,
                "flagged": a.flagged,
                "frq_text": a.frq_text,
                "late": a.late,
                "server_saved_at": a.server_saved_at,
            }
            for a in answers.values()
        ],
    }


def create_attempt(
    db: Session,
    store: ContentStore,
    user: User,
    body: AttemptCreate,
) -> dict[str, Any]:
    paper = store.get_paper(body.paper_id)
    if not paper:
        raise AppError(404, "PAPER_NOT_FOUND", "试卷不存在")
    entitlements.assert_paper_access(db, user.id, store, body.paper_id)
    if body.mode not in paper.get("modes", []):
        raise AppError(400, "MODE_NOT_AVAILABLE", "这套卷不支持该模式")
    config = store.get_exam_config(body.paper_id)
    if not config:
        raise AppError(400, "EXAM_CONFIG_MISSING", "试卷缺少考试配置")

    frq_form = body.frq_form
    forms = config.get("frq_forms") or []
    if body.mode in ("frq", "full"):
        if forms:
            if not frq_form:
                raise AppError(400, "FRQ_FORM_REQUIRED", "请选择 FRQ Set 1 / Set 2")
            if frq_form not in forms:
                raise AppError(400, "FRQ_FORM_INVALID", "FRQ 套次不存在")
        else:
            frq_form = None
    else:
        frq_form = None

    existing = db.scalar(
        select(Attempt)
        .where(
            Attempt.user_id == user.id,
            Attempt.paper_id == body.paper_id,
            Attempt.status.in_(["in_progress", "awaiting_self_grade"]),
        )
        .order_by(Attempt.updated_at.desc())
        .limit(1)
    )
    if existing and not body.restart:
        return _state_payload(db, store, existing)
    if existing:
        _abandon(db, existing)
        db.flush()

    mcq_ids = (
        store.question_ids_for_paper(body.paper_id, "MCQ") if body.mode in ("mcq", "full") else []
    )
    frq_ids = (
        store.question_ids_for_paper(body.paper_id, "FRQ", frq_form)
        if body.mode in ("frq", "full")
        else []
    )
    if body.mode in ("mcq", "full"):
        if len(mcq_ids) != int(config.get("mcq_count") or 0):
            raise AppError(409, "PAPER_INCOMPLETE", "MCQ 题数与配置不一致")
    if body.mode in ("frq", "full"):
        if len(frq_ids) != int(config.get("frq_count") or 0):
            raise AppError(409, "PAPER_INCOMPLETE", "FRQ 题数与配置不一致")

    mcq_questions = store.get_questions(mcq_ids, include_answers=False)
    frq_questions = store.get_questions(frq_ids, include_answers=False)
    if len(mcq_questions) != len(mcq_ids) or len(frq_questions) != len(frq_ids):
        raise AppError(409, "PAPER_INCOMPLETE", "试卷存在缺失题目")

    now = utcnow()
    attempt = Attempt(
        user_id=user.id,
        paper_id=body.paper_id,
        mode=body.mode,
        frq_form=frq_form,
        status="in_progress",
        current_section="mcq" if body.mode in ("mcq", "full") else "frq",
        started_at=now,
        mcq_total=len(mcq_ids) if mcq_ids else None,
        frq_total=store.frq_total_points(frq_ids) if frq_ids else None,
        content_release_id=store.release_id,
        config_snapshot=config,
    )
    db.add(attempt)
    db.flush()

    if body.mode in ("mcq", "full"):
        mcq_expires = now + timedelta(minutes=int(config.get("mcq_minutes") or 0))
        db.add(
            AttemptSection(
                attempt_id=attempt.id,
                section="mcq",
                status="active",
                started_at=now,
                expires_at=mcq_expires,
                total=len(mcq_ids),
            )
        )
        for i, qid in enumerate(mcq_ids, start=1):
            q = mcq_questions[qid]
            db.add(
                AttemptQuestion(
                    attempt_id=attempt.id,
                    question_id=qid,
                    section="mcq",
                    sort_order=i,
                    display_number=int(q.get("display_number") or q.get("number") or i),
                )
            )

    if body.mode in ("frq", "full"):
        frq_active = body.mode == "frq"
        frq_expires = (
            now + timedelta(minutes=int(config.get("frq_minutes") or 0)) if frq_active else None
        )
        db.add(
            AttemptSection(
                attempt_id=attempt.id,
                section="frq",
                status="active" if frq_active else "not_started",
                started_at=now if frq_active else None,
                expires_at=frq_expires,
                total=store.frq_total_points(frq_ids),
            )
        )
        for i, qid in enumerate(frq_ids, start=1):
            q = frq_questions[qid]
            db.add(
                AttemptQuestion(
                    attempt_id=attempt.id,
                    question_id=qid,
                    section="frq",
                    sort_order=i,
                    display_number=int(q.get("display_number") or q.get("number") or i),
                )
            )

    db.commit()
    db.refresh(attempt)
    return _state_payload(db, store, attempt)


def get_attempt(db: Session, store: ContentStore, user: User, attempt_id: str) -> dict[str, Any]:
    attempt = _get_attempt(db, user, attempt_id)
    _finalize_if_expired(db, store, user, attempt)
    attempt = _get_attempt(db, user, attempt_id)
    return _state_payload(db, store, attempt)


def pause_attempt(db: Session, store: ContentStore, user: User, attempt_id: str) -> dict[str, Any]:
    attempt = _get_attempt(db, user, attempt_id)
    if attempt.status != "in_progress":
        raise AppError(409, "ATTEMPT_NOT_ACTIVE", "考试已结束，无法暂停")

    _finalize_if_expired(db, store, user, attempt)
    if attempt.status != "in_progress":
        raise AppError(409, "SECTION_EXPIRED", "考试时间已结束")

    section = _get_section(db, attempt.id, attempt.current_section or "mcq")
    if section.status != "active":
        raise AppError(409, "SECTION_NOT_ACTIVE", "当前 section 不能暂停")

    pause = _pause_row(db, attempt.id, section.section)
    if pause:
        return _state_payload(db, store, attempt)

    if section.expires_at is None:
        raise AppError(409, "SECTION_NOT_ACTIVE", "当前 section 没有计时")

    now = utcnow()
    remaining = _remaining_ms(section.expires_at, now)
    if remaining <= 0:
        raise AppError(409, "SECTION_EXPIRED", "考试时间已结束")

    db.add(
        AttemptSectionPause(
            attempt_id=attempt.id,
            section=section.section,
            remaining_ms=remaining,
            paused_at=now,
        )
    )
    attempt.updated_at = now
    db.commit()
    return _state_payload(db, store, attempt)


def resume_attempt(db: Session, store: ContentStore, user: User, attempt_id: str) -> dict[str, Any]:
    attempt = _get_attempt(db, user, attempt_id)
    if attempt.status != "in_progress":
        raise AppError(409, "ATTEMPT_NOT_ACTIVE", "考试已结束，无法继续")

    section = _get_section(db, attempt.id, attempt.current_section or "mcq")
    pause = _pause_row(db, attempt.id, section.section)
    if not pause or section.status != "active":
        return _state_payload(db, store, attempt)

    now = utcnow()
    section.expires_at = now + timedelta(milliseconds=max(1, int(pause.remaining_ms)))
    attempt.updated_at = now
    db.delete(pause)
    db.commit()
    return _state_payload(db, store, attempt)


def start_section(
    db: Session, store: ContentStore, user: User, attempt_id: str, section_name: str
) -> dict[str, Any]:
    attempt = _get_attempt(db, user, attempt_id)
    section = _get_section(db, attempt.id, section_name)
    if section_name != "frq":
        return _state_payload(db, store, attempt)
    if attempt.mode == "full":
        mcq_section = _get_section(db, attempt.id, "mcq")
        if mcq_section.status != "submitted":
            raise AppError(409, "MCQ_NOT_SUBMITTED", "先提交 Section I")
    if section.status == "active":
        return _state_payload(db, store, attempt)
    if section.status != "not_started":
        raise AppError(409, "SECTION_NOT_ACTIVE", "section 无法开始")
    config = store.get_exam_config(attempt.paper_id) or {}
    now = utcnow()
    section.status = "active"
    section.started_at = now
    section.expires_at = now + timedelta(minutes=int(config.get("frq_minutes") or 0))
    attempt.current_section = "frq"
    db.commit()
    return _state_payload(db, store, attempt)


def save_answers(
    db: Session,
    store: ContentStore,
    user: User,
    attempt_id: str,
    items: list[AttemptAnswerItem],
) -> dict[str, Any]:
    attempt = _get_attempt(db, user, attempt_id)
    section = _get_section(db, attempt.id, attempt.current_section or "mcq")
    if section.status != "active":
        raise AppError(409, "SECTION_FINISHED", "当前 section 已结束")
    if _pause_row(db, attempt.id, section.section):
        raise AppError(409, "SECTION_PAUSED", "考试已暂停，请继续考试后再作答")
    now = utcnow()
    expired = section.expires_at and now > as_utc(section.expires_at)
    if expired and now > as_utc(section.expires_at) + timedelta(seconds=GRACE_SECONDS):
        raise AppError(409, "SECTION_EXPIRED", "考试时间已结束")
    qids = {q.question_id for q in _questions(db, attempt.id, section.section)}
    labels_by_q: dict[str, set[str]] = {}
    for item in items:
        if item.question_id not in qids:
            raise AppError(400, "QUESTION_NOT_IN_ATTEMPT", "题目不在本次考试中")
        if item.selected_label:
            if item.question_id not in labels_by_q:
                q = store.get_questions([item.question_id], include_answers=False).get(
                    item.question_id
                )
                labels_by_q[item.question_id] = {o["label"] for o in (q or {}).get("options", [])}
            if item.selected_label.strip().upper() not in labels_by_q[item.question_id]:
                raise AppError(400, "OPTION_INVALID", "选项不存在")

    saved = 0
    for item in items:
        row = db.get(AttemptAnswer, (attempt.id, item.question_id))
        if not row:
            row = AttemptAnswer(attempt_id=attempt.id, question_id=item.question_id)
            db.add(row)
        if item.selected_label is not None:
            row.selected_label = item.selected_label.strip().upper()
        if item.flagged is not None:
            row.flagged = item.flagged
        if item.frq_text is not None:
            row.frq_text = item.frq_text
        if item.time_spent_ms is not None:
            row.time_spent_ms = item.time_spent_ms
        row.late = bool(expired)
        row.server_saved_at = now
        saved += 1
    db.commit()
    return {
        "saved": saved,
        "server_time": now,
        "remaining_ms": _remaining_ms(section.expires_at, now) if section.expires_at else None,
        "late": bool(expired),
    }


def submit_section(
    db: Session,
    store: ContentStore,
    user: User,
    attempt_id: str,
    section_name: str,
    auto: bool = False,
) -> dict[str, Any]:
    attempt = _get_attempt(db, user, attempt_id)
    section = _get_section(db, attempt.id, section_name)
    if section.status == "submitted":
        return {
            "attempt_id": attempt.id,
            "section": section.section,
            "status": attempt.status,
            "score": section.score,
            "total": section.total,
        }
    if section.status != "active":
        raise AppError(409, "SECTION_NOT_ACTIVE", "section 尚未开始")
    if _pause_row(db, attempt.id, section.section):
        raise AppError(409, "SECTION_PAUSED", "考试已暂停，请继续考试后再交卷")

    now = utcnow()
    if section_name == "mcq":
        qrows = _questions(db, attempt.id, "mcq")
        ids = [q.question_id for q in qrows]
        questions = store.get_questions(ids, include_answers=True)
        answers = _answers(db, attempt.id)
        score = 0
        for qid in ids:
            answer = answers.get(qid)
            q = questions.get(qid)
            if not answer or not q or answer.selected_label is None:
                continue
            correct = bool(answer.selected_label == q.get("correct_label"))
            answer.is_correct = correct
            if correct:
                score += 1
            record_answer(db, store, user.id, qid, correct)

        section.status = "submitted"
        section.submitted_at = now
        section.finalized_reason = "timeout" if auto else "manual"
        section.score = score
        section.total = len(ids)
        attempt.mcq_score = score
        attempt.mcq_total = len(ids)
        if attempt.mode == "full":
            attempt.status = "in_progress"
            attempt.current_section = "frq"
            db.commit()
            return {
                "attempt_id": attempt.id,
                "section": "mcq",
                "status": attempt.status,
                "score": score,
                "total": len(ids),
                "next_section": "frq",
                "can_start": True,
            }
        attempt.status = "submitted"
        attempt.submitted_at = now
        db.commit()
        return {
            "attempt_id": attempt.id,
            "section": "mcq",
            "status": attempt.status,
            "score": score,
            "total": len(ids),
        }

    if section_name == "frq":
        qrows = _questions(db, attempt.id, "frq")
        section.status = "submitted"
        section.submitted_at = now
        section.finalized_reason = "timeout" if auto else "manual"
        section.total = attempt.frq_total
        attempt.status = "awaiting_self_grade"
        attempt.submitted_at = now
        db.commit()
        return {
            "attempt_id": attempt.id,
            "section": "frq",
            "status": attempt.status,
            "score": None,
            "total": attempt.frq_total,
            "questions": len(qrows),
            "self_grade_required": True,
        }

    raise AppError(400, "SECTION_INVALID", "section 不正确")


def review_attempt(db: Session, store: ContentStore, user: User, attempt_id: str) -> dict[str, Any]:
    attempt = _get_attempt(db, user, attempt_id)
    if attempt.status not in ("submitted", "graded", "awaiting_self_grade", "abandoned"):
        raise AppError(409, "REVIEW_LOCKED", "交卷后才能看解析")

    answers = _answers(db, attempt.id)
    mcq_items: list[dict[str, Any]] = []
    frq_items: list[dict[str, Any]] = []

    if attempt.mode in ("mcq", "full"):
        mcq_section = _get_section(db, attempt.id, "mcq")
        if mcq_section.status == "submitted":
            qrows = _questions(db, attempt.id, "mcq")
            ids = [q.question_id for q in qrows]
            display = {q.question_id: q.display_number for q in qrows}
            questions = store.get_questions(ids, include_answers=True, display_numbers=display)
            for qid in ids:
                q = questions.get(qid)
                if not q:
                    continue
                a = answers.get(qid)
                item = dict(q)
                item["selected_label"] = a.selected_label if a else None
                if a and a.is_correct is not None:
                    item["is_correct"] = a.is_correct
                elif a and a.selected_label and q.get("correct_label"):
                    item["is_correct"] = a.selected_label == q["correct_label"]
                else:
                    item["is_correct"] = None
                item["flagged"] = a.flagged if a else False
                item["answered_at"] = a.server_saved_at if a and a.selected_label else None
                item["feedback"] = store.get_feedback(qid)
                mcq_items.append(item)

    if attempt.mode in ("frq", "full"):
        frq_section = _get_section(db, attempt.id, "frq")
        if frq_section.status == "submitted":
            qrows = _questions(db, attempt.id, "frq")
            ids = [q.question_id for q in qrows]
            display = {q.question_id: q.display_number for q in qrows}
            questions = store.get_questions(ids, include_answers=True, display_numbers=display)
            scores = {
                (s.question_id, s.part_id): s
                for s in db.scalars(
                    select(AttemptFrqScore).where(AttemptFrqScore.attempt_id == attempt.id)
                )
            }
            for qid in ids:
                q = questions.get(qid)
                if not q:
                    continue
                a = answers.get(qid)
                item = dict(q)
                item["frq_text"] = a.frq_text if a else ""
                item["answered_at"] = a.server_saved_at if a and a.frq_text else None
                guidelines = store.get_frq_guidelines(qid)
                item["guidelines"] = guidelines
                item["scores"] = [
                    {
                        "part_id": s.part_id,
                        "points": s.points,
                        "max_points": s.max_points,
                    }
                    for (sqid, _), s in scores.items()
                    if sqid == qid
                ]
                frq_items.append(item)

    return {
        "attempt": {
            "id": attempt.id,
            "paper_id": attempt.paper_id,
            "mode": attempt.mode,
            "status": attempt.status,
            "frq_form": attempt.frq_form,
            "mcq_score": attempt.mcq_score,
            "mcq_total": attempt.mcq_total,
            "frq_score": attempt.frq_score,
            "frq_total": attempt.frq_total,
        },
        "mcq_items": mcq_items,
        "frq_items": frq_items,
        "score": attempt.mcq_score,
        "total": attempt.mcq_total,
    }


def save_frq_scores(
    db: Session,
    store: ContentStore,
    user: User,
    attempt_id: str,
    scores: list[FrqScoreItem],
) -> dict[str, Any]:
    attempt = _get_attempt(db, user, attempt_id)
    if attempt.status == "abandoned":
        raise AppError(409, "ATTEMPT_ABANDONED", "这场考试已中途结束，不能再自评")
    if attempt.mode not in ("frq", "full"):
        raise AppError(400, "FRQ_NOT_AVAILABLE", "这不是 FRQ 考试")
    section = _get_section(db, attempt.id, "frq")
    if section.status != "submitted":
        raise AppError(409, "FRQ_NOT_SUBMITTED", "FRQ 交卷后才能自评")
    qrows = _questions(db, attempt.id, "frq")
    ids = [q.question_id for q in qrows]
    allowed: dict[str, dict[str, int]] = {}
    expected_total = 0
    for qid in ids:
        guidelines = store.get_frq_guidelines(qid)
        parts = {p["part_id"]: int(p["max_points"] or 0) for p in guidelines.get("parts", [])}
        allowed[qid] = parts
        expected_total += sum(parts.values())

    for item in scores:
        if item.question_id not in allowed:
            raise AppError(400, "QUESTION_NOT_IN_ATTEMPT", "题目不在本次考试中")
        max_points = allowed[item.question_id].get(item.part_id)
        if max_points is None:
            raise AppError(400, "PART_INVALID", "评分点不存在")
        if item.points < 0 or item.points > max_points:
            raise AppError(400, "SCORE_INVALID", f"分数必须在 0..{max_points}")
        row = db.get(AttemptFrqScore, (attempt.id, item.question_id, item.part_id))
        if not row:
            row = AttemptFrqScore(
                attempt_id=attempt.id,
                question_id=item.question_id,
                part_id=item.part_id,
                points=0,
                max_points=max_points,
            )
            db.add(row)
        row.points = item.points
        row.max_points = max_points

    db.flush()
    existing = {
        (s.question_id, s.part_id): s
        for s in db.scalars(select(AttemptFrqScore).where(AttemptFrqScore.attempt_id == attempt.id))
    }
    missing = 0
    total = 0
    for qid, parts in allowed.items():
        for part_id, max_points in parts.items():
            row = existing.get((qid, part_id))
            if row is None:
                missing += 1
            else:
                total += row.points
    attempt.frq_score = total
    attempt.frq_total = expected_total
    section.score = total
    section.total = expected_total
    if missing == 0 and expected_total > 0:
        attempt.status = "graded"
    else:
        attempt.status = "awaiting_self_grade"
    db.commit()
    return {
        "attempt_id": attempt.id,
        "frq_score": total,
        "frq_total": expected_total,
        "graded": attempt.status == "graded",
        "missing_parts": missing,
    }


def abandon_attempt(db: Session, user: User, attempt_id: str) -> dict[str, Any]:
    attempt = _get_attempt(db, user, attempt_id)
    _abandon(db, attempt)
    db.commit()
    return {"attempt": {"id": attempt.id, "status": attempt.status}}
