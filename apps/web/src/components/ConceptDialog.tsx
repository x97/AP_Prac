"use client";

import { Sparkles, X } from "lucide-react";
import { useEffect, useRef } from "react";
import type { CSSProperties } from "react";

import type { Concept } from "@/lib/types";

const REL_LABEL: Record<string, string> = {
  core: "Core Concept",
  supporting: "Related Concept",
  confusable: "Confusable Concept",
  kp: "Concept",
};

export function ConceptDialog({
  concept,
  anchorTop,
  onClose,
}: {
  concept: Concept | null;
  anchorTop?: number | null;
  onClose: () => void;
}) {
  const cardRef = useRef<HTMLDivElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!concept) return;
    closeRef.current?.focus({ preventScroll: true });

    function onPointerDown(event: MouseEvent) {
      if (!cardRef.current?.contains(event.target as Node)) {
        // Close only the knowledge card; do not also trigger the question
        // modal's backdrop or an underlying button.
        event.stopPropagation();
        onClose();
      }
    }
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("mousedown", onPointerDown, true);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onPointerDown, true);
      document.removeEventListener("keydown", onKey);
    };
  }, [concept, onClose]);

  if (!concept) return null;

  let positionStyle: CSSProperties | undefined;
  if (anchorTop != null && typeof window !== "undefined") {
    const preferred = anchorTop - 24;
    const maxTop = Math.max(12, window.innerHeight - 380);
    const top = Math.min(Math.max(12, preferred), maxTop);
    const maxHeight = Math.max(
      220,
      Math.min(window.innerHeight * 0.82, window.innerHeight - top - 16),
    );
    positionStyle = {
      top: `${top}px`,
      transform: "translateX(-50%)",
      maxHeight: `${maxHeight}px`,
    };
  }

  return (
    <div
      ref={cardRef}
      className="concept-popover"
      style={positionStyle}
      role="dialog"
      aria-modal="false"
      aria-label="Concept details"
    >
      <div className="modal-head">
        <div className="text-[11px] faint">Concept Details</div>
        <button
          ref={closeRef}
          type="button"
          className="btn btn-ghost btn-sm"
          onClick={onClose}
          aria-label="Close concept details"
        >
          <X size={16} />
        </button>
      </div>

      <div className="flex items-start justify-between gap-3">
        <h3 className="concept-name text-[22px]" lang="en">
          {concept.canonical_name}
        </h3>
        {concept.relation_type && (
          <span
            className={
              concept.relation_type === "core"
                ? "badge badge-core"
                : concept.relation_type === "confusable"
                  ? "badge badge-confusable"
                  : "badge"
            }
          >
            {REL_LABEL[concept.relation_type] || concept.relation_type}
          </span>
        )}
      </div>

      {concept.plain_en && (
        <p className="mt-4 text-[15px] leading-7" lang="en">
          {concept.plain_en}
        </p>
      )}
      {!concept.plain_en && !concept.definition_quote && (
        <p className="mt-4 text-[13px] muted">No detailed definition is available yet.</p>
      )}

      {concept.definition_quote && (
        <blockquote
          className="mt-4 rounded-xl border border-[var(--line)] bg-[var(--surface-2)] p-4 text-[13px] leading-6 muted"
          lang="en"
        >
          {concept.definition_quote}
        </blockquote>
      )}

      {concept.option_label && (
        <div className="mt-3 text-[11.5px] text-[var(--accent)]">
          Option {concept.option_label}
        </div>
      )}

      {(concept.book_title || concept.section_heading) && (
        <div className="mt-4 flex items-center gap-1.5 text-[10.5px] faint">
          <Sparkles size={11} />
          <span>
            {[concept.book_title, concept.section_heading]
              .filter(Boolean)
              .join(" · ")}
          </span>
        </div>
      )}
    </div>
  );
}
