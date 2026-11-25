from __future__ import annotations

import json
import sqlite3
from collections import Counter, defaultdict
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Optional

from app.core.assets import sign_asset_url
from app.core.config import Settings

UNIT_TITLES_EN = {
    "1": "Biological Bases of Behavior",
    "2": "Cognition",
    "3": "Development and Learning",
    "4": "Social Psychology and Personality",
    "5": "Mental and Physical Health",
}

MINDMAP_PATH = Path(__file__).resolve().parent / "data" / "psychology-mindmaps.json"


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
    """Normalize typographic punctuation while keeping the label English-only."""
    return " ".join(str(value or "").translate(_LABEL_TRANSLATION).split())


def _mindmap_norm(value: str) -> str:
    text = _ascii_label(value).lower()
    return " ".join("".join(ch if ch.isalnum() else " " for ch in text).split())


def _chunks(values: list[str], size: int = 500) -> Iterable[list[str]]:
    for i in range(0, len(values), size):
        yield values[i : i + size]


def _placeholders(values: list[str]) -> str:
    return ",".join("?" for _ in values)


def _canonical_json(value: Any) -> str:
    if not value:
        return ""
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


class ContentStore:
    """Read-only access to a content release.

    The release exam.db contains practice_groups/topics and paper metadata.
    The release knowledge.db contains concepts/KPs. They are opened separately;
    we do not rely on SQLite ATTACH for cross-database joins.
    """

    def __init__(self, content_dir: Path, settings: Settings, subject_id: Optional[str] = None):
        self.dir = content_dir
        self.resolved_dir = content_dir.resolve()
        self.settings = settings
        self.exam_path = content_dir / "exam.db"
        self.knowledge_path = content_dir / "knowledge.db"
        if not self.exam_path.exists() or not self.knowledge_path.exists():
            raise RuntimeError(f"content DBs missing under {content_dir}")
        self.release = self._load_release()
        self.release_id = str(self.release.get("release_id") or "local")
        self.subject_id = subject_id or str(self.release.get("subject_id") or "psychology")
        self.exclusions = self._load_exclusions()
        self.has_pronunciations = self._has_pronunciations()

    def _has_pronunciations(self) -> bool:
        """Older Releases predate the pronunciation table; stay compatible."""
        with self._know() as conn:
            row = conn.execute(
                "SELECT 1 FROM sqlite_master "
                "WHERE type='table' AND name='concept_pronunciations'"
            ).fetchone()
        return row is not None

    def _load_release(self) -> dict[str, Any]:
        path = self.dir / "release.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {"release_id": "local", "subject_id": "psychology", "counts": {}}

    @contextmanager
    def _exam(self):
        conn = sqlite3.connect(f"file:{self.exam_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only=ON")
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def _know(self):
        conn = sqlite3.connect(f"file:{self.knowledge_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only=ON")
        try:
            yield conn
        finally:
            conn.close()

    def _load_exclusions(self) -> set[str]:
        with self._exam() as conn:
            return {
                row["question_id"]
                for row in conn.execute("SELECT question_id FROM question_exclusions")
            }

    @lru_cache(maxsize=1)
    def _mindmap_source(self) -> dict[str, Any]:
        if not MINDMAP_PATH.exists():
            return {}
        try:
            return json.loads(MINDMAP_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    @lru_cache(maxsize=8)
    def get_unit_concepts(self, unit_id: str) -> dict[str, dict[str, Any]]:
        """All concepts belonging to one Unit, including concepts not mapped to a practice Topic.

        The PDF mind map may name concepts that are in the knowledge DB but not
        in practice_topic_concepts. Loading the Unit's full concept table lets
        those nodes stay clickable without adding them to the Topic graph.
        """
        with self._know() as conn:
            ids = [
                str(row["cluster_id"])
                for row in conn.execute(
                    "SELECT cluster_id FROM concept_clusters WHERE subject_id=? AND ap_unit=?",
                    (self.subject_id, str(unit_id)),
                )
            ]
        return self._concept_details(ids)

    def unit_mindmaps(
        self,
        unit_id: str,
        overrides: Optional[dict[str, Any]] = None,
    ) -> dict[str, dict[str, Any]]:
        """Resolve the static PDF hierarchy against the current Release concepts.

        The JSON ships with the API and contains English labels plus canonical
        concept names. IDs are resolved at request time so activating a new
        Release does not require rebuilding the hierarchy file.

        Admin graph drafts (``overrides``) replace a Topic tree at request time.
        They live in the app database, never in the immutable Release. The
        cache key includes a canonical serialization of the overrides so a
        draft save is visible on the next request without a process restart.
        """
        override_json = _canonical_json(overrides)
        return self._unit_mindmaps_cached(str(unit_id), override_json)

    @lru_cache(maxsize=32)
    def _unit_mindmaps_cached(
        self, unit_id: str, override_json: str
    ) -> dict[str, dict[str, Any]]:
        unit = (self._mindmap_source().get("units") or {}).get(str(unit_id)) or {}
        topics = dict(unit.get("topics") or {})
        if override_json:
            for code, tree in json.loads(override_json).items():
                topics[str(code)] = tree
        if not topics:
            return {}
        concepts = self.get_unit_concepts(unit_id)
        by_name: dict[str, dict[str, Any]] = {}
        for row in concepts.values():
            name = str(row.get("canonical_name") or "")
            if not name:
                continue
            by_name.setdefault(name, row)
            by_name.setdefault(_mindmap_norm(name), row)

        def resolve(node: dict[str, Any]) -> tuple[dict[str, Any], int, int]:
            raw_id = node.get("concept_id")
            raw_name = node.get("concept")
            row = concepts.get(str(raw_id)) if raw_id else None
            if row is None and raw_name:
                row = by_name.get(raw_name)
            if row is None and raw_name:
                row = by_name.get(_mindmap_norm(raw_name))
            label = _ascii_label(node.get("label") or "")
            out: dict[str, Any] = {"label": label}
            matched = 0
            if row is not None:
                out["concept_id"] = str(row["cluster_id"])
                out["concept_name"] = str(row["canonical_name"])
                matched = 1
            elif node.get("supplement"):
                supplement = dict(node["supplement"])
                out["concept_id"] = str(
                    supplement.get("id") or f"psy-supp-{unit_id}-{_mindmap_norm(label)}"
                )
                out["concept_name"] = str(supplement.get("name") or label)
                out["supplement"] = {
                    "definition": str(supplement.get("definition") or ""),
                    "source": str(supplement.get("source") or "ai_supplement"),
                    "review_status": str(supplement.get("review_status") or "draft"),
                }
                matched = 1
            children: list[dict[str, Any]] = []
            total = 0
            for child in node.get("children") or []:
                resolved, child_total, child_matched = resolve(child)
                children.append(resolved)
                total += child_total
                matched += child_matched
            if children:
                out["children"] = children
            return out, total + 1, matched

        out: dict[str, dict[str, Any]] = {}
        for code, tree in topics.items():
            children: list[dict[str, Any]] = []
            total = matched = 0
            for child in tree.get("children") or []:
                resolved, child_total, child_matched = resolve(child)
                children.append(resolved)
                total += child_total
                matched += child_matched
            out[str(code)] = {
                "label": str(tree.get("label") or ""),
                "node_count": total,
                "matched_count": matched,
                "children": children,
            }
        return out

    def version(self) -> dict[str, Any]:
        return {
            "release_id": self.release_id,
            "subject_id": self.subject_id,
            "schema_version": self.release.get("schema_version", 1),
            "counts": self.release.get("counts", {}),
            "created_at": self.release.get("created_at"),
        }

    # ------------------------------------------------------------------ groups
    def list_groups(self) -> list[dict[str, Any]]:
        with self._exam() as conn:
            rows = conn.execute(
                """
                SELECT g.group_id, g.unit_id, g.title, g.status, g.bundle_paper_id,
                       COUNT(t.topic_id) AS topic_count,
                       COALESCE(SUM(t.question_count), 0) AS question_count
                FROM practice_groups g
                LEFT JOIN practice_topics t ON t.group_id = g.group_id
                WHERE g.subject_id=? AND g.status='active'
                GROUP BY g.group_id
                ORDER BY CAST(g.unit_id AS INTEGER), g.unit_id
                """,
                (self.subject_id,),
            ).fetchall()
        return [self._group_row(r) for r in rows]

    def _group_row(self, row: sqlite3.Row) -> dict[str, Any]:
        data = dict(row)
        data["title_en"] = UNIT_TITLES_EN.get(str(data.get("unit_id")), "")
        return data

    def get_group(self, group_id: str) -> Optional[dict[str, Any]]:
        with self._exam() as conn:
            row = conn.execute(
                """
                SELECT group_id, unit_id, title, status, bundle_paper_id
                FROM practice_groups
                WHERE group_id=? AND subject_id=? AND status='active'
                """,
                (group_id, self.subject_id),
            ).fetchone()
        return self._group_row(row) if row else None

    def list_topics(self, group_id: str) -> list[dict[str, Any]]:
        with self._exam() as conn:
            rows = conn.execute(
                """
                SELECT topic_id, group_id, unit_id, code, title_zh, title_en, kind,
                       sort_order, question_count
                FROM practice_topics
                WHERE group_id=? AND question_count > 0
                ORDER BY sort_order, code
                """,
                (group_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    @lru_cache(maxsize=8)
    def list_all_topics(self, unit_id: Optional[str] = None) -> list[dict[str, Any]]:
        """All active topics for the store's subject (old Releases may lack the table)."""
        with self._exam() as conn:
            table = conn.execute(
                "SELECT 1 FROM sqlite_master "
                "WHERE type='table' AND name='practice_topics'"
            ).fetchone()
            if not table:
                return []
            clauses = [
                "g.subject_id=?",
                "g.status='active'",
                "pt.question_count > 0",
            ]
            params: list[Any] = [self.subject_id]
            if unit_id:
                clauses.append("pt.unit_id=?")
                params.append(str(unit_id))
            rows = conn.execute(
                f"""
                SELECT pt.topic_id, pt.group_id, pt.unit_id, pt.code, pt.title_zh,
                       pt.title_en, pt.kind, pt.sort_order, pt.question_count
                FROM practice_topics pt
                JOIN practice_groups g ON g.group_id = pt.group_id
                WHERE {' AND '.join(clauses)}
                ORDER BY CAST(pt.unit_id AS INTEGER), pt.sort_order, pt.code
                """,
                tuple(params),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_topic(self, topic_id: str) -> Optional[dict[str, Any]]:
        with self._exam() as conn:
            row = conn.execute(
                """
                SELECT topic_id, group_id, unit_id, code, title_zh, title_en, kind,
                       sort_order, question_count
                FROM practice_topics
                WHERE topic_id=?
                """,
                (topic_id,),
            ).fetchone()
        return dict(row) if row else None

    # Content releases are immutable, so these read-only payloads can be
    # memoized per worker. User answers/scores still come from the app DB.
    @lru_cache(maxsize=512)
    def get_topic_concepts(self, topic_id: str) -> list[dict[str, Any]]:
        with self._exam() as conn:
            rows = conn.execute(
                """
                SELECT concept_id, weight, sort_order
                FROM practice_topic_concepts
                WHERE topic_id=?
                ORDER BY sort_order
                """,
                (topic_id,),
            ).fetchall()
        if not rows:
            return []
        ids = [r["concept_id"] for r in rows]
        details = self._concept_details(ids)
        out = []
        for row in rows:
            detail = details.get(row["concept_id"])
            if detail:
                detail = dict(detail)
                detail["weight"] = row["weight"]
                out.append(detail)
        return out

    def question_ids_for_topic(self, topic_id: str) -> list[str]:
        with self._exam() as conn:
            rows = conn.execute(
                """
                SELECT question_id
                FROM practice_topic_questions
                WHERE topic_id=? AND is_primary=1
                ORDER BY sort_order
                """,
                (topic_id,),
            ).fetchall()
        return [r["question_id"] for r in rows]

    def question_ids_for_group(self, group_id: str) -> list[str]:
        with self._exam() as conn:
            rows = conn.execute(
                """
                SELECT DISTINCT q.question_id
                FROM practice_topic_questions q
                JOIN practice_topics t ON t.topic_id=q.topic_id
                WHERE t.group_id=? AND q.is_primary=1
                ORDER BY q.sort_order
                """,
                (group_id,),
            ).fetchall()
        return [r["question_id"] for r in rows]

    def topic_question_map(self, group_id: str) -> dict[str, list[str]]:
        with self._exam() as conn:
            rows = conn.execute(
                """
                SELECT t.topic_id, q.question_id
                FROM practice_topic_questions q
                JOIN practice_topics t ON t.topic_id=q.topic_id
                WHERE t.group_id=? AND q.is_primary=1
                ORDER BY t.sort_order, q.sort_order
                """,
                (group_id,),
            ).fetchall()
        out: dict[str, list[str]] = {}
        for row in rows:
            out.setdefault(row["topic_id"], []).append(row["question_id"])
        return out

    def question_contexts(self, question_ids: list[str]) -> dict[str, dict[str, Any]]:
        if not question_ids:
            return {}
        out: dict[str, dict[str, Any]] = {}
        with self._exam() as conn:
            for chunk in _chunks(question_ids):
                ph = _placeholders(chunk)
                rows = conn.execute(
                    f"""
                    SELECT q.question_id, t.topic_id, t.unit_id, t.group_id,
                           t.title_zh, t.title_en, t.code
                    FROM practice_topic_questions q
                    JOIN practice_topics t ON t.topic_id=q.topic_id
                    WHERE q.question_id IN ({ph}) AND q.is_primary=1
                    ORDER BY q.question_id, t.sort_order
                    """,
                    chunk,
                ).fetchall()
                for row in rows:
                    data = dict(row)
                    question_id = data.pop("question_id")
                    out.setdefault(question_id, data)
        return out

    @lru_cache(maxsize=4096)
    def question_context(self, question_id: str) -> dict[str, Any]:
        return self.question_contexts([question_id]).get(question_id, {})

    @lru_cache(maxsize=4096)
    def topic_for_question(self, question_id: str) -> Optional[dict[str, Any]]:
        """Resolve the closest practice topic for a question.

        Unit practice has a direct question -> topic mapping. Real-exam
        questions don't, so fall back to the topics containing the question's
        linked concepts (core links weigh most).
        """
        context = self.question_context(question_id)
        if context.get("topic_id"):
            return self.get_topic(str(context["topic_id"]))

        concepts = self.get_question_concepts(question_id)
        if not concepts:
            return None

        relation_weight = {
            "core": 3.0,
            "supporting": 1.0,
            "confusable": 0.5,
            "kp": 0.25,
        }
        concept_weights: dict[str, float] = {}
        for concept in concepts:
            concept_id = concept.get("concept_id")
            if not concept_id:
                continue
            relation = str(concept.get("relation_type") or "supporting")
            weight = relation_weight.get(relation, 0.5)
            concept_weights[concept_id] = max(
                concept_weights.get(concept_id, 0.0), weight
            )
        if not concept_weights:
            return None

        scores: dict[str, float] = {}
        with self._exam() as conn:
            for chunk in _chunks(list(concept_weights)):
                placeholders = _placeholders(chunk)
                rows = conn.execute(
                    f"""
                    SELECT topic_id, concept_id, weight
                    FROM practice_topic_concepts
                    WHERE concept_id IN ({placeholders})
                    """,
                    chunk,
                ).fetchall()
                for row in rows:
                    relation_score = concept_weights.get(row["concept_id"], 0.0)
                    topic_weight = min(float(row["weight"] or 0), 100.0)
                    scores[row["topic_id"]] = (
                        scores.get(row["topic_id"], 0.0)
                        + relation_score * (1.0 + topic_weight / 1000.0)
                    )

        if not scores:
            return None
        topic_id = max(scores.items(), key=lambda item: (item[1], item[0]))[0]
        return self.get_topic(topic_id)

    # ---------------------------------------------------------- knowledge graph
    RELATION_LABELS = {
        "part_of": "组成",
        "broader_narrower": "上下位",
        "related_to": "相关",
        "same_name_different_sense": "同名异义",
    }
    PAPER_LABELS = {
        "real_exam": "真题",
        "mock_exam": "模拟",
        "unit_practice": "单元练习",
        "bundle": "练习组",
    }

    def _unit_question_links(self, concept_ids: list[str]) -> list[sqlite3.Row]:
        if not concept_ids:
            return []
        rows: list[sqlite3.Row] = []
        with self._know() as conn:
            for chunk in _chunks(concept_ids):
                ph = _placeholders(chunk)
                rows.extend(
                    conn.execute(
                        f"""
                        SELECT question_id, concept_id, relation_type, option_label,
                               confidence, evidence, rationale
                        FROM question_concept_links
                        WHERE concept_id IN ({ph})
                        """,
                        chunk,
                    ).fetchall()
                )
        return rows

    def _unit_relations(self, concept_ids: list[str]) -> list[sqlite3.Row]:
        if not concept_ids:
            return []
        rows: list[sqlite3.Row] = []
        with self._know() as conn:
            for chunk in _chunks(concept_ids):
                ph = _placeholders(chunk)
                rows.extend(
                    conn.execute(
                        f"""
                        SELECT concept_id_a, concept_id_b, relation_type,
                               evidence, confidence
                        FROM concept_relations
                        WHERE concept_id_a IN ({ph}) AND concept_id_b IN ({ph})
                        """,
                        chunk + chunk,
                    ).fetchall()
                )
        return rows

    def _unit_question_meta(self, question_ids: list[str]) -> tuple[dict[str, dict], dict[str, dict]]:
        questions: dict[str, dict[str, Any]] = {}
        papers: dict[str, dict[str, Any]] = {}
        if not question_ids:
            return questions, papers
        with self._exam() as conn:
            for chunk in _chunks(question_ids):
                ph = _placeholders(chunk)
                for row in conn.execute(
                    f"""
                    SELECT question_id, paper_id, number, stem, section
                    FROM questions WHERE question_id IN ({ph})
                    """,
                    chunk,
                ):
                    questions[row["question_id"]] = dict(row)
            paper_ids = sorted({q["paper_id"] for q in questions.values() if q.get("paper_id")})
            for chunk in _chunks(paper_ids):
                ph = _placeholders(chunk)
                for row in conn.execute(
                    f"""
                    SELECT paper_id, year, title, paper_type
                    FROM papers WHERE paper_id IN ({ph})
                    """,
                    chunk,
                ):
                    papers[row["paper_id"]] = dict(row)
        return questions, papers

    def unit_knowledge_graph(
        self,
        unit_id: str,
        overrides: Optional[dict[str, Any]] = None,
    ) -> Optional[dict[str, Any]]:
        """Build the Unit graph payload from a content Release plus admin drafts.

        V1 relation layers are deliberately explicit:
        - textbook hierarchy from concept_relations
        - exam contrast from core vs confusable links in the same question
        - exam co-occurrence from core + supporting links in the same question

        No AI / prerequisite edges are generated here. The graph is additive
        content, so the frontend can render a structure layer and drill into a
        Topic without exposing unrelated units.
        """
        override_json = _canonical_json(overrides)
        return self._unit_knowledge_graph_cached(str(unit_id), override_json)

    @lru_cache(maxsize=32)
    def _unit_knowledge_graph_cached(
        self, unit_id: str, override_json: str
    ) -> Optional[dict[str, Any]]:
        overrides = json.loads(override_json) if override_json else None
        group = next(
            (g for g in self.list_groups() if str(g.get("unit_id")) == str(unit_id)),
            None,
        )
        if not group:
            return None
        group_id = str(group["group_id"])
        topics_meta = self.list_topics(group_id)
        if not topics_meta:
            return None

        mindmaps = self.unit_mindmaps(str(unit_id), overrides=overrides)
        unit_concepts = self.get_unit_concepts(str(unit_id)) if mindmaps else {}

        topic_concepts: dict[str, list[dict[str, Any]]] = {}
        concepts_by_id: dict[str, dict[str, Any]] = {}
        concept_topics: dict[str, str] = {}
        topic_concept_ids: dict[str, set[str]] = {}
        for topic in topics_meta:
            rows = self.get_topic_concepts(topic["topic_id"])
            topic_concepts[topic["topic_id"]] = rows
            ids = {str(row["cluster_id"]) for row in rows}
            topic_concept_ids[topic["topic_id"]] = ids
            for row in rows:
                cid = str(row["cluster_id"])
                concept_topics.setdefault(cid, str(topic["code"]))
                concepts_by_id.setdefault(cid, row)

        mindmap_concept_ids: set[str] = set()
        mindmap_concept_topic: dict[str, str] = {}
        supplement_payloads: dict[str, dict[str, Any]] = {}

        def collect_mindmap_ids(node: dict[str, Any], topic_code: str) -> None:
            cid = node.get("concept_id")
            if cid:
                cid = str(cid)
                mindmap_concept_ids.add(cid)
                mindmap_concept_topic.setdefault(cid, topic_code)
                supplement = node.get("supplement")
                if supplement:
                    source = str(supplement.get("source") or "ai_supplement")
                    supplement_payloads[cid] = {
                        "concept_id": cid,
                        "name": str(node.get("concept_name") or node.get("label") or ""),
                        "tier": "supplement",
                        "weight": 0,
                        "questions": {"core": 0, "supporting": 0, "confusable": 0, "total": 0},
                        "definition": str(supplement.get("definition") or ""),
                        "quote": "",
                        "chapter": "",
                        "section": "",
                        "book": (
                            "Admin supplement"
                            if source == "admin"
                            else "AI-assisted supplement"
                        ),
                        "relations": [],
                        "contrast": [],
                        "samples": [],
                        "supplement": True,
                        "supplement_source": source,
                        "review_status": str(supplement.get("review_status") or "draft"),
                    }
            for child in node.get("children") or []:
                collect_mindmap_ids(child, topic_code)

        for topic_code, tree in mindmaps.items():
            for child in tree.get("children") or []:
                collect_mindmap_ids(child, str(topic_code))
        for cid in sorted(mindmap_concept_ids):
            if cid in supplement_payloads:
                continue
            if cid not in concepts_by_id and cid in unit_concepts:
                concepts_by_id[cid] = unit_concepts[cid]

        concept_ids = sorted(concepts_by_id)
        relations = self._unit_relations(concept_ids)
        links = self._unit_question_links(concept_ids)
        question_ids = sorted({str(row["question_id"]) for row in links})
        question_meta, paper_meta = self._unit_question_meta(question_ids)

        def paper_label(paper_id: str | None) -> str:
            paper = paper_meta.get(str(paper_id or ""), {})
            year = paper.get("year")
            ptype = str(paper.get("paper_type") or "")
            label = self.PAPER_LABELS.get(ptype, "练习")
            return f"{year} {label}".strip() if year else label

        def sample(row) -> dict[str, Any]:
            # The graph only renders question numbers, paper and role. The
            # stem is fetched by the read-only preview endpoint, so omit it
            # here to keep the payload small.
            qid = str(row["question_id"])
            q = question_meta.get(qid, {})
            return {
                "question_id": qid,
                "role": row["relation_type"],
                "paper": paper_label(q.get("paper_id")),
                "number": q.get("number"),
            }

        # Concept-level relation and question summaries.
        rel_by_concept: dict[str, list[dict[str, Any]]] = defaultdict(list)
        seen_rel: set[tuple[str, str, str]] = set()
        relation_edges: list[dict[str, Any]] = []
        for row in relations:
            a, b = str(row["concept_id_a"]), str(row["concept_id_b"])
            rtype = str(row["relation_type"])
            key = (a, b, rtype)
            if key in seen_rel or a not in concepts_by_id or b not in concepts_by_id:
                continue
            seen_rel.add(key)
            label = self.RELATION_LABELS.get(rtype, "相关")
            evidence = str(row["evidence"] or "")
            confidence = float(row["confidence"] or 0)
            edge = {
                "source": a,
                "target": b,
                "type": rtype,
                "kind": "relation",
                "label": label,
                "evidence": evidence,
                "confidence": confidence,
                "source_type": "textbook_relation",
            }
            relation_edges.append(edge)
            for cid, other, direction in ((a, b, "out"), (b, a, "in")):
                rel_by_concept[cid].append(
                    {
                        "id": other,
                        "name": str(concepts_by_id[other]["canonical_name"]),
                        "type": rtype,
                        "label": label,
                        "direction": direction,
                        "evidence": evidence,
                        "confidence": confidence,
                    }
                )

        stats: dict[str, Counter] = defaultdict(Counter)
        samples: dict[str, list[dict[str, Any]]] = defaultdict(list)
        seen_samples: dict[str, set[str]] = defaultdict(set)
        by_question: dict[str, dict[str, set[str]]] = defaultdict(
            lambda: {"core": set(), "supporting": set(), "confusable": set()}
        )
        for row in sorted(
            links,
            key=lambda r: (
                {"core": 0, "supporting": 1, "confusable": 2}.get(r["relation_type"], 9),
                -(float(r["confidence"] or 0)),
            ),
        ):
            cid = str(row["concept_id"])
            if cid not in concepts_by_id:
                continue
            qid = str(row["question_id"])
            rtype = str(row["relation_type"])
            stats[cid][rtype] += 1
            by_question[qid][rtype].add(cid)
            if qid not in seen_samples[cid] and len(samples[cid]) < 4:
                seen_samples[cid].add(qid)
                samples[cid].append(sample(row))

        co_weight: Counter = Counter()
        contrast_weight: Counter = Counter()
        contrast_questions: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for qid, buckets in by_question.items():
            cores = sorted(buckets["core"])
            for a in cores:
                for b in sorted(buckets["supporting"]):
                    if a != b:
                        co_weight[tuple(sorted((a, b)))] += 1
                for b in sorted(buckets["confusable"]):
                    if a != b:
                        key = tuple(sorted((a, b)))
                        contrast_weight[key] += 1
                        if len(contrast_questions[key]) < 2:
                            q = question_meta.get(qid, {})
                            contrast_questions[key].append(
                                {
                                    "question_id": qid,
                                    "paper": paper_label(q.get("paper_id")),
                                    "number": q.get("number"),
                                }
                            )

        def pair_rows(counter: Counter, kind: str) -> list[dict[str, Any]]:
            out = []
            for (a, b), weight in counter.items():
                if a not in concepts_by_id or b not in concepts_by_id:
                    continue
                out.append(
                    {
                        "source": a,
                        "target": b,
                        "weight": int(weight),
                        "kind": kind,
                        "type": kind,
                        "source_type": "exam_confusable" if kind == "contrast" else "exam_cooccurrence",
                    }
                )
            return out

        contrast_edges = pair_rows(contrast_weight, "contrast")
        co_edges = pair_rows(co_weight, "cooccurrence")

        contrast_by_concept: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for edge in contrast_edges:
            a, b = edge["source"], edge["target"]
            for cid, other in ((a, b), (b, a)):
                contrast_by_concept[cid].append(
                    {
                        "id": other,
                        "name": str(concepts_by_id[other]["canonical_name"]),
                        "weight": edge["weight"],
                        "questions": contrast_questions.get(tuple(sorted((a, b))), []),
                    }
                )

        # Topic-local edges for the Topic graph, plus aggregate Topic bridges.
        topic_edges: dict[str, list[dict[str, Any]]] = {t["topic_id"]: [] for t in topics_meta}
        edge_keys: dict[str, set[tuple[str, str, str, str]]] = defaultdict(set)
        for edge in relation_edges:
            a, b = edge["source"], edge["target"]
            for topic in topics_meta:
                ids = topic_concept_ids[topic["topic_id"]]
                if a in ids and b in ids:
                    key = (a, b, edge["kind"], edge["type"])
                    if key not in edge_keys[topic["topic_id"]]:
                        edge_keys[topic["topic_id"]].add(key)
                        topic_edges[topic["topic_id"]].append(edge)
        for edge in contrast_edges + co_edges:
            if edge["kind"] == "contrast" and edge["weight"] < 3:
                continue
            if edge["kind"] == "cooccurrence" and edge["weight"] < 2:
                continue
            a, b = edge["source"], edge["target"]
            for topic in topics_meta:
                ids = topic_concept_ids[topic["topic_id"]]
                if a in ids and b in ids:
                    key = (a, b, edge["kind"], edge["type"])
                    if key not in edge_keys[topic["topic_id"]]:
                        edge_keys[topic["topic_id"]].add(key)
                        topic_edges[topic["topic_id"]].append(edge)
        # Keep the Topic graph readable: semantic edges plus the strongest
        # contrast/co-occurrence edges. The full unit bridges still retain the
        # aggregate weights.
        for topic in topics_meta:
            edges = topic_edges[topic["topic_id"]]
            relations = [e for e in edges if e["kind"] == "relation"]
            contrast = sorted(
                (e for e in edges if e["kind"] == "contrast"),
                key=lambda e: (-e["weight"], e["source"], e["target"]),
            )[:20]
            co = sorted(
                (e for e in edges if e["kind"] == "cooccurrence"),
                key=lambda e: (-e["weight"], e["source"], e["target"]),
            )[:12]
            topic_edges[topic["topic_id"]] = relations + contrast + co

        topic_by_id = {str(t["topic_id"]): t for t in topics_meta}
        topic_code_by_id = {str(t["topic_id"]): str(t["code"]) for t in topics_meta}
        bridges: dict[tuple[str, str], dict[str, Any]] = {}

        def add_bridge(a: str, b: str, field: str, weight: int = 1) -> None:
            ca, cb = concept_topics.get(a), concept_topics.get(b)
            if not ca or not cb or ca == cb:
                return
            key = tuple(sorted((ca, cb)))
            if key not in bridges:
                bridges[key] = {
                    "source": key[0],
                    "target": key[1],
                    "semantic": 0,
                    "contrast": 0,
                    "co": 0,
                }
            bridges[key][field] += weight

        for edge in relation_edges:
            add_bridge(edge["source"], edge["target"], "semantic")
        for edge in contrast_edges:
            add_bridge(edge["source"], edge["target"], "contrast", edge["weight"])
        for edge in co_edges:
            add_bridge(edge["source"], edge["target"], "co", edge["weight"])

        def concept_payload(cid: str, topic_weight: float | None = None) -> dict[str, Any]:
            c = concepts_by_id[cid]
            raw_definition = str(c.get("plain_en") or "").strip()
            quote = str(c.get("definition_quote") or "").strip()
            definition = raw_definition or quote
            relation_rows = sorted(
                rel_by_concept.get(cid, []),
                key=lambda r: (-(r["confidence"] or 0), r["name"]),
            )[:10]
            contrast_rows = sorted(
                contrast_by_concept.get(cid, []),
                key=lambda r: (-r["weight"], r["name"]),
            )[:6]
            return {
                "concept_id": cid,
                "name": str(c["canonical_name"]),
                "tier": str(c.get("weight_tier") or "supporting"),
                "weight": round(float(topic_weight if topic_weight is not None else (c.get("weight") or 0)), 2),
                "questions": {
                    "core": stats[cid]["core"],
                    "supporting": stats[cid]["supporting"],
                    "confusable": stats[cid]["confusable"],
                    "total": sum(stats[cid].values()),
                },
                "definition": definition,
                "quote": quote,
                "chapter": str(c.get("topic") or ""),
                "section": str(c.get("section_heading") or ""),
                "book": str(c.get("book_title") or ""),
                "relations": relation_rows,
                "contrast": contrast_rows,
                "samples": samples.get(cid, []),
            }

        topics_payload = []
        for topic in topics_meta:
            concepts = []
            for c in topic_concepts[topic["topic_id"]]:
                cid = str(c["cluster_id"])
                concepts.append(concept_payload(cid, c.get("weight")))
            concepts.sort(key=lambda c: (-(c["weight"] or 0), c["name"]))
            topics_payload.append(
                {
                    "topic_id": str(topic["topic_id"]),
                    "code": str(topic["code"]),
                    "title_zh": str(topic.get("title_zh") or ""),
                    "title_en": str(topic.get("title_en") or ""),
                    "kind": str(topic.get("kind") or "ced"),
                    "sort_order": topic.get("sort_order") or 0,
                    "concept_count": len(concepts),
                    "question_count": int(topic.get("question_count") or 0),
                    "concepts": concepts,
                    "edges": topic_edges[topic["topic_id"]],
                    **({"mindmap": mindmaps[str(topic["code"])]} if str(topic["code"]) in mindmaps else {}),
                }
            )

        return {
            "unit_id": str(unit_id),
            "group_id": group_id,
            "title": str(group.get("title") or ""),
            "title_en": str(group.get("title_en") or ""),
            "topic_count": len(topics_payload),
            "concept_count": len(concept_ids),
            "question_count": int(group.get("question_count") or 0),
            "topics": topics_payload,
            "mindmap_concepts": {
                cid: {
                    **(
                        supplement_payloads[cid]
                        if cid in supplement_payloads
                        else concept_payload(cid)
                    ),
                    "topic_code": mindmap_concept_topic.get(cid),
                }
                for cid in sorted(
                    mindmap_concept_ids - set().union(*topic_concept_ids.values())
                    if topic_concept_ids
                    else mindmap_concept_ids
                )
            },
            "bridges": sorted(
                bridges.values(),
                key=lambda b: (-(b["semantic"] + b["contrast"] + b["co"]), b["source"], b["target"]),
            ),
            "graph_version": 1,
        }

    # ----------------------------------------------------------------- papers
    def list_papers(self, paper_type: Optional[str] = None) -> list[dict[str, Any]]:
        params: list[Any] = [self.subject_id]
        where = "p.subject_id=? AND p.paper_type IN ('real_exam','mock_exam')"
        if paper_type in ("real_exam", "mock_exam"):
            where = "p.subject_id=? AND p.paper_type=?"
            params.append(paper_type)
        with self._exam() as conn:
            rows = conn.execute(
                f"""
                SELECT p.paper_id, p.year, p.title, p.chinese_title, p.paper_type,
                       p.question_count, c.format_code, c.mcq_count, c.mcq_minutes,
                       c.frq_count, c.frq_minutes, c.frq_forms, c.section_order,
                       c.is_complete, c.frq_rubric_complete, c.expected_frq_points, c.notes
                FROM papers p
                LEFT JOIN paper_exam_configs c ON c.paper_id=p.paper_id
                WHERE {where}
                ORDER BY p.year DESC, p.paper_type, p.paper_id
                """,
                params,
            ).fetchall()
        return [self._paper_row(r) for r in rows]

    def get_paper(self, paper_id: str) -> Optional[dict[str, Any]]:
        with self._exam() as conn:
            row = conn.execute(
                """
                SELECT p.paper_id, p.year, p.title, p.chinese_title, p.paper_type,
                       p.question_count, c.format_code, c.mcq_count, c.mcq_minutes,
                       c.frq_count, c.frq_minutes, c.frq_forms, c.section_order,
                       c.is_complete, c.frq_rubric_complete, c.expected_frq_points, c.notes
                FROM papers p
                LEFT JOIN paper_exam_configs c ON c.paper_id=p.paper_id
                WHERE p.paper_id=? AND p.subject_id=?
                """,
                (paper_id, self.subject_id),
            ).fetchone()
        return self._paper_row(row) if row else None

    def _paper_row(self, row: sqlite3.Row) -> dict[str, Any]:
        data = dict(row)
        forms = data.get("frq_forms")
        data["frq_forms"] = json.loads(forms) if forms else []
        order = data.get("section_order")
        data["section_order"] = json.loads(order) if order else []
        data["modes"] = []
        if (data.get("mcq_count") or 0) > 0:
            data["modes"].append("mcq")
        if (data.get("frq_count") or 0) > 0:
            data["modes"].append("frq")
        if (data.get("mcq_count") or 0) > 0 and (data.get("frq_count") or 0) > 0:
            data["modes"].append("full")
        data["frq_warning"] = None
        if data.get("frq_count") and not data.get("frq_rubric_complete", 1):
            if data.get("paper_id") != "psychology-ap-2018":
                data["frq_warning"] = "Incomplete rubric (3/7); self-grade is reference only"
        return data

    def question_ids_for_paper(
        self, paper_id: str, section: str, form: Optional[str] = None
    ) -> list[str]:
        params: list[Any] = [paper_id, self.subject_id, section]
        form_sql = ""
        if form:
            form_sql = " AND form=?"
            params.append(form)
        with self._exam() as conn:
            rows = conn.execute(
                f"""
                SELECT question_id, number, form
                FROM questions
                WHERE paper_id=? AND subject_id=? AND section=?{form_sql}
                ORDER BY number
                """,
                params,
            ).fetchall()
        return [r["question_id"] for r in rows]

    def get_exam_config(self, paper_id: str) -> Optional[dict[str, Any]]:
        with self._exam() as conn:
            row = conn.execute(
                "SELECT * FROM paper_exam_configs WHERE paper_id=?", (paper_id,)
            ).fetchone()
        if not row:
            return None
        data = dict(row)
        forms = data.get("frq_forms")
        data["frq_forms"] = json.loads(forms) if forms else []
        order = data.get("section_order")
        data["section_order"] = json.loads(order) if order else []
        return data

    # --------------------------------------------------------------- questions
    def get_questions(
        self,
        question_ids: list[str],
        include_answers: bool = False,
        display_numbers: Optional[dict[str, int]] = None,
    ) -> dict[str, dict[str, Any]]:
        if not question_ids:
            return {}
        questions: dict[str, dict[str, Any]] = {}
        with self._exam() as conn:
            asset_columns = {
                row[1] for row in conn.execute("PRAGMA table_info(assets)").fetchall()
            }
            asset_description = (
                "description" if "description" in asset_columns else "NULL AS description"
            )
            for chunk in _chunks(question_ids):
                ph = _placeholders(chunk)
                for row in conn.execute(
                    f"""
                    SELECT question_id, paper_id, section, number, stem, context,
                           correct_answer, answer_text, answer_source, answer_confidence, form
                    FROM questions
                    WHERE question_id IN ({ph})
                    """,
                    chunk,
                ):
                    questions[row["question_id"]] = dict(row)
                for row in conn.execute(
                    f"""
                    SELECT question_id, label, content, sort_order, is_correct,
                           explanation, ai_explanation
                    FROM options
                    WHERE question_id IN ({ph})
                    ORDER BY question_id, sort_order
                    """,
                    chunk,
                ):
                    q = questions.get(row["question_id"])
                    if not q:
                        continue
                    q.setdefault("options", []).append(dict(row))
                for row in conn.execute(
                    f"""
                    SELECT asset_id, question_id, option_label, kind, path, page, bbox,
                           {asset_description}
                    FROM assets
                    WHERE question_id IN ({ph})
                    ORDER BY question_id, kind, option_label, asset_id
                    """,
                    chunk,
                ):
                    q = questions.get(row["question_id"])
                    if not q:
                        continue
                    asset = dict(row)
                    asset["url"] = self.asset_url(asset["path"])
                    q.setdefault("assets", []).append(asset)
                for row in conn.execute(
                    f"""
                    SELECT question_id, display_number FROM question_display
                    WHERE question_id IN ({ph})
                    """,
                    chunk,
                ):
                    q = questions.get(row["question_id"])
                    if q:
                        q["display_number"] = row["display_number"]

        out: dict[str, dict[str, Any]] = {}
        for qid, q in questions.items():
            options = q.get("options", [])
            assets = q.get("assets", [])
            option_assets: dict[str, list[dict[str, Any]]] = {}
            for asset in assets:
                if asset.get("option_label"):
                    option_assets.setdefault(str(asset["option_label"]), []).append(asset)
            public_options = []
            for opt in options:
                item = {
                    "label": opt["label"],
                    "content": opt["content"] or "",
                    "sort_order": opt["sort_order"],
                    "asset_urls": [a["url"] for a in option_assets.get(opt["label"], [])],
                }
                if include_answers:
                    item.update(
                        {
                            "is_correct": bool(opt["is_correct"]),
                            "explanation": opt["explanation"] or "",
                            "ai_explanation": opt["ai_explanation"] or "",
                        }
                    )
                public_options.append(item)
            item = {
                "question_id": qid,
                "paper_id": q["paper_id"],
                "section": q["section"],
                "number": q["number"],
                "form": q.get("form"),
                "display_number": (display_numbers or {}).get(
                    qid, q.get("display_number") or q["number"]
                ),
                "stem": q["stem"],
                "context": q.get("context") or "",
                "options": public_options,
                "assets": [
                    {
                        "asset_id": a["asset_id"],
                        "kind": a["kind"],
                        "option_label": a["option_label"],
                        "url": a["url"],
                        "page": a["page"],
                        "bbox": a["bbox"],
                        "description": a.get("description"),
                    }
                    for a in assets
                ],
                "answer_source": q.get("answer_source"),
                "answer_confidence": q.get("answer_confidence"),
            }
            if include_answers:
                item["answer_text"] = q.get("answer_text")
                correct = next((o for o in public_options if o.get("is_correct")), None)
                item["correct_label"] = correct["label"] if correct else None
            out[qid] = item
        return out

    @lru_cache(maxsize=4096)
    def get_feedback(self, question_id: str) -> dict[str, Any]:
        data = self.get_questions([question_id], include_answers=True)[question_id]
        correct = next((o for o in data["options"] if o.get("is_correct")), None)
        explanation = ""
        source = None
        if correct:
            if correct.get("explanation"):
                explanation, source = correct["explanation"], "book"
            elif correct.get("ai_explanation"):
                explanation, source = correct["ai_explanation"], "ai"
        data["explanation"] = explanation
        data["explanation_source"] = source
        data["concepts"] = self.get_question_concepts(question_id)
        return data

    def frq_total_points(self, question_ids: list[str]) -> int:
        if not question_ids:
            return 0
        total = 0
        with self._exam() as conn:
            for chunk in _chunks(question_ids):
                ph = _placeholders(chunk)
                row = conn.execute(
                    f"""
                    SELECT COALESCE(SUM(total_points), 0)
                    FROM frq_rubrics WHERE question_id IN ({ph})
                    """,
                    chunk,
                ).fetchone()
                total += int(row[0] or 0)
        return total

    @lru_cache(maxsize=512)
    def get_frq_guidelines(self, question_id: str) -> dict[str, Any]:
        with self._exam() as conn:
            q = conn.execute(
                "SELECT answer_text FROM questions WHERE question_id=?", (question_id,)
            ).fetchone()
            rubric = conn.execute(
                """
                SELECT rubric_id, total_points, general_considerations, format
                FROM frq_rubrics WHERE question_id=?
                """,
                (question_id,),
            ).fetchone()
            parts = []
            if rubric:
                for row in conn.execute(
                    """
                    SELECT part_id, label, title, max_points, criteria, decision_rules,
                           examples_positive, examples_negative, notes, sort_order
                    FROM rubric_parts WHERE rubric_id=? ORDER BY sort_order
                    """,
                    (rubric["rubric_id"],),
                ):
                    part = dict(row)
                    for key in ("criteria", "examples_positive", "examples_negative"):
                        raw = part.get(key)
                        if raw:
                            try:
                                part[key + "_json"] = json.loads(raw)
                            except Exception:
                                part[key + "_json"] = None
                    parts.append(part)
        return {
            "question_id": question_id,
            "answer_text": q["answer_text"] if q else None,
            "rubric": dict(rubric) if rubric else None,
            "parts": parts,
        }

    def get_question_concepts(self, question_id: str) -> list[dict[str, Any]]:
        with self._know() as conn:
            rows = conn.execute(
                """
                SELECT l.concept_id, l.relation_type, l.option_label, l.confidence,
                       l.evidence, l.rationale,
                       c.canonical_name, c.topic, c.ap_unit, c.weight
                FROM question_concept_links l
                JOIN concept_clusters c ON c.cluster_id=l.concept_id
                WHERE l.question_id=? AND c.subject_id=?
                """,
                (question_id, self.subject_id),
            ).fetchall()
        if not rows:
            return self._fallback_kp_concepts(question_id)
        ids = [r["concept_id"] for r in rows]
        details = self._concept_details(ids)
        out = []
        for row in rows:
            d = dict(row)
            detail = details.get(row["concept_id"], {})
            d.update(detail)
            out.append(d)
        order = {"core": 0, "supporting": 1, "confusable": 2}
        out.sort(key=lambda x: (order.get(x.get("relation_type"), 9), -(x.get("weight") or 0)))
        return out

    def _concept_details(self, concept_ids: list[str]) -> dict[str, dict[str, Any]]:
        if not concept_ids:
            return {}
        out: dict[str, dict[str, Any]] = {}
        pronunciation_select = (
            ", p.ipa, p.audio_path, p.duration_ms"
            if self.has_pronunciations
            else ""
        )
        pronunciation_join = (
            "LEFT JOIN concept_pronunciations p ON p.cluster_id=c.cluster_id"
            if self.has_pronunciations
            else ""
        )
        with self._know() as conn:
            for chunk in _chunks(concept_ids):
                ph = _placeholders(chunk)
                for row in conn.execute(
                    f"""
                    SELECT c.cluster_id, c.canonical_name, c.topic, c.ap_unit, c.weight,
                           c.weight_tier,
                           COALESCE(NULLIF(c.description, ''), k.plain_en) AS plain_en,
                           k.definition_quote, k.name AS kp_name,
                           s.heading AS section_heading,
                           CASE
                             WHEN c.canonical_kp_id IS NULL AND c.description IS NOT NULL
                             THEN 'Admin content'
                             ELSE b.title
                           END AS book_title
                           {pronunciation_select}
                    FROM concept_clusters c
                    LEFT JOIN knowledge_points k ON k.kp_id=c.canonical_kp_id
                    LEFT JOIN sections s ON s.section_id=k.section_id
                    LEFT JOIN books b ON b.book_id=k.book_id
                    {pronunciation_join}
                    WHERE c.cluster_id IN ({ph})
                    """,
                    chunk,
                ):
                    detail = dict(row)
                    if detail.get("audio_path"):
                        detail["audio_url"] = self.asset_url(str(detail["audio_path"]))
                    out[row["cluster_id"]] = detail
        return out

    def _fallback_kp_concepts(self, question_id: str) -> list[dict[str, Any]]:
        with self._know() as conn:
            rows = conn.execute(
                """
                SELECT l.kp_id, k.name, k.plain_en, k.definition_quote,
                       s.heading AS section_heading, b.title AS book_title
                FROM question_kp_links l
                JOIN knowledge_points k ON k.kp_id=l.kp_id
                LEFT JOIN sections s ON s.section_id=k.section_id
                LEFT JOIN books b ON b.book_id=k.book_id
                WHERE l.question_id=?
                """,
                (question_id,),
            ).fetchall()
        return [
            {
                "concept_id": r["kp_id"],
                "relation_type": "kp",
                "canonical_name": r["name"],
                "plain_en": r["plain_en"],
                "definition_quote": r["definition_quote"],
                "section_heading": r["section_heading"],
                "book_title": r["book_title"],
            }
            for r in rows
        ]

    # -------------------------------------------------------------- flashcards
    def flashcard_pool(
        self, unit_id: Optional[str] = None, min_weight: float = 0.0
    ) -> list[dict[str, Any]]:
        where = [
            "c.subject_id=?",
            "c.canonical_kp_id IS NOT NULL",
            "TRIM(COALESCE(c.canonical_name, '')) != ''",
            "("
            "TRIM(COALESCE(k.plain_en, '')) != ''"
            " OR TRIM(COALESCE(k.definition_quote, '')) != ''"
            ")",
        ]
        params: list[Any] = [self.subject_id]
        if unit_id == "methods":
            where.append("c.ap_unit IN ('0','EM')")
        elif unit_id:
            where.append("c.ap_unit=?")
            params.append(unit_id)
        if min_weight > 0:
            where.append("c.weight >= ?")
            params.append(min_weight)
        with self._know() as conn:
            rows = conn.execute(
                f"""
                SELECT c.cluster_id, c.weight, c.weight_tier
                FROM concept_clusters c
                JOIN knowledge_points k ON k.kp_id=c.canonical_kp_id
                WHERE {" AND ".join(where)}
                ORDER BY c.weight DESC, c.canonical_name
                """,
                params,
            ).fetchall()
        return [dict(r) for r in rows]

    def flashcard_ids(self, unit_id: Optional[str] = None, min_weight: float = 0.0) -> list[str]:
        return [item["cluster_id"] for item in self.flashcard_pool(unit_id, min_weight)]

    def get_flashcard_concepts(self, concept_ids: list[str]) -> list[dict[str, Any]]:
        if not concept_ids:
            return []
        details = self._concept_details(concept_ids)
        out = []
        for concept_id in concept_ids:
            detail = details.get(concept_id)
            if detail:
                out.append(detail)
        return out

    # ------------------------------------------------------------------ assets
    def asset_url(self, path: str) -> str:
        base = (self.settings.asset_base_url or "/assets").rstrip("/")
        if path.startswith("assets/"):
            path = path[len("assets/") :]
        if base in ("", "/assets") and self.settings.asset_signing_required:
            return sign_asset_url(
                path,
                "/assets",
                self.settings.resolved_asset_signing_key,
                self.settings.asset_url_ttl_seconds,
            )
        return f"{base}/{path.lstrip('/')}"
