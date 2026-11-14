"use client";

import { AlertTriangle, Check, CheckCircle2, Loader2, Send } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";

import { apiPost } from "@/lib/api";
import { Modal } from "@/components/Modal";

const REASONS = [
  {
    value: "wrong_answer",
    label: "Wrong answer",
    hint: "The correct option or answer key looks wrong.",
  },
  {
    value: "bad_explanation",
    label: "Unclear explanation",
    hint: "The explanation is confusing, incomplete, or contradicts the answer.",
  },
  {
    value: "image_missing",
    label: "Image problem",
    hint: "A figure, table, or option image is missing or unreadable.",
  },
  {
    value: "typo",
    label: "Typo or formatting",
    hint: "Spelling, punctuation, or layout needs a fix.",
  },
  {
    value: "other",
    label: "Something else",
    hint: "Tell us what you noticed in the details below.",
  },
] as const;

type ReportReason = (typeof REASONS)[number]["value"];

export function ReportQuestionModal({
  open,
  onClose,
  questionId,
  attemptId,
  practiceSessionId,
  selectedLabel,
  onReported,
}: {
  open: boolean;
  onClose: () => void;
  questionId: string;
  attemptId?: string;
  practiceSessionId?: string;
  selectedLabel?: string | null;
  onReported: () => void;
}) {
  const [reason, setReason] = useState<ReportReason | null>(null);
  const [detail, setDetail] = useState("");
  const [status, setStatus] = useState<"idle" | "submitting" | "success" | "error">("idle");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setReason(null);
    setDetail("");
    setStatus("idle");
    setError(null);
  }, [open, questionId]);

  const submitting = status === "submitting";
  const canSubmit =
    Boolean(reason) && !submitting && (reason !== "other" || detail.trim().length > 0);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!reason || !canSubmit) return;
    setStatus("submitting");
    setError(null);
    try {
      await apiPost("/question-reports", {
        question_id: questionId,
        reason,
        detail: detail.trim() || undefined,
        attempt_id: attemptId,
        practice_session_id: practiceSessionId,
        selected_label: selectedLabel || undefined,
      });
      setStatus("success");
      onReported();
    } catch (err) {
      setStatus("error");
      setError(err instanceof Error ? err.message : "Report failed. Please try again.");
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={status === "success" ? "Report sent" : "Report a question"}
      dismissible={!submitting}
    >
      {status === "success" ? (
        <div className="px-2 py-6 text-center">
          <div className="mx-auto grid h-14 w-14 place-items-center rounded-full bg-[var(--success-soft)] text-[var(--success)]">
            <CheckCircle2 size={28} />
          </div>
          <h3 className="mt-4 text-[18px] font-semibold tracking-[-0.01em]">Thanks for the heads-up</h3>
          <p className="mx-auto mt-2 max-w-[360px] text-[13px] leading-6 muted">
            The content team will review this question. You can keep practicing while we check it.
          </p>
          <button type="button" className="btn btn-primary mt-5" onClick={onClose}>
            Done
          </button>
        </div>
      ) : (
        <form onSubmit={submit} className="space-y-5">
          <div className="flex items-start gap-3 rounded-2xl border border-[var(--line)] bg-[var(--surface-2)] p-4">
            <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-[var(--accent-soft)] text-[var(--accent)]">
              <AlertTriangle size={18} />
            </div>
            <div className="min-w-0">
              <p className="text-[13.5px] font-semibold">Help us improve this question</p>
              <p className="mt-1 text-[12px] leading-5 muted">
                Your report goes directly to the content team. Please do not include personal
                information.
              </p>
            </div>
          </div>

          <div>
            <div className="flex items-baseline justify-between gap-3">
              <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[var(--faint)]">
                What is the issue?
              </span>
              <span className="text-[11px] faint">Required</span>
            </div>
            <div
              className="mt-2 grid gap-2 sm:grid-cols-2"
              role="radiogroup"
              aria-label="Report reason"
            >
              {REASONS.map((item) => {
                const selected = reason === item.value;
                return (
                  <button
                    key={item.value}
                    type="button"
                    role="radio"
                    aria-checked={selected}
                    onClick={() => setReason(item.value)}
                    className={[
                      "rounded-xl border p-3 text-left transition",
                      selected
                        ? "border-[var(--primary)] bg-[var(--primary-soft)] shadow-[0_0_0_1px_var(--primary)]"
                        : "border-[var(--line)] bg-[var(--surface)] hover:border-[var(--primary)] hover:bg-[var(--surface-2)]",
                    ].join(" ")}
                  >
                    <span className="flex items-center gap-2 text-[13px] font-medium">
                      <span
                        className={[
                          "grid h-4 w-4 place-items-center rounded-full border",
                          selected
                            ? "border-[var(--primary)] bg-[var(--primary)] text-white"
                            : "border-[var(--line)]",
                        ].join(" ")}
                      >
                        {selected && <Check size={11} strokeWidth={3} />}
                      </span>
                      {item.label}
                    </span>
                    <span className="mt-1 block pl-6 text-[11.5px] leading-5 muted">
                      {item.hint}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          <div>
            <div className="flex items-baseline justify-between gap-3">
              <label
                htmlFor="report-detail"
                className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[var(--faint)]"
              >
                Details
              </label>
              <span className="text-[11px] faint">{detail.length} / 2000</span>
            </div>
            <textarea
              id="report-detail"
              className="input mt-2 min-h-[112px] resize-y text-[13px] leading-6"
              maxLength={2000}
              value={detail}
              onChange={(event) => setDetail(event.target.value)}
              placeholder="Optional. Include the option letter or the part of the explanation that looks wrong."
            />
          </div>

          {error && (
            <div className="rounded-xl border border-[#f6d5d2] bg-[var(--danger-soft)] px-3.5 py-3 text-[12px] text-[var(--danger)]">
              {error}
            </div>
          )}

          <div className="flex items-center justify-end gap-2 border-t border-[var(--line)] pt-4">
            <button type="button" className="btn" onClick={onClose} disabled={submitting}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary min-w-[124px]" disabled={!canSubmit}>
              {submitting ? (
                <Loader2 size={15} className="animate-spin" />
              ) : (
                <Send size={15} />
              )}
              {submitting ? "Sending…" : "Send report"}
            </button>
          </div>
        </form>
      )}
    </Modal>
  );
}
