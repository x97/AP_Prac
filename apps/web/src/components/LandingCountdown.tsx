"use client";

import { useExamCountdown } from "@/hooks/useExamCountdown";

export function LandingCountdown() {
  const { countdown } = useExamCountdown();
  const days = countdown?.days;

  return (
    <span className="landing-countdown-parts" role="timer" aria-label="距离 AP Psychology 考试">
      <span>
        <strong>{days === undefined ? "--" : days}</strong>
        <em>天</em>
      </span>
    </span>
  );
}
