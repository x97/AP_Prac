"use client";

import {
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  ListChecks,
  Loader2,
  Pencil,
  Search,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { AdminModal } from "@/components/AdminModal";
import { StarRating } from "@/components/StarRating";
import { useAdmin, useAdminSubject } from "@/components/AdminShell";
import { apiGet, apiPatch } from "@/lib/api";
import type {
  AdminQuestionListItem,
  AdminQuestionListResponse,
  AdminQuestionUnit,
  QuestionDetail,
} from "@/lib/types";

const LIMIT = 50;

const SOURCE_OPTIONS = [
  { value: "all", label: "全部来源" },
  { value: "unit", label: "单元练习" },
  { value: "real_exam", label: "真题" },
  { value: "mock_exam", label: "模拟题" },
  { value: "unit_practice", label: "章节练习" },
];

const PAPER_TYPE_LABEL: Record<string, string> = {
  real_exam: "真题",
  mock_exam: "模拟题",
  unit_practice: "章节练习",
  practice_bundle: "练习包",
  bundle: "题包",
};

function shortStem(value: string, length = 220) {
  return value.length > length ? `${value.slice(0, length)}…` : value;
}

export default function QuestionsPage() {
  const admin = useAdmin();
  const { subjectId, subject } = useAdminSubject();
  const canEdit = Boolean(admin?.can_edit_content);

  const [source, setSource] = useState("all");
  const [unit, setUnit] = useState("");
  const [section, setSection] = useState("all");
  const [query, setQuery] = useState("");
  const [appliedQuery, setAppliedQuery] = useState("");
  const [questions, setQuestions] = useState<AdminQuestionListItem[]>([]);
  const [units, setUnits] = useState<AdminQuestionUnit[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [starError, setStarError] = useState<string | null>(null);
  const [previewId, setPreviewId] = useState<string | null>(null);
  const [preview, setPreview] = useState<QuestionDetail | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [noteQuestion, setNoteQuestion] = useState<AdminQuestionListItem | null>(
    null,
  );
  const [noteDraft, setNoteDraft] = useState("");
  const [noteSaving, setNoteSaving] = useState(false);
  const [noteError, setNoteError] = useState<string | null>(null);
  const [previewNoteEditing, setPreviewNoteEditing] = useState(false);
  const [previewNoteDraft, setPreviewNoteDraft] = useState("");
  const [previewNoteSaving, setPreviewNoteSaving] = useState(false);
  const [previewNoteError, setPreviewNoteError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError(null);
    const params = new URLSearchParams({
      subject: subjectId,
      source,
      limit: String(LIMIT),
      offset: String(offset),
    });
    if (section !== "all") params.set("section", section);
    if (source === "unit" && unit) params.set("unit", unit);
    if (appliedQuery) params.set("q", appliedQuery);
    apiGet<AdminQuestionListResponse>(`/content/questions?${params.toString()}`)
      .then((value) => {
        if (!alive) return;
        setQuestions(value.questions);
        setUnits(value.units);
        setTotal(value.total);
      })
      .catch((e: Error) => alive && setError(e.message))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [subjectId, source, unit, section, appliedQuery, offset]);

  useEffect(() => {
    if (!previewId) return;
    let alive = true;
    setPreview(null);
    setPreviewError(null);
    setPreviewLoading(true);
    setPreviewNoteEditing(false);
    setPreviewNoteError(null);
    setPreviewNoteSaving(false);
    apiGet<QuestionDetail>(
      `/content/questions/${previewId}?subject=${encodeURIComponent(subjectId)}`,
    )
      .then((value) => {
        if (!alive) return;
        setPreview(value);
        setPreviewNoteDraft(value.admin_note || "");
      })
      .catch((e: Error) => alive && setPreviewError(e.message))
      .finally(() => alive && setPreviewLoading(false));
    return () => {
      alive = false;
    };
  }, [previewId, subjectId]);

  function closePreview() {
    setPreviewId(null);
    setPreview(null);
    setPreviewError(null);
    setPreviewLoading(false);
    setPreviewNoteEditing(false);
    setPreviewNoteError(null);
    setPreviewNoteSaving(false);
  }

  function changeSource(value: string) {
    setSource(value);
    if (value !== "unit") setUnit("");
    setOffset(0);
  }

  async function saveStars(questionId: string, stars: number | null) {
    const previous =
      questions.find((item) => item.question_id === questionId)?.stars ?? null;
    setStarError(null);
    setQuestions((prev) =>
      prev.map((item) =>
        item.question_id === questionId ? { ...item, stars } : item,
      ),
    );
    try {
      await apiPatch(
        `/content/questions/${questionId}/stars?subject=${encodeURIComponent(subjectId)}`,
        { stars },
      );
    } catch (e) {
      setQuestions((prev) =>
        prev.map((item) =>
          item.question_id === questionId ? { ...item, stars: previous } : item,
        ),
      );
      setStarError(e instanceof Error ? e.message : "星级保存失败");
    }
  }

  const page = Math.floor(offset / LIMIT) + 1;
  const pages = Math.max(1, Math.ceil(total / LIMIT));
  const previewMeta = previewId
    ? questions.find((item) => item.question_id === previewId) || null
    : null;

  function openNoteEditor(question: AdminQuestionListItem) {
    setNoteQuestion(question);
    setNoteDraft(question.admin_note || "");
    setNoteError(null);
  }

  function closeNoteEditor() {
    if (noteSaving) return;
    setNoteQuestion(null);
    setNoteError(null);
  }

  async function persistNote(
    questionId: string,
    note: string | null,
  ): Promise<string | null> {
    const result = await apiPatch<{
      ok: boolean;
      question_id: string;
      admin_note: string | null;
    }>(
      `/content/questions/${questionId}/note?subject=${encodeURIComponent(subjectId)}`,
      { note },
    );
    setQuestions((prev) =>
      prev.map((item) =>
        item.question_id === questionId
          ? { ...item, admin_note: result.admin_note }
          : item,
      ),
    );
    return result.admin_note;
  }

  async function saveNote() {
    if (!noteQuestion) return;
    setNoteSaving(true);
    setNoteError(null);
    try {
      await persistNote(noteQuestion.question_id, noteDraft.trim() || null);
      setNoteQuestion(null);
    } catch (e) {
      setNoteError(e instanceof Error ? e.message : "备注保存失败");
    } finally {
      setNoteSaving(false);
    }
  }

  async function savePreviewNote() {
    if (!preview) return;
    setPreviewNoteSaving(true);
    setPreviewNoteError(null);
    try {
      const saved = await persistNote(
        preview.question_id,
        previewNoteDraft.trim() || null,
      );
      setPreview((prev) => (prev ? { ...prev, admin_note: saved } : prev));
      setPreviewNoteEditing(false);
    } catch (e) {
      setPreviewNoteError(e instanceof Error ? e.message : "备注保存失败");
    } finally {
      setPreviewNoteSaving(false);
    }
  }

  return (
    <div>
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="text-[11px] uppercase tracking-[0.14em] text-[var(--faint)]">
            Content
          </div>
          <h1 className="mt-1 text-[27px] font-semibold tracking-[-0.03em]">题目</h1>
          <p className="mt-1 text-[12.5px] text-[var(--muted)]">
            当前内容分类：{subject?.name || subjectId}。按单元、真题、模拟题和题型筛选所有题目，可直接修改星级和备注。
          </p>
        </div>
        <span className="a-badge">
          <ListChecks size={13} /> {total} 道 · {subject?.name || subjectId}
        </span>
      </div>

      <div className="mb-4 flex flex-wrap gap-2">
        <select
          className="a-input w-auto"
          value={source}
          onChange={(event) => changeSource(event.target.value)}
        >
          {SOURCE_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        {source === "unit" && (
          <select
            className="a-input w-auto"
            value={unit}
            onChange={(event) => {
              setUnit(event.target.value);
              setOffset(0);
            }}
          >
            <option value="">全部单元</option>
            {units.map((item) => (
              <option key={item.unit_id} value={item.unit_id}>
                Unit {item.unit_id}
              </option>
            ))}
          </select>
        )}
        <select
          className="a-input w-auto"
          value={section}
          onChange={(event) => {
            setSection(event.target.value);
            setOffset(0);
          }}
        >
          <option value="all">全部题型</option>
          <option value="MCQ">选择题 MCQ</option>
          <option value="FRQ">问答题 FRQ</option>
        </select>
        <form
          className="flex min-w-[280px] flex-1 gap-2"
          onSubmit={(event) => {
            event.preventDefault();
            setAppliedQuery(query.trim());
            setOffset(0);
          }}
        >
          <div className="relative flex-1">
            <Search
              size={15}
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--faint)]"
            />
            <input
              className="a-input pl-9"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="搜索题干或题目 ID"
            />
          </div>
          <button className="a-btn">搜索</button>
        </form>
      </div>

      {error && (
        <div className="mb-3 rounded-xl border border-[#f6d5d2] bg-[var(--danger-soft)] px-3 py-2 text-[12px] text-[var(--danger)]">
          {error}
        </div>
      )}
      {starError && (
        <div className="mb-3 rounded-xl border border-[#f6d5d2] bg-[var(--danger-soft)] px-3 py-2 text-[12px] text-[var(--danger)]">
          星级保存失败：{starError}
        </div>
      )}

      <div className="a-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="a-table min-w-[1260px]">
            <thead>
              <tr>
                <th>题目</th>
                <th>来源</th>
                <th>题型</th>
                <th>选项</th>
                <th>星级</th>
                <th>备注</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={7} className="py-20 text-center">
                    <Loader2
                      size={22}
                      className="mx-auto animate-spin text-[var(--primary)]"
                    />
                  </td>
                </tr>
              ) : (
                questions.map((question) => (
                  <QuestionListRow
                    key={question.question_id}
                    question={question}
                    canEdit={canEdit}
                    onStarsChange={saveStars}
                    onEditNote={openNoteEditor}
                    onPreview={setPreviewId}
                  />
                ))
              )}
              {!loading && questions.length === 0 && (
                <tr>
                  <td
                    colSpan={7}
                    className="py-16 text-center text-[12px] text-[var(--faint)]"
                  >
                    没有匹配的题目
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[var(--line)] px-5 py-3 text-[11.5px] text-[var(--muted)]">
          <span>
            共 {total} 道 · 第 {page} / {pages} 页
          </span>
          <div className="flex gap-2">
            <button
              className="a-btn a-btn-sm"
              disabled={loading || offset === 0}
              onClick={() => setOffset(Math.max(0, offset - LIMIT))}
            >
              <ChevronLeft size={14} /> 上一页
            </button>
            <button
              className="a-btn a-btn-sm"
              disabled={loading || offset + LIMIT >= total}
              onClick={() => setOffset(offset + LIMIT)}
            >
              下一页 <ChevronRight size={14} />
            </button>
          </div>
        </div>
      </div>

      <AdminModal
        open={Boolean(previewId)}
        onClose={closePreview}
        title="题目预览"
        wide
      >
        {previewLoading ? (
          <div className="grid place-items-center py-16">
            <Loader2 size={22} className="animate-spin text-[var(--primary)]" />
          </div>
        ) : previewError ? (
          <div className="rounded-xl border border-[#f6d5d2] bg-[var(--danger-soft)] px-3 py-2 text-[12px] text-[var(--danger)]">
            {previewError}
          </div>
        ) : preview ? (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <span className="a-badge a-badge-primary font-mono">
                {preview.section} {preview.number}
              </span>
              {preview.form && <span className="a-badge">{preview.form}</span>}
              {previewMeta &&
                (previewMeta.unit_ids || []).map((unitId) => (
                  <span key={unitId} className="a-badge a-badge-primary">
                    Unit {unitId}
                  </span>
                ))}
              {previewMeta && (
                <>
                  <span className="a-badge">
                    {PAPER_TYPE_LABEL[previewMeta.paper_type || ""] ||
                      previewMeta.paper_type ||
                      "—"}
                  </span>
                  {previewMeta.year && (
                    <span className="a-badge">{previewMeta.year}</span>
                  )}
                </>
              )}
              <StarRating value={preview.stars} size={14} label="题目星级" />
            </div>
            {previewMeta && (
              <div className="text-[11.5px] text-[var(--muted)]">
                {previewMeta.paper_chinese_title ||
                  previewMeta.paper_title ||
                  previewMeta.paper_id}
              </div>
            )}
            {(canEdit || preview.admin_note) && (
              <div className="rounded-xl border border-[#f4dfc4] bg-[var(--accent-soft)] p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="text-[10.5px] uppercase tracking-[0.12em] text-[var(--accent)]">
                    管理员备注
                  </div>
                  {canEdit && !previewNoteEditing && (
                    <button
                      type="button"
                      className="a-btn a-btn-sm"
                      onClick={() => {
                        setPreviewNoteDraft(preview.admin_note || "");
                        setPreviewNoteError(null);
                        setPreviewNoteEditing(true);
                      }}
                    >
                      <Pencil size={12} />{" "}
                      {preview.admin_note ? "编辑备注" : "添加备注"}
                    </button>
                  )}
                </div>
                {previewNoteEditing ? (
                  <div className="mt-2">
                    <textarea
                      className="a-input min-h-[110px] resize-y leading-6"
                      value={previewNoteDraft}
                      maxLength={2000}
                      autoFocus
                      placeholder="例如：答案已核对 / 题干表述待确认 / 需要补充解析…"
                      onChange={(event) => setPreviewNoteDraft(event.target.value)}
                      onKeyDown={(event) => {
                        if (
                          (event.metaKey || event.ctrlKey) &&
                          event.key === "Enter"
                        ) {
                          event.preventDefault();
                          if (!previewNoteSaving) savePreviewNote();
                        }
                      }}
                    />
                    {previewNoteError && (
                      <div className="mt-2 rounded-lg border border-[#f6d5d2] bg-[var(--danger-soft)] px-3 py-2 text-[12px] text-[var(--danger)]">
                        {previewNoteError}
                      </div>
                    )}
                    <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
                      <span className="text-[10.5px] text-[var(--faint)]">
                        {previewNoteDraft.length}/2000 · 仅管理员可见
                      </span>
                      <div className="flex gap-2">
                        <button
                          type="button"
                          className="a-btn a-btn-sm"
                          disabled={previewNoteSaving}
                          onClick={() => {
                            setPreviewNoteEditing(false);
                            setPreviewNoteError(null);
                          }}
                        >
                          取消
                        </button>
                        <button
                          type="button"
                          className="a-btn a-btn-sm a-btn-primary"
                          disabled={previewNoteSaving}
                          onClick={savePreviewNote}
                        >
                          {previewNoteSaving ? (
                            <Loader2 size={13} className="animate-spin" />
                          ) : (
                            <Pencil size={13} />
                          )}
                          {previewNoteSaving ? "保存中…" : "保存备注"}
                        </button>
                      </div>
                    </div>
                  </div>
                ) : preview.admin_note ? (
                  <div className="mt-1 whitespace-pre-wrap text-[12.5px] leading-6 text-[var(--ink)]">
                    {preview.admin_note}
                  </div>
                ) : (
                  <div className="mt-1 text-[12px] text-[var(--muted)]">
                    暂无备注，点击右上角添加。
                  </div>
                )}
              </div>
            )}
            {preview.context && (
              <div className="whitespace-pre-wrap rounded-xl border border-[var(--line)] bg-[var(--surface-2)] p-4 text-[12.5px] leading-6 text-[var(--muted)]">
                {preview.context}
              </div>
            )}
            {preview.assets
              .filter((asset) => !asset.option_label)
              .map((asset) => (
                <img
                  key={asset.asset_id}
                  src={`/${asset.path}`}
                  alt="题目图片"
                  className="max-h-[360px] max-w-full rounded-xl border border-[var(--line)] bg-white"
                />
              ))}
            <div className="whitespace-pre-wrap text-[14px] leading-7">
              {preview.stem}
            </div>
            {preview.options.length > 0 && (
              <div className="space-y-2">
                {preview.options.map((option) => (
                  <div
                    key={option.label}
                    className={[
                      "rounded-xl border px-4 py-3",
                      option.is_correct === 1
                        ? "border-[#bfe8d1] bg-[var(--success-soft)]"
                        : "border-[var(--line)]",
                    ].join(" ")}
                  >
                    <div className="flex items-start gap-3">
                      <span className="grid h-6 w-6 shrink-0 place-items-center rounded-md border border-[var(--line)] bg-white font-mono text-[11px] font-semibold">
                        {option.label}
                      </span>
                      <div className="min-w-0 flex-1">
                        <div className="whitespace-pre-wrap text-[13px] leading-6">
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
                    </div>
                  </div>
                ))}
              </div>
            )}
            {preview.answer_text && (
              <div className="rounded-xl border border-[var(--line)] bg-[var(--surface-2)] p-4">
                <div className="text-[10.5px] uppercase tracking-[0.12em] text-[var(--faint)]">
                  Answer / Rubric
                </div>
                <div className="mt-2 max-h-[320px] overflow-y-auto whitespace-pre-wrap text-[12px] leading-5 text-[var(--muted)]">
                  {preview.answer_text}
                </div>
              </div>
            )}
            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[var(--line)] pt-3">
              <div className="text-[10.5px] text-[var(--faint)]">
                答案来源：{preview.answer_source || "—"} · 置信度：
                {preview.answer_confidence || "—"} · 正确项：
                {preview.correct_answer || "—"}
              </div>
              <Link
                href={`/content/questions/${preview.question_id}?subject=${encodeURIComponent(subjectId)}`}
                className="a-btn a-btn-sm a-btn-primary"
              >
                <ExternalLink size={13} /> 打开完整详情
              </Link>
            </div>
          </div>
        ) : null}
      </AdminModal>

      <AdminModal
        open={Boolean(noteQuestion)}
        onClose={closeNoteEditor}
        title="题目备注"
      >
        {noteQuestion && (
          <div className="space-y-3">
            <div className="rounded-xl border border-[var(--line)] bg-[var(--surface-2)] p-3">
              <div className="font-mono text-[10px] text-[var(--faint)]">
                {noteQuestion.question_id}
              </div>
              <p className="mt-1 line-clamp-3 text-[12.5px] leading-5">
                {shortStem(noteQuestion.stem, 180)}
              </p>
            </div>
            <textarea
              className="a-input min-h-[150px] resize-y leading-6"
              value={noteDraft}
              maxLength={2000}
              autoFocus
              placeholder="例如：答案已核对 / 题干表述待确认 / 需要补充解析…"
              onChange={(event) => setNoteDraft(event.target.value)}
              onKeyDown={(event) => {
                if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
                  event.preventDefault();
                  if (!noteSaving) saveNote();
                }
              }}
            />
            {noteError && (
              <div className="rounded-xl border border-[#f6d5d2] bg-[var(--danger-soft)] px-3 py-2 text-[12px] text-[var(--danger)]">
                {noteError}
              </div>
            )}
            <div className="flex flex-wrap items-center justify-between gap-3">
              <span className="text-[11px] text-[var(--faint)]">
                {noteDraft.length}/2000 · 仅管理员可见
              </span>
              <div className="flex gap-2">
                <button
                  type="button"
                  className="a-btn a-btn-sm"
                  disabled={noteSaving}
                  onClick={closeNoteEditor}
                >
                  取消
                </button>
                <button
                  type="button"
                  className="a-btn a-btn-sm a-btn-primary"
                  disabled={noteSaving}
                  onClick={saveNote}
                >
                  {noteSaving ? (
                    <Loader2 size={13} className="animate-spin" />
                  ) : (
                    <Pencil size={13} />
                  )}
                  {noteSaving ? "保存中…" : "保存备注"}
                </button>
              </div>
            </div>
          </div>
        )}
      </AdminModal>
    </div>
  );
}

function QuestionListRow({
  question,
  canEdit,
  onStarsChange,
  onEditNote,
  onPreview,
}: {
  question: AdminQuestionListItem;
  canEdit: boolean;
  onStarsChange: (questionId: string, stars: number | null) => Promise<void>;
  onEditNote: (question: AdminQuestionListItem) => void;
  onPreview: (questionId: string) => void;
}) {
  const [savingStars, setSavingStars] = useState(false);
  return (
    <tr>
      <td>
        <button
          type="button"
          className="block max-w-[520px] cursor-pointer text-left transition hover:text-[var(--primary)]"
          onClick={() => onPreview(question.question_id)}
        >
          <div className="line-clamp-2 text-[12.5px] leading-5">
            {shortStem(question.stem)}
          </div>
          <div className="mt-1 font-mono text-[9.5px] text-[var(--faint)]">
            {question.question_id}
          </div>
        </button>
      </td>
      <td>
        <div className="flex flex-wrap items-center gap-1.5">
          {(question.unit_ids || []).map((unitId) => (
            <span key={unitId} className="a-badge a-badge-primary">
              Unit {unitId}
            </span>
          ))}
          <span className="a-badge">
            {PAPER_TYPE_LABEL[question.paper_type || ""] ||
              question.paper_type ||
              "—"}
          </span>
          {question.year && (
            <span className="text-[10.5px] text-[var(--faint)]">
              {question.year}
            </span>
          )}
        </div>
        <div
          className="mt-1 max-w-[260px] truncate text-[11px] text-[var(--muted)]"
          title={question.paper_title || question.paper_id || ""}
        >
          {question.paper_chinese_title ||
            question.paper_title ||
            question.paper_id}
        </div>
      </td>
      <td>
        <span className="a-badge font-mono">
          {question.section} {question.number}
          {question.form ? ` · ${question.form}` : ""}
        </span>
      </td>
      <td className="font-mono text-[11.5px] text-[var(--muted)]">
        {question.option_count}
      </td>
      <td>
        <StarRating
          value={question.stars}
          size={14}
          label={`${question.section} ${question.number} 星级`}
          disabled={!canEdit || savingStars}
          onChange={
            canEdit
              ? (next) => {
                  setSavingStars(true);
                  onStarsChange(question.question_id, next).finally(() =>
                    setSavingStars(false),
                  );
                }
              : undefined
          }
        />
      </td>
      <td>
        {canEdit ? (
          <button
            type="button"
            className="block max-w-[220px] text-left"
            title={question.admin_note || "添加备注"}
            onClick={() => onEditNote(question)}
          >
            <span
              className={`line-clamp-2 text-[11.5px] leading-5 ${
                question.admin_note
                  ? "text-[var(--muted)]"
                  : "text-[var(--faint)]"
              }`}
            >
              {question.admin_note || "添加备注"}
            </span>
            {question.admin_note && (
              <span className="mt-1 inline-flex items-center gap-1 text-[10px] text-[var(--primary)]">
                <Pencil size={10} /> 编辑
              </span>
            )}
          </button>
        ) : question.admin_note ? (
          <span className="line-clamp-2 max-w-[220px] text-[11.5px] leading-5 text-[var(--muted)]">
            {question.admin_note}
          </span>
        ) : (
          <span className="text-[var(--faint)]">—</span>
        )}
      </td>
      <td className="text-right">
        <button
          type="button"
          className="a-btn a-btn-sm"
          onClick={() => onPreview(question.question_id)}
        >
          查看
        </button>
      </td>
    </tr>
  );
}
