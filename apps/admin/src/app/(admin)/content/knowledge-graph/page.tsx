"use client";

import {
  AlertTriangle,
  ArrowDown,
  ArrowUp,
  BookOpen,
  ChevronDown,
  ChevronRight,
  FolderTree,
  Loader2,
  Network,
  Plus,
  RefreshCw,
  Save,
  Search,
  Sparkles,
  Trash2,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { AdminModal } from "@/components/AdminModal";
import { useAdmin, useAdminSubject } from "@/components/AdminShell";
import { KnowledgeGraphCanvas } from "@/components/KnowledgeGraphCanvas";
import { apiDelete, apiGet, apiPost, apiPut } from "@/lib/api";
import type {
  KnowledgeGraphCustomConcept,
  KnowledgeGraphEditorNode,
  KnowledgeGraphSaveResult,
  KnowledgeGraphSearchResponse,
  KnowledgeGraphSearchResult,
  KnowledgeGraphTopicPayload,
  KnowledgeGraphUnitOption,
  KnowledgeGraphUnitsResponse,
} from "@/lib/types";

type NodeLocation = {
  node: KnowledgeGraphEditorNode;
  parent: KnowledgeGraphEditorNode | null;
  index: number;
};

type PickerState =
  | { mode: "child"; parentId: string }
  | { mode: "replace"; nodeId: string }
  | null;

const TYPE_LABEL: Record<KnowledgeGraphEditorNode["type"], string> = {
  branch: "分支",
  concept: "概念",
  supplement: "补充",
};

const TYPE_CLASS: Record<KnowledgeGraphEditorNode["type"], string> = {
  branch: "a-badge",
  concept: "a-badge a-badge-primary",
  supplement: "a-badge a-badge-warn",
};

function makeNodeId() {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `n-${crypto.randomUUID()}`;
  }
  return `n-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function normaliseLabel(value: string) {
  return value
    .replace(/[’‘]/g, "'")
    .replace(/[“”]/g, '"')
    .replace(/[–—]/g, "-")
    .replace(/\u00a0/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function isEnglishLabel(value: string) {
  return /^[\x20-\x7e]+$/.test(normaliseLabel(value));
}

function walkTree(
  node: KnowledgeGraphEditorNode,
  visit: (item: KnowledgeGraphEditorNode, parent: KnowledgeGraphEditorNode | null) => void,
  parent: KnowledgeGraphEditorNode | null = null,
) {
  visit(node, parent);
  for (const child of node.children) walkTree(child, visit, node);
}

function findLocation(
  root: KnowledgeGraphEditorNode,
  id: string,
): NodeLocation | null {
  if (root.id === id) return { node: root, parent: null, index: -1 };
  for (let index = 0; index < root.children.length; index += 1) {
    const child = root.children[index];
    if (child.id === id) return { node: child, parent: root, index };
    const nested = findLocation(child, id);
    if (nested) return nested;
  }
  return null;
}

function mapNode(
  node: KnowledgeGraphEditorNode,
  id: string,
  update: (item: KnowledgeGraphEditorNode) => KnowledgeGraphEditorNode,
): KnowledgeGraphEditorNode {
  if (node.id === id) return update(node);
  return {
    ...node,
    children: node.children.map((child) => mapNode(child, id, update)),
  };
}

function appendChild(
  node: KnowledgeGraphEditorNode,
  parentId: string,
  child: KnowledgeGraphEditorNode,
): KnowledgeGraphEditorNode {
  if (node.id === parentId) {
    return { ...node, children: [...node.children, child] };
  }
  return {
    ...node,
    children: node.children.map((item) => appendChild(item, parentId, child)),
  };
}

function removeNode(
  node: KnowledgeGraphEditorNode,
  id: string,
): KnowledgeGraphEditorNode {
  return {
    ...node,
    children: node.children
      .filter((child) => child.id !== id)
      .map((child) => removeNode(child, id)),
  };
}

function moveNode(
  node: KnowledgeGraphEditorNode,
  id: string,
  delta: number,
): KnowledgeGraphEditorNode {
  const index = node.children.findIndex((child) => child.id === id);
  if (index >= 0) {
    const target = index + delta;
    if (target < 0 || target >= node.children.length) return node;
    const children = [...node.children];
    [children[index], children[target]] = [children[target], children[index]];
    return { ...node, children };
  }
  return {
    ...node,
    children: node.children.map((child) => moveNode(child, id, delta)),
  };
}

function collectParentIds(node: KnowledgeGraphEditorNode, out: Set<string>) {
  if (node.children.length) out.add(node.id);
  for (const child of node.children) collectParentIds(child, out);
}

function collectAllIds(node: KnowledgeGraphEditorNode, out: Set<string>) {
  out.add(node.id);
  for (const child of node.children) collectAllIds(child, out);
}

function countNodes(node: KnowledgeGraphEditorNode): number {
  return 1 + node.children.reduce((total, child) => total + countNodes(child), 0);
}

function duplicateConceptNames(root: KnowledgeGraphEditorNode | null): string[] {
  if (!root) return [];
  const counts = new Map<string, { count: number; label: string }>();
  walkTree(root, (node) => {
    if (!node.concept_id || node.type === "branch") return;
    const current = counts.get(node.concept_id);
    counts.set(node.concept_id, {
      count: (current?.count || 0) + 1,
      label: node.label,
    });
  });
  return [...counts.entries()]
    .filter(([, value]) => value.count > 1)
    .map(([id, value]) => `${value.label}（${id}）`);
}

function validateTree(root: KnowledgeGraphEditorNode): string[] {
  const issues: string[] = [];
  const ids = new Set<string>();
  if (!root.children.length) return ["图谱至少需要一个子节点"];
  walkTree(root, (node, parent) => {
    if (!node.label.trim()) issues.push("存在标题为空的节点");
    else if (!isEnglishLabel(node.label)) {
      issues.push(`「${node.label}」仅支持英文、数字和常用符号`);
    }
    if (ids.has(node.id)) issues.push("节点 ID 重复，请刷新后重试");
    ids.add(node.id);
    if (node.type === "concept" && !node.concept_id) {
      issues.push(`「${node.label}」还没有关联知识点`);
    }
    if (node.type === "supplement") {
      if (!node.supplement?.definition.trim()) {
        issues.push(`补充知识点「${node.label}」缺少释义`);
      }
    }
    if (node.type === "branch" && parent && node.children.length === 0) {
      issues.push(`分支「${node.label}」至少需要一个子节点`);
    }
  });
  return [...new Set(issues)];
}

function toKnowledgeNode(result: KnowledgeGraphSearchResult): KnowledgeGraphEditorNode {
  if (result.kind === "concept") {
    return {
      id: makeNodeId(),
      label: result.name,
      type: "concept",
      concept_id: result.concept_id,
      concept_name: normaliseLabel(result.name),
      definition: result.definition,
      tier: result.tier || null,
      children: [],
    };
  }
  return {
    id: makeNodeId(),
    label: normaliseLabel(result.name),
    type: "supplement",
    concept_id: result.concept_id,
    concept_name: normaliseLabel(result.name),
    supplement: {
      id: result.concept_id,
      name: normaliseLabel(result.name),
      definition: result.definition,
      source: result.source || "admin",
      review_status: result.review_status || "draft",
    },
    children: [],
  };
}

function nodeIcon(type: KnowledgeGraphEditorNode["type"]) {
  if (type === "concept") return <BookOpen size={13} />;
  if (type === "supplement") return <Sparkles size={13} />;
  return <FolderTree size={13} />;
}

function sourceLabel(node: KnowledgeGraphEditorNode) {
  if (node.type !== "supplement") return "";
  if (node.supplement?.source === "ai_supplement") return "AI 补充";
  return "人工补充";
}

function TreeRow({
  node,
  depth,
  selectedId,
  expanded,
  duplicateIds,
  onSelect,
  onToggle,
}: {
  node: KnowledgeGraphEditorNode;
  depth: number;
  selectedId: string | null;
  expanded: Set<string>;
  duplicateIds: Set<string>;
  onSelect: (id: string) => void;
  onToggle: (id: string) => void;
}) {
  const hasChildren = node.children.length > 0;
  const open = expanded.has(node.id);
  const selected = selectedId === node.id;
  const duplicate = Boolean(
    node.concept_id && node.type !== "branch" && duplicateIds.has(node.concept_id),
  );
  const emptyBranch = node.type === "branch" && node.children.length === 0 && depth > 0;

  return (
    <div>
      <div
        role="button"
        tabIndex={0}
        className={`group flex cursor-pointer items-start gap-2 rounded-lg border px-2.5 py-2 transition ${
          selected
            ? "border-[var(--primary)] bg-[var(--primary-soft)]"
            : "border-transparent hover:border-[var(--line)] hover:bg-[var(--surface-2)]"
        }`}
        style={{ marginLeft: Math.min(depth, 8) * 15 }}
        onClick={() => onSelect(node.id)}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            onSelect(node.id);
          }
        }}
      >
        <button
          type="button"
          className="mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded text-[var(--faint)] hover:bg-white hover:text-[var(--ink)]"
          onClick={(event) => {
            event.stopPropagation();
            onToggle(node.id);
          }}
          aria-label={open ? "收起" : "展开"}
        >
          {hasChildren ? (
            open ? <ChevronDown size={15} /> : <ChevronRight size={15} />
          ) : (
            <span className="h-1 w-1 rounded-full bg-[var(--line)]" />
          )}
        </button>
        <span
          className={`mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded ${
            node.type === "concept"
              ? "bg-[var(--primary-soft)] text-[var(--primary)]"
              : node.type === "supplement"
                ? "bg-[var(--accent-soft)] text-[var(--accent)]"
                : "bg-[var(--surface-2)] text-[var(--muted)]"
          }`}
        >
          {nodeIcon(node.type)}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex min-w-0 items-center gap-2">
            <span className="truncate text-[12.5px] font-medium">{node.label}</span>
            <span className={`${TYPE_CLASS[node.type]} shrink-0`}>
              {TYPE_LABEL[node.type]}
            </span>
            {duplicate && (
              <span title="同一 Topic 中重复出现" className="shrink-0 text-[var(--accent)]">
                <AlertTriangle size={13} />
              </span>
            )}
          </div>
          <div className="mt-0.5 truncate font-mono text-[9.5px] text-[var(--faint)]">
            {node.type === "concept"
              ? `${node.tier || "concept"} · ${node.concept_id || "未关联"}`
              : node.type === "supplement"
                ? `${sourceLabel(node)} · ${node.supplement?.review_status || "draft"} · ${node.concept_id || ""}`
                : emptyBranch
                  ? "分支需要至少一个子节点"
                  : "结构分组，学生端不可点击"}
          </div>
        </div>
      </div>
      {open &&
        node.children.map((child) => (
          <TreeRow
            key={child.id}
            node={child}
            depth={depth + 1}
            selectedId={selectedId}
            expanded={expanded}
            duplicateIds={duplicateIds}
            onSelect={onSelect}
            onToggle={onToggle}
          />
        ))}
    </div>
  );
}

function KnowledgePicker({
  open,
  mode,
  unitId,
  topicCode,
  subjectId,
  subjectLabel,
  onClose,
  onSelect,
}: {
  open: boolean;
  mode: "child" | "replace";
  unitId: string;
  topicCode: string;
  subjectId: string;
  subjectLabel: string;
  onClose: () => void;
  onSelect: (result: KnowledgeGraphSearchResult) => void;
}) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<KnowledgeGraphSearchResult[]>([]);
  const [total, setTotal] = useState(0);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [name, setName] = useState("");
  const [definition, setDefinition] = useState("");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setQuery("");
    setResults([]);
    setTotal(0);
    setSearchError(null);
    setCreateOpen(false);
    setName("");
    setDefinition("");
    setCreateError(null);
  }, [open, mode]);

  useEffect(() => {
    if (!open || createOpen) return;
    const q = query.trim();
    if (!q) {
      setResults([]);
      setTotal(0);
      setSearchError(null);
      setSearching(false);
      return;
    }
    let alive = true;
    setSearching(true);
    const timer = window.setTimeout(() => {
      apiGet<KnowledgeGraphSearchResponse>(
        `/content/knowledge-graph/search?unit_id=${encodeURIComponent(unitId)}&q=${encodeURIComponent(q)}&limit=30&subject=${encodeURIComponent(subjectId)}`,
      )
        .then((response) => {
          if (!alive) return;
          setResults(response.results);
          setTotal(response.total);
          setSearchError(null);
        })
        .catch((error: Error) => {
          if (alive) setSearchError(error.message);
        })
        .finally(() => {
          if (alive) setSearching(false);
        });
    }, 220);
    return () => {
      alive = false;
      window.clearTimeout(timer);
    };
  }, [open, query, unitId, subjectId, createOpen]);

  function beginCreate() {
    setName(query.trim());
    setDefinition("");
    setCreateError(null);
    setCreateOpen(true);
  }

  async function createConcept(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCreating(true);
    setCreateError(null);
    try {
      const created = await apiPost<KnowledgeGraphCustomConcept>(
        `/content/knowledge-graph/custom-concepts?subject=${encodeURIComponent(subjectId)}`,
        { unit_id: unitId, topic_code: topicCode || null, name, definition },
      );
      onSelect({
        kind: "supplement",
        concept_id: created.concept_id,
        name: created.name,
        definition: created.definition,
        source: created.source,
        review_status: created.review_status,
        topic_code: created.topic_code,
      });
    } catch (error) {
      setCreateError(error instanceof Error ? error.message : "创建失败");
    } finally {
      setCreating(false);
    }
  }

  return (
    <AdminModal
      open={open}
      onClose={onClose}
      title={mode === "replace" ? "更换知识点" : "添加知识点"}
      wide
    >
      <div className="space-y-3">
        <div className="rounded-xl border border-[var(--line)] bg-[var(--surface-2)] px-3 py-2 text-[12px] leading-5 text-[var(--muted)]">
          先从当前 Unit 的本地知识库搜索；找不到时再创建补充知识点。补充知识点会标记为草稿，
          不会伪装成教材原文。
        </div>

        {!createOpen ? (
          <>
            <label className="relative block">
              <Search
                size={15}
                className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--faint)]"
              />
              <input
                autoFocus
                className="a-input pl-9"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="搜索概念名称、定义或主题"
                maxLength={200}
              />
            </label>

            <div className="flex items-center justify-between gap-2 text-[11px] text-[var(--faint)]">
              <span>
                {query.trim()
                  ? searching
                    ? "正在搜索…"
                    : `找到 ${total} 个本地结果`
                  : "输入关键词开始搜索"}
              </span>
              <button
                type="button"
                className="a-btn a-btn-sm"
                onClick={beginCreate}
                disabled={!query.trim()}
              >
                <Plus size={13} /> 创建新的补充知识点
              </button>
            </div>

            {searchError && (
              <div className="rounded-xl border border-[#f6d5d2] bg-[var(--danger-soft)] px-3 py-2 text-[12px] text-[var(--danger)]">
                {searchError}
              </div>
            )}

            <div className="max-h-[420px] space-y-2 overflow-y-auto">
              {results.map((result) => (
                <button
                  key={`${result.kind}-${result.concept_id}`}
                  type="button"
                  className="block w-full rounded-xl border border-[var(--line)] bg-white p-3 text-left transition hover:border-[var(--primary)] hover:bg-[var(--primary-soft)]"
                  onClick={() => onSelect(result)}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-medium">{result.name}</span>
                        <span
                          className={
                            result.kind === "concept"
                              ? "a-badge a-badge-primary"
                              : "a-badge a-badge-warn"
                          }
                        >
                          {result.kind === "concept" ? "知识库概念" : "已有补充"}
                        </span>
                        {result.tier && <span className="a-badge">{result.tier}</span>}
                      </div>
                      <div className="mt-1 line-clamp-2 text-[11.5px] leading-5 text-[var(--muted)]">
                        {result.definition || "暂无释义"}
                      </div>
                      <div className="mt-1 font-mono text-[9.5px] text-[var(--faint)]">
                        {result.concept_id}
                      </div>
                    </div>
                    <span className="a-badge shrink-0">
                      {result.topic_code || "Unit"}
                    </span>
                  </div>
                </button>
              ))}
              {query.trim() && !searching && results.length === 0 && !searchError && (
                <div className="rounded-xl border border-dashed border-[var(--line)] py-10 text-center">
                  <div className="text-[12.5px] font-medium">本地没有找到「{query.trim()}」</div>
                  <p className="mt-1 text-[11.5px] text-[var(--muted)]">
                    可以创建补充知识点，保存后学生端可点击查看释义。
                  </p>
                  <button type="button" className="a-btn a-btn-primary a-btn-sm mt-3" onClick={beginCreate}>
                    <Plus size={13} /> 创建新的补充知识点
                  </button>
                </div>
              )}
            </div>
          </>
        ) : (
          <form className="space-y-3" onSubmit={createConcept}>
            <div className="rounded-xl border border-[#f4dfc4] bg-[var(--accent-soft)] px-3 py-2 text-[11.5px] leading-5 text-[var(--accent)]">
              当前科目：{subjectLabel}。新节点将以「补充知识点」进入图谱，来源标记为人工补充；
              它只用于图谱补缺，不进入题目关联。
            </div>
            <label className="block text-[12px] font-medium">
              知识点名称（英文）
              <input
                autoFocus
                className="a-input mt-1.5"
                value={name}
                onChange={(event) => setName(event.target.value)}
                required
                maxLength={300}
              />
            </label>
            <label className="block text-[12px] font-medium">
              释义
              <textarea
                className="a-input mt-1.5 min-h-[130px] resize-y leading-6"
                value={definition}
                onChange={(event) => setDefinition(event.target.value)}
                required
                maxLength={8000}
                placeholder="写一句学生能看懂的英文释义"
              />
            </label>
            {createError && (
              <div className="rounded-xl border border-[#f6d5d2] bg-[var(--danger-soft)] px-3 py-2 text-[12px] text-[var(--danger)]">
                {createError}
              </div>
            )}
            <div className="flex justify-between gap-2">
              <button type="button" className="a-btn" onClick={() => setCreateOpen(false)}>
                返回搜索
              </button>
              <button className="a-btn a-btn-primary" disabled={creating}>
                {creating ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
                创建并添加
              </button>
            </div>
          </form>
        )}
      </div>
    </AdminModal>
  );
}

export default function KnowledgeGraphPage() {
  const admin = useAdmin();
  const { subjectId, subject } = useAdminSubject();
  const [units, setUnits] = useState<KnowledgeGraphUnitOption[]>([]);
  const [canEdit, setCanEdit] = useState(false);
  const [unitId, setUnitId] = useState("");
  const [topicCode, setTopicCode] = useState("");
  const [payload, setPayload] = useState<KnowledgeGraphTopicPayload | null>(null);
  const [tree, setTree] = useState<KnowledgeGraphEditorNode | null>(null);
  const [revision, setRevision] = useState(0);
  const [source, setSource] = useState<"release" | "draft">("release");
  const [originalJson, setOriginalJson] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [loadingUnits, setLoadingUnits] = useState(true);
  const [loadingTree, setLoadingTree] = useState(false);
  const [saving, setSaving] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [picker, setPicker] = useState<PickerState>(null);
  const [branchParentId, setBranchParentId] = useState<string | null>(null);
  const [branchLabel, setBranchLabel] = useState("");
  const [branchError, setBranchError] = useState<string | null>(null);

  const currentUnit = units.find((unit) => unit.unit_id === unitId) || null;
  const currentTopic = currentUnit?.topics.find((topic) => topic.topic_code === topicCode) || null;
  const dirty = Boolean(tree && originalJson && JSON.stringify(tree) !== originalJson);
  const issues = useMemo(() => (tree ? validateTree(tree) : []), [tree]);
  const duplicateNames = useMemo(() => duplicateConceptNames(tree), [tree]);
  const selected = useMemo(
    () => (tree && selectedId ? findLocation(tree, selectedId) : null),
    [tree, selectedId],
  );
  const duplicateIdSet = useMemo(() => {
    const counts = new Map<string, number>();
    if (tree) {
      walkTree(tree, (node) => {
        if (node.concept_id && node.type !== "branch") {
          counts.set(node.concept_id, (counts.get(node.concept_id) || 0) + 1);
        }
      });
    }
    return new Set(
      [...counts.entries()].filter(([, count]) => count > 1).map(([id]) => id),
    );
  }, [tree]);

  useEffect(() => {
    let alive = true;
    setLoadingUnits(true);
    setUnits([]);
    setUnitId("");
    setTopicCode("");
    setTree(null);
    setPayload(null);
    setError(null);
    apiGet<KnowledgeGraphUnitsResponse>(
      `/content/knowledge-graph/units?subject=${encodeURIComponent(subjectId)}`,
    )
      .then((response) => {
        if (!alive) return;
        setUnits(response.units);
        setCanEdit(response.can_edit);
        const firstUnit = response.units[0];
        if (firstUnit) {
          setUnitId(firstUnit.unit_id);
          const firstTopic =
            firstUnit.topics.find((topic) => topic.has_mindmap) || firstUnit.topics[0];
          setTopicCode(firstTopic?.topic_code || "");
        }
        setError(null);
      })
      .catch((error: Error) => {
        if (alive) setError(error.message);
      })
      .finally(() => {
        if (alive) setLoadingUnits(false);
      });
    return () => {
      alive = false;
    };
  }, [subjectId]);

  const loadTopic = useCallback(async () => {
    if (!unitId || !topicCode) {
      setPayload(null);
      setTree(null);
      setOriginalJson("");
      setSelectedId(null);
      return;
    }
    setLoadingTree(true);
    setError(null);
    setNotice(null);
    try {
      const data = await apiGet<KnowledgeGraphTopicPayload>(
        `/content/knowledge-graph/topic?unit_id=${encodeURIComponent(unitId)}&topic_code=${encodeURIComponent(topicCode)}&subject=${encodeURIComponent(subjectId)}`,
      );
      const openIds = new Set<string>();
      collectParentIds(data.tree, openIds);
      setPayload(data);
      setTree(data.tree);
      setRevision(data.revision);
      setSource(data.source);
      setOriginalJson(JSON.stringify(data.tree));
      setExpanded(openIds);
      setSelectedId(data.tree.id);
    } catch (error) {
      setError(error instanceof Error ? error.message : "加载知识图谱失败");
      setPayload(null);
      setTree(null);
    } finally {
      setLoadingTree(false);
    }
  }, [unitId, topicCode, subjectId]);

  useEffect(() => {
    void loadTopic();
  }, [loadTopic]);

  function confirmDiscard() {
    return !dirty || window.confirm("当前修改尚未保存，确定切换？");
  }

  function selectUnit(nextUnitId: string) {
    if (nextUnitId === unitId || !confirmDiscard()) return;
    const nextUnit = units.find((unit) => unit.unit_id === nextUnitId);
    const firstTopic =
      nextUnit?.topics.find((topic) => topic.has_mindmap) || nextUnit?.topics[0];
    setUnitId(nextUnitId);
    setTopicCode(firstTopic?.topic_code || "");
    setSelectedId(null);
  }

  function selectTopic(nextTopicCode: string) {
    if (nextTopicCode === topicCode || !confirmDiscard()) return;
    setTopicCode(nextTopicCode);
    setSelectedId(null);
  }

  function toggleNode(id: string) {
    setExpanded((previous) => {
      const next = new Set(previous);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function expandAll() {
    if (!tree) return;
    const ids = new Set<string>();
    collectAllIds(tree, ids);
    setExpanded(ids);
  }

  function collapseAll() {
    if (!tree) return;
    setExpanded(new Set());
  }

  function patchNode(id: string, update: (node: KnowledgeGraphEditorNode) => KnowledgeGraphEditorNode) {
    setTree((previous) => (previous ? mapNode(previous, id, update) : previous));
  }

  function changeLabel(value: string) {
    if (!selected) return;
    patchNode(selected.node.id, (node) => ({
      ...node,
      label: normaliseLabel(value),
      ...(node.type === "supplement" && node.supplement
        ? { supplement: { ...node.supplement, name: normaliseLabel(value) } }
        : {}),
    }));
  }

  function changeDefinition(value: string) {
    if (!selected) return;
    patchNode(selected.node.id, (node) =>
      node.supplement
        ? { ...node, supplement: { ...node.supplement, definition: value } }
        : node,
    );
  }

  function addKnowledgeNode(result: KnowledgeGraphSearchResult) {
    if (!picker || !tree) return;
    if (picker.mode === "replace") {
      patchNode(picker.nodeId, (node) => ({
        ...node,
        label: normaliseLabel(result.name),
        type: result.kind === "concept" ? "concept" : "supplement",
        concept_id: result.concept_id,
        concept_name: normaliseLabel(result.name),
        definition: result.kind === "concept" ? result.definition : null,
        tier: result.kind === "concept" ? result.tier || null : null,
        supplement:
          result.kind === "supplement"
            ? {
                id: result.concept_id,
                name: normaliseLabel(result.name),
                definition: result.definition,
                source: result.source || "admin",
                review_status: result.review_status || "draft",
              }
            : null,
      }));
    } else {
      const child = toKnowledgeNode(result);
      setTree((previous) =>
        previous ? appendChild(previous, picker.parentId, child) : previous,
      );
      setExpanded((previous) => new Set(previous).add(picker.parentId));
      setSelectedId(child.id);
    }
    setPicker(null);
    setNotice(null);
  }

  function openAddChild(parentId: string) {
    setPicker({ mode: "child", parentId });
  }

  function openReplace(nodeId: string) {
    setPicker({ mode: "replace", nodeId });
  }

  function openAddBranch(parentId: string) {
    setBranchParentId(parentId);
    setBranchLabel("New Branch");
    setBranchError(null);
  }

  function addBranch(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!tree || !branchParentId) return;
    const label = normaliseLabel(branchLabel);
    if (!label || !isEnglishLabel(label)) {
      setBranchError("分支标题必须是英文、数字和常用符号");
      return;
    }
    const branch: KnowledgeGraphEditorNode = {
      id: makeNodeId(),
      label,
      type: "branch",
      children: [],
    };
    setTree((previous) =>
      previous ? appendChild(previous, branchParentId, branch) : previous,
    );
    setExpanded((previous) => new Set(previous).add(branchParentId));
    setSelectedId(branch.id);
    setBranchParentId(null);
  }

  function deleteSelected() {
    if (!tree || !selected || !selected.parent) return;
    if (!window.confirm(`删除「${selected.node.label}」及其所有子节点？`)) return;
    const parentId = selected.parent.id;
    setTree((previous) => (previous ? removeNode(previous, selected.node.id) : previous));
    setSelectedId(parentId);
  }

  function moveSelected(delta: number) {
    if (!tree || !selected || !selected.parent) return;
    setTree((previous) =>
      previous ? moveNode(previous, selected.node.id, delta) : previous,
    );
  }

  async function save() {
    if (!tree || !unitId || !topicCode) return;
    const problems = validateTree(tree);
    if (problems.length) {
      setError(problems[0]);
      setNotice(null);
      return;
    }
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const result = await apiPut<KnowledgeGraphSaveResult>(
        `/content/knowledge-graph/topic?subject=${encodeURIComponent(subjectId)}`,
        {
          unit_id: unitId,
          topic_code: topicCode,
          tree,
          expected_revision: revision,
        },
      );
      setRevision(result.revision);
      setSource("draft");
      setOriginalJson(JSON.stringify(tree));
      setNotice(`已保存，学生端立即生效 · ${result.node_count} 个节点`);
      setUnits((previous) =>
        previous.map((unit) =>
          unit.unit_id === unitId
            ? {
                ...unit,
                topics: unit.topics.map((topic) =>
                  topic.topic_code === topicCode
                    ? {
                        ...topic,
                        has_draft: true,
                        revision: result.revision,
                        node_count: result.node_count,
                      }
                    : topic,
                ),
              }
            : unit,
        ),
      );
    } catch (error) {
      setError(error instanceof Error ? error.message : "保存失败");
    } finally {
      setSaving(false);
    }
  }

  async function resetDraft() {
    if (!unitId || !topicCode) return;
    if (!window.confirm("恢复为 Release 原图？当前 Topic 的后台修改会被删除。")) return;
    setResetting(true);
    setError(null);
    setNotice(null);
    try {
      await apiDelete(
        `/content/knowledge-graph/topic?unit_id=${encodeURIComponent(unitId)}&topic_code=${encodeURIComponent(topicCode)}&subject=${encodeURIComponent(subjectId)}`,
      );
      setUnits((previous) =>
        previous.map((unit) =>
          unit.unit_id === unitId
            ? {
                ...unit,
                topics: unit.topics.map((topic) =>
                  topic.topic_code === topicCode
                    ? { ...topic, has_draft: false, revision: 0 }
                    : topic,
                ),
              }
            : unit,
        ),
      );
      await loadTopic();
      setNotice("已恢复为 Release 原图");
    } catch (error) {
      setError(error instanceof Error ? error.message : "恢复失败");
    } finally {
      setResetting(false);
    }
  }

  return (
    <div>
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="text-[11px] uppercase tracking-[0.14em] text-[var(--faint)]">
            Content
          </div>
          <h1 className="mt-1 flex items-center gap-2 text-[27px] font-semibold tracking-[-0.03em]">
            <Network size={23} className="text-[var(--primary)]" />
            知识图谱
          </h1>
          <p className="mt-1 max-w-3xl text-[12.5px] leading-6 text-[var(--muted)]">
            当前分类：{subject?.name || subjectId}。编辑学生端思维导图的 Topic 树；
            修改保存在应用数据库的后台草稿中，不写入 Release 内容库，保存后学生端立即生效。
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            className="a-btn"
            onClick={resetDraft}
            disabled={!canEdit || resetting || source !== "draft" || saving}
          >
            {resetting ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
            恢复原图
          </button>
          <button
            type="button"
            className="a-btn a-btn-primary"
            onClick={save}
            disabled={!canEdit || saving || loadingTree || !dirty}
          >
            {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
            保存并生效
          </button>
        </div>
      </div>

      <div className="mb-4 grid gap-2 md:grid-cols-3">
        <div className="a-card p-3">
          <div className="flex items-center gap-2 text-[12px] font-semibold">
            <FolderTree size={14} className="text-[var(--muted)]" /> 分支 Branch
          </div>
          <p className="mt-1 text-[11px] leading-5 text-[var(--muted)]">
            结构分组，如 Theories、Obstacles。不可点击，只负责组织层级。
          </p>
        </div>
        <div className="a-card p-3">
          <div className="flex items-center gap-2 text-[12px] font-semibold">
            <BookOpen size={14} className="text-[var(--primary)]" /> 知识库概念 Concept
          </div>
          <p className="mt-1 text-[11px] leading-5 text-[var(--muted)]">
            来自 Release 的 concept_clusters，可点击查看定义、关系、易混题。
          </p>
        </div>
        <div className="a-card p-3">
          <div className="flex items-center gap-2 text-[12px] font-semibold">
            <Sparkles size={14} className="text-[var(--accent)]" /> 补充知识点 Supplement
          </div>
          <p className="mt-1 text-[11px] leading-5 text-[var(--muted)]">
            知识库没有的词，人工或 AI 补充；以草稿来源标记，可点击查看释义。
          </p>
        </div>
      </div>

      <div className="a-card mb-4 flex flex-wrap items-center gap-2 p-3">
        <select
          className="a-input max-w-[310px]"
          value={unitId}
          onChange={(event) => selectUnit(event.target.value)}
          disabled={loadingUnits}
        >
          {units.map((unit) => (
            <option key={unit.unit_id} value={unit.unit_id}>
              Unit {unit.unit_id} · {unit.title_en || unit.title}
            </option>
          ))}
        </select>
        <select
          className="a-input max-w-[360px]"
          value={topicCode}
          onChange={(event) => selectTopic(event.target.value)}
          disabled={!currentUnit || loadingTree}
        >
          {currentUnit?.topics.map((topic) => (
            <option key={topic.topic_code} value={topic.topic_code}>
              {topic.topic_code} · {topic.title_en}
            </option>
          ))}
        </select>
        <span className={source === "draft" ? "a-badge a-badge-warn" : "a-badge"}>
          {source === "draft" ? `后台草稿 rev.${revision}` : "Release 原图"}
        </span>
        <span className="a-badge">{tree ? countNodes(tree) : 0} 个节点</span>
        {dirty && <span className="a-badge a-badge-warn">未保存</span>}
        {payload?.title_zh && (
          <span className="text-[11px] text-[var(--faint)]">{payload.title_zh}</span>
        )}
      </div>

      {(error || notice || issues.length > 0 || duplicateNames.length > 0 || (payload?.unresolved_concept_ids.length || 0) > 0) && (
        <div className="mb-4 space-y-2">
          {error && (
            <div className="rounded-xl border border-[#f6d5d2] bg-[var(--danger-soft)] px-3 py-2 text-[12px] text-[var(--danger)]">
              {error}
            </div>
          )}
          {notice && (
            <div className="rounded-xl border border-[#ccecda] bg-[var(--success-soft)] px-3 py-2 text-[12px] text-[var(--success)]">
              {notice}
            </div>
          )}
          {issues.length > 0 && (
            <div className="rounded-xl border border-[#f4dfc4] bg-[var(--accent-soft)] px-3 py-2 text-[12px] text-[var(--accent)]">
              <div className="flex items-center gap-1.5 font-medium">
                <AlertTriangle size={13} /> 保存前需要处理
              </div>
              <ul className="mt-1 list-inside list-disc space-y-0.5">
                {issues.slice(0, 4).map((issue) => <li key={issue}>{issue}</li>)}
                {issues.length > 4 && <li>还有 {issues.length - 4} 项…</li>}
              </ul>
            </div>
          )}
          {duplicateNames.length > 0 && (
            <div className="rounded-xl border border-[#f4dfc4] bg-[var(--accent-soft)] px-3 py-2 text-[12px] text-[var(--accent)]">
              <div className="flex items-center gap-1.5 font-medium">
                <AlertTriangle size={13} /> 同一 Topic 中有重复知识点
              </div>
              <div className="mt-1">{duplicateNames.slice(0, 4).join("；")}</div>
              <div className="mt-1 text-[11px] opacity-80">
                重复会让学生端出现多个入口，建议保留一个。仍可保存。
              </div>
            </div>
          )}
          {(payload?.unresolved_concept_ids.length || 0) > 0 && (
            <div className="rounded-xl border border-[#f6d5d2] bg-[var(--danger-soft)] px-3 py-2 text-[12px] text-[var(--danger)]">
              有 {payload?.unresolved_concept_ids.length} 个知识点已不在当前 Release：
              {payload?.unresolved_concept_ids.join("、")}。请更换或删除后再保存。
            </div>
          )}
        </div>
      )}

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.25fr)_minmax(330px,0.75fr)]">
        <section className="a-card overflow-hidden">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--line)] px-3 py-2.5">
            <div className="flex gap-2">
              <button type="button" className="a-btn a-btn-sm" onClick={expandAll} disabled={!tree}>
                展开全部
              </button>
              <button type="button" className="a-btn a-btn-sm" onClick={collapseAll} disabled={!tree}>
                收起全部
              </button>
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                className="a-btn a-btn-sm"
                onClick={() => tree && openAddBranch(tree.id)}
                disabled={!canEdit || !tree}
              >
                <FolderTree size={13} /> 根分支
              </button>
              <button
                type="button"
                className="a-btn a-btn-sm a-btn-primary"
                onClick={() => tree && openAddChild(selected?.node.id || tree.id)}
                disabled={!canEdit || !tree}
              >
                <Plus size={13} /> 添加子节点
              </button>
            </div>
          </div>

          <div className="p-2.5">
            {loadingUnits || loadingTree ? (
              <div className="grid min-h-[420px] place-items-center py-24">
                <Loader2 size={24} className="animate-spin text-[var(--primary)]" />
              </div>
            ) : tree ? (
              <>
                {tree.children.length === 0 ? (
                  <div className="mx-2 mt-2 rounded-xl border border-dashed border-[var(--line)] px-4 py-16 text-center text-[12px] text-[var(--muted)]">
                    这个 Topic 还没有导图。点击「添加子节点」创建第一个知识点，再保存。
                  </div>
                ) : (
                  <KnowledgeGraphCanvas
                    tree={tree}
                    selectedId={selectedId}
                    expanded={expanded}
                    canEdit={canEdit}
                    onSelect={setSelectedId}
                    onToggle={toggleNode}
                    onAddChild={openAddChild}
                  />
                )}
              </>
            ) : (
              <div className="py-20 text-center text-[12px] text-[var(--faint)]">
                选择 Unit 和 Topic 后开始编辑
              </div>
            )}
          </div>
        </section>

        <aside className="a-card h-fit p-4 xl:sticky xl:top-4">
          <div className="flex items-center justify-between gap-2">
            <h2 className="text-[14px] font-semibold">节点设置</h2>
            <span className="a-badge">{canEdit ? "可编辑" : "只读"}</span>
          </div>
          {selected ? (
            <div className="mt-3 space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <span className={TYPE_CLASS[selected.node.type]}>
                  {TYPE_LABEL[selected.node.type]}
                </span>
                {selected.parent ? (
                  <span className="text-[10.5px] text-[var(--faint)]">
                    父节点：{selected.parent.label}
                  </span>
                ) : (
                  <span className="text-[10.5px] text-[var(--faint)]">Topic 根节点</span>
                )}
              </div>

              <label className="block text-[12px] font-medium">
                显示标题（英文）
                <input
                  className="a-input mt-1.5"
                  value={selected.node.label}
                  onChange={(event) => changeLabel(event.target.value)}
                  disabled={!canEdit}
                  maxLength={300}
                />
              </label>

              {selected.node.type === "concept" && (
                <div className="rounded-xl bg-[var(--surface-2)] p-3">
                  <div className="flex items-center justify-between gap-2">
                    <div className="text-[11px] uppercase tracking-[0.1em] text-[var(--faint)]">
                      知识库概念
                    </div>
                    <button
                      type="button"
                      className="a-btn a-btn-sm"
                      onClick={() => openReplace(selected.node.id)}
                      disabled={!canEdit}
                    >
                      <Search size={12} /> 更换
                    </button>
                  </div>
                  <div className="mt-1 text-[12px] font-medium">
                    {selected.node.concept_name || selected.node.label}
                  </div>
                  <div className="mt-1 font-mono text-[9.5px] text-[var(--faint)]">
                    {selected.node.concept_id} · {selected.node.tier || "concept"}
                  </div>
                  <p className="mt-2 line-clamp-6 text-[11.5px] leading-5 text-[var(--muted)]">
                    {selected.node.definition || "暂无定义"}
                  </p>
                </div>
              )}

              {selected.node.type === "supplement" && (
                <div className="rounded-xl border border-[#f4dfc4] bg-[var(--accent-soft)] p-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="a-badge a-badge-warn">{sourceLabel(selected.node)}</span>
                    <span className="a-badge">
                      {selected.node.supplement?.review_status || "draft"}
                    </span>
                    <button
                      type="button"
                      className="a-btn a-btn-sm ml-auto"
                      onClick={() => openReplace(selected.node.id)}
                      disabled={!canEdit}
                    >
                      <Search size={12} /> 更换
                    </button>
                  </div>
                  <label className="mt-2 block text-[11.5px] font-medium">
                    释义
                    <textarea
                      className="a-input mt-1.5 min-h-[130px] resize-y bg-white leading-5"
                      value={selected.node.supplement?.definition || ""}
                      onChange={(event) => changeDefinition(event.target.value)}
                      disabled={!canEdit}
                      maxLength={8000}
                    />
                  </label>
                  <div className="mt-1 font-mono text-[9.5px] opacity-75">
                    {selected.node.concept_id}
                  </div>
                </div>
              )}

              {selected.node.type === "branch" && (
                <div className="rounded-xl bg-[var(--surface-2)] p-3 text-[11.5px] leading-5 text-[var(--muted)]">
                  <p>结构分支不关联知识点，学生端不可点击。它至少需要一个子节点。</p>
                  {selected.parent && (
                    <button
                      type="button"
                      className="a-btn a-btn-sm mt-2"
                      onClick={() => openReplace(selected.node.id)}
                      disabled={!canEdit}
                    >
                      <BookOpen size={12} /> 关联知识点
                    </button>
                  )}
                </div>
              )}

              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  className="a-btn a-btn-sm"
                  onClick={() => openAddChild(selected.node.id)}
                  disabled={!canEdit}
                >
                  <Plus size={13} /> 添加子节点
                </button>
                <button
                  type="button"
                  className="a-btn a-btn-sm"
                  onClick={() => openAddBranch(selected.node.id)}
                  disabled={!canEdit}
                >
                  <FolderTree size={13} /> 添加分支
                </button>
              </div>

              {selected.parent && (
                <div className="flex flex-wrap gap-2 border-t border-[var(--line)] pt-3">
                  <button
                    type="button"
                    className="a-btn a-btn-sm"
                    onClick={() => moveSelected(-1)}
                    disabled={!canEdit || selected.index <= 0}
                  >
                    <ArrowUp size={13} /> 上移
                  </button>
                  <button
                    type="button"
                    className="a-btn a-btn-sm"
                    onClick={() => moveSelected(1)}
                    disabled={!canEdit || selected.index >= (selected.parent?.children.length || 0) - 1}
                  >
                    <ArrowDown size={13} /> 下移
                  </button>
                  <button
                    type="button"
                    className="a-btn a-btn-sm a-btn-danger ml-auto"
                    onClick={deleteSelected}
                    disabled={!canEdit}
                  >
                    <Trash2 size={13} /> 删除
                  </button>
                </div>
              )}
            </div>
          ) : (
            <div className="py-16 text-center text-[12px] text-[var(--faint)]">
              从左侧选择一个节点
            </div>
          )}
        </aside>
      </div>

      <div className="mt-4 rounded-xl border border-[var(--line)] bg-[var(--surface-2)] px-4 py-3 text-[11.5px] leading-5 text-[var(--muted)]">
        知识点类型说明：图谱里展示 3 种节点：分支、知识库概念、补充知识点。后台知识库内部还有
        core / supporting / confusable 权重层级，那是概念的相关性层级，不是新的节点类型。
        当前后台账号：{admin?.username || "—"}。
      </div>

      <KnowledgePicker
        open={Boolean(picker)}
        mode={picker?.mode === "replace" ? "replace" : "child"}
        unitId={unitId}
        topicCode={topicCode}
        subjectId={subjectId}
        subjectLabel={subject?.name || subjectId}
        onClose={() => setPicker(null)}
        onSelect={addKnowledgeNode}
      />

      <AdminModal
        open={Boolean(branchParentId)}
        onClose={() => setBranchParentId(null)}
        title="添加结构分支"
      >
        <form className="space-y-3" onSubmit={addBranch}>
          <label className="block text-[12px] font-medium">
            分支标题（英文）
            <input
              autoFocus
              className="a-input mt-1.5"
              value={branchLabel}
              onChange={(event) => setBranchLabel(event.target.value)}
              required
              maxLength={300}
            />
          </label>
          <p className="text-[11.5px] leading-5 text-[var(--muted)]">
            分支只是结构分组，不会出现在知识点详情里；添加后还需要给它添加至少一个子节点。
          </p>
          {branchError && (
            <div className="rounded-xl border border-[#f6d5d2] bg-[var(--danger-soft)] px-3 py-2 text-[12px] text-[var(--danger)]">
              {branchError}
            </div>
          )}
          <div className="flex justify-end gap-2">
            <button type="button" className="a-btn" onClick={() => setBranchParentId(null)}>
              取消
            </button>
            <button className="a-btn a-btn-primary">
              <Plus size={14} /> 添加分支
            </button>
          </div>
        </form>
      </AdminModal>
    </div>
  );
}
