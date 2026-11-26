"use client";

import { Loader2 } from "lucide-react";
import { useEffect, useState } from "react";

import { Modal } from "@/components/Modal";
import { QuestionView } from "@/components/QuestionView";
import { apiGet } from "@/lib/api";
import { useLanguage } from "@/lib/i18n";
import type { Question } from "@/lib/types";

export function QaQuestionModal({
  open,
  threadId,
  onClose,
}: {
  open: boolean;
  threadId: string | null;
  onClose: () => void;
}) {
  const { t } = useLanguage();
  const [question, setQuestion] = useState<Question | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open || !threadId) return;
    let alive = true;
    setQuestion(null);
    setError(null);
    setLoading(true);
    apiGet<Question>(`/qa/threads/${threadId}/question`)
      .then((value) => {
        if (alive) setQuestion(value);
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
  }, [open, threadId]);

  return (
    <Modal open={open} onClose={onClose} title={t("题目详情")} wide>
      {loading ? (
        <div className="grid place-items-center py-16">
          <Loader2 size={24} className="animate-spin text-[var(--primary)]" />
        </div>
      ) : error ? (
        <div className="qa-error">{error}</div>
      ) : question ? (
        <div>
          <p className="mb-3 text-[11.5px] text-[var(--muted)]">
            {t("这里只显示题目内容，不包含答案和解析。")}
          </p>
          <QuestionView
            question={question}
            onSelect={() => {}}
            readOnly
          />
        </div>
      ) : null}
    </Modal>
  );
}
