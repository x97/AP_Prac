"use client";

import { useEffect, useState } from "react";

import {
  DEFAULT_SUBJECT_ID,
  getExamCountdown,
  getExamSchedule,
  type ExamCountdown,
} from "@/config/examSchedule";

export function useExamCountdown(subjectId = DEFAULT_SUBJECT_ID) {
  const schedule = getExamSchedule(subjectId);
  const [countdown, setCountdown] = useState<ExamCountdown | null>(null);

  useEffect(() => {
    const tick = () => setCountdown(getExamCountdown(schedule));
    tick();
    const timer = window.setInterval(tick, 60_000);
    return () => window.clearInterval(timer);
  }, [schedule]);

  return { schedule, countdown };
}
