from __future__ import annotations

import re
import uuid
from collections import Counter
from typing import Any, Iterable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.content.store import ContentStore
from app.core.errors import AppError
from app.users.models import (
    AdminUser,
    KnowledgeGraphCustomConcept,
    KnowledgeGraphTopicDraft,
)

SUBJECT_ID = "psychology"
MAX_TREE_DEPTH = 8
MAX_TREE_NODES = 300
MAX_LABEL_LENGTH = 300
MAX_DEFINITION_LENGTH = 8000
NODE_TYPES = {"branch", "concept", "supplement"}
_ASCII_LABEL = re.compile(r"^[\x20-\x7e]+$")
_LABEL_TRANSLATION = str.maketrans(
    {
        "’": "'",
        "‘": "'",
        "“": '"',
        "”": '"',
        "–": "-",
        "—": "-",
        "\u00a0": " ",
    }
)


def _ascii_label(value: str) -> str:
    return " ".join(str(value or "").translate(_LABEL_TRANSLATION).split())


# --------------------------------------------------------------------- loading
def load_overrides(
    db: Session, subject_id: str = SUBJECT_ID
) -> dict[str, dict[str, Any]]:
    """Return ``{unit_id: {topic_code: tree}}`` from app-side admin drafts."""
    rows = db.scalars(
        select(KnowledgeGraphTopicDraft).where(
            KnowledgeGraphTopicDraft.subject_id == subject_id
        )
    ).all()
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        tree = row.tree if isinstance(row.tree, dict) else None
        if not tree:
            continue
        out.setdefault(str(row.unit_id), {})[str(row.topic_code)] = tree
    return out


def get_topic_draft(
    db: Session, unit_id: str, topic_code: str, subject_id: str = SUBJECT_ID
) -> Optional[KnowledgeGraphTopicDraft]:
    return db.scalar(
        select(KnowledgeGraphTopicDraft).where(
            KnowledgeGraphTopicDraft.subject_id == subject_id,
            KnowledgeGraphTopicDraft.unit_id == str(unit_id),
            KnowledgeGraphTopicDraft.topic_code == str(topic_code),
        )
    )


# ------------------------------------------------------------------- unit/topic
def _unit_context(
    store: ContentStore, unit_id: str
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, dict[str, Any]]]:
    unit_id = str(unit_id)
    group = next(
        (item for item in store.list_groups() if str(item.get("unit_id")) == unit_id),
        None,
    )
    if not group:
        raise AppError(404, "UNIT_NOT_FOUND", "Unit 不存在")
    topics = store.list_topics(str(group["group_id"]))
    return group, topics, store.unit_mindmaps(unit_id)


def assert_unit_exists(store: ContentStore, unit_id: str) -> dict[str, Any]:
    group, _, _ = _unit_context(store, unit_id)
    return group


def _topic_meta(
    topics: Iterable[dict[str, Any]], topic_code: str
) -> Optional[dict[str, Any]]:
    return next(
        (item for item in topics if str(item.get("code")) == str(topic_code)),
        None,
    )


def list_units_and_topics(
    store: ContentStore, db: Session, subject_id: str = SUBJECT_ID
) -> list[dict[str, Any]]:
    drafts = {
        (str(row.unit_id), str(row.topic_code)): row
        for row in db.scalars(
            select(KnowledgeGraphTopicDraft).where(
                KnowledgeGraphTopicDraft.subject_id == subject_id
            )
        ).all()
    }
    out: list[dict[str, Any]] = []
    for group in store.list_groups():
        unit_id = str(group.get("unit_id") or "")
        if not unit_id:
            continue
        topics = store.list_topics(str(group["group_id"]))
        base = store.unit_mindmaps(unit_id)
        by_code = {str(item.get("code")): item for item in topics}
        codes = list(by_code)
        for code in base:
            if code not in by_code:
                codes.append(code)
        topic_items = []
        for code in codes:
            meta = by_code.get(code) or {}
            draft = drafts.get((unit_id, code))
            effective = draft.tree if draft and isinstance(draft.tree, dict) else None
            if effective is None:
                effective = base.get(code)
            title = (
                str(meta.get("title_en") or "").strip()
                or str((effective or {}).get("label") or "").strip()
                or code
            )
            topic_items.append(
                {
                    "topic_code": code,
                    "topic_id": meta.get("topic_id"),
                    "title_en": title,
                    "title_zh": meta.get("title_zh") or "",
                    "kind": meta.get("kind") or "ced",
                    "has_mindmap": code in base,
                    "has_draft": draft is not None,
                    "revision": int(draft.revision) if draft else 0,
                    "node_count": _count_tree(effective) if effective else 0,
                }
            )
        out.append(
            {
                "unit_id": unit_id,
                "group_id": str(group.get("group_id") or ""),
                "title": str(group.get("title") or ""),
                "title_en": str(group.get("title_en") or ""),
                "topics": topic_items,
            }
        )
    return out


# -------------------------------------------------------------------- tree view
def _node(payload: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": str(payload.get("id") or ""),
        "label": str(payload.get("label") or ""),
        "type": str(payload.get("type") or "branch"),
        "children": list(payload.get("children") or []),
    }
    concept_id = payload.get("concept_id")
    if concept_id:
        out["concept_id"] = str(concept_id)
    concept_name = payload.get("concept_name")
    if concept_name:
        out["concept_name"] = str(concept_name)
    supplement = payload.get("supplement")
    if isinstance(supplement, dict):
        out["supplement"] = {
            "id": str(supplement.get("id") or ""),
            "name": str(supplement.get("name") or ""),
            "definition": str(supplement.get("definition") or ""),
            "source": str(supplement.get("source") or "ai_supplement"),
            "review_status": str(supplement.get("review_status") or "draft"),
        }
    definition = payload.get("definition")
    if definition:
        out["definition"] = str(definition)
    return out


def _resolved_to_editor(
    node: dict[str, Any],
    concepts: dict[str, dict[str, Any]],
    prefix: str,
    path: tuple[int, ...],
) -> dict[str, Any]:
    node_id = f"{prefix}-{'-'.join(str(part) for part in path)}"
    supplement = node.get("supplement")
    concept_id = str(node.get("concept_id") or "") or None
    if supplement:
        kind = "supplement"
    elif concept_id:
        kind = "concept"
    else:
        kind = "branch"
    payload: dict[str, Any] = {
        "id": node_id,
        "label": _ascii_label(node.get("label") or ""),
        "type": kind,
        "concept_id": concept_id,
        "concept_name": node.get("concept_name") or None,
        "children": [
            _resolved_to_editor(child, concepts, prefix, path + (index,))
            for index, child in enumerate(node.get("children") or [])
        ],
    }
    if supplement:
        payload["supplement"] = {
            "id": str(supplement.get("id") or concept_id or node_id),
            "name": _ascii_label(
                supplement.get("name")
                or node.get("concept_name")
                or node.get("label")
                or ""
            ),
            "definition": str(supplement.get("definition") or ""),
            "source": str(supplement.get("source") or "ai_supplement"),
            "review_status": str(supplement.get("review_status") or "draft"),
        }
    elif concept_id and concept_id in concepts:
        row = concepts[concept_id]
        payload["definition"] = str(
            row.get("plain_en") or row.get("definition_quote") or ""
        )
        payload["tier"] = str(row.get("weight_tier") or "")
    return payload


def _normalise_draft(
    node: dict[str, Any],
    concepts: dict[str, dict[str, Any]],
    prefix: str,
    path: tuple[int, ...],
    *,
    is_root: bool = False,
) -> dict[str, Any]:
    node_id = str(node.get("id") or "").strip() or (
        f"{prefix}-{'-'.join(str(part) for part in path)}"
    )
    supplement = node.get("supplement") if isinstance(node.get("supplement"), dict) else None
    concept_id = str(node.get("concept_id") or "") or None
    if supplement:
        kind = "supplement"
        concept_id = str(supplement.get("id") or concept_id or node_id)
    elif concept_id:
        kind = "concept"
    else:
        kind = "branch"
    if is_root:
        kind = "branch"
        concept_id = None
        supplement = None
    payload: dict[str, Any] = {
        "id": node_id,
        "label": str(node.get("label") or ""),
        "type": kind,
        "children": [
            _normalise_draft(
                child,
                concepts,
                prefix,
                path + (index,),
                is_root=False,
            )
            for index, child in enumerate(node.get("children") or [])
            if isinstance(child, dict)
        ],
    }
    if concept_id:
        payload["concept_id"] = concept_id
    if node.get("concept_name"):
        payload["concept_name"] = str(node.get("concept_name"))
    elif kind == "concept" and concept_id in concepts:
        payload["concept_name"] = str(concepts[concept_id].get("canonical_name") or "")
    if supplement:
        payload["supplement"] = {
            "id": str(supplement.get("id") or concept_id or node_id),
            "name": _ascii_label(
                supplement.get("name") or payload.get("label") or ""
            ),
            "definition": str(supplement.get("definition") or ""),
            "source": str(supplement.get("source") or "ai_supplement"),
            "review_status": str(supplement.get("review_status") or "draft"),
        }
    if kind == "concept" and concept_id in concepts:
        row = concepts[concept_id]
        payload["definition"] = str(
            row.get("plain_en") or row.get("definition_quote") or ""
        )
        payload["tier"] = str(row.get("weight_tier") or "")
    return payload


def _base_editor_tree(
    base: Optional[dict[str, Any]],
    topic: Optional[dict[str, Any]],
    topic_code: str,
    unit_id: str,
    concepts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    prefix = f"base-{unit_id}-{topic_code}"
    if base:
        children = base.get("children") or []
        return {
            "id": f"root-{unit_id}-{topic_code}",
            "label": str(base.get("label") or (topic or {}).get("title_en") or topic_code),
            "type": "branch",
            "children": [
                _resolved_to_editor(child, concepts, prefix, (index,))
                for index, child in enumerate(children)
            ],
        }
    return {
        "id": f"root-{unit_id}-{topic_code}",
        "label": str((topic or {}).get("title_en") or topic_code),
        "type": "branch",
        "children": [],
    }


def get_editor_tree(
    store: ContentStore,
    db: Session,
    unit_id: str,
    topic_code: str,
    subject_id: str = SUBJECT_ID,
) -> dict[str, Any]:
    group, topics, base_map = _unit_context(store, unit_id)
    topic = _topic_meta(topics, topic_code)
    base = base_map.get(str(topic_code))
    if topic is None and base is None:
        raise AppError(404, "TOPIC_NOT_FOUND", "Topic 不存在")
    concepts = store.get_unit_concepts(str(unit_id))
    draft = get_topic_draft(db, unit_id, topic_code, subject_id)
    if draft and isinstance(draft.tree, dict):
        tree = _normalise_draft(
            draft.tree,
            concepts,
            f"draft-{unit_id}-{topic_code}",
            (),
            is_root=True,
        )
        source = "draft"
        revision = int(draft.revision)
    else:
        tree = _base_editor_tree(
            base,
            topic,
            str(topic_code),
            str(unit_id),
            concepts,
        )
        source = "release"
        revision = 0
    if not tree.get("label"):
        tree["label"] = str(
            (topic or {}).get("title_en") or (base or {}).get("label") or topic_code
        )
    duplicate_ids, duplicate_labels, unresolved = _tree_warnings(tree, concepts)
    return {
        "unit_id": str(unit_id),
        "group_id": str(group["group_id"]),
        "topic_code": str(topic_code),
        "title_en": (
            str((topic or {}).get("title_en") or "").strip()
            or str(tree.get("label") or "")
            or str(topic_code)
        ),
        "title_zh": str((topic or {}).get("title_zh") or ""),
        "source": source,
        "revision": revision,
        "node_count": _count_tree(tree),
        "tree": tree,
        "duplicate_concept_ids": duplicate_ids,
        "duplicate_labels": duplicate_labels,
        "unresolved_concept_ids": unresolved,
    }


# ---------------------------------------------------------------------- search
def _search_key(value: str) -> str:
    text = str(value or "").replace("’", "'").lower()
    return " ".join("".join(ch if ch.isalnum() else " " for ch in text).split())


def _walk(node: dict[str, Any]) -> Iterable[dict[str, Any]]:
    yield node
    for child in node.get("children") or []:
        if isinstance(child, dict):
            yield from _walk(child)


def search_local(
    store: ContentStore,
    db: Session,
    unit_id: str,
    q: str,
    limit: int = 20,
    subject_id: str = SUBJECT_ID,
) -> dict[str, Any]:
    query = _search_key(q)
    if not query:
        return {"results": [], "total": 0}
    _, topics, base_map = _unit_context(store, unit_id)
    concepts = store.get_unit_concepts(str(unit_id))

    concept_topic: dict[str, str] = {}
    supplement_rows: dict[str, dict[str, Any]] = {}
    for code, tree in base_map.items():
        for node in _walk({"children": tree.get("children") or []}):
            cid = node.get("concept_id")
            if cid:
                concept_topic.setdefault(str(cid), str(code))
            supplement = node.get("supplement")
            if supplement and supplement.get("id"):
                sid = str(supplement["id"])
                supplement_rows.setdefault(
                    sid,
                    {
                        "kind": "supplement",
                        "concept_id": sid,
                        "name": str(supplement.get("name") or node.get("label") or ""),
                        "definition": str(supplement.get("definition") or ""),
                        "source": str(supplement.get("source") or "ai_supplement"),
                        "review_status": str(
                            supplement.get("review_status") or "draft"
                        ),
                        "topic_code": str(code),
                    },
                )

    # Draft trees may introduce supplements that are not in the shipped JSON.
    for row in db.scalars(
        select(KnowledgeGraphTopicDraft).where(
            KnowledgeGraphTopicDraft.subject_id == subject_id,
            KnowledgeGraphTopicDraft.unit_id == str(unit_id),
        )
    ).all():
        if not isinstance(row.tree, dict):
            continue
        for node in _walk({"children": row.tree.get("children") or []}):
            supplement = node.get("supplement")
            if supplement and supplement.get("id"):
                sid = str(supplement["id"])
                supplement_rows.setdefault(
                    sid,
                    {
                        "kind": "supplement",
                        "concept_id": sid,
                        "name": str(supplement.get("name") or node.get("label") or ""),
                        "definition": str(supplement.get("definition") or ""),
                        "source": str(supplement.get("source") or "ai_supplement"),
                        "review_status": str(
                            supplement.get("review_status") or "draft"
                        ),
                        "topic_code": str(row.topic_code),
                    },
                )

    custom_rows = db.scalars(
        select(KnowledgeGraphCustomConcept).where(
            KnowledgeGraphCustomConcept.subject_id == subject_id,
            KnowledgeGraphCustomConcept.unit_id == str(unit_id),
        )
    ).all()
    custom_by_id = {row.id: row for row in custom_rows}

    results: list[dict[str, Any]] = []
    for cid, row in concepts.items():
        name = str(row.get("canonical_name") or "")
        definition = str(
            row.get("plain_en") or row.get("definition_quote") or ""
        )
        haystack = " ".join(
            [
                name,
                definition,
                str(row.get("topic") or ""),
                str(row.get("section_heading") or ""),
            ]
        )
        if query not in _search_key(haystack):
            continue
        results.append(
            {
                "kind": "concept",
                "concept_id": str(cid),
                "name": name,
                "definition": definition,
                "tier": str(row.get("weight_tier") or ""),
                "topic_code": concept_topic.get(str(cid)),
                "source": "knowledge_db",
            }
        )

    for sid, row in supplement_rows.items():
        custom = custom_by_id.get(sid)
        name = str((custom.name if custom else row["name"]) or "")
        definition = str((custom.definition if custom else row["definition"]) or "")
        if query not in _search_key(f"{name} {definition}"):
            continue
        results.append(
            {
                **row,
                "name": name,
                "definition": definition,
                "source": str(custom.source if custom else row["source"]),
                "review_status": str(
                    custom.review_status if custom else row["review_status"]
                ),
            }
        )

    seen = {(item["kind"], item["concept_id"]) for item in results}
    for custom in custom_rows:
        key = ("supplement", custom.id)
        if key in seen:
            continue
        if query not in _search_key(f"{custom.name} {custom.definition}"):
            continue
        results.append(
            {
                "kind": "supplement",
                "concept_id": custom.id,
                "name": custom.name,
                "definition": custom.definition,
                "source": custom.source,
                "review_status": custom.review_status,
                "topic_code": custom.topic_code,
            }
        )

    def rank(item: dict[str, Any]) -> tuple[int, int, str]:
        name_key = _search_key(str(item.get("name") or ""))
        if name_key == query:
            score = 0
        elif name_key.startswith(query):
            score = 1
        elif query in name_key:
            score = 2
        else:
            score = 3
        kind_rank = 0 if item.get("kind") == "concept" else 1
        return score, kind_rank, name_key

    results.sort(key=rank)
    return {"results": results[:limit], "total": len(results)}


# --------------------------------------------------------------------- create
def create_custom_concept(
    db: Session,
    admin: AdminUser,
    unit_id: str,
    name: str,
    definition: str,
    topic_code: Optional[str] = None,
    subject_id: str = SUBJECT_ID,
) -> dict[str, Any]:
    name = _ascii_label(name)
    definition = str(definition or "").strip()
    _validate_label(name, "知识点名称")
    if not definition:
        raise AppError(400, "DEFINITION_REQUIRED", "请填写知识点释义")
    if len(definition) > MAX_DEFINITION_LENGTH:
        raise AppError(400, "DEFINITION_TOO_LONG", "释义过长")
    concept_id = f"psy-custom-{uuid.uuid4().hex[:12]}"
    row = KnowledgeGraphCustomConcept(
        id=concept_id,
        subject_id=subject_id,
        unit_id=str(unit_id),
        topic_code=str(topic_code) if topic_code else None,
        name=name,
        definition=definition,
        source="admin",
        review_status="draft",
        created_by=admin.id,
    )
    db.add(row)
    db.flush()
    return {
        "concept_id": concept_id,
        "name": name,
        "definition": definition,
        "source": "admin",
        "review_status": "draft",
        "unit_id": str(unit_id),
        "topic_code": str(topic_code) if topic_code else None,
    }


# ----------------------------------------------------------------------- save
def _count_tree(tree: Any) -> int:
    if not isinstance(tree, dict):
        return 0
    return 1 + sum(
        _count_tree(child)
        for child in tree.get("children") or []
        if isinstance(child, dict)
    )


def _tree_warnings(
    tree: dict[str, Any], concepts: dict[str, dict[str, Any]]
) -> tuple[list[str], list[str], list[str]]:
    id_counts: Counter[str] = Counter()
    label_counts: Counter[str] = Counter()
    names: dict[str, str] = {}
    unresolved: list[str] = []
    for node in _walk(tree):
        cid = str(node.get("concept_id") or "")
        if cid and node.get("type") in ("concept", "supplement"):
            id_counts[cid] += 1
            names.setdefault(cid, str(node.get("label") or cid))
            if node.get("type") == "concept" and cid not in concepts:
                unresolved.append(cid)
        label = str(node.get("label") or "").strip().lower()
        if label:
            label_counts[label] += 1
    duplicate_ids = [
        f"{names.get(cid, cid)} ({cid})"
        for cid, count in id_counts.items()
        if count > 1
    ]
    duplicate_labels = [
        label for label, count in label_counts.items() if count > 1
    ]
    return duplicate_ids, duplicate_labels, unresolved


def _validate_label(value: str, field: str) -> None:
    if not value:
        raise AppError(400, "LABEL_REQUIRED", f"{field}不能为空")
    if len(value) > MAX_LABEL_LENGTH:
        raise AppError(400, "LABEL_TOO_LONG", f"{field}过长")
    if not _ASCII_LABEL.match(value):
        raise AppError(
            400,
            "LABEL_NOT_ENGLISH",
            f"{field}仅支持英文、数字和常用符号",
        )


def _clean_tree(
    raw: Any,
    *,
    unit_id: str,
    topic_code: str,
    concepts: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], int]:
    ids: set[str] = set()
    count = 0

    def clean(
        node: Any,
        *,
        is_root: bool,
        depth: int,
        path: tuple[int, ...],
    ) -> dict[str, Any]:
        nonlocal count
        if not isinstance(node, dict):
            raise AppError(400, "TREE_INVALID", "节点格式不正确")
        if depth > MAX_TREE_DEPTH:
            raise AppError(400, "TREE_TOO_DEEP", "知识图谱层级过深")
        count += 1
        if count > MAX_TREE_NODES:
            raise AppError(400, "TREE_TOO_LARGE", "单个 Topic 的节点过多")

        label = _ascii_label(node.get("label") or "")
        _validate_label(label, "节点标题")
        node_id = str(node.get("id") or "").strip()
        if not node_id:
            node_id = f"node-{unit_id}-{topic_code}-{'-'.join(str(part) for part in path)}"
        if len(node_id) > 80:
            raise AppError(400, "NODE_ID_INVALID", "节点 ID 过长")
        if node_id in ids:
            raise AppError(400, "NODE_ID_DUPLICATE", "节点 ID 重复，请刷新后重试")
        ids.add(node_id)

        children_raw = node.get("children") or []
        if not isinstance(children_raw, list):
            raise AppError(400, "TREE_INVALID", "子节点格式不正确")
        children = [
            clean(
                child,
                is_root=False,
                depth=depth + 1,
                path=path + (index,),
            )
            for index, child in enumerate(children_raw)
        ]

        supplement = node.get("supplement")
        concept_id = str(node.get("concept_id") or "").strip() or None
        declared_type = str(node.get("type") or "").strip()
        if is_root and (
            isinstance(supplement, dict)
            or concept_id
            or declared_type in ("concept", "supplement")
        ):
            raise AppError(400, "ROOT_MUST_BE_BRANCH", "Topic 根节点必须是结构分支")

        if isinstance(supplement, dict) or declared_type == "supplement":
            if not isinstance(supplement, dict):
                raise AppError(400, "SUPPLEMENT_REQUIRED", "补充知识点缺少释义")
            sid = str(supplement.get("id") or "").strip()
            if not sid:
                raise AppError(400, "SUPPLEMENT_ID_REQUIRED", "补充知识点缺少 ID")
            if len(sid) > 80:
                raise AppError(400, "SUPPLEMENT_ID_INVALID", "补充知识点 ID 过长")
            name = _ascii_label(supplement.get("name") or label) or label
            _validate_label(name, "知识点名称")
            definition = str(supplement.get("definition") or "").strip()
            if not definition:
                raise AppError(400, "DEFINITION_REQUIRED", "请填写知识点释义")
            if len(definition) > MAX_DEFINITION_LENGTH:
                raise AppError(400, "DEFINITION_TOO_LONG", "释义过长")
            payload: dict[str, Any] = {
                "id": node_id,
                "label": label,
                "type": "supplement",
                "concept_id": sid,
                "concept_name": name,
                "supplement": {
                    "id": sid,
                    "name": name,
                    "definition": definition,
                    "source": str(supplement.get("source") or "admin"),
                    "review_status": str(
                        supplement.get("review_status") or "draft"
                    ),
                },
                "children": children,
            }
            return payload

        if declared_type == "concept" or concept_id:
            if not concept_id:
                raise AppError(400, "CONCEPT_REQUIRED", "概念节点缺少知识点")
            row = concepts.get(concept_id)
            if row is None:
                raise AppError(
                    400,
                    "CONCEPT_NOT_IN_UNIT",
                    f"知识点 {concept_id} 不属于当前 Unit，请重新选择",
                )
            return {
                "id": node_id,
                "label": label,
                "type": "concept",
                "concept_id": concept_id,
                "concept_name": str(row.get("canonical_name") or label),
                "children": children,
            }

        if not children:
            message = "根节点至少需要一个子节点" if is_root else "分支节点至少需要一个子节点"
            raise AppError(400, "BRANCH_EMPTY", message)
        return {
            "id": node_id,
            "label": label,
            "type": "branch",
            "children": children,
        }

    tree = clean(raw, is_root=True, depth=0, path=())
    if not tree.get("children"):
        raise AppError(400, "TREE_EMPTY", "知识图谱至少需要一个节点")
    return tree, count


def save_topic_tree(
    store: ContentStore,
    db: Session,
    admin: AdminUser,
    unit_id: str,
    topic_code: str,
    tree: Any,
    expected_revision: Optional[int] = None,
    subject_id: str = SUBJECT_ID,
) -> dict[str, Any]:
    _, topics, base_map = _unit_context(store, unit_id)
    if _topic_meta(topics, topic_code) is None and str(topic_code) not in base_map:
        raise AppError(404, "TOPIC_NOT_FOUND", "Topic 不存在")
    concepts = store.get_unit_concepts(str(unit_id))
    clean, count = _clean_tree(
        tree,
        unit_id=str(unit_id),
        topic_code=str(topic_code),
        concepts=concepts,
    )
    row = get_topic_draft(db, unit_id, topic_code, subject_id)
    current_revision = int(row.revision) if row else 0
    if expected_revision is not None and int(expected_revision) != current_revision:
        raise AppError(
            409,
            "GRAPH_REVISION_CONFLICT",
            "图谱已被其他人修改，请刷新后再保存",
        )
    if row:
        row.tree = clean
        row.revision = current_revision + 1
        row.updated_by = admin.id
    else:
        row = KnowledgeGraphTopicDraft(
            subject_id=subject_id,
            unit_id=str(unit_id),
            topic_code=str(topic_code),
            tree=clean,
            revision=1,
            updated_by=admin.id,
        )
        db.add(row)
    _sync_custom_concepts(db, clean, str(unit_id), str(topic_code), admin.id)
    db.flush()
    duplicate_ids, duplicate_labels, _ = _tree_warnings(clean, concepts)
    return {
        "ok": True,
        "revision": int(row.revision),
        "node_count": count,
        "duplicate_concept_ids": duplicate_ids,
        "duplicate_labels": duplicate_labels,
    }


def _sync_custom_concepts(
    db: Session,
    tree: dict[str, Any],
    unit_id: str,
    topic_code: str,
    admin_id: str,
) -> None:
    for node in _walk(tree):
        supplement = node.get("supplement")
        if not isinstance(supplement, dict):
            continue
        sid = str(supplement.get("id") or "")
        if not sid or not sid.startswith("psy-custom-"):
            continue
        row = db.get(KnowledgeGraphCustomConcept, sid)
        if row is None:
            continue
        row.name = str(supplement.get("name") or node.get("label") or row.name)
        row.definition = str(supplement.get("definition") or row.definition)
        row.topic_code = topic_code
        row.unit_id = unit_id
        row.review_status = str(supplement.get("review_status") or row.review_status)


def reset_topic_tree(
    db: Session,
    unit_id: str,
    topic_code: str,
    subject_id: str = SUBJECT_ID,
) -> dict[str, Any]:
    row = get_topic_draft(db, unit_id, topic_code, subject_id)
    if not row:
        return {"ok": True, "revision": 0}
    revision = int(row.revision)
    db.delete(row)
    db.flush()
    return {"ok": True, "revision": revision}
