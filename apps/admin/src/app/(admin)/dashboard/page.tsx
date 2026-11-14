"use client";

import {
  Activity,
  AlertTriangle,
  BookOpenCheck,
  FileText,
  Loader2,
  Users,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { apiGet } from "@/lib/api";
import type { Dashboard } from "@/lib/types";

function date(value: string | null | undefined) {
  if (!value) return "—";
  return new Date(value).toLocaleString("zh-CN", { hour12: false });
}

export default function DashboardPage() {
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    apiGet<Dashboard>("/dashboard")
      .then((value) => alive && setData(value))
      .catch((e: Error) => alive && setError(e.message));
    return () => {
      alive = false;
    };
  }, []);

  if (error) {
    return <div className="a-card p-5 text-[13px] text-[var(--danger)]">{error}</div>;
  }

  if (!data) {
    return (
      <div className="grid place-items-center py-24">
        <Loader2 size={24} className="animate-spin text-[var(--primary)]" />
      </div>
    );
  }

  const { stats, release } = data;
  const cards = [
    { label: "学生总数", value: stats.students, icon: Users, href: "/students" },
    { label: "近 7 天活跃", value: stats.active_students_7d, icon: Activity, href: "/students" },
    { label: "练习记录", value: stats.practice_sessions, icon: BookOpenCheck },
    { label: "考试记录", value: stats.attempts, icon: FileText },
    { label: "待复习错题", value: stats.wrong_active, icon: AlertTriangle },
    { label: "待处理报错", value: stats.open_reports, icon: AlertTriangle },
  ];

  return (
    <div>
      <div className="mb-6">
        <div className="text-[11px] uppercase tracking-[0.14em] text-[var(--faint)]">
          Overview
        </div>
        <h1 className="mt-1 text-[27px] font-semibold tracking-[-0.03em]">仪表盘</h1>
        <p className="mt-1 text-[12.5px] text-[var(--muted)]">
          学生进度、内容版本和近期活动概览。
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {cards.map((item) => {
          const Icon = item.icon;
          const content = (
            <div className="a-card h-full p-4 transition hover:border-[#cbd5e1]">
              <div className="flex items-start justify-between">
                <span className="text-[12px] text-[var(--muted)]">{item.label}</span>
                <Icon size={17} className="text-[var(--faint)]" />
              </div>
              <div className="mt-3 text-[28px] font-semibold tracking-[-0.04em]">
                {item.value.toLocaleString()}
              </div>
            </div>
          );
          return item.href ? (
            <Link key={item.label} href={item.href}>
              {content}
            </Link>
          ) : (
            <div key={item.label}>{content}</div>
          );
        })}
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-[1.3fr_1fr]">
        <section className="a-card p-5">
          <div className="flex items-center justify-between">
            <h2 className="text-[15px] font-semibold">最近考试</h2>
            <Link href="/students" className="text-[11.5px] text-[var(--primary)]">
              查看学生
            </Link>
          </div>
          {data.recent_attempts.length === 0 ? (
            <div className="py-8 text-center text-[12px] text-[var(--faint)]">
              暂无考试记录
            </div>
          ) : (
            <div className="mt-3 divide-y divide-[var(--line)]">
              {data.recent_attempts.map((item) => (
                <div key={item.id} className="flex items-center justify-between gap-3 py-3">
                  <div className="min-w-0">
                    <div className="truncate text-[12.5px] font-medium">
                      {item.paper_title}
                    </div>
                    <div className="mt-1 text-[10.5px] text-[var(--faint)]">
                      {item.mode} · {item.status} · {date(item.created_at)}
                    </div>
                  </div>
                  <span className="a-badge shrink-0">
                    {item.mcq_score ?? "—"}/{item.mcq_total ?? "—"}
                  </span>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="a-card p-5">
          <h2 className="text-[15px] font-semibold">当前内容版本</h2>
          <div className="mt-4 rounded-xl border border-[var(--line)] bg-[var(--surface-2)] p-3">
            <div className="break-all font-mono text-[11.5px]">{release.release_id}</div>
            <div className="mt-1 text-[10.5px] text-[var(--faint)]">
              {release.created_at ? date(release.created_at) : "—"}
            </div>
          </div>
          <div className="mt-3 grid grid-cols-2 gap-2 text-[11.5px]">
            <span className="text-[var(--muted)]">题目</span>
            <span className="text-right font-mono">{release.counts.questions ?? "—"}</span>
            <span className="text-[var(--muted)]">知识点</span>
            <span className="text-right font-mono">{release.counts.kps ?? "—"}</span>
            <span className="text-[var(--muted)]">概念</span>
            <span className="text-right font-mono">{release.counts.concepts ?? "—"}</span>
          </div>
          <Link href="/releases" className="a-btn a-btn-sm mt-4 w-full">
            查看发布记录
          </Link>
        </section>
      </div>

      <section className="a-card mt-4 p-5">
        <div className="flex items-center justify-between">
          <h2 className="text-[15px] font-semibold">最近练习</h2>
          <Link href="/students" className="text-[11.5px] text-[var(--primary)]">
            学生进度
          </Link>
        </div>
        {data.recent_practice.length === 0 ? (
          <div className="py-8 text-center text-[12px] text-[var(--faint)]">
            暂无练习记录
          </div>
        ) : (
          <div className="mt-3 divide-y divide-[var(--line)]">
            {data.recent_practice.map((item) => (
              <div key={item.id} className="flex items-center justify-between gap-3 py-3">
                <div className="min-w-0">
                  <div className="truncate text-[12.5px] font-medium">
                    {item.topic_title || item.group_title || "练习"}
                  </div>
                  <div className="mt-1 text-[10.5px] text-[var(--faint)]">
                    {item.source} · {item.status} · {date(item.created_at)}
                  </div>
                </div>
                <span className="a-badge">{item.status}</span>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
