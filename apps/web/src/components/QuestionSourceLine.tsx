"use client";

import { useLanguage } from "@/lib/i18n";
import {
  EXAM_PAPER_FALLBACK_LABEL,
  questionSourceParts,
} from "@/lib/questionSource";
import type { QuestionSourceInfo } from "@/lib/types";

export function QuestionSourceLine({
  question,
  className = "",
}: {
  question?: QuestionSourceInfo | null;
  className?: string;
}) {
  const { t } = useLanguage();
  const { primary, secondary } = questionSourceParts(question);
  if (!primary) return null;
  const primaryLabel =
    primary === EXAM_PAPER_FALLBACK_LABEL ? t(primary) : primary;
  return (
    <div
      className={className}
      title={[primaryLabel, secondary].filter(Boolean).join(" · ")}
    >
      <div className="truncate">{primaryLabel}</div>
      {secondary && <div className="truncate opacity-80">{secondary}</div>}
    </div>
  );
}
