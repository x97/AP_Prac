"use client";

import { useExamCountdown } from "@/hooks/useExamCountdown";
import { useLanguage } from "@/lib/i18n";

export function LandingCountdown() {
  const { t } = useLanguage();
  const { countdown } = useExamCountdown();
  const days = countdown?.days;

  return (
    <span
      className="landing-countdown-parts"
      role="timer"
      aria-label={t("距离 AP Psychology 考试")}
    >
      <span>
        <strong>{days === undefined ? "--" : days}</strong>
        <em>{t("天")}</em>
      </span>
    </span>
  );
}
