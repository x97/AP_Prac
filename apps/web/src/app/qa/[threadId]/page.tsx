"use client";

import { ArrowLeft, Loader2 } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { QaThreadCard } from "@/components/qa/QaThreadCard";
import { apiGet, apiPost } from "@/lib/api";
import { useLanguage } from "@/lib/i18n";
import type { QaThreadDetail } from "@/lib/types";

export default function QaThreadPage() {
  const params = useParams<{ threadId: string }>();
  const { t } = useLanguage();
  const [thread, setThread] = useState<QaThreadDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [replying, setReplying] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const value = await apiGet<QaThreadDetail>(`/qa/threads/${params.threadId}`);
      setThread(value);
      window.dispatchEvent(new Event("ap:qa-read"));
    } catch (e) {
      setError(e instanceof Error ? e.message : t("加载失败"));
    } finally {
      setLoading(false);
    }
  }, [params.threadId, t]);

  useEffect(() => {
    load();
  }, [load]);

  async function reply(threadId: string, content: string) {
    setReplying(true);
    try {
      await apiPost(`/qa/threads/${threadId}/replies`, { content });
      await load();
    } finally {
      setReplying(false);
    }
  }

  if (loading && !thread) {
    return (
      <div className="grid place-items-center py-24">
        <Loader2 size={24} className="animate-spin text-[var(--primary)]" />
      </div>
    );
  }

  return (
    <div>
      <Link href="/qa" className="btn btn-sm mb-4">
        <ArrowLeft size={14} /> {t("老师答疑")}
      </Link>

      {error && <div className="qa-error">{error}</div>}

      {thread ? (
        <>
          <div className="page-head">
            <div>
              <div className="eyebrow">Teacher Q&amp;A</div>
              <h1 className="h1 mt-1">{t("提问详情")}</h1>
            </div>
          </div>
          <div className="qa-context card card-pad mb-4">
            <div className="text-[11px] uppercase tracking-[0.1em] text-[var(--faint)]">
              {t("题目")}
            </div>
            <p className="mt-1 text-[13px] leading-6">
              {thread.question_stem || t("题目已从题库移除")}
            </p>
            <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-[var(--muted)]">
              {thread.plan_title && <span>{thread.plan_title}</span>}
              {thread.task_title && <span>· {thread.task_title}</span>}
              {thread.homework_title && <span>· {thread.homework_title}</span>}
            </div>
          </div>
          <QaThreadCard thread={thread} onReply={reply} replying={replying} />
        </>
      ) : null}
    </div>
  );
}
