"use client";

import { ArrowRight, BookOpen, Lightbulb, RotateCcw } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { useLanguage } from "@/lib/i18n";

const OPTIONS = [
  { label: "A", text: "Amygdala" },
  { label: "B", text: "Hippocampus" },
  { label: "C", text: "Cerebellum" },
  { label: "D", text: "Medulla" },
];

const TOPIC_CONCEPTS = [
  {
    name: "Hippocampus",
    definition:
      "Consolidates new declarative memories; damage makes it hard to form new explicit memories.",
    core: true,
  },
  {
    name: "Amygdala",
    definition: "Processes emotional significance, especially fear and threat detection.",
  },
  {
    name: "Cerebellum",
    definition: "Coordinates voluntary movement, balance, and procedural learning.",
  },
  {
    name: "Medulla",
    definition: "Controls autonomic functions such as breathing, heart rate, and blood pressure.",
  },
];

const QUESTION_CONCEPTS = [
  {
    name: "Hippocampus",
    definition:
      "Consolidates new declarative memories; damage makes it hard to form new explicit memories.",
    relation: "Core",
    relationClass: "badge badge-core",
  },
  {
    name: "Amygdala",
    definition: "Emotion and threat processing; it does not consolidate declarative memories.",
    relation: "Confusable",
    relationClass: "badge badge-confusable",
  },
];

const CORRECT_LABEL = "B";

export function LandingSampleQuestion() {
  const { t } = useLanguage();
  const [selected, setSelected] = useState<string | null>(null);
  const [revealed, setRevealed] = useState(false);
  const [tab, setTab] = useState<"question" | "topic">("question");

  function choose(label: string) {
    if (revealed) return;
    setSelected(label);
    setRevealed(true);
    setTab("question");
  }

  function reset() {
    setSelected(null);
    setRevealed(false);
    setTab("question");
  }

  const correct = selected === CORRECT_LABEL;

  return (
    <div className="landing-sample-grid">
      <div className="card card-pad">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <div className="eyebrow">Free sample · Unit 1</div>
            <div className="mt-1 text-[12px] muted">1.4 The Brain · MCQ</div>
          </div>
          <span className="pill">{t("即时解析")}</span>
        </div>

        <h3 className="mt-5 text-[21px] font-semibold leading-8 tracking-[-0.02em]" lang="en">
          After damage to which brain structure would a patient have the most difficulty
          forming new declarative memories?
        </h3>

        <div className="mt-4 space-y-2.5" role="group" aria-label="Sample question options">
          {OPTIONS.map((option) => {
            const isCorrect = revealed && option.label === CORRECT_LABEL;
            const isWrong =
              revealed && option.label === selected && option.label !== CORRECT_LABEL;
            const isDim = revealed && !isCorrect && !isWrong;
            return (
              <div
                key={option.label}
                role="button"
                tabIndex={revealed ? -1 : 0}
                aria-disabled={revealed}
                className={[
                  "option",
                  isCorrect ? "correct" : "",
                  isWrong ? "wrong" : "",
                  isDim ? "dim" : "",
                  revealed ? "locked" : "",
                ].join(" ")}
                onClick={() => choose(option.label)}
                onKeyDown={(event) => {
                  if (revealed) return;
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    choose(option.label);
                  }
                }}
              >
                <span className="option-letter">{option.label}</span>
                <span className="min-w-0 flex-1" lang="en">
                  {option.text}
                </span>
                {isCorrect && <span className="text-[16px] text-[var(--success)]">✓</span>}
                {isWrong && <span className="text-[16px] text-[var(--danger)]">×</span>}
              </div>
            );
          })}
        </div>

        {revealed && (
          <div
            className={`feedback mt-5 ${
              correct ? "feedback-ok" : "feedback-bad"
            }`}
          >
            <div className="flex items-center gap-2 text-[13.5px] font-semibold">
              {correct ? (
                <>{t("正确")}</>
              ) : (
                <>
                  {t("正确答案是 {label} · {concept}", {
                    label: CORRECT_LABEL,
                    concept: "Hippocampus",
                  })}
                </>
              )}
            </div>
            <p className="mt-2 text-[13px] leading-6" lang="en">
              The hippocampus is critical for consolidating new declarative memories.
              The amygdala is involved in emotional processing; the cerebellum supports
              motor coordination and procedural learning.
            </p>
          </div>
        )}

        {revealed && (
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <Link href="/dashboard" className="btn btn-primary btn-sm">
              {t("登录后继续做 Unit 1")} <ArrowRight size={14} />
            </Link>
            <button type="button" className="btn btn-sm btn-ghost" onClick={reset}>
              <RotateCcw size={13} /> {t("再试一次")}
            </button>
          </div>
        )}
      </div>

      <aside className="rail-card card landing-knowledge" aria-label="Sample question concepts">
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="eyebrow">Knowledge rail</div>
            <h3 className="landing-knowledge-title">1.4 The Brain</h3>
          </div>
          <span className="landing-knowledge-icon">
            <BookOpen size={17} strokeWidth={1.8} />
          </span>
        </div>

        <div className="rail-tabs" role="group" aria-label={t("概念分类")}>
          <button
            type="button"
            className={tab === "question" ? "rail-tab active" : "rail-tab"}
            aria-pressed={tab === "question"}
            onClick={() => setTab("question")}
          >
            Question Concepts
            <span>{revealed ? QUESTION_CONCEPTS.length : "after answer"}</span>
          </button>
          <button
            type="button"
            className={tab === "topic" ? "rail-tab active" : "rail-tab"}
            aria-pressed={tab === "topic"}
            onClick={() => setTab("topic")}
          >
            Topic Concepts
            <span>{TOPIC_CONCEPTS.length}</span>
          </button>
        </div>

        {tab === "question" && !revealed && (
          <div className="rail-empty-hint">
            <Lightbulb size={16} className="text-[var(--accent)]" />
            <div>
              <div className="text-[12.5px] font-medium">Answer first, then review concepts</div>
              <p className="text-[11.5px] muted mt-1 leading-5">
                {t("选完答案后，这里会显示本题的核心概念和易混概念。")}
              </p>
              <button
                type="button"
                className="btn btn-sm btn-ghost mt-2"
                onClick={() => setTab("topic")}
              >
                View Topic Concepts
              </button>
            </div>
          </div>
        )}

        {tab === "question" && revealed && (
          <div className="landing-concepts mt-2">
            {QUESTION_CONCEPTS.map((concept) => (
              <div key={concept.name} className="concept">
                <div className="flex items-start justify-between gap-2">
                  <div className="concept-name" lang="en">
                    {concept.name}
                  </div>
                  <span className={concept.relationClass}>{concept.relation}</span>
                </div>
                <div className="concept-def" lang="en">
                  {concept.definition}
                </div>
              </div>
            ))}
          </div>
        )}

        {tab === "topic" && (
          <div className="landing-concepts mt-2">
            {TOPIC_CONCEPTS.map((concept) => (
              <div key={concept.name} className="concept">
                <div className="concept-name" lang="en">
                  {concept.name}
                </div>
                <div className="concept-def" lang="en">
                  {concept.definition}
                </div>
              </div>
            ))}
          </div>
        )}
      </aside>
    </div>
  );
}
