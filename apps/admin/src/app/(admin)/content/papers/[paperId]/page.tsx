"use client";

import { ArrowLeft, Loader2, Pencil, Plus, Sparkles } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { apiGet, apiPatch, apiPost } from "@/lib/api";
import { AdminModal } from "@/components/AdminModal";
import { StarRating } from "@/components/StarRating";
import { useAdmin, useAdminSubject } from "@/components/AdminShell";
import type { PaperDetail, QuestionDetail, QuestionSummary } from "@/lib/types";

const PAPER_TYPE_LABEL: Record<string, string> = {
  real_exam: "真题",
  mock_exam: "模拟题",
  unit_practice: "单元练习",
  practice_bundle: "练习包",
  bundle: "题包",
};

function shortStem(value: string, length = 180) {
  return value.length > length ? `${value.slice(0, length)}…` : value;
}

type NewOption = { label: string; content: string; is_correct: boolean };

const DEFAULT_OPTIONS: NewOption[] = ["A", "B", "C", "D"].map((label) => ({
  label,
  content: "",
  is_correct: label === "A",
}));

export default function PaperDetailPage() {
  const params = useParams<{ paperId: string }>();
  const router = useRouter();
  const admin = useAdmin();
  const { subjectId, subject } = useAdminSubject();
  const canEdit = Boolean(admin?.can_edit_content);
  const [paper, setPaper] = useState<PaperDetail | null>(null);
  const [section, setSection] = useState<"all" | "MCQ" | "FRQ">("all");
  const [error, setError] = useState<string | null>(null);
  const [editOpen, setEditOpen] = useState(false);
  const [edit, setEdit] = useState({ title: "", chinese_title: "", year: "", paper_type: "" });
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [starError, setStarError] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [createBusy, setCreateBusy] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [newQuestion, setNewQuestion] = useState({
    stem: "",
    context: "",
    options: DEFAULT_OPTIONS,
  });

  useEffect(() => {
    let alive = true;
    setError(null);
    apiGet<PaperDetail>(
      `/content/papers/${params.paperId}?subject=${encodeURIComponent(subjectId)}`,
    )
      .then((value) => {
        if (!alive) return;
        setPaper(value);
        setEdit({
          title: value.title || "",
          chinese_title: value.chinese_title || "",
          year: String(value.year),
          paper_type: value.paper_type,
        });
      })
      .catch((e: Error) => alive && setError(e.message));
    return () => {
      alive = false;
    };
  }, [params.paperId, subjectId]);

  if (error) {
    return (
      <div>
        <Link href="/content/papers" className="a-btn a-btn-sm mb-4">
          <ArrowLeft size={14} /> 返回试卷
        </Link>
        <div className="a-card p-5 text-[13px] text-[var(--danger)]">{error}</div>
      </div>
    );
  }

  if (!paper) {
    return (
      <div className="grid place-items-center py-24">
        <Loader2 size={24} className="animate-spin text-[var(--primary)]" />
      </div>
    );
  }

  async function createQuestion(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCreateBusy(true);
    setCreateError(null);
    try {
      const created = await apiPost<QuestionDetail>("/content/questions", {
        subject_id: subjectId,
        paper_id: paper?.paper_id,
        section: "MCQ",
        stem: newQuestion.stem,
        context: newQuestion.context,
        answer_source: "admin",
        answer_confidence: "admin",
        options: newQuestion.options.map((option) => ({
          label: option.label,
          content: option.content,
          is_correct: option.is_correct,
          explanation: null,
          ai_explanation: null,
        })),
      });
      router.push(`/content/questions/${created.question_id}`);
    } catch (e) {
      setCreateError(e instanceof Error ? e.message : "创建题目失败");
    } finally {
      setCreateBusy(false);
    }
  }

  function updateNewOption(index: number, patch: Partial<NewOption>) {
    setNewQuestion((prev) => ({
      ...prev,
      options: prev.options.map((option, optionIndex) =>
        optionIndex === index ? { ...option, ...patch } : option,
      ),
    }));
  }

  function setNewCorrect(index: number) {
    setNewQuestion((prev) => ({
      ...prev,
      options: prev.options.map((option, optionIndex) => ({
        ...option,
        is_correct: optionIndex === index,
      })),
    }));
  }

  async function savePaper(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setSaveError(null);
    try {
      await apiPatch(
        `/content/papers/${params.paperId}?subject=${encodeURIComponent(subjectId)}`,
        {
        title: edit.title,
        chinese_title: edit.chinese_title,
          year: Number(edit.year),
          paper_type: edit.paper_type,
        },
      );
      const refreshed = await apiGet<PaperDetail>(
        `/content/papers/${params.paperId}?subject=${encodeURIComponent(subjectId)}`,
      );
      setPaper(refreshed);
      setEditOpen(false);
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : "保存失败");
    } finally {
      setSaving(false);
    }
  }

  async function saveStars(questionId: string, stars: number | null) {
    const previous =
      paper?.questions.find((item) => item.question_id === questionId)?.stars ?? null;
    setStarError(null);
    setPaper((prev) =>
      prev
        ? {
            ...prev,
            questions: prev.questions.map((item) =>
              item.question_id === questionId ? { ...item, stars } : item,
            ),
          }
        : prev,
    );
    try {
      await apiPatch(
        `/content/questions/${questionId}/stars?subject=${encodeURIComponent(subjectId)}`,
        { stars },
      );
    } catch (e) {
      setPaper((prev) =>
        prev
          ? {
              ...prev,
              questions: prev.questions.map((item) =>
                item.question_id === questionId
                  ? { ...item, stars: previous }
                  : item,
              ),
            }
          : prev,
      );
      setStarError(e instanceof Error ? e.message : "星级保存失败");
    }
  }

  const questions =
    section === "all"
      ? paper.questions
      : paper.questions.filter((item) => item.section === section);
  const isBundle = ["practice_bundle", "bundle"].includes(paper.paper_type);

  return (
    <div>
      <Link href="/content/papers" className="a-btn a-btn-sm mb-4">
        <ArrowLeft size={14} /> 返回试卷
      </Link>

      <div className="mb-5">
        <div className="text-[11px] uppercase tracking-[0.14em] text-[var(--faint)]">
          {subject?.name || subjectId} · {paper.year} ·{" "}
          {PAPER_TYPE_LABEL[paper.paper_type] || paper.paper_type}
        </div>
        <h1 className="mt-1 max-w-4xl text-[26px] font-semibold leading-8 tracking-[-0.03em]">
          {paper.title || paper.paper_id}
        </h1>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <span className="font-mono text-[11.5px] text-[var(--faint)]">{paper.paper_id}</span>
          {paper.admin_origin && (
            <span className="a-badge a-badge-warn">
              <Sparkles size={12} /> {paper.admin_origin === "admin_created" ? "Admin 新建" : "Admin 修改"}
            </span>
          )}
          {canEdit ? (
            <>
              <button className="a-btn a-btn-sm" onClick={() => setEditOpen(true)}>
                <Pencil size={13} /> 编辑试卷
              </button>
              {!isBundle && (
                <button className="a-btn a-btn-sm a-btn-primary" onClick={() => setCreateOpen(true)}>
                  <Plus size={13} /> 新建题目
                </button>
              )}
            </>
          ) : (
            <span className="a-badge">只读</span>
          )}
        </div>
      </div>

      {isBundle && (
        <div className="mb-4 rounded-xl border border-[#f4dfc4] bg-[var(--accent-soft)] px-4 py-3 text-[12px] leading-5 text-[var(--accent)]">
          这是练习包（虚拟试卷）：{paper.questions.length} 道题通过 paper_question_map 来自源试卷。
          {paper.practice && (
            <> 学生 Unit 练习实际可用 {paper.practice.usable} 道，
              {paper.practice.excluded > 0 ? `另有 ${paper.practice.excluded} 道因内容排除未进入练习。` : ""}
            </>
          )}{" "}
          学生端通过 Unit 练习 Topic 使用，不作为整卷考试；题目请到源试卷维护。
        </div>
      )}

      <AdminModal
        open={editOpen}
        onClose={() => setEditOpen(false)}
        title="编辑试卷"
      >
        <form className="space-y-3" onSubmit={savePaper}>
          <label className="block text-[12px] font-medium">
            英文标题
            <input
              className="a-input mt-1.5"
              value={edit.title}
              onChange={(event) => setEdit((prev) => ({ ...prev, title: event.target.value }))}
              maxLength={500}
            />
          </label>
          <label className="block text-[12px] font-medium">
            中文标题
            <input
              className="a-input mt-1.5"
              value={edit.chinese_title}
              onChange={(event) =>
                setEdit((prev) => ({ ...prev, chinese_title: event.target.value }))
              }
              maxLength={500}
            />
          </label>
          <div className="grid grid-cols-2 gap-3">
            <label className="block text-[12px] font-medium">
              年份
              <input
                className="a-input mt-1.5"
                type="number"
                min={1990}
                max={2100}
                value={edit.year}
                onChange={(event) => setEdit((prev) => ({ ...prev, year: event.target.value }))}
                required
              />
            </label>
            <label className="block text-[12px] font-medium">
              类型
              <select
                className="a-input mt-1.5"
                value={edit.paper_type}
                disabled={isBundle}
                onChange={(event) =>
                  setEdit((prev) => ({ ...prev, paper_type: event.target.value }))
                }
              >
                <option value="real_exam">真题 real_exam</option>
                <option value="mock_exam">模拟题 mock_exam</option>
                <option value="unit_practice">单元练习 unit_practice</option>
                <option value="practice_bundle">练习包 practice_bundle</option>
                <option value="bundle">题包 bundle</option>
              </select>
            </label>
          </div>
          {isBundle && (
            <p className="text-[11px] leading-5 text-[var(--muted)]">
              练习包通过 paper_question_map 组织源试卷题目，类型不可改为普通试卷。
            </p>
          )}
          {saveError && (
            <div className="rounded-xl border border-[#f6d5d2] bg-[var(--danger-soft)] px-3 py-2 text-[12px] text-[var(--danger)]">
              {saveError}
            </div>
          )}
          <div className="flex justify-end gap-2 pt-1">
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
        title="新建题目（MCQ）"
        wide
      >
        <form className="space-y-3" onSubmit={createQuestion}>
          <div className="rounded-xl border border-[#f4dfc4] bg-[var(--accent-soft)] px-3 py-2 text-[11.5px] leading-5 text-[var(--accent)]">
            当前科目：{subject?.name || subjectId}。新题会直接进入当前试卷，
            学生端题数同步增加，并标记为 Admin 新建；本地同步遇到同一内容时以 Admin 内容为准。
          </div>
          <label className="block text-[12px] font-medium">
            题干
            <textarea
              className="a-input mt-1.5 min-h-[120px] resize-y leading-6"
              value={newQuestion.stem}
              onChange={(event) => setNewQuestion((prev) => ({ ...prev, stem: event.target.value }))}
              required
            />
          </label>
          <label className="block text-[12px] font-medium">
            Context / 材料（可选）
            <textarea
              className="a-input mt-1.5 min-h-[80px] resize-y leading-5"
              value={newQuestion.context}
              onChange={(event) => setNewQuestion((prev) => ({ ...prev, context: event.target.value }))}
            />
          </label>
          <div className="space-y-2">
            {newQuestion.options.map((option, index) => (
              <div key={option.label} className="rounded-xl border border-[var(--line)] p-3">
                <div className="flex items-center gap-3">
                  <label className="flex items-center gap-1.5 text-[11.5px] font-medium">
                    <input
                      type="radio"
                      name="new-correct"
                      checked={option.is_correct}
                      onChange={() => setNewCorrect(index)}
                    />
                    正确项
                  </label>
                  <span className="font-mono text-[11px] text-[var(--faint)]">{option.label}</span>
                </div>
                <textarea
                  className="a-input mt-2 min-h-[55px] resize-y leading-5"
                  value={option.content}
                  onChange={(event) => updateNewOption(index, { content: event.target.value })}
                  placeholder={`选项 ${option.label}`}
                  required
                />
              </div>
            ))}
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
              创建题目
            </button>
          </div>
        </form>
      </AdminModal>

      <div className="mb-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {[
          ["题目总数", paper.questions.length],
          ["MCQ", paper.questions.filter((item) => item.section === "MCQ").length],
          ["FRQ", paper.questions.filter((item) => item.section === "FRQ").length],
          ["考试时长", `${paper.config?.mcq_minutes ?? "—"} / ${paper.config?.frq_minutes ?? "—"} 分钟`],
        ].map(([label, value]) => (
          <div key={String(label)} className="a-card p-4">
            <div className="text-[11.5px] text-[var(--muted)]">{label}</div>
            <div className="mt-1.5 font-mono text-[19px] font-semibold">{value}</div>
          </div>
        ))}
      </div>

      {paper.config?.frq_rubric_complete === 0 && (
        <div className="mb-4 rounded-xl border border-[#f4dfc4] bg-[var(--accent-soft)] px-4 py-3 text-[12px] text-[var(--accent)]">
          这套卷的 FRQ 评分标准不完整：{paper.config.notes || "请发布前检查。"}
        </div>
      )}

      {starError && (
        <div className="mb-4 rounded-xl border border-[#f6d5d2] bg-[var(--danger-soft)] px-4 py-3 text-[12px] text-[var(--danger)]">
          星级保存失败：{starError}
        </div>
      )}

      <div className="a-card overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--line)] px-5 py-4">
          <h2 className="text-[15px] font-semibold">题目列表</h2>
          <div className="flex gap-2">
            {(["all", "MCQ", "FRQ"] as const).map((value) => (
              <button
                key={value}
                className={section === value ? "a-btn a-btn-sm a-btn-primary" : "a-btn a-btn-sm"}
                onClick={() => setSection(value)}
              >
                {value === "all" ? "全部" : value}
              </button>
            ))}
          </div>
        </div>
        <div className="divide-y divide-[var(--line)]">
          {questions.map((question) => (
            <QuestionRow
              key={question.question_id}
              question={question}
              subjectId={subjectId}
              canEdit={canEdit}
              onStarsChange={saveStars}
            />
          ))}
          {questions.length === 0 && (
            <div className="py-16 text-center text-[12px] text-[var(--faint)]">暂无题目</div>
          )}
        </div>
      </div>
    </div>
  );
}

function QuestionRow({
  question,
  subjectId,
  canEdit,
  onStarsChange,
}: {
  question: QuestionSummary;
  subjectId: string;
  canEdit: boolean;
  onStarsChange: (questionId: string, stars: number | null) => Promise<void>;
}) {
  const [savingStars, setSavingStars] = useState(false);
  return (
    <div className="flex items-start gap-3 px-5 py-4 transition hover:bg-[var(--surface-2)]">
      <Link
        href={`/content/questions/${question.question_id}?subject=${encodeURIComponent(subjectId)}`}
        className="flex min-w-0 flex-1 items-start gap-3"
      >
        <span className="a-badge shrink-0 font-mono">
          {question.section} {question.number}
        </span>
        <div className="min-w-0 flex-1">
          <div className="whitespace-pre-wrap text-[13px] leading-6">
            {shortStem(question.stem)}
          </div>
          <div className="mt-1.5 flex flex-wrap gap-2 text-[10.5px] text-[var(--faint)]">
            <span>{question.option_count} 个选项</span>
            <span>·</span>
            <span>{question.correct_count} 个正确项</span>
            {question.source_paper_id && (
            <><span>·</span><span>来自 {question.source_paper_id}</span></>
          )}
          {question.answer_source && <><span>·</span><span>{question.answer_source}</span></>}
          </div>
        </div>
      </Link>
      <div className="shrink-0 pt-0.5">
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
      </div>
    </div>
  );
}
