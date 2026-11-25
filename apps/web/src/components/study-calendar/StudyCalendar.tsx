"use client";

import { ChevronLeft, ChevronRight, Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { DayDetailPanel } from "@/components/study-calendar/DayDetailPanel";
import { CalendarMonthGrid } from "@/components/study-calendar/CalendarMonthGrid";
import { StudyBacklogPanel } from "@/components/study-calendar/StudyBacklogPanel";
import { StudyCalendarEmptyState } from "@/components/study-calendar/StudyCalendarEmptyState";
import { TeacherContactModal } from "@/components/TeacherContactModal";
import { apiGet, apiPost, ApiError } from "@/lib/api";
import {
  addMonths,
  monthCells,
  monthKeyFromDate,
  monthLabel,
  todayKeyFromShanghai,
  weekdayLabels,
} from "@/lib/calendar";
import { useLanguage } from "@/lib/i18n";
import type {
  StudyCalendarDay,
  StudyCalendarResponse,
  StudyDayResponse,
  StudyDayTask,
} from "@/lib/types";

function monthOf(date: string) {
  return date.slice(0, 7);
}

export function StudyCalendar() {
  const { t } = useLanguage();
  const router = useRouter();
  const today = todayKeyFromShanghai();
  const [month, setMonth] = useState(monthKeyFromDate(today));
  const [selected, setSelected] = useState(today);
  const [panelMode, setPanelMode] = useState<"backlog" | "date">("backlog");
  const [data, setData] = useState<StudyCalendarResponse | null>(null);
  const [dayData, setDayData] = useState<StudyDayResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [dayLoading, setDayLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dayError, setDayError] = useState<string | null>(null);
  const [startingId, setStartingId] = useState<string | null>(null);
  const [contactOpen, setContactOpen] = useState(false);
  const [refresh, setRefresh] = useState(0);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError(null);
    apiGet<StudyCalendarResponse>(`/study-calendar?month=${month}`)
      .then((value) => {
        if (!alive) return;
        setData(value);
        setSelected((current) => {
          if (monthOf(current) === value.month) return current;
          if (monthOf(value.today) === value.month) return value.today;
          return `${value.month}-01`;
        });
      })
      .catch((e: Error) => alive && setError(e.message))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [month, refresh]);

  useEffect(() => {
    if (!selected) return;
    let alive = true;
    setDayLoading(true);
    setDayError(null);
    apiGet<StudyDayResponse>(`/study-calendar/days/${selected}`)
      .then((value) => alive && setDayData(value))
      .catch((e: Error) => alive && setDayError(e.message))
      .finally(() => alive && setDayLoading(false));
    return () => {
      alive = false;
    };
  }, [selected, refresh]);

  useEffect(() => {
    function onFocus() {
      setRefresh((value) => value + 1);
    }
    window.addEventListener("focus", onFocus);
    document.addEventListener("visibilitychange", onFocus);
    return () => {
      window.removeEventListener("focus", onFocus);
      document.removeEventListener("visibilitychange", onFocus);
    };
  }, []);

  const daysByDate = useMemo(() => {
    const map: Record<string, StudyCalendarDay> = {};
    for (const day of data?.days || []) map[day.date] = day;
    return map;
  }, [data]);

  const cells = useMemo(() => monthCells(month), [month]);

  const restDates = useMemo(() => {
    const values = new Set<string>();
    if (!data) return values;
    for (const cell of cells) {
      if (!cell.inMonth || daysByDate[cell.date]) continue;
      const inside = data.plans.some(
        (plan) => cell.date >= plan.start_date && cell.date <= plan.end_date,
      );
      if (inside) values.add(cell.date);
    }
    return values;
  }, [cells, data, daysByDate]);

  function selectDate(dateKey: string, inMonth: boolean) {
    if (!inMonth) setMonth(monthOf(dateKey));
    setSelected(dateKey);
    setPanelMode("date");
  }

  async function startTask(task: StudyDayTask) {
    setStartingId(task.task_id);
    setError(null);
    try {
      const result = await apiPost<{ session_id?: string }>(
        `/study-calendar/tasks/${task.task_id}/start`,
      );
      if (!result.session_id) {
        setRefresh((value) => value + 1);
        return;
      }
      router.push(
        `/practice/session/${result.session_id}?from=calendar&task=${task.task_id}`,
      );
    } catch (e) {
      if (e instanceof ApiError && e.code === "TASK_LOCKED") {
        setRefresh((value) => value + 1);
      }
      setError(e instanceof Error ? e.message : t("开始失败"));
    } finally {
      setStartingId(null);
    }
  }

  if (loading && !data) {
    return (
      <div className="grid place-items-center py-24">
        <Loader2 size={24} className="animate-spin text-[var(--primary)]" />
      </div>
    );
  }

  if (data && !data.has_ever_plan) {
    return (
      <>
        <StudyCalendarEmptyState onContact={() => setContactOpen(true)} />
        <TeacherContactModal open={contactOpen} onClose={() => setContactOpen(false)} />
      </>
    );
  }

  return (
    <div>
      <div className="page-head study-calendar-head">        <div>
          <div className="eyebrow">Study calendar</div>
          <h1 className="h1 mt-1">{t("学习日历")}</h1>
          <p className="mt-1 text-[12.5px] muted">
            {t("老师安排的任务都在这里；完成当天的题，下一项自动解锁。")}
          </p>
        </div>
        <div className="study-month-nav">
          <button
            type="button"
            className="btn btn-sm"
            onClick={() => setMonth(addMonths(month, -1))}
            aria-label={t("上个月")}
          >
            <ChevronLeft size={15} />
          </button>
          <span className="study-month-label">{monthLabel(month)}</span>
          <button
            type="button"
            className="btn btn-sm"
            onClick={() => setMonth(addMonths(month, 1))}
            aria-label={t("下个月")}
          >
            <ChevronRight size={15} />
          </button>
          <button
            type="button"
            className="btn btn-sm"
            onClick={() => {
              setMonth(monthOf(today));
              setSelected(today);
              setPanelMode("date");
            }}
          >
            {t("今天")}
          </button>
        </div>
      </div>

      {error && <div className="study-alert is-error">{error}</div>}

      <div className="study-calendar-layout">
        <section className="card study-calendar-card">
          <div className="study-weekdays" aria-hidden="true">
            {weekdayLabels().map((label) => (
              <span key={label}>{label}</span>
            ))}
          </div>
          <CalendarMonthGrid
            cells={cells}
            days={daysByDate}
            restDates={restDates}
            today={data?.today || today}
            selected={selected}
            onSelect={selectDate}
          />
          <div className="study-legend">
            <span><i className="is-completed" />{t("已完成")}</span>
            <span><i className="is-pending" />{t("可开始")}</span>
            <span><i className="is-locked" />{t("已锁定")}</span>
            <span><i className="is-overdue" />{t("逾期")}</span>
            <span><i className="is-rest" />{t("休息")}</span>
          </div>
        </section>

        {panelMode === "backlog" ? (
          <StudyBacklogPanel
            tasks={data?.backlog || []}
            today={data?.today || today}
            startingId={startingId}
            onStart={startTask}
            onSelectDate={(date) => {
              setMonth(monthOf(date));
              setSelected(date);
              setPanelMode("date");
            }}
          />
        ) : (
          <DayDetailPanel
            date={selected}
            data={dayData}
            loading={dayLoading}
            error={dayError}
            startingId={startingId}
            onStart={startTask}
            onBacklog={() => setPanelMode("backlog")}
          />
        )}
      </div>

      <TeacherContactModal open={contactOpen} onClose={() => setContactOpen(false)} />
    </div>
  );
}
