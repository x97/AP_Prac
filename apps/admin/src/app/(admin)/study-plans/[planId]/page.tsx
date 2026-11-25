"use client";

import {
  ArrowLeft,
  CalendarRange,
  ChevronDown,
  ChevronUp,
  Loader2,
  Plus,
  Save,
  Trash2,
  UserPlus,
} from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { useAdmin, useAdminSubject } from "@/components/AdminShell";
import { AdminModal } from "@/components/AdminModal";
import { AssignPlanModal } from "@/components/AssignPlanModal";
import { HomeworkPicker } from "@/components/HomeworkPicker";
import { apiDelete, apiGet, apiPatch, apiPost, apiPut } from "@/lib/api";
import type {
  ClassroomHomework,
  StudyAssignment,
  StudyAssignmentDetail,
  StudyAssignmentList,
  StudyPlanDetail,
} from "@/lib/types";

type EditableItem = {
  key: string;
  id?: string;
  homework_id: string;
  title: string;
  homework_title: string;
  unit_id?: string | null;
  topic_code?: string | null;
  question_count?: number;
};

const COLORS = [
  ["primary", "经典蓝"],
  ["accent", "琥珀"],
  ["success", "森林绿"],
  ["violet", "紫罗兰"],
  ["cyan", "青碧"],
];

export default function StudyPlanEditorPage() {
  const params = useParams<{ planId: string }>();
  const router = useRouter();
  const admin = useAdmin();
  const { subjectId } = useAdminSubject();
  const canEdit = Boolean(admin?.can_edit_content);
  const planId = params.planId;

  const [plan, setPlan] = useState<StudyPlanDetail | null>(null);
  const [title, setTitle] = useState("");
  const [note, setNote] = useState("");
  const [category, setCategory] = useState("");
  const [color, setColor] = useState("primary");
  const [items, setItems] = useState<EditableItem[]>([]);
  const [assignments, setAssignments] = useState<StudyAssignment[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [homeworkPickerOpen, setHomeworkPickerOpen] = useState(false);
  const [assignOpen, setAssignOpen] = useState(false);
  const [progressId, setProgressId] = useState<string | null>(null);
  const [progress, setProgress] = useState<StudyAssignmentDetail | null>(null);
  const [progressLoading, setProgressLoading] = useState(false);

  function load() {
    setLoading(true);
    Promise.all([
      apiGet<StudyPlanDetail>(`/study-plans/${planId}?subject=${subjectId}`),
      apiGet<StudyAssignmentList>(
        `/study-plan-assignments?plan_id=${planId}&limit=100`,
      ),
    ])
      .then(([planValue, assignmentValue]) => {
        setPlan(planValue);
        setTitle(planValue.title);
        setNote(planValue.note || "");
        setCategory(planValue.category || "");
        setColor(planValue.color || "primary");
        setItems(
          planValue.items.map((item) => ({
            key: item.id,
            id: item.id,
            homework_id: item.homework_id,
            title: item.title,
            homework_title: item.homework_title,
            question_count: item.question_count,
          })),
        );
        setAssignments(assignmentValue.assignments);
        setError(null);
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }

  useEffect(load, [planId, subjectId]);

  async function saveMeta() {
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      await apiPatch(`/study-plans/${planId}?subject=${subjectId}`, {
        title: title.trim(),
        note,
        category: category || null,
        color,
      });
      setMessage("计划信息已保存");
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "保存失败");
    } finally {
      setSaving(false);
    }
  }

  async function saveItems() {
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      await apiPut(`/study-plans/${planId}/items?subject=${subjectId}`, {
        items: items.map((item) => ({
          homework_id: item.homework_id,
          title: item.title,
        })),
      });
      setMessage("学习项已保存");
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "保存学习项失败");
    } finally {
      setSaving(false);
    }
  }

  function addHomeworks(homeworks: ClassroomHomework[]) {
    setItems((current) => [
      ...current,
      ...homeworks.map((homework) => ({
        key: `new-${homework.id}`,
        homework_id: homework.id,
        title: homework.title,
        homework_title: homework.title,
        unit_id: homework.unit_id,
        topic_code: homework.topic_code,
        question_count: homework.question_count,
      })),
    ]);
  }

  function move(index: number, delta: number) {
    const target = index + delta;
    if (target < 0 || target >= items.length) return;
    setItems((current) => {
      const next = [...current];
      [next[index], next[target]] = [next[target], next[index]];
      return next;
    });
  }

  async function cancelAssignment(assignment: StudyAssignment) {
    if (
      !window.confirm(
        `取消 ${assignment.student?.nickname || assignment.student?.email_masked || "该学生"} 的学习计划？`,
      )
    ) {
      return;
    }
    try {
      await apiPost(`/study-plan-assignments/${assignment.id}/cancel`, {});
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "取消失败");
    }
  }

  async function openProgress(assignmentId: string) {
    setProgressId(assignmentId);
    setProgress(null);
    setProgressLoading(true);
    try {
      const value = await apiGet<StudyAssignmentDetail>(
        `/study-plan-assignments/${assignmentId}`,
      );
      setProgress(value);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载进度失败");
    } finally {
      setProgressLoading(false);
    }
  }

  async function deletePlan() {
    if (!window.confirm("删除这个学习计划？已有指派记录时不能删除，请改为归档。")) {
      return;
    }
    try {
      await apiDelete(`/study-plans/${planId}?subject=${subjectId}`);
      router.push("/study-plans");
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

  if (!plan) {
    return (
      <div className="py-20 text-center text-[12px] text-[var(--danger)]">
        {error || "学习计划不存在"}
      </div>
    );
  }

  return (
    <div>
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <Link
            href="/study-plans"
            className="mb-2 inline-flex items-center gap-1 text-[11.5px] text-[var(--muted)] hover:text-[var(--primary)]"
          >
            <ArrowLeft size={13} /> 学习计划
          </Link>
          <h1 className="text-[27px] font-semibold tracking-[-0.03em]">
            {plan.title}
          </h1>
          <p className="mt-1 text-[12.5px] text-[var(--muted)]">
            {plan.item_count} 个学习项 · {plan.active_assignment_count} 名进行中学生 · 修改只影响之后的指派
          </p>
        </div>
        <div className="flex gap-2">
          <button
            className="a-btn"
            onClick={() => setAssignOpen(true)}
            disabled={!canEdit || plan.item_count === 0}
          >
            <UserPlus size={14} /> 指派学生
          </button>
          {canEdit && (
            <button className="a-btn a-btn-primary" onClick={saveMeta} disabled={saving}>
              {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
              保存信息
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

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(360px,0.8fr)]">
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
                  disabled={!canEdit}
                />
              </label>
              <label className="block">
                <span className="mb-1 block text-[11.5px] text-[var(--muted)]">
                  分类
                </span>
                <select
                  className="a-input"
                  value={category}
                  onChange={(event) => setCategory(event.target.value)}
                  disabled={!canEdit}
                >
                  <option value="">未分类</option>
                  <option value="基础">基础</option>
                  <option value="强化">强化</option>
                  <option value="冲刺">冲刺</option>
                  <option value="陪跑">陪跑</option>
                </select>
              </label>
              <label className="block">
                <span className="mb-1 block text-[11.5px] text-[var(--muted)]">
                  月历颜色
                </span>
                <select
                  className="a-input"
                  value={color}
                  onChange={(event) => setColor(event.target.value)}
                  disabled={!canEdit}
                >
                  {COLORS.map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block sm:col-span-2">
                <span className="mb-1 block text-[11.5px] text-[var(--muted)]">
                  备注
                </span>
                <textarea
                  className="a-input min-h-[80px]"
                  value={note}
                  onChange={(event) => setNote(event.target.value)}
                  disabled={!canEdit}
                />
              </label>
            </div>
          </div>

          <div className="a-card overflow-hidden">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--line)] px-5 py-3">
              <div className="text-[13px] font-semibold">
                学习项 <span className="a-badge ml-1">{items.length}</span>
              </div>
              <div className="flex gap-2">
                {canEdit && (
                  <button
                    className="a-btn a-btn-sm"
                    onClick={() => setHomeworkPickerOpen(true)}
                  >
                    <Plus size={13} /> 添加学习项
                  </button>
                )}
                {canEdit && (
                  <button
                    className="a-btn a-btn-sm a-btn-primary"
                    onClick={saveItems}
                    disabled={saving}
                  >
                    保存学习项
                  </button>
                )}
              </div>
            </div>
            {items.length === 0 ? (
              <div className="py-16 text-center text-[12px] text-[var(--faint)]">
                还没有学习项。添加课堂作业作为每天的任务。
              </div>
            ) : (
              <table className="a-table">
                <thead>
                  <tr>
                    <th className="w-10">#</th>
                    <th>学习项 / 课堂作业</th>
                    <th>题目数</th>
                    <th className="w-44" />
                  </tr>
                </thead>
                <tbody>
                  {items.map((item, index) => (
                    <tr key={item.key}>
                      <td className="font-mono text-[11px]">{index + 1}</td>
                      <td>
                        <input
                          className="a-input mb-1 max-w-[420px] py-1.5 text-[12.5px]"
                          value={item.title}
                          onChange={(event) =>
                            setItems((current) =>
                              current.map((row, rowIndex) =>
                                rowIndex === index
                                  ? { ...row, title: event.target.value }
                                  : row,
                              ),
                            )
                          }
                          disabled={!canEdit}
                        />
                        <div className="text-[10.5px] text-[var(--faint)]">
                          {item.homework_title}
                          {item.topic_code ? ` · ${item.topic_code}` : ""}
                        </div>
                      </td>
                      <td className="font-mono">{item.question_count ?? "—"}</td>
                      <td>
                        {canEdit && (
                          <div className="flex justify-end gap-1">
                            <button
                              className="a-btn a-btn-sm"
                              onClick={() => move(index, -1)}
                              disabled={index === 0}
                            >
                              <ChevronUp size={13} />
                            </button>
                            <button
                              className="a-btn a-btn-sm"
                              onClick={() => move(index, 1)}
                              disabled={index === items.length - 1}
                            >
                              <ChevronDown size={13} />
                            </button>
                            <Link
                              href={`/homeworks/${item.homework_id}`}
                              className="a-btn a-btn-sm"
                            >
                              作业
                            </Link>
                            <button
                              className="a-btn a-btn-sm"
                              onClick={() =>
                                setItems((current) =>
                                  current.filter((_, rowIndex) => rowIndex !== index),
                                )
                              }
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

          {!canEdit ? null : (
            <button className="a-btn a-btn-danger" onClick={deletePlan}>
              <Trash2 size={14} /> 删除计划
            </button>
          )}
        </div>

        <div className="space-y-4">
          <div className="a-card overflow-hidden">
            <div className="flex items-center justify-between border-b border-[var(--line)] px-5 py-3">
              <div className="text-[13px] font-semibold">
                已指派学生 <span className="a-badge ml-1">{assignments.length}</span>
              </div>
              <CalendarRange size={15} className="text-[var(--faint)]" />
            </div>
            {assignments.length === 0 ? (
              <div className="py-12 text-center text-[12px] text-[var(--faint)]">
                还没有指派学生
              </div>
            ) : (
              <div className="max-h-[620px] overflow-y-auto">
                {assignments.map((assignment) => {
                  const percent =
                    assignment.total_items > 0
                      ? Math.round(
                          (assignment.completed_items / assignment.total_items) * 100,
                        )
                      : 0;
                  return (
                    <div
                      key={assignment.id}
                      className="border-b border-[var(--line)] px-5 py-3 last:border-b-0"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <div className="text-[12.5px] font-medium">
                            {assignment.student?.nickname ||
                              assignment.student?.email_masked ||
                              assignment.student?.phone_masked ||
                              "学生"}
                          </div>
                          <div className="mt-0.5 text-[10.5px] text-[var(--faint)]">
                            {assignment.start_date} → {assignment.end_date}
                          </div>
                        </div>
                        <span
                          className={`a-badge ${
                            assignment.status === "active"
                              ? "a-badge-primary"
                              : ""
                          }`}
                        >
                          {assignment.status === "active"
                            ? "进行中"
                            : assignment.status === "completed"
                              ? "已完成"
                              : "已取消"}
                        </span>
                      </div>
                      <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-[var(--surface-3)]">
                        <div
                          className="h-full rounded-full bg-[var(--primary)]"
                          style={{ width: `${percent}%` }}
                        />
                      </div>
                      <div className="mt-1 flex items-center justify-between text-[10.5px] text-[var(--muted)]">
                        <span>
                          {assignment.completed_items}/{assignment.total_items} 项
                          {assignment.overdue_task_days > 0
                            ? ` · 逾期 ${assignment.overdue_task_days} 天`
                            : ""}
                        </span>
                        <div className="flex gap-1">
                          <button
                            className="a-btn a-btn-sm"
                            onClick={() => openProgress(assignment.id)}
                          >
                            进度
                          </button>
                          {canEdit && assignment.status === "active" && (
                            <button
                              className="a-btn a-btn-sm"
                              onClick={() => cancelAssignment(assignment)}
                            >
                              取消
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>

      <HomeworkPicker
        open={homeworkPickerOpen}
        subjectId={subjectId}
        excludeIds={items.map((item) => item.homework_id)}
        onClose={() => setHomeworkPickerOpen(false)}
        onConfirm={addHomeworks}
      />
      <AssignPlanModal
        open={assignOpen}
        subjectId={subjectId}
        fixedPlan={{ id: plan.id, title: plan.title }}
        onClose={() => setAssignOpen(false)}
        onAssigned={load}
      />
      <AdminModal
        open={Boolean(progressId)}
        onClose={() => {
          setProgressId(null);
          setProgress(null);
        }}
        title="学习进度"
        wide
      >
        {progressLoading ? (
          <div className="grid place-items-center py-16">
            <Loader2 size={20} className="animate-spin text-[var(--primary)]" />
          </div>
        ) : progress ? (
          <div className="space-y-3">
            <div className="text-[12px] text-[var(--muted)]">
              {progress.plan_title} · {progress.start_date} → {progress.end_date} ·{" "}
              {progress.completed_items}/{progress.total_items} 项 ·{" "}
              {progress.answered_questions}/{progress.total_questions} 题
            </div>
            <div className="max-h-[420px] overflow-y-auto">
              <table className="a-table">
                <thead>
                  <tr>
                    <th>日期</th>
                    <th>学习项</th>
                    <th>状态</th>
                    <th>题目</th>
                  </tr>
                </thead>
                <tbody>
                  {progress.tasks.map((task) => (
                    <tr key={task.id}>
                      <td className="font-mono text-[11px]">{task.study_date}</td>
                      <td>
                        <div>{task.title}</div>
                        <div className="text-[10.5px] text-[var(--faint)]">
                          {task.homework_title}
                        </div>
                      </td>
                      <td>
                        <span
                          className={`a-badge ${
                            task.status === "completed" ? "a-badge-success" : ""
                          }`}
                        >
                          {task.status === "completed"
                            ? "已完成"
                            : task.overdue
                              ? "逾期"
                              : task.status}
                        </span>
                      </td>
                      <td className="font-mono text-[11px]">
                        {task.answered_question_count}/{task.question_count}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : null}
      </AdminModal>
    </div>
  );
}
