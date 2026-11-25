"use client";

import {
  ArrowLeft,
  ArrowRight,
  Bookmark,
  BookmarkCheck,
  CheckCircle2,
  Loader2,
  RotateCcw,
  Save,
} from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { KnowledgeRail } from "@/components/KnowledgeRail";
import { QuestionView } from "@/components/QuestionView";
import { QaPanel } from "@/components/qa/QaPanel";
import { TeacherPromoCard } from "@/components/TeacherPromoCard";
import { apiDelete, apiGet, apiPost, apiPut } from "@/lib/api";
import { useLanguage } from "@/lib/i18n";
import type {
  Note,
  Question,
  SessionPayload,
  SessionTopicContext,
} from "@/lib/types";

type AnswerResponse = {
  question_id: string;
  selected_label: string;
  is_correct: boolean;
  already_answered: boolean;
  feedback: Question["feedback"];
  completed: boolean;
  session_status: string;
  score: number | null;
  total: number | null;
};

function recomputeProgress(questions: Question[]) {
  const answered = questions.filter((q) => q.answered_at).length;
  const correct = questions.filter((q) => q.is_correct).length;
  return {
    answered,
    correct,
    total: questions.length,
    accuracy: answered ? correct / answered : null,
  };
}

function pagerItems(total: number, current: number): Array<number | "ellipsis"> {
  if (total <= 9) {
    return Array.from({ length: total }, (_, index) => index + 1);
  }
  const visible = new Set<number>();
  for (let page = 1; page <= 3; page += 1) visible.add(page);
  for (let page = total - 2; page <= total; page += 1) visible.add(page);
  visible.add(current);
  const sorted = Array.from(visible).sort((a, b) => a - b);
  const items: Array<number | "ellipsis"> = [];
  sorted.forEach((page, index) => {
    if (index > 0 && page - sorted[index - 1] > 1) items.push("ellipsis");
    items.push(page);
  });
  return items.filter(
    (item, index, array) =>
      !(item === "ellipsis" && array[index - 1] === "ellipsis"),
  );
}

export default function PracticeSessionPage() {
  const { t } = useLanguage();
  const params = useParams<{ sessionId: string }>();
  const router = useRouter();
  const sessionId = params.sessionId;

  const [data, setData] = useState<SessionPayload | null>(null);
  const [index, setIndex] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [notesMap, setNotesMap] = useState<Record<string, Note>>({});
  const [bookmarkSet, setBookmarkSet] = useState<Set<string>>(new Set());
  const [topicContext, setTopicContext] = useState<SessionTopicContext | null>(null);
  const [topicLoading, setTopicLoading] = useState(false);
  const [noteDraft, setNoteDraft] = useState("");
  const [savingNote, setSavingNote] = useState(false);
  const [noteSaved, setNoteSaved] = useState(false);
  const [qaTab, setQaTab] = useState<"qa" | "notes">("qa");

  useEffect(() => {
    let alive = true;
    Promise.all([
      apiGet<SessionPayload>(`/practice-sessions/${sessionId}`),
      apiGet<Note[]>("/me/notes?target_type=question&limit=200").catch(() => []),
      apiGet<Array<{ question_id: string }>>("/me/bookmarks?limit=200").catch(() => []),
    ])
      .then(([session, notes, bookmarks]) => {
        if (!alive) return;
        setData(session);
        setIndex(
          session.session.status === "in_progress" ? session.session.next_index ?? 0 : 0,
        );
        setSubmitted(session.session.status !== "in_progress");
        const map: Record<string, Note> = {};
        notes.forEach((n) => {
          map[n.target_id] = n;
        });
        setNotesMap(map);
        setBookmarkSet(new Set(bookmarks.map((b) => b.question_id)));
      })
      .catch((e: Error) => alive && setError(e.message));
    return () => {
      alive = false;
    };
  }, [sessionId]);

  const current = data?.questions[index];
  const currentId = current?.question_id;

  useEffect(() => {
    if (!currentId) return;
    setNoteDraft(notesMap[currentId]?.content || "");
    setNoteSaved(false);
    // Only reinitialize when the question changes; saving a note should keep "Saved".
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentId]);

  useEffect(() => {
    if (!currentId || !data) {
      setTopicContext(null);
      setTopicLoading(false);
      return;
    }
    // Topic practice has one session-level topic; wrong/bookmark/unit practice
    // can mix topics, so resolve Topic Concepts from the current question.
    if (data.session.topic_id) {
      setTopicContext(null);
      setTopicLoading(false);
      return;
    }

    let alive = true;
    setTopicContext(null);
    setTopicLoading(true);
    apiGet<SessionTopicContext>(
      `/practice-sessions/${sessionId}/questions/${currentId}/topic-concepts`,
    )
      .then((result) => {
        if (alive) setTopicContext(result);
      })
      .catch(() => {
        if (alive) setTopicContext(null);
      })
      .finally(() => {
        if (alive) setTopicLoading(false);
      });

    return () => {
      alive = false;
    };
  }, [currentId, data?.session.topic_id, sessionId]);

  const answered = Boolean(current?.answered_at);
  const concepts = current?.feedback?.concepts || [];
  const topicConcepts = data?.session.topic_id
    ? data.topic_concepts
    : topicContext?.concepts || [];
  const topicTitle = topicContext?.topic
    ? [topicContext.topic.code, topicContext.topic.title_en || "Practice"]
        .filter(Boolean)
        .join(" · ")
    : undefined;

  const progress = useMemo(
    () => data?.progress || { answered: 0, correct: 0, total: 0, accuracy: null },
    [data],
  );

  function go(delta: number) {
    if (!data) return;
    setIndex((i) => Math.max(0, Math.min(data.questions.length - 1, i + delta)));
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function select(label: string) {
    if (!current || busy || submitted) return;
    setBusy(true);
    setError(null);
    try {
      const res = await apiPost<AnswerResponse>(
        `/practice-sessions/${sessionId}/answers`,
        { question_id: current.question_id, selected_label: label },
      );
      if (res.completed) setSubmitted(true);
      setData((prev) => {
        if (!prev) return prev;
        const questions = prev.questions.map((q) =>
          q.question_id === res.question_id
            ? {
                ...q,
                selected_label: res.selected_label,
                is_correct: res.is_correct,
                answered_at: q.answered_at || new Date().toISOString(),
                feedback: res.feedback,
              }
            : q,
        );
        return {
          ...prev,
          session: {
            ...prev.session,
            status: res.session_status || prev.session.status,
            score: res.score ?? prev.session.score,
            total: res.total ?? prev.session.total,
          },
          questions,
          progress: recomputeProgress(questions),
        };
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to submit answer");
    } finally {
      setBusy(false);
    }
  }

  async function saveNote() {
    if (!current) return;
    setSavingNote(true);
    setError(null);
    try {
      const note = await apiPost<Note>("/me/notes", {
        target_type: "question",
        target_id: current.question_id,
        content: noteDraft,
      });
      setNotesMap((prev) => ({ ...prev, [current.question_id]: note }));
      setNoteSaved(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save note");
    } finally {
      setSavingNote(false);
    }
  }

  async function toggleBookmark() {
    if (!current) return;
    const isBookmarked = bookmarkSet.has(current.question_id);
    if (isBookmarked && !window.confirm(t("移除这道题的收藏？"))) return;
    try {
      if (isBookmarked) {
        await apiDelete(`/me/bookmarks/${current.question_id}`);
      } else {
        await apiPut(`/me/bookmarks/${current.question_id}`);
      }
      setBookmarkSet((prev) => {
        const next = new Set(prev);
        if (isBookmarked) next.delete(current.question_id);
        else next.add(current.question_id);
        return next;
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update bookmark");
    }
  }

  async function abandon() {
    if (!data || data.session.status !== "in_progress") return;
    if (
      !window.confirm(
        "End this session? It will be marked as ended early. Your answered questions remain available in History.",
      )
    ) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await apiPost(`/practice-sessions/${sessionId}/abandon`);
      router.push(
        data.session.group_id ? `/practice/${data.session.group_id}` : "/practice",
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to end session");
      setBusy(false);
    }
  }

  async function restart() {
    if (!data) return;
    const wrongPractice = data.session.source === "wrong";
    if (!wrongPractice && !data.session.topic_id) return;
    if (
      !window.confirm(
        wrongPractice
          ? t("重新开始错题练习？当前答题记录会保留在「做题记录」，新练习会从第一题开始。")
          : t("重新开始本次练习？当前答题记录会保留在「做题记录」。"),
      )
    ) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const next = await apiPost<SessionPayload>(
        "/practice-sessions",
        wrongPractice
          ? { source: "wrong", restart: true }
          : {
              source: "topic",
              group_id: data.session.group_id,
              topic_id: data.session.topic_id,
              restart: true,
            },
      );
      router.push(`/practice/session/${next.session.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to restart");
      setBusy(false);
    }
  }

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const target = e.target as HTMLElement | null;
      if (target && /^(INPUT|TEXTAREA|SELECT|BUTTON|A)$/.test(target.tagName)) return;
      if (target?.isContentEditable) return;
      if (!current || busy) return;
      const key = e.key.toLowerCase();
      if (["a", "b", "c", "d", "e"].includes(key)) {
        e.preventDefault();
        void select(key.toUpperCase());
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        go(1);
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        go(-1);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  if (error && !data) {
    return (
      <div>
        <div className="feedback feedback-bad">{error}</div>
        <Link href="/practice" className="btn mt-4">
          Back to Practice
        </Link>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="space-y-4">
        <div className="skeleton h-10 w-64" />
        <div className="skeleton h-96 w-full" />
      </div>
    );
  }

  const isWrongPractice = data.session.source === "wrong";
  const isHomework = data.session.source === "homework";
  const backHref = isHomework
    ? "/study-calendar"
    : isWrongPractice
      ? "/wrong"
      : data.session.group_id
        ? `/practice/${data.session.group_id}`
        : "/practice";
  const backLabel = isHomework
    ? t("返回学习日历")
    : isWrongPractice
      ? t("返回错题本")
      : "Back to Unit";

  if (data.questions.length === 0) {
    return (
      <div>
        <div className="flex items-center gap-2 mb-4">
          <Link href={backHref} className="btn btn-ghost btn-sm -ml-2">
            <ArrowLeft size={14} /> {backLabel}
          </Link>
          {isWrongPractice && <span className="pill pill-primary">{t("错题练习卷")}</span>}
        </div>
        <div className="card empty">
          {isWrongPractice
            ? "There are no questions left in this wrong-practice paper. They may all be marked as mastered."
            : "This practice session has no questions."}
          <div className="mt-4">
            <Link href={backHref} className="btn btn-sm">
              {isWrongPractice ? t("退出错题本") : "Back"}
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (!current) {
    return (
      <div className="space-y-4">
        <div className="skeleton h-10 w-64" />
        <div className="skeleton h-96 w-full" />
      </div>
    );
  }

  const isBookmarked = bookmarkSet.has(current.question_id);

  const notesBody = (
    <>
      <div className={`flex items-center ${isHomework ? "justify-end" : "justify-between"}`}>
        {!isHomework && <h3 className="text-[13px] font-semibold">{t("我的笔记")}</h3>}
        {noteSaved && <span className="text-[11px] text-[var(--success)]">{t("已保存")}</span>}
      </div>
      <textarea
        className="input mt-2 min-h-[92px] resize-y"
        placeholder={t("记下易错点、关键词或自己的理解…")}
        value={noteDraft}
        onChange={(e) => {
          setNoteDraft(e.target.value);
          setNoteSaved(false);
        }}
        maxLength={20000}
      />
      <div className="flex items-center justify-between mt-2">
        <span className="text-[11px] faint">{t("按题目保存；可在笔记本中查看全部。")}</span>
        <button
          className="btn btn-sm"
          onClick={saveNote}
          disabled={savingNote || !noteDraft.trim()}
        >
          {savingNote ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />}
          {t("保存")}
        </button>
      </div>
    </>
  );

  return (
    <div>
      <div className="top-row-clear flex items-center justify-between gap-3 mb-4">
        <div className="flex items-center gap-2">
          <Link href={backHref} className="btn btn-ghost btn-sm -ml-2">
            <ArrowLeft size={14} /> {backLabel}
          </Link>
          {isWrongPractice && <span className="pill pill-primary">{t("错题练习卷")}</span>}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="pill">
            {data.session.status === "in_progress"
              ? "Progress saved"
              : data.session.status === "submitted"
                ? "Completed"
                : "Ended Early"}
          </span>
          {isWrongPractice && (
            <button className="btn btn-sm btn-ghost" onClick={restart} disabled={busy}>
              <RotateCcw size={13} /> {t("重新开始")}
            </button>
          )}
          {data.session.status === "in_progress" && !isHomework && (
            <button className="btn btn-sm btn-ghost" onClick={abandon} disabled={busy}>
              End Session
            </button>
          )}
        </div>
      </div>

      {isHomework && data.homework && (
        <div
          className={`study-homework-head color-${data.homework.plan_color}`}
        >
          <span className="study-homework-plan">{data.homework.plan_title}</span>
          <span className="study-homework-sep">·</span>
          <span className="study-homework-task">{data.homework.task_title}</span>
          <span className="study-homework-sep">·</span>
          <span className="study-homework-date">{data.homework.study_date}</span>
        </div>
      )}

      {isWrongPractice && data.session.status === "in_progress" && (
        <div className="feedback mb-4 text-[12.5px] leading-5">
          This is a dynamic wrong-practice paper, independent of the original Unit. New wrong questions are added automatically and mastered questions are removed. Correct answers update the status: Unmastered → Reviewing → Mastered.
        </div>
      )}

      {data.session.status !== "in_progress" && (
        <div className="card card-pad mb-4 border-[color-mix(in_srgb,var(--primary)_30%,var(--line))] bg-[var(--primary-soft)]">
          <div className="flex items-center gap-2">
            <CheckCircle2 size={18} className="text-[var(--primary)]" />
            <h2 className="h2">
              {isHomework
                ? data.session.status === "submitted"
                  ? t("作业完成")
                  : t("作业已结束")
                : isWrongPractice
                  ? data.session.status === "submitted"
                    ? t("错题练习完成")
                    : t("错题练习已结束")
                  : data.session.status === "submitted"
                    ? "Chapter Complete"
                    : "Session Ended Early"}
            </h2>
          </div>
          {isHomework && data.homework && (
            <div className="mt-2 text-[12px] text-[var(--muted)]">
              {data.homework.plan_title} · {data.homework.task_title} ·{" "}
              {data.homework.study_date}
            </div>
          )}
          <p className="muted text-[13px] mt-1">
            Answered {progress.answered}/{progress.total} · Correct {progress.correct}
            {progress.answered
              ? ` · Accuracy ${Math.round((progress.correct / progress.answered) * 100)}%`
              : ""}
            {data.session.status === "submitted" ? ". Wrong answers were added to your wrong book." : ". Answered questions remain available for review."}
          </p>
          <div className="flex flex-wrap gap-2 mt-4">
            {isHomework ? (
              <Link href="/study-calendar" className="btn btn-sm btn-primary">
                <ArrowLeft size={14} /> {t("返回学习日历")}
              </Link>
            ) : (
              <Link href="/history" className="btn btn-sm">
                History
              </Link>
            )}
            {!isHomework && (
              <Link
                href="/wrong"
                className={isWrongPractice ? "btn btn-sm btn-primary" : "btn btn-sm"}
              >
                {isWrongPractice ? t("退出错题本") : "Wrong Book"}
              </Link>
            )}
            {data.session.topic_id && (
              <button className="btn btn-sm" onClick={restart} disabled={busy}>
                <RotateCcw size={13} /> Practice Again
              </button>
            )}
          </div>
        </div>
      )}

      {data.session.status === "submitted" && !isWrongPractice && !isHomework && (
        <TeacherPromoCard variant="result" />
      )}

      {error && <div className="feedback feedback-bad mb-4">{error}</div>}

      <div className="practice-layout">
        <div>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2 text-[12px] muted">
              <span className="font-mono">
                {index + 1} / {data.questions.length}
              </span>
              <span>·</span>
              <span>
                Answered {progress.answered} · Correct {progress.correct}
              </span>
            </div>
            <button
              className="btn btn-sm btn-ghost"
              onClick={toggleBookmark}
              title={isBookmarked ? "Remove bookmark" : "Bookmark question"}
            >
              {isBookmarked ? (
                <>
                  <BookmarkCheck size={15} className="text-[var(--accent)]" /> Bookmarked
                </>
              ) : (
                <>
                  <Bookmark size={15} /> Bookmark
                </>
              )}
            </button>
          </div>

          <div className="flex items-center justify-between gap-3 mb-3">
            <button
              className="btn btn-sm"
              onClick={() => go(-1)}
              disabled={index === 0}
            >
              <ArrowLeft size={15} /> Back
            </button>
            <span className="sm:hidden text-[11px] faint font-mono">
              {index + 1} / {data.questions.length}
            </span>
            <div className="hidden sm:flex items-center gap-1.5">
              {pagerItems(data.questions.length, index + 1).map((item, itemIndex) =>
                item === "ellipsis" ? (
                  <span
                    key={`ellipsis-${itemIndex}`}
                    className="h-7 w-5 grid place-items-center text-[11px] text-[var(--faint)]"
                  >
                    …
                  </span>
                ) : (
                  <button
                    key={item}
                    className={[
                      "h-7 min-w-7 px-1.5 rounded-lg border text-[11px] font-mono",
                      item === index + 1
                        ? "border-[var(--primary)] bg-[var(--primary)] text-white"
                        : data.questions[item - 1]?.answered_at
                          ? "border-[var(--line)] bg-[var(--surface-2)] text-[var(--muted)]"
                          : "border-[var(--line)] bg-[var(--surface)] text-[var(--faint)]",
                    ].join(" ")}
                    onClick={() => setIndex(item - 1)}
                  >
                    {item}
                  </button>
                ),
              )}
            </div>
            <button
              className="btn btn-sm btn-primary"
              onClick={() => go(1)}
              disabled={index === data.questions.length - 1}
            >
              Next <ArrowRight size={15} />
            </button>
          </div>

          <QuestionView question={current} onSelect={select} disabled={busy || submitted} />

          {isHomework ? (
            <div className="card card-pad mt-4">
              <div className="qa-tabs">
                <button
                  type="button"
                  className={`qa-tab ${qaTab === "qa" ? "is-active" : ""}`}
                  onClick={() => setQaTab("qa")}
                >
                  {t("老师答疑")}
                </button>
                <button
                  type="button"
                  className={`qa-tab ${qaTab === "notes" ? "is-active" : ""}`}
                  onClick={() => setQaTab("notes")}
                >
                  {t("我的笔记")}
                </button>
              </div>
              {qaTab === "qa" ? (
                <QaPanel sessionId={data.session.id} questionId={current.question_id} />
              ) : (
                notesBody
              )}
            </div>
          ) : (
            <div className="card card-pad mt-4">{notesBody}</div>
          )}

        </div>

        <KnowledgeRail
          concepts={concepts}
          topicConcepts={topicConcepts}
          topicTitle={topicTitle}
          topicInferred={topicContext?.inferred}
          topicLoading={topicLoading}
          answered={answered}
          questionId={current.question_id}
        />
      </div>
    </div>
  );
}
