"use client";

import { Loader2, MessageCircleQuestion, Send } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { QaThreadCard } from "@/components/qa/QaThreadCard";
import { apiGet, apiPost } from "@/lib/api";
import { useLanguage } from "@/lib/i18n";
import type { QaQuestionThreads } from "@/lib/types";

export function QaPanel({
  sessionId,
  questionId,
}: {
  sessionId: string;
  questionId: string;
}) {
  const { t } = useLanguage();
  const [data, setData] = useState<QaQuestionThreads | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [replyingId, setReplyingId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const value = await apiGet<QaQuestionThreads>(
        `/qa/questions/${questionId}?session_id=${encodeURIComponent(sessionId)}`,
      );
      setData(value);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("加载答疑失败"));
    } finally {
      setLoading(false);
    }
  }, [questionId, sessionId, t]);

  useEffect(() => {
    load();
  }, [load]);

  async function ask() {
    if (!draft.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      await apiPost("/qa/questions", {
        session_id: sessionId,
        question_id: questionId,
        content: draft.trim(),
      });
      setDraft("");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("提问失败"));
    } finally {
      setSubmitting(false);
    }
  }

  async function reply(threadId: string, content: string) {
    setReplyingId(threadId);
    try {
      await apiPost(`/qa/threads/${threadId}/replies`, { content });
      await load();
    } finally {
      setReplyingId(null);
    }
  }

  return (
    <div className="qa-panel">
      <div className="qa-panel-head">
        <div>
          <h3 className="text-[13.5px] font-semibold">{t("老师答疑")}</h3>
          <p className="mt-0.5 text-[11px] text-[var(--muted)]">
            {t("提问会公开显示给做这道题的同学；老师回复后会出现在这里。")}
          </p>
        </div>
        {data && data.threads.length > 0 && (
          <span className="pill">{data.threads.length} {t("条提问")}</span>
        )}
      </div>

      {error && <div className="qa-error">{error}</div>}

      {loading ? (
        <div className="grid place-items-center py-10">
          <Loader2 size={20} className="animate-spin text-[var(--primary)]" />
        </div>
      ) : data && data.threads.length > 0 ? (
        <div className="qa-thread-list">
          {data.threads.map((thread) => (
            <QaThreadCard
              key={thread.id}
              thread={thread}
              onReply={reply}
              replying={replyingId === thread.id}
            />
          ))}
        </div>
      ) : (
        <div className="qa-empty">
          <MessageCircleQuestion size={24} className="mx-auto mb-2 text-[var(--faint)]" />
          {t("还没有同学提问，你可以成为第一个。")}
        </div>
      )}

      <div className="qa-composer">
        <textarea
          className="input min-h-[84px]"
          placeholder={t("关于这道题，想问老师什么？")}
          value={draft}
          maxLength={5000}
          onChange={(event) => setDraft(event.target.value)}
        />
        <div className="qa-composer-actions">
          <span className="text-[10.5px] text-[var(--faint)]">
            {draft.length}/5000
          </span>
          <button
            type="button"
            className="btn btn-primary btn-sm"
            disabled={submitting || !draft.trim()}
            onClick={ask}
          >
            <Send size={13} />
            {submitting ? t("提交中…") : t("提问老师")}
          </button>
        </div>
      </div>
    </div>
  );
}
