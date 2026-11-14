"use client";

import { Check, ChevronDown, Loader2 } from "lucide-react";
import { useState } from "react";

import { apiPost } from "@/lib/api";
import type { FrqReviewItem } from "@/lib/types";

export function FrqReviewCard({
  item,
  attemptId,
  onChanged,
  readOnly = false,
}: {
  item: FrqReviewItem;
  attemptId: string;
  onChanged: () => void;
  readOnly?: boolean;
}) {
  const [scores, setScores] = useState<Record<string, number>>(() => {
    const map: Record<string, number> = {};
    item.scores.forEach((s) => {
      map[s.part_id] = s.points;
    });
    return map;
  });
  const [saving, setSaving] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [showGuide, setShowGuide] = useState(false);
  const [showNotes, setShowNotes] = useState(false);

  const parts = item.guidelines.parts;
  const maxTotal = parts.reduce((sum, p) => sum + (p.max_points || 0), 0);
  const currentTotal = parts.reduce((sum, p) => sum + (scores[p.part_id] ?? 0), 0);
  const allScored = parts.every((p) => scores[p.part_id] !== undefined);

  async function setScore(partId: string, points: number) {
    const next = { ...scores, [partId]: points };
    setScores(next);
    setSaving(partId);
    setMessage(null);
    try {
      await apiPost(`/attempts/${attemptId}/frq-scores`, {
        scores: [{ question_id: item.question_id, part_id: partId, points }],
      });
      setMessage("Saved");
      if (parts.every((p) => next[p.part_id] !== undefined)) {
        onChanged();
      }
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(null);
    }
  }

  return (
    <div className="card card-pad">
      <div className="flex items-start justify-between gap-3">
        <div>
          <span className="pill pill-primary font-mono">FRQ {item.display_number}</span>
          <div className="text-[11px] faint mt-1">
            {item.guidelines.rubric?.format || "rubric"} · Max {maxTotal}
            {item.guidelines.rubric?.total_points !== undefined &&
              item.guidelines.rubric.total_points !== maxTotal &&
              ` · Rubric total ${item.guidelines.rubric.total_points}`}
          </div>
        </div>
        <span className="text-[12px] muted font-mono">
          {readOnly ? `Max ${maxTotal}` : `Self-graded ${currentTotal}/${maxTotal}`}
        </span>
      </div>

      {maxTotal < 7 && (
        <div className="feedback feedback-bad mt-3 text-[12px] text-[var(--danger)]">
          This rubric is incomplete ({maxTotal}/7). Self-grading is reference only.
        </div>
      )}

      {item.assets?.filter((a) => !a.option_label).length > 0 && (
        <div className="mt-4 space-y-2">
          {item.assets
            .filter((a) => !a.option_label)
            .map((a) => (
              <a key={a.asset_id} href={a.url} target="_blank" rel="noreferrer">
                <img
                  src={a.url}
                  alt="FRQ material"
                  className="max-w-full rounded-xl border border-[var(--line)] bg-white"
                />
              </a>
            ))}
        </div>
      )}

      <div className="mt-4 max-h-[38vh] overflow-y-auto rounded-xl border border-[var(--line)] bg-[var(--surface-2)] p-4 whitespace-pre-wrap text-[13.5px] leading-6" lang="en">
        {item.stem}
      </div>

      <div className="mt-4">
        <div className="text-[12px] muted">Your Response</div>
        <div className="mt-1 rounded-xl border border-[var(--line)] p-4 text-[13.5px] leading-6 whitespace-pre-wrap min-h-[80px]" lang="en">
          {item.frq_text?.trim() || "Not answered"}
        </div>
      </div>

      <div className="mt-5">
        <div className="flex items-center justify-between">
          <h3 className="text-[13px] font-semibold">
            {readOnly ? "Rubric" : "Self-Grade with Rubric"}
          </h3>
          <span className="text-[11px] faint">
            {readOnly ? "Ended early; no self-grade submitted" : message || (allScored ? "Completed" : "Select points for each criterion")}
          </span>
        </div>

        <div className="mt-3 space-y-3">
          {parts.map((part) => {
            const value = scores[part.part_id];
            return (
              <div key={part.part_id} className="rounded-xl border border-[var(--line)] p-3.5">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <span className="font-mono text-[12px] text-[var(--primary)]">{part.label}</span>
                    <span className="ml-2 text-[13px] font-medium">{part.title || "Scoring point"}</span>
                  </div>
                  <span className="pill">{part.max_points} pts</span>
                </div>

                {part.criteria_json && part.criteria_json.length > 0 ? (
                  <ul className="mt-2 space-y-1">
                    {part.criteria_json.map((c, i) => (
                      <li key={i} className="text-[12px] muted leading-5 flex gap-2">
                        <span className="font-mono text-[10px] text-[var(--faint)] mt-0.5">
                          {c.points}
                        </span>
                        <span lang="en">{c.criterion}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  part.criteria && (
                    <p className="mt-2 text-[12px] muted whitespace-pre-wrap" lang="en">
                      {part.criteria}
                    </p>
                  )
                )}

                {!readOnly && (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {Array.from({ length: part.max_points + 1 }, (_, p) => (
                      <button
                        key={p}
                        className={[
                          "h-8 min-w-8 px-2 rounded-lg border text-[12px] font-mono",
                          value === p
                            ? "bg-[var(--primary)] border-[var(--primary)] text-white"
                            : "bg-[var(--surface)] border-[var(--line)] text-[var(--muted)]",
                        ].join(" ")}
                        onClick={() => setScore(part.part_id, p)}
                        disabled={saving === part.part_id}
                      >
                        {saving === part.part_id && value === p ? (
                          <Loader2 size={12} className="animate-spin mx-auto" />
                        ) : p === 0 ? (
                          "0"
                        ) : (
                          p
                        )}
                      </button>
                    ))}
                    {value !== undefined && (
                      <Check size={15} className="self-center text-[var(--success)]" />
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {item.guidelines.rubric?.general_considerations && (
          <button className="btn btn-sm" onClick={() => setShowGuide((v) => !v)}>
            <ChevronDown size={13} /> General Scoring Notes
          </button>
        )}
        {item.guidelines.answer_text && (
          <button className="btn btn-sm" onClick={() => setShowNotes((v) => !v)}>
            <ChevronDown size={13} /> Scoring Notes / Sample Response
          </button>
        )}
      </div>

      {showGuide && item.guidelines.rubric?.general_considerations && (
        <div className="mt-3 rounded-xl border border-[var(--line)] p-4 text-[12px] leading-5 whitespace-pre-wrap muted">
          {item.guidelines.rubric.general_considerations}
        </div>
      )}
      {showNotes && item.guidelines.answer_text && (
        <div className="mt-3 max-h-[50vh] overflow-y-auto rounded-xl border border-[var(--line)] p-4 text-[12px] leading-5 whitespace-pre-wrap muted" lang="en">
          {item.guidelines.answer_text}
        </div>
      )}

      <div className="mt-4 flex items-center justify-between border-t border-[var(--line)] pt-3">
        <span className="text-[11px] faint">
          {readOnly ? "FRQ self-grading was not completed for this exam." : "Self-grading is for reference only and is not an official score."}
        </span>
        <span className="text-[12px] font-medium">
          {readOnly ? `Max ${maxTotal}` : `${currentTotal} / ${maxTotal}`}
        </span>
      </div>
    </div>
  );
}
