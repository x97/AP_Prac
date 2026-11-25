"use client";

import { ArrowLeft, Clock3, Loader2, Send } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { apiGet, apiPost } from "@/lib/api";
import type { AdminQaReply, AdminQaThread } from "@/lib/types";

function timeLabel(value: string) {
  return new Date(value).toLocaleString("zh-CN", {
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

function MessageRow({ reply }: { reply: AdminQaReply }) {
  return (
    <div className={`a-qa-message ${reply.is_teacher ? "is-teacher" : ""}`}>
      <div className="a-qa-message-head">
        <span className="a-qa-message-avatar">
          {reply.is_teacher ? "师" : reply.author_name.slice(0, 1)}
        </span>
        <span className="a-qa-message-name">
          {reply.is_teacher ? (
            <span className="a-qa-teacher-tag">老师</span>
          ) : (
            reply.author_name
          )}
        </span>
        <span className="a-qa-message-time">{timeLabel(reply.created_at)}</span>
      </div>
      <div className="a-qa-message-body">{reply.content}</div>
    </div>
  );
}

export default function AdminQaThreadPage() {
  const params = useParams<{ threadId: string }>();
  const [thread, setThread] = useState<AdminQaThread | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);

  const load = useCallback(async () => {
    try {
      const value = await apiGet<AdminQaThread>(`/qa/threads/${params.threadId}`);
      setThread(value);
      setError(null);
      window.dispatchEvent(new Event("ap:admin-qa-read"));
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }, [params.threadId]);

  useEffect(() => {
    load();
  }, [load]);

  async function send() {
    if (!draft.trim()) return;
    setSending(true);
    setError(null);
    try {
      await apiPost(`/qa/threads/${params.threadId}/replies`, {
        content: draft.trim(),
      });
      setDraft("");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "发送失败");
    } finally {
      setSending(false);
    }
  }

  if (loading && !thread) {
    return (
      <div className="grid place-items-center py-24">
        <Loader2 size={24} className="animate-spin text-[var(--primary)]" />
      </div>
    );
  }

  if (!thread) {
    return (
      <div>
        <Link href="/qa" className="a-btn a-btn-sm mb-4">
          <ArrowLeft size={14} /> 老师答疑
        </Link>
        <div className="a-error">{error || "提问不存在"}</div>
      </div>
    );
  }

  const replies = thread.replies || [];

  return (
    <div>
      <Link href="/qa" className="a-btn a-btn-sm mb-4">
        <ArrowLeft size={14} /> 老师答疑
      </Link>

      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="text-[11px] uppercase tracking-[0.14em] text-[var(--faint)]">
            Teacher Q&amp;A · {thread.student.nickname || "未命名学生"}
          </div>
          <h1 className="mt-1 text-[25px] font-semibold tracking-[-0.03em]">
            答疑详情
          </h1>
        </div>
        <div className="flex items-center gap-2">
          {thread.unread ? (
            <span className="a-badge a-badge-primary">新提问</span>
          ) : thread.teacher_replied ? (
            <span className="a-badge a-badge-success">已回复</span>
          ) : (
            <span className="a-badge a-badge-warn">待回复</span>
          )}
          <span className="a-badge">
            <Clock3 size={12} /> {timeLabel(thread.created_at)}
          </span>
        </div>
      </div>

      {error && <div className="a-error mb-4">{error}</div>}

      <div className="a-qa-layout">
        <div className="flex min-w-0 flex-col gap-4">
          <section className="a-card a-qa-question">
            <div className="a-qa-question-label">题目</div>
            <p className="a-qa-question-stem">
              {thread.question_stem || "题目已从题库移除"}
            </p>
            <div className="a-qa-context">
              {thread.plan_title && <span>{thread.plan_title}</span>}
              {thread.task_title && <span>· {thread.task_title}</span>}
              {thread.homework_title && <span>· {thread.homework_title}</span>}
            </div>
          </section>

          <section className="a-card a-qa-thread">
            <div className="a-qa-thread-head">
              <h2>对话 · {thread.reply_count} 条回复</h2>
              <span className="text-[11px] text-[var(--faint)]">
                最近更新 {timeLabel(thread.last_reply_at)}
              </span>
            </div>

            <div className="a-qa-messages">
              <MessageRow
                reply={{
                  id: `${thread.id}-question`,
                  author_type: "student",
                  is_teacher: false,
                  author_name: thread.student.nickname || "匿名同学",
                  content: thread.content,
                  created_at: thread.created_at,
                }}
              />
              {replies.map((reply) => (
                <MessageRow key={reply.id} reply={reply} />
              ))}
            </div>

            <div className="a-qa-composer">
              <textarea
                className="a-input a-qa-textarea"
                placeholder="回复学生，可用 Command/Ctrl + Enter 发送…"
                value={draft}
                maxLength={5000}
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={(event) => {
                  if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
                    event.preventDefault();
                    send();
                  }
                }}
              />
              <div className="mt-2 flex items-center justify-between gap-3">
                <span className="text-[11px] text-[var(--faint)]">
                  {draft.length}/5000 · 回复后学生会看到未读提醒
                </span>
                <button
                  type="button"
                  className="a-btn a-btn-primary"
                  disabled={sending || !draft.trim()}
                  onClick={send}
                >
                  <Send size={14} /> {sending ? "发送中…" : "发送回复"}
                </button>
              </div>
            </div>
          </section>
        </div>

        <aside className="flex flex-col gap-4">
          <section className="a-card p-4">
            <div className="flex items-center gap-3">
              <span className="a-qa-student-avatar">
                {(thread.student.nickname || "匿").slice(0, 1)}
              </span>
              <div className="min-w-0">
                <div className="truncate text-[14px] font-semibold">
                  {thread.student.nickname || "未命名学生"}
                </div>
                <div className="text-[11.5px] text-[var(--muted)]">提问学生</div>
              </div>
            </div>
            <dl className="a-qa-facts">
              {thread.student.email_masked && (
                <div>
                  <dt>邮箱</dt>
                  <dd>{thread.student.email_masked}</dd>
                </div>
              )}
              {thread.student.phone_masked && (
                <div>
                  <dt>手机</dt>
                  <dd>{thread.student.phone_masked}</dd>
                </div>
              )}
              <div>
                <dt>提问时间</dt>
                <dd>{timeLabel(thread.created_at)}</dd>
              </div>
              <div>
                <dt>题目 ID</dt>
                <dd className="font-mono text-[11px]">{thread.question_id}</dd>
              </div>
            </dl>
            <Link
              href={`/students/${thread.student.id}`}
              className="a-btn a-btn-sm mt-4 w-full"
            >
              查看学生详情
            </Link>
          </section>

          <section className="a-card p-4">
            <div className="text-[11px] font-semibold uppercase tracking-[0.1em] text-[var(--faint)]">
              可见范围
            </div>
            <p className="mt-2 text-[12.5px] leading-6 text-[var(--muted)]">
              这条提问和你的回复会显示给所有做这道学习日历作业题目的学生。请避免在回复中透露学生个人隐私。
            </p>
          </section>
        </aside>
      </div>
    </div>
  );
}
