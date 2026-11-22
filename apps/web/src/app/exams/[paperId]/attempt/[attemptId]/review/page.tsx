"use client";

import { ArrowLeft, RotateCcw } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { ConceptTags } from "@/components/ConceptTags";
import { FrqReviewCard } from "@/components/FrqReviewCard";
import { QuestionView } from "@/components/QuestionView";
import { TeacherPromoCard } from "@/components/TeacherPromoCard";
import { apiGet } from "@/lib/api";
import type { AttemptReview, Question } from "@/lib/types";

const FILTERS = [
  { key: "all", label: "All" },
  { key: "wrong", label: "Wrong" },
  { key: "flagged", label: "Marked for Review" },
  { key: "unanswered", label: "Unanswered" },
] as const;

type FilterKey = (typeof FILTERS)[number]["key"];

export default function ReviewPage() {
  const params = useParams<{ paperId: string; attemptId: string }>();
  const { paperId, attemptId } = params;
  const [data, setData] = useState<AttemptReview | null>(null);
  const [filter, setFilter] = useState<FilterKey>("all");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    apiGet<AttemptReview>(`/attempts/${attemptId}/review`)
      .then(setData)
      .catch((e: Error) => setError(e.message));
  }, [attemptId]);

  useEffect(() => {
    load();
  }, [load]);

  const mcqItems = useMemo(() => {
    if (!data) return [];
    const normalized: Question[] = data.mcq_items.map((q) => ({
      ...q,
      answered_at: q.answered_at || new Date().toISOString(),
    }));
    if (filter === "wrong") {
      return normalized.filter((q) => Boolean(q.selected_label) && q.is_correct === false);
    }
    if (filter === "flagged") return normalized.filter((q) => q.flagged);
    if (filter === "unanswered") return normalized.filter((q) => !q.selected_label);
    return normalized;
  }, [data, filter]);

  if (error) return <div className="feedback feedback-bad">{error}</div>;
  if (!data) return <div className="skeleton h-96 w-full" />;

  const isAbandoned = data.attempt.status === "abandoned";
  const score = data.attempt.mcq_score ?? 0;
  const total = data.attempt.mcq_total ?? 0;
  const mcqAnswered = data.mcq_items.filter((q) => q.selected_label).length;
  const mcqCorrect = data.mcq_items.filter((q) => q.is_correct).length;
  const accuracy = total ? Math.round((score / total) * 100) : 0;
  const answeredAccuracy = mcqAnswered
    ? Math.round((mcqCorrect / mcqAnswered) * 100)
    : 0;
  const hasMcq = data.attempt.mode !== "frq";
  const hasFrq = data.attempt.mode !== "mcq";
  const frqTotal = data.attempt.frq_total ?? 0;
  const frqScore = data.attempt.frq_score;

  return (
    <div>
      <div className="top-row-clear flex items-center justify-between gap-3 mb-4">
        <Link href={`/exams/${paperId}`} className="btn btn-ghost btn-sm -ml-2">
          <ArrowLeft size={14} /> Back to Paper
        </Link>
        <Link href={`/exams/${paperId}`} className="btn btn-sm">
          <RotateCcw size={14} /> Try Again
        </Link>
      </div>

      <div className="card card-pad mb-5">
        <div className="eyebrow">
          Review ·{" "}
          {isAbandoned
            ? "Ended Early"
            : data.attempt.status === "graded"
              ? "Completed"
              : data.attempt.status === "awaiting_self_grade"
                ? "Awaiting Self-Grade"
                : "Completed"}
        </div>
        <div className="flex flex-wrap items-end gap-6 mt-2">
          {hasMcq && (
            <>
              {isAbandoned ? (
                <>
                  <div>
                    <div className="stat-value">
                      {mcqAnswered}
                      <span className="text-[15px] muted font-normal"> / {total}</span>
                    </div>
                    <div className="stat-label">MCQ Answered</div>
                  </div>
                  <div>
                    <div className="stat-value">{mcqCorrect}</div>
                    <div className="stat-label">Correct</div>
                  </div>
                  <div>
                    <div className="stat-value">{answeredAccuracy}%</div>
                    <div className="stat-label">Answered Accuracy</div>
                  </div>
                </>
              ) : (
                <>
                  <div>
                    <div className="stat-value">
                      {score}
                      <span className="text-[15px] muted font-normal"> / {total}</span>
                    </div>
                    <div className="stat-label">MCQ Score</div>
                  </div>
                  <div>
                    <div className="stat-value">{accuracy}%</div>
                    <div className="stat-label">MCQ Accuracy</div>
                  </div>
                </>
              )}
            </>
          )}
          {hasFrq && (
            <div>
              <div className="stat-value">
                {frqScore ?? "—"}
                <span className="text-[15px] muted font-normal"> / {frqTotal || "—"}</span>
              </div>
              <div className="stat-label">FRQ Self-Grade</div>
            </div>
          )}
          {hasMcq && (
            <div>
              <div className="stat-value">{data.mcq_items.filter((q) => q.flagged).length}</div>
              <div className="stat-label">Marked for Review</div>
            </div>
          )}
        </div>
        <p className="text-[11px] faint mt-4">
          {isAbandoned
            ? "This exam ended early. Answers are for review only and are not counted in the wrong book or completion stats."
            : "Raw scores are not AP 1–5 estimates. Wrong MCQs are added to your wrong book; FRQ self-grading is for study reference only."}
        </p>
      </div>

      <TeacherPromoCard variant="result" />

      {hasMcq && (
        <>
          <div className="flex gap-2 mb-4 flex-wrap">
            {FILTERS.map((f) => (
              <button
                key={f.key}
                className={filter === f.key ? "btn btn-sm btn-primary" : "btn btn-sm"}
                onClick={() => setFilter(f.key)}
              >
                {f.label}
              </button>
            ))}
            <span className="pill self-center">{mcqItems.length} questions</span>
          </div>

          <div className="space-y-5">
            {mcqItems.map((q) => (
              <div key={q.question_id}>
                <QuestionView question={q} onSelect={() => undefined} disabled />
                {q.feedback?.concepts && q.feedback.concepts.length > 0 && (
                  <div className="card card-pad mt-2">
                    <div className="text-[11px] faint mb-2">
                      Related Concepts (click for details)
                    </div>
                    <ConceptTags concepts={q.feedback.concepts} limit={8} />
                  </div>
                )}
              </div>
            ))}
            {mcqItems.length === 0 && <div className="card empty">No questions in this filter.</div>}
          </div>
        </>
      )}

      {hasFrq && (
        <div className={hasMcq ? "mt-8" : ""}>
          <div className="flex items-center justify-between mb-3">
            <h2 className="h2">FRQ · Self-Grade</h2>
            <span className="pill">
              {fracText(frqScore, frqTotal)}
            </span>
          </div>
          <div className="space-y-5">
            {data.frq_items.map((item) => (
              <FrqReviewCard
                key={item.question_id}
                item={item}
                attemptId={attemptId}
                onChanged={load}
                readOnly={isAbandoned}
              />
            ))}
            {data.frq_items.length === 0 && (
              <div className="card empty">FRQ was not submitted or has no questions.</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function fracText(score: number | null, total: number) {
  if (score === null || score === undefined) return `Not graded / ${total || "—"}`;
  return `Self-graded ${score} / ${total || "—"}`;
}
