"use client";

import { AlertTriangle, Check } from "lucide-react";
import { useEffect, useState } from "react";

import { ReportQuestionModal } from "@/components/ReportQuestionModal";

export function QuestionReportButton({
  questionId,
  attemptId,
  practiceSessionId,
  selectedLabel,
  className = "btn btn-ghost btn-sm",
}: {
  questionId: string;
  attemptId?: string;
  practiceSessionId?: string;
  selectedLabel?: string | null;
  className?: string;
}) {
  const [reported, setReported] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    setReported(false);
    setOpen(false);
  }, [questionId]);

  return (
    <>
      <button
        type="button"
        className={className}
        onClick={() => setOpen(true)}
        disabled={reported}
        aria-label={reported ? "Question reported" : "Report a question"}
      >
        {reported ? (
          <Check size={13} className="text-[var(--success)]" />
        ) : (
          <AlertTriangle size={13} />
        )}
        {reported ? "Reported" : "Report"}
      </button>
      <ReportQuestionModal
        open={open}
        onClose={() => setOpen(false)}
        questionId={questionId}
        attemptId={attemptId}
        practiceSessionId={practiceSessionId}
        selectedLabel={selectedLabel}
        onReported={() => setReported(true)}
      />
    </>
  );
}
