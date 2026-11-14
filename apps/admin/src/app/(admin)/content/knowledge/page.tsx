"use client";

import { BookOpen, FileText, Loader2, Pencil, Plus, Search, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";

import { AdminModal } from "@/components/AdminModal";
import { useAdmin, useAdminSubject } from "@/components/AdminShell";
import { apiGet, apiPatch, apiPost } from "@/lib/api";
import type { Concept, ConceptDetail, KnowledgePoint } from "@/lib/types";

type Tab = "concepts" | "kps";

export default function KnowledgePage() {
  const admin = useAdmin();
  const { subjectId, subject } = useAdminSubject();
  const canEdit = Boolean(admin?.can_edit_content);
  const [tab, setTab] = useState<Tab>("concepts");
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [concepts, setConcepts] = useState<Concept[]>([]);
  const [kps, setKps] = useState<KnowledgePoint[]>([]);
  const [page, setPage] = useState(0);
  const [total, setTotal] = useState(0);
  const pageSize = 50;
  const [selectedConcept, setSelectedConcept] = useState<ConceptDetail | null>(null);
  const [selectedKp, setSelectedKp] = useState<KnowledgePoint | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editOpen, setEditOpen] = useState(false);
  const [editForm, setEditForm] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [createBusy, setCreateBusy] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [createForm, setCreateForm] = useState({
    canonical_name: "",
    definition: "",
    ap_unit: "",
    topic: "",
  });

  useEffect(() => {
    setPage(0);
    setSelectedConcept(null);
    setSelectedKp(null);
  }, [subjectId]);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    const params = new URLSearchParams({
      limit: String(pageSize),
      offset: String(page * pageSize),
      subject: subjectId,
    });
    if (search) params.set("q", search);
    const path = tab === "concepts"
      ? `/content/knowledge/concepts?${params.toString()}`
      : `/content/knowledge/kps?${params.toString()}`;
    apiGet<
      | { concepts: Concept[]; total: number }
      | { kps: KnowledgePoint[]; total: number }
    >(path)
      .then((value) => {
        if (!alive) return;
        if ("concepts" in value) setConcepts(value.concepts);
        else setKps(value.kps);
        setTotal(value.total);
        setError(null);
      })
      .catch((e: Error) => alive && setError(e.message))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [tab, search, page, subjectId]);

  async function createConcept(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCreateBusy(true);
    setCreateError(null);
    try {
      const created = await apiPost<ConceptDetail>("/content/knowledge/concepts", {
        subject_id: subjectId,
        canonical_name: createForm.canonical_name.trim(),
        definition: createForm.definition.trim(),
        ap_unit: createForm.ap_unit || null,
        topic: createForm.topic || null,
      });
      setConcepts((prev) => [{ ...created, members: undefined }, ...prev]);
      setTotal((prev) => prev + 1);
      setSelectedConcept(created);
      setCreateOpen(false);
      setCreateForm({ canonical_name: "", definition: "", ap_unit: "", topic: "" });
    } catch (e) {
      setCreateError(e instanceof Error ? e.message : "创建知识点失败");
    } finally {
      setCreateBusy(false);
    }
  }

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPage(0);
    setSearch(query.trim());
  }

  async function openConcept(clusterId: string) {
    setDetailLoading(true);
    setSelectedConcept(null);
    try {
      setSelectedConcept(
        await apiGet<ConceptDetail>(
          `/content/knowledge/concepts/${clusterId}?subject=${encodeURIComponent(subjectId)}`,
        ),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setDetailLoading(false);
    }
  }

  async function openKp(kpId: string) {
    setDetailLoading(true);
    setSelectedKp(null);
    try {
      setSelectedKp(
        await apiGet<KnowledgePoint>(
          `/content/knowledge/kps/${kpId}?subject=${encodeURIComponent(subjectId)}`,
        ),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setDetailLoading(false);
    }
  }

  function openEdit() {
    if (selectedConcept) {
      setEditForm({
        canonical_name: selectedConcept.canonical_name,
        description: selectedConcept.description || "",
        ap_unit: selectedConcept.ap_unit || "",
        topic: selectedConcept.topic || "",
        status: selectedConcept.status,
        weight: String(selectedConcept.weight ?? 0),
      });
    } else if (selectedKp) {
      setEditForm({
        name: selectedKp.name,
        plain_en: selectedKp.plain_en || "",
        definition_quote: selectedKp.definition_quote || "",
        subheading: selectedKp.subheading || "",
        status: selectedKp.status,
        weight: String(selectedKp.weight ?? 0),
      });
    }
    setSaveError(null);
    setEditOpen(true);
  }

  async function saveEdit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setSaveError(null);
    try {
      if (selectedConcept) {
        const updated = await apiPatch<ConceptDetail>(
          `/content/knowledge/concepts/${selectedConcept.cluster_id}?subject=${encodeURIComponent(subjectId)}`,
          {
            ...editForm,
            weight: Number(editForm.weight || 0),
          },
        );
        setSelectedConcept(updated);
        setConcepts((prev) =>
          prev.map((item) =>
            item.cluster_id === updated.cluster_id
              ? { ...item, ...updated, members: undefined }
              : item,
          ),
        );
      } else if (selectedKp) {
        const updated = await apiPatch<KnowledgePoint>(
          `/content/knowledge/kps/${selectedKp.kp_id}?subject=${encodeURIComponent(subjectId)}`,
          {
            ...editForm,
            weight: Number(editForm.weight || 0),
          },
        );
        setSelectedKp(updated);
        setKps((prev) =>
          prev.map((item) => (item.kp_id === updated.kp_id ? updated : item)),
        );
      }
      setEditOpen(false);
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : "保存失败");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="text-[11px] uppercase tracking-[0.14em] text-[var(--faint)]">
            Content
          </div>
          <h1 className="mt-1 text-[27px] font-semibold tracking-[-0.03em]">知识点</h1>
          <p className="mt-1 text-[12.5px] text-[var(--muted)]">
            当前分类：{subject?.name || subjectId}。Concepts 是学生端使用的标准知识点；KPs 是教材原文条目。
            后台修改/新建会进入应用层覆盖，优先于本地同步内容。
          </p>
        </div>
        <div className="flex gap-2">
          <span className="a-badge"><BookOpen size={13} /> 内容源</span>
          {canEdit && tab === "concepts" && (
            <button className="a-btn a-btn-sm a-btn-primary" onClick={() => setCreateOpen(true)}>
              <Plus size={13} /> 新建概念
            </button>
          )}
        </div>
      </div>

      <div className="mb-4 grid gap-2 lg:grid-cols-2">
        <div className="a-card p-4">
          <div className="flex flex-wrap items-center gap-2">
            <BookOpen size={16} className="text-[var(--primary)]" />
            <span className="text-[13px] font-semibold">概念 Concepts</span>
            <span className="a-badge a-badge-primary">学生端实际使用</span>
          </div>
          <p className="mt-2 text-[12px] leading-5 text-[var(--muted)]">
            把多本教材、多个原始条目去重聚合后的「标准知识点」。学生知识图谱、题目—知识点关联、题目解析都读这一层；一个概念可以聚合多个 KP。
          </p>
          <p className="mt-1 text-[11px] leading-5 text-[var(--faint)]">
            要新增一个学生端可见的术语、修改图谱里的名称/释义、给题目关联知识点，优先用 Concepts。
          </p>
        </div>
        <div className="a-card p-4">
          <div className="flex flex-wrap items-center gap-2">
            <FileText size={16} className="text-[var(--accent)]" />
            <span className="text-[13px] font-semibold">原始知识点 KPs</span>
            <span className="a-badge a-badge-warn">教材来源 / 证据层</span>
          </div>
          <p className="mt-2 text-[12px] leading-5 text-[var(--muted)]">
            教材中某个具体 book / section / subheading 下的一条原文条目，带 original quote、页码和归属概念。它主要用于审校和追溯来源，不作为一个独立图谱节点直接展示。
          </p>
          <p className="mt-1 text-[11px] leading-5 text-[var(--faint)]">
            要修正某条教材原文或定义来源，编辑 KP；要新建术语或修改学生端知识点，使用 Concepts。
          </p>
        </div>
      </div>

      <div className="a-card mb-4 p-4">
        <div className="flex flex-wrap items-center gap-2">
          <Sparkles size={16} className="text-[var(--primary)]" />
          <h2 className="text-[13px] font-semibold">概念在系统中的作用</h2>
          <span className="a-badge a-badge-primary">学生端标准知识点</span>
        </div>
        <div className="mt-3 grid gap-2 md:grid-cols-2 xl:grid-cols-3">
          {[
            ["01", "标准知识点身份", "把多本教材、多个条目去重聚合，学生端只看到一个标准术语。"],
            ["02", "知识图谱节点", "Unit 结构、Topic 思维导图、概念详情、关系/易混/相关题目都挂在概念上。"],
            ["03", "题目关联桥梁", "question_concept_links 连接题目与概念，core / supporting / confusable 驱动题目解析和知识栏。"],
            ["04", "记忆卡片", "卡片池按概念权重和星级出卡，复习进度也以概念为单位。"],
            ["05", "教材证据聚合", "一个概念聚合多个原始 KP；KP 保留教材原文、页码和来源，概念负责学生端统一呈现。"],
            ["06", "Admin 内容优先", "Admin 新建/修改概念后进入有效内容层，学生端立即生效，并优先于本地同步内容。"],
          ].map(([number, title, body]) => (
            <div key={number} className="rounded-xl bg-[var(--surface-2)] p-3">
              <div className="font-mono text-[10px] text-[var(--faint)]">{number}</div>
              <div className="mt-1 text-[12px] font-semibold">{title}</div>
              <p className="mt-1 text-[11px] leading-5 text-[var(--muted)]">{body}</p>
            </div>
          ))}
        </div>
        <p className="mt-3 text-[10.5px] leading-5 text-[var(--faint)]">
          题目关联的是「概念」，不是原始 KP；知识图谱编辑器里的「补充知识点」只用于图谱补缺，不进入题目关联。
        </p>
      </div>

      <div className="mb-4 flex flex-wrap gap-2">
        <div className="flex gap-2">
          <button
            className={tab === "concepts" ? "a-btn a-btn-sm a-btn-primary" : "a-btn a-btn-sm"}
            onClick={() => { setTab("concepts"); setPage(0); setSelectedConcept(null); setSelectedKp(null); }}
          >
            概念 Concepts
          </button>
          <button
            className={tab === "kps" ? "a-btn a-btn-sm a-btn-primary" : "a-btn a-btn-sm"}
            onClick={() => { setTab("kps"); setPage(0); setSelectedConcept(null); setSelectedKp(null); }}
          >
            原始知识点 KPs
          </button>
        </div>
        <form className="relative min-w-[240px] flex-1" onSubmit={submit}>
          <Search size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--faint)]" />
          <input
            className="a-input pl-9"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={tab === "concepts" ? "按概念名称模糊搜索" : "按知识点名称模糊搜索"}
          />
        </form>
      </div>

      {error && (
        <div className="mb-3 rounded-xl border border-[#f6d5d2] bg-[var(--danger-soft)] px-3 py-2 text-[12px] text-[var(--danger)]">
          {error}
        </div>
      )}

      <div className="grid gap-4 xl:grid-cols-[1.3fr_0.7fr]">
        <div className="a-card overflow-hidden">
          {loading ? (
            <div className="grid place-items-center py-20">
              <Loader2 size={22} className="animate-spin text-[var(--primary)]" />
            </div>
          ) : tab === "concepts" ? (
            <div className="divide-y divide-[var(--line)]">
              {concepts.map((concept) => (
                <button
                  key={concept.cluster_id}
                  type="button"
                  className="block w-full px-5 py-4 text-left transition hover:bg-[var(--surface-2)]"
                  onClick={() => openConcept(concept.cluster_id)}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="font-medium">{concept.canonical_name}</div>
                      <div className="mt-1 line-clamp-2 text-[12px] leading-5 text-[var(--muted)]">
                        {concept.description || "暂无描述"}
                      </div>
                    </div>
                    <div className="flex shrink-0 flex-col items-end gap-1">
                      <span className="a-badge">Unit {concept.ap_unit || "—"}</span>
                      <span className="font-mono text-[10px] text-[var(--faint)]">
                        weight {concept.weight?.toFixed?.(1) ?? "—"}
                      </span>
                    </div>
                  </div>
                </button>
              ))}
              {concepts.length === 0 && (
                <div className="py-16 text-center text-[12px] text-[var(--faint)]">没有匹配的概念</div>
              )}
            </div>
          ) : (
            <div className="divide-y divide-[var(--line)]">
              {kps.map((kp) => (
                <button
                  key={kp.kp_id}
                  type="button"
                  className="block w-full px-5 py-4 text-left transition hover:bg-[var(--surface-2)]"
                  onClick={() => openKp(kp.kp_id)}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2 font-medium">
                        {kp.name}
                        {kp.admin_origin && (
                          <span className="a-badge a-badge-warn">
                            <Sparkles size={11} /> Admin 修改
                          </span>
                        )}
                      </div>
                      <div className="mt-1 line-clamp-2 text-[12px] leading-5 text-[var(--muted)]">
                        {kp.plain_en || kp.definition_quote || "暂无定义"}
                      </div>
                      <div className="mt-1 font-mono text-[10px] text-[var(--faint)]">
                        {kp.book_id} · {kp.section_id}
                      </div>
                    </div>
                    <span className="a-badge shrink-0">{kp.status}</span>
                  </div>
                </button>
              ))}
              {kps.length === 0 && (
                <div className="py-16 text-center text-[12px] text-[var(--faint)]">没有匹配的知识点</div>
              )}
            </div>
          )}
          <div className="flex flex-wrap items-center justify-between gap-2 border-t border-[var(--line)] px-4 py-3 text-[11px] text-[var(--muted)]">
            <span>
              共 {total} 条 · 第 {Math.min(page + 1, Math.max(1, Math.ceil(total / pageSize)))} /{" "}
              {Math.max(1, Math.ceil(total / pageSize))} 页
            </span>
            <div className="flex gap-2">
              <button
                type="button"
                className="a-btn a-btn-sm"
                disabled={page === 0 || loading}
                onClick={() => setPage((current) => Math.max(0, current - 1))}
              >
                上一页
              </button>
              <button
                type="button"
                className="a-btn a-btn-sm"
                disabled={loading || (page + 1) * pageSize >= total}
                onClick={() => setPage((current) => current + 1)}
              >
                下一页
              </button>
            </div>
          </div>
        </div>

        <aside className="a-card p-5">
          <div className="flex items-center justify-between gap-2">
            <h2 className="text-[14px] font-semibold">详情</h2>
            {(selectedConcept || selectedKp) &&
              (canEdit ? (
                <button className="a-btn a-btn-sm" onClick={openEdit}>
                  <Pencil size={13} /> 编辑
                </button>
              ) : (
                <span className="a-badge">只读</span>
              ))}
          </div>
          {detailLoading ? (
            <div className="grid place-items-center py-16">
              <Loader2 size={20} className="animate-spin text-[var(--primary)]" />
            </div>
          ) : selectedConcept ? (
            <div className="mt-3">
              <div className="text-[16px] font-semibold">{selectedConcept.canonical_name}</div>
              <div className="mt-1 text-[11px] leading-5 text-[var(--muted)]">
                学生端概念层 · 聚合 {selectedConcept.member_count} 个原始 KP
              </div>
              <div className="mt-1 flex flex-wrap items-center gap-2 text-[11px] text-[var(--faint)]">
                {selectedConcept.admin_origin && (
                  <span className="a-badge a-badge-warn">
                    {selectedConcept.admin_origin === "admin_created" ? "Admin 新建" : "Admin 修改"}
                  </span>
                )}
                <span>
                  {selectedConcept.cluster_id} · Unit {selectedConcept.ap_unit || "—"} ·{" "}
                  {selectedConcept.topic || "—"}
                </span>
              </div>
              <p className="mt-3 whitespace-pre-wrap text-[12.5px] leading-6 text-[var(--muted)]">
                {selectedConcept.description || "暂无概念描述"}
              </p>
              <div className="mt-4 text-[11px] uppercase tracking-[0.1em] text-[var(--faint)]">
                成员知识点（教材原始条目）
              </div>
              <div className="mt-2 space-y-3">
                {selectedConcept.members.map((member) => (
                  <div key={member.kp_id} className="rounded-lg bg-[var(--surface-2)] p-3">
                    <div className="text-[12px] font-medium">{member.name}</div>
                    <div className="mt-1 text-[11.5px] leading-5 text-[var(--muted)]">
                      {member.plain_en || member.definition_quote || "—"}
                    </div>
                    <div className="mt-1 font-mono text-[9.5px] text-[var(--faint)]">
                      {member.book_id} · {member.section_id}
                    </div>
                  </div>
                ))}
                {selectedConcept.members.length === 0 && (
                  <div className="text-[12px] text-[var(--faint)]">暂无成员知识点</div>
                )}
              </div>
            </div>
          ) : selectedKp ? (
            <div className="mt-3">
              <div className="text-[16px] font-semibold">{selectedKp.name}</div>
              <div className="mt-1 text-[11px] leading-5 text-[var(--muted)]">
                教材原始知识点 · {selectedKp.book_id} / {selectedKp.section_id} · 归属概念：
                {selectedKp.concept_cluster_id ? (
                  <button
                    type="button"
                    className="ml-1 font-mono text-[var(--primary)] hover:underline"
                    onClick={() => {
                      setTab("concepts");
                      setPage(0);
                      setSelectedKp(null);
                      void openConcept(selectedKp.concept_cluster_id!);
                    }}
                  >
                    {selectedKp.concept_cluster_id}
                  </button>
                ) : (
                  " 未关联"
                )}
              </div>
              <div className="mt-1 flex flex-wrap items-center gap-2 font-mono text-[10px] text-[var(--faint)]">
                {selectedKp.admin_origin && (
                  <span className="a-badge a-badge-warn">Admin 修改</span>
                )}
                <span>
                  {selectedKp.kp_id} · {selectedKp.book_id} · {selectedKp.section_id}
                </span>
              </div>
              <p className="mt-3 whitespace-pre-wrap text-[12.5px] leading-6 text-[var(--muted)]">
                {selectedKp.plain_en || "暂无 plain definition"}
              </p>
              {selectedKp.definition_quote && (
                <blockquote className="mt-3 border-l-2 border-[var(--line)] pl-3 text-[11.5px] leading-5 text-[var(--muted)]">
                  {selectedKp.definition_quote}
                </blockquote>
              )}
              <div className="mt-3 flex flex-wrap gap-2 text-[10.5px] text-[var(--faint)]">
                <span>status: {selectedKp.status}</span>
                <span>weight: {selectedKp.weight}</span>
                <span>confidence: {selectedKp.confidence ?? "—"}</span>
              </div>
            </div>
          ) : (
            <div className="py-16 text-center text-[12px] text-[var(--faint)]">
              从左侧选择一条记录查看详情
            </div>
          )}
        </aside>
      </div>

      <AdminModal
        open={editOpen}
        onClose={() => setEditOpen(false)}
        title={selectedConcept ? "编辑概念" : "编辑知识点"}
        wide
      >
        <form className="space-y-3" onSubmit={saveEdit}>
          {selectedConcept ? (
            <>
              <label className="block text-[12px] font-medium">
                概念名称
                <input
                  className="a-input mt-1.5"
                  value={editForm.canonical_name || ""}
                  onChange={(event) =>
                    setEditForm((prev) => ({ ...prev, canonical_name: event.target.value }))
                  }
                  required
                />
              </label>
              <label className="block text-[12px] font-medium">
                描述
                <textarea
                  className="a-input mt-1.5 min-h-[110px] resize-y leading-6"
                  value={editForm.description || ""}
                  onChange={(event) =>
                    setEditForm((prev) => ({ ...prev, description: event.target.value }))
                  }
                />
              </label>
              <div className="grid grid-cols-3 gap-3">
                <label className="block text-[12px] font-medium">
                  Unit
                  <input
                    className="a-input mt-1.5"
                    value={editForm.ap_unit || ""}
                    onChange={(event) =>
                      setEditForm((prev) => ({ ...prev, ap_unit: event.target.value }))
                    }
                  />
                </label>
                <label className="block text-[12px] font-medium">
                  Topic
                  <input
                    className="a-input mt-1.5"
                    value={editForm.topic || ""}
                    onChange={(event) =>
                      setEditForm((prev) => ({ ...prev, topic: event.target.value }))
                    }
                  />
                </label>
                <label className="block text-[12px] font-medium">
                  Weight
                  <input
                    className="a-input mt-1.5"
                    type="number"
                    step="0.1"
                    min="0"
                    value={editForm.weight || ""}
                    onChange={(event) =>
                      setEditForm((prev) => ({ ...prev, weight: event.target.value }))
                    }
                  />
                </label>
              </div>
              <label className="block text-[12px] font-medium">
                Status
                <input
                  className="a-input mt-1.5"
                  value={editForm.status || ""}
                  onChange={(event) =>
                    setEditForm((prev) => ({ ...prev, status: event.target.value }))
                  }
                />
              </label>
            </>
          ) : (
            <>
              <label className="block text-[12px] font-medium">
                知识点名称
                <input
                  className="a-input mt-1.5"
                  value={editForm.name || ""}
                  onChange={(event) =>
                    setEditForm((prev) => ({ ...prev, name: event.target.value }))
                  }
                  required
                />
              </label>
              <label className="block text-[12px] font-medium">
                Plain English definition
                <textarea
                  className="a-input mt-1.5 min-h-[110px] resize-y leading-6"
                  value={editForm.plain_en || ""}
                  onChange={(event) =>
                    setEditForm((prev) => ({ ...prev, plain_en: event.target.value }))
                  }
                />
              </label>
              <label className="block text-[12px] font-medium">
                Original quote
                <textarea
                  className="a-input mt-1.5 min-h-[110px] resize-y leading-6"
                  value={editForm.definition_quote || ""}
                  onChange={(event) =>
                    setEditForm((prev) => ({ ...prev, definition_quote: event.target.value }))
                  }
                />
              </label>
              <div className="grid grid-cols-3 gap-3">
                <label className="block text-[12px] font-medium">
                  Subheading
                  <input
                    className="a-input mt-1.5"
                    value={editForm.subheading || ""}
                    onChange={(event) =>
                      setEditForm((prev) => ({ ...prev, subheading: event.target.value }))
                    }
                  />
                </label>
                <label className="block text-[12px] font-medium">
                  Status
                  <input
                    className="a-input mt-1.5"
                    value={editForm.status || ""}
                    onChange={(event) =>
                      setEditForm((prev) => ({ ...prev, status: event.target.value }))
                    }
                  />
                </label>
                <label className="block text-[12px] font-medium">
                  Weight
                  <input
                    className="a-input mt-1.5"
                    type="number"
                    step="0.1"
                    min="0"
                    value={editForm.weight || ""}
                    onChange={(event) =>
                      setEditForm((prev) => ({ ...prev, weight: event.target.value }))
                    }
                  />
                </label>
              </div>
            </>
          )}
          {saveError && (
            <div className="rounded-xl border border-[#f6d5d2] bg-[var(--danger-soft)] px-3 py-2 text-[12px] text-[var(--danger)]">
              {saveError}
            </div>
          )}
          <div className="flex justify-end gap-2">
            <button type="button" className="a-btn" onClick={() => setEditOpen(false)}>
              取消
            </button>
            <button className="a-btn a-btn-primary" disabled={saving}>
              {saving ? <Loader2 size={14} className="animate-spin" /> : null}
              保存
            </button>
          </div>
        </form>
      </AdminModal>

      <AdminModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        title="新建概念（Admin 新建）"
        wide
      >
        <form className="space-y-3" onSubmit={createConcept}>
          <div className="rounded-xl border border-[#f4dfc4] bg-[var(--accent-soft)] px-3 py-2 text-[11.5px] leading-5 text-[var(--accent)]">
            这里创建的是学生端使用的概念层标准知识点，会进入知识图谱和题目关联，标记为 Admin 新建；
            本地同步遇到冲突时以 Admin 内容为准。原始 KP 需要来自具体教材 book/section，不能在这里新建。
          </div>
          <label className="block text-[12px] font-medium">
            科目分类
            <input
              className="a-input mt-1.5 bg-[var(--surface-2)]"
              value={subject?.name || subjectId}
              disabled
            />
          </label>
          <label className="block text-[12px] font-medium">
            名称
            <input
              className="a-input mt-1.5"
              value={createForm.canonical_name}
              onChange={(event) =>
                setCreateForm((prev) => ({ ...prev, canonical_name: event.target.value }))
              }
              required
              maxLength={300}
            />
          </label>
          <label className="block text-[12px] font-medium">
            释义
            <textarea
              className="a-input mt-1.5 min-h-[120px] resize-y leading-6"
              value={createForm.definition}
              onChange={(event) =>
                setCreateForm((prev) => ({ ...prev, definition: event.target.value }))
              }
              required
            />
          </label>
          <div className="grid grid-cols-2 gap-3">
            <label className="block text-[12px] font-medium">
              Unit
              <select
                className="a-input mt-1.5"
                value={createForm.ap_unit}
                onChange={(event) =>
                  setCreateForm((prev) => ({ ...prev, ap_unit: event.target.value }))
                }
              >
                <option value="">选择 Unit</option>
                {[1, 2, 3, 4, 5].map((unit) => (
                  <option key={unit} value={String(unit)}>Unit {unit}</option>
                ))}
              </select>
            </label>
            <label className="block text-[12px] font-medium">
              Topic（可选）
              <input
                className="a-input mt-1.5"
                value={createForm.topic}
                onChange={(event) =>
                  setCreateForm((prev) => ({ ...prev, topic: event.target.value }))
                }
                placeholder="例如 1.1"
              />
            </label>
          </div>
          {createError && (
            <div className="rounded-xl border border-[#f6d5d2] bg-[var(--danger-soft)] px-3 py-2 text-[12px] text-[var(--danger)]">
              {createError}
            </div>
          )}
          <div className="flex justify-end gap-2">
            <button type="button" className="a-btn" onClick={() => setCreateOpen(false)}>
              取消
            </button>
            <button className="a-btn a-btn-primary" disabled={createBusy}>
              {createBusy ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
              创建知识点
            </button>
          </div>
        </form>
      </AdminModal>
    </div>
  );
}
