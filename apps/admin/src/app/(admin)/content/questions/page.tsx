"use client";

import { ChevronLeft, ChevronRight, ListChecks, Loader2, Search } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { StarRating } from "@/components/StarRating";
import { useAdmin, useAdminSubject } from "@/components/AdminShell";
import { apiGet, apiPatch } from "@/lib/api";
import type {
  AdminQuestionListItem,
  AdminQuestionListResponse,
  AdminQuestionUnit,
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

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError(null);
    const params = new URLSearchParams({
      subject: subjectId,
      source,
      section,
      limit: String(LIMIT),
      offset: String(offset),
    });
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

  return (
    <div>
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="text-[11px] uppercase tracking-[0.14em] text-[var(--faint)]">
            Content
          </div>
          <h1 className="mt-1 text-[27px] font-semibold tracking-[-0.03em]">题目</h1>
          <p className="mt-1 text-[12.5px] text-[var(--muted)]">
            当前内容分类：{subject?.name || subjectId}。按单元、真题、模拟题和题型筛选所有题目，可直接修改星级。
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
          <table className="a-table min-w-[1100px]">
            <thead>
              <tr>
                <th>题目</th>
                <th>来源</th>
                <th>题型</th>
                <th>选项</th>
                <th>星级</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={6} className="py-20 text-center">
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
                    subjectId={subjectId}
                    canEdit={canEdit}
                    onStarsChange={saveStars}
                  />
                ))
              )}
              {!loading && questions.length === 0 && (
                <tr>
                  <td
                    colSpan={6}
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
    </div>
  );
}

function QuestionListRow({
  question,
  subjectId,
  canEdit,
  onStarsChange,
}: {
  question: AdminQuestionListItem;
  subjectId: string;
  canEdit: boolean;
  onStarsChange: (questionId: string, stars: number | null) => Promise<void>;
}) {
  const [savingStars, setSavingStars] = useState(false);
  const detailHref = `/content/questions/${question.question_id}?subject=${encodeURIComponent(subjectId)}`;
  return (
    <tr>
      <td>
        <Link href={detailHref} className="block max-w-[520px]">
          <div className="line-clamp-2 text-[12.5px] leading-5">
            {shortStem(question.stem)}
          </div>
          <div className="mt-1 font-mono text-[9.5px] text-[var(--faint)]">
            {question.question_id}
          </div>
        </Link>
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
      <td className="text-right">
        <Link href={detailHref} className="a-btn a-btn-sm">
          查看
        </Link>
      </td>
    </tr>
  );
}
