from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.v1.schemas import (
    KnowledgeGraphCustomConceptCreate,
    KnowledgeGraphTopicSave,
)
from app.content.store import ContentStore
from app.core.admin_deps import get_current_admin, require_admin_roles
from app.core.db import get_db
from app.core.deps import get_store
from app.services import knowledge_graph as graph
from app.services.admin_auth import record_audit
from app.users.models import AdminUser

router = APIRouter(prefix="/admin/content/knowledge-graph", tags=["admin"])

_EDITOR_ROLES = ("super_admin", "content_editor")


@router.get("/units")
def admin_graph_units(
    store: ContentStore = Depends(get_store),
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    return {
        "units": graph.list_units_and_topics(
            store, db, subject_id=store.subject_id
        ),
        "can_edit": admin.role in _EDITOR_ROLES,
        "subject_id": store.subject_id,
    }


@router.get("/topic")
def admin_graph_topic(
    unit_id: str = Query(min_length=1, max_length=16),
    topic_code: str = Query(min_length=1, max_length=16),
    store: ContentStore = Depends(get_store),
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    payload = graph.get_editor_tree(
        store, db, unit_id, topic_code, subject_id=store.subject_id
    )
    payload["can_edit"] = admin.role in _EDITOR_ROLES
    return payload


@router.get("/search")
def admin_graph_search(
    unit_id: str = Query(min_length=1, max_length=16),
    q: str = Query(default="", max_length=200),
    limit: int = Query(default=20, ge=1, le=50),
    store: ContentStore = Depends(get_store),
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    return graph.search_local(
        store, db, unit_id, q, limit, subject_id=store.subject_id
    )


@router.post("/custom-concepts")
def admin_graph_create_custom_concept(
    body: KnowledgeGraphCustomConceptCreate,
    request: Request,
    store: ContentStore = Depends(get_store),
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin_roles(*_EDITOR_ROLES)),
):
    graph.assert_unit_exists(store, body.unit_id)
    payload = graph.create_custom_concept(
        db,
        admin,
        body.unit_id,
        body.name,
        body.definition,
        body.topic_code,
        subject_id=store.subject_id,
    )
    record_audit(
        db,
        admin,
        "knowledge_graph.custom_concept.create",
        target_type="knowledge_graph_concept",
        target_id=payload["concept_id"],
        detail={"unit_id": body.unit_id, "topic_code": body.topic_code},
        request=request,
    )
    db.commit()
    return payload


@router.put("/topic")
def admin_graph_save_topic(
    body: KnowledgeGraphTopicSave,
    request: Request,
    store: ContentStore = Depends(get_store),
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin_roles(*_EDITOR_ROLES)),
):
    payload = graph.save_topic_tree(
        store,
        db,
        admin,
        body.unit_id,
        body.topic_code,
        body.tree,
        body.expected_revision,
        subject_id=store.subject_id,
    )
    record_audit(
        db,
        admin,
        "knowledge_graph.topic.save",
        target_type="knowledge_graph_topic",
        target_id=f"{body.unit_id}:{body.topic_code}",
        detail={
            "revision": payload["revision"],
            "node_count": payload["node_count"],
            "duplicate_concept_ids": payload["duplicate_concept_ids"],
        },
        request=request,
    )
    db.commit()
    return payload


@router.delete("/topic")
def admin_graph_reset_topic(
    request: Request,
    unit_id: str = Query(min_length=1, max_length=16),
    topic_code: str = Query(min_length=1, max_length=16),
    store: ContentStore = Depends(get_store),
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin_roles(*_EDITOR_ROLES)),
):
    payload = graph.reset_topic_tree(
        db, unit_id, topic_code, subject_id=store.subject_id
    )
    record_audit(
        db,
        admin,
        "knowledge_graph.topic.reset",
        target_type="knowledge_graph_topic",
        target_id=f"{unit_id}:{topic_code}",
        detail={"revision": payload["revision"]},
        request=request,
    )
    db.commit()
    return payload
