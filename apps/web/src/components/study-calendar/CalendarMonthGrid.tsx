"use client";

import { LockGlyph } from "@/components/LockGlyph";
import { useLanguage } from "@/lib/i18n";
import type { StudyCalendarDay, StudyCalendarTask } from "@/lib/types";
import type { CalendarCell } from "@/lib/calendar";

const STATUS_CLASS: Record<StudyCalendarTask["status"], string> = {
  completed: "is-completed",
  pending: "is-pending",
  overdue: "is-overdue",
  locked: "is-locked",
};

export function CalendarMonthGrid({
  cells,
  days,
  restDates,
  today,
  selected,
  onSelect,
}: {
  cells: CalendarCell[];
  days: Record<string, StudyCalendarDay>;
  restDates: Set<string>;
  today: string;
  selected: string;
  onSelect: (date: string, inMonth: boolean) => void;
}) {
  const { t } = useLanguage();
  return (
    <div className="study-calendar-grid" role="grid" aria-label="学习日历">
      {cells.map((cell) => {
        const day = days[cell.date];
        const summary = day?.summary;
        const overdue = Boolean(summary && summary.overdue > 0);
        const complete = Boolean(
          summary && summary.total > 0 && summary.completed === summary.total,
        );
        const todayPending = Boolean(
          cell.date === today && summary && summary.total > 0 && !complete && !overdue,
        );
        const taskDay = Boolean(
          summary && summary.total > 0 && !overdue && !todayPending && !complete,
        );
        const rest = !day && restDates.has(cell.date);
        const visible = (day?.tasks || []).slice(0, 2);
        const extra = (day?.tasks?.length || 0) - visible.length;
        return (
          <button
            key={cell.date}
            type="button"
            role="gridcell"
            className={[
              "study-day",
              cell.inMonth ? "" : "is-outside",
              cell.date === today ? "is-today" : "",
              cell.date === selected ? "is-selected" : "",
              overdue ? "is-overdue-day" : "",
              complete ? "is-complete-day" : "",
              todayPending ? "is-today-task-day" : "",
              taskDay ? "is-task-day" : "",
              rest ? "is-rest-day" : "",
            ].join(" ")}
            onClick={() => onSelect(cell.date, cell.inMonth)}
          >
            <span className="study-day-number">{cell.day}</span>
            {rest && <span className="study-day-rest">{t("休息")}</span>}
            {day && (
              <>
                <span className="study-day-pills">
                  {visible.map((task) => (
                    <span
                      key={task.task_id}
                      className={`study-pill ${STATUS_CLASS[task.status]} color-${task.color}`}
                      title={`${task.plan_title} · ${task.title}`}
                    >
                      {task.status === "completed" && (
                        <span className="study-pill-check">✓</span>
                      )}
                      {task.status === "locked" && <LockGlyph size={9} />}
                      <span className="study-pill-text">{task.title}</span>
                    </span>
                  ))}
                  {extra > 0 && (
                    <span className="study-pill is-more">+{extra}</span>
                  )}
                </span>
                <span className="study-day-dots" aria-hidden="true">
                  {(day.tasks || []).slice(0, 3).map((task) => (
                    <i key={task.task_id} className={STATUS_CLASS[task.status]} />
                  ))}
                </span>
              </>
            )}
            {overdue && <span className="study-day-badge">{t("逾期")}</span>}
          </button>
        );
      })}
    </div>
  );
}
