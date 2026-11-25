"use client";

import { CalendarDays, CheckCircle2, MessageCircle, Sparkles } from "lucide-react";
import Link from "next/link";

import { useLanguage } from "@/lib/i18n";

export function StudyCalendarEmptyState({ onContact }: { onContact: () => void }) {
  const { t } = useLanguage();
  return (
    <div className="study-empty-hero">
      <div className="study-empty-illustration" aria-hidden="true">
        <CalendarDays size={38} />
      </div>
      <div className="eyebrow">Study calendar</div>
      <h1 className="h1 mt-2">{t("还没有老师为你定制的学习计划")}</h1>
      <p className="mt-2 max-w-[560px] text-[13.5px] leading-6 muted">
        {t("学习计划会把阶段目标拆成每天该做的题：打开日历就知道今天做什么，落下的任务会醒目标记。")}
      </p>
      <div className="study-empty-points">
        <span>
          <Sparkles size={15} /> {t("按阶段和基础定制")}
        </span>
        <span>
          <CalendarDays size={15} /> {t("每天任务清清楚楚")}
        </span>
        <span>
          <CheckCircle2 size={15} /> {t("完成一项解锁下一项")}
        </span>
      </div>
      <div className="mt-5 flex flex-wrap justify-center gap-2">
        <button className="btn btn-primary" onClick={onContact}>
          <MessageCircle size={15} /> {t("加老师微信，定制陪跑计划")}
        </button>
        <Link href="/practice" className="btn">
          {t("先自己练习 Unit 1")}
        </Link>
      </div>
    </div>
  );
}
