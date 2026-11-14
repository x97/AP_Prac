export type ExamSchedule = {
  subjectId: string;
  subjectName: string;
  /** YYYY-MM-DD */
  examDate: string;
  examTime: string;
  displayDate: string;
  timeZone: string;
};

// Frontend-only exam schedule. Add future subjects here; the homepage can
// later select the schedule from the user's active subject.
export const EXAM_SCHEDULES: Record<string, ExamSchedule> = {
  psychology: {
    subjectId: "psychology",
    subjectName: "AP Psychology",
    examDate: "2027-05-14",
    examTime: "12:00",
    displayDate: "May 14, 2027 · 12:00 PM",
    timeZone: "Asia/Shanghai",
  },
};

export const DEFAULT_SUBJECT_ID = "psychology";

export function getExamSchedule(subjectId = DEFAULT_SUBJECT_ID): ExamSchedule {
  return (
    EXAM_SCHEDULES[subjectId] ?? EXAM_SCHEDULES[DEFAULT_SUBJECT_ID]
  );
}

export type ExamCountdown =
  | {
      kind: "upcoming";
      days: number;
      hours: number;
      minutes: number;
      seconds: number;
      totalSeconds: number;
    }
  | { kind: "today"; days: 0; hours: 0; minutes: 0; seconds: 0; totalSeconds: 0 }
  | { kind: "done"; days: 0; hours: 0; minutes: 0; seconds: 0; totalSeconds: 0 };

export function getExamCountdown(
  schedule: ExamSchedule,
  now = new Date(),
): ExamCountdown {
  // The exam starts at the local (Asia/Shanghai) exam time. China has no DST.
  const start = new Date(
    `${schedule.examDate}T${schedule.examTime || "00:00"}:00+08:00`,
  );
  const end = new Date(start.getTime() + 86_400_000);
  if (now >= end) {
    return { kind: "done", days: 0, hours: 0, minutes: 0, seconds: 0, totalSeconds: 0 };
  }
  if (now >= start) {
    return { kind: "today", days: 0, hours: 0, minutes: 0, seconds: 0, totalSeconds: 0 };
  }

  const totalSeconds = Math.max(0, Math.floor((start.getTime() - now.getTime()) / 1000));
  return {
    kind: "upcoming",
    days: Math.floor(totalSeconds / 86_400),
    hours: Math.floor((totalSeconds % 86_400) / 3_600),
    minutes: Math.floor((totalSeconds % 3_600) / 60),
    seconds: totalSeconds % 60,
    totalSeconds,
  };
}
