"use client";

import {
  Check,
  Loader2,
  RotateCcw,
  Sparkles,
  Star,
  Volume2,
  X,
} from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { apiGet, apiPost } from "@/lib/api";
import { useLanguage } from "@/lib/i18n";
import type { FlashcardDeck, FlashcardNext } from "@/lib/types";

const UNIT_LABEL: Record<string, string> = {
  "0": "Research Methods",
  "1": "Unit 1",
  "2": "Unit 2",
  "3": "Unit 3",
  "4": "Unit 4",
  "5": "Unit 5",
  EM: "Research Methods",
};

function StarRow({ count, weight }: { count: number; weight: number }) {
  return (
    <span
      className="flashcard-stars"
      aria-label={`Importance ${count} of 5 stars`}
      title={`Concept weight ${weight.toFixed(1)}`}
    >
      {Array.from({ length: 5 }, (_, index) => {
        const filled = index < count;
        return (
          <Star
            key={index}
            size={13}
            strokeWidth={1.6}
            className={filled ? "filled" : ""}
            fill={filled ? "currentColor" : "none"}
          />
        );
      })}
    </span>
  );
}

export function FlashcardStudy({
  unit = "",
  minStars = 0,
  limit = 20,
  compact = false,
  showStats = true,
  showAllLink = true,
  custom = false,
  preview = false,
  continuous = false,
}: {
  unit?: string;
  minStars?: number;
  limit?: number;
  compact?: boolean;
  showStats?: boolean;
  showAllLink?: boolean;
  custom?: boolean;
  preview?: boolean;
  continuous?: boolean;
}) {
  const { t } = useLanguage();
  const [deck, setDeck] = useState<FlashcardDeck | null>(null);
  const [queue, setQueue] = useState<FlashcardNext | null>(null);
  const [index, setIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [known, setKnown] = useState(0);
  const [again, setAgain] = useState(0);
  const [loading, setLoading] = useState(true);
  const [rating, setRating] = useState<"known" | "again" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [speechSupported, setSpeechSupported] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const voicesRef = useRef<SpeechSynthesisVoice[]>([]);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const load = useCallback(async (resetSession = true, silent = false) => {
    if (!silent) setLoading(true);
    setError(null);
    if (!silent) setDeck(null);
    setIndex(0);
    setFlipped(false);
    if (resetSession) {
      setKnown(0);
      setAgain(0);
    }
    try {
      if (continuous && !preview) {
        const qs = new URLSearchParams();
        if (!custom) {
          if (unit) qs.set("unit_id", unit);
          if (minStars > 0) qs.set("min_stars", String(minStars));
        }
        const endpoint = custom ? "/flashcards/custom/next" : "/flashcards/next";
        const data = await apiGet<FlashcardNext>(`${endpoint}?${qs.toString()}`);
        setQueue(data);
        setDeck({
          cards: data.card ? [data.card] : [],
          stats: {
            total: data.total,
            due: data.due,
            new: data.new_remaining,
            reviewed: data.reviewed_today,
          },
          ahead: false,
        });
      } else {
        const qs = new URLSearchParams({ limit: String(limit) });
        if (!custom && !preview) {
          if (unit) qs.set("unit_id", unit);
          if (minStars > 0) qs.set("min_stars", String(minStars));
        }
        const endpoint = custom
          ? "/flashcards/custom/deck"
          : preview
            ? "/flashcards/preview"
            : "/flashcards";
        const data = await apiGet<FlashcardDeck>(`${endpoint}?${qs.toString()}`);
        setDeck(data);
        setQueue(null);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : t("加载卡片失败"));
      setDeck(null);
    } finally {
      if (!silent) setLoading(false);
    }
  }, [unit, minStars, limit, custom, preview, continuous, t]);

  useEffect(() => {
    void load(true);
  }, [load]);

  const card = deck?.cards[index];
  const continuousDone = continuous && Boolean(queue?.caught_up);
  const done = Boolean(deck && index >= deck.cards.length);
  const overdueDays = card?.next_due_at
    ? Math.max(
        0,
        Math.floor(
          (Date.now() - new Date(card.next_due_at).getTime()) / 86_400_000,
        ),
      )
    : 0;
  const canSpeak = Boolean(card?.audio_url) || speechSupported;

  useEffect(() => {
    if (typeof window === "undefined") return;
    const supported =
      "speechSynthesis" in window && "SpeechSynthesisUtterance" in window;
    setSpeechSupported(supported);
    if (!supported) return;

    const synth = window.speechSynthesis;
    const updateVoices = () => {
      voicesRef.current = synth.getVoices();
    };
    updateVoices();
    synth.addEventListener("voiceschanged", updateVoices);
    return () => {
      synth.removeEventListener("voiceschanged", updateVoices);
      synth.cancel();
    };
  }, []);

  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
    if (speechSupported) window.speechSynthesis.cancel();
    setSpeaking(false);
    return () => {
      if (audioRef.current) audioRef.current.pause();
      if (speechSupported) window.speechSynthesis.cancel();
    };
  }, [card?.concept_id, speechSupported]);

  function speakWithBrowser() {
    if (!card || !speechSupported) return;
    const synth = window.speechSynthesis;
    synth.cancel();
    const utterance = new SpeechSynthesisUtterance(card.term);
    utterance.lang = "en-US";
    utterance.rate = 0.9;
    utterance.pitch = 1;
    const voices = voicesRef.current.length
      ? voicesRef.current
      : synth.getVoices();
    const englishVoice =
      voices.find((voice) => /^en[-_]us/i.test(voice.lang)) ||
      voices.find((voice) => /^en/i.test(voice.lang));
    if (englishVoice) utterance.voice = englishVoice;
    setSpeaking(true);
    utterance.onend = () => setSpeaking(false);
    utterance.onerror = () => setSpeaking(false);
    synth.speak(utterance);
  }

  function speakTerm() {
    if (!card) return;
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
    if (speechSupported) window.speechSynthesis.cancel();

    if (card.audio_url) {
      const audio = new Audio(card.audio_url);
      audioRef.current = audio;
      audio.onended = () => setSpeaking(false);
      audio.onerror = () => {
        setSpeaking(false);
        speakWithBrowser();
      };
      setSpeaking(true);
      void audio.play().catch(() => {
        setSpeaking(false);
        speakWithBrowser();
      });
      return;
    }
    speakWithBrowser();
  }

  function toggleFlip() {
    setFlipped((value) => !value);
  }

  async function rate(value: "known" | "again") {
    if (!card || rating) return;
    setRating(value);
    setError(null);
    try {
      if (!preview) {
        const endpoint = custom
          ? `/flashcards/custom/${card.concept_id}/review`
          : `/flashcards/${card.concept_id}/review`;
        await apiPost(endpoint, { rating: value });
      }
      if (value === "known") setKnown((current) => current + 1);
      else setAgain((current) => current + 1);
      setFlipped(false);
      if (continuous && !preview) {
        await load(false, true);
      } else {
        setIndex((current) => current + 1);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : t("保存卡片进度失败"));
    } finally {
      setRating(null);
    }
  }

  if (loading) {
    return (
      <div
        className={
          preview
            ? "skeleton h-[320px] w-full"
            : compact
              ? "skeleton h-[330px] w-full"
              : "skeleton h-[430px] w-full"
        }
      />
    );
  }

  if (error && !deck) {
    return <div className="feedback feedback-bad text-[12.5px]">{error}</div>;
  }

  if (continuousDone) {
    return (
      <div className="card card-pad text-center">
        <div className="eyebrow">{t("今日学习完成")}</div>
        <h2 className="h1 text-[26px] mt-2">{t("今天到期的卡片已经复习完")}</h2>
        <p className="muted text-[13px] mt-2">
          {custom
            ? t("今日已复习 {n} 张", { n: queue?.reviewed_today ?? 0 })
            : t("今日新卡 {today} / {limit} · 今日已复习 {reviewed} 张", {
                today: queue?.new_today ?? 0,
                limit: queue?.new_limit ?? 0,
                reviewed: queue?.reviewed_today ?? 0,
              })}
        </p>
        {queue?.new_limit_reached && (
          <p className="muted text-[12.5px] mt-2">
            {t("今日新卡上限已到。到期卡片仍会按时间自动出现。")}
          </p>
        )}
        {queue?.next_due_at && (
          <p className="muted text-[12.5px] mt-2">
            {t("后续到期卡片会在到时间后重新进入队列。")}
          </p>
        )}
        <div className="flex flex-wrap justify-center gap-2 mt-5">
          <button className="btn btn-primary" onClick={() => void load(true)}>
            <RotateCcw size={15} /> {t("重新检查")}
          </button>
          {showAllLink && (
            <Link href="/cards" className="btn">
              {t("全部卡片")}
            </Link>
          )}
        </div>
      </div>
    );
  }

  if (!deck || deck.cards.length === 0) {
    return (
      <div className="card empty">
        <Sparkles size={26} className="mx-auto mb-2 text-[var(--faint)]" />
        {custom ? t("还没有创建任何卡片。") : t("当前筛选范围没有卡片。")}
      </div>
    );
  }

  if (done) {
    return (
      <div className="card card-pad text-center">
        <div className="eyebrow">{t("本组完成")}</div>
        <h2 className="h1 text-[26px] mt-2">{t("本组完成")}</h2>
        <p className="muted text-[13px] mt-2">
          {t("认识了 {known} 张 · 还不熟 {again} 张。没记住的卡片会更早再次出现。", {
            known,
            again,
          })}
        </p>
        <div className="flex flex-wrap justify-center gap-2 mt-5">
          <button className="btn btn-primary" onClick={() => void load(true)}>
            <RotateCcw size={15} /> {t("新一组")}
          </button>
          {showAllLink && (
            <Link href="/cards" className="btn">
              {t("全部卡片")}
            </Link>
          )}
        </div>
      </div>
    );
  }

  if (!card) return null;

  return (
    <div>
      {error && <div className="feedback feedback-bad text-[12.5px] mb-3">{error}</div>}

      {showStats && (
        <div className="flex flex-wrap items-center justify-between gap-2 text-[11.5px] muted mb-3">
          <span>
            {continuous && queue
              ? custom
                ? t("待复习 {due} · 新卡 {new}", {
                    due: queue.due,
                    new: queue.new_remaining,
                  })
                : t("待复习 {due} · 今日新卡 {today}/{limit}", {
                    due: queue.due,
                    today: queue.new_today,
                    limit: queue.new_limit,
                  })
              : t("本组 {n} 张 · 共 {total} 张", {
                  n: deck.cards.length,
                  total: deck.stats.total,
                })}
          </span>
          <span>
            {continuous && queue
              ? t("今日已复习 {reviewed} 张 · 本次 {session} 张", {
                  reviewed: queue.reviewed_today,
                  session: known + again,
                })
              : t("待复习 {due} · 新卡 {new} · 已复习 {reviewed}", {
                  due: deck.stats.due,
                  new: deck.stats.new,
                  reviewed: deck.stats.reviewed,
                })}
          </span>
        </div>
      )}

      {!preview && !continuous && (
        <>
          <div className="flex flex-wrap items-center justify-between gap-2 text-[12px] muted mb-2">
            <span>
              {index + 1} / {deck.cards.length}
            </span>
            <div className="flex items-center gap-2">
              <span>
                {t("认识了 {known} 张 · 还不熟 {again} 张", { known, again })}
              </span>
            </div>
          </div>
          <div className="progress mb-4">
            <i style={{ width: `${(index / deck.cards.length) * 100}%` }} />
          </div>
        </>
      )}

      {deck.ahead && (
        <div className="feedback text-[12px] mb-3">
          You are caught up for today. Showing the earliest upcoming cards.
        </div>
      )}

      <div className="flashcard-wrap">
        <button
          type="button"
          className={[
            "flashcard",
            compact ? "flashcard-compact" : "",
            flipped ? "flipped" : "",
          ].join(" ")}
          onClick={toggleFlip}
          aria-label={flipped ? t("显示术语") : t("显示释义")}
        >
          <div className="flashcard-inner">
            <div className="flashcard-face flashcard-front">
              {overdueDays > 0 && (
                <span className="badge badge-confusable mb-2">
                  {overdueDays} days overdue
                </span>
              )}
              <div
                className="eyebrow flashcard-origin"
                title={
                  custom
                    ? t("我的卡片")
                    : `${UNIT_LABEL[card.ap_unit || ""] || "AP Psychology"}${
                        card.topic ? ` · ${card.topic}` : ""
                      }`
                }
              >
                {custom ? t("我的卡片") : UNIT_LABEL[card.ap_unit || ""] || "AP Psychology"}
                {!custom && card.topic ? ` · ${card.topic}` : ""}
              </div>
              <div className="flashcard-term" lang="en">
                {card.term}
              </div>
              {card.ipa && (
                <div
                  className="flashcard-ipa"
                  lang="en"
                  aria-label={t("音标 {ipa}", { ipa: card.ipa })}
                  title={t("IPA 音标")}
                >
                  /{card.ipa}/
                </div>
              )}
              <div className="flashcard-hint">{t("点击翻面")}</div>
            </div>
            <div className="flashcard-face flashcard-back">
              <div className="flashcard-back-inner">
                <div className="flashcard-def" lang="en">
                  {card.definition || card.quote}
                </div>
                {card.definition && card.quote && (
                  <div className="flashcard-quote" lang="en">
                    {card.quote}
                  </div>
                )}
              </div>
            </div>
          </div>
        </button>

        <div className="flashcard-top-tools">
          {canSpeak && (
            <button
              type="button"
              className="flashcard-speak"
              onClick={speakTerm}
              disabled={speaking}
              aria-label={t("朗读术语")}
              title={t("朗读术语")}
            >
              {speaking ? (
                <Loader2 size={13} className="animate-spin" />
              ) : (
                <Volume2 size={13} />
              )}
              {t("朗读")}
            </button>
          )}
          {!custom && !flipped && <StarRow count={card.stars} weight={card.weight} />}
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3">
        <button
          className="btn"
          onClick={() => rate("again")}
          disabled={rating !== null}
        >
          {rating === "again" ? (
            <Loader2 size={15} className="animate-spin" />
          ) : (
            <X size={15} />
          )}
          Review Later
        </button>
        <button
          className="btn btn-primary"
          onClick={() => rate("known")}
          disabled={rating !== null}
        >
          {rating === "known" ? (
            <Loader2 size={15} className="animate-spin" />
          ) : (
            <Check size={15} />
          )}
          Already Know
        </button>
      </div>
      {!preview && (
        <p className="text-center text-[11px] faint mt-2">
          {t("点击卡片查看释义。可随时选择 Already Know 或 Review Later。")}
        </p>
      )}
    </div>
  );
}
