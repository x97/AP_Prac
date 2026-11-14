"use client";

import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  ChevronDown,
  Flag,
  Loader2,
  LogOut,
  Pause,
  Play,
  Send,
  XCircle,
} from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { ExamQuestionSplit } from "@/components/ExamQuestionSplit";
import { Modal } from "@/components/Modal";
import { QuestionReportButton } from "@/components/QuestionReportButton";
import { apiGet, apiPatch, apiPost } from "@/lib/api";
import type { AttemptAnswer, AttemptState, Paper } from "@/lib/types";

type LocalAnswer = {
  selected_label: string | null;
  flagged: boolean;
  frq_text: string;
};

function formatTime(ms: number) {
  const total = Math.max(0, Math.floor(ms / 1000));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  return h > 0
    ? `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`
    : `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

export default function ExamAttemptPage() {
  const params = useParams<{ paperId: string; attemptId: string }>();
  const router = useRouter();
  const { paperId, attemptId } = params;

  const [data, setData] = useState<AttemptState | null>(null);
  const [paper, setPaper] = useState<Paper | null>(null);
  const [answers, setAnswers] = useState<Record<string, LocalAnswer>>({});
  const [index, setIndex] = useState(0);
  const [remaining, setRemaining] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [savingId, setSavingId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [frqDraft, setFrqDraft] = useState("");
  const [frqSaved, setFrqSaved] = useState(false);
  const [startingFrq, setStartingFrq] = useState(false);
  const [navigatorOpen, setNavigatorOpen] = useState(false);
  const [navigatorFilter, setNavigatorFilter] = useState<"all" | "flagged">("all");
  const [paused, setPaused] = useState(false);
  const [pauseOpen, setPauseOpen] = useState(false);
  const [pauseBusy, setPauseBusy] = useState(false);
  const [leavePausing, setLeavePausing] = useState(false);
  const [leavePauseError, setLeavePauseError] = useState<string | null>(null);
  const [confirmAbandon, setConfirmAbandon] = useState(false);
  const [submitConfirmOpen, setSubmitConfirmOpen] = useState(false);
  const submittedRef = useRef(false);
  const pausedRef = useRef(false);
  const examActiveRef = useRef(false);
  const leavePauseSentRef = useRef(false);
  const guardPushedRef = useRef(false);
  const previousExistsRef = useRef(false);
  const ignorePopRef = useRef(false);
  const pauseInFlightRef = useRef(false);
  const autoTriedRef = useRef(false);
  const deadlineRef = useRef<number | null>(null);
  const frqTimer = useRef<number | null>(null);

  function mergeState(state: AttemptState) {
    setConfirmAbandon(false);
    setData(state);
    const map: Record<string, LocalAnswer> = {};
    state.answers.forEach((a: AttemptAnswer) => {
      map[a.question_id] = {
        selected_label: a.selected_label,
        flagged: a.flagged,
        frq_text: a.frq_text || "",
      };
    });
    setAnswers(map);
    if (state.attempt.status !== "in_progress") submittedRef.current = true;
    if (state.section.status === "active") autoTriedRef.current = false;
    const isPaused = Boolean(state.paused ?? state.section.paused);
    pausedRef.current = isPaused;
    examActiveRef.current =
      state.attempt.status === "in_progress" &&
      state.section.status === "active" &&
      !isPaused;
    setPaused(isPaused);
    if (isPaused) {
      deadlineRef.current = null;
      setRemaining(state.remaining_ms);
      setPauseOpen(true);
    } else {
      setPauseOpen(false);
      if (state.remaining_ms !== null) {
        deadlineRef.current = Date.now() + state.remaining_ms;
        setRemaining(state.remaining_ms);
      } else {
        deadlineRef.current = null;
        setRemaining(null);
      }
    }
  }

  useEffect(() => {
    let alive = true;
    Promise.all([
      apiGet<AttemptState>(`/attempts/${attemptId}`),
      apiGet<Paper>(`/papers/${paperId}`),
    ])
      .then(([state, p]) => {
        if (!alive) return;
        setPaper(p);
        mergeState(state);
      })
      .catch((e: Error) => alive && setError(e.message));
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [attemptId, paperId]);

  useEffect(() => {
    examActiveRef.current = Boolean(
      data &&
        data.attempt.status === "in_progress" &&
        data.section.status === "active" &&
        !pausedRef.current,
    );
  }, [data, paused]);

  const pushExamGuard = useCallback(() => {
    if (guardPushedRef.current) return;
    window.history.pushState(
      { ...(window.history.state || {}), __examGuard: attemptId },
      "",
      window.location.href,
    );
    guardPushedRef.current = true;
  }, [attemptId]);

  useEffect(() => {
    if (!data || paused) return;
    if (data.attempt.status !== "in_progress" || data.section.status !== "active") {
      return;
    }
    if (guardPushedRef.current) return;
    previousExistsRef.current = window.history.length > 1;
    pushExamGuard();
  }, [data, paused, pushExamGuard]);

  const leaveExam = useCallback(
    (path: string) => {
      const navigate = () => router.replace(path);
      if (!guardPushedRef.current) {
        navigate();
        return;
      }
      guardPushedRef.current = false;
      let done = false;
      function finish() {
        if (done) return;
        done = true;
        window.removeEventListener("popstate", onPop);
        navigate();
      }
      function onPop() {
        finish();
      }
      window.addEventListener("popstate", onPop);
      window.history.back();
      window.setTimeout(finish, 180);
    },
    [router],
  );

  const pauseForLeave = useCallback(async () => {
    if (pauseInFlightRef.current) {
      pushExamGuard();
      return;
    }
    if (!examActiveRef.current || pausedRef.current || submittedRef.current) return;
    pauseInFlightRef.current = true;
    setLeavePauseError(null);
    setLeavePausing(true);
    const loadingStartedAt = Date.now();
    const waitForLoading = async () => {
      const left = 1500 - (Date.now() - loadingStartedAt);
      if (left > 0) {
        await new Promise((resolve) => window.setTimeout(resolve, left));
      }
    };
    // Replace the popped guard with a new one while the request is in flight,
    // so repeated back presses cannot leave before the pause is acknowledged.
    pushExamGuard();
    try {
      const state = await apiPost<AttemptState>(`/attempts/${attemptId}/pause`, {});
      pausedRef.current = true;
      examActiveRef.current = false;
      setPaused(true);
      setRemaining(state.remaining_ms);
      await waitForLoading();
      if (previousExistsRef.current) {
        // Current stack: previous page, exam, guard. Remove the guard and the
        // duplicate exam entry, landing on the previous page.
        guardPushedRef.current = false;
        ignorePopRef.current = true;
        window.history.go(-2);
        window.setTimeout(() => {
          setLeavePausing(false);
          setPauseOpen(true);
        }, 1500);
      } else {
        // No previous page to return to: pop the guard and show the pause menu.
        guardPushedRef.current = false;
        ignorePopRef.current = true;
        window.history.back();
        setLeavePausing(false);
        setPauseOpen(true);
      }
    } catch (e) {
      await waitForLoading();
      setLeavePausing(false);
      setLeavePauseError(
        e instanceof Error ? e.message : "暂停考试失败，请重试。",
      );
      pushExamGuard();
    } finally {
      pauseInFlightRef.current = false;
    }
  }, [attemptId, pushExamGuard]);

  useEffect(() => {
    function onPopState() {
      if (ignorePopRef.current) {
        ignorePopRef.current = false;
        return;
      }
      const hadGuard = guardPushedRef.current;
      if (!hadGuard) return;
      guardPushedRef.current = false;
      if (pauseInFlightRef.current) {
        pushExamGuard();
        return;
      }
      if (pausedRef.current || submittedRef.current || !examActiveRef.current) {
        if (previousExistsRef.current) {
          ignorePopRef.current = true;
          window.history.back();
        } else if (pausedRef.current) {
          setPauseOpen(true);
        }
        return;
      }
      void pauseForLeave();
    }

    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, [pauseForLeave, pushExamGuard]);

  useEffect(() => {
    function sendPauseOnLeave() {
      if (
        !examActiveRef.current ||
        pausedRef.current ||
        submittedRef.current ||
        leavePauseSentRef.current
      ) {
        return;
      }
      leavePauseSentRef.current = true;
      const path = `/api/v1/attempts/${encodeURIComponent(attemptId)}/pause`;
      let queued = false;
      try {
        const body = new Blob(["{}"], { type: "application/json" });
        queued = navigator.sendBeacon(path, body);
      } catch {
        queued = false;
      }
      if (!queued) {
        void fetch(path, {
          method: "POST",
          credentials: "include",
          keepalive: true,
        }).catch(() => undefined);
      }
    }

    function onPageShow(event: PageTransitionEvent) {
      // Returning through the browser back/forward cache must re-read the
      // server state so an auto-paused exam opens the paused menu.
      if (event.persisted) window.location.reload();
    }

    // Fallback for full document unloads (refresh/close) that do not go
    // through the guarded popstate path. The normal back path uses the
    // loading overlay and waits for the pause response.
    window.addEventListener("pagehide", sendPauseOnLeave);
    window.addEventListener("pageshow", onPageShow);
    return () => {
      window.removeEventListener("pagehide", sendPauseOnLeave);
      window.removeEventListener("pageshow", onPageShow);
    };
  }, [attemptId]);

  useEffect(() => {
    if (deadlineRef.current === null || pausedRef.current) return;
    const tick = () => {
      if (pausedRef.current) return;
      const left = Math.max(0, (deadlineRef.current || 0) - Date.now());
      setRemaining(left);
      if (left <= 0 && !submittedRef.current && !autoTriedRef.current) {
        autoTriedRef.current = true;
        void submitSection(true);
      }
    };
    tick();
    const timer = window.setInterval(tick, 1000);
    return () => window.clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data?.section.name, data?.section.status, data?.section.expires_at, paused]);

  const current = data?.questions[index];
  const currentId = current?.question_id;
  const sectionName = data?.attempt.current_section || "mcq";
  const isFrq = sectionName === "frq";

  useEffect(() => {
    if (!currentId) return;
    setFrqDraft(answers[currentId]?.frq_text || "");
    setFrqSaved(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentId]);

  function go(delta: number) {
    if (!data || pausedRef.current) return;
    if (isFrq && current) {
      if (frqTimer.current) window.clearTimeout(frqTimer.current);
      void saveFrqText(frqDraft);
    }
    setIndex((i) => Math.max(0, Math.min(data.questions.length - 1, i + delta)));
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function select(label: string) {
    if (!current || isFrq || submittedRef.current || pausedRef.current) return;
    const before = answers[current.question_id] || {
      selected_label: null,
      flagged: false,
      frq_text: "",
    };
    setAnswers((prev) => ({
      ...prev,
      [current.question_id]: { ...before, selected_label: label },
    }));
    setSavingId(current.question_id);
    try {
      await apiPatch(`/attempts/${attemptId}/answers`, {
        answers: [{ question_id: current.question_id, selected_label: label }],
      });
    } catch (e) {
      setAnswers((prev) => ({ ...prev, [current.question_id]: before }));
      setError(e instanceof Error ? e.message : "Failed to save answer");
    } finally {
      setSavingId(null);
    }
  }

  async function saveFrqText(text: string) {
    if (!current || submittedRef.current) return;
    try {
      await apiPatch(`/attempts/${attemptId}/answers`, {
        answers: [{ question_id: current.question_id, frq_text: text }],
      });
      setAnswers((prev) => ({
        ...prev,
        [current.question_id]: {
          ...(prev[current.question_id] || { selected_label: null, flagged: false, frq_text: "" }),
          frq_text: text,
        },
      }));
      setFrqSaved(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save response");
    }
  }

  function onFrqChange(text: string) {
    if (pausedRef.current) return;
    setFrqDraft(text);
    setFrqSaved(false);
    if (frqTimer.current) window.clearTimeout(frqTimer.current);
    frqTimer.current = window.setTimeout(() => {
      void saveFrqText(text);
    }, 800);
  }

  async function toggleFlag(questionId: string) {
    if (submittedRef.current || pausedRef.current) return;
    const before = answers[questionId] || {
      selected_label: null,
      flagged: false,
      frq_text: "",
    };
    const next = { ...before, flagged: !before.flagged };
    setAnswers((prev) => ({ ...prev, [questionId]: next }));
    try {
      await apiPatch(`/attempts/${attemptId}/answers`, {
        answers: [{ question_id: questionId, flagged: next.flagged }],
      });
    } catch (e) {
      setAnswers((prev) => ({ ...prev, [questionId]: before }));
      setError(e instanceof Error ? e.message : "Failed to update mark");
    }
  }

  async function pauseExam() {
    if (submittedRef.current || pauseBusy || savingId) return;
    if (pausedRef.current) {
      setPauseOpen(true);
      return;
    }
    setPauseBusy(true);
    setError(null);
    try {
      if (isFrq && current) {
        if (frqTimer.current) window.clearTimeout(frqTimer.current);
        await saveFrqText(frqDraft);
      }
      const state = await apiPost<AttemptState>(`/attempts/${attemptId}/pause`, {});
      mergeState(state);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to pause exam");
    } finally {
      setPauseBusy(false);
    }
  }

  async function resumeExam() {
    if (pauseBusy) return;
    setPauseBusy(true);
    setError(null);
    try {
      const state = await apiPost<AttemptState>(`/attempts/${attemptId}/resume`, {});
      mergeState(state);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to resume exam");
    } finally {
      setPauseBusy(false);
    }
  }

  async function saveForLater() {
    if (pauseBusy) return;
    setPauseBusy(true);
    setError(null);
    try {
      if (!pausedRef.current) {
        if (isFrq && current) {
          if (frqTimer.current) window.clearTimeout(frqTimer.current);
          await saveFrqText(frqDraft);
        }
        await apiPost<AttemptState>(`/attempts/${attemptId}/pause`, {});
        pausedRef.current = true;
      }
      leaveExam(`/exams/${paperId}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save exam for later");
      setPauseBusy(false);
    }
  }

  async function abandonExam() {
    if (pauseBusy) return;
    setPauseBusy(true);
    setError(null);
    try {
      await apiPost(`/attempts/${attemptId}/abandon`);
      submittedRef.current = true;
      leaveExam(`/exams/${paperId}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to abandon exam");
      setPauseBusy(false);
    }
  }

  async function startFrq() {
    setStartingFrq(true);
    setError(null);
    try {
      const state = await apiPost<AttemptState>(`/attempts/${attemptId}/sections/frq/start`, {});
      mergeState(state);
      setIndex(0);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start Section II");
    } finally {
      setStartingFrq(false);
    }
  }

  async function submitSection(auto = false, confirmed = false) {
    if (!data || submitting || submittedRef.current || pausedRef.current) return;
    if (!auto && savingId) return;
    if (!auto && !confirmed) {
      setError(null);
      setSubmitConfirmOpen(true);
      return;
    }
    const section = data.section.name;
    setSubmitConfirmOpen(false);
    setSubmitting(true);
    setError(null);
    try {
      if (section === "frq" && current) {
        if (frqTimer.current) window.clearTimeout(frqTimer.current);
        await saveFrqText(frqDraft);
      }
      const res = await apiPost<{
        next_section?: string;
        status: string;
      }>(`/attempts/${attemptId}/sections/${section}/submit`, {});
      if (res.next_section === "frq") {
        const state = await apiGet<AttemptState>(`/attempts/${attemptId}`);
        mergeState(state);
        setIndex(0);
        setSubmitConfirmOpen(false);
        setSubmitting(false);
        return;
      }
      submittedRef.current = true;
      leaveExam(`/exams/${paperId}/attempt/${attemptId}/review`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to submit exam");
      submittedRef.current = false;
      autoTriedRef.current = false;
      setSubmitting(false);
    }
  }

  if (error && !data) {
    return (
      <div className="exam-wrap">
        <div className="feedback feedback-bad">{error}</div>
        <Link href={`/exams/${paperId}`} className="btn">
          Back to Paper
        </Link>
      </div>
    );
  }

  if (!data || !paper) {
    return (
      <div className="exam-wrap">
        <div className="skeleton h-96 w-full" />
      </div>
    );
  }

  const isSubmitted = ["submitted", "awaiting_self_grade", "graded", "abandoned"].includes(
    data.attempt.status,
  );
  const timerClass =
    remaining !== null && remaining <= 60_000
      ? "danger"
      : remaining !== null && remaining <= 5 * 60_000
        ? "warn"
        : "";
  const answeredCount = data.questions.filter((q) => {
    const a = answers[q.question_id];
    if (sectionName !== "frq") return Boolean(a?.selected_label);
    const text =
      q.question_id === current?.question_id ? frqDraft : a?.frq_text || "";
    return Boolean(text.trim());
  }).length;
  const flaggedCount = Object.values(answers).filter((a) => a.flagged).length;
  const sectionLabel =
    sectionName === "frq"
      ? "Section II · FRQ"
      : data.attempt.mode === "full"
        ? "Section I · MCQ"
        : "Section I · MCQ";
  const submitLabel =
    sectionName === "frq"
      ? "Submit FRQ"
      : data.attempt.mode === "full"
        ? "Submit Section I"
        : "Submit Exam";
  const unansweredCount = data.questions.length - answeredCount;
  const unansweredNoun = isFrq
    ? unansweredCount === 1
      ? "response"
      : "responses"
    : unansweredCount === 1
      ? "question"
      : "questions";
  const unansweredVerb = unansweredCount === 1 ? "is" : "are";

  // Transition page between MCQ and FRQ in full mode.
  if (isFrq && data.can_start && !isSubmitted) {
    return (
      <div>
        <header className="exam-top">
          <div className="exam-top-inner">
            <div className="min-w-0 flex-1">
              <div className="eyebrow">Section I submitted</div>
              <div className="font-semibold text-[14px] truncate">
                {paper.title || paper.chinese_title || paper.paper_id}
              </div>
            </div>
            <span className="pill">Section II · FRQ</span>
          </div>
        </header>
        <div className="exam-wrap">
          <div className="card card-pad">
            <div className="flex items-center gap-2">
              <CheckCircle2 size={19} className="text-[var(--success)]" />
              <h1 className="h1 text-[24px]">Section I Submitted</h1>
            </div>
            <p className="muted text-[13.5px] mt-2">
              Next is Section II: {paper.frq_count} FRQs in {paper.frq_minutes} minutes.
              The timer starts only after you click “Start Section II”.
            </p>
            <div className="feedback mt-4 text-[12.5px]">
              Section I explanations stay locked until you submit FRQ and review the full exam.
            </div>
            {error && <div className="feedback feedback-bad mt-3">{error}</div>}
            <button className="btn btn-primary mt-4" onClick={startFrq} disabled={startingFrq}>
              {startingFrq ? <Loader2 size={15} className="animate-spin" /> : <ArrowRight size={15} />}
              Start Section II
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (isSubmitted && data.questions.length === 0) {
    return (
      <div className="exam-wrap">
        <div className="card card-pad">
          <div className="font-semibold">Exam Submitted</div>
          <Link
            href={`/exams/${paperId}/attempt/${attemptId}/review`}
            className="btn btn-primary btn-sm mt-3"
          >
            View Review
          </Link>
        </div>
      </div>
    );
  }

  if (!current) {
    return (
      <div className="exam-wrap">
        <div className="card empty">No questions in this section.</div>
      </div>
    );
  }

  return (
    <div>
      <header className="exam-top">
        <div className="exam-top-inner">
          <div className="min-w-0 flex-1">
            <div className="eyebrow truncate">
              {paper.paper_type === "real_exam" ? "Real Exam" : "Mock Exam"} · {paper.year}
              {paper.frq_forms.length ? ` · ${data.attempt.frq_form || ""}` : ""}
            </div>
            <div className="font-semibold text-[14px] truncate">
              {paper.title || paper.chinese_title || paper.paper_id}
            </div>
          </div>
          <div className="text-center shrink-0">
            <div className={`exam-timer ${timerClass}`}>
              {remaining === null ? "—" : formatTime(remaining)}
            </div>
            <div className={`text-[10px] ${paused ? "text-[var(--accent)]" : "faint"}`}>
              {paused ? "Paused" : sectionLabel}
            </div>
          </div>
          <div className="hidden sm:flex items-center gap-2 text-[12px] muted">
            <span>
              {answeredCount}/{data.questions.length}
            </span>
            <span>·</span>
            <span>⚑ {flaggedCount}</span>
          </div>
          {!isSubmitted && (
            <div className="flex items-center gap-2 shrink-0">
              <button
                className="btn btn-sm"
                onClick={() => {
                  if (paused) {
                    setError(null);
                    setPauseOpen(true);
                  } else {
                    void pauseExam();
                  }
                }}
                disabled={submitting || pauseBusy || Boolean(savingId)}
                aria-label={paused ? "Open paused exam menu" : "Pause exam timer"}
              >
                {pauseBusy ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : paused ? (
                  <Play size={14} />
                ) : (
                  <Pause size={14} />
                )}
                <span className="hidden sm:inline">{paused ? "Resume" : "Pause"}</span>
              </button>
              <button
                className="btn btn-primary btn-sm"
                onClick={() => submitSection(false)}
                disabled={submitting || Boolean(savingId) || paused}
              >
                {submitting ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
                {submitLabel}
              </button>
            </div>
          )}
        </div>
      </header>

      <div className={isFrq ? "exam-wrap" : "exam-wrap exam-wrap-single"}>
        <div>
          {error && <div className="feedback feedback-bad mb-3">{error}</div>}
          {isSubmitted ? (
            <div className="card card-pad mb-3">
              <div className="font-semibold">Exam Submitted</div>
              <div className="text-[12px] muted mt-1">Your answers are saved. Review explanations and self-grade FRQ.</div>
              <Link
                href={`/exams/${paperId}/attempt/${attemptId}/review`}
                className="btn btn-primary btn-sm mt-3"
              >
                View Review
              </Link>
            </div>
          ) : isFrq ? (
            <div className="card card-pad">
              <div className="flex items-center justify-between gap-2">
                <span className="pill pill-primary font-mono">FRQ {data.questions[index]?.display_number}</span>
                <div className="flex flex-wrap items-center justify-end gap-2">
                  <QuestionReportButton
                    questionId={current.question_id}
                    attemptId={attemptId}
                  />
                  <button
                    className="btn btn-ghost btn-sm"
                    onClick={() => toggleFlag(current.question_id)}
                  >
                    <Flag
                      size={14}
                      className={answers[current.question_id]?.flagged ? "text-[var(--accent)]" : ""}
                    />
                    {answers[current.question_id]?.flagged ? "Marked for Review" : "Mark for Review"}
                  </button>
                </div>
              </div>
              {(current.assets || []).filter((a) => !a.option_label).length > 0 && (
                <div className="mt-3 space-y-2">
                  {current.assets
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
              <div className="mt-4 max-h-[42vh] overflow-y-auto rounded-xl border border-[var(--line)] bg-[var(--surface-2)] p-4 whitespace-pre-wrap text-[13.5px] leading-6" lang="en">
                {current.stem}
              </div>
              <div className="mt-4">
                <div className="flex items-center justify-between">
                  <span className="text-[12px] muted">Your Response</span>
                  <span className="text-[11px] faint">
                    {frqDraft.length} characters {frqSaved ? "· Saved" : ""}
                  </span>
                </div>
                <textarea
                  className="input mt-2 min-h-[320px] resize-y leading-6"
                  placeholder="Answer each part A–F in separate paragraphs. Your work is saved automatically."
                  value={frqDraft}
                  onChange={(e) => onFrqChange(e.target.value)}
                  maxLength={50000}
                  lang="en"
                />
              </div>
              <div className="flex items-center justify-between mt-4">
                <button className="btn" onClick={() => go(-1)} disabled={index === 0}>
                  <ArrowLeft size={15} /> Back
                </button>
                <span className="text-[11px] faint">
                  {index + 1} / {data.questions.length}
                </span>
                <button
                  className="btn btn-primary"
                  onClick={() => go(1)}
                  disabled={index === data.questions.length - 1}
                >
                  Next <ArrowRight size={15} />
                </button>
              </div>
            </div>
          ) : (
            <>
              <ExamQuestionSplit
                question={current}
                attemptId={attemptId}
                onSelect={select}
                selectedLabel={answers[current.question_id]?.selected_label}
                disabled={savingId === current.question_id || isSubmitted || paused}
                flagged={Boolean(answers[current.question_id]?.flagged)}
                onToggleFlag={() => toggleFlag(current.question_id)}
              />

              <div className="exam-question-nav mt-3">
                <button
                  type="button"
                  className="exam-question-jump"
                  onClick={() => {
                    setNavigatorFilter("all");
                    setNavigatorOpen(true);
                  }}
                  aria-haspopup="dialog"
                  aria-label={`Question ${index + 1} of ${data.questions.length}${answers[current.question_id]?.flagged ? ", marked for review" : ""}. Open question navigator.`}
                >
                  <span className="font-mono">
                    Question {index + 1} of {data.questions.length}
                  </span>
                  <ChevronDown size={16} />
                </button>
                <button
                  className="btn btn-sm"
                  onClick={() => go(-1)}
                  disabled={index === 0}
                  aria-label="Back to previous question"
                >
                  <ArrowLeft size={15} /> Back
                </button>
                <button
                  className="btn btn-sm btn-primary"
                  onClick={() => go(1)}
                  disabled={index === data.questions.length - 1}
                  aria-label="Next question"
                >
                  Next <ArrowRight size={15} />
                </button>
              </div>
            </>
          )}
        </div>

        {isFrq && (
        <aside className="card card-pad">
          <div className="flex items-center justify-between">
            <h2 className="text-[13px] font-semibold">Answer Sheet</h2>
            <span className="pill">{data.questions.length}</span>
          </div>
          <div className="palette-grid mt-3">
            {data.questions.map((q, i) => {
              const a = answers[q.question_id];
              const done = isFrq ? Boolean(a?.frq_text.trim()) : Boolean(a?.selected_label);
              return (
                <button
                  key={q.question_id}
                  className={[
                    "palette-btn",
                    i === index ? "current" : "",
                    done ? "answered" : "",
                    a?.flagged ? "flagged" : "",
                  ].join(" ")}
                  onClick={() => setIndex(i)}
                  aria-label={`Question ${q.display_number}${done ? ", answered" : ""}${a?.flagged ? ", marked for review" : ""}`}
                  title={a?.flagged ? "Marked for Review" : undefined}
                >
                  {q.display_number}
                </button>
              );
            })}
          </div>
          <div className="mt-4 grid grid-cols-2 gap-2 text-[10.5px] faint">
            <span>Answered {answeredCount}</span>
            <span>Unanswered {data.questions.length - answeredCount}</span>
            <span>⚑ Marked for Review {flaggedCount}</span>
            <span>Total {data.questions.length}</span>
          </div>
          <div className="border-t border-[var(--line)] mt-4 pt-3 text-[11px] faint leading-5">
            After submitting FRQ, self-grade each rubric point. No automatic scoring.
          </div>
        </aside>
        )}
      </div>

      {leavePausing && (
        <div className="exam-grading-overlay" role="status" aria-live="assertive">
          <div className="exam-grading-card">
            <Loader2 size={30} className="animate-spin text-[var(--primary)]" />
            <div className="exam-grading-title">正在暂停考试…</div>
            <p className="exam-grading-copy">
              正在保存考试状态并冻结计时，暂停成功后会返回上一页。
            </p>
          </div>
        </div>
      )}

      <Modal
        open={Boolean(leavePauseError)}
        onClose={() => setLeavePauseError(null)}
        title="暂停失败"
        narrow
        dismissible={false}
      >
        <p className="text-[13px] muted leading-6">
          {leavePauseError}
        </p>
        <p className="mt-2 text-[11.5px] faint leading-5">
          暂停请求没有成功，考试仍在计时。请重试；只有暂停成功后才会返回上一页。
        </p>
        <div className="mt-4 flex justify-end gap-2">
          <button
            type="button"
            className="btn"
            onClick={() => setLeavePauseError(null)}
          >
            继续考试
          </button>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => {
              setLeavePauseError(null);
              void pauseForLeave();
            }}
          >
            <Loader2 size={14} className={leavePausing ? "animate-spin" : ""} />
            重试暂停
          </button>
        </div>
      </Modal>

      <Modal
        open={pauseOpen}
        onClose={() => setPauseOpen(false)}
        title={confirmAbandon ? "Abandon Exam?" : "Exam Paused"}
        narrow
        dismissible={false}
      >
        {confirmAbandon ? (
          <div>
            <div className="flex flex-col items-center text-center">
              <div className="grid h-12 w-12 place-items-center rounded-full bg-[var(--danger-soft)] text-[var(--danger)]">
                <AlertTriangle size={22} />
              </div>
              <p className="mt-3 max-w-[300px] text-[13px] muted leading-6">
                Your saved answers will stay available in review, but this attempt
                cannot be resumed.
              </p>
            </div>

            <div className="mt-4 rounded-xl border border-[var(--line)] bg-[var(--surface-2)] p-3.5 text-[12px]">
              <div className="flex items-center justify-between gap-3">
                <span className="muted">Time remaining</span>
                <span className="font-mono font-semibold">
                  {remaining === null ? "—" : formatTime(remaining)}
                </span>
              </div>
              <div className="mt-2 flex items-center justify-between gap-3">
                <span className="muted">Answered</span>
                <span className="font-mono font-semibold">
                  {answeredCount} / {data.questions.length}
                </span>
              </div>
            </div>

            {error && <div className="feedback feedback-bad mt-3">{error}</div>}

            <div className="mt-4 grid grid-cols-2 gap-2">
              <button
                type="button"
                className="btn"
                onClick={() => {
                  setError(null);
                  setConfirmAbandon(false);
                }}
                disabled={pauseBusy}
              >
                Keep Exam
              </button>
              <button
                type="button"
                className="btn btn-danger"
                onClick={abandonExam}
                disabled={pauseBusy}
              >
                {pauseBusy ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : (
                  <XCircle size={16} />
                )}
                Abandon
              </button>
            </div>
          </div>
        ) : (
          <>
            <p className="text-[13px] muted leading-6">
              The timer is stopped at{" "}
              <span className="font-mono font-semibold text-[var(--ink)]">
                {remaining === null ? "—" : formatTime(remaining)}
              </span>
              . Your saved answers will be here when you return.
            </p>
            {error && <div className="feedback feedback-bad mt-3">{error}</div>}
            <div className="mt-4 flex flex-col gap-2">
              <button
                type="button"
                className="btn justify-start text-left"
                onClick={saveForLater}
                disabled={pauseBusy}
              >
                <LogOut size={16} />
                <span>Save for Later</span>
                <span className="ml-auto text-[10.5px] faint">Exit and keep this time</span>
              </button>
              <button
                type="button"
                className="btn justify-start text-left text-[var(--danger)]"
                onClick={() => {
                  setError(null);
                  setConfirmAbandon(true);
                }}
                disabled={pauseBusy}
              >
                <XCircle size={16} />
                <span>Abandon Exam</span>
                <span className="ml-auto text-[10.5px] faint">End this attempt</span>
              </button>
              <button
                type="button"
                className="btn btn-primary justify-start text-left"
                onClick={resumeExam}
                disabled={pauseBusy}
              >
                {pauseBusy ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />}
                <span>Continue Exam</span>
                <span className="ml-auto text-[10.5px] opacity-75">Resume the timer</span>
              </button>
            </div>
            <p className="mt-3 text-[10.5px] faint leading-5">
              This menu stays open while the exam is paused. You can close the tab and
              return later; the timer stays frozen. Choose Continue Exam to resume it.
              Using the browser back button pauses the exam first, then returns to the previous page.
            </p>
          </>
        )}
      </Modal>

      <Modal
        open={submitConfirmOpen}
        onClose={() => {
          if (submitting) return;
          setSubmitConfirmOpen(false);
          setError(null);
        }}
        title={`${submitLabel}?`}
        narrow
        dismissible={!submitting}
      >
        <div className="flex flex-col items-center text-center">
          <div className="grid h-12 w-12 place-items-center rounded-full bg-[var(--primary-soft)] text-[var(--primary)]">
            <Send size={22} />
          </div>
          <p className="mt-3 max-w-[310px] text-[13px] muted leading-6">
            {isFrq
              ? "Submit your responses and continue to rubric self-grading?"
              : "Once submitted, this section cannot be changed."}
          </p>
        </div>

        <div className="mt-4 rounded-xl border border-[var(--line)] bg-[var(--surface-2)] p-3.5 text-[12px]">
          <div className="flex items-center justify-between gap-3">
            <span className="muted">Answered</span>
            <span className="font-mono font-semibold">
              {answeredCount} / {data.questions.length}
            </span>
          </div>
          <div className="mt-2 flex items-center justify-between gap-3">
            <span className="muted">Unanswered</span>
            <span
              className={`font-mono font-semibold ${
                unansweredCount > 0 ? "text-[var(--accent)]" : "text-[var(--success)]"
              }`}
            >
              {unansweredCount}
            </span>
          </div>
          <div className="mt-2 flex items-center justify-between gap-3">
            <span className="muted">Marked for Review</span>
            <span className="font-mono font-semibold">{flaggedCount}</span>
          </div>
          <div className="mt-2 flex items-center justify-between gap-3">
            <span className="muted">Time remaining</span>
            <span className="font-mono font-semibold">
              {remaining === null ? "—" : formatTime(remaining)}
            </span>
          </div>
        </div>

        {unansweredCount > 0 ? (
          <div className="feedback mt-3 flex items-start gap-2 text-[12px] leading-5">
            <AlertTriangle
              size={15}
              className="mt-0.5 shrink-0 text-[var(--accent)]"
            />
            <span>
              {unansweredCount} {unansweredNoun} {unansweredVerb} unanswered.{" "}
              {isFrq
                ? "Empty responses receive no credit."
                : "Unanswered questions will be scored incorrect."}
            </span>
          </div>
        ) : (
          <div className="feedback feedback-ok mt-3 flex items-center gap-2 text-[12px]">
            <CheckCircle2 size={15} className="text-[var(--success)]" />
            <span>
              All {isFrq ? "responses" : "questions"} answered.
            </span>
          </div>
        )}

        {error && <div className="feedback feedback-bad mt-3">{error}</div>}

        <div className="mt-4 grid grid-cols-2 gap-2">
          <button
            type="button"
            className="btn"
            onClick={() => {
              setSubmitConfirmOpen(false);
              setError(null);
            }}
            disabled={submitting}
          >
            Keep Working
          </button>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => void submitSection(false, true)}
            disabled={submitting}
          >
            {submitting ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <Send size={16} />
            )}
            {submitLabel}
          </button>
        </div>
        <p className="mt-3 text-center text-[10.5px] faint leading-5">
          {isFrq
            ? "After submitting, you will self-grade each rubric point."
            : data.attempt.mode === "full"
              ? "After Section I, Section II will start. Explanations stay locked until the full exam is submitted."
              : "Explanations and answers unlock after submission."}
        </p>
      </Modal>

      <Modal
        open={navigatorOpen}
        onClose={() => setNavigatorOpen(false)}
        title="Question Navigator"
        wide
      >
        <div className="flex flex-wrap items-center justify-between gap-2 text-[11.5px] muted">
          <span>
            Question {index + 1} of {data.questions.length}
          </span>
          <span>
            Answered {answeredCount} · Marked for Review {flaggedCount}
          </span>
        </div>
        <div className="palette-filter mt-3" role="group" aria-label="Filter questions">
          <button
            type="button"
            className={navigatorFilter === "all" ? "palette-filter-btn active" : "palette-filter-btn"}
            onClick={() => setNavigatorFilter("all")}
            aria-pressed={navigatorFilter === "all"}
          >
            All <span className="palette-filter-count">{data.questions.length}</span>
          </button>
          <button
            type="button"
            className={navigatorFilter === "flagged" ? "palette-filter-btn active" : "palette-filter-btn"}
            onClick={() => setNavigatorFilter("flagged")}
            aria-pressed={navigatorFilter === "flagged"}
          >
            <Flag size={12} /> Marked for Review <span className="palette-filter-count">{flaggedCount}</span>
          </button>
        </div>
        <div className="palette-grid palette-grid-wide mt-3">
          {data.questions.map((q, i) => {
            const a = answers[q.question_id];
            const done = isFrq ? Boolean(a?.frq_text.trim()) : Boolean(a?.selected_label);
            return { q, i, a, done };
          }).filter(({ q }) => navigatorFilter === "all" || answers[q.question_id]?.flagged)
            .map(({ q, i, a, done }) => (
              <button
                key={q.question_id}
                className={[
                  "palette-btn",
                  i === index ? "current" : "",
                  done ? "answered" : "",
                  a?.flagged ? "flagged" : "",
                ].join(" ")}
                onClick={() => {
                  setIndex(i);
                  setNavigatorOpen(false);
                  window.scrollTo({ top: 0, behavior: "smooth" });
                }}
                aria-label={`Question ${q.display_number}${done ? ", answered" : ""}${a?.flagged ? ", marked for review" : ""}`}
                title={a?.flagged ? "Marked for Review" : undefined}
              >
                {q.display_number}
              </button>
            ))}
        </div>
        {navigatorFilter === "flagged" && flaggedCount === 0 && (
          <p className="mt-4 text-center text-[12px] muted">
            No questions marked for review yet.
          </p>
        )}
        <div className="mt-4 grid grid-cols-2 gap-2 text-[10.5px] faint sm:grid-cols-4">
          <span>Answered {answeredCount}</span>
          <span>Unanswered {data.questions.length - answeredCount}</span>
          <span>⚑ Marked for Review {flaggedCount}</span>
          <span>Total {data.questions.length}</span>
        </div>
        <div className="border-t border-[var(--line)] mt-4 pt-3 text-[11px] faint leading-5">
          Answers and explanations stay locked until submission. Refresh restores saved answers.
        </div>
      </Modal>

      {submitting && (
        <div className="exam-grading-overlay" role="status" aria-live="assertive">
          <div className="exam-grading-card">
            <Loader2 size={30} className="animate-spin text-[var(--primary)]" />
            <div className="exam-grading-title">
              {sectionName === "frq" ? "正在交卷…" : "正在批改中…"}
            </div>
            <p className="exam-grading-copy">
              {sectionName === "frq"
                ? "交卷后进入评分标准自评；错题会在整卷完成后统一记录。"
                : "交卷后统一批改；错题会在批改完成后进入错题本。"}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
