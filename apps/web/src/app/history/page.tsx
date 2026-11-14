"use client";

import { ArrowRight, BookOpen, FileText, History } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { apiGet } from "@/lib/api";
import type { AttemptHistoryItem, PracticeHistoryItem } from "@/lib/types";

type Tab = "practice" | "attempt";

const MODE_LABEL: Record<string, string> = {
  mcq: "MCQ",
  frq: "FRQ",
  full: "MCQ + FRQ",
};

function statusLabel(status: string) {
  if (status === "in_progress") return "In Progress";
  if (status === "awaiting_self_grade") return "Awaiting Self-Grade";
  if (status === "submitted" || status === "graded" || status === "completed")
    return "Completed";
  if (status === "abandoned") return "Ended Early";
  return status;
}

function statusClass(status: string) {
  if (status === "in_progress") return "pill pill-primary";
  if (status === "abandoned") return "pill pill-warn";
  if (status === "awaiting_self_grade") return "pill";
  return "pill";
}

function practiceTitle(item: PracticeHistoryItem) {
  if (item.topic_title_en) return item.topic_title_en;
  if (item.source === "wrong") return "Wrong Practice";
  if (item.source === "bookmark") return "Bookmark Practice";
  if (item.group_title_en) return item.group_title_en;
  return "Chapter Practice";
}

function practiceSubtitle(item: PracticeHistoryItem) {
  const parts = [];
  if (item.topic_code) parts.push(item.topic_code);
  const group = item.group_title_en;
  if (group) parts.push(group);
  return parts.join(" · ");
}

export default function HistoryPage() {
  const [tab, setTab] = useState<Tab>("practice");
  const [practice, setPractice] = useState<PracticeHistoryItem[] | null>(null);
  const [attempts, setAttempts] = useState<AttemptHistoryItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setError(null);
    const request =
      tab === "practice"
        ? apiGet<PracticeHistoryItem[]>("/me/practice-sessions?limit=100").then(
            (rows) => alive && setPractice(rows),
          )
        : apiGet<AttemptHistoryItem[]>("/me/attempts?limit=100").then(
            (rows) => alive && setAttempts(rows),
          );
    request.catch((e: Error) => alive && setError(e.message));
    return () => {
      alive = false;
    };
  }, [tab]);

  const loading = tab === "practice" ? practice === null : attempts === null;
  const practiceRows = practice || [];
  const attemptRows = attempts || [];

  return (
    <div>
      <div className="page-head">
        <div>
          <div className="eyebrow">History</div>
          <h1 className="h1">History</h1>
          <p className="muted text-[13px] mt-2">
            Every chapter and exam keeps a record. Completed sessions show scores; ended-early sessions can still be reviewed.
          </p>
        </div>
        <span className="pill">
          <History size={13} /> Reviewable
        </span>
      </div>

      <div className="flex gap-2 mb-4">
        <button
          className={tab === "practice" ? "btn btn-sm btn-primary" : "btn btn-sm"}
          onClick={() => setTab("practice")}
        >
          <BookOpen size={14} /> Practice Records
          {practice && <span className="ml-1 opacity-70">{practice.length}</span>}
        </button>
        <button
          className={tab === "attempt" ? "btn btn-sm btn-primary" : "btn btn-sm"}
          onClick={() => setTab("attempt")}
        >
          <FileText size={14} /> Exam Records
          {attempts && <span className="ml-1 opacity-70">{attempts.length}</span>}
        </button>
      </div>

      {error && <div className="feedback feedback-bad mb-4">{error}</div>}
      {loading && <div className="skeleton h-64 w-full" />}

      {!loading && tab === "practice" && practiceRows.length === 0 && (
        <div className="card empty">
          <BookOpen size={26} className="mx-auto mb-2 text-[var(--faint)]" />
          No practice records yet. Answer a few questions in a chapter; progress is saved automatically.
        </div>
      )}

      {!loading && tab === "practice" && practiceRows.length > 0 && (
        <div className="space-y-2">
          {practiceRows.map((item) => (
            <Link
              key={item.id}
              href={`/practice/session/${item.id}`}
              className="card card-pad flex items-center justify-between gap-4 hover:bg-[var(--surface-2)]"
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className={statusClass(item.status)}>
                    {statusLabel(item.status)}
                  </span>
                  {item.topic_code && (
                    <span className="badge font-mono">{item.topic_code}</span>
                  )}
                  {item.source === "wrong" && <span className="badge">Wrong</span>}
                  {item.source === "bookmark" && <span className="badge">Bookmark</span>}
                </div>
                <div className="font-semibold text-[14px] mt-1.5" lang="en">
                  {practiceTitle(item)}
                </div>
                <div className="text-[11.5px] faint mt-0.5 truncate">
                  {practiceSubtitle(item)}
                </div>
                <div className="text-[11px] faint mt-1.5">
                  Answered {item.answered}/{item.total_questions} · {item.correct} correct
                  {item.accuracy !== null
                    ? ` · Accuracy ${Math.round(item.accuracy * 100)}%`
                    : ""}
                  {" · "}
                  {new Date(item.created_at).toLocaleString("zh-CN")}
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0 text-[12px] font-medium text-[var(--primary)]">
                {item.status === "in_progress" ? "Continue" : "View Record"}
                <ArrowRight size={15} />
              </div>
            </Link>
          ))}
        </div>
      )}

      {!loading && tab === "attempt" && attemptRows.length === 0 && (
        <div className="card empty">
          <FileText size={26} className="mx-auto mb-2 text-[var(--faint)]" />
          No exam records yet. Start an exam from Exams.
        </div>
      )}

      {!loading && tab === "attempt" && attemptRows.length > 0 && (
        <div className="space-y-2">
          {attemptRows.map((item) => {
            const isReview = item.status !== "in_progress";
            const href = isReview
              ? `/exams/${item.paper_id}/attempt/${item.id}/review`
              : `/exams/${item.paper_id}/attempt/${item.id}`;
            return (
              <Link
                key={item.id}
                href={href}
                className="card card-pad flex items-center justify-between gap-4 hover:bg-[var(--surface-2)]"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={statusClass(item.status)}>
                      {statusLabel(item.status)}
                    </span>
                    <span className="badge">
                      {MODE_LABEL[item.mode] || item.mode}
                    </span>
                    {item.frq_form && (
                      <span className="badge">FRQ {item.frq_form}</span>
                    )}
                  </div>
                  <div className="font-semibold text-[14px] mt-1.5">
                    {item.paper_title || item.paper_id}
                  </div>
                  <div className="text-[11.5px] faint mt-0.5 truncate" lang="en">
                    {item.paper_title_en || item.paper_id}
                    {item.paper_year ? ` · ${item.paper_year}` : ""}
                  </div>
                  <div className="text-[11px] faint mt-1.5">
                    {item.status === "in_progress"
                      ? "Exam in progress. Saved answers and time can be restored from the server."
                      : item.status === "awaiting_self_grade"
                        ? "FRQ submitted. Awaiting rubric self-grade."
                        : item.status === "abandoned"
                          ? "Ended early. Answered questions can be reviewed."
                          : `MCQ ${item.mcq_score ?? 0}/${item.mcq_total ?? 0}${
                              item.mode !== "mcq"
                                ? ` · FRQ ${item.frq_score ?? "Not graded"}/${item.frq_total ?? 0}`
                                : ""
                            }`}
                    {" · "}
                    {new Date(item.created_at).toLocaleString("zh-CN")}
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0 text-[12px] font-medium text-[var(--primary)]">
                  {item.status === "in_progress"
                    ? "Continue"
                    : item.status === "awaiting_self_grade"
                      ? "Self-Grade"
                      : "Review"}
                  <ArrowRight size={15} />
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
