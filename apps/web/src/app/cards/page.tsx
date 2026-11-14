"use client";

import {
  ArrowLeft,
  BookOpen,
  ChevronDown,
  Sparkles,
  Star,
  User,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { FlashcardStudy } from "@/components/FlashcardStudy";
import { MyFlashcards } from "@/components/MyFlashcards";

const UNITS = [
  { value: "", label: "全部单元" },
  { value: "1", label: "Unit 1" },
  { value: "2", label: "Unit 2" },
  { value: "3", label: "Unit 3" },
  { value: "4", label: "Unit 4" },
  { value: "5", label: "Unit 5" },
  { value: "methods", label: "研究方法" },
];

const STAR_OPTIONS = [
  { value: 0, label: "全部" },
  { value: 4, label: "4★+" },
  { value: 5, label: "5★" },
];

export default function CardsPage() {
  const [tab, setTab] = useState<"official" | "my">("official");
  const [unit, setUnit] = useState("");
  const [minStars, setMinStars] = useState(0);

  return (
    <div>
      <div className="flex items-center justify-between gap-3 mb-4">
        <Link href="/dashboard" className="btn btn-ghost btn-sm -ml-2">
          <ArrowLeft size={14} /> 首页
        </Link>
        <Link href="/history" className="btn btn-sm btn-ghost">
          做题记录
        </Link>
      </div>

      <div className="page-head">
        <div>
          <div className="eyebrow">记忆卡片</div>
          <h1 className="h1">记忆卡片</h1>
          <p className="muted text-[13px] mt-2">
            {tab === "official"
              ? "先看术语，翻面查看释义。按到期顺序连续出现，学完可以随时停下。"
              : "自己创建卡片：术语、简短含义和详细解释。只有你自己能看到。"}
          </p>
        </div>
        {tab === "official" && (
          <span className="pill">
            <Star size={13} /> 按权重排序
          </span>
        )}
      </div>

      <div className="max-w-5xl mx-auto">
        <div className="cards-controls mb-4">
          <div className="source-tabs" role="group" aria-label="卡片来源">
            <button
              type="button"
              className="source-tab"
              aria-pressed={tab === "official"}
              onClick={() => setTab("official")}
            >
              <BookOpen size={14} className="source-tab-icon" />
              官方卡片
            </button>
            <button
              type="button"
              className="source-tab"
              aria-pressed={tab === "my"}
              onClick={() => setTab("my")}
            >
              <User size={14} className="source-tab-icon" />
              我的卡片
            </button>
          </div>

          {tab === "official" && (
            <>
              <span className="filter-select-wrap">
                <select
                  className="filter-select"
                  aria-label="按单元筛选"
                  value={unit}
                  onChange={(event) => setUnit(event.target.value)}
                >
                  {UNITS.map((item) => (
                    <option key={item.value} value={item.value}>
                      {item.label}
                    </option>
                  ))}
                </select>
                <ChevronDown
                  size={13}
                  className="filter-select-icon"
                  aria-hidden="true"
                />
              </span>

              <div className="filter-inline-group">
                <span className="filter-field-label">重要程度</span>
                <div className="segmented" role="group" aria-label="按重要程度筛选">
                  {STAR_OPTIONS.map((item) => (
                    <button
                      type="button"
                      key={item.value}
                      className="segment"
                      aria-pressed={minStars === item.value}
                      onClick={() => setMinStars(item.value)}
                    >
                      {item.label}
                    </button>
                  ))}
                </div>
              </div>

            </>
          )}
        </div>

        {tab === "official" ? (
          <>
            <FlashcardStudy
              unit={unit}
              minStars={minStars}
              continuous
              showAllLink={false}
            />

            <div className="mt-4 text-[11px] faint leading-5">
              <p className="flex items-start gap-1.5">
                <Sparkles size={12} className="mt-0.5 shrink-0" />
                星星表示概念权重：5★ 最重要。高权重卡片优先出现，也可以在上方筛选
                4★+。卡片按到期顺序连续出现，不再按组抽取。每天最多引入 60 张新卡；
                新卡第一次选择「Already Know」后 30 分钟内会再次出现，第二次后进入
                1 / 2 / 4 / 7 / 15 天间隔；「Review Later」10 分钟后再次出现。逾期卡片显示
                「逾期 N 天」，最长间隔为 15 天。
              </p>
            </div>
          </>
        ) : (
          <MyFlashcards />
        )}
      </div>
    </div>
  );
}
