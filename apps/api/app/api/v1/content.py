from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.content.store import ContentStore
from app.core.config import REPO_ROOT
from app.core.db import get_db
from app.core.deps import get_current_user, get_store
from app.core.errors import AppError
from app.services import entitlements, exam_engine, knowledge_graph, progress
from app.users.models import (
    Attempt,
    AttemptAnswer,
    AttemptQuestion,
    AttemptSection,
    User,
)

router = APIRouter(tags=["content"])


@router.get("/content/version")
def content_version(store: ContentStore = Depends(get_store)):
    return store.version()


SUBJECT_NAMES = {
    "psychology": ("AP Psychology", "AP 心理学"),
}


@router.get("/knowledge-graph")
def get_knowledge_graph(
    store: ContentStore = Depends(get_store),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Return the knowledge graph for units the current user can access.

    Locked units expose only their metadata, never concepts or edges. This is
    the same subject-level entitlement rule used by Unit practice: free units
    remain visible; other units require an active subject entitlement.
    """
    units = []
    overrides = knowledge_graph.load_overrides(db, store.subject_id)
    for group in store.list_groups():
        unit_id = str(group.get("unit_id"))
        locked = entitlements.is_group_locked(
            db, user.id, store.subject_id, unit_id
        )
        item = {
            "unit_id": unit_id,
            "group_id": group.get("group_id"),
            "title": group.get("title"),
            "title_en": group.get("title_en"),
            "topic_count": group.get("topic_count", 0),
            "question_count": group.get("question_count", 0),
            "locked": locked,
        }
        if not locked:
            graph = store.unit_knowledge_graph(
                unit_id, overrides=overrides.get(unit_id)
            )
            if graph:
                item.update(graph)
        units.append(item)
    return {
        "release_id": store.release_id,
        "subject_id": store.subject_id,
        "units": units,
    }


@router.get("/knowledge-graph/questions/{question_id}")
def get_knowledge_graph_question_preview(
    question_id: str,
    store: ContentStore = Depends(get_store),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Read-only question preview used by the knowledge graph.

    A question belongs to Unit practice when its practice-topic attachment is
    available; otherwise the source paper access rule applies. The payload does
    not include correctness or explanations, so it cannot be used as a scoring
    endpoint.
    """
    questions = store.get_questions([question_id], include_answers=False)
    question = questions.get(question_id)
    if not question:
        raise AppError(404, "QUESTION_NOT_FOUND", "题目不存在")
    context = store.question_context(question_id)
    unit_id = context.get("unit_id") if context else None
    if unit_id:
        if entitlements.is_group_locked(db, user.id, store.subject_id, unit_id):
            raise AppError(403, "CONTENT_LOCKED", "该题所属 Unit 尚未解锁")
    else:
        entitlements.assert_paper_access(db, user.id, store, question["paper_id"])
    return question


@router.get("/subjects")
def subjects():
    releases = REPO_ROOT / "data" / "releases"
    subject_ids: set[str] = set()
    active_root = releases / "active"
    active_manifest = active_root / "release.json"
    if active_manifest.exists():
        # Merged Release: subjects come from the manifest, not from files in
        # the Release directory (exam.db/assets/... are not subjects).
        try:
            payload = json.loads(active_manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = {}
        subjects = payload.get("subjects")
        if not isinstance(subjects, list) or not subjects:
            subjects = [payload.get("subject_id") or "psychology"]
        subject_ids.update(str(item) for item in subjects)
    elif active_root.exists():
        # Transitional active/<subject> directory layout.
        for path in active_root.iterdir():
            if path.name.startswith("."):
                continue
            if path.is_dir() or path.is_symlink():
                subject_ids.add(path.name)
    # Backward-compatible single-subject pointer.
    legacy = releases / "current"
    if legacy.exists() or legacy.is_symlink():
        subject_ids.add("psychology")
    if not subject_ids:
        subject_ids.add("psychology")
    out = []
    for subject_id in sorted(subject_ids):
        name, name_zh = SUBJECT_NAMES.get(subject_id, (subject_id, subject_id))
        out.append({"subject_id": subject_id, "name": name, "name_zh": name_zh})
    return out


@router.get("/practice-groups")
def list_practice_groups(
    store: ContentStore = Depends(get_store),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    groups = progress.unit_progress(db, store, user.id)
    entitlements.mark_locked_groups(db, user.id, store.subject_id, groups)
    return groups


@router.get("/practice-groups/{group_id}")
def get_practice_group(
    group_id: str,
    store: ContentStore = Depends(get_store),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    group = store.get_group(group_id)
    if not group:
        raise AppError(404, "GROUP_NOT_FOUND", "单元不存在")
    group["locked"] = entitlements.is_group_locked(
        db, user.id, store.subject_id, group.get("unit_id")
    )
    topics = store.list_topics(group_id)
    group["topic_count"] = len(topics)
    group["question_count"] = sum(t["question_count"] for t in topics)
    ids = store.question_ids_for_group(group_id)
    agg = progress.aggregate(db, user.id, ids)
    group.update(agg)
    group["accuracy"] = round(agg["correct"] / agg["answered"], 3) if agg["answered"] else None
    return group


@router.get("/practice-groups/{group_id}/topics")
def list_topics(
    group_id: str,
    store: ContentStore = Depends(get_store),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    group = store.get_group(group_id)
    if not group:
        raise AppError(404, "GROUP_NOT_FOUND", "单元不存在")
    locked = entitlements.is_group_locked(db, user.id, store.subject_id, group.get("unit_id"))
    topics = progress.topic_progress(db, store, user.id, group_id)
    for topic in topics:
        topic["locked"] = locked
    return topics


@router.get("/practice-groups/{group_id}/topics/{topic_id}")
def get_topic(
    group_id: str,
    topic_id: str,
    store: ContentStore = Depends(get_store),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    topic = store.get_topic(topic_id)
    if not topic or topic["group_id"] != group_id:
        raise AppError(404, "TOPIC_NOT_FOUND", "Topic 不存在")
    group = store.get_group(group_id)
    topic["locked"] = entitlements.is_group_locked(
        db, user.id, store.subject_id, group.get("unit_id") if group else None
    )
    topic["concepts"] = store.get_topic_concepts(topic_id)
    ids = store.question_ids_for_topic(topic_id)
    agg = progress.aggregate(db, user.id, ids)
    topic.update(agg)
    topic["accuracy"] = round(agg["correct"] / agg["answered"], 3) if agg["answered"] else None
    return topic


@router.get("/papers")
def list_papers(
    paper_type: Optional[str] = None,
    store: ContentStore = Depends(get_store),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    papers = store.list_papers(paper_type)
    entitlements.mark_locked_papers(db, user.id, store.subject_id, papers)
    return papers


def _active_attempts(db: Session, user: User, paper_id: str) -> list[dict]:
    attempts = list(
        db.scalars(
            select(Attempt)
            .where(
                Attempt.user_id == user.id,
                Attempt.paper_id == paper_id,
                Attempt.status.in_(["in_progress", "awaiting_self_grade"]),
            )
            .order_by(Attempt.updated_at.desc())
        )
    )
    out = []
    for attempt in attempts:
        section_name = attempt.current_section or "mcq"
        section = db.scalar(
            select(AttemptSection).where(
                AttemptSection.attempt_id == attempt.id,
                AttemptSection.section == section_name,
            )
        )
        total = (
            db.scalar(
                select(func.count())
                .select_from(AttemptQuestion)
                .where(
                    AttemptQuestion.attempt_id == attempt.id,
                    AttemptQuestion.section == section_name,
                )
            )
            or 0
        )
        answered = (
            db.scalar(
                select(func.count())
                .select_from(AttemptAnswer)
                .where(
                    AttemptAnswer.attempt_id == attempt.id,
                    AttemptAnswer.question_id.in_(
                        select(AttemptQuestion.question_id).where(
                            AttemptQuestion.attempt_id == attempt.id,
                            AttemptQuestion.section == section_name,
                        )
                    ),
                    or_(
                        AttemptAnswer.selected_label.is_not(None),
                        AttemptAnswer.frq_text.is_not(None),
                    ),
                )
            )
            or 0
        )
        out.append(
            {
                "id": attempt.id,
                "mode": attempt.mode,
                "frq_form": attempt.frq_form,
                "status": attempt.status,
                "current_section": section_name,
                "section_status": section.status if section else None,
                "answered": int(answered),
                "total": int(total),
                "mcq_score": attempt.mcq_score,
                "mcq_total": attempt.mcq_total,
                "frq_score": attempt.frq_score,
                "frq_total": attempt.frq_total,
                "updated_at": attempt.updated_at,
            }
        )
    return out


@router.get("/papers/{paper_id}")
def get_paper(
    paper_id: str,
    store: ContentStore = Depends(get_store),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    paper = store.get_paper(paper_id)
    if not paper:
        raise AppError(404, "PAPER_NOT_FOUND", "试卷不存在")
    paper["locked"] = entitlements.is_paper_locked(db, user.id, store.subject_id, paper_id)
    exam_engine.finalize_expired_for_paper(db, store, user, paper_id)
    paper["active_attempts"] = _active_attempts(db, user, paper_id)
    return paper
