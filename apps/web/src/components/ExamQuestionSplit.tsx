"use client";

import { Check, Flag } from "lucide-react";
import { useEffect, useRef, useState, type CSSProperties } from "react";

import { Modal } from "@/components/Modal";
import { QuestionReportButton } from "@/components/QuestionReportButton";
import type { Question } from "@/lib/types";

const MIN_SPLIT = 32;
const MAX_SPLIT = 72;

export function ExamQuestionSplit({
  question,
  attemptId,
  selectedLabel,
  onSelect,
  disabled = false,
  flagged = false,
  onToggleFlag,
}: {
  question: Question;
  attemptId: string;
  selectedLabel?: string | null;
  onSelect: (label: string) => void;
  disabled?: boolean;
  flagged?: boolean;
  onToggleFlag?: () => void;
}) {
  const [split, setSplit] = useState(54);
  const [previewImage, setPreviewImage] = useState<{
    url: string;
    alt: string;
  } | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const draggingRef = useRef(false);

  useEffect(() => {
    function onMove(event: PointerEvent) {
      if (!draggingRef.current) return;
      const rect = containerRef.current?.getBoundingClientRect();
      if (!rect) return;
      const percent = ((event.clientX - rect.left) / rect.width) * 100;
      setSplit(Math.min(MAX_SPLIT, Math.max(MIN_SPLIT, percent)));
    }
    function onUp() {
      if (!draggingRef.current) return;
      draggingRef.current = false;
      document.body.classList.remove("exam-resizing");
    }
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
    window.addEventListener("pointercancel", onUp);
    return () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
      window.removeEventListener("pointercancel", onUp);
      document.body.classList.remove("exam-resizing");
    };
  }, []);

  const stemAssets = (question.assets || []).filter((asset) => !asset.option_label);
  const options = question.options || [];

  return (
    <div
      ref={containerRef}
      className="exam-split"
      style={{ "--exam-split": `${split}%` } as CSSProperties}
    >
      <section className="exam-split-pane exam-split-left" aria-label="Question">
        <div className="flex items-center justify-between gap-3">
          <span className="pill pill-primary font-mono">
            Question {question.display_number}
          </span>
          <div className="flex flex-wrap items-center justify-end gap-2">
            {question.context && (
              <span className="text-[10.5px] faint uppercase tracking-[0.12em]">
                Stimulus
              </span>
            )}
            <QuestionReportButton
              questionId={question.question_id}
              attemptId={attemptId}
              selectedLabel={selectedLabel}
            />
          </div>
        </div>

        <div className="question-stem mt-5" lang="en">
          {question.stem}
        </div>

        {question.context && (
          <div
            className="mt-4 rounded-xl border border-[var(--line)] bg-[var(--surface-2)] p-4 text-[13.5px] leading-6 whitespace-pre-wrap muted"
            lang="en"
          >
            {question.context}
          </div>
        )}

        {stemAssets.length > 0 && (
          <div className="exam-question-assets">
            {stemAssets.map((asset) => (
              <figure key={asset.asset_id} className="exam-question-figure">
                <button
                  type="button"
                  className="exam-question-asset"
                  onClick={() =>
                    setPreviewImage({ url: asset.url, alt: asset.description || "Question material" })
                  }
                  aria-label="Enlarge question image"
                  title="Click to enlarge"
                >
                  <img
                    src={asset.url}
                    alt={asset.description || "Question material"}
                    loading="lazy"
                  />
                </button>
              </figure>
            ))}
          </div>
        )}
      </section>

      <div
        className="exam-split-divider"
        role="separator"
        aria-orientation="vertical"
        aria-label="Resize question and answer panes"
        aria-valuemin={MIN_SPLIT}
        aria-valuemax={MAX_SPLIT}
        aria-valuenow={Math.round(split)}
        tabIndex={0}
        onPointerDown={(event) => {
          event.preventDefault();
          draggingRef.current = true;
          document.body.classList.add("exam-resizing");
        }}
        onKeyDown={(event) => {
          if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
            event.preventDefault();
            event.stopPropagation();
            setSplit((value) =>
              Math.min(
                MAX_SPLIT,
                Math.max(MIN_SPLIT, value + (event.key === "ArrowRight" ? 2 : -2)),
              ),
            );
          }
        }}
      >
        <span className="exam-split-grip" aria-hidden="true" />
      </div>

      <section className="exam-split-pane exam-split-right" aria-label="Answer options">
        <div className="flex items-center justify-between gap-2">
          <span className="text-[10.5px] faint uppercase tracking-[0.12em]">
            Answer Options
          </span>
          {onToggleFlag && (
            <button
              type="button"
              className="btn btn-ghost btn-sm shrink-0"
              onClick={onToggleFlag}
              disabled={disabled}
              aria-pressed={flagged}
            >
              <Flag
                size={14}
                className={flagged ? "text-[var(--accent)]" : ""}
              />
              <span className="text-[11.5px]">
                {flagged ? "Marked for Review" : "Mark for Review"}
              </span>
            </button>
          )}
        </div>
        <div className="text-[10.5px] faint mt-1 mb-3">Select one answer</div>
        <div className="space-y-2.5">
          {options.map((option) => {
            const isSelected = option.label === selectedLabel;
            const locked = disabled;
            const optionAssets = (question.assets || []).filter(
              (asset) => asset.option_label === option.label,
            );
            return (
              <div
                key={option.label}
                role="button"
                tabIndex={locked ? -1 : 0}
                aria-disabled={locked}
                aria-pressed={isSelected}
                className={["option", isSelected ? "selected" : "", locked ? "locked" : ""].join(
                  " ",
                )}
                onClick={() => {
                  if (!locked) onSelect(option.label);
                }}
                onKeyDown={(event) => {
                  if (locked) return;
                  if (["A", "BUTTON"].includes((event.target as HTMLElement).tagName)) return;
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
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
                  {optionAssets.length > 0 && (
                    <span className="mt-2 flex flex-col gap-2">
                      {optionAssets.map((asset) => (
                        <span key={asset.asset_id} className="option-image-wrap">
                          <button
                            type="button"
                            className="option-image-button"
                            onClick={(event) => {
                              event.stopPropagation();
                              setPreviewImage({
                                url: asset.url,
                                alt: `Option ${option.label}`,
                              });
                            }}
                            aria-label={`Enlarge option ${option.label} image`}
                          >
                            <img
                              src={asset.url}
                              alt={asset.description || `Option ${option.label}`}
                              className="max-h-[190px] rounded-lg border border-[var(--line)] bg-white"
                              loading="lazy"
                            />
                          </button>
                        </span>
                      ))}
                    </span>
                  )}
                </span>
                {isSelected && (
                  <Check size={17} className="mt-0.5 shrink-0 text-[var(--primary)]" />
                )}
              </div>
            );
          })}
        </div>
      </section>

      <Modal
        open={Boolean(previewImage)}
        onClose={() => setPreviewImage(null)}
        title="Question image"
        wide
      >
        {previewImage && (
          <img
            className="exam-image-full"
            src={previewImage.url}
            alt={`${previewImage.alt} enlarged`}
          />
        )}
      </Modal>
    </div>
  );
}
