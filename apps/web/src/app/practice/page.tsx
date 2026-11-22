"use client";

import { AlertCircle, ArrowRight, BookOpen, Layers, LockKeyhole } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { apiGet } from "@/lib/api";
import { useLanguage } from "@/lib/i18n";
import type { PracticeGroup } from "@/lib/types";

export default function PracticePage() {
  const { t, lang } = useLanguage();
  const [groups, setGroups] = useState<PracticeGroup[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadGroups = useCallback(() => {
    apiGet<PracticeGroup[]>("/practice-groups")
      .then(setGroups)
      .catch((e: Error) => setError(e.message));
  }, []);

  useEffect(() => {
    loadGroups();
  }, [loadGroups]);

  return (
    <div>
      <div className="page-head">
        <div>
          <div className="eyebrow">{t("单元练习")}</div>
          <h1 className="h1">{t("按 Unit 练习")}</h1>
          <p className="muted text-[13px] mt-2">
            {t("先选择 Unit，再选择章节。答题后即时判分，右侧同步显示相关概念。")}
          </p>
        </div>
        <span className="pill">
          <Layers size={13} /> {t("{count} 个 Unit", { count: groups?.length ?? 5 })}
        </span>
      </div>

      <Link
        href="/wrong"
        className="card card-pad mb-4 flex items-center justify-between gap-4"
      >
        <div className="flex items-center gap-3">
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-[var(--danger-soft)] text-[var(--danger)]">
            <AlertCircle size={18} />
          </span>
          <div>
            <div className="font-semibold text-[14px]">{t("错题练习卷")}</div>
            <div className="text-[12px] muted mt-0.5">
              {t("独立的错题练习卷，包含未掌握和复习中的题目，并随错题本更新。")}
            </div>
          </div>
        </div>
        <ArrowRight size={16} className="text-[var(--danger)] shrink-0" />
      </Link>

      {error && <div className="feedback feedback-bad">{error}</div>}
      {!groups && (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {[0, 1, 2, 3, 4].map((i) => (
            <div key={i} className="card card-pad h-44 skeleton" />
          ))}
        </div>
      )}

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {groups?.map((g) => {
          const progress = g.total ? Math.round((g.answered / g.total) * 100) : 0;
          const inner = (
            <>
              <div className="flex items-center justify-between gap-3">
                <span className={g.locked ? "pill pill-locked" : "pill pill-primary"}>
                  {g.locked && <LockKeyhole size={11} />} Unit {g.unit_id}
                </span>
                {g.locked ? (
                  <LockKeyhole size={18} className="text-[var(--danger)]" strokeWidth={2.2} />
                ) : (
                  <BookOpen size={16} className="text-[var(--muted)]" />
                )}
              </div>
              <h2 className="h2 mt-4" lang={lang}>
                {lang === "zh" ? g.title || g.title_en : g.title_en || g.title}
              </h2>
              <div className="mt-1 text-[12px] muted">
                {t("{topics} 个 Topic · {questions} 道练习题", {
                  topics: g.topic_count,
                  questions: g.question_count,
                })}
              </div>
              <div className="mt-5 flex items-center justify-between text-[12px] muted">
                <span>
                  {t("已答 {answered}/{total}", {
                    answered: g.answered,
                    total: g.total,
                  })}
                </span>
                <span>{g.accuracy === null ? "—" : `${Math.round(g.accuracy * 100)}%`}</span>
              </div>
              <div className="progress mt-2">
                <i style={{ width: `${progress}%` }} />
              </div>
              <div className="mt-4 flex items-center justify-between">
                <span className={g.locked ? "text-[12px] text-[var(--muted)]" : "text-[12px] text-[var(--primary)] font-medium"}>
                  {g.locked ? t("查看章节") : t("进入 Unit")}
                </span>
                {g.locked ? (
                  <LockKeyhole size={15} className="text-[var(--danger)]" />
                ) : (
                  <ArrowRight size={15} className="text-[var(--primary)]" />
                )}
              </div>
            </>
          );
          return (
            <Link key={g.group_id} href={`/practice/${g.group_id}`} className="card unit-card">
              {inner}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
