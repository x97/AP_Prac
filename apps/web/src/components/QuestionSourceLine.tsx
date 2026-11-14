import { questionSourceParts } from "@/lib/questionSource";
import type { QuestionSourceInfo } from "@/lib/types";

export function QuestionSourceLine({
  question,
  className = "",
}: {
  question?: QuestionSourceInfo | null;
  className?: string;
}) {
  const { primary, secondary } = questionSourceParts(question);
  if (!primary) return null;
  return (
    <div
      className={className}
      title={[primary, secondary].filter(Boolean).join(" · ")}
    >
      <div className="truncate">{primary}</div>
      {secondary && <div className="truncate opacity-80">{secondary}</div>}
    </div>
  );
}
