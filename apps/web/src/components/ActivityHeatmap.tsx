"use client";

import { useEffect, useMemo, useRef } from "react";

type ActivityDay = {
  day: string;
  answered: number;
  correct: number;
};

type Summary = {
  days: number;
  active_days: number;
  total_answered: number;
};

const MONTHS = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

function parseDay(value: string) {
  const [year, month, day] = value.split("-").map(Number);
  return new Date(year, month - 1, day);
}

function isoDay(date: Date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(
    date.getDate(),
  ).padStart(2, "0")}`;
}

export function ActivityHeatmap({
  activity,
  summary,
  streakDays,
}: {
  activity: ActivityDay[];
  summary: Summary;
  streakDays: number;
}) {
  const scrollRef = useRef<HTMLDivElement>(null);

  const { weeks, months, maxCount } = useMemo(() => {
    if (activity.length === 0) {
      return { weeks: [] as Array<{ days: Array<ActivityDay | null> }>, months: [], maxCount: 1 };
    }
    const byDay = new Map(activity.map((item) => [item.day, item]));
    const end = parseDay(activity[activity.length - 1].day);
    const start = new Date(end);
    start.setDate(start.getDate() - 364);
    start.setDate(start.getDate() - start.getDay());

    const weeks: Array<{ days: Array<ActivityDay | null> }> = [];
    const months: Array<{ label: string; index: number }> = [];
    let week: Array<ActivityDay | null> = [];
    let cursor = new Date(start);
    let lastMonth = -1;

    while (cursor <= end) {
      const key = isoDay(cursor);
      week.push(
        byDay.get(key) || {
          day: key,
          answered: 0,
          correct: 0,
        },
      );
      if (week.length === 1) {
        const month = cursor.getMonth();
        if (month !== lastMonth) {
          months.push({ label: MONTHS[month], index: weeks.length });
          lastMonth = month;
        }
      }
      if (week.length === 7) {
        weeks.push({ days: week });
        week = [];
      }
      cursor.setDate(cursor.getDate() + 1);
    }
    if (week.length > 0) {
      while (week.length < 7) week.push(null);
      weeks.push({ days: week });
    }
    const maxCount = Math.max(1, ...activity.map((item) => item.answered));
    return { weeks, months, maxCount };
  }, [activity]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollLeft = scrollRef.current.scrollWidth;
    }
  }, [weeks.length]);

  function level(count: number) {
    if (count <= 0) return 0;
    const ratio = count / maxCount;
    if (ratio <= 0.25) return 1;
    if (ratio <= 0.5) return 2;
    if (ratio <= 0.75) return 3;
    return 4;
  }

  return (
    <div>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="eyebrow">Activity</div>
          <h2 className="h2 mt-1">Practice Heatmap</h2>
        </div>
        <div className="text-right text-[11px] faint leading-5">
          <div>{summary.total_answered} reviews in the past year</div>
          <div>
            Active {summary.active_days} days · Streak {streakDays} days
          </div>
        </div>
      </div>

      {weeks.length === 0 ? (
        <div className="empty py-10 text-[12.5px]">No activity yet.</div>
      ) : (
        <>
          <div className="heat-body mt-4">
            <div className="heat-weekdays">
              <span>Sun</span>
              <span>Mon</span>
              <span>Tue</span>
              <span>Wed</span>
              <span>Thu</span>
              <span>Fri</span>
              <span>Sat</span>
            </div>
            <div className="heat-scroll" ref={scrollRef}>
              <div
                className="heat-months"
                style={{ gridTemplateColumns: `repeat(${weeks.length}, var(--heat-cell))` }}
              >
                {weeks.map((_, index) => {
                  const label = months.find((month) => month.index === index)?.label;
                  return <span key={index}>{label || ""}</span>;
                })}
              </div>
              <div
                className="heat-grid"
                style={{ gridTemplateColumns: `repeat(${weeks.length}, var(--heat-cell))` }}
              >
                {weeks.map((week, weekIndex) => (
                  <div className="heat-week" key={weekIndex}>
                    {week.days.map((day, dayIndex) =>
                      day ? (
                        <span
                          key={day.day}
                          className={`heat-cell heat-${level(day.answered)}`}
                          title={`${day.day} · ${day.answered} reviews · ${day.correct} correct`}
                        />
                      ) : (
                        <span key={`empty-${dayIndex}`} className="heat-cell heat-empty" />
                      ),
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between mt-3 gap-3">
            <span className="text-[10.5px] faint">
              Each square is one day. Darker means more reviews.
            </span>
            <div className="heat-legend">
              <span>Less</span>
              {[0, 1, 2, 3, 4].map((value) => (
                <i key={value} className={`heat-cell heat-${value}`} />
              ))}
              <span>More</span>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
