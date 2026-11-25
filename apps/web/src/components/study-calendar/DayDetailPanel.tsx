"use client";

import { ArrowLeft, CalendarDays, Loader2 } from "lucide-react";

import { useLanguage } from "@/lib/i18n";
import { formatDayLabel } from "@/lib/calendar";
import type { StudyDayResponse, StudyDayTask } from "@/lib/types";
import { StudyTaskCard } from "@/components/study-calendar/StudyTaskCard";

export function DayDetailPanel({
  date,
  data,
  loading,
  error,
  startingId,
  onStart,
  onBacklog,
}: {
  date: string;
  data: StudyDayResponse | null;
  loading: boolean;
  error: string | null;
  startingId: string | null;
  onStart: (task: StudyDayTask) => void;
  onBacklog?: () => void;
}) {
  const { t } = useLanguage();
  const total = data?.assignments.reduce(
    (sum, group) => sum + group.summary.total,
    0,
  ) ?? 0;
  const completed = data?.assignments.reduce(
    (sum, group) => sum + group.summary.completed,
    0,
  ) ?? 0;

  return (
    <aside className="study-day-panel">
      {onBacklog && (
        <button
          type="button"
          className="mb-2 flex items-center gap-1 text-[11px] text-[var(--muted)] hover:text-[var(--primary)]"
          onClick={onBacklog}
        >
          <ArrowLeft size={12} /> {t("待学习")}
        </button>
      )}
      <div className="study-day-panel-head">
        <div>
          <div className="eyebrow">{data?.is_today ? t("今天") : "Agenda"}</div>
          <h2 className="mt-1 text-[18px] font-semibold tracking-[-0.02em]">
            {formatDayLabel(date)}
          </h2>
        </div>
        {total > 0 && (
          <span className="pill pill-primary">
            {completed}/{total} {t("项")}
          </span>
        )}
      </div>

      {loading ? (
        <div className="grid place-items-center py-16">
          <Loader2 size={20} className="animate-spin text-[var(--primary)]" />
        </div>
      ) : error ? (
        <div className="study-empty-note">{error}</div>
      ) : !data || data.assignments.length === 0 ? (
        <div className="study-empty-note">
          <CalendarDays size={24} className="mx-auto mb-2 text-[var(--faint)]" />
          {t("这一天没有安排任务")}
        </div>
      ) : (
        <div className="space-y-4">
          {data.assignments.map((group) => (
            <section key={group.assignment_id}>
              <div className="mb-2 flex items-center justify-between gap-2">
                <div className="flex min-w-0 items-center gap-2">
                  <span className="truncate text-[13px] font-semibold">
                    {group.plan_title}
                  </span>
                </div>
                <span className="text-[10.5px] text-[var(--faint)]">
                  {group.summary.completed}/{group.summary.total}
                </span>
              </div>
              <div className="space-y-2">
                {group.tasks.map((task) => (
                  <StudyTaskCard
                    key={task.task_id}
                    task={task}
                    planColor={group.color}
                    starting={startingId === task.task_id}
                    onStart={onStart}
                  />
                ))}
              </div>
            </section>
          ))}
        </div>
      )}
    </aside>
  );
}
