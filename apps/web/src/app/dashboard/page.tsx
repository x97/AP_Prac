"use client";

import { ArrowRight, BookOpen, Flame, Play } from "lucide-react";
import { useEffect, useState } from "react";

import { ActivatedSubjectsCard } from "@/components/ActivatedSubjectsCard";
import { ActivityHeatmap } from "@/components/ActivityHeatmap";
import { FlashcardStudy } from "@/components/FlashcardStudy";
import { TeacherPromoCard } from "@/components/TeacherPromoCard";
import { useExamCountdown } from "@/hooks/useExamCountdown";
import { QuietLink } from "@/components/QuietLink";
import { apiGet } from "@/lib/api";
import type { Dashboard } from "@/lib/types";


function CountdownUnit({ value, label }: { value: number; label: string }) {
  return (
    <span className="inline-flex items-baseline gap-1.5">
      <span className="text-[34px] leading-none font-semibold tabular-nums tracking-tight">
        {value}
      </span>
      <span className="text-[11px] muted font-normal">{label}</span>
    </span>
  );
}

function statusLabel(status: string) {
  if (status === "in_progress") return "In Progress";
  if (status === "completed" || status === "submitted" || status === "graded") return "Completed";
  if (status === "awaiting_self_grade") return "Awaiting Self-Grade";
  if (status === "abandoned") return "Ended Early";
  return status;
}

function recentPill(r: Dashboard["recent"][number]) {
  if (r.status === "in_progress") {
    return r.type === "practice"
      ? `${r.answered ?? 0}/${r.total_questions ?? 0}`
      : "In Progress";
  }
  if (r.status === "abandoned") return "Ended Early";
  if (r.status === "awaiting_self_grade") return "Awaiting Self-Grade";
  if (r.type === "attempt") {
    if (r.mode === "frq") {
      return `FRQ ${r.frq_score ?? 0}/${r.frq_total ?? 0}`;
    }
    return `${r.mcq_score ?? 0}/${r.mcq_total ?? 0}`;
  }
  return `${r.score ?? r.answered ?? 0}/${r.total ?? r.total_questions ?? 0}`;
}

export default function DashboardPage() {
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const activeSubjectId = "psychology";
  const { schedule: examSchedule, countdown } = useExamCountdown(activeSubjectId);

  useEffect(() => {
    let alive = true;
    apiGet<Dashboard>("/me/dashboard")
      .then((d) => alive && setData(d))
      .catch((e: Error) => alive && setError(e.message));
    return () => {
      alive = false;
    };
  }, []);

  if (error) {
    return <div className="feedback feedback-bad">{error}</div>;
  }

  if (!data) {
    return (
      <div className="space-y-4">
        <div className="skeleton h-8 w-56" />
        <div className="stat-grid">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="card card-pad h-24 skeleton" />
          ))}
        </div>
        <div className="skeleton h-36 w-full" />
      </div>
    );
  }

  const { overview, units, continue: last, recent } = data;
  const unit = units.find((u) => u.group_id === last?.group_id);
  const continueHref = last
    ? last.type === "attempt"
      ? ["awaiting_self_grade", "submitted", "graded"].includes(last.status)
        ? `/exams/${last.paper_id}/attempt/${last.id}/review`
        : `/exams/${last.paper_id}/attempt/${last.id}`
      : `/practice/session/${last.id}`
    : "/practice";
  const lastScore =
    last?.type === "attempt"
      ? last.mode === "frq"
        ? `FRQ ${last.frq_score ?? 0}/${last.frq_total ?? 0}`
        : `MCQ ${last.mcq_score ?? 0}/${last.mcq_total ?? 0}`
      : `${last?.answered ?? 0}/${last?.total_questions ?? last?.total ?? 0}`;
  const lastTitle =
    last?.type === "attempt"
      ? "Continue Exam"
      : last
        ? "Continue Practice"
        : "Start with Unit 1";
  const lastPracticeTitle =
    last?.source === "wrong"
      ? "Wrong Practice"
      : last?.source === "bookmark"
        ? "Bookmark Practice"
        : last?.topic_title_en ||
          last?.group_title_en ||
          unit?.title_en ||
          unit?.title ||
          "Unit Practice";
  const lastAttemptTitle =
    last?.paper_title || last?.paper_title_en || last?.paper_id || "Full Exam";

  return (
    <div>
      <div className="page-head">
        <div>
          <div className="eyebrow">AP Psychology · Exam Countdown</div>
          {!countdown ? (
            <div className="skeleton h-11 w-64 mt-2" />
          ) : countdown.kind === "upcoming" ? (
            <h1 className="mt-1 flex flex-wrap items-baseline gap-x-4 gap-y-1">
              <CountdownUnit value={countdown.days} label="天" />
            </h1>
          ) : (
            <h1 className="h1">
              {countdown.kind === "today" ? "Exam Day" : "Exam Completed"}
            </h1>
          )}
          <p className="muted text-[13px] mt-2">
            {examSchedule.subjectName} · {examSchedule.displayDate}
          </p>
        </div>
        <QuietLink href="/practice" className="btn btn-primary">
          <Play size={15} />
          Start Practice
        </QuietLink>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.55fr_1fr]">
        <div className="card card-pad">
          <ActivityHeatmap
            activity={data.activity}
            summary={data.activity_summary}
            streakDays={overview.streak_days}
          />
        </div>

        <div className="card card-pad relative overflow-hidden">
          <div className="absolute -right-10 -top-12 h-40 w-40 rounded-full bg-[var(--primary-soft)]" />
          <div className="relative">
            <div className="eyebrow">Continue</div>
            <h2 className="h2 mt-2">{lastTitle}</h2>
            <p className="muted text-[13px] mt-2">
              {last
                ? last.type === "attempt"
                  ? `${lastAttemptTitle} · ${lastScore} · ${statusLabel(last.status)}`
                  : `${lastPracticeTitle} · Answered ${lastScore} · ${statusLabel(last.status)}`
                : "5 Units · 45 topics. Practice by topic."}
            </p>
            <div className="mt-5 flex items-center gap-3">
              <QuietLink href={continueHref} className="btn btn-primary">
                <ArrowRight size={15} />
                {last ? "Continue" : "Start Practice"}
              </QuietLink>
              <QuietLink href="/exams" className="btn">
                View Exams
              </QuietLink>
            </div>
          </div>
        </div>
      </div>

      <ActivatedSubjectsCard />

      <div className="mt-7 grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <div className="flex items-end justify-between gap-3">
            <div>
              <h2 className="h2">Flashcards</h2>
              <p className="text-[12.5px] muted mt-1">
                High-weight concepts first. Flip cards directly on the homepage.
              </p>
            </div>
            <QuietLink href="/cards" className="text-[13px] text-[var(--primary)] shrink-0">
              All Cards
            </QuietLink>
          </div>
          <div className="card card-pad mt-3">
            <FlashcardStudy limit={20} compact />
          </div>
        </div>

        <div className="space-y-4">
          <div className="card card-pad">
            <h2 className="h2">学习建议</h2>
            <div className="mt-3 space-y-3">
              <div className="flex gap-3">
                <BookOpen size={18} className="mt-0.5 text-[var(--primary)]" />
                <div>
                  <div className="text-[13px] font-medium">先按单元练习</div>
                  <div className="text-[12px] muted mt-0.5">
                    单元练习会即时给出解析和知识点；整套真题用来训练节奏和耐力。
                  </div>
                </div>
              </div>
              <div className="flex gap-3">
                <Flame size={18} className="mt-0.5 text-[var(--accent)]" />
                <div>
                  <div className="text-[13px] font-medium">连续答对两次才算掌握</div>
                  <div className="text-[12px] muted mt-0.5">
                    错题本会自动记录；连续答对后再标记为已掌握，仍可在「已掌握」中查看。
                  </div>
                </div>
              </div>
            </div>
          </div>

          <TeacherPromoCard variant="home" />

          <div className="card card-pad">
            <div className="flex items-center justify-between">
              <h2 className="h2">Recent Practice</h2>
              <QuietLink href="/history" className="text-[12px] text-[var(--primary)]">
                View All
              </QuietLink>
            </div>
            <div className="mt-3">
              {recent.length === 0 && <div className="empty py-8">No practice records yet.</div>}
              {recent.map((r) => {
                const href =
                  r.type === "attempt"
                    ? r.status === "in_progress"
                      ? `/exams/${r.paper_id}/attempt/${r.id}`
                      : `/exams/${r.paper_id}/attempt/${r.id}/review`
                    : `/practice/session/${r.id}`;
                return (
                  <QuietLink key={r.id} href={href} className="topic-row hover:bg-[var(--surface-2)]">
                    <div className="min-w-0">
                      <div className="text-[13px] font-medium truncate" lang="en">
                        {r.type === "attempt"
                          ? r.paper_title || r.paper_title_en || `Exam ${r.paper_id}`
                          : r.topic_title_en ||
                            (r.source === "wrong"
                              ? "Wrong Practice"
                              : r.source === "bookmark"
                                ? "Bookmark Practice"
                                : "Topic Practice")}
                      </div>
                      <div className="text-[11px] faint mt-0.5">
                        {statusLabel(r.status)} · {new Date(r.created_at).toLocaleString("en-US")}
                      </div>
                    </div>
                    <span className="pill">{recentPill(r)}</span>
                  </QuietLink>
                );
              })}
            </div>
          </div>
        </div>
      </div>

    </div>
  );
}
