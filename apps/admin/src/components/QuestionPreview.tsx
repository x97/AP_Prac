"use client";

import { Loader2 } from "lucide-react";
import { useEffect, useState } from "react";

import { AdminModal } from "@/components/AdminModal";
import { StarRating } from "@/components/StarRating";
import { apiGet } from "@/lib/api";
import type { QuestionDetail } from "@/lib/types";

export function QuestionPreview({
  questionId,
  subjectId,
  onClose,
}: {
  questionId: string | null;
  subjectId: string;
  onClose: () => void;
}) {
  const [data, setData] = useState<QuestionDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!questionId) return;
    let alive = true;
    setLoading(true);
    setError(null);
    setData(null);
    apiGet<QuestionDetail>(
      `/content/questions/${questionId}?subject=${encodeURIComponent(subjectId)}`,
    )
      .then((value) => alive && setData(value))
      .catch((e: Error) => alive && setError(e.message))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [questionId, subjectId]);

  return (
    <AdminModal
      open={Boolean(questionId)}
      onClose={onClose}
      title="题目预览"
      wide
    >
      {loading ? (
        <div className="grid place-items-center py-16">
          <Loader2 size={22} className="animate-spin text-[var(--primary)]" />
        </div>
      ) : error ? (
        <div className="rounded-xl border border-[#f6d5d2] bg-[var(--danger-soft)] px-3 py-2 text-[12px] text-[var(--danger)]">
          {error}
        </div>
      ) : data ? (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <span className="a-badge a-badge-primary font-mono">
              {data.section} {data.number}
            </span>
            {data.form && <span className="a-badge">{data.form}</span>}
            <StarRating value={data.stars} size={14} label="题目星级" />
          </div>
          {data.context && (
            <div className="whitespace-pre-wrap rounded-xl border border-[var(--line)] bg-[var(--surface-2)] p-4 text-[12.5px] leading-6 text-[var(--muted)]">
              {data.context}
            </div>
          )}
          {data.assets
            .filter((asset) => !asset.option_label)
            .map((asset) => (
              <img
                key={asset.asset_id}
                src={`/${asset.path}`}
                alt="题目图片"
                className="max-h-[360px] max-w-full rounded-xl border border-[var(--line)] bg-white"
              />
            ))}
          <div className="whitespace-pre-wrap text-[14px] leading-7">{data.stem}</div>
          {data.options.length > 0 && (
            <div className="space-y-2">
              {data.options.map((option) => (
                <div
                  key={option.label}
                  className={[
                    "rounded-xl border px-4 py-3",
                    option.is_correct === 1
                      ? "border-[#bfe8d1] bg-[var(--success-soft)]"
                      : "border-[var(--line)]",
                  ].join(" ")}
                >
                  <div className="flex items-start gap-3">
                    <span className="grid h-6 w-6 shrink-0 place-items-center rounded-md border border-[var(--line)] bg-white font-mono text-[11px] font-semibold">
                      {option.label}
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="whitespace-pre-wrap text-[13px] leading-6">
                        {option.content}
                      </div>
                      {option.explanation && (
                        <div className="mt-2 whitespace-pre-wrap text-[11.5px] leading-5 text-[var(--muted)]">
                          {option.explanation}
                        </div>
                      )}
                      {option.ai_explanation && (
                        <div className="mt-2 whitespace-pre-wrap text-[11.5px] leading-5 text-[var(--muted)]">
                          AI：{option.ai_explanation}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
          {data.answer_text && (
            <div className="rounded-xl border border-[var(--line)] bg-[var(--surface-2)] p-4">
              <div className="text-[10.5px] uppercase tracking-[0.12em] text-[var(--faint)]">
                Answer / Rubric
              </div>
              <div className="mt-2 max-h-[320px] overflow-y-auto whitespace-pre-wrap text-[12px] leading-5 text-[var(--muted)]">
                {data.answer_text}
              </div>
            </div>
          )}
        </div>
      ) : null}
    </AdminModal>
  );
}
