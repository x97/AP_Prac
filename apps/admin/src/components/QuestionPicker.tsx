"use client";

import {
  ChevronLeft,
  ChevronRight,
  Loader2,
  Search,
  Trash2,
  X,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { AdminModal } from "@/components/AdminModal";
import { QuestionPreview } from "@/components/QuestionPreview";
import { StarRating } from "@/components/StarRating";
import { apiGet } from "@/lib/api";
import type {
  AdminQuestionListItem,
  AdminQuestionListResponse,
  Paper,
  StudyTaxonomy,
} from "@/lib/types";

const LIMIT = 50;
const MAX_SELECTED = 300;

const SOURCES = [
  { value: "all", label: "全部来源" },
  { value: "unit", label: "单元练习" },
  { value: "real_exam", label: "真题" },
  { value: "mock_exam", label: "模拟题" },
  { value: "unit_practice", label: "章节练习" },
  { value: "self_bank", label: "自研题" },
];

export type PickerQuestion = {
  question_id: string;
  stem: string;
  stars?: number | null;
};

function shortStem(value: string, length = 120) {
  return value.length > length ? `${value.slice(0, length)}…` : value;
}

export function QuestionPicker({
  open,
  subjectId,
  initialUnitId,
  initialTopicId,
  initialSelected = [],
  onClose,
  onConfirm,
}: {
  open: boolean;
  subjectId: string;
  initialUnitId?: string | null;
  initialTopicId?: string | null;
  initialSelected?: PickerQuestion[];
  onClose: () => void;
  onConfirm: (ids: string[], questions: PickerQuestion[]) => void;
}) {
  const [taxonomy, setTaxonomy] = useState<StudyTaxonomy | null>(null);
  const [papers, setPapers] = useState<Paper[]>([]);
  const [source, setSource] = useState("all");
  const [paperId, setPaperId] = useState("");
  const [unit, setUnit] = useState(initialUnitId || "");
  const [topic, setTopic] = useState(initialTopicId || "");
  const [section, setSection] = useState("MCQ");
  const [query, setQuery] = useState("");
  const [appliedQuery, setAppliedQuery] = useState("");
  const [questions, setQuestions] = useState<AdminQuestionListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<PickerQuestion[]>([]);
  const [previewId, setPreviewId] = useState<string | null>(null);
  const [selectingAll, setSelectingAll] = useState(false);
  const searchRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!open) return;
    setUnit(initialUnitId || "");
    setTopic(initialTopicId || "");
    setSelected(initialSelected);
    setQuery("");
    setAppliedQuery("");
    setSource("all");
    setPaperId("");
    setSection("MCQ");
    setOffset(0);
    setPreviewId(null);
    setTimeout(() => searchRef.current?.focus(), 40);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, initialUnitId, initialTopicId]);

  useEffect(() => {
    if (!open) return;
    apiGet<StudyTaxonomy>(`/content/taxonomy?subject=${encodeURIComponent(subjectId)}`)
      .then(setTaxonomy)
      .catch((e: Error) => setError(e.message));
    apiGet<{ papers: Paper[] }>(
      `/content/papers?subject=${encodeURIComponent(subjectId)}`,
    )
      .then((value) => setPapers(value.papers || []))
      .catch(() => setPapers([]));
  }, [open, subjectId]);

  useEffect(() => {
    if (!open) return;
    const timer = window.setTimeout(() => {
      setAppliedQuery(query.trim());
      setOffset(0);
    }, 300);
    return () => window.clearTimeout(timer);
  }, [query, open]);

  const appliedUnit = unit;
  const appliedTopic = topic;

  useEffect(() => {
    if (!open) return;
    let alive = true;
    setLoading(true);
    setError(null);
    const queryParams = new URLSearchParams({
      subject: subjectId,
      source,
      section,
      limit: String(LIMIT),
      offset: String(offset),
    });
    if (appliedUnit) queryParams.set("unit", appliedUnit);
    if (appliedTopic) queryParams.set("topic", appliedTopic);
    if (paperId) queryParams.set("paper_id", paperId);
    if (appliedQuery) queryParams.set("q", appliedQuery);
    apiGet<AdminQuestionListResponse>(`/content/questions?${queryParams.toString()}`)
      .then((value) => {
        if (!alive) return;
        setQuestions(value.questions);
        setTotal(value.total);
      })
      .catch((e: Error) => alive && setError(e.message))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, subjectId, source, section, appliedUnit, appliedTopic, paperId, appliedQuery, offset]);

  const selectedIds = new Set(selected.map((item) => item.question_id));

  function toggle(question: AdminQuestionListItem) {
    setSelected((current) => {
      if (current.some((item) => item.question_id === question.question_id)) {
        return current.filter((item) => item.question_id !== question.question_id);
      }
      if (current.length >= MAX_SELECTED) return current;
      return [
        ...current,
        {
          question_id: question.question_id,
          stem: question.stem,
          stars: question.stars,
        },
      ];
    });
  }

  async function selectAllFiltered() {
    setSelectingAll(true);
    setError(null);
    try {
      const value = new URLSearchParams({
        subject: subjectId,
        source,
        section,
        max: "2000",
      });
      if (appliedUnit) value.set("unit", appliedUnit);
      if (appliedTopic) value.set("topic", appliedTopic);
      if (paperId) value.set("paper_id", paperId);
      if (appliedQuery) value.set("q", appliedQuery);
      const result = await apiGet<{ question_ids: string[]; truncated: boolean }>(
        `/content/questions/ids?${value.toString()}`,
      );
      const remaining = MAX_SELECTED - selected.length;
      const ids = result.question_ids.slice(0, Math.max(0, remaining));
      const visible = new Map(
        questions.map((question) => [question.question_id, question]),
      );
      setSelected((current) => {
        const known = new Set(current.map((item) => item.question_id));
        return [
          ...current,
          ...ids
            .filter((id) => !known.has(id))
            .map((id) => ({
              question_id: id,
              stem: visible.get(id)?.stem || id,
              stars: visible.get(id)?.stars,
            })),
        ];
      });
      if (result.truncated || ids.length < result.question_ids.length) {
        setError(`已选最多 ${MAX_SELECTED} 道，超出部分未加入`);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "全选失败");
    } finally {
      setSelectingAll(false);
    }
  }

  function confirm() {
    onConfirm(
      selected.map((item) => item.question_id),
      selected,
    );
    onClose();
  }

  const topicOptions =
    taxonomy?.units.find((item) => item.unit_id === unit)?.topics ||
    taxonomy?.topics.filter((item) => !unit || item.unit_id === unit) ||
    [];

  return (
    <>
      <AdminModal open={open} onClose={onClose} title="从题库选择题目" wide>
        <div className="space-y-3">
          <div className="flex flex-wrap gap-2">
            <select
              className="a-input w-auto"
              value={source}
              onChange={(event) => {
                setSource(event.target.value);
                setOffset(0);
              }}
            >
              {SOURCES.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
            <select
              className="a-input w-auto"
              value={unit}
              onChange={(event) => {
                setUnit(event.target.value);
                setTopic("");
                setOffset(0);
              }}
            >
              <option value="">全部单元</option>
              {taxonomy?.units.map((item) => (
                <option key={item.unit_id} value={item.unit_id}>
                  Unit {item.unit_id}
                </option>
              ))}
            </select>
            <select
              className="a-input w-auto max-w-[240px]"
              value={topic}
              onChange={(event) => {
                setTopic(event.target.value);
                setOffset(0);
              }}
            >
              <option value="">全部章节</option>
              {topicOptions.map((item) => (
                <option key={item.topic_id} value={item.topic_id}>
                  {item.code} {item.title_zh || item.title_en}
                </option>
              ))}
            </select>
            <select
              className="a-input w-auto max-w-[240px]"
              value={paperId}
              onChange={(event) => {
                setPaperId(event.target.value);
                setOffset(0);
              }}
            >
              <option value="">全部试卷</option>
              {papers.map((paper) => (
                <option key={paper.paper_id} value={paper.paper_id}>
                  {paper.chinese_title || paper.title || paper.paper_id}
                </option>
              ))}
            </select>
            <select
              className="a-input w-auto"
              value={section}
              onChange={(event) => {
                setSection(event.target.value);
                setOffset(0);
              }}
            >
              <option value="MCQ">选择题 MCQ</option>
            </select>
            <div className="relative min-w-[220px] flex-1">
              <Search
                size={15}
                className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--faint)]"
              />
              <input
                ref={searchRef}
                className="a-input pl-9"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="搜索题干或题目 ID"
              />
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-2 text-[11.5px] text-[var(--muted)]">
            <span>
              筛选结果 {total} 道 · 已选 {selected.length} / {MAX_SELECTED}
            </span>
            <div className="flex gap-2">
              <button
                className="a-btn a-btn-sm"
                type="button"
                onClick={selectAllFiltered}
                disabled={selectingAll || loading || total === 0}
              >
                {selectingAll ? <Loader2 size={13} className="animate-spin" /> : null}
                全选当前筛选
              </button>
              <button
                className="a-btn a-btn-sm"
                type="button"
                onClick={() => setSelected([])}
                disabled={selected.length === 0}
              >
                <Trash2 size={13} /> 清空
              </button>
            </div>
          </div>

          {error && (
            <div className="rounded-xl border border-[#f6d5d2] bg-[var(--danger-soft)] px-3 py-2 text-[12px] text-[var(--danger)]">
              {error}
            </div>
          )}

          <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_280px]">
            <div className="a-card min-h-[360px] overflow-hidden">
              <div className="max-h-[430px] overflow-y-auto">
                <table className="a-table text-[12px]">
                  <thead>
                    <tr>
                      <th className="w-10" />
                      <th>题目</th>
                      <th>来源 / 单元</th>
                      <th>星级</th>
                    </tr>
                  </thead>
                  <tbody>
                    {loading ? (
                      <tr>
                        <td colSpan={4} className="py-20 text-center">
                          <Loader2
                            size={20}
                            className="mx-auto animate-spin text-[var(--primary)]"
                          />
                        </td>
                      </tr>
                    ) : questions.length === 0 ? (
                      <tr>
                        <td colSpan={4} className="py-16 text-center text-[var(--faint)]">
                          没有匹配的题目
                        </td>
                      </tr>
                    ) : (
                      questions.map((question) => (
                        <tr key={question.question_id}>
                          <td>
                            <input
                              type="checkbox"
                              className="h-4 w-4 accent-[var(--primary)]"
                              checked={selectedIds.has(question.question_id)}
                              onChange={() => toggle(question)}
                            />
                          </td>
                          <td>
                            <button
                              type="button"
                              className="block max-w-[520px] text-left hover:text-[var(--primary)]"
                              onClick={() => setPreviewId(question.question_id)}
                            >
                              <div className="line-clamp-2 leading-5">
                                {shortStem(question.stem)}
                              </div>
                              <div className="mt-1 font-mono text-[9.5px] text-[var(--faint)]">
                                {question.question_id}
                              </div>
                            </button>
                          </td>
                          <td>
                            <div className="flex flex-wrap gap-1">
                              <span className="a-badge">
                                {question.paper_type || "—"}
                              </span>
                              {(question.unit_ids || []).map((unitId) => (
                                <span key={unitId} className="a-badge a-badge-primary">
                                  U{unitId}
                                </span>
                              ))}
                            </div>
                          </td>
                          <td>
                            <StarRating
                              value={question.stars}
                              size={13}
                              label="题目星级"
                              disabled
                            />
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
              <div className="flex items-center justify-between border-t border-[var(--line)] px-4 py-2 text-[11.5px] text-[var(--muted)]">
                <span>
                  {offset + 1}–{Math.min(offset + LIMIT, total)} / {total}
                </span>
                <div className="flex gap-2">
                  <button
                    className="a-btn a-btn-sm"
                    disabled={offset === 0 || loading}
                    onClick={() => setOffset(Math.max(0, offset - LIMIT))}
                  >
                    <ChevronLeft size={13} />
                  </button>
                  <button
                    className="a-btn a-btn-sm"
                    disabled={offset + LIMIT >= total || loading}
                    onClick={() => setOffset(offset + LIMIT)}
                  >
                    <ChevronRight size={13} />
                  </button>
                </div>
              </div>
            </div>

            <div className="a-card flex max-h-[500px] min-h-[240px] flex-col p-3">
              <div className="mb-2 flex items-center justify-between text-[12px] font-semibold">
                已选题目
                <span className="a-badge">{selected.length}</span>
              </div>
              <div className="flex-1 space-y-2 overflow-y-auto">
                {selected.length === 0 ? (
                  <div className="py-10 text-center text-[12px] text-[var(--faint)]">
                    从左侧勾选题目
                  </div>
                ) : (
                  selected.map((item, index) => (
                    <div
                      key={item.question_id}
                      className="rounded-lg border border-[var(--line)] p-2"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="line-clamp-2 text-[11.5px] leading-5">
                          {index + 1}. {shortStem(item.stem, 70)}
                        </div>
                        <button
                          type="button"
                          className="shrink-0 text-[var(--faint)] hover:text-[var(--danger)]"
                          onClick={() =>
                            setSelected((current) =>
                              current.filter(
                                (row) => row.question_id !== item.question_id,
                              ),
                            )
                          }
                          aria-label="移除题目"
                        >
                          <X size={13} />
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          <div className="flex justify-end gap-2 border-t border-[var(--line)] pt-3">
            <button className="a-btn" type="button" onClick={onClose}>
              取消
            </button>
            <button
              className="a-btn a-btn-primary"
              type="button"
              onClick={confirm}
              disabled={selected.length === 0}
            >
              加入作业（{selected.length}）
            </button>
          </div>
        </div>
      </AdminModal>
      <QuestionPreview
        questionId={previewId}
        subjectId={subjectId}
        onClose={() => setPreviewId(null)}
      />
    </>
  );
}
