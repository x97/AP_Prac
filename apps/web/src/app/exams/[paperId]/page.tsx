"use client";

import {
  ArrowLeft,
  Check,
  Clock3,
  FlaskConical,
  Loader2,
  LockKeyhole,
  Play,
  RotateCcw,
} from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { apiGet, apiPost } from "@/lib/api";
import { useLanguage } from "@/lib/i18n";
import type { Paper } from "@/lib/types";

type AttemptState = {
  attempt: { id: string; paper_id: string; mode: string; status: string };
};

const MODE_LABEL: Record<string, string> = {
  mcq: "MCQ Only",
  frq: "FRQ Only",
  full: "MCQ + FRQ (Full)",
};

export default function PaperPage() {
  const { t } = useLanguage();
  const params = useParams<{ paperId: string }>();
  const router = useRouter();
  const paperId = params.paperId;
  const [paper, setPaper] = useState<Paper | null>(null);
  const [mode, setMode] = useState("mcq");
  const [frqForm, setFrqForm] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiGet<Paper>(`/papers/${paperId}`)
      .then((p) => {
        setPaper(p);
        setMode(p.modes.includes("mcq") ? "mcq" : p.modes[0] || "mcq");
        if (p.frq_forms.length) setFrqForm(p.frq_forms[0]);
      })
      .catch((e: Error) => setError(e.message));
  }, [paperId]);

  async function start(override?: {
    mode?: string;
    frqForm?: string | null;
    restart?: boolean;
  }) {
    if (!paper) return;
    const nextMode = override?.mode || mode;
    const nextForm = override ? override.frqForm : frqForm;
    setLoading(true);
    setError(null);
    try {
      const state = await apiPost<AttemptState>("/attempts", {
        paper_id: paper.paper_id,
        mode: nextMode,
        frq_form: nextMode === "mcq" ? null : nextForm || null,
        restart: override?.restart || false,
      });
      router.push(`/exams/${paper.paper_id}/attempt/${state.attempt.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start exam");
      setLoading(false);
    }
  }

  if (!paper) {
    return error ? (
      <div className="feedback feedback-bad">{error}</div>
    ) : (
      <div className="skeleton h-72 w-full" />
    );
  }

  const formatLabel = paper.format_code === "legacy_100" ? "Legacy 100 Q" : "New 75 Q";
  const activeAttempts = paper.active_attempts || [];

  return (
    <div>
      <Link href="/exams" className="btn btn-ghost btn-sm -ml-2 mb-4">
        <ArrowLeft size={14} /> Back to Exams
      </Link>

      <div className="page-head">
        <div>
          <div className="eyebrow">
            {paper.paper_type === "real_exam" ? "Real Exam" : "Mock Exam"} · {paper.year} · {formatLabel}
          </div>
          <h1 className="h1">{paper.title || paper.paper_id}</h1>
        </div>
      </div>

      {activeAttempts.length > 0 && (
        <div className="card card-pad mb-4 border-[color-mix(in_srgb,var(--accent)_35%,var(--line))] bg-[var(--accent-soft)]">
          <h2 className="h2">Exam In Progress or Awaiting Self-Grade</h2>
          <p className="text-[12px] muted mt-1">
            Expired exams are settled automatically and no longer appear as “Continue”. Continuing restores saved answers and time from the server. Restarting ends the previous attempt and creates a new one.
          </p>
          <div className="mt-3 space-y-1">
            {activeAttempts.map((a) => {
              const isSelfGrade = a.status === "awaiting_self_grade";
              const isWaitingSecond =
                a.current_section === "frq" && a.section_status === "not_started";
              const href = isSelfGrade
                ? `/exams/${paper.paper_id}/attempt/${a.id}/review`
                : `/exams/${paper.paper_id}/attempt/${a.id}`;
              return (
                <div key={a.id} className="topic-row">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="pill pill-primary">{MODE_LABEL[a.mode] || a.mode}</span>
                      {a.frq_form && <span className="badge">FRQ {a.frq_form}</span>}
                      <span className="badge">
                        {isSelfGrade
                          ? "Awaiting Self-Grade"
                          : isWaitingSecond
                            ? "Section II Not Started"
                            : a.current_section === "frq"
                              ? "Section II"
                              : "Section I"}
                      </span>
                    </div>
                    <div className="text-[12px] muted mt-1.5">
                      {isSelfGrade
                        ? "FRQ submitted. Complete your rubric self-grade."
                        : isWaitingSecond
                          ? "Section I has ended. Section II has not started yet."
                          : `Answered ${a.answered}/${a.total} · Updated ${new Date(a.updated_at).toLocaleString("en-US")}`}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <Link href={href} className="btn btn-sm btn-primary">
                      {isSelfGrade ? "Self-Grade" : "Continue"}
                    </Link>
                    <button
                      className="btn btn-sm"
                      onClick={() =>
                        start({
                          mode: a.mode,
                          frqForm: a.frq_form,
                          restart: true,
                        })
                      }
                      disabled={loading}
                    >
                      <RotateCcw size={13} /> Restart
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <div className="card card-pad">
          <h2 className="h2">Exam Structure</h2>
          <div className="grid grid-cols-2 gap-4 mt-4">
            <div className="rounded-xl border border-[var(--line)] p-4">
              <div className="flex items-center gap-2 text-[12px] muted">
                <FlaskConical size={14} /> Section I · MCQ
              </div>
              <div className="stat-value mt-1">{paper.mcq_count ?? 0}</div>
              <div className="text-[11px] faint flex items-center gap-1 mt-1">
                <Clock3 size={11} /> {paper.mcq_minutes ?? 0} min
              </div>
            </div>
            <div className="rounded-xl border border-[var(--line)] p-4">
              <div className="flex items-center gap-2 text-[12px] muted">
                <FlaskConical size={14} /> Section II · FRQ
              </div>
              <div className="stat-value mt-1">{paper.frq_count ?? 0}</div>
              <div className="text-[11px] faint flex items-center gap-1 mt-1">
                <Clock3 size={11} /> {paper.frq_minutes ?? 0} min
              </div>
            </div>
          </div>
          {paper.frq_forms.length > 0 && (
            <p className="text-[12px] muted mt-4">
              FRQ has {paper.frq_forms.join(" / ")}; the real exam uses only one set.
            </p>
          )}
          {paper.frq_warning && (
            <div className="feedback feedback-bad mt-4 text-[12px] text-[var(--danger)]">
              {paper.frq_warning}
            </div>
          )}
          {paper.notes && <p className="text-[12px] muted mt-3">{paper.notes}</p>}
        </div>

        <div className="card card-pad">
          <h2 className="h2">Select Mode</h2>
          <div className="mt-3 space-y-2">
            {paper.modes.map((m) => {
              return (
                <button
                  key={m}
                  className={[
                    "w-full text-left rounded-xl border p-3.5 transition",
                    mode === m
                      ? "border-[var(--primary)] bg-[var(--primary-soft)]"
                      : "border-[var(--line)] bg-[var(--surface)]",
                    "hover:border-[var(--primary)]",
                  ].join(" ")}
                  onClick={() => setMode(m)}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium text-[13.5px]">{MODE_LABEL[m]}</span>
                    {mode === m ? <Check size={15} className="text-[var(--primary)]" /> : null}
                  </div>
                  <div className="text-[11.5px] muted mt-1">
                    {m === "mcq"
                      ? `${paper.mcq_count} questions · ${paper.mcq_minutes} min · review after submission`
                      : m === "frq"
                        ? `${paper.frq_count} questions · ${paper.frq_minutes} min · rubric self-grade`
                        : `MCQ ${paper.mcq_count} + FRQ ${paper.frq_count} · separate section timers`}
                  </div>
                </button>
              );
            })}
          </div>

          {mode !== "mcq" && paper.frq_forms.length > 0 && (
            <div className="mt-3">
              <div className="text-[12px] muted mb-1.5">FRQ Set</div>
              <div className="flex gap-2">
                {paper.frq_forms.map((f) => (
                  <button
                    key={f}
                    className={f === frqForm ? "btn btn-sm btn-primary" : "btn btn-sm"}
                    onClick={() => setFrqForm(f)}
                  >
                    {f}
                  </button>
                ))}
              </div>
            </div>
          )}

          {error && <div className="feedback feedback-bad mt-3 text-[12px]">{error}</div>}

          <button
            className="btn btn-primary w-full mt-4"
            onClick={() => start()}
            disabled={loading || activeAttempts.length > 0 || paper.locked}
          >
            {paper.locked ? (
              <LockKeyhole size={15} />
            ) : loading ? (
              <Loader2 size={15} className="animate-spin" />
            ) : (
              <Play size={15} />
            )}
            {paper.locked
              ? t("需要解锁")
              : activeAttempts.length > 0
                ? "Continue or restart above first"
                : "Start Exam"}
          </button>
          <p className="text-[11px] faint mt-2 leading-5">
            {paper.locked
              ? t("这套试卷需要激活码。可在「我的 → 课程权限」中输入激活码后开始。")
              : "The timer starts immediately. Refreshing or leaving the page restores saved answers. Explanations remain locked until submission."}
          </p>
        </div>
      </div>
    </div>
  );
}
