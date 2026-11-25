from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.schemas import (
    HomeworkCreate,
    HomeworkQuestionsReplace,
    HomeworkUpdate,
    StudyAssignmentCancel,
    StudyPlanAssign,
    StudyPlanAssignPreview,
    StudyPlanCreate,
    StudyPlanItemsReplace,
    StudyPlanUpdate,
)
from app.content.store import ContentStore
from app.core.admin_deps import get_current_admin, require_admin_roles
from app.core.db import get_db
from app.core.deps import get_store
from app.core.errors import AppError
from app.services import homeworks, study_plans, subject_catalog
from app.services.admin_auth import record_audit
from app.users.models import AdminUser, StudyPlan, StudyPlanAssignment, User

router = APIRouter(prefix="/admin", tags=["admin-study-plans"])

WRITE_ROLES = ("super_admin", "content_editor")


def _admin_subject(subject: Optional[str]) -> str:
    subject_id = (subject or "psychology").strip()
    if not subject_catalog.get_subject_config(subject_id):
        raise AppError(400, "SUBJECT_INVALID", "科目分类不存在")
    return subject_id


# ---------------------------------------------------------------------------
# Classroom homeworks
# ---------------------------------------------------------------------------
@router.get("/homeworks")
def list_homeworks(
    q: Optional[str] = None,
    unit: Optional[str] = None,
    topic: Optional[str] = None,
    status: str = "active",
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    subject: Optional[str] = None,
    db: Session = Depends(get_db),
    store: ContentStore = Depends(get_store),
    admin: AdminUser = Depends(get_current_admin),
):
    subject_id = _admin_subject(subject)
    return homeworks.list_homeworks(
        db,
        store,
        subject_id=subject_id,
        q=q,
        unit_id=unit,
        topic_id=topic,
        status=status,
        limit=limit,
        offset=offset,
    )


@router.post("/homeworks")
def create_homework(
    body: HomeworkCreate,
    request: Request,
    subject: Optional[str] = None,
    db: Session = Depends(get_db),
    store: ContentStore = Depends(get_store),
    admin: AdminUser = Depends(require_admin_roles(*WRITE_ROLES)),
):
    subject_id = _admin_subject(body.subject_id or subject)
    if store.subject_id != subject_id:
        raise AppError(400, "SUBJECT_MISMATCH", "科目不匹配")
    result = homeworks.create_homework(
        db,
        store,
        subject_id=subject_id,
        title=body.title,
        note=body.note,
        unit_id=body.unit_id,
        topic_id=body.topic_id,
        question_ids=body.question_ids,
        created_by=admin.id,
    )
    record_audit(
        db,
        admin,
        "homework.create",
        target_type="classroom_homework",
        target_id=result["id"],
        detail={"subject_id": subject_id, "question_count": result["question_count"]},
        request=request,
    )
    db.commit()
    return result


@router.get("/homeworks/{homework_id}")
def get_homework(
    homework_id: str,
    subject: Optional[str] = None,
    db: Session = Depends(get_db),
    store: ContentStore = Depends(get_store),
    admin: AdminUser = Depends(get_current_admin),
):
    return homeworks.get_homework(db, store, homework_id, _admin_subject(subject))


@router.patch("/homeworks/{homework_id}")
def update_homework(
    homework_id: str,
    body: HomeworkUpdate,
    request: Request,
    subject: Optional[str] = None,
    db: Session = Depends(get_db),
    store: ContentStore = Depends(get_store),
    admin: AdminUser = Depends(require_admin_roles(*WRITE_ROLES)),
):
    subject_id = _admin_subject(subject)
    result = homeworks.update_homework(
        db,
        store,
        homework_id,
        subject_id=subject_id,
        title=body.title,
        note=body.note,
        unit_id=body.unit_id,
        topic_id=body.topic_id,
        question_ids=body.question_ids,
    )
    record_audit(
        db,
        admin,
        "homework.update",
        target_type="classroom_homework",
        target_id=homework_id,
        detail={"subject_id": subject_id, "version": result["version"]},
        request=request,
    )
    db.commit()
    return result


@router.put("/homeworks/{homework_id}/questions")
def replace_homework_questions(
    homework_id: str,
    body: HomeworkQuestionsReplace,
    request: Request,
    subject: Optional[str] = None,
    db: Session = Depends(get_db),
    store: ContentStore = Depends(get_store),
    admin: AdminUser = Depends(require_admin_roles(*WRITE_ROLES)),
):
    subject_id = _admin_subject(subject)
    result = homeworks.update_homework(
        db,
        store,
        homework_id,
        subject_id=subject_id,
        question_ids=body.question_ids,
    )
    record_audit(
        db,
        admin,
        "homework.questions.update",
        target_type="classroom_homework",
        target_id=homework_id,
        detail={"subject_id": subject_id, "question_count": result["question_count"]},
        request=request,
    )
    db.commit()
    return result


@router.post("/homeworks/{homework_id}/duplicate")
def duplicate_homework(
    homework_id: str,
    request: Request,
    subject: Optional[str] = None,
    db: Session = Depends(get_db),
    store: ContentStore = Depends(get_store),
    admin: AdminUser = Depends(require_admin_roles(*WRITE_ROLES)),
):
    subject_id = _admin_subject(subject)
    result = homeworks.duplicate_homework(
        db, store, homework_id, subject_id, created_by=admin.id
    )
    record_audit(
        db,
        admin,
        "homework.duplicate",
        target_type="classroom_homework",
        target_id=result["id"],
        detail={"subject_id": subject_id, "source_id": homework_id},
        request=request,
    )
    db.commit()
    return result


@router.delete("/homeworks/{homework_id}")
def delete_homework(
    homework_id: str,
    request: Request,
    subject: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin_roles(*WRITE_ROLES)),
):
    subject_id = _admin_subject(subject)
    result = homeworks.delete_homework(db, homework_id, subject_id)
    record_audit(
        db,
        admin,
        "homework.delete",
        target_type="classroom_homework",
        target_id=homework_id,
        detail={"subject_id": subject_id},
        request=request,
    )
    db.commit()
    return result


@router.get("/content/taxonomy")
def content_taxonomy(
    subject: Optional[str] = None,
    store: ContentStore = Depends(get_store),
    admin: AdminUser = Depends(get_current_admin),
):
    _admin_subject(subject)
    return homeworks.taxonomy(store)


# ---------------------------------------------------------------------------
# Study plans
# ---------------------------------------------------------------------------
@router.get("/study-plans")
def list_plans(
    q: Optional[str] = None,
    status: str = "active",
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    subject: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    return study_plans.list_plans(
        db,
        subject_id=_admin_subject(subject),
        q=q,
        status=status,
        limit=limit,
        offset=offset,
    )


@router.post("/study-plans")
def create_plan(
    body: StudyPlanCreate,
    request: Request,
    subject: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin_roles(*WRITE_ROLES)),
):
    subject_id = _admin_subject(body.subject_id or subject)
    result = study_plans.create_plan(
        db,
        subject_id=subject_id,
        title=body.title,
        note=body.note,
        category=body.category,
        color=body.color,
        created_by=admin.id,
    )
    record_audit(
        db,
        admin,
        "study_plan.create",
        target_type="study_plan",
        target_id=result["id"],
        detail={"subject_id": subject_id},
        request=request,
    )
    db.commit()
    return result


@router.get("/study-plans/{plan_id}")
def get_plan(
    plan_id: str,
    subject: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    return study_plans.get_plan(db, plan_id, _admin_subject(subject))


@router.patch("/study-plans/{plan_id}")
def update_plan(
    plan_id: str,
    body: StudyPlanUpdate,
    request: Request,
    subject: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin_roles(*WRITE_ROLES)),
):
    subject_id = _admin_subject(subject)
    result = study_plans.update_plan(
        db,
        plan_id,
        subject_id=subject_id,
        title=body.title,
        note=body.note,
        category=body.category,
        color=body.color,
        status=body.status,
    )
    record_audit(
        db,
        admin,
        "study_plan.update",
        target_type="study_plan",
        target_id=plan_id,
        detail={"subject_id": subject_id, "version": result["version"]},
        request=request,
    )
    db.commit()
    return result


@router.put("/study-plans/{plan_id}/items")
def replace_plan_items(
    plan_id: str,
    body: StudyPlanItemsReplace,
    request: Request,
    subject: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin_roles(*WRITE_ROLES)),
):
    subject_id = _admin_subject(subject)
    result = study_plans.replace_plan_items(
        db,
        plan_id,
        subject_id=subject_id,
        items=[item.model_dump() for item in body.items],
    )
    record_audit(
        db,
        admin,
        "study_plan.items.update",
        target_type="study_plan",
        target_id=plan_id,
        detail={"subject_id": subject_id, "item_count": result["item_count"]},
        request=request,
    )
    db.commit()
    return result


@router.post("/study-plans/{plan_id}/assign-preview")
def assign_preview(
    plan_id: str,
    body: StudyPlanAssignPreview,
    subject: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    subject_id = _admin_subject(subject)
    plan_row = db.get(StudyPlan, plan_id)
    if plan_row is None or plan_row.subject_id != subject_id:
        raise AppError(404, "PLAN_NOT_FOUND", "学习计划不存在")
    return study_plans.assign_preview(db, plan_row, body.start_date, body.end_date)


@router.post("/study-plans/{plan_id}/assign")
def assign_plan(
    plan_id: str,
    body: StudyPlanAssign,
    request: Request,
    subject: Optional[str] = None,
    db: Session = Depends(get_db),
    store: ContentStore = Depends(get_store),
    admin: AdminUser = Depends(require_admin_roles(*WRITE_ROLES)),
):
    subject_id = _admin_subject(subject)
    plan = db.get(StudyPlan, plan_id)
    if plan is None or plan.subject_id != subject_id:
        raise AppError(404, "PLAN_NOT_FOUND", "学习计划不存在")
    users = db.scalars(
        select(User).where(User.id.in_(body.student_ids))
    ).all()
    found = {user.id for user in users}
    missing = [user_id for user_id in body.student_ids if user_id not in found]
    if missing:
        raise AppError(404, "STUDENT_NOT_FOUND", f"{len(missing)} 名学生不存在")
    result = study_plans.create_assignments(
        db,
        plan=plan,
        users=list(users),
        start_date=body.start_date,
        end_date=body.end_date,
        assigned_by=admin.id,
        note=body.note,
        content_release_id=store.release_id,
    )
    record_audit(
        db,
        admin,
        "study_plan.assign",
        target_type="study_plan",
        target_id=plan_id,
        detail={
            "subject_id": subject_id,
            "assigned": len(result["assigned"]),
            "skipped": len(result["skipped"]),
            "start_date": body.start_date.isoformat(),
            "end_date": body.end_date.isoformat(),
        },
        request=request,
    )
    db.commit()
    return result


@router.get("/study-plan-assignments")
def list_assignments(
    plan_id: Optional[str] = None,
    user_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    return study_plans.list_assignments(
        db,
        plan_id=plan_id,
        user_id=user_id,
        status=status,
        limit=limit,
        offset=offset,
    )


@router.get("/study-plan-assignments/{assignment_id}")
def get_assignment(
    assignment_id: str,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    return study_plans.assignment_detail(db, assignment_id)


@router.post("/study-plan-assignments/{assignment_id}/cancel")
def cancel_assignment(
    assignment_id: str,
    body: StudyAssignmentCancel,
    request: Request,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin_roles(*WRITE_ROLES)),
):
    assignment = db.get(StudyPlanAssignment, assignment_id)
    if assignment is None:
        raise AppError(404, "ASSIGNMENT_NOT_FOUND", "学习计划指派不存在")
    result = study_plans.cancel_assignment(
        db, assignment, admin.id, reason=body.reason
    )
    record_audit(
        db,
        admin,
        "study_plan.assignment.cancel",
        target_type="study_plan_assignment",
        target_id=assignment_id,
        detail={"plan_id": assignment.plan_id, "student_id": assignment.user_id},
        request=request,
    )
    db.commit()
    return result


@router.delete("/study-plans/{plan_id}")
def delete_plan(
    plan_id: str,
    request: Request,
    subject: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin_roles(*WRITE_ROLES)),
):
    subject_id = _admin_subject(subject)
    result = study_plans.delete_plan(db, plan_id, subject_id)
    record_audit(
        db,
        admin,
        "study_plan.delete",
        target_type="study_plan",
        target_id=plan_id,
        detail={"subject_id": subject_id},
        request=request,
    )
    db.commit()
    return result
