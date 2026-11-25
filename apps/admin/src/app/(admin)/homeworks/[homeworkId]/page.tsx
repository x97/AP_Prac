"use client";

import {
  ArrowLeft,
  ChevronDown,
  ChevronUp,
  Copy,
  Loader2,
  Plus,
  Save,
  Trash2,
} from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { useAdmin, useAdminSubject } from "@/components/AdminShell";
import { QuestionPicker, type PickerQuestion } from "@/components/QuestionPicker";
import { QuestionPreview } from "@/components/QuestionPreview";
import { apiDelete, apiGet, apiPatch, apiPost } from "@/lib/api";
import type {
  ClassroomHomeworkDetail,
  StudyTaxonomy,
  StudyTaxonomyTopic,
} from "@/lib/types";

type QuestionRow = {
  question_id: string;
  stem: string;
  section: string;
  stars?: number | null;
  missing?: boolean;
};

export default function HomeworkEditorPage() {
  const params = useParams<{ homeworkId: string }>();
  const router = useRouter();
  const admin = useAdmin();
  const { subjectId } = useAdminSubject();
  const canEdit = Boolean(admin?.can_edit_content);
  const isNew = params.homeworkId === "new";

  const [title, setTitle] = useState("");
  const [note, setNote] = useState("");
  const [unit, setUnit] = useState("");
  const [topic, setTopic] = useState("");
  const [questions, setQuestions] = useState<QuestionRow[]>([]);
  const [taxonomy, setTaxonomy] = useState<StudyTaxonomy | null>(null);
  const [loading, setLoading] = useState(!isNew);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [previewId, setPreviewId] = useState<string | null>(null);
  const [original, setOriginal] = useState<ClassroomHomeworkDetail | null>(null);

  useEffect(() => {
    apiGet<StudyTaxonomy>(`/content/taxonomy?subject=${subjectId}`)
      .then(setTaxonomy)
      .catch((e: Error) => setError(e.message));
  }, [subjectId]);

  useEffect(() => {
    if (isNew) return;
    let alive = true;
    setLoading(true);
    apiGet<ClassroomHomeworkDetail>(
      `/homeworks/${params.homeworkId}?subject=${subjectId}`,
    )
      .then((value) => {
        if (!alive) return;
        setOriginal(value);
        setTitle(value.title);
        setNote(value.note || "");
        setUnit(value.unit_id || "");
        setTopic(value.topic_id || "");
        setQuestions(
          value.questions.map((question) => ({
            question_id: question.question_id,
            stem: question.missing ? "（题目已从题库移除）" : question.stem,
            section: question.section,
            stars: question.stars,
            missing: question.missing,
          })),
        );
      })
      .catch((e: Error) => alive && setError(e.message))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [isNew, params.homeworkId, subjectId]);

  const topicOptions: StudyTaxonomyTopic[] = useMemo(
    () =>
      taxonomy?.units.find((item) => item.unit_id === unit)?.topics ||
      taxonomy?.topics.filter((item) => !unit || item.unit_id === unit) ||
      [],
    [taxonomy, unit],
  );

  function setQuestionsFromIds(ids: string[], picked: PickerQuestion[]) {
    const current = new Map(questions.map((row) => [row.question_id, row]));
    setQuestions(
      ids.map((id) => {
        const existing = current.get(id);
        if (existing) return existing;
        const pickedRow = picked.find((row) => row.question_id === id);
        return {
          question_id: id,
          stem: pickedRow?.stem || id,
          section: "MCQ",
          stars: pickedRow?.stars,
        };
      }),
    );
  }

  function move(index: number, delta: number) {
    const target = index + delta;
    if (target < 0 || target >= questions.length) return;
    setQuestions((current) => {
      const next = [...current];
      [next[index], next[target]] = [next[target], next[index]];
      return next;
    });
  }

  async function save() {
    if (!canEdit) return;
    if (!title.trim()) {
      setError("请填写标题");
      return;
    }
    if (!unit || !topic) {
      setError("请选择 Unit 和章节");
      return;
    }
    if (questions.length === 0) {
      setError("至少加入一道题目");
      return;
    }
    if (questions.every((row) => row.missing)) {
      setError("题目都已从题库移除，请重新选择");
      return;
    }
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const body = {
        title: title.trim(),
        note,
        unit_id: unit,
        topic_id: topic,
        question_ids: questions
          .filter((row) => !row.missing)
          .map((row) => row.question_id),
      };
      if (isNew) {
        const created = await apiPost<ClassroomHomeworkDetail>(
          `/homeworks?subject=${subjectId}`,
          body,
        );
        router.replace(`/homeworks/${created.id}`);
        return;
      }
      const updated = await apiPatch<ClassroomHomeworkDetail>(
        `/homeworks/${params.homeworkId}?subject=${subjectId}`,
        body,
      );
      setOriginal(updated);
      setMessage("已保存");
      setQuestions(
        updated.questions.map((question) => ({
          question_id: question.question_id,
          stem: question.missing ? "（题目已从题库移除）" : question.stem,
          section: question.section,
          stars: question.stars,
          missing: question.missing,
        })),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "保存失败");
    } finally {
      setSaving(false);
    }
  }

  async function duplicate() {
    if (isNew) return;
    try {
      const copy = await apiPost<ClassroomHomeworkDetail>(
        `/homeworks/${params.homeworkId}/duplicate?subject=${subjectId}`,
      );
      router.push(`/homeworks/${copy.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "复制失败");
    }
  }

  async function removeHomework() {
    if (isNew) return;
    if (!window.confirm("删除这份课堂作业？已被学习计划引用时不能删除。")) return;
    try {
      await apiDelete(`/homeworks/${params.homeworkId}?subject=${subjectId}`);
      router.push("/homeworks");
    } catch (e) {
      setError(e instanceof Error ? e.message : "删除失败");
    }
  }

  if (loading) {
    return (
      <div className="grid place-items-center py-24">
        <Loader2 size={24} className="animate-spin text-[var(--primary)]" />
      </div>
    );
  }

  return (
    <div>
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <Link
            href="/homeworks"
            className="mb-2 inline-flex items-center gap-1 text-[11.5px] text-[var(--muted)] hover:text-[var(--primary)]"
          >
            <ArrowLeft size={13} /> 课堂作业
          </Link>
          <h1 className="text-[27px] font-semibold tracking-[-0.03em]">
            {isNew ? "新建课堂作业" : title || "课堂作业"}
          </h1>
          <p className="mt-1 text-[12.5px] text-[var(--muted)]">
            Unit/Chapter 与 CB 题库一致；先选章节，再从题库批量选择 MCQ。
          </p>
        </div>
        <div className="flex gap-2">
          {!isNew && (
            <button className="a-btn" onClick={duplicate} disabled={!canEdit}>
              <Copy size={14} /> 复制
            </button>
          )}
          {canEdit && (
            <button
              className="a-btn a-btn-primary"
              onClick={save}
              disabled={saving}
            >
              {saving ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <Save size={14} />
              )}
              {isNew ? "创建" : "保存"}
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="mb-3 rounded-xl border border-[#f6d5d2] bg-[var(--danger-soft)] px-3 py-2 text-[12px] text-[var(--danger)]">
          {error}
        </div>
      )}
      {message && (
        <div className="mb-3 rounded-xl border border-[#bfe8d1] bg-[var(--success-soft)] px-3 py-2 text-[12px] text-[var(--success)]">
          {message}
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_300px]">
        <div className="space-y-4">
          <div className="a-card p-5">
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="block sm:col-span-2">
                <span className="mb-1 block text-[11.5px] text-[var(--muted)]">
                  标题
                </span>
                <input
                  className="a-input"
                  value={title}
                  onChange={(event) => setTitle(event.target.value)}
                  placeholder="例如：Unit 3 3.2 课堂作业"
                  disabled={!canEdit}
                />
              </label>
              <label className="block">
                <span className="mb-1 block text-[11.5px] text-[var(--muted)]">
                  Unit
                </span>
                <select
                  className="a-input"
                  value={unit}
                  onChange={(event) => {
                    setUnit(event.target.value);
                    setTopic("");
                  }}
                  disabled={!canEdit}
                >
                  <option value="">选择 Unit</option>
                  {taxonomy?.units.map((item) => (
                    <option key={item.unit_id} value={item.unit_id}>
                      Unit {item.unit_id} · {item.title}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block">
                <span className="mb-1 block text-[11.5px] text-[var(--muted)]">
                  章节
                </span>
                <select
                  className="a-input"
                  value={topic}
                  onChange={(event) => {
                    setTopic(event.target.value);
                    const value = taxonomy?.topics.find(
                      (item) => item.topic_id === event.target.value,
                    );
                    if (value) setUnit(value.unit_id);
                  }}
                  disabled={!canEdit}
                >
                  <option value="">选择章节</option>
                  {topicOptions.map((item) => (
                    <option key={item.topic_id} value={item.topic_id}>
                      {item.code} · {item.title_zh || item.title_en}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block sm:col-span-2">
                <span className="mb-1 block text-[11.5px] text-[var(--muted)]">
                  备注
                </span>
                <textarea
                  className="a-input min-h-[90px]"
                  value={note}
                  onChange={(event) => setNote(event.target.value)}
                  placeholder="给学生看的说明，例如：先复习神经元结构"
                  disabled={!canEdit}
                />
              </label>
            </div>
          </div>

          <div className="a-card overflow-hidden">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--line)] px-5 py-3">
              <div className="text-[13px] font-semibold">
                题目 <span className="a-badge ml-1">{questions.length}</span>
              </div>
              <div className="flex gap-2">
                {canEdit && (
                  <button
                    className="a-btn a-btn-primary a-btn-sm"
                    onClick={() => setPickerOpen(true)}
                    disabled={!unit || !topic}
                    title={!unit || !topic ? "请先选择 Unit/章节" : undefined}
                  >
                    <Plus size={13} /> 从题库选择
                  </button>
                )}
              </div>
            </div>
            {questions.length === 0 ? (
              <div className="py-16 text-center text-[12px] text-[var(--faint)]">
                还没有题目。选择 Unit/章节后从题库批量加入。
              </div>
            ) : (
              <table className="a-table">
                <thead>
                  <tr>
                    <th className="w-10">#</th>
                    <th>题目</th>
                    <th className="w-24">题型</th>
                    <th className="w-40" />
                  </tr>
                </thead>
                <tbody>
                  {questions.map((question, index) => (
                    <tr key={question.question_id}>
                      <td className="font-mono text-[11px]">{index + 1}</td>
                      <td>
                        <button
                          className="block max-w-[620px] text-left text-[12.5px] leading-5 hover:text-[var(--primary)]"
                          onClick={() => setPreviewId(question.question_id)}
                          disabled={question.missing}
                        >
                          <span className="line-clamp-2">{question.stem}</span>
                          <span className="mt-0.5 block font-mono text-[9.5px] text-[var(--faint)]">
                            {question.question_id}
                          </span>
                        </button>
                      </td>
                      <td>
                        <span className="a-badge">{question.section}</span>
                      </td>
                      <td>
                        {canEdit && (
                          <div className="flex justify-end gap-1">
                            <button
                              className="a-btn a-btn-sm"
                              onClick={() => move(index, -1)}
                              disabled={index === 0}
                              title="上移"
                            >
                              <ChevronUp size={13} />
                            </button>
                            <button
                              className="a-btn a-btn-sm"
                              onClick={() => move(index, 1)}
                              disabled={index === questions.length - 1}
                              title="下移"
                            >
                              <ChevronDown size={13} />
                            </button>
                            <button
                              className="a-btn a-btn-sm"
                              onClick={() =>
                                setQuestions((current) =>
                                  current.filter(
                                    (row) =>
                                      row.question_id !== question.question_id,
                                  ),
                                )
                              }
                              title="移除"
                            >
                              <Trash2 size={13} />
                            </button>
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        <div className="space-y-4">
          <div className="a-card p-4 text-[12px] text-[var(--muted)]">
            <div className="font-semibold text-[var(--ink)]">保存后</div>
            <ul className="mt-2 list-disc space-y-1 pl-4">
              <li>可被多个学习计划引用</li>
              <li>修改题目会影响未开始的任务</li>
              <li>已开始的练习保留原题目</li>
            </ul>
          </div>
          {original && (original.used_in_plans ?? 0) > 0 && (
            <div className="rounded-xl border border-[#f3d9a8] bg-[var(--accent-soft)] p-4 text-[12px] text-[var(--accent)]">
              已被 {original.used_in_plans} 个学习计划使用
              {original.plan_titles?.length
                ? `：${original.plan_titles.join("、")}`
                : ""}
              。修改题目会影响这些计划中未开始的任务。
            </div>
          )}
          {!isNew && canEdit && (
            <button className="a-btn a-btn-danger w-full" onClick={removeHomework}>
              <Trash2 size={14} /> 删除课堂作业
            </button>
          )}
        </div>
      </div>

      <QuestionPicker
        open={pickerOpen}
        subjectId={subjectId}
        initialUnitId={unit}
        initialTopicId={topic}
        initialSelected={questions.map((row) => ({
          question_id: row.question_id,
          stem: row.stem,
          stars: row.stars,
        }))}
        onClose={() => setPickerOpen(false)}
        onConfirm={setQuestionsFromIds}
      />
      <QuestionPreview
        questionId={previewId}
        subjectId={subjectId}
        onClose={() => setPreviewId(null)}
      />
    </div>
  );
}
