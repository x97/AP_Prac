"use client";

import { useRef, useState } from "react";

import { ConceptDialog } from "@/components/ConceptDialog";
import type { Concept } from "@/lib/types";

export function ConceptTags({
  concepts,
  limit = 12,
}: {
  concepts: Concept[];
  limit?: number;
}) {
  const [active, setActive] = useState<Concept | null>(null);
  const [anchorTop, setAnchorTop] = useState<number | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  if (concepts.length === 0) return null;

  function open(concept: Concept) {
    const rect = containerRef.current?.getBoundingClientRect();
    setAnchorTop(rect ? rect.top : null);
    setActive(concept);
  }

  return (
    <>
      <div className="flex flex-wrap gap-1.5" ref={containerRef}>
        {concepts.slice(0, limit).map((concept, index) => (
          <button
            key={`${concept.concept_id}-${index}`}
            type="button"
            className={[
              "badge concept-tag",
              concept.relation_type === "core" ? "badge-core" : "",
              concept.relation_type === "confusable" ? "badge-confusable" : "",
            ].join(" ")}
            onClick={() => open(concept)}
            title="Click for concept details"
            lang="en"
          >
            {concept.canonical_name}
          </button>
        ))}
      </div>
      <ConceptDialog
        concept={active}
        anchorTop={anchorTop}
        onClose={() => setActive(null)}
      />
    </>
  );
}
