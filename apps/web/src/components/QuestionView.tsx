"use client";

import { AlertTriangle, BookOpen, Check, X } from "lucide-react";
import { useEffect, useState } from "react";

import { ReportQuestionModal } from "@/components/ReportQuestionModal";
import type { Question } from "@/lib/types";

export function QuestionView({
  question,
  onSelect,
  disabled = false,
  selectedLabel,
  resultLabel,
  resultTone,
  readOnly = false,
}: {
  question: Question;
  onSelect: (label: string) => void;
  disabled?: boolean;
  selectedLabel?: string | null;
  resultLabel?: string;
  resultTone?: "ok" | "bad" | "neutral";
  readOnly?: boolean;
}) {
  const view = question.feedback ?? question;
  const answered = Boolean(question.answered_at);
  const tone = resultTone ?? (question.is_correct ? "ok" : "bad");
  const options = view.options || [];
  const selected = selectedLabel ?? question.selected_label;
  const stemAssets = (question.assets || []).filter((a) => !a.option_label);
  const [reported, setReported] = useState(false);
  const [reportOpen, setReportOpen] = useState(false);

  useEffect(() => {
    setReported(false);
    setReportOpen(false);
  }, [question.question_id]);

  return (
    <div className="card card-pad">
      <div className="flex items-center justify-between gap-3">
        <span className="pill pill-primary font-mono">Question {question.display_number}</span>
        <div className="flex items-center gap-2">
          <span className="text-[11px] faint font-mono hidden sm:inline">{question.question_id}</span>
          {!readOnly && (
            <button
              className="btn btn-ghost btn-sm"
              onClick={() => setReportOpen(true)}
              disabled={reported}
              aria-label={reported ? "Question reported" : "Report a question"}
            >
              {reported ? <Check size={13} className="text-[var(--success)]" /> : <AlertTriangle size={13} />}
              {reported ? "Reported" : "Report"}
            </button>
          )}
        </div>
      </div>

      {question.context && (
        <div className="mt-4 rounded-xl border border-[var(--line)] bg-[var(--surface-2)] p-4 text-[13.5px] whitespace-pre-wrap muted" lang="en">
          {question.context}
        </div>
      )}

      {stemAssets.length > 0 && (
        <div className="mt-4 space-y-2">
          {stemAssets.map((asset) => (
            <a key={asset.asset_id} href={asset.url} target="_blank" rel="noreferrer">
              <img
                src={asset.url}
                alt="Question image"
                className="max-w-full rounded-xl border border-[var(--line)] bg-white"
                loading="lazy"
              />
            </a>
          ))}
        </div>
      )}

      <div className="question-stem mt-5" lang="en">
        {question.stem}
      </div>

      <div className="mt-5 space-y-2.5">
        {options.map((option) => {
          const isCorrect = answered && Boolean(option.is_correct);
          const isWrong = answered && !option.is_correct && option.label === selected;
          const isDim = answered && !isCorrect && !isWrong;
          const isSelected = !answered && option.label === selected;
          const locked = answered || disabled || readOnly;
          return (
            <div
              key={option.label}
              role="button"
              tabIndex={locked ? -1 : 0}
              aria-disabled={locked}
              className={[
                "option",
                isCorrect ? "correct" : "",
                isWrong ? "wrong" : "",
                isDim ? "dim" : "",
                isSelected ? "selected" : "",
                locked ? "locked" : "",
              ].join(" ")}
              onClick={() => {
                if (!locked) onSelect(option.label);
              }}
              onKeyDown={(e) => {
                if (locked) return;
                if ((e.target as HTMLElement).tagName === "A") return;
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onSelect(option.label);
                }
              }}
            >
              <span className="option-letter">{option.label}</span>
              <span className="min-w-0 flex-1">
                {option.content && (
                  <span className="block whitespace-pre-wrap" lang="en">
                    {option.content}
                  </span>
                )}
                {option.asset_urls?.length > 0 && (
                  <span className="mt-2 flex flex-wrap gap-2">
                    {option.asset_urls.map((url) => (
                      <a
                        key={url}
                        href={url}
                        target="_blank"
                        rel="noreferrer"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <img
                          src={url}
                          alt={`Option ${option.label}`}
                          className="max-h-[190px] rounded-lg border border-[var(--line)] bg-white"
                          loading="lazy"
                        />
                      </a>
                    ))}
                  </span>
                )}
              </span>
              {isCorrect && <Check size={17} className="mt-0.5 shrink-0 text-[var(--success)]" />}
              {isWrong && <X size={17} className="mt-0.5 shrink-0 text-[var(--danger)]" />}
            </div>
          );
        })}
      </div>

      {answered && (
        <div
          className={`feedback mt-5 ${
            tone === "ok" ? "feedback-ok" : tone === "bad" ? "feedback-bad" : ""
          }`}
        >
          <div className="flex items-center gap-2 text-[13.5px] font-semibold">
            {tone === "neutral" ? (
              <>
                <BookOpen size={16} className="text-[var(--primary)]" />
                {resultLabel || "Question Review"}
                {view.correct_label ? `. Correct answer: ${view.correct_label}` : ""}
              </>
            ) : tone === "ok" ? (
              <>
                <Check size={16} className="text-[var(--success)]" />
                {resultLabel || "Correct"}
              </>
            ) : (
              <>
                <X size={16} className="text-[var(--danger)]" />
                {resultLabel || (selected ? "Incorrect" : "Not answered")}
                {view.correct_label ? `. Correct answer: ${view.correct_label}` : ""}
              </>
            )}
          </div>
          {view.explanation && (
            <p className="mt-3 text-[13.5px] leading-6 whitespace-pre-wrap" lang="en">
              {view.explanation}
            </p>
          )}
          {!view.explanation && (
            <p className="mt-2 text-[13px] muted">No explanation is available for this question.</p>
          )}
        </div>
      )}

      <ReportQuestionModal
        open={reportOpen}
        onClose={() => setReportOpen(false)}
        questionId={question.question_id}
        onReported={() => setReported(true)}
      />
    </div>
  );
}
