from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional
from urllib.parse import quote

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Query,
    Request,
    Response,
    UploadFile,
)
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from app.api.v1.schemas import (
    ActivationCodeBatchCreate,
    AdminConceptCreate,
    AdminLoginRequest,
    AdminQuestionConceptLinkCreate,
    AdminQuestionCreate,
    AdminStudentPatch,
    ConceptPatch,
    KnowledgePointPatch,
    PaperPatch,
    QuestionNotePatch,
    QuestionPatch,
    QuestionReportUpdate,
    QuestionStarsPatch,
)
from app.content.store import ContentStore
from app.core.admin_deps import get_current_admin, require_admin_roles
from app.core.config import REPO_ROOT, get_settings
from app.core.db import get_db
from app.core.deps import get_store
from app.core.errors import AppError
from app.core.security import hash_token, mask_email, mask_phone, verify_password
from app.core.time import utcnow
from app.services import (
    activation_codes,
    admin_content,
    admin_content_edits,
    progress,
    self_question_import,
    subject_catalog,
)
from app.services.admin_auth import (
    admin_payload,
    clear_admin_cookie,
    create_admin_session,
    record_audit,
    set_admin_cookie,
)
from app.services.effective_content import ensure_effective_content
from app.services.self_question_import import ImportValidationError
from app.services.self_question_workbook import read_questions, write_template
from app.users.models import (
    ActivationCode,
    ActivationCodeBatch,
    AdminAuditLog,
    AdminSession,
    AdminUser,
    Attempt,
    ContentActiveRelease,
    ContentRelease,
    PracticeSession,
    PracticeSessionQuestion,
    QuestionAdminNote,
    QuestionReport,
    QuestionStar,
    ReleaseJob,
    StudyPlanAssignment,
    User,
    UserQuestionStat,
    WrongQuestion,
)

router = APIRouter(prefix="/admin", tags=["admin"])
settings = get_settings()


@router.post("/auth/login")
def admin_login(
    body: AdminLoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    identifier = body.identifier.strip()
    admin = db.scalar(
        select(AdminUser).where(
            or_(
                func.lower(AdminUser.username) == identifier.lower(),
                func.lower(AdminUser.email) == identifier.lower(),
            )
        )
    )
    if (
        not admin
        or admin.status != "active"
        or not verify_password(body.password, admin.password_hash)
    ):
        raise AppError(401, "ADMIN_LOGIN_FAILED", "管理员账号或密码不正确")
    token = create_admin_session(db, admin, request, settings)
    record_audit(
        db,
        admin,
        "admin.login",
        target_type="admin",
        target_id=admin.id,
        request=request,
    )
    db.commit()
    set_admin_cookie(response, token, settings)
    return {"admin": admin_payload(admin)}


@router.post("/auth/logout")
def admin_logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    token = request.cookies.get(settings.admin_cookie_name)
    if token:
        session = db.scalar(
            select(AdminSession).where(AdminSession.token_hash == hash_token(token))
        )
        if session:
            db.delete(session)
            db.commit()
    clear_admin_cookie(response, settings)
    return {"ok": True}


@router.get("/auth/me")
def admin_me(admin: AdminUser = Depends(get_current_admin)):
    return {"admin": admin_payload(admin)}


@router.get("/dashboard")
def admin_dashboard(
    db: Session = Depends(get_db),
    store: ContentStore = Depends(get_store),
    admin: AdminUser = Depends(get_current_admin),
):
    now = utcnow()
    week_ago = now - timedelta(days=7)
    student_count = db.scalar(select(func.count()).select_from(User)) or 0
    active_students = (
        db.scalar(
            select(func.count(func.distinct(UserQuestionStat.user_id))).where(
                UserQuestionStat.last_answered_at >= week_ago
            )
        )
        or 0
    )
    practice_count = db.scalar(select(func.count()).select_from(PracticeSession)) or 0
    attempt_count = db.scalar(select(func.count()).select_from(Attempt)) or 0
    wrong_active = (
        db.scalar(
            select(func.count())
            .select_from(WrongQuestion)
            .where(WrongQuestion.mastery.in_(["learning", "reviewing"]))
        )
        or 0
    )
    open_reports = (
        db.scalar(
            select(func.count()).select_from(QuestionReport).where(QuestionReport.status == "open")
        )
        or 0
    )

    recent_attempts = []
    for row in db.scalars(select(Attempt).order_by(Attempt.created_at.desc()).limit(5)):
        paper = store.get_paper(row.paper_id) or {}
        recent_attempts.append(
            {
                "id": row.id,
                "paper_id": row.paper_id,
                "paper_title": paper.get("title") or row.paper_id,
                "mode": row.mode,
                "status": row.status,
                "mcq_score": row.mcq_score,
                "mcq_total": row.mcq_total,
                "created_at": row.created_at,
            }
        )

    recent_practice = []
    for row in db.scalars(
        select(PracticeSession).order_by(PracticeSession.created_at.desc()).limit(5)
    ):
        group = store.get_group(row.group_id) if row.group_id else None
        topic = store.get_topic(row.topic_id) if row.topic_id else None
        recent_practice.append(
            {
                "id": row.id,
                "source": row.source,
                "status": row.status,
                "group_title": group.get("title_en") if group else None,
                "topic_title": topic.get("title_en") if topic else None,
                "created_at": row.created_at,
            }
        )

    return {
        "admin": admin_payload(admin),
        "release": store.version(),
        "stats": {
            "students": student_count,
            "active_students_7d": active_students,
            "practice_sessions": practice_count,
            "attempts": attempt_count,
            "wrong_active": wrong_active,
            "open_reports": open_reports,
        },
        "recent_attempts": recent_attempts,
        "recent_practice": recent_practice,
    }


def _question_report_payload(
    report: QuestionReport,
    user: Optional[User],
    question: Optional[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "id": report.id,
        "question_id": report.question_id,
        "reason": report.reason,
        "detail": report.detail,
        "selected_label": report.selected_label,
        "status": report.status,
        "created_at": report.created_at,
        "resolved_at": report.resolved_at,
        "content_release_id": report.content_release_id,
        "attempt_id": report.attempt_id,
        "practice_session_id": report.practice_session_id,
        "reporter": {
            "nickname": user.nickname if user else None,
            "email_masked": mask_email(user.email) if user and user.email else None,
            "phone_masked": mask_phone(user.phone) if user and user.phone else None,
        },
        "question": question,
    }


def _question_report_question(
    db: Session, subject_id: str, question_id: str
) -> Optional[dict[str, Any]]:
    detail = admin_content.get_question(question_id, subject_id=subject_id)
    if not detail:
        return None
    return {
        "question_id": detail["question_id"],
        "paper_id": detail["paper_id"],
        "section": detail["section"],
        "number": detail["number"],
        "stem": detail["stem"],
        "correct_answer": detail.get("correct_answer"),
        "answer_text": detail.get("answer_text"),
        "options": [
            {
                "label": option.get("label"),
                "content": option.get("content"),
                "is_correct": bool(option.get("is_correct")),
            }
            for option in detail.get("options") or []
        ],
    }


@router.get("/question-reports")
def admin_question_reports(
    status: str = "open",
    q: Optional[str] = None,
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    subject: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    subject_id = _admin_subject(subject)
    _prepare_admin_content(db, subject_id)
    status_value = (status or "open").strip().lower()
    if status_value not in ("open", "done", "all"):
        raise AppError(400, "REPORT_STATUS_INVALID", "报错状态筛选不合法")

    clauses = []
    if status_value == "open":
        clauses.append(QuestionReport.status == "open")
    elif status_value == "done":
        clauses.append(QuestionReport.status.in_(["resolved", "ignored"]))

    needle = (q or "").strip()
    if needle:
        like = f"%{needle}%"
        clauses.append(
            or_(
                QuestionReport.question_id.ilike(like),
                QuestionReport.detail.ilike(like),
                User.email.ilike(like),
                User.nickname.ilike(like),
            )
        )

    stmt = (
        select(QuestionReport, User)
        .outerjoin(User, User.id == QuestionReport.user_id)
        .where(*clauses)
    )
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.execute(
        stmt.order_by(
            case((QuestionReport.status == "open", 0), else_=1),
            QuestionReport.created_at.desc(),
        )
        .limit(limit)
        .offset(offset)
    ).all()

    counts_rows = db.execute(
        select(QuestionReport.status, func.count()).group_by(
            QuestionReport.status
        )
    ).all()
    counts = {"open": 0, "resolved": 0, "ignored": 0}
    for key, count in counts_rows:
        counts[str(key)] = int(count)
    counts["total"] = counts["open"] + counts["resolved"] + counts["ignored"]

    reports = [
        _question_report_payload(
            report,
            user,
            _question_report_question(db, subject_id, report.question_id),
        )
        for report, user in rows
    ]
    return {
        "reports": reports,
        "total": int(total),
        "limit": limit,
        "offset": offset,
        "counts": counts,
    }


@router.patch("/question-reports/{report_id}")
def admin_update_question_report(
    report_id: str,
    body: QuestionReportUpdate,
    request: Request,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin_roles("super_admin", "content_editor")),
):
    report = db.get(QuestionReport, report_id)
    if not report:
        raise AppError(404, "REPORT_NOT_FOUND", "题目报错不存在")
    report.status = body.status
    report.resolved_at = utcnow() if body.status != "open" else None
    record_audit(
        db,
        admin,
        "content.question_report.update",
        target_type="question_report",
        target_id=report.id,
        detail={
            "question_id": report.question_id,
            "status": body.status,
        },
        request=request,
    )
    db.commit()
    return {
        "id": report.id,
        "status": report.status,
        "resolved_at": report.resolved_at,
    }


def _student_stats(db: Session, user_id: str) -> dict:
    row = db.execute(
        select(
            func.count(),
            func.sum(case((UserQuestionStat.last_is_correct.is_(True), 1), else_=0)),
            func.max(UserQuestionStat.last_answered_at),
        ).where(UserQuestionStat.user_id == user_id)
    ).one()
    practice_count = (
        db.scalar(
            select(func.count())
            .select_from(PracticeSession)
            .where(PracticeSession.user_id == user_id)
        )
        or 0
    )
    attempt_count = (
        db.scalar(select(func.count()).select_from(Attempt).where(Attempt.user_id == user_id)) or 0
    )
    answered = int(row[0] or 0)
    correct = int(row[1] or 0)
    return {
        "answered": answered,
        "correct": correct,
        "accuracy": round(correct / answered, 3) if answered else None,
        "practice_count": practice_count,
        "attempt_count": attempt_count,
        "last_answered_at": row[2],
    }


@router.get("/students")
def admin_students(
    q: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    stmt = select(User)
    count_stmt = select(func.count()).select_from(User)
    if q:
        pattern = f"%{q.strip()}%"
        condition = or_(
            User.email.ilike(pattern),
            User.phone.ilike(pattern),
            User.nickname.ilike(pattern),
        )
        stmt = stmt.where(condition)
        count_stmt = count_stmt.where(condition)
    total = db.scalar(count_stmt) or 0
    rows = list(db.scalars(stmt.order_by(User.created_at.desc()).limit(limit).offset(offset)))
    user_ids = [user.id for user in rows]
    active_plan_counts: dict[str, int] = {}
    latest_plan_titles: dict[str, str] = {}
    if user_ids:
        assignments = db.scalars(
            select(StudyPlanAssignment)
            .where(
                StudyPlanAssignment.user_id.in_(user_ids),
                StudyPlanAssignment.status == "active",
            )
            .order_by(StudyPlanAssignment.created_at.desc())
        ).all()
        for assignment in assignments:
            active_plan_counts[assignment.user_id] = (
                active_plan_counts.get(assignment.user_id, 0) + 1
            )
            latest_plan_titles.setdefault(assignment.user_id, assignment.plan_title)
    items = []
    for user in rows:
        stat = _student_stats(db, user.id)
        last_active = max(
            [value for value in (user.last_login_at, stat["last_answered_at"]) if value],
            default=None,
        )
        items.append(
            {
                "id": user.id,
                "email": user.email,
                "email_masked": mask_email(user.email),
                "phone_masked": mask_phone(user.phone),
                "nickname": user.nickname,
                "grade": user.grade,
                "region": user.region,
                "target_score": user.target_score,
                "studied_psychology": user.studied_psychology,
                "study_mode": user.study_mode,
                "exam_time": user.exam_time,
                "status": user.status,
                "created_at": user.created_at,
                "last_login_at": user.last_login_at,
                "last_active_at": last_active,
                "active_plan_count": active_plan_counts.get(user.id, 0),
                "latest_plan_title": latest_plan_titles.get(user.id),
                **stat,
            }
        )
    return {"students": items, "total": total, "limit": limit, "offset": offset}


def _session_stats(db: Session, session_id: str) -> dict:
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


@router.get("/students/{user_id}")
def admin_student_detail(
    user_id: str,
    db: Session = Depends(get_db),
    store: ContentStore = Depends(get_store),
    admin: AdminUser = Depends(get_current_admin),
):
    user = db.get(User, user_id)
    if not user:
        raise AppError(404, "STUDENT_NOT_FOUND", "学生不存在")

    dashboard = progress.dashboard(db, store, user.id)
    sessions = []
    for row in db.scalars(
        select(PracticeSession)
        .where(PracticeSession.user_id == user.id)
        .order_by(PracticeSession.created_at.desc())
        .limit(20)
    ):
        group = store.get_group(row.group_id) if row.group_id else None
        topic = store.get_topic(row.topic_id) if row.topic_id else None
        stat = _session_stats(db, row.id)
        sessions.append(
            {
                "id": row.id,
                "source": row.source,
                "status": row.status,
                "score": row.score,
                "group_title": group.get("title_en") if group else None,
                "topic_title": topic.get("title_en") if topic else None,
                "created_at": row.created_at,
                "submitted_at": row.submitted_at,
                **stat,
            }
        )

    attempts = []
    for row in db.scalars(
        select(Attempt)
        .where(Attempt.user_id == user.id)
        .order_by(Attempt.created_at.desc())
        .limit(20)
    ):
        paper = store.get_paper(row.paper_id) or {}
        attempts.append(
            {
                "id": row.id,
                "paper_id": row.paper_id,
                "paper_title": paper.get("title") or row.paper_id,
                "paper_year": paper.get("year"),
                "mode": row.mode,
                "status": row.status,
                "mcq_score": row.mcq_score,
                "mcq_total": row.mcq_total,
                "frq_score": row.frq_score,
                "frq_total": row.frq_total,
                "created_at": row.created_at,
                "submitted_at": row.submitted_at,
            }
        )

    wrong_rows = db.execute(
        select(WrongQuestion.mastery, func.count())
        .where(WrongQuestion.user_id == user.id)
        .group_by(WrongQuestion.mastery)
    ).all()
    wrong_summary = {"learning": 0, "reviewing": 0, "mastered": 0}
    for mastery, count in wrong_rows:
        wrong_summary[mastery] = int(count)

    return {
        "student": {
            "id": user.id,
            "email": user.email,
            "email_masked": mask_email(user.email),
            "phone_masked": mask_phone(user.phone),
            "nickname": user.nickname,
            "grade": user.grade,
            "region": user.region,
            "target_score": user.target_score,
            "studied_psychology": user.studied_psychology,
            "study_mode": user.study_mode,
            "exam_time": user.exam_time,
            "teacher_note": user.teacher_note,
            "profile_completed_at": user.profile_completed_at,
            "status": user.status,
            "created_at": user.created_at,
            "last_login_at": user.last_login_at,
        },
        "dashboard": dashboard,
        "sessions": sessions,
        "attempts": attempts,
        "wrong_summary": wrong_summary,
    }


@router.patch("/students/{user_id}")
def admin_update_student(
    user_id: str,
    body: AdminStudentPatch,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    user = db.get(User, user_id)
    if not user:
        raise AppError(404, "STUDENT_NOT_FOUND", "学生不存在")
    if body.teacher_note is not None:
        user.teacher_note = body.teacher_note.strip() or None
    record_audit(
        db,
        admin,
        "student.note.update",
        target_type="student",
        target_id=user.id,
        detail={"has_note": bool(user.teacher_note)},
    )
    db.commit()
    db.refresh(user)
    return {
        "student": {
            "id": user.id,
            "teacher_note": user.teacher_note,
        }
    }


def _admin_subject(subject: Optional[str]) -> str:
    subject_id = (subject or "psychology").strip()
    if not subject_catalog.get_subject_config(subject_id):
        raise AppError(400, "SUBJECT_INVALID", "科目分类不存在")
    return subject_id


def _admin_import_subject(subject: Optional[str]) -> str:
    subject_id = _admin_subject(subject)
    config = subject_catalog.get_subject_config(subject_id) or {}
    if not config.get("enabled"):
        raise AppError(400, "SUBJECT_DISABLED", "该科目未启用，不能导入题目")
    return subject_id


def _prepare_admin_content(db: Session, subject_id: str = "psychology") -> None:
    try:
        ensure_effective_content(db, subject_id, force_marker_columns=True)
    except Exception as exc:  # noqa: BLE001
        raise AppError(
            503, "ADMIN_CONTENT_NOT_READY", "管理员内容层暂不可用"
        ) from exc


MAX_SELF_QUESTION_IMPORT_BYTES = 10 * 1024 * 1024


def _write_self_question_upload(file: UploadFile) -> Path:
    filename = file.filename or ""
    if not filename.lower().endswith(".xlsx"):
        raise AppError(400, "IMPORT_FILE_TYPE", "请上传 .xlsx 文件")
    data = file.file.read(MAX_SELF_QUESTION_IMPORT_BYTES + 1)
    if len(data) > MAX_SELF_QUESTION_IMPORT_BYTES:
        raise AppError(400, "IMPORT_FILE_TOO_LARGE", "Excel 文件不能超过 10MB")
    fd, name = tempfile.mkstemp(suffix=".xlsx")
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
    return Path(name)


def _read_self_question_upload(file: UploadFile) -> tuple[list[Any], list[str]]:
    path = _write_self_question_upload(file)
    try:
        questions, errors, warnings = read_questions(path)
    finally:
        path.unlink(missing_ok=True)
    if errors:
        raise AppError(
            400,
            "IMPORT_WORKBOOK_INVALID",
            "Excel 校验未通过",
            {"errors": errors, "warnings": warnings},
        )
    if not questions:
        raise AppError(400, "IMPORT_WORKBOOK_EMPTY", "Excel 中没有题目")
    return questions, warnings


def _build_self_question_plan(
    db: Session, subject_id: str, file: UploadFile
):
    questions, warnings = _read_self_question_upload(file)
    plan = self_question_import.build_plan(
        db, subject_id, questions, warnings
    )
    if plan.errors:
        raise AppError(
            400,
            "IMPORT_PLAN_INVALID",
            "导入计划有误",
            {"errors": plan.errors, "warnings": plan.warnings},
        )
    return plan


def _question_stars(
    db: Session, subject_id: str, question_ids: list[str]
) -> dict[str, int]:
    if not question_ids:
        return {}
    rows = db.scalars(
        select(QuestionStar).where(
            QuestionStar.subject_id == subject_id,
            QuestionStar.question_id.in_(question_ids),
        )
    )
    return {row.question_id: row.stars for row in rows}


def _question_notes(
    db: Session, subject_id: str, question_ids: list[str]
) -> dict[str, str]:
    if not question_ids:
        return {}
    rows = db.scalars(
        select(QuestionAdminNote).where(
            QuestionAdminNote.subject_id == subject_id,
            QuestionAdminNote.question_id.in_(question_ids),
        )
    )
    return {row.question_id: row.note for row in rows}


def _attach_admin_question_meta(
    db: Session, subject_id: str, question: dict
) -> dict:
    question_id = str(question["question_id"])
    question["stars"] = _question_stars(db, subject_id, [question_id]).get(
        question_id
    )
    question["admin_note"] = _question_notes(db, subject_id, [question_id]).get(
        question_id
    )
    return question


def _attach_admin_meta_to_questions(
    db: Session, subject_id: str, questions: list[dict]
) -> list[dict]:
    question_ids = [str(item["question_id"]) for item in questions]
    stars = _question_stars(db, subject_id, question_ids)
    notes = _question_notes(db, subject_id, question_ids)
    for item in questions:
        question_id = str(item["question_id"])
        item["stars"] = stars.get(question_id)
        item["admin_note"] = notes.get(question_id)
    return questions


@router.get("/content/papers")
def admin_papers(
    subject: Optional[str] = None,
    store: ContentStore = Depends(get_store),
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    subject_id = _admin_subject(subject)
    _prepare_admin_content(db, subject_id)
    papers = admin_content.list_papers(subject_id=subject_id)
    for paper in papers:
        config = store.get_exam_config(paper["paper_id"]) or {}
        paper["config"] = {
            "format_code": config.get("format_code"),
            "mcq_count": config.get("mcq_count"),
            "mcq_minutes": config.get("mcq_minutes"),
            "frq_count": config.get("frq_count"),
            "frq_minutes": config.get("frq_minutes"),
            "frq_forms": config.get("frq_forms") or [],
            "is_complete": config.get("is_complete"),
            "frq_rubric_complete": config.get("frq_rubric_complete"),
            "expected_frq_points": config.get("expected_frq_points"),
            "notes": config.get("notes"),
        }
    return {"papers": papers}


@router.get("/content/papers/{paper_id}")
def admin_paper_detail(
    paper_id: str,
    subject: Optional[str] = None,
    store: ContentStore = Depends(get_store),
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    subject_id = _admin_subject(subject)
    _prepare_admin_content(db, subject_id)
    paper = admin_content.get_paper(paper_id, subject_id=subject_id)
    if not paper:
        raise AppError(404, "PAPER_NOT_FOUND", "试卷不存在")
    paper["config"] = store.get_exam_config(paper_id) or {}
    paper["questions"] = _attach_admin_meta_to_questions(
        db,
        subject_id,
        admin_content.list_questions(paper_id, subject_id=subject_id),
    )
    if paper.get("paper_type") in ("practice_bundle", "bundle"):
        paper["practice"] = admin_content.bundle_practice_stats(paper_id)
    return paper


@router.get("/content/questions")
def admin_question_list(
    source: str = "all",
    unit: Optional[str] = None,
    topic: Optional[str] = None,
    paper_id: Optional[str] = None,
    section: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    subject: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    subject_id = _admin_subject(subject)
    _prepare_admin_content(db, subject_id)
    source_value = (source or "all").strip()
    if source_value not in (
        "all",
        "unit",
        "real_exam",
        "mock_exam",
        "unit_practice",
        "self_bank",
    ):
        raise AppError(400, "QUESTION_SOURCE_INVALID", "来源筛选不合法")
    section_value = (section or "").strip().upper()
    if section_value in ("", "ALL"):
        section_value = None
    elif section_value not in ("MCQ", "FRQ"):
        raise AppError(400, "QUESTION_SECTION_INVALID", "题型筛选不合法")
    result = admin_content.list_all_questions(
        source=source_value,
        unit_id=unit,
        topic_id=topic,
        paper_id=paper_id,
        section=section_value,
        q=q,
        limit=limit,
        offset=offset,
        subject_id=subject_id,
    )
    _attach_admin_meta_to_questions(db, subject_id, result["questions"])
    return {
        "questions": result["questions"],
        "total": result["total"],
        "limit": limit,
        "offset": offset,
        "units": result["units"],
    }


@router.get("/content/questions/ids")
def admin_question_ids(
    source: str = "all",
    unit: Optional[str] = None,
    topic: Optional[str] = None,
    paper_id: Optional[str] = None,
    section: Optional[str] = None,
    q: Optional[str] = None,
    max: int = Query(default=2000, ge=1, le=2000),
    subject: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    subject_id = _admin_subject(subject)
    _prepare_admin_content(db, subject_id)
    source_value = (source or "all").strip()
    if source_value not in (
        "all",
        "unit",
        "real_exam",
        "mock_exam",
        "unit_practice",
        "self_bank",
    ):
        raise AppError(400, "QUESTION_SOURCE_INVALID", "来源筛选不合法")
    section_value = (section or "").strip().upper()
    if section_value in ("", "ALL"):
        section_value = None
    elif section_value not in ("MCQ", "FRQ"):
        raise AppError(400, "QUESTION_SECTION_INVALID", "题型筛选不合法")
    return admin_content.list_all_question_ids(
        source=source_value,
        unit_id=unit,
        topic_id=topic,
        paper_id=paper_id,
        section=section_value,
        q=q,
        max_ids=max,
        subject_id=subject_id,
    )


@router.get("/content/questions/{question_id}")
def admin_question_detail(
    question_id: str,
    subject: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    subject_id = _admin_subject(subject)
    _prepare_admin_content(db, subject_id)
    question = admin_content.get_question(question_id, subject_id=subject_id)
    if not question:
        raise AppError(404, "QUESTION_NOT_FOUND", "题目不存在")
    return _attach_admin_question_meta(db, subject_id, question)


@router.get("/content/knowledge/concepts")
def admin_concepts(
    q: Optional[str] = None,
    subject: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    subject_id = _admin_subject(subject)
    _prepare_admin_content(db, subject_id)
    return {
        "concepts": admin_content.list_concepts(
            q, limit, offset, subject_id=subject_id
        ),
        "total": admin_content.count_concepts(q, subject_id=subject_id),
        "limit": limit,
        "offset": offset,
    }


@router.get("/content/knowledge/concepts/{cluster_id}")
def admin_concept_detail(
    cluster_id: str,
    subject: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    subject_id = _admin_subject(subject)
    _prepare_admin_content(db, subject_id)
    concept = admin_content.get_concept(cluster_id, subject_id=subject_id)
    if not concept:
        raise AppError(404, "CONCEPT_NOT_FOUND", "概念不存在")
    return concept


@router.get("/content/knowledge/kps")
def admin_kps(
    q: Optional[str] = None,
    subject: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    subject_id = _admin_subject(subject)
    _prepare_admin_content(db, subject_id)
    return {
        "kps": admin_content.list_kps(
            q, limit, offset, subject_id=subject_id
        ),
        "total": admin_content.count_kps(q, subject_id=subject_id),
        "limit": limit,
        "offset": offset,
    }


@router.get("/content/knowledge/kps/{kp_id}")
def admin_kp_detail(
    kp_id: str,
    subject: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    subject_id = _admin_subject(subject)
    _prepare_admin_content(db, subject_id)
    kp = admin_content.get_kp(kp_id, subject_id=subject_id)
    if not kp:
        raise AppError(404, "KP_NOT_FOUND", "知识点不存在")
    return kp


@router.patch("/content/papers/{paper_id}")
def admin_update_paper(
    paper_id: str,
    body: PaperPatch,
    subject: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin_roles("super_admin", "content_editor")),
):
    subject_id = _admin_subject(subject)
    updates = body.model_dump(exclude_unset=True)
    admin_content_edits.update_paper(
        db, admin, paper_id, updates, subject_id=subject_id
    )
    record_audit(
        db,
        admin,
        "content.paper.update",
        target_type="paper",
        target_id=paper_id,
        detail={"subject_id": subject_id, "fields": sorted(updates)},
    )
    db.commit()
    admin_content_edits.refresh_content(db, subject_id)
    paper = admin_content.get_paper(paper_id, subject_id=subject_id)
    if not paper:
        raise AppError(404, "PAPER_NOT_FOUND", "试卷不存在")
    return paper


@router.patch("/content/questions/{question_id}")
def admin_update_question(
    question_id: str,
    body: QuestionPatch,
    subject: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin_roles("super_admin", "content_editor")),
):
    subject_id = _admin_subject(subject)
    updates = body.model_dump(exclude_unset=True)
    admin_content_edits.update_question(
        db, admin, question_id, updates, subject_id=subject_id
    )
    record_audit(
        db,
        admin,
        "content.question.update",
        target_type="question",
        target_id=question_id,
        detail={"subject_id": subject_id, "fields": sorted(updates)},
    )
    db.commit()
    admin_content_edits.refresh_content(db, subject_id)
    question = admin_content.get_question(question_id, subject_id=subject_id)
    if not question:
        raise AppError(404, "QUESTION_NOT_FOUND", "题目不存在")
    return _attach_admin_question_meta(db, subject_id, question)


@router.patch("/content/questions/{question_id}/stars")
def admin_update_question_stars(
    question_id: str,
    body: QuestionStarsPatch,
    request: Request,
    subject: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin_roles("super_admin", "content_editor")),
):
    subject_id = _admin_subject(subject)
    _prepare_admin_content(db, subject_id)
    if not admin_content.get_question(question_id, subject_id=subject_id):
        raise AppError(404, "QUESTION_NOT_FOUND", "题目不存在")
    row = db.get(QuestionStar, (subject_id, question_id))
    if body.stars is None:
        if row is not None:
            db.delete(row)
    elif row is None:
        db.add(
            QuestionStar(
                subject_id=subject_id,
                question_id=question_id,
                stars=body.stars,
                updated_by=admin.id,
            )
        )
    else:
        row.stars = body.stars
        row.updated_by = admin.id
    record_audit(
        db,
        admin,
        "content.question.stars.update",
        target_type="question",
        target_id=question_id,
        detail={"subject_id": subject_id, "stars": body.stars},
        request=request,
    )
    db.commit()
    return {"ok": True, "question_id": question_id, "stars": body.stars}


@router.patch("/content/questions/{question_id}/note")
def admin_update_question_note(
    question_id: str,
    body: QuestionNotePatch,
    request: Request,
    subject: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin_roles("super_admin", "content_editor")),
):
    subject_id = _admin_subject(subject)
    _prepare_admin_content(db, subject_id)
    if not admin_content.get_question(question_id, subject_id=subject_id):
        raise AppError(404, "QUESTION_NOT_FOUND", "题目不存在")
    note = (body.note or "").strip()
    row = db.get(QuestionAdminNote, (subject_id, question_id))
    if not note:
        if row is not None:
            db.delete(row)
    elif row is None:
        db.add(
            QuestionAdminNote(
                subject_id=subject_id,
                question_id=question_id,
                note=note,
                updated_by=admin.id,
            )
        )
    else:
        row.note = note
        row.updated_by = admin.id
    record_audit(
        db,
        admin,
        "content.question.note.update",
        target_type="question",
        target_id=question_id,
        detail={
            "subject_id": subject_id,
            "cleared": not note,
            "length": len(note),
        },
        request=request,
    )
    db.commit()
    return {
        "ok": True,
        "question_id": question_id,
        "admin_note": note or None,
    }


@router.post("/content/questions")
def admin_create_question(
    body: AdminQuestionCreate,
    request: Request,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin_roles("super_admin", "content_editor")),
):
    payload = body.model_dump()
    subject_id = _admin_subject(payload.get("subject_id"))
    payload["subject_id"] = subject_id
    data = admin_content_edits.create_question(db, admin, payload)
    record_audit(
        db,
        admin,
        "content.question.create",
        target_type="question",
        target_id=data["question_id"],
        detail={
            "subject_id": subject_id,
            "paper_id": body.paper_id,
            "section": body.section,
        },
        request=request,
    )
    db.commit()
    admin_content_edits.refresh_content(db, subject_id)
    question = admin_content.get_question(
        data["question_id"], subject_id=subject_id
    )
    if not question:
        raise AppError(500, "QUESTION_CREATE_FAILED", "题目创建失败")
    return _attach_admin_question_meta(db, subject_id, question)


@router.post("/content/questions/import/preview")
def admin_preview_question_import(
    file: UploadFile = File(...),
    subject: Optional[str] = Form(default=None),
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin_roles("super_admin", "content_editor")),
):
    subject_id = _admin_import_subject(subject)
    _prepare_admin_content(db, subject_id)
    plan = _build_self_question_plan(db, subject_id, file)
    return self_question_import.preview_payload(plan)


@router.post("/content/questions/import")
def admin_apply_question_import(
    request: Request,
    file: UploadFile = File(...),
    subject: Optional[str] = Form(default=None),
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin_roles("super_admin", "content_editor")),
):
    subject_id = _admin_import_subject(subject)
    _prepare_admin_content(db, subject_id)
    plan = _build_self_question_plan(db, subject_id, file)
    try:
        result = self_question_import.apply_plan(db, admin, plan)
    except ImportValidationError as exc:
        raise AppError(
            400,
            "IMPORT_PLAN_INVALID",
            "导入计划有误",
            {"errors": exc.errors},
        ) from exc
    record_audit(
        db,
        admin,
        "content.question.import",
        target_type="paper",
        target_id=result["paper_id"],
        detail={
            "subject_id": subject_id,
            "filename": file.filename,
            **result["summary"],
        },
        request=request,
    )
    db.commit()
    admin_content_edits.refresh_content(db, subject_id)
    return result


@router.get("/content/questions/import/template")
def admin_download_question_import_template(
    admin: AdminUser = Depends(require_admin_roles("super_admin", "content_editor")),
):
    fd, name = tempfile.mkstemp(suffix=".xlsx")
    os.close(fd)
    path = Path(name)
    try:
        write_template(path)
        data = path.read_bytes()
    finally:
        path.unlink(missing_ok=True)
    filename = "自研题导入模板.xlsx"
    disposition = (
        'attachment; filename="self-question-template.xlsx"; '
        f"filename*=UTF-8''{quote(filename)}"
    )
    return Response(
        content=data,
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": disposition,
            "Cache-Control": "no-store",
        },
    )


@router.post("/content/questions/{question_id}/concepts")
def admin_add_question_concept(
    question_id: str,
    body: AdminQuestionConceptLinkCreate,
    request: Request,
    subject: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin_roles("super_admin", "content_editor")),
):
    subject_id = _admin_subject(subject)
    data = admin_content_edits.add_question_concept_link(
        db, admin, question_id, body.model_dump(), subject_id=subject_id
    )
    record_audit(
        db,
        admin,
        "content.question_concept.create",
        target_type="question",
        target_id=question_id,
        detail={
            "subject_id": subject_id,
            "concept_id": body.concept_id,
            "relation_type": body.relation_type,
        },
        request=request,
    )
    db.commit()
    admin_content_edits.refresh_content(db, subject_id)
    return {
        "ok": data["ok"],
        "concepts": admin_content.get_question_concepts(
            question_id, subject_id=subject_id
        ),
    }


@router.delete("/content/questions/{question_id}/concepts/{link_id}")
def admin_delete_question_concept(
    question_id: str,
    link_id: int,
    request: Request,
    subject: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin_roles("super_admin", "content_editor")),
):
    subject_id = _admin_subject(subject)
    admin_content_edits.delete_question_concept_link(
        db, admin, question_id, link_id, subject_id=subject_id
    )
    record_audit(
        db,
        admin,
        "content.question_concept.delete",
        target_type="question",
        target_id=question_id,
        detail={"subject_id": subject_id, "link_id": link_id},
        request=request,
    )
    db.commit()
    admin_content_edits.refresh_content(db, subject_id)
    return {
        "ok": True,
        "concepts": admin_content.get_question_concepts(
            question_id, subject_id=subject_id
        ),
    }


@router.patch("/content/knowledge/concepts/{cluster_id}")
def admin_update_concept(
    cluster_id: str,
    body: ConceptPatch,
    subject: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin_roles("super_admin", "content_editor")),
):
    subject_id = _admin_subject(subject)
    updates = body.model_dump(exclude_unset=True)
    admin_content_edits.update_concept(
        db, admin, cluster_id, updates, subject_id=subject_id
    )
    record_audit(
        db,
        admin,
        "content.concept.update",
        target_type="concept",
        target_id=cluster_id,
        detail={"subject_id": subject_id, "fields": sorted(updates)},
    )
    db.commit()
    admin_content_edits.refresh_content(db, subject_id)
    concept = admin_content.get_concept(cluster_id, subject_id=subject_id)
    if not concept:
        raise AppError(404, "CONCEPT_NOT_FOUND", "概念不存在")
    return concept


@router.post("/content/knowledge/concepts")
def admin_create_concept(
    body: AdminConceptCreate,
    request: Request,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin_roles("super_admin", "content_editor")),
):
    payload = body.model_dump()
    subject_id = _admin_subject(payload.get("subject_id"))
    payload["subject_id"] = subject_id
    data = admin_content_edits.create_concept(db, admin, payload)
    record_audit(
        db,
        admin,
        "content.concept.create",
        target_type="concept",
        target_id=data["cluster_id"],
        detail={
            "subject_id": subject_id,
            "name": data["canonical_name"],
            "ap_unit": data.get("ap_unit"),
        },
        request=request,
    )
    db.commit()
    admin_content_edits.refresh_content(db, subject_id)
    concept = admin_content.get_concept(
        data["cluster_id"], subject_id=subject_id
    )
    if not concept:
        raise AppError(500, "CONCEPT_CREATE_FAILED", "知识点创建失败")
    return concept


@router.patch("/content/knowledge/kps/{kp_id}")
def admin_update_kp(
    kp_id: str,
    body: KnowledgePointPatch,
    subject: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin_roles("super_admin", "content_editor")),
):
    subject_id = _admin_subject(subject)
    updates = body.model_dump(exclude_unset=True)
    admin_content_edits.update_kp(
        db, admin, kp_id, updates, subject_id=subject_id
    )
    record_audit(
        db,
        admin,
        "content.kp.update",
        target_type="kp",
        target_id=kp_id,
        detail={"subject_id": subject_id, "fields": sorted(updates)},
    )
    db.commit()
    admin_content_edits.refresh_content(db, subject_id)
    kp = admin_content.get_kp(kp_id, subject_id=subject_id)
    if not kp:
        raise AppError(404, "KP_NOT_FOUND", "知识点不存在")
    return kp


def _release_subjects(payload: dict) -> list[str]:
    subjects = payload.get("subjects")
    if isinstance(subjects, list) and subjects:
        return [str(item) for item in subjects]
    return [str(payload.get("subject_id") or "psychology")]


def _global_active_release_id() -> Optional[str]:
    """Read the merged ``data/releases/active`` pointer, if present."""
    active = REPO_ROOT / "data" / "releases" / "active"
    release_file = active / "release.json"
    if not release_file.exists():
        return None
    try:
        payload = json.loads(release_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return str(payload.get("release_id") or active.resolve().name)


def _release_payload(path: Path, active_release_id: str) -> Optional[dict]:
    release_file = path / "release.json"
    if not release_file.exists():
        return None
    try:
        payload = json.loads(release_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    subjects = _release_subjects(payload)
    return {
        "release_id": payload.get("release_id", path.name),
        "subjects": subjects,
        "merged": isinstance(payload.get("subjects"), list),
        "created_at": payload.get("created_at"),
        "counts": payload.get("counts", {}),
        "counts_by_subject": payload.get("counts_by_subject", {}),
        "active": payload.get("release_id") == active_release_id,
    }


@router.get("/releases")
def admin_releases(
    store: ContentStore = Depends(get_store),
    admin: AdminUser = Depends(get_current_admin),
):
    active_release_id = _global_active_release_id() or store.release_id
    releases_root = REPO_ROOT / "data" / "releases"
    archive_root = releases_root / ".archive"
    items = []
    archived = []
    if releases_root.exists():
        for path in releases_root.iterdir():
            if not path.is_dir() or path.name.startswith(".") or path.name in {"current", "active"}:
                continue
            item = _release_payload(path, active_release_id)
            if item:
                items.append(item)
    if archive_root.exists():
        for path in archive_root.iterdir():
            if not path.is_dir() or path.name.startswith("."):
                continue
            item = _release_payload(path, active_release_id)
            if item:
                item["archived"] = True
                archived.append(item)
    items.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    archived.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    return {
        "active_release_id": active_release_id,
        "releases": items,
        "archived": archived,
    }


@router.post("/releases/{release_id}/archive")
def admin_archive_release(
    release_id: str,
    db: Session = Depends(get_db),
    store: ContentStore = Depends(get_store),
    admin: AdminUser = Depends(require_admin_roles("super_admin")),
):
    if "/" in release_id or "\\" in release_id or release_id in (".", ".."):
        raise AppError(400, "RELEASE_ID_INVALID", "Release ID 不合法")
    active_release_id = _global_active_release_id() or store.release_id
    if release_id == active_release_id:
        raise AppError(409, "ACTIVE_RELEASE_LOCKED", "不能归档当前 active release")

    releases_root = REPO_ROOT / "data" / "releases"
    release_dir = releases_root / release_id
    if not release_dir.is_dir() or not (release_dir / "release.json").exists():
        raise AppError(404, "RELEASE_NOT_FOUND", "Release 不存在")
    archive_root = releases_root / ".archive"
    archive_root.mkdir(parents=True, exist_ok=True)
    target = archive_root / release_id
    if target.exists():
        raise AppError(409, "RELEASE_ARCHIVE_EXISTS", "归档目录已存在")
    release_dir.rename(target)
    for release_row in db.scalars(
        select(ContentRelease).where(ContentRelease.release_id == release_id)
    ):
        release_row.status = "archived"
        release_row.path = str(target)
        release_row.archived_at = utcnow()
    record_audit(
        db,
        admin,
        "release.archive",
        target_type="release",
        target_id=release_id,
    )
    db.commit()
    return {"ok": True, "release_id": release_id, "archived": True}


@router.post("/releases/{release_id}/restore")
def admin_restore_release(
    release_id: str,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin_roles("super_admin")),
):
    if "/" in release_id or "\\" in release_id or release_id in (".", ".."):
        raise AppError(400, "RELEASE_ID_INVALID", "Release ID 不合法")
    releases_root = REPO_ROOT / "data" / "releases"
    archived_dir = releases_root / ".archive" / release_id
    if not archived_dir.is_dir() or not (archived_dir / "release.json").exists():
        raise AppError(404, "RELEASE_NOT_FOUND", "归档 Release 不存在")
    target = releases_root / release_id
    if target.exists():
        raise AppError(409, "RELEASE_EXISTS", "同 ID 的 Release 已存在，无法恢复")
    archived_dir.rename(target)
    for release_row in db.scalars(
        select(ContentRelease).where(ContentRelease.release_id == release_id)
    ):
        release_row.status = "imported"
        release_row.path = str(target)
        release_row.archived_at = None
    record_audit(
        db,
        admin,
        "release.restore",
        target_type="release",
        target_id=release_id,
    )
    db.commit()
    return {"ok": True, "release_id": release_id, "archived": False}


def _release_job_payload(job: ReleaseJob) -> dict:
    return {
        "id": job.id,
        "release_id": job.release_id,
        "status": job.status,
        "log": job.log,
        "error": job.error,
        "created_at": job.created_at,
        "finished_at": job.finished_at,
    }


@router.get("/releases/jobs")
def admin_release_jobs(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    jobs = list(db.scalars(select(ReleaseJob).order_by(ReleaseJob.created_at.desc()).limit(limit)))
    return {"jobs": [_release_job_payload(job) for job in jobs]}


@router.post("/releases/build")
def admin_build_release(
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin_roles("super_admin", "content_editor")),
):
    today = datetime.now().strftime("%Y%m%d")
    prefix = f"content-{today}-"
    releases_root = REPO_ROOT / "data" / "releases"
    sequence = 0
    if releases_root.exists():
        for path in releases_root.iterdir():
            if path.name.startswith(prefix) and path.name[len(prefix) :].isdigit():
                sequence = max(sequence, int(path.name[len(prefix) :]))
    while True:
        sequence += 1
        release_id = f"{prefix}{sequence:02d}"
        if (
            not (releases_root / release_id).exists()
            and not (releases_root / ".staging" / release_id).exists()
        ):
            break

    job = ReleaseJob(
        admin_id=admin.id,
        release_id=release_id,
        status="building",
        created_at=utcnow(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    script = REPO_ROOT / "_tools" / "build_merged_release.py"
    if not script.exists():
        job.status = "failed"
        job.error = f"build script not found: {script}"
        job.finished_at = utcnow()
        db.commit()
        return {"job": _release_job_payload(job)}

    try:
        result = subprocess.run(
            [sys.executable, str(script), "--release-id", release_id],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=900,
            check=False,
        )
        log = (result.stdout or "") + (result.stderr or "")
        job.log = log[-50000:]
        if result.returncode == 0:
            job.status = "succeeded"
        else:
            job.status = "failed"
            job.error = (result.stderr or result.stdout or "")[-5000:]
    except subprocess.TimeoutExpired:
        job.status = "failed"
        job.error = "build timed out after 900 seconds"
    except Exception as exc:  # noqa: BLE001
        job.status = "failed"
        job.error = str(exc)
    job.finished_at = utcnow()
    record_audit(
        db,
        admin,
        "release.build",
        target_type="release",
        target_id=release_id,
        detail={"status": job.status},
    )
    db.commit()
    return {"job": _release_job_payload(job)}


def _switch_symlink(link: Path, target: Path) -> None:
    """Atomically point ``link`` at ``target`` (both under the same parent)."""
    link.parent.mkdir(parents=True, exist_ok=True)
    temp = link.parent / f".{link.name}.tmp"
    if temp.is_symlink() or temp.exists():
        temp.unlink()
    temp.symlink_to(os.path.relpath(target, link.parent), target_is_directory=True)
    os.replace(temp, link)


def _prepare_global_active_slot(active: Path) -> None:
    """Migrate the transitional ``active/<subject>`` directory layout.

    The merged Release design uses one symlink at ``data/releases/active``.
    The only automatic migration allowed is removing a directory whose
    children are all symlinks; anything else is left for an operator.
    """
    if active.is_symlink() or not active.exists():
        return
    if not active.is_dir() or (active / "release.json").exists():
        raise AppError(409, "ACTIVE_LAYOUT_UNSUPPORTED", "data/releases/active 布局无法自动迁移")
    children = list(active.iterdir())
    if any(not child.is_symlink() for child in children):
        raise AppError(
            409,
            "ACTIVE_LAYOUT_UNSUPPORTED",
            "data/releases/active 内存在非符号链接文件",
        )
    for child in children:
        child.unlink()
    active.rmdir()


def _reload_store_for_subject(request: Request, subject_id: str) -> ContentStore:
    settings = get_settings()
    target = settings.resolve_content_dir(subject_id)
    store = ContentStore(target, settings, subject_id=subject_id)
    for method in (
        "get_topic_concepts",
        "question_context",
        "get_feedback",
        "get_frq_guidelines",
    ):
        cache_clear = getattr(getattr(store, method), "cache_clear", None)
        if cache_clear:
            cache_clear()
    stores = getattr(request.app.state, "stores", None)
    if stores is None:
        stores = {}
        request.app.state.stores = stores
    stores[subject_id] = store
    if subject_id == "psychology":
        request.app.state.store = store
    return store


@router.post("/releases/{release_id}/activate")
def admin_activate_release(
    release_id: str,
    request: Request,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin_roles("super_admin")),
):
    if "/" in release_id or "\\" in release_id or release_id in (".", ".."):
        raise AppError(400, "RELEASE_ID_INVALID", "Release ID 不合法")
    releases_root = REPO_ROOT / "data" / "releases"
    release_dir = releases_root / release_id
    release_file = release_dir / "release.json"
    if not release_dir.is_dir() or not release_file.exists():
        raise AppError(404, "RELEASE_NOT_FOUND", "Release 不存在或缺少 release.json")
    try:
        payload = json.loads(release_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AppError(400, "RELEASE_MANIFEST_INVALID", "Release 清单不合法") from exc
    subjects = _release_subjects(payload)
    active = releases_root / "active"
    _prepare_global_active_slot(active)
    _switch_symlink(active, release_dir)
    current = releases_root / "current"
    if current.is_symlink() or not current.exists():
        _switch_symlink(current, release_dir)

    now = utcnow()
    counts_by_subject = payload.get("counts_by_subject") or {}
    for subject_id in subjects:
        for row in db.scalars(
            select(ContentRelease).where(
                ContentRelease.subject_id == subject_id,
                ContentRelease.status == "active",
            )
        ):
            row.status = "imported"
            row.activated_at = None
        release_row = db.get(ContentRelease, (subject_id, release_id))
        counts = counts_by_subject.get(subject_id) or payload.get("counts", {})
        if release_row is None:
            release_row = ContentRelease(
                subject_id=subject_id,
                release_id=release_id,
                path=str(release_dir),
                status="active",
                counts_json=counts,
                checksums_json=payload.get("checksums", {}),
                source=payload.get("source"),
                created_at=now,
            )
            db.add(release_row)
        release_row.status = "active"
        release_row.activated_at = now
        active_row = db.get(ContentActiveRelease, subject_id)
        if active_row is None:
            db.add(
                ContentActiveRelease(
                    subject_id=subject_id,
                    release_id=release_id,
                    activated_at=now,
                    activated_by=admin.id,
                )
            )
        else:
            active_row.release_id = release_id
            active_row.activated_at = now
            active_row.activated_by = admin.id

    stores = {subject_id: _reload_store_for_subject(request, subject_id) for subject_id in subjects}
    record_audit(
        db,
        admin,
        "release.activate",
        target_type="release",
        target_id=release_id,
        request=request,
        detail={"subjects": subjects},
    )
    db.commit()
    active_release_id = _global_active_release_id() or stores[subjects[0]].release_id
    return {"active_release_id": active_release_id, "subjects": subjects}


@router.get("/subjects")
def admin_subjects(
    include_disabled: bool = Query(default=False),
    admin: AdminUser = Depends(get_current_admin),
):
    return {
        "subjects": subject_catalog.subject_payloads(include_disabled=include_disabled)
    }


@router.get("/codes/batches")
def admin_code_batches(
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    batches = list(
        db.scalars(
            select(ActivationCodeBatch).order_by(ActivationCodeBatch.created_at.desc()).limit(limit)
        )
    )
    return {"batches": [activation_codes.batch_payload(db, batch) for batch in batches]}


@router.post("/codes/batches")
def admin_create_code_batch(
    body: ActivationCodeBatchCreate,
    request: Request,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin_roles("super_admin")),
):
    batch, codes = activation_codes.create_batch(
        db,
        admin_id=admin.id,
        scope_type=body.scope_type,
        subject_id=body.subject_id,
        duration_days=body.duration_days,
        expires_on=body.expires_on,
        count=body.count,
        note=body.note,
    )
    record_audit(
        db,
        admin,
        "activation_codes.create",
        target_type="activation_code_batch",
        target_id=batch.id,
        request=request,
        detail={
            "scope_type": batch.scope_type,
            "subject_ids": batch.subject_ids,
            "duration_days": batch.duration_days,
            "expires_on": batch.expires_on.isoformat() if batch.expires_on else None,
            "count": batch.count,
        },
    )
    db.commit()
    return {
        "batch": activation_codes.batch_payload(db, batch),
        "codes": codes,
    }


@router.get("/codes/batches/{batch_id}/codes")
def admin_batch_codes(
    batch_id: str,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    batch = db.get(ActivationCodeBatch, batch_id)
    if not batch:
        raise AppError(404, "CODE_BATCH_NOT_FOUND", "激活码批次不存在")
    return {
        "batch": activation_codes.batch_payload(db, batch),
        "codes": [
            activation_codes.code_payload(code)
            for code in activation_codes.batch_codes(db, batch.id)
        ],
    }


@router.get("/codes/batches/{batch_id}/download")
def admin_download_code_batch(
    batch_id: str,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin_roles("super_admin")),
):
    batch = db.get(ActivationCodeBatch, batch_id)
    if not batch:
        raise AppError(404, "CODE_BATCH_NOT_FOUND", "激活码批次不存在")
    content = activation_codes.batch_download_text(db, batch)
    return Response(
        content=content,
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{batch.id}.txt"',
            "Cache-Control": "no-store",
        },
    )


@router.post("/codes/{code_id}/void")
def admin_void_code(
    code_id: str,
    request: Request,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin_roles("super_admin")),
):
    code = db.get(ActivationCode, code_id)
    if not code:
        raise AppError(404, "CODE_NOT_FOUND", "激活码不存在")
    activation_codes.void_code(db, code, admin.id)
    record_audit(
        db,
        admin,
        "activation_codes.void",
        target_type="activation_code",
        target_id=code.id,
        request=request,
    )
    db.commit()
    return {"ok": True}


@router.post("/codes/batches/{batch_id}/void")
def admin_void_code_batch(
    batch_id: str,
    request: Request,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin_roles("super_admin")),
):
    batch = db.get(ActivationCodeBatch, batch_id)
    if not batch:
        raise AppError(404, "CODE_BATCH_NOT_FOUND", "激活码批次不存在")
    activation_codes.void_batch(db, batch, admin.id)
    record_audit(
        db,
        admin,
        "activation_codes.batch_void",
        target_type="activation_code_batch",
        target_id=batch.id,
        request=request,
    )
    db.commit()
    return {"ok": True}


@router.get("/audit")
def admin_audit(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    rows = list(
        db.scalars(select(AdminAuditLog).order_by(AdminAuditLog.created_at.desc()).limit(limit))
    )
    admins = {
        item.id: item
        for item in db.scalars(
            select(AdminUser).where(
                AdminUser.id.in_({row.admin_id for row in rows if row.admin_id})
            )
        )
    }
    return {
        "logs": [
            {
                "id": row.id,
                "admin_id": row.admin_id,
                "admin_username": admins[row.admin_id].username if row.admin_id in admins else None,
                "action": row.action,
                "target_type": row.target_type,
                "target_id": row.target_id,
                "detail": row.detail,
                "ip": row.ip,
                "created_at": row.created_at,
            }
            for row in rows
        ]
    }
