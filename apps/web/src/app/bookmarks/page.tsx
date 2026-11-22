"use client";

import { Bookmark, BookmarkX, BookOpen, Loader2, Play, RefreshCw } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ConceptTags } from "@/components/ConceptTags";
import { Modal } from "@/components/Modal";
import { QuestionSourceLine } from "@/components/QuestionSourceLine";
import { QuestionView } from "@/components/QuestionView";
import { apiDelete, apiGet, apiPost } from "@/lib/api";
import { useLanguage } from "@/lib/i18n";
import type {
  Bookmark as BookmarkType,
  Feedback,
  SessionPayload,
} from "@/lib/types";

export default function BookmarksPage() {
  const { t } = useLanguage();
  const router = useRouter();
  const [items, setItems] = useState<BookmarkType[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [openItem, setOpenItem] = useState<BookmarkType | null>(null);
  const [detail, setDetail] = useState<Feedback | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  useEffect(() => {
    apiGet<BookmarkType[]>("/me/bookmarks?limit=200")
      .then(setItems)
      .catch((e: Error) => setError(e.message));
  }, []);

  async function practice() {
    setBusy(true);
    setError(null);
    try {
      const session = await apiPost<SessionPayload>("/practice-sessions", {
        source: "bookmark",
        count: 20,
      });
      router.push(`/practice/session/${session.session.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("收藏练习启动失败"));
      setBusy(false);
    }
  }

  async function remove(questionId: string) {
    if (!window.confirm(t("移除这道题的收藏？"))) return;
    try {
      await apiDelete(`/me/bookmarks/${questionId}`);
      setItems((prev) => (prev ? prev.filter((x) => x.question_id !== questionId) : prev));
    } catch (e) {
      setError(e instanceof Error ? e.message : t("移除收藏失败"));
    }
  }

  async function openQuestion(item: BookmarkType) {
    setOpenItem(item);
    setDetail(null);
    setDetailError(null);
    setDetailLoading(true);
    try {
      const data = await apiGet<Feedback>(`/me/questions/${item.question_id}`);
      setDetail(data);
    } catch (e) {
      setDetailError(e instanceof Error ? e.message : t("题目加载失败"));
    } finally {
      setDetailLoading(false);
    }
  }

  function closeQuestion() {
    setOpenItem(null);
    setDetail(null);
    setDetailError(null);
  }

  return (
    <div>
      <div className="page-head flex-wrap">
        <div>
          <div className="eyebrow">{t("收藏题目")}</div>
          <h1 className="h1">{t("收藏题目")}</h1>
          <p className="muted text-[13px] mt-2">
            {t("长期收藏的题目，与考试中的「标记待复查」分开。")}
          </p>
        </div>
        <button className="btn btn-primary w-full sm:w-auto" onClick={practice} disabled={busy}>
          {busy ? <RefreshCw size={15} className="animate-spin" /> : <Play size={15} />}
          {t("练习收藏题目")}
        </button>
      </div>

      {error && <div className="feedback feedback-bad mb-4">{error}</div>}
      {!items && <div className="skeleton h-56 w-full" />}
      {items && items.length === 0 && (
        <div className="card empty">
          <Bookmark size={26} className="mx-auto mb-2 text-[var(--faint)]" />
          {t("还没有收藏题目。练习时点题目右上角的「收藏」即可加入。")}
        </div>
      )}

      <div className="space-y-3">
        {items?.map((item) => (
          <div key={item.question_id} className="card card-pad">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="pill">
                    {item.section || "Question"}{" "}
                    {item.display_number ? `Q${item.display_number}` : ""}
                  </span>
                  <QuestionSourceLine
                    question={item}
                    className="min-w-0 text-[11px] faint leading-4"
                  />
                </div>
                <div className="mt-2 text-[14px] leading-6 line-clamp-3 break-words" lang="en">
                  {item.stem || item.question_id}
                </div>
              </div>
              <button
                className="btn btn-sm shrink-0 self-end lg:self-auto"
                onClick={() => remove(item.question_id)}
              >
                <BookmarkX size={13} /> {t("移除收藏")}
              </button>
            </div>

            <div className="mt-3 flex flex-col gap-2 border-t border-[var(--line)] pt-3 sm:flex-row sm:items-center sm:justify-between">
              <button
                className="btn btn-sm btn-outline-primary w-full justify-center sm:w-auto"
                onClick={() => openQuestion(item)}
              >
                <BookOpen size={14} />
                {t("查看题目、答案与解析")}
              </button>
              <span className="text-center text-[11px] faint sm:text-right">
                {t("弹窗查看")}
              </span>
            </div>
          </div>
        ))}
      </div>

      <Modal
        open={Boolean(openItem)}
        onClose={closeQuestion}
        title={
          openItem?.display_number
            ? t("题目回顾 · Q{number}", { number: openItem.display_number })
            : t("题目回顾")
        }
        wide
      >
        {detailLoading && <div className="skeleton h-64 w-full" />}
        {detailError && (
          <div className="feedback feedback-bad text-[13px]">{detailError}</div>
        )}
        {detail && openItem && (
          <>
            <QuestionSourceLine
              question={openItem}
              className="text-[11.5px] muted mb-2 leading-4"
            />
            {detail.concepts && detail.concepts.length > 0 && (
              <div className="card card-pad mb-3">
                <div className="text-[11px] faint mb-2">
                  {t("相关概念（点击查看详情）")}
                </div>
                <ConceptTags concepts={detail.concepts} limit={12} />
              </div>
            )}
            <QuestionView
              question={{
                ...detail,
                answered_at: new Date().toISOString(),
                selected_label: null,
                is_correct: false,
                feedback: detail,
              }}
              onSelect={() => undefined}
              disabled
              readOnly
              resultLabel={t("收藏题目回顾")}
              resultTone="neutral"
            />
          </>
        )}
      </Modal>
    </div>
  );
}
