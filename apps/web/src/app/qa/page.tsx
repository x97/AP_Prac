"use client";

import {
  ArrowRight,
  ChevronLeft,
  ChevronRight,
  Eye,
  Loader2,
  MessageCircleQuestion,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { QaQuestionModal } from "@/components/qa/QaQuestionModal";
import { apiGet } from "@/lib/api";
import { useLanguage } from "@/lib/i18n";
import type { QaMyThreadList } from "@/lib/types";

const LIMIT = 20;

function timeLabel(value: string) {
  return new Date(value).toLocaleString("zh-CN", {
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

export default function QaListPage() {
  const { t } = useLanguage();
  const [data, setData] = useState<QaMyThreadList | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [offset, setOffset] = useState(0);
  const [refreshKey, setRefreshKey] = useState(0);
  const [questionThreadId, setQuestionThreadId] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    apiGet<QaMyThreadList>(`/qa/my-threads?limit=${LIMIT}&offset=${offset}`)
      .then((value) => alive && setData(value))
      .catch((e: Error) => alive && setError(e.message))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [offset, refreshKey]);

  useEffect(() => {
    function onRead() {
      setRefreshKey((value) => value + 1);
    }
    window.addEventListener("ap:qa-read", onRead);
    return () => window.removeEventListener("ap:qa-read", onRead);
  }, []);

  const total = data?.total ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / LIMIT));
  const page = Math.floor(offset / LIMIT) + 1;

  function goToOffset(next: number) {
    setOffset(Math.max(0, next));
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  return (
    <div>
      <div className="page-head">
        <div>
          <div className="eyebrow">Teacher Q&amp;A</div>
          <h1 className="h1 mt-1">{t("老师答疑")}</h1>
          <p className="mt-1 text-[12.5px] muted">
            {t("这里汇总你在学习日历作业里向老师提过的问题和回复。")}
          </p>
        </div>
        <span className="pill">{data?.total ?? 0} {t("条提问")}</span>
      </div>

      {error && <div className="qa-error">{error}</div>}

      {loading && !data ? (
        <div className="grid place-items-center py-24">
          <Loader2 size={24} className="animate-spin text-[var(--primary)]" />
        </div>
      ) : data && data.threads.length > 0 ? (
        <>
          <div className={`qa-list ${loading ? "is-loading" : ""}`}>
            {data.threads.map((thread) => (
              <div key={thread.id} className="qa-list-card">
                <div className="qa-list-main">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="qa-list-title line-clamp-2">
                      {thread.question_stem || t("题目已从题库移除")}
                    </span>
                    {thread.unread && (
                      <span className="qa-unread-badge">{t("新回复")}</span>
                    )}
                    {!thread.teacher_replied && (
                      <span className="pill">{t("等待老师回复")}</span>
                    )}
                  </div>
                  <div className="qa-list-meta">
                    {thread.plan_title && <span>{thread.plan_title}</span>}
                    {thread.task_title && <span>· {thread.task_title}</span>}
                    <span>· {timeLabel(thread.last_reply_at)}</span>
                  </div>
                  <p className="qa-list-preview">{thread.last_message}</p>
                </div>
                <div className="qa-list-actions">
                  <button
                    type="button"
                    className="btn btn-sm"
                    onClick={() => setQuestionThreadId(thread.id)}
                  >
                    <Eye size={13} /> {t("查看题目")}
                  </button>
                  <Link
                    href={`/qa/${thread.id}`}
                    className="btn btn-sm btn-primary"
                  >
                    {t("详情")} <ArrowRight size={13} />
                  </Link>
                </div>
              </div>
            ))}
          </div>

          {total > 0 && (
            <div className="qa-pagination">
              <span className="qa-pagination-info">
                {loading && <Loader2 size={13} className="animate-spin" />}
                {t("第 {page} / {pages} 页 · 共 {total} 条", {
                  page,
                  pages: pageCount,
                  total,
                })}
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  className="btn btn-sm"
                  disabled={offset === 0 || loading}
                  onClick={() => goToOffset(offset - LIMIT)}
                >
                  <ChevronLeft size={14} /> {t("上一页")}
                </button>
                <button
                  type="button"
                  className="btn btn-sm"
                  disabled={page >= pageCount || loading}
                  onClick={() => goToOffset(offset + LIMIT)}
                >
                  {t("下一页")} <ChevronRight size={14} />
                </button>
              </div>
            </div>
          )}
        </>
      ) : (
        <div className="card empty">
          <MessageCircleQuestion size={26} className="mx-auto mb-2 text-[var(--faint)]" />
          <div>{t("还没有提问")}</div>
          <p className="mt-1 text-[12px]">
            {t("只有学习日历里的作业题目可以向老师提问。")}
          </p>
        </div>
      )}

      <QaQuestionModal
        open={Boolean(questionThreadId)}
        threadId={questionThreadId}
        onClose={() => setQuestionThreadId(null)}
      />
    </div>
  );
}
