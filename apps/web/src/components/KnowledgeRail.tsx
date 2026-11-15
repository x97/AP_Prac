"use client";

import {
  BookOpen,
  ChevronDown,
  ChevronUp,
  Lightbulb,
  Sparkles,
} from "lucide-react";
import { useEffect, useState } from "react";

import { useLanguage } from "@/lib/i18n";
import type { Concept } from "@/lib/types";

const REL_LABEL: Record<string, string> = {
  core: "Core",
  supporting: "Related",
  confusable: "Confusable",
  kp: "Concept",
};

const REL_CLASS: Record<string, string> = {
  core: "badge badge-core",
  confusable: "badge badge-confusable",
};

function ConceptItem({ concept }: { concept: Concept }) {
  return (
    <div className="concept">
      <div className="flex items-start justify-between gap-2">
        <div className="concept-name" lang="en">
          {concept.canonical_name}
        </div>
        {concept.relation_type && (
          <span className={REL_CLASS[concept.relation_type] || "badge"}>
            {REL_LABEL[concept.relation_type] || concept.relation_type}
          </span>
        )}
      </div>
      {concept.plain_en && (
        <div className="concept-def" lang="en">
          {concept.plain_en}
        </div>
      )}
      {concept.definition_quote && (
        <div className="mt-2 text-[12px] leading-5 muted line-clamp-4" lang="en">
          {concept.definition_quote}
        </div>
      )}
      {(concept.section_heading || concept.book_title) && (
        <div className="mt-2 flex items-center gap-1.5 text-[10.5px] faint">
          <Sparkles size={11} />
          <span className="truncate">
            {[concept.book_title, concept.section_heading].filter(Boolean).join(" · ")}
          </span>
        </div>
      )}
      {concept.relation_type === "confusable" && concept.option_label && (
        <div className="mt-1 text-[10.5px] text-[var(--accent)]">
          Option {concept.option_label}
        </div>
      )}
    </div>
  );
}

export function KnowledgeRail({
  concepts,
  topicConcepts,
  topicTitle,
  topicInferred = false,
  topicLoading = false,
  answered,
  questionId,
}: {
  concepts: Concept[];
  topicConcepts: Concept[];
  topicTitle?: string;
  topicInferred?: boolean;
  topicLoading?: boolean;
  answered: boolean;
  questionId: string;
}) {
  const { t } = useLanguage();
  const [tab, setTab] = useState<"question" | "topic">("question");
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    setTab("question");
    setCollapsed(false);
    // Only reset when the user moves to another question.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [questionId]);

  const questionList = answered ? concepts : [];
  const list = tab === "question" ? questionList : topicConcepts;
  const count = collapsed
    ? answered
      ? concepts.length
      : topicConcepts.length
    : list.length;

  return (
    <div className="rail-card card">
      <div className="flex items-center justify-between gap-2">
        <button
          type="button"
          className="rail-head-btn"
          onClick={() => setCollapsed((value) => !value)}
          aria-expanded={!collapsed}
        >
          <BookOpen size={15} className="text-[var(--primary)]" />
          <span>Concepts</span>
          {collapsed ? <ChevronDown size={15} /> : <ChevronUp size={15} />}
        </button>
        <span className="pill">{count}</span>
      </div>

      {collapsed && (
        <div className="rail-hint">
          <Lightbulb size={13} className="shrink-0 text-[var(--accent)]" />
          <span>
            {answered
              ? "Question concepts are ready. Expand to view."
              : "Question concepts appear after you answer."}
          </span>
        </div>
      )}

      {!collapsed && (
        <>
          <div className="rail-tabs">
            <button
              type="button"
              className={tab === "question" ? "rail-tab active" : "rail-tab"}
              onClick={() => setTab("question")}
            >
              Question Concepts
              <span>{answered ? concepts.length : "after answer"}</span>
            </button>
            <button
              type="button"
              className={tab === "topic" ? "rail-tab active" : "rail-tab"}
              onClick={() => setTab("topic")}
            >
              Topic Concepts
              <span>{topicLoading ? "…" : topicConcepts.length}</span>
            </button>
          </div>

          {tab === "topic" && !topicLoading && topicTitle && (
            <div className="mb-1 mt-2 font-mono text-[10px] text-[var(--muted)]">
              {topicTitle}
              {topicInferred && (
                <span className="ml-1.5 text-[var(--accent)]">{t("近似匹配")}</span>
              )}
            </div>
          )}

          {tab === "question" && !answered && (
            <div className="rail-empty-hint">
              <Lightbulb size={16} className="text-[var(--accent)]" />
              <div>
                <div className="text-[12.5px] font-medium">Answer first, then review concepts</div>
                <p className="text-[11.5px] muted mt-1 leading-5">
                  After you answer, this tab shows the core, related, and confusable concepts for this question.
                </p>
                {topicConcepts.length > 0 && (
                  <button
                    type="button"
                    className="btn btn-sm btn-ghost mt-2"
                    onClick={() => setTab("topic")}
                  >
                    View Topic Concepts
                  </button>
                )}
              </div>
            </div>
          )}

          {tab === "question" && answered && questionList.length === 0 && (
            <div className="empty py-7 text-[12.5px]">No concepts are linked to this question yet.</div>
          )}
          {tab === "topic" && topicLoading && (
            <div className="empty py-7 text-[12.5px]">Loading topic concepts…</div>
          )}
          {tab === "topic" && !topicLoading && topicConcepts.length === 0 && (
            <div className="empty py-7 text-[12.5px]">No concepts are linked to this topic yet.</div>
          )}

          {!(tab === "question" && !answered) && (
            <div className="mt-2">
              {list.map((concept, index) => (
                <ConceptItem key={`${concept.concept_id}-${index}`} concept={concept} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
