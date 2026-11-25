"use client";

import { CalendarDays, Loader2, Search, Users } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { AdminModal } from "@/components/AdminModal";
import { apiGet, apiPost } from "@/lib/api";
import type {
  StudentList,
  StudentListItem,
  StudyPlan,
  StudyPlanList,
  StudySchedulePreview,
} from "@/lib/types";

function shanghaiToday() {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Shanghai" }).format(
    new Date(),
  );
}

function addDays(key: string, days: number) {
  const [year, month, day] = key.split("-").map(Number);
  const value = new Date(Date.UTC(year, month - 1, day + days));
  return value.toISOString().slice(0, 10);
}

export function AssignPlanModal({
  open,
  subjectId,
  fixedStudent,
  fixedPlan,
  onClose,
  onAssigned,
}: {
  open: boolean;
  subjectId: string;
  fixedStudent?: StudentListItem | { id: string; nickname: string | null } | null;
  fixedPlan?: Pick<StudyPlan, "id" | "title"> | null;
  onClose: () => void;
  onAssigned?: () => void;
}) {
  const today = shanghaiToday();
  const [plans, setPlans] = useState<StudyPlan[]>([]);
  const [planId, setPlanId] = useState(fixedPlan?.id || "");
  const [studentQuery, setStudentQuery] = useState("");
  const [students, setStudents] = useState<StudentListItem[]>([]);
  const [selectedStudents, setSelectedStudents] = useState<StudentListItem[]>([]);
  const [startDate, setStartDate] = useState(today);
  const [endDate, setEndDate] = useState(addDays(today, 29));
  const [preview, setPreview] = useState<StudySchedulePreview | null>(null);
  const [loading, setLoading] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{
    assigned: Array<Record<string, unknown>>;
    skipped: Array<{ user_id: string; reason: string }>;
  } | null>(null);

  useEffect(() => {
    if (!open) return;
    setPlanId(fixedPlan?.id || "");
    setSelectedStudents([]);
    setStudentQuery("");
    setStartDate(today);
    setEndDate(addDays(today, 29));
    setPreview(null);
    setError(null);
    setResult(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, fixedPlan?.id]);

  useEffect(() => {
    if (!open || fixedPlan) return;
    let alive = true;
    apiGet<StudyPlanList>(
      `/study-plans?subject=${encodeURIComponent(subjectId)}&status=active&limit=100`,
    )
      .then((value) => alive && setPlans(value.plans))
      .catch((e: Error) => alive && setError(e.message));
    return () => {
      alive = false;
    };
  }, [open, fixedPlan, subjectId]);

  useEffect(() => {
    if (!open || fixedStudent) return;
    let alive = true;
    const timer = window.setTimeout(() => {
      setLoading(true);
      const params = new URLSearchParams({ limit: "20" });
      if (studentQuery) params.set("q", studentQuery);
      apiGet<StudentList>(`/students?${params.toString()}`)
        .then((value) => alive && setStudents(value.students))
        .catch((e: Error) => alive && setError(e.message))
        .finally(() => alive && setLoading(false));
    }, 300);
    return () => {
      alive = false;
      window.clearTimeout(timer);
    };
  }, [open, fixedStudent, studentQuery]);

  useEffect(() => {
    if (!open || !planId || !startDate || !endDate) {
      setPreview(null);
      return;
    }
    let alive = true;
    setPreviewLoading(true);
    setError(null);
    apiPost<StudySchedulePreview>(
      `/study-plans/${planId}/assign-preview?subject=${encodeURIComponent(subjectId)}`,
      { start_date: startDate, end_date: endDate },
    )
      .then((value) => alive && setPreview(value))
      .catch((e: Error) => {
        if (!alive) return;
        setPreview(null);
        setError(e.message);
      })
      .finally(() => alive && setPreviewLoading(false));
    return () => {
      alive = false;
    };
  }, [open, planId, startDate, endDate, subjectId]);

  const activeStudents = useMemo(() => {
    if (fixedStudent) {
      return [fixedStudent as StudentListItem];
    }
    return selectedStudents;
  }, [fixedStudent, selectedStudents]);

  function toggleStudent(student: StudentListItem) {
    setSelectedStudents((current) =>
      current.some((item) => item.id === student.id)
        ? current.filter((item) => item.id !== student.id)
        : [...current, student],
    );
  }

  async function submit() {
    if (!planId || activeStudents.length === 0) return;
    setSubmitting(true);
    setError(null);
    try {
      const payload = await apiPost<{
        assigned: Array<Record<string, unknown>>;
        skipped: Array<{ user_id: string; reason: string }>;
      }>(`/study-plans/${planId}/assign?subject=${encodeURIComponent(subjectId)}`, {
        student_ids: activeStudents.map((student) => student.id),
        start_date: startDate,
        end_date: endDate,
      });
      setResult(payload);
      onAssigned?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : "指派失败");
    } finally {
      setSubmitting(false);
    }
  }

  const selectedPlan = fixedPlan || plans.find((item) => item.id === planId);

  return (
    <AdminModal open={open} onClose={onClose} title="指派学习计划" wide>
      <div className="space-y-4">
        {error && (
          <div className="rounded-xl border border-[#f6d5d2] bg-[var(--danger-soft)] px-3 py-2 text-[12px] text-[var(--danger)]">
            {error}
          </div>
        )}
        {result ? (
          <div className="space-y-3">
            <div className="rounded-xl border border-[#bfe8d1] bg-[var(--success-soft)] px-4 py-3 text-[13px]">
              已指派 {result.assigned.length} 名学生
              {result.skipped.length > 0
                ? `，跳过 ${result.skipped.length} 名（已指派或不可用）`
                : ""}
              。
            </div>
            <div className="flex justify-end">
              <button className="a-btn a-btn-primary" onClick={onClose}>
                完成
              </button>
            </div>
          </div>
        ) : (
          <>
            {!fixedPlan && (
              <label className="block">
                <span className="mb-1 block text-[11.5px] text-[var(--muted)]">
                  学习计划
                </span>
                <select
                  className="a-input"
                  value={planId}
                  onChange={(event) => setPlanId(event.target.value)}
                >
                  <option value="">选择学习计划</option>
                  {plans.map((plan) => (
                    <option key={plan.id} value={plan.id}>
                      {plan.title}（{plan.item_count} 项）
                    </option>
                  ))}
                </select>
              </label>
            )}

            {fixedPlan && (
              <div className="rounded-xl border border-[var(--line)] bg-[var(--surface-2)] px-3 py-2 text-[12.5px]">
                计划：<strong>{fixedPlan.title}</strong>
              </div>
            )}

            {!fixedStudent && (
              <div>
                <div className="mb-1 text-[11.5px] text-[var(--muted)]">学生</div>
                <div className="relative">
                  <Search
                    size={15}
                    className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--faint)]"
                  />
                  <input
                    className="a-input pl-9"
                    value={studentQuery}
                    onChange={(event) => setStudentQuery(event.target.value)}
                    placeholder="搜索邮箱、手机号或昵称"
                  />
                </div>
                <div className="mt-2 max-h-[180px] overflow-y-auto rounded-xl border border-[var(--line)]">
                  {loading ? (
                    <div className="grid place-items-center py-8">
                      <Loader2
                        size={18}
                        className="animate-spin text-[var(--primary)]"
                      />
                    </div>
                  ) : students.length === 0 ? (
                    <div className="py-8 text-center text-[12px] text-[var(--faint)]">
                      没有找到学生
                    </div>
                  ) : (
                    students.map((student) => {
                      const checked = selectedStudents.some(
                        (item) => item.id === student.id,
                      );
                      return (
                        <label
                          key={student.id}
                          className="flex cursor-pointer items-center gap-2 border-b border-[var(--line)] px-3 py-2 last:border-b-0 hover:bg-[var(--surface-2)]"
                        >
                          <input
                            type="checkbox"
                            className="h-4 w-4 accent-[var(--primary)]"
                            checked={checked}
                            onChange={() => toggleStudent(student)}
                          />
                          <span className="text-[12px]">
                            {student.nickname ||
                              student.email_masked ||
                              student.phone_masked}
                          </span>
                          <span className="ml-auto text-[10.5px] text-[var(--faint)]">
                            {student.email_masked || student.phone_masked}
                          </span>
                        </label>
                      );
                    })
                  )}
                </div>
                {selectedStudents.length > 0 && (
                  <div className="mt-2 text-[11.5px] text-[var(--muted)]">
                    已选 {selectedStudents.length} 名学生
                  </div>
                )}
              </div>
            )}

            {fixedStudent && (
              <div className="rounded-xl border border-[var(--line)] bg-[var(--surface-2)] px-3 py-2 text-[12.5px]">
                学生：
                <strong>
                  {fixedStudent.nickname ||
                    ("email_masked" in fixedStudent
                      ? fixedStudent.email_masked
                      : null) ||
                    fixedStudent.id}
                </strong>
              </div>
            )}

            <div className="grid gap-3 sm:grid-cols-2">
              <label className="block">
                <span className="mb-1 block text-[11.5px] text-[var(--muted)]">
                  开始日期（北京时间）
                </span>
                <input
                  type="date"
                  className="a-input"
                  value={startDate}
                  onChange={(event) => setStartDate(event.target.value)}
                />
              </label>
              <label className="block">
                <span className="mb-1 block text-[11.5px] text-[var(--muted)]">
                  结束日期（北京时间）
                </span>
                <input
                  type="date"
                  className="a-input"
                  value={endDate}
                  onChange={(event) => setEndDate(event.target.value)}
                />
              </label>
            </div>

            <div className="rounded-xl border border-[var(--line)] bg-[var(--surface-2)] p-3">
              <div className="mb-2 flex items-center gap-2 text-[12px] font-semibold">
                <CalendarDays size={14} /> 分配预览
                {previewLoading && (
                  <Loader2 size={13} className="animate-spin text-[var(--primary)]" />
                )}
              </div>
              {preview ? (
                <>
                  <div className="text-[12px] text-[var(--muted)]">
                    共 {preview.total_items} 个学习项 / {preview.total_days} 天：
                    有任务的 {preview.task_days} 天，休息 {preview.rest_days} 天；
                    每天最多 {preview.max_items_per_day} 项。
                  </div>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {preview.days.map((day) => (
                      <span
                        key={day.date}
                        title={`${day.date}：${day.item_count} 项`}
                        className={`grid h-6 min-w-6 place-items-center rounded px-1 font-mono text-[10px] ${
                          day.item_count
                            ? "bg-[var(--primary-soft)] text-[var(--primary)]"
                            : "bg-[var(--surface-3)] text-[var(--faint)]"
                        }`}
                      >
                        {day.item_count || "·"}
                      </span>
                    ))}
                  </div>
                </>
              ) : (
                <div className="text-[12px] text-[var(--faint)]">
                  选择计划和日期后显示分配结果。
                </div>
              )}
            </div>

            <div className="flex items-center justify-between border-t border-[var(--line)] pt-3">
              <div className="flex items-center gap-1 text-[11.5px] text-[var(--muted)]">
                <Users size={13} /> {activeStudents.length} 名学生
              </div>
              <div className="flex gap-2">
                <button className="a-btn" onClick={onClose}>
                  取消
                </button>
                <button
                  className="a-btn a-btn-primary"
                  disabled={
                    submitting ||
                    !planId ||
                    activeStudents.length === 0 ||
                    !selectedPlan
                  }
                  onClick={submit}
                >
                  {submitting ? (
                    <Loader2 size={14} className="animate-spin" />
                  ) : null}
                  确认指派
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </AdminModal>
  );
}
