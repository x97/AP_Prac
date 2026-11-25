export type CalendarCell = {
  date: string;
  day: number;
  inMonth: boolean;
};

const WEEKDAYS = ["一", "二", "三", "四", "五", "六", "日"];

export function todayKeyFromShanghai() {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Shanghai" }).format(
    new Date(),
  );
}

export function monthKeyFromDate(value: Date | string = new Date()) {
  if (typeof value === "string") return value.slice(0, 7);
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
  }).formatToParts(value);
  const year = parts.find((part) => part.type === "year")?.value;
  const month = parts.find((part) => part.type === "month")?.value;
  return `${year}-${month}`;
}

export function addMonths(monthKey: string, delta: number) {
  const [year, month] = monthKey.split("-").map(Number);
  const value = new Date(Date.UTC(year, month - 1 + delta, 1));
  return value.toISOString().slice(0, 7);
}

export function monthLabel(monthKey: string) {
  const [year, month] = monthKey.split("-").map(Number);
  return `${year} 年 ${month} 月`;
}

export function monthCells(monthKey: string): CalendarCell[] {
  const [year, month] = monthKey.split("-").map(Number);
  const first = new Date(Date.UTC(year, month - 1, 1));
  // Monday-first grid, always 42 cells (6 weeks).
  const offset = (first.getUTCDay() + 6) % 7;
  const start = new Date(Date.UTC(year, month - 1, 1 - offset));
  const cells: CalendarCell[] = [];
  for (let index = 0; index < 42; index += 1) {
    const value = new Date(start.getTime() + index * 86_400_000);
    const date = value.toISOString().slice(0, 10);
    cells.push({
      date,
      day: value.getUTCDate(),
      inMonth: value.getUTCMonth() === month - 1,
    });
  }
  return cells;
}

export function weekdayLabels() {
  return WEEKDAYS;
}

export function formatDayLabel(dateKey: string) {
  const [year, month, day] = dateKey.split("-").map(Number);
  return `${year} 年 ${month} 月 ${day} 日`;
}
