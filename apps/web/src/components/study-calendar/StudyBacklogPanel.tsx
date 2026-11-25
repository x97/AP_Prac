"use client";

import { CalendarCheck2, ChevronRight } from "lucide-react";

import { useLanguage } from "@/lib/i18n";
import { formatDayLabel } from "@/lib/calendar";
import type { StudyBacklogTask, StudyDayTask } from "@/lib/types";
import { StudyTaskCard } from "@/components/study-calendar/StudyTaskCard";

export function StudyBacklogPanel({
  tasks,
  today,
  startingId,
  onStart,
  onSelectDate,
}: {
  tasks: StudyBacklogTask[];
  today: string;
  startingId: string | null;
  onStart: (task: StudyDayTask) => void;
  onSelectDate: (date: string) => void;
}) {
  const { t } = useLanguage();
  const groups = new Map<string, StudyBacklogTask[]>();
  for (const task of tasks) {
    groups.set(task.study_date, [...(groups.get(task.study_date) || []), task]);
  }

  return (
    <aside className="study-day-panel">
      <div className="study-day-panel-head">
        <div>
          <div className="eyebrow">To do</div>
          <h2 className="mt-1 text-[20px] font-semibold tracking-[-0.02em]">
            {t("待学习")}
          </h2>
          <p className="mt-1 text-[12.5px] text-[var(--muted)]">
            {t("今天及以前未完成的任务，可以直接补做。")}
          </p>
        </div>
        <span className="pill pill-primary">{tasks.length}</span>
      </div>

      {tasks.length === 0 ? (
        <div className="study-empty-note">
          <CalendarCheck2
            size={26}
            className="mx-auto mb-2 text-[var(--success)]"
          />
          {t("今天没有待补做的任务")}
        </div>
      ) : (
        <div className="space-y-4">
          {[...groups.entries()].map(([date, group]) => {
            const overdue = date < today;
            return (
              <section key={date}>
                <button
                  type="button"
                  className="mb-2 flex w-full items-center justify-between gap-2 text-left"
                  onClick={() => onSelectDate(date)}
                >
                  <span className="flex items-center gap-2 text-[13px] font-semibold">
                    {formatDayLabel(date)}
                    {date === today ? (
                      <span className="pill pill-primary">{t("今天")}</span>
                    ) : overdue ? (
                      <span className="pill pill-warn">{t("逾期")}</span>
                    ) : null}
                  </span>
                  <ChevronRight size={13} className="text-[var(--faint)]" />
                </button>
                <div className="space-y-2">
                  {group.map((task) => (
                    <div key={task.task_id}>
                      <div className="mb-1 flex items-center gap-1.5 text-[12px] text-[var(--muted)]">
                        <span className="truncate">{task.plan_title}</span>
                      </div>
                      <StudyTaskCard
                        task={task}
                        planColor={task.plan_color}
                        starting={startingId === task.task_id}
                        onStart={onStart}
                      />
                    </div>
                  ))}
                </div>
              </section>
            );
          })}
        </div>
      )}
    </aside>
  );
}
