"use client";

import { ArrowLeft, BookOpen, Check, Loader2, Pencil, Plus, Search, Sparkles, Trash2 } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { AdminModal } from "@/components/AdminModal";
import { StarRating } from "@/components/StarRating";
import { useAdmin, useAdminSubject } from "@/components/AdminShell";
import { apiDelete, apiGet, apiPatch, apiPost } from "@/lib/api";
import type { Concept, QuestionConceptLink, QuestionDetail } from "@/lib/types";

type EditOption = {
  label: string;
  content: string;
  is_correct: boolean;
  explanation: string;
  ai_explanation: string;
};

type EditForm = {
  stem: string;
  context: string;
  answer_text: string;
  answer_source: string;
  answer_confidence: string;
  options: EditOption[];
};

export default function QuestionDetailPage() {
  const params = useParams<{ questionId: string }>();
  const admin = useAdmin();
  const { subjectId, subject } = useAdminSubject();
  const canEdit = Boolean(admin?.can_edit_content);
  const [question, setQuestion] = useState<QuestionDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [editOpen, setEditOpen] = useState(false);
  const [form, setForm] = useState<EditForm | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [starSaving, setStarSaving] = useState(false);
  const [starError, setStarError] = useState<string | null>(null);
  const [linkOpen, setLinkOpen] = useState(false);
  const [linkQuery, setLinkQuery] = useState("");
  const [linkResults, setLinkResults] = useState<Concept[]>([]);
  const [linkSearching, setLinkSearching] = useState(false);
  const [linkError, setLinkError] = useState<string | null>(null);
  const [linkConcept, setLinkConcept] = useState<Concept | null>(null);
  const [linkRelation, setLinkRelation] = useState<"core" | "supporting" | "confusable">("core");
  const [linkOption, setLinkOption] = useState("");
  const [linkSaving, setLinkSaving] = useState(false);
  const [newConceptOpen, setNewConceptOpen] = useState(false);
  const [newConcept, setNewConcept] = useState({ name: "", definition: "", unit: "", topic: "" });
  const [creatingConcept, setCreatingConcept] = useState(false);
  const [conceptError, setConceptError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    apiGet<QuestionDetail>(
      `/content/questions/${params.questionId}?subject=${encodeURIComponent(subjectId)}`,
    )
      .then((value) => {
        if (!alive) return;
        setQuestion(value);
        setForm({
          stem: value.stem,
          context: value.context || "",
          answer_text: value.answer_text || "",
          answer_source: value.answer_source || "",
          answer_confidence: value.answer_confidence || "",
          options: value.options.map((option) => ({
            label: option.label,
            content: option.content,
            is_correct: option.is_correct === 1,
            explanation: option.explanation || "",
            ai_explanation: option.ai_explanation || "",
          })),
        });
      })
      .catch((e: Error) => alive && setError(e.message));
    return () => {
      alive = false;
    };
  }, [params.questionId, subjectId]);

  async function saveQuestion(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!form) return;
    setSaving(true);
    setSaveError(null);
    try {
      const payload: Record<string, unknown> = {
        stem: form.stem,
        context: form.context,
        answer_text: form.answer_text,
        answer_source: form.answer_source || null,
        answer_confidence: form.answer_confidence || null,
      };
      if (question?.section === "MCQ") {
        payload.options = form.options.map((option) => ({
          label: option.label,
          content: option.content,
          is_correct: option.is_correct,
          explanation: option.explanation || null,
          ai_explanation: option.ai_explanation || null,
        }));
      }
      await apiPatch(
        `/content/questions/${params.questionId}?subject=${encodeURIComponent(subjectId)}`,
        payload,
      );
      const refreshed = await apiGet<QuestionDetail>(
        `/content/questions/${params.questionId}?subject=${encodeURIComponent(subjectId)}`,
      );
      setQuestion(refreshed);
      setEditOpen(false);
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : "保存失败");
    } finally {
      setSaving(false);
    }
  }

  async function saveStars(next: number | null) {
    if (!question) return;
    const previous = question.stars ?? null;
    setStarSaving(true);
    setStarError(null);
    setQuestion((prev) => (prev ? { ...prev, stars: next } : prev));
    try {
      await apiPatch(
        `/content/questions/${question.question_id}/stars?subject=${encodeURIComponent(subjectId)}`,
        { stars: next },
      );
    } catch (e) {
      setQuestion((prev) => (prev ? { ...prev, stars: previous } : prev));
      setStarError(e instanceof Error ? e.message : "星级保存失败");
    } finally {
      setStarSaving(false);
    }
  }

  async function searchConcepts(event?: React.FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    const q = linkQuery.trim();
    if (!q) return;
    setLinkSearching(true);
    setLinkError(null);
    try {
      const result = await apiGet<{ concepts: Concept[] }>(
        `/content/knowledge/concepts?q=${encodeURIComponent(q)}&limit=30&subject=${encodeURIComponent(subjectId)}`,
      );
      setLinkResults(result.concepts);
    } catch (e) {
      setLinkError(e instanceof Error ? e.message : "搜索失败");
    } finally {
      setLinkSearching(false);
    }
  }

  async function addConceptLink() {
    if (!linkConcept || !question) return;
    if (linkRelation === "confusable" && !linkOption) {
      setLinkError("易混知识点需要选择一个干扰项");
      return;
    }
    setLinkSaving(true);
    setLinkError(null);
    try {
      const result = await apiPost<{ ok: boolean; concepts: QuestionConceptLink[] }>(
        `/content/questions/${question.question_id}/concepts?subject=${encodeURIComponent(subjectId)}`,
        {
          concept_id: linkConcept.cluster_id,
          relation_type: linkRelation,
          option_label: linkRelation === "confusable" ? linkOption : null,
        },
      );
      setQuestion((prev) => (prev ? { ...prev, concepts: result.concepts } : prev));
      setLinkOpen(false);
      setLinkConcept(null);
      setLinkQuery("");
      setLinkResults([]);
      setLinkOption("");
      setLinkRelation("core");
    } catch (e) {
      setLinkError(e instanceof Error ? e.message : "关联失败");
    } finally {
      setLinkSaving(false);
    }
  }

  async function removeConceptLink(linkId: number) {
    if (!question) return;
    if (!window.confirm("移除这个题目—知识点关联？")) return;
    try {
      const result = await apiDelete<{ ok: boolean; concepts: QuestionConceptLink[] }>(
        `/content/questions/${question.question_id}/concepts/${linkId}?subject=${encodeURIComponent(subjectId)}`,
      );
      setQuestion((prev) => (prev ? { ...prev, concepts: result.concepts } : prev));
    } catch (e) {
      setError(e instanceof Error ? e.message : "移除失败");
    }
  }

  async function createConceptAndSelect(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!newConcept.name.trim() || !newConcept.definition.trim()) {
      setConceptError("名称和释义不能为空");
      return;
    }
    setCreatingConcept(true);
    setConceptError(null);
    try {
      const created = await apiPost<Concept>("/content/knowledge/concepts", {
        subject_id: subjectId,
        canonical_name: newConcept.name.trim(),
        definition: newConcept.definition.trim(),
        ap_unit: newConcept.unit || null,
        topic: newConcept.topic || null,
      });
      setLinkConcept(created);
      setLinkResults([created, ...linkResults]);
      setNewConceptOpen(false);
      setNewConcept({ name: "", definition: "", unit: "", topic: "" });
    } catch (e) {
      setConceptError(e instanceof Error ? e.message : "创建知识点失败");
    } finally {
      setCreatingConcept(false);
    }
  }

  function updateOption(index: number, patch: Partial<EditOption>) {
    setForm((prev) =>
      prev
        ? {
            ...prev,
            options: prev.options.map((option, optionIndex) =>
              optionIndex === index ? { ...option, ...patch } : option,
            ),
          }
        : prev,
    );
  }

  function setCorrect(index: number) {
    setForm((prev) =>
      prev
        ? {
            ...prev,
            options: prev.options.map((option, optionIndex) => ({
              ...option,
              is_correct: optionIndex === index,
            })),
          }
        : prev,
    );
  }

  if (error) {
    return <div className="a-card p-5 text-[13px] text-[var(--danger)]">{error}</div>;
  }

  if (!question) {
    return (
      <div className="grid place-items-center py-24">
        <Loader2 size={24} className="animate-spin text-[var(--primary)]" />
      </div>
    );
  }

  const originLabel =
    question.admin_origin === "admin_created"
      ? "Admin 新建"
      : question.admin_origin === "admin_edited"
        ? "Admin 修改"
        : null;

  return (
    <div className="mx-auto max-w-5xl">
      <Link href={`/content/papers/${question.paper_id}`} className="a-btn a-btn-sm mb-4">
        <ArrowLeft size={14} /> 返回试卷
      </Link>

      <div className="a-card p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="a-badge a-badge-primary font-mono">
              {question.section} {question.number}
            </span>
            {question.form && <span className="a-badge">{question.form}</span>}
            <span className="a-badge">{subject?.name || subjectId}</span>
            <span className="a-badge gap-1.5 py-1">
              星级
              <StarRating
                value={question.stars}
                size={12}
                label="题目星级"
                disabled={!canEdit || starSaving}
                onChange={canEdit ? saveStars : undefined}
              />
            </span>
            {originLabel && (
              <span className={question.admin_origin === "admin_created" ? "a-badge a-badge-warn" : "a-badge a-badge-primary"}>
                <Sparkles size={12} /> {originLabel}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {canEdit ? (
              <button className="a-btn a-btn-sm" onClick={() => setEditOpen(true)}>
                <Pencil size={13} /> 编辑题目
              </button>
            ) : (
              <span className="a-badge">只读</span>
            )}
            <span className="font-mono text-[10.5px] text-[var(--faint)]">
              {question.question_id}
            </span>
          </div>
        </div>

        {starError && (
          <div className="mt-3 rounded-xl border border-[#f6d5d2] bg-[var(--danger-soft)] px-3 py-2 text-[12px] text-[var(--danger)]">
            星级保存失败：{starError}
          </div>
        )}

        <AdminModal
          open={editOpen && form !== null}
          onClose={() => setEditOpen(false)}
          title="编辑题目"
          wide
        >
          {form && (
            <form className="space-y-4" onSubmit={saveQuestion}>
              <label className="block text-[12px] font-medium">
                Stem 题干
                <textarea
                  className="a-input mt-1.5 min-h-[140px] resize-y leading-6"
                  value={form.stem}
                  onChange={(event) =>
                    setForm((prev) => (prev ? { ...prev, stem: event.target.value } : prev))
                  }
                  required
                />
              </label>
              <label className="block text-[12px] font-medium">
                Context / 材料
                <textarea
                  className="a-input mt-1.5 min-h-[100px] resize-y leading-6"
                  value={form.context}
                  onChange={(event) =>
                    setForm((prev) => (prev ? { ...prev, context: event.target.value } : prev))
                  }
                />
              </label>

              {question.section === "MCQ" && (
                <div>
                  <div className="mb-2 text-[12px] font-medium">选项与解析</div>
                  <div className="space-y-3">
                    {form.options.map((option, index) => (
                      <div key={option.label} className="rounded-xl border border-[var(--line)] p-3">
                        <div className="flex items-center gap-3">
                          <label className="flex items-center gap-1.5 text-[11.5px] font-medium">
                            <input
                              type="radio"
                              name="correct-option"
                              checked={option.is_correct}
                              onChange={() => setCorrect(index)}
                            />
                            正确项
                          </label>
                          <span className="font-mono text-[11px] text-[var(--faint)]">
                            {option.label}
                          </span>
                        </div>
                        <textarea
                          className="a-input mt-2 min-h-[70px] resize-y leading-5"
                          value={option.content}
                          onChange={(event) =>
                            updateOption(index, { content: event.target.value })
                          }
                          placeholder="选项内容"
                        />
                        <textarea
                          className="a-input mt-2 min-h-[60px] resize-y leading-5"
                          value={option.explanation}
                          onChange={(event) =>
                            updateOption(index, { explanation: event.target.value })
                          }
                          placeholder="原书解析"
                        />
                        <textarea
                          className="a-input mt-2 min-h-[60px] resize-y leading-5"
                          value={option.ai_explanation}
                          onChange={(event) =>
                            updateOption(index, { ai_explanation: event.target.value })
                          }
                          placeholder="AI 解析"
                        />
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <label className="block text-[12px] font-medium">
                Answer text / FRQ 评分标准
                <textarea
                  className="a-input mt-1.5 min-h-[120px] resize-y leading-6"
                  value={form.answer_text}
                  onChange={(event) =>
                    setForm((prev) =>
                      prev ? { ...prev, answer_text: event.target.value } : prev,
                    )
                  }
                />
              </label>
              <div className="grid grid-cols-2 gap-3">
                <label className="block text-[12px] font-medium">
                  Answer source
                  <input
                    className="a-input mt-1.5"
                    value={form.answer_source}
                    onChange={(event) =>
                      setForm((prev) =>
                        prev ? { ...prev, answer_source: event.target.value } : prev,
                      )
                    }
                  />
                </label>
                <label className="block text-[12px] font-medium">
                  Answer confidence
                  <input
                    className="a-input mt-1.5"
                    value={form.answer_confidence}
                    onChange={(event) =>
                      setForm((prev) =>
                        prev ? { ...prev, answer_confidence: event.target.value } : prev,
                      )
                    }
                  />
                </label>
              </div>
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
                  保存题目
                </button>
              </div>
            </form>
          )}
        </AdminModal>

        {question.context && (
          <div className="mt-4 whitespace-pre-wrap rounded-xl border border-[var(--line)] bg-[var(--surface-2)] p-4 text-[13px] leading-6 text-[var(--muted)]">
            {question.context}
          </div>
        )}

        {question.assets.filter((asset) => !asset.option_label).map((asset) => (
          <a
            key={asset.asset_id}
            href={`/${asset.path}`}
            target="_blank"
            rel="noreferrer"
            className="mt-4 block"
          >
            <img
              src={`/${asset.path}`}
              alt="题目图片"
              className="max-h-[420px] max-w-full rounded-xl border border-[var(--line)] bg-white"
            />
          </a>
        ))}

        <div className="mt-5 whitespace-pre-wrap text-[15px] leading-7">{question.stem}</div>

        {question.options.length > 0 && (
          <div className="mt-5 space-y-2">
            {question.options.map((option) => (
              <div
                key={option.label}
                className={[
                  "rounded-xl border px-4 py-3",
                  option.is_correct
                    ? "border-[#bfe8d1] bg-[var(--success-soft)]"
                    : "border-[var(--line)]",
                ].join(" ")}
              >
                <div className="flex items-start gap-3">
                  <span className="grid h-6 w-6 shrink-0 place-items-center rounded-md border border-[var(--line)] bg-white font-mono text-[11px] font-semibold">
                    {option.label}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="whitespace-pre-wrap text-[13.5px] leading-6">
                      {option.content}
                    </div>
                    {option.explanation && (
                      <div className="mt-2 whitespace-pre-wrap text-[11.5px] leading-5 text-[var(--muted)]">
                        {option.explanation}
                      </div>
                    )}
                    {option.ai_explanation && (
                      <div className="mt-2 whitespace-pre-wrap text-[11.5px] leading-5 text-[var(--muted)]">
                        AI：{option.ai_explanation}
                      </div>
                    )}
                  </div>
                  {option.is_correct === 1 && (
                    <Check size={16} className="mt-0.5 shrink-0 text-[var(--success)]" />
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {question.answer_text && (
          <div className="mt-5 rounded-xl border border-[var(--line)] bg-[var(--surface-2)] p-4">
            <div className="text-[10.5px] uppercase tracking-[0.12em] text-[var(--faint)]">
              Answer / Rubric Source
            </div>
            <div className="mt-2 max-h-[420px] overflow-y-auto whitespace-pre-wrap text-[12px] leading-5 text-[var(--muted)]">
              {question.answer_text}
            </div>
          </div>
        )}

        <div className="mt-4 flex flex-wrap gap-2 text-[10.5px] text-[var(--faint)]">
          <span>答案来源：{question.answer_source || "—"}</span>
          <span>·</span>
          <span>置信度：{question.answer_confidence || "—"}</span>
          <span>·</span>
          <span>正确项：{question.correct_answer || "—"}</span>
        </div>
      </div>

      <div className="a-card mt-4 p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="flex items-center gap-2 text-[15px] font-semibold">
              <BookOpen size={16} className="text-[var(--primary)]" /> 关联知识点
            </h2>
            <p className="mt-1 text-[11.5px] text-[var(--muted)]">
              题目与概念的核心/支持/易混关系；Admin 新建或修改的关联会单独标记。
            </p>
          </div>
          {canEdit && (
            <button className="a-btn a-btn-sm a-btn-primary" onClick={() => setLinkOpen(true)}>
              <Plus size={14} /> 添加关联
            </button>
          )}
        </div>

        <div className="mt-3 divide-y divide-[var(--line)] rounded-xl border border-[var(--line)]">
          {(question.concepts || []).map((concept) => (
            <div key={concept.link_id} className="flex flex-wrap items-start gap-3 px-3 py-3">
              <span className={
                concept.relation_type === "core"
                  ? "a-badge a-badge-primary"
                  : concept.relation_type === "confusable"
                    ? "a-badge a-badge-danger"
                    : "a-badge"
              }>
                {concept.relation_type}
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-[12.5px] font-medium">
                    {concept.canonical_name || concept.concept_id}
                  </span>
                  {concept.option_label && (
                    <span className="a-badge">option {concept.option_label}</span>
                  )}
                  {concept.admin_origin && (
                    <span className="a-badge a-badge-warn">
                      {concept.admin_origin === "admin_created" ? "Admin 新建" : "Admin 修改"}
                    </span>
                  )}
                </div>
                <div className="mt-1 font-mono text-[9.5px] text-[var(--faint)]">
                  {concept.ap_unit ? `Unit ${concept.ap_unit} · ` : ""}
                  {concept.topic || "—"} · {concept.concept_id}
                </div>
              </div>
              {canEdit && (
                <button
                  type="button"
                  className="a-btn a-btn-sm a-btn-danger"
                  onClick={() => removeConceptLink(concept.link_id)}
                >
                  <Trash2 size={13} /> 移除
                </button>
              )}
            </div>
          ))}
          {(question.concepts || []).length === 0 && (
            <div className="px-4 py-8 text-center text-[12px] text-[var(--faint)]">
              还没有关联知识点
            </div>
          )}
        </div>
      </div>

      <AdminModal
        open={linkOpen}
        onClose={() => setLinkOpen(false)}
        title="关联知识点"
        wide
      >
        <div className="space-y-3">
          {!newConceptOpen ? (
            <>
              <form className="flex gap-2" onSubmit={searchConcepts}>
                <div className="relative flex-1">
                  <Search size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--faint)]" />
                  <input
                    className="a-input pl-9"
                    value={linkQuery}
                    onChange={(event) => setLinkQuery(event.target.value)}
                    placeholder="搜索概念名称、定义或主题"
                  />
                </div>
                <button className="a-btn" disabled={linkSearching}>
                  {linkSearching ? <Loader2 size={14} className="animate-spin" /> : "搜索"}
                </button>
                <button
                  type="button"
                  className="a-btn"
                  onClick={() => {
                    setNewConceptOpen(true);
                    setNewConcept((prev) => ({ ...prev, name: linkQuery.trim() }));
                  }}
                >
                  <Plus size={14} /> 新建
                </button>
              </form>
              <div className="max-h-[300px] space-y-2 overflow-y-auto">
                {linkResults.map((concept) => (
                  <button
                    key={concept.cluster_id}
                    type="button"
                    className={[
                      "block w-full rounded-xl border p-3 text-left transition",
                      linkConcept?.cluster_id === concept.cluster_id
                        ? "border-[var(--primary)] bg-[var(--primary-soft)]"
                        : "border-[var(--line)] hover:bg-[var(--surface-2)]",
                    ].join(" ")}
                    onClick={() => setLinkConcept(concept)}
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-medium">{concept.canonical_name}</span>
                      {concept.admin_origin && (
                        <span className="a-badge a-badge-warn">Admin</span>
                      )}
                      <span className="a-badge">Unit {concept.ap_unit || "—"}</span>
                    </div>
                    <div className="mt-1 line-clamp-2 text-[11.5px] leading-5 text-[var(--muted)]">
                      {concept.description || "暂无描述"}
                    </div>
                  </button>
                ))}
                {linkResults.length === 0 && (
                  <div className="py-8 text-center text-[12px] text-[var(--faint)]">
                    输入关键词搜索已有知识点，或新建一个
                  </div>
                )}
              </div>
              {linkConcept && (
                <div className="rounded-xl border border-[var(--line)] bg-[var(--surface-2)] p-3">
                  <div className="text-[12px] font-medium">
                    已选择：{linkConcept.canonical_name}
                  </div>
                  <div className="mt-2 grid grid-cols-2 gap-2">
                    <label className="block text-[11.5px] font-medium">
                      关系
                      <select
                        className="a-input mt-1"
                        value={linkRelation}
                        onChange={(event) =>
                          setLinkRelation(event.target.value as typeof linkRelation)
                        }
                      >
                        <option value="core">core 核心</option>
                        <option value="supporting">supporting 支持</option>
                        <option value="confusable">confusable 易混</option>
                      </select>
                    </label>
                    {linkRelation === "confusable" && (
                      <label className="block text-[11.5px] font-medium">
                        干扰项
                        <select
                          className="a-input mt-1"
                          value={linkOption}
                          onChange={(event) => setLinkOption(event.target.value)}
                        >
                          <option value="">选择选项</option>
                          {question.options.map((option) => (
                            <option key={option.label} value={option.label}>{option.label}</option>
                          ))}
                        </select>
                      </label>
                    )}
                  </div>
                  <button
                    type="button"
                    className="a-btn a-btn-primary mt-3"
                    onClick={addConceptLink}
                    disabled={linkSaving}
                  >
                    {linkSaving ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
                    保存关联
                  </button>
                </div>
              )}
            </>
          ) : (
            <form className="space-y-3" onSubmit={createConceptAndSelect}>
              <div className="flex items-center justify-between">
                <div className="text-[12px] font-medium">新建概念（Admin 新建）</div>
                <button type="button" className="a-btn a-btn-sm" onClick={() => setNewConceptOpen(false)}>
                  返回搜索
                </button>
              </div>
              <label className="block text-[12px] font-medium">
                名称
                <input
                  className="a-input mt-1.5"
                  value={newConcept.name}
                  onChange={(event) => setNewConcept((prev) => ({ ...prev, name: event.target.value }))}
                  required
                />
              </label>
              <label className="block text-[12px] font-medium">
                释义
                <textarea
                  className="a-input mt-1.5 min-h-[110px] resize-y leading-6"
                  value={newConcept.definition}
                  onChange={(event) => setNewConcept((prev) => ({ ...prev, definition: event.target.value }))}
                  required
                />
              </label>
              <div className="grid grid-cols-2 gap-2">
                <label className="block text-[12px] font-medium">
                  Unit
                  <select
                    className="a-input mt-1.5"
                    value={newConcept.unit}
                    onChange={(event) => setNewConcept((prev) => ({ ...prev, unit: event.target.value }))}
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
                    value={newConcept.topic}
                    onChange={(event) => setNewConcept((prev) => ({ ...prev, topic: event.target.value }))}
                    placeholder="例如 1.1"
                  />
                </label>
              </div>
              {conceptError && (
                <div className="rounded-xl border border-[#f6d5d2] bg-[var(--danger-soft)] px-3 py-2 text-[12px] text-[var(--danger)]">
                  {conceptError}
                </div>
              )}
              <div className="flex justify-end">
                <button className="a-btn a-btn-primary" disabled={creatingConcept}>
                  {creatingConcept ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
                  创建并选择
                </button>
              </div>
            </form>
          )}
          {linkError && (
            <div className="rounded-xl border border-[#f6d5d2] bg-[var(--danger-soft)] px-3 py-2 text-[12px] text-[var(--danger)]">
              {linkError}
            </div>
          )}
        </div>
      </AdminModal>
    </div>
  );
}
