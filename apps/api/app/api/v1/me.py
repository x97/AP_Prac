from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.api.v1.schemas import (
    ActivationCodeRedeem,
    EmailBindCodeRequest,
    EmailBindRequest,
    NotePatchRequest,
    NoteUpsertRequest,
    PasswordChangeRequest,
    QuestionReportRequest,
    UserProfilePatch,
)
from app.content.store import ContentStore
from app.core.config import get_settings
from app.core.db import get_db
from app.core.deps import get_current_user, get_store
from app.core.errors import AppError
from app.core.security import (
    client_ip,
    hash_password,
    hash_token,
    normalize_email,
    request_token,
    resolve_merged_user,
    revoke_user_sessions,
    validate_password,
    verify_password,
)
from app.core.time import utcnow
from app.services import (
    account_merge,
    activation_codes,
    entitlements,
    progress,
    verification_codes,
)
from app.users.models import (
    Attempt,
    AttemptQuestion,
    Bookmark,
    Note,
    PracticeSession,
    PracticeSessionQuestion,
    QuestionReport,
    User,
    UserIdentity,
    WrongQuestion,
)
from app.users.payload import user_payload

settings = get_settings()

router = APIRouter(tags=["me"])


def _find_email_owner(db: Session, email: str) -> Optional[User]:
    return db.scalar(select(User).where(User.email == email))


def _has_wechat_identity(db: Session, user_id: str) -> bool:
    count = (
        db.scalar(
            select(func.count())
            .select_from(UserIdentity)
            .where(
                UserIdentity.user_id == user_id,
                UserIdentity.provider == "wechat_mini",
            )
        )
        or 0
    )
    return count > 0


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"user": user_payload(user)}


@router.post("/me/email/code")
def send_bind_email_code(
    body: EmailBindCodeRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.email:
        raise AppError(409, "EMAIL_ALREADY_BOUND", "当前账号已绑定邮箱")
    email = normalize_email(body.email)
    target = _find_email_owner(db, email)
    if target:
        target = resolve_merged_user(db, target) or target
        if target.id != user.id:
            if target.status != "active":
                raise AppError(409, "EMAIL_ACCOUNT_UNAVAILABLE", "该邮箱账号不可用，请联系客服")
            if _has_wechat_identity(db, target.id):
                raise AppError(
                    409,
                    "EMAIL_BOUND_TO_OTHER_WECHAT",
                    "该邮箱已绑定其他微信，请使用邮箱登录",
                )
    return verification_codes.issue_code(
        db,
        identifier=email,
        purpose="bind_email",
        ip=client_ip(request),
        settings=settings,
    )


@router.post("/me/email/bind")
def bind_email(
    body: EmailBindRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    email = normalize_email(body.email)
    if user.email:
        if user.email == email:
            return {"user": user_payload(user), "merged": False}
        raise AppError(
            409, "EMAIL_ALREADY_BOUND", "当前账号已绑定其他邮箱，暂不支持直接换绑"
        )

    target = _find_email_owner(db, email)
    if target:
        target = resolve_merged_user(db, target) or target
        if target.id != user.id and target.status != "active":
            raise AppError(409, "EMAIL_ACCOUNT_UNAVAILABLE", "该邮箱账号不可用，请联系客服")
        if target.id != user.id and _has_wechat_identity(db, target.id):
            raise AppError(
                409,
                "EMAIL_BOUND_TO_OTHER_WECHAT",
                "该邮箱已绑定其他微信，请使用邮箱登录",
            )
    elif not body.password:
        raise AppError(400, "PASSWORD_REQUIRED", "首次绑定邮箱需要设置密码")
    if body.password:
        validate_password(body.password, settings)

    verification_codes.verify_code(
        db,
        identifier=email,
        purpose="bind_email",
        code=body.code,
        settings=settings,
    )

    # Re-read after verification so a concurrent registration cannot be missed.
    current = _find_email_owner(db, email)
    if current:
        current = resolve_merged_user(db, current) or current
        if current.id == user.id:
            db.commit()
            return {"user": user_payload(user), "merged": False}
        if current.status != "active":
            db.rollback()
            raise AppError(409, "EMAIL_ACCOUNT_UNAVAILABLE", "该邮箱账号不可用，请联系客服")
        if _has_wechat_identity(db, current.id):
            db.rollback()
            raise AppError(
                409,
                "EMAIL_BOUND_TO_OTHER_WECHAT",
                "该邮箱已绑定其他微信，请使用邮箱登录",
            )
        counts = account_merge.merge_users(db, user, current)
        db.commit()
        return {
            "user": user_payload(current),
            "merged": True,
            "merge_counts": counts,
        }

    user.email = email
    user.email_verified_at = utcnow()
    user.password_hash = hash_password(body.password) if body.password else None
    user.password_changed_at = utcnow() if body.password else None
    db.commit()
    db.refresh(user)
    return {"user": user_payload(user), "merged": False}


@router.post("/me/password")
def change_password(
    body: PasswordChangeRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not user.password_hash:
        raise AppError(
            400,
            "PASSWORD_NOT_SET",
            "当前账号尚未设置密码，请先绑定邮箱后再修改密码",
        )
    if not verify_password(body.old_password, user.password_hash):
        raise AppError(400, "OLD_PASSWORD_INVALID", "原密码不正确")
    validate_password(body.new_password, settings)
    user.password_hash = hash_password(body.new_password)
    user.password_changed_at = utcnow()
    token = request_token(request)
    revoke_user_sessions(db, user.id, hash_token(token) if token else None)
    db.commit()
    return {"ok": True}


@router.get("/me/entitlements")
def my_entitlements(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    items = entitlements.entitlement_payload(db, user.id)
    return {
        "entitlements": items,
        "active_count": sum(1 for item in items if item.get("active")),
    }


@router.post("/me/activation-codes/redeem")
def redeem_activation_code(
    body: ActivationCodeRedeem,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = activation_codes.redeem(db, user, body.code)
    items = entitlements.entitlement_payload(db, user.id)
    result["entitlements"] = items
    result["active_count"] = sum(1 for item in items if item.get("active"))
    return result


@router.patch("/me")
def update_me(
    body: UserProfilePatch,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    nickname = body.nickname.strip()
    if not nickname:
        raise AppError(400, "NICKNAME_REQUIRED", "昵称不能为空")
    if any(char in nickname for char in "\r\n\t"):
        raise AppError(400, "NICKNAME_INVALID", "昵称不能包含换行或制表符")
    user.nickname = nickname
    db.commit()
    db.refresh(user)
    return {"user": user_payload(user)}


@router.get("/me/dashboard")
def dashboard(
    db: Session = Depends(get_db),
    store: ContentStore = Depends(get_store),
    user: User = Depends(get_current_user),
):
    data = progress.dashboard(db, store, user.id)
    entitlements.mark_locked_groups(db, user.id, store.subject_id, data["units"])
    data["user"] = user_payload(user)
    total_questions = sum(u.get("total", 0) for u in data["units"])
    data["overview"]["total_questions"] = total_questions
    return data


@router.get("/me/progress")
def my_progress(
    db: Session = Depends(get_db),
    store: ContentStore = Depends(get_store),
    user: User = Depends(get_current_user),
):
    units = progress.unit_progress(db, store, user.id)
    entitlements.mark_locked_groups(db, user.id, store.subject_id, units)
    return {
        "overview": {
            "total_questions": sum(u.get("total", 0) for u in units),
            "answered": sum(u.get("answered", 0) for u in units),
            "correct": sum(u.get("correct", 0) for u in units),
            "streak_days": progress.streak_days(db, user.id),
        },
        "units": units,
    }


def _session_counts(db: Session, session_ids: list[str]) -> dict[str, dict[str, int]]:
    if not session_ids:
        return {}
    rows = db.execute(
        select(
            PracticeSessionQuestion.session_id,
            func.count(),
            func.count(PracticeSessionQuestion.answered_at),
            func.sum(case((PracticeSessionQuestion.is_correct.is_(True), 1), else_=0)),
        )
        .where(PracticeSessionQuestion.session_id.in_(session_ids))
        .group_by(PracticeSessionQuestion.session_id)
    ).all()
    return {
        row[0]: {
            "total_questions": int(row[1] or 0),
            "answered": int(row[2] or 0),
            "correct": int(row[3] or 0),
        }
        for row in rows
    }


@router.get("/me/practice-sessions")
def practice_sessions(
    group_id: Optional[str] = None,
    topic_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    store: ContentStore = Depends(get_store),
    user: User = Depends(get_current_user),
):
    stmt = select(PracticeSession).where(PracticeSession.user_id == user.id)
    if group_id:
        stmt = stmt.where(PracticeSession.group_id == group_id)
    if topic_id:
        stmt = stmt.where(PracticeSession.topic_id == topic_id)
    if status:
        stmt = stmt.where(PracticeSession.status == status)
    rows = list(db.scalars(stmt.order_by(PracticeSession.created_at.desc()).limit(limit)))
    counts = _session_counts(db, [r.id for r in rows])
    group_cache: dict[str, Optional[dict]] = {}
    topic_cache: dict[str, Optional[dict]] = {}
    out = []
    for r in rows:
        if r.group_id and r.group_id not in group_cache:
            group_cache[r.group_id] = store.get_group(r.group_id)
        if r.topic_id and r.topic_id not in topic_cache:
            topic_cache[r.topic_id] = store.get_topic(r.topic_id)
        group = group_cache.get(r.group_id or "")
        topic = topic_cache.get(r.topic_id or "")
        stat = counts.get(r.id, {})
        answered = int(stat.get("answered") or 0)
        correct = int(stat.get("correct") or 0)
        out.append(
            {
                "id": r.id,
                "source": r.source,
                "group_id": r.group_id,
                "topic_id": r.topic_id,
                "status": r.status,
                "score": r.score,
                "total": r.total,
                "total_questions": int(stat.get("total_questions") or r.total or 0),
                "answered": answered,
                "correct": correct,
                "accuracy": round(correct / answered, 3) if answered else None,
                "group_title": group.get("title") if group else None,
                "group_title_en": group.get("title_en") if group else None,
                "topic_title_zh": topic.get("title_zh") if topic else None,
                "topic_title_en": topic.get("title_en") if topic else None,
                "topic_code": topic.get("code") if topic else None,
                "started_at": r.started_at,
                "submitted_at": r.submitted_at,
                "created_at": r.created_at,
                "updated_at": r.updated_at,
            }
        )
    return out


@router.get("/me/attempts")
def attempts(
    paper_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    store: ContentStore = Depends(get_store),
    user: User = Depends(get_current_user),
):
    from app.services.exam_engine import finalize_expired_for_user

    finalize_expired_for_user(db, store, user.id)
    stmt = select(Attempt).where(Attempt.user_id == user.id)
    if paper_id:
        stmt = stmt.where(Attempt.paper_id == paper_id)
    if status:
        stmt = stmt.where(Attempt.status == status)
    rows = list(db.scalars(stmt.order_by(Attempt.created_at.desc()).limit(limit)))
    paper_cache: dict[str, Optional[dict]] = {}
    out = []
    for r in rows:
        if r.paper_id not in paper_cache:
            paper_cache[r.paper_id] = store.get_paper(r.paper_id)
        paper = paper_cache[r.paper_id] or {}
        out.append(
            {
                "id": r.id,
                "paper_id": r.paper_id,
                "mode": r.mode,
                "frq_form": r.frq_form,
                "status": r.status,
                "current_section": r.current_section,
                "mcq_score": r.mcq_score,
                "mcq_total": r.mcq_total,
                "frq_score": r.frq_score,
                "frq_total": r.frq_total,
                "paper_title": paper.get("title") or paper.get("chinese_title"),
                "paper_title_en": paper.get("title"),
                "paper_year": paper.get("year"),
                "paper_type": paper.get("paper_type"),
                "started_at": r.started_at,
                "submitted_at": r.submitted_at,
                "created_at": r.created_at,
                "updated_at": r.updated_at,
            }
        )
    return out


def _ensure_question_viewable(db: Session, user_id: str, question_id: str) -> None:
    locked = (
        db.scalar(
            select(func.count())
            .select_from(AttemptQuestion)
            .join(Attempt, Attempt.id == AttemptQuestion.attempt_id)
            .where(
                Attempt.user_id == user_id,
                Attempt.status == "in_progress",
                AttemptQuestion.question_id == question_id,
            )
        )
        or 0
    )
    if locked:
        raise AppError(409, "QUESTION_LOCKED", "考试进行中，交卷后才能查看解析")


def _question_summaries(store: ContentStore, ids: list[str]) -> dict[str, dict]:
    questions = store.get_questions(ids, include_answers=False)
    contexts = store.question_contexts(list(questions.keys()))
    paper_cache: dict[str, Optional[dict]] = {}
    group_cache: dict[str, Optional[dict]] = {}
    out = {}
    for qid, q in questions.items():
        paper_id = q["paper_id"]
        if paper_id not in paper_cache:
            paper_cache[paper_id] = store.get_paper(paper_id)
        paper = paper_cache[paper_id] or {}
        context = contexts.get(qid, {})
        group_id = context.get("group_id")
        if group_id and group_id not in group_cache:
            group_cache[group_id] = store.get_group(group_id)
        group = group_cache.get(group_id or "")
        out[qid] = {
            "question_id": qid,
            "paper_id": paper_id,
            "paper_title": paper.get("title") or paper.get("chinese_title"),
            "paper_title_en": paper.get("title"),
            "paper_type": paper.get("paper_type"),
            "paper_year": paper.get("year"),
            "section": q["section"],
            "display_number": q["display_number"],
            "stem": q["stem"],
            "unit_id": context.get("unit_id"),
            "topic_id": context.get("topic_id"),
            "topic_code": context.get("code"),
            "topic_title_zh": context.get("title_zh"),
            "topic_title_en": context.get("title_en"),
            "group_id": group_id,
            "group_title": group.get("title") if group else None,
            "group_title_en": group.get("title_en") if group else None,
        }
    return out


@router.get("/me/questions/{question_id}")
def question_detail(
    question_id: str,
    db: Session = Depends(get_db),
    store: ContentStore = Depends(get_store),
    user: User = Depends(get_current_user),
):
    _ensure_question_viewable(db, user.id, question_id)
    try:
        return store.get_feedback(question_id)
    except KeyError:
        raise AppError(404, "QUESTION_NOT_FOUND", "题目不存在")


@router.get("/me/wrong-questions")
def wrong_questions(
    mastery: Optional[str] = None,
    unit_id: Optional[str] = None,
    topic_id: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    store: ContentStore = Depends(get_store),
    user: User = Depends(get_current_user),
):
    stmt = select(WrongQuestion).where(WrongQuestion.user_id == user.id)
    if mastery:
        stmt = stmt.where(WrongQuestion.mastery == mastery)
    if unit_id:
        stmt = stmt.where(WrongQuestion.unit_id == unit_id)
    if topic_id:
        stmt = stmt.where(WrongQuestion.primary_topic_id == topic_id)
    rows = list(db.scalars(stmt.order_by(WrongQuestion.last_wrong_at.desc()).limit(limit)))
    summaries = _question_summaries(store, [r.question_id for r in rows])
    out = []
    for r in rows:
        item = {
            "question_id": r.question_id,
            "wrong_count": r.wrong_count,
            "correct_streak": r.correct_streak,
            "mastery": r.mastery,
            "last_wrong_at": r.last_wrong_at,
            "mastered_at": r.mastered_at,
            "unit_id": r.unit_id,
            "topic_id": r.primary_topic_id,
        }
        item.update(summaries.get(r.question_id, {}))
        out.append(item)
    return out


@router.get("/me/wrong-questions/summary")
def wrong_question_summary(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = db.execute(
        select(WrongQuestion.mastery, func.count())
        .where(WrongQuestion.user_id == user.id)
        .group_by(WrongQuestion.mastery)
    ).all()
    counts = {"learning": 0, "reviewing": 0, "mastered": 0}
    for mastery, count in rows:
        counts[mastery] = int(count)
    active = counts["learning"] + counts["reviewing"]
    return {
        **counts,
        "active": active,
        "all": active + counts["mastered"],
    }


@router.get("/me/wrong-questions/{question_id}")
def wrong_question_detail(
    question_id: str,
    db: Session = Depends(get_db),
    store: ContentStore = Depends(get_store),
    user: User = Depends(get_current_user),
):
    row = db.get(WrongQuestion, (user.id, question_id))
    if not row:
        raise AppError(404, "WRONG_QUESTION_NOT_FOUND", "错题不存在")
    _ensure_question_viewable(db, user.id, question_id)
    feedback = store.get_feedback(question_id)
    return {
        "question_id": question_id,
        "wrong_count": row.wrong_count,
        "correct_streak": row.correct_streak,
        "mastery": row.mastery,
        "last_wrong_at": row.last_wrong_at,
        "mastered_at": row.mastered_at,
        "unit_id": row.unit_id,
        "topic_id": row.primary_topic_id,
        "question": feedback,
    }


@router.post("/me/wrong-questions/{question_id}/master")
def master_wrong_question(
    question_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = db.get(WrongQuestion, (user.id, question_id))
    if not row:
        raise AppError(404, "WRONG_QUESTION_NOT_FOUND", "错题不存在")
    row.mastery = "mastered"
    row.correct_streak = max(row.correct_streak, 2)
    row.mastered_at = utcnow()
    db.commit()
    return {"question_id": question_id, "mastery": row.mastery}


@router.post("/me/wrong-questions/{question_id}/unmaster")
def unmaster_wrong_question(
    question_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = db.get(WrongQuestion, (user.id, question_id))
    if not row:
        raise AppError(404, "WRONG_QUESTION_NOT_FOUND", "错题不存在")
    row.mastery = "learning"
    row.correct_streak = 0
    row.mastered_at = None
    row.updated_at = utcnow()
    db.commit()
    return {"question_id": question_id, "mastery": row.mastery}


@router.get("/me/bookmarks")
def bookmarks(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    store: ContentStore = Depends(get_store),
    user: User = Depends(get_current_user),
):
    rows = list(
        db.scalars(
            select(Bookmark)
            .where(Bookmark.user_id == user.id)
            .order_by(Bookmark.created_at.desc())
            .limit(limit)
        )
    )
    summaries = _question_summaries(store, [r.question_id for r in rows])
    out = []
    for r in rows:
        item = {"question_id": r.question_id, "created_at": r.created_at}
        item.update(summaries.get(r.question_id, {}))
        out.append(item)
    return out


@router.put("/me/bookmarks/{question_id}")
def add_bookmark(
    question_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = db.get(Bookmark, (user.id, question_id))
    if not row:
        db.add(Bookmark(user_id=user.id, question_id=question_id))
        db.commit()
    return {"question_id": question_id, "bookmarked": True}


@router.delete("/me/bookmarks/{question_id}")
def remove_bookmark(
    question_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = db.get(Bookmark, (user.id, question_id))
    if row:
        db.delete(row)
        db.commit()
    return {"question_id": question_id, "bookmarked": False}


@router.get("/me/notes")
def notes(
    target_type: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    store: ContentStore = Depends(get_store),
    user: User = Depends(get_current_user),
):
    stmt = select(Note).where(Note.user_id == user.id)
    if target_type:
        stmt = stmt.where(Note.target_type == target_type)
    if q:
        stmt = stmt.where(Note.content.ilike(f"%{q}%"))
    rows = list(db.scalars(stmt.order_by(Note.updated_at.desc()).limit(limit)))
    question_ids = [n.target_id for n in rows if n.target_type == "question"]
    summaries = _question_summaries(store, question_ids)
    out = []
    for n in rows:
        item = {
            "id": n.id,
            "target_type": n.target_type,
            "target_id": n.target_id,
            "content": n.content,
            "created_at": n.created_at,
            "updated_at": n.updated_at,
        }
        if n.target_type == "question":
            item["question"] = summaries.get(n.target_id)
        out.append(item)
    return out


@router.post("/me/notes")
def upsert_note(
    body: NoteUpsertRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    note = db.scalar(
        select(Note).where(
            Note.user_id == user.id,
            Note.target_type == body.target_type,
            Note.target_id == body.target_id,
        )
    )
    if note:
        note.content = body.content
    else:
        note = Note(
            user_id=user.id,
            target_type=body.target_type,
            target_id=body.target_id,
            content=body.content,
        )
        db.add(note)
    db.commit()
    db.refresh(note)
    return {
        "id": note.id,
        "target_type": note.target_type,
        "target_id": note.target_id,
        "content": note.content,
        "updated_at": note.updated_at,
    }


@router.patch("/me/notes/{note_id}")
def patch_note(
    note_id: str,
    body: NotePatchRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    note = db.get(Note, note_id)
    if not note or note.user_id != user.id:
        raise AppError(404, "NOTE_NOT_FOUND", "笔记不存在")
    note.content = body.content
    db.commit()
    return {"id": note.id, "content": note.content, "updated_at": note.updated_at}


@router.delete("/me/notes/{note_id}")
def delete_note(
    note_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    note = db.get(Note, note_id)
    if not note or note.user_id != user.id:
        raise AppError(404, "NOTE_NOT_FOUND", "笔记不存在")
    db.delete(note)
    db.commit()
    return {"ok": True}


@router.post("/question-reports")
def create_report(
    body: QuestionReportRequest,
    db: Session = Depends(get_db),
    store: ContentStore = Depends(get_store),
    user: User = Depends(get_current_user),
):
    if body.attempt_id:
        attempt = db.get(Attempt, body.attempt_id)
        if not attempt or attempt.user_id != user.id:
            raise AppError(404, "ATTEMPT_NOT_FOUND", "考试记录不存在")
    if body.practice_session_id:
        session = db.get(PracticeSession, body.practice_session_id)
        if not session or session.user_id != user.id:
            raise AppError(404, "PRACTICE_SESSION_NOT_FOUND", "练习记录不存在")
    report = QuestionReport(
        user_id=user.id,
        question_id=body.question_id,
        attempt_id=body.attempt_id,
        practice_session_id=body.practice_session_id,
        selected_label=body.selected_label,
        content_release_id=store.release_id,
        reason=body.reason,
        detail=body.detail,
    )
    db.add(report)
    db.commit()
    return {"id": report.id, "status": report.status}
