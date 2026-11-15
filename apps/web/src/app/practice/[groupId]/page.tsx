"use client";

import { ArrowLeft, ArrowRight, Loader2, LockKeyhole, RotateCcw } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { apiGet, apiPost } from "@/lib/api";
import { useLanguage } from "@/lib/i18n";
import type { PracticeGroup, SessionPayload, Topic } from "@/lib/types";

function sessionLabel(topic: Topic) {
  const current = topic.current_session;
  if (!current) return "Start Practice";
  if (current.status === "in_progress") return "Continue";
  if (current.status === "submitted") return "View Record";
  return "Start New Set";
}

export default function GroupPage() {
  const { t } = useLanguage();
  const params = useParams<{ groupId: string }>();
  const router = useRouter();
  const groupId = params.groupId;
  const [group, setGroup] = useState<PracticeGroup | null>(null);
  const [topics, setTopics] = useState<Topic[] | null>(null);
  const [starting, setStarting] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    Promise.all([
      apiGet<PracticeGroup>(`/practice-groups/${groupId}`),
      apiGet<Topic[]>(`/practice-groups/${groupId}/topics`),
    ])
      .then(([g, t]) => {
        if (!alive) return;
        setGroup(g);
        setTopics(t);
      })
      .catch((e: Error) => alive && setError(e.message));
    return () => {
      alive = false;
    };
  }, [groupId]);

  async function start(topic: Topic, restart: boolean) {
    if (group?.locked || topic.locked) return;
    setError(null);
    setStarting(topic.topic_id);
    try {
      const session = await apiPost<SessionPayload>("/practice-sessions", {
        source: "topic",
        group_id: groupId,
        topic_id: topic.topic_id,
        restart,
      });
      router.push(`/practice/session/${session.session.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start practice");
      setStarting(null);
    }
  }

  function openTopic(topic: Topic) {
    if (starting !== null || group?.locked || topic.locked) return;
    const current = topic.current_session;
    if (current && (current.status === "in_progress" || current.status === "submitted")) {
      router.push(`/practice/session/${current.id}`);
      return;
    }
    void start(topic, false);
  }

  if (!group && !error) {
    return <div className="skeleton h-40 w-full" />;
  }

  return (
    <div>
      <Link href="/practice" className="btn btn-ghost btn-sm -ml-2 mb-4">
        <ArrowLeft size={14} /> Back to Units
      </Link>

      <div className="page-head">
        <div>
          <div className="eyebrow">Unit {group?.unit_id}</div>
          <h1 className="h1">{group?.title_en || group?.title || "Unit Practice"}</h1>
          {group?.locked && (
            <p className="mt-2 inline-flex items-center gap-1.5 rounded-lg border border-[color-mix(in_srgb,var(--danger)_22%,var(--line))] bg-[var(--danger-soft)] px-2.5 py-1 text-[11.5px] text-[var(--danger)]">
              <LockKeyhole size={12} /> {t("需要激活码，章节暂不可开始")}
            </p>
          )}
          <p className="muted text-[13px] mt-2">
            {group?.question_count} practice questions · {group?.answered ?? 0} answered · Accuracy{" "}
            {group?.accuracy === null || group?.accuracy === undefined
              ? "—"
              : `${Math.round(group.accuracy * 100)}%`}
          </p>
        </div>
      </div>

      {error && <div className="feedback feedback-bad mb-4">{error}</div>}

      <div className="card card-pad">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="h2">Chapters</h2>
            <p className="text-[12px] muted mt-1">
              Click a chapter to resume. Choose “Practice Again” to start a new record from Question 1.
            </p>
          </div>
          <span className="pill">{topics?.length ?? 0} topics</span>
        </div>

        <div className="mt-3">
          {topics?.map((topic) => {
            const current = topic.current_session;
            const total = current?.total || topic.question_count;
            const answered = current?.answered ?? 0;
            const progress = total ? Math.round((answered / total) * 100) : 0;
            const status =
              current?.status === "submitted"
                ? "Completed"
                : current?.status === "in_progress"
                  ? "In Progress"
                  : current?.status === "abandoned"
                    ? "Ended Early"
                    : null;
            const detail = current
              ? current.status === "submitted"
                ? `Completed ${total}/${total} · ${current.correct} correct`
                : current.status === "in_progress"
                  ? `${answered}/${total} done · Continue at Question ${Math.min((current.next_index ?? answered) + 1, total)}`
                  : `Ended early · ${answered}/${total} answered`
              : `${topic.question_count} questions`;
            const locked = Boolean(group?.locked || topic.locked);
            return (
              <div
                key={topic.topic_id}
                role={locked ? undefined : "button"}
                tabIndex={locked ? -1 : 0}
                aria-disabled={locked}
                className={locked ? "topic-row" : "topic-row topic-row-clickable"}
                onClick={locked ? undefined : () => openTopic(topic)}
                onKeyDown={(e) => {
                  if (locked) return;
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    openTopic(topic);
                  }
                }}
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="pill font-mono">{topic.code}</span>
                    <span className="font-semibold text-[15px]" lang="en">
                      {topic.title_en}
                    </span>
                    {topic.kind !== "ced" && (
                      <span className="badge">
                        {topic.kind === "methods" ? "Research Methods" : "Other"}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-3 mt-2 text-[11px] faint flex-wrap">
                    <span>{detail}</span>
                    {status && <span>{status}</span>}
                    <span>
                      Cumulative {topic.answered}/{topic.total} ·{" "}
                      {topic.accuracy === null
                        ? "—"
                        : `${Math.round(topic.accuracy * 100)}%`}
                    </span>
                  </div>
                  <div className="progress mt-1.5 max-w-[320px]">
                    <i style={{ width: `${progress}%` }} />
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  {locked ? (
                    <span className="pill pill-locked" aria-label="Locked">
                      <LockKeyhole size={13} />
                    </span>
                  ) : (
                    <>
                      <button
                        className="btn btn-sm btn-ghost"
                        onClick={(e) => {
                          e.stopPropagation();
                          void start(topic, true);
                        }}
                        disabled={starting !== null || total === 0}
                      >
                        {starting === topic.topic_id ? (
                          <Loader2 size={13} className="animate-spin" />
                        ) : (
                          <RotateCcw size={13} />
                        )}
                        Practice Again
                      </button>
                      <span className="btn btn-sm pointer-events-none">
                        {sessionLabel(topic)}
                        <ArrowRight size={13} />
                      </span>
                    </>
                  )}
                </div>
              </div>
            );
          })}
          {topics?.length === 0 && <div className="empty">This Unit has no practice questions yet.</div>}
        </div>
      </div>
    </div>
  );
}
