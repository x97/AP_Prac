"use client";

import {
  ChevronLeft,
  ChevronRight,
  Loader2,
  MessageCircleQuestion,
  Search,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { useAdminSubject } from "@/components/AdminShell";
import { apiGet } from "@/lib/api";
import type { AdminQaThreadList } from "@/lib/types";

const LIMIT = 30;

function timeLabel(value: string) {
  return new Date(value).toLocaleString("zh-CN", {
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

export default function AdminQaPage() {
  const { subjectId, subject } = useAdminSubject();
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<AdminQaThreadList | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    const params = new URLSearchParams({
      subject: subjectId,
      limit: String(LIMIT),
      offset: String(offset),
    });
    if (unreadOnly) params.set("unread", "true");
    if (search) params.set("q", search);
    apiGet<AdminQaThreadList>(`/qa/threads?${params.toString()}`)
      .then((value) => {
        if (!alive) return;
        setData(value);
        setError(null);
      })
      .catch((e: Error) => {
        if (alive) setError(e.message);
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [subjectId, unreadOnly, search, offset]);

  useEffect(() => {
    setOffset(0);
  }, [subjectId, unreadOnly, search]);

  return (
    <div>
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="text-[11px] uppercase tracking-[0.14em] text-[var(--faint)]">
            Teacher Q&amp;A
          </div>
          <h1 className="mt-1 text-[27px] font-semibold tracking-[-0.03em]">
            老师答疑
          </h1>
          <p className="mt-1 max-w-[760px] text-[14px] leading-6 text-[var(--muted)]">
            学生在学习日历作业里提问后会出现在这里。回复后学生端会收到未读提醒；同一道题的提问对所有做这道题的同学可见。
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="a-badge">
            <MessageCircleQuestion size={13} /> {data?.total ?? 0} 条
          </span>
          <span className="a-badge">{subject?.name || subjectId}</span>
        </div>
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <div className="a-segment">
          <button
            type="button"
            className={unreadOnly ? "" : "is-active"}
            onClick={() => setUnreadOnly(false)}
          >
            全部
          </button>
          <button
            type="button"
            className={unreadOnly ? "is-active" : ""}
            onClick={() => setUnreadOnly(true)}
          >
            未读
          </button>
        </div>
        <form
          className="flex min-w-[260px] max-w-md flex-1 gap-2"
          onSubmit={(event) => {
            event.preventDefault();
            setSearch(query.trim());
          }}
        >
          <div className="relative flex-1">
            <Search
              size={15}
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--faint)]"
            />
            <input
              className="a-input pl-9"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="搜索学生、题干或提问内容"
            />
          </div>
          <button className="a-btn" type="submit">
            搜索
          </button>
        </form>
      </div>

      {error && <div className="a-error mb-4">{error}</div>}

      {loading && !data ? (
        <div className="grid place-items-center py-24">
          <Loader2 size={24} className="animate-spin text-[var(--primary)]" />
        </div>
      ) : data && data.threads.length > 0 ? (
        <>
          <div className="a-qa-list">
            {data.threads.map((thread) => (
              <Link
                key={thread.id}
                href={`/qa/${thread.id}`}
                className={`a-qa-card ${thread.unread ? "is-unread" : ""}`}
              >
                <div className="a-qa-card-main">
                  <div className="a-qa-card-meta">
                    {thread.unread && <span className="a-qa-dot" />}
                    <span className="a-qa-student">
                      {thread.student.nickname || "未命名学生"}
                    </span>
                    {thread.student.email_masked && (
                      <span className="text-[var(--faint)]">
                        {thread.student.email_masked}
                      </span>
                    )}
                    {thread.unread && (
                      <span className="a-badge a-badge-primary">新提问</span>
                    )}
                    {!thread.teacher_replied && !thread.unread && (
                      <span className="a-badge a-badge-warn">待回复</span>
                    )}
                    {thread.teacher_replied && (
                      <span className="a-badge a-badge-success">已回复</span>
                    )}
                    <span className="a-qa-time">{timeLabel(thread.last_reply_at)}</span>
                  </div>
                  <div className="a-qa-stem">
                    {thread.question_stem || "题目已从题库移除"}
                  </div>
                  <p className="a-qa-preview">
                    <span className="a-qa-preview-author">
                      {thread.last_message === thread.content
                        ? "学生提问"
                        : "最近消息"}
                      ：
                    </span>
                    {thread.last_message}
                  </p>
                  <div className="a-qa-context">
                    {thread.plan_title && <span>{thread.plan_title}</span>}
                    {thread.task_title && <span>· {thread.task_title}</span>}
                    {thread.homework_title && <span>· {thread.homework_title}</span>}
                    <span>· {thread.reply_count} 条回复</span>
                  </div>
                </div>
                <span className="a-qa-arrow">→</span>
              </Link>
            ))}
          </div>

          <div className="mt-4 flex items-center justify-between gap-3">
            <span className="text-[12px] text-[var(--muted)]">
              第 {offset + 1}–{Math.min(offset + LIMIT, data.total)} 条，共{" "}
              {data.total} 条
            </span>
            <div className="flex gap-2">
              <button
                type="button"
                className="a-btn a-btn-sm"
                disabled={offset === 0}
                onClick={() => setOffset(Math.max(0, offset - LIMIT))}
              >
                <ChevronLeft size={14} /> 上一页
              </button>
              <button
                type="button"
                className="a-btn a-btn-sm"
                disabled={offset + LIMIT >= data.total}
                onClick={() => setOffset(offset + LIMIT)}
              >
                下一页 <ChevronRight size={14} />
              </button>
            </div>
          </div>
        </>
      ) : (
        <div className="a-card grid place-items-center px-6 py-16 text-center">
          <MessageCircleQuestion size={28} className="mb-3 text-[var(--faint)]" />
          <div className="text-[14px] font-medium">
            {unreadOnly || search ? "没有符合条件的提问" : "还没有学生提问"}
          </div>
          <p className="mt-1 max-w-md text-[12.5px] leading-6 text-[var(--muted)]">
            学生只能在「学习日历」的课堂作业题目下提问；普通练习题目没有答疑入口。
          </p>
        </div>
      )}
    </div>
  );
}
