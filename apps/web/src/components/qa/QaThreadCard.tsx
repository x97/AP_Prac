"use client";

import { CornerDownRight, MessageCircle, Send } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { useLanguage } from "@/lib/i18n";
import type { QaReply, QaThread } from "@/lib/types";

function timeLabel(value: string) {
  return new Date(value).toLocaleString("zh-CN", {
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

function ReplyRow({ reply }: { reply: QaReply }) {
  return (
    <div className={`qa-reply ${reply.is_teacher ? "is-teacher" : ""}`}>
      <div className="qa-reply-head">
        <span className="qa-reply-name">
          {reply.is_teacher ? (
            <span className="qa-teacher-badge">老师</span>
          ) : (
            reply.author_name
          )}
        </span>
        <span className="qa-reply-time">{timeLabel(reply.created_at)}</span>
      </div>
      <div className="qa-reply-body">{reply.content}</div>
    </div>
  );
}

export function QaThreadCard({
  thread,
  onReply,
  replying = false,
}: {
  thread: QaThread;
  onReply?: (threadId: string, content: string) => Promise<void>;
  replying?: boolean;
}) {
  const { t } = useLanguage();
  const [reply, setReply] = useState("");
  const [open, setOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submitReply() {
    if (!onReply || !reply.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      await onReply(thread.id, reply.trim());
      setReply("");
      setOpen(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("发送失败"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <article className={`qa-thread ${thread.is_mine ? "is-mine" : ""}`}>
      <header className="qa-thread-head">
        <span className="qa-avatar">{thread.student.nickname.slice(0, 1)}</span>
        <span className="qa-thread-author">{thread.student.nickname}</span>
        {thread.is_mine && <span className="pill pill-primary">{t("我的提问")}</span>}
        {!thread.teacher_replied && (
          <span className="pill">{t("等待老师回复")}</span>
        )}
        <span className="qa-thread-time">{timeLabel(thread.created_at)}</span>
      </header>
      <div className="qa-thread-question">{thread.content}</div>
      {thread.is_mine && thread.teacher_replied && (
        <div className="qa-thread-actions">
          {thread.unread && (
            <span className="qa-unread-badge">{t("新回复")}</span>
          )}
          <Link href={`/qa/${thread.id}`} className="qa-thread-detail-link">
            {t("查看消息详情")} <span aria-hidden="true">→</span>
          </Link>
        </div>
      )}
      {thread.replies.length > 0 && (
        <div className="qa-replies">
          {thread.replies.map((item) => (
            <ReplyRow key={item.id} reply={item} />
          ))}
        </div>
      )}
      {thread.is_mine && onReply && (
        <div className="qa-followup">
          {!open ? (
            <button
              type="button"
              className="qa-followup-toggle"
              onClick={() => setOpen(true)}
            >
              <CornerDownRight size={13} /> {t("追问老师")}
            </button>
          ) : (
            <div className="qa-composer is-compact">
              <textarea
                className="input min-h-[72px]"
                placeholder={t("补充你的问题…")}
                value={reply}
                maxLength={5000}
                onChange={(event) => setReply(event.target.value)}
              />
              {error && <div className="qa-error">{error}</div>}
              <div className="qa-composer-actions">
                <button
                  type="button"
                  className="btn btn-sm btn-ghost"
                  onClick={() => setOpen(false)}
                >
                  {t("取消")}
                </button>
                <button
                  type="button"
                  className="btn btn-sm btn-primary"
                  disabled={submitting || replying || !reply.trim()}
                  onClick={submitReply}
                >
                  <Send size={13} />
                  {submitting ? t("发送中…") : t("发送追问")}
                </button>
              </div>
            </div>
          )}
        </div>
      )}
      {!thread.replies.length && !thread.is_mine && (
        <div className="qa-empty-replies">
          <MessageCircle size={13} /> {t("还没有老师回复")}
        </div>
      )}
    </article>
  );
}
