"use client";

import {
  AlertCircle,
  BookOpen,
  Check,
  Loader2,
  Play,
  RefreshCw,
  RotateCcw,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ConceptTags } from "@/components/ConceptTags";
import { Modal } from "@/components/Modal";
import { QuestionSourceLine } from "@/components/QuestionSourceLine";
import { QuestionView } from "@/components/QuestionView";
import { apiGet, apiPost } from "@/lib/api";
import { useLanguage } from "@/lib/i18n";
import type {
  SessionPayload,
  WrongQuestion,
  WrongQuestionDetail,
  WrongSummary,
} from "@/lib/types";

const TABS = [
  { key: "", label: "全部进行中" },
  { key: "learning", label: "未掌握" },
  { key: "reviewing", label: "复习中" },
  { key: "mastered", label: "已掌握" },
];

export default function WrongPage() {
  const { t } = useLanguage();
  const router = useRouter();
  const [tab, setTab] = useState("");
  const [allItems, setAllItems] = useState<WrongQuestion[] | null>(null);
  const [summary, setSummary] = useState<WrongSummary | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [openItem, setOpenItem] = useState<WrongQuestion | null>(null);
  const [detail, setDetail] = useState<WrongQuestionDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [removing, setRemoving] = useState<Set<string>>(new Set());

  useEffect(() => {
    let alive = true;
    setAllItems(null);
    setSummary(null);
    setOpenItem(null);
    setDetail(null);
    Promise.all([
      apiGet<WrongQuestion[]>("/me/wrong-questions?limit=200"),
      apiGet<WrongSummary>("/me/wrong-questions/summary"),
    ])
      .then(([items, stats]) => {
        if (!alive) return;
        setAllItems(items);
        setSummary(stats);
      })
      .catch((e: Error) => alive && setError(e.message));
    return () => {
      alive = false;
    };
  }, []);

  const activeFallback =
    allItems?.filter((item) => item.mastery !== "mastered").length ?? 0;
  const counts: Record<string, number> = {
    "": summary?.active ?? activeFallback,
    learning:
      summary?.learning ??
      allItems?.filter((item) => item.mastery === "learning").length ??
      0,
    reviewing:
      summary?.reviewing ??
      allItems?.filter((item) => item.mastery === "reviewing").length ??
      0,
    mastered:
      summary?.mastered ??
      allItems?.filter((item) => item.mastery === "mastered").length ??
      0,
  };
  const items = allItems
    ? allItems.filter((item) => {
        if (removing.has(item.question_id)) return true;
        return tab ? item.mastery === tab : item.mastery !== "mastered";
      })
    : null;
  const practiceCount = counts.learning + counts.reviewing;

  async function practice() {
    setBusy(true);
    setError(null);
    try {
      const session = await apiPost<SessionPayload>("/practice-sessions", {
        source: "wrong",
        count: 20,
      });
      router.push(`/practice/session/${session.session.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("错题练习启动失败"));
      setBusy(false);
    }
  }

  async function changeMastery(
    questionId: string,
    mastery: "mastered" | "learning",
  ) {
    if (removing.has(questionId)) return;
    setError(null);
    setRemoving((prev) => new Set(prev).add(questionId));
    try {
      const action = mastery === "mastered" ? "master" : "unmaster";
      await apiPost(`/me/wrong-questions/${questionId}/${action}`);
      window.setTimeout(() => {
        setAllItems((prev) =>
          prev
            ? prev.map((item) =>
                item.question_id === questionId ? { ...item, mastery } : item,
              )
            : prev,
        );
        setRemoving((prev) => {
          const next = new Set(prev);
          next.delete(questionId);
          return next;
        });
        apiGet<WrongSummary>("/me/wrong-questions/summary")
          .then(setSummary)
          .catch(() => undefined);
      }, 240);
    } catch (e) {
      setRemoving((prev) => {
        const next = new Set(prev);
        next.delete(questionId);
        return next;
      });
      setError(e instanceof Error ? e.message : t("操作失败"));
    }
  }

  async function openQuestion(item: WrongQuestion) {
    setOpenItem(item);
    setDetail(null);
    setDetailError(null);
    setDetailLoading(true);
    try {
      const data = await apiGet<WrongQuestionDetail>(
        `/me/wrong-questions/${item.question_id}`,
      );
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
      <div className="page-head">
        <div>
          <div className="eyebrow">{t("错题本")}</div>
          <h1 className="h1">{t("错题本")}</h1>
          <p className="muted text-[13px] mt-2">
            {t("答错的题目会自动记录。点击卡片查看完整题目、正确答案和解析。")}
          </p>
        </div>
      </div>

      <div className="card card-pad mb-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="eyebrow">{t("错题练习卷")}</div>
            <h2 className="h2 mt-1">{t("错题练习卷")}</h2>
            <p className="text-[13px] muted mt-1">
              {t("独立于原单元的错题练习卷，包含未掌握和复习中的题目。")}
            </p>
            <p className="text-[12px] faint mt-2">
              {t("{learning} 道未掌握 · {reviewing} 道复习中 · 已掌握题目不包含在内", {
                learning: counts.learning,
                reviewing: counts.reviewing,
              })}
            </p>
            <p className="text-[11.5px] muted mt-2 leading-5">
              {t("这份练习卷是动态的：新错题会自动加入，已掌握题目会移除，已作答进度会保留。")}
            </p>
            <p className="text-[11.5px] muted mt-1 leading-5">
              {t("复习中 = 答错后已经答对一次；再连续答对一次即可标记为已掌握。")}
            </p>
          </div>
          <button
            className="btn btn-primary w-full sm:w-auto"
            onClick={practice}
            disabled={busy || practiceCount === 0}
          >
            {busy ? (
              <RefreshCw size={15} className="animate-spin" />
            ) : (
              <Play size={15} />
            )}
            {practiceCount > 0 ? t("开始练习") : t("暂无可练习题目")}
          </button>
        </div>
      </div>

      <div className="flex gap-2 mb-4 flex-wrap">
        {TABS.map((item) => (
          <button
            key={item.key}
            className={item.key === tab ? "btn btn-sm btn-primary" : "btn btn-sm"}
            onClick={() => setTab(item.key)}
          >
            {t(item.label)}
            <span className="ml-1 text-[10px] opacity-70">{counts[item.key]}</span>
          </button>
        ))}
      </div>

      {error && <div className="feedback feedback-bad mb-4">{error}</div>}

      {!items && <div className="skeleton h-64 w-full" />}

      {items && items.length === 0 && (
        <div className="card empty">
          <AlertCircle size={26} className="mx-auto mb-2 text-[var(--faint)]" />
          {allItems && allItems.length > 0
            ? tab === ""
              ? t("当前没有进行中的错题。已掌握的题目在「已掌握」标签中。")
              : t("「{tab}」中没有题目。", {
                  tab: t(TABS.find((item) => item.key === tab)?.label || "全部进行中"),
                })
            : t("还没有错题。练习中答错的题目会自动出现在这里。")}
        </div>
      )}

      <div className="grid gap-3 md:grid-cols-2">
        {items?.map((item) => (
          <div
            key={item.question_id}
            className={[
              "card card-pad wrong-card",
              removing.has(item.question_id) ? "is-removing" : "",
            ].join(" ")}
          >
              <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="pill pill-warn">{t("错 {count} 次", { count: item.wrong_count })}</span>
                    <span className="badge">
                      {item.mastery === "mastered"
                        ? t("已掌握")
                        : item.mastery === "reviewing"
                          ? t("复习中")
                          : t("未掌握")}
                    </span>
                    {item.mastery === "reviewing" && (
                      <span className="badge badge-core">{t("再答对一次即掌握")}</span>
                    )}
                    {item.mastery === "learning" && (
                      <span className="badge">{t("答对一次进入复习中")}</span>
                    )}
                  </div>
                  <QuestionSourceLine
                    question={item}
                    className="text-[11px] muted mt-1.5 leading-4"
                  />
                  <div
                    className="mt-1.5 text-[14px] leading-6 whitespace-pre-wrap break-words"
                    lang="en"
                  >
                    {item.stem || item.question_id}
                  </div>
                </div>
                <div className="flex flex-wrap items-center justify-between gap-2 lg:flex-col lg:items-end">
                  {item.mastery === "mastered" ? (
                    <button
                      className="btn btn-sm"
                      onClick={() => changeMastery(item.question_id, "learning")}
                      disabled={removing.has(item.question_id)}
                    >
                      {removing.has(item.question_id) ? (
                        <Loader2 size={13} className="animate-spin" />
                      ) : (
                        <RotateCcw size={13} />
                      )}
                      {t("标记为未掌握")}
                    </button>
                  ) : (
                    <button
                      className="btn btn-sm"
                      onClick={() => changeMastery(item.question_id, "mastered")}
                      disabled={removing.has(item.question_id)}
                    >
                      {removing.has(item.question_id) ? (
                        <Loader2 size={13} className="animate-spin" />
                      ) : (
                        <Check size={13} />
                      )}
                      {t("标记为已掌握")}
                    </button>
                  )}
                  <span className="text-[10px] faint font-mono text-right">
                    {item.display_number ? `Q${item.display_number}` : ""}
                  </span>
                </div>
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
            {detail.question.concepts && detail.question.concepts.length > 0 && (
              <div className="card card-pad mb-3">
                <div className="text-[11px] faint mb-2">
                  {t("相关概念（点击查看详情）")}
                </div>
                <ConceptTags concepts={detail.question.concepts} limit={12} />
              </div>
            )}
            <QuestionView
              question={{
                ...detail.question,
                answered_at: detail.last_wrong_at || new Date().toISOString(),
                selected_label: null,
                is_correct: false,
                feedback: detail.question,
              }}
              onSelect={() => undefined}
              disabled
              resultLabel={t("你当时答错了")}
            />
            <div className="mt-3 text-[11px] faint">
              {t("错 {count} 次 · 正确答案与解析仅供复习", { count: openItem.wrong_count })}
            </div>
          </>
        )}
      </Modal>
    </div>
  );
}
