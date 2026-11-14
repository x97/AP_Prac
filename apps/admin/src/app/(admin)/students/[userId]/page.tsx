"use client";

import { ArrowLeft, Loader2 } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { apiGet } from "@/lib/api";
import type { StudentDetail } from "@/lib/types";

function date(value: string | null | undefined) {
  if (!value) return "—";
  return new Date(value).toLocaleString("zh-CN", { hour12: false });
}

function percent(value: number | null | undefined) {
  return value === null || value === undefined
    ? "—"
    : `${Math.round(value * 100)}%`;
}

export default function StudentDetailPage() {
  const params = useParams<{ userId: string }>();
  const [data, setData] = useState<StudentDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    apiGet<StudentDetail>(`/students/${params.userId}`)
      .then((value) => alive && setData(value))
      .catch((e: Error) => alive && setError(e.message));
    return () => {
      alive = false;
    };
  }, [params.userId]);

  if (error) {
    return (
      <div>
        <Link href="/students" className="a-btn a-btn-sm mb-4">
          <ArrowLeft size={14} /> 返回学生列表
        </Link>
        <div className="a-card p-5 text-[13px] text-[var(--danger)]">{error}</div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="grid place-items-center py-24">
        <Loader2 size={24} className="animate-spin text-[var(--primary)]" />
      </div>
    );
  }

  const { student, dashboard, sessions, attempts, wrong_summary } = data;
  const overview = dashboard.overview;

  return (
    <div>
      <Link href="/students" className="a-btn a-btn-sm mb-4">
        <ArrowLeft size={14} /> 返回学生列表
      </Link>

      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="text-[11px] uppercase tracking-[0.14em] text-[var(--faint)]">
            Student
          </div>
          <h1 className="mt-1 text-[27px] font-semibold tracking-[-0.03em]">
            {student.nickname || student.email_masked || student.phone_masked}
          </h1>
          <p className="mt-1 font-mono text-[12px] text-[var(--muted)]">
            {student.email_masked || student.phone_masked || "—"} · 注册于{" "}
            {date(student.created_at)}
          </p>
        </div>
        <span className="a-badge">{student.status}</span>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {[
          ["已答题目", overview.answered.toLocaleString()],
          ["正确率", percent(overview.accuracy)],
          ["连续学习", `${overview.streak_days} 天`],
          ["已掌握错题", wrong_summary.mastered.toLocaleString()],
        ].map(([label, value]) => (
          <div key={label} className="a-card p-4">
            <div className="text-[11.5px] text-[var(--muted)]">{label}</div>
            <div className="mt-2 text-[24px] font-semibold tracking-[-0.03em]">
              {value}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
        <section className="a-card p-5">
          <h2 className="text-[15px] font-semibold">Unit 进度</h2>
          <div className="mt-4 space-y-4">
            {dashboard.units.map((unit) => {
              const completion = unit.total ? unit.answered / unit.total : 0;
              return (
                <div key={unit.group_id}>
                  <div className="flex items-center justify-between gap-3 text-[12px]">
                    <span className="font-medium">
                      Unit {unit.unit_id} · {unit.title_en || unit.title}
                    </span>
                    <span className="text-[var(--muted)]">
                      {unit.answered}/{unit.total} · {percent(unit.accuracy)}
                    </span>
                  </div>
                  <div className="mt-2 h-2 overflow-hidden rounded-full bg-[var(--surface-2)]">
                    <div
                      className="h-full rounded-full bg-[var(--primary)]"
                      style={{ width: `${Math.min(100, completion * 100)}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        <section className="a-card p-5">
          <h2 className="text-[15px] font-semibold">错题状态</h2>
          <div className="mt-4 space-y-3">
            {[
              ["未掌握", wrong_summary.learning, "a-badge-danger"],
              ["复习中", wrong_summary.reviewing, "a-badge-warn"],
              ["已掌握", wrong_summary.mastered, "a-badge-success"],
            ].map(([label, value, className]) => (
              <div key={String(label)} className="flex items-center justify-between">
                <span className="text-[12.5px] text-[var(--muted)]">{label}</span>
                <span className={`a-badge ${className}`}>{String(value)}</span>
              </div>
            ))}
          </div>
        </section>
      </div>

      <section className="a-card mt-4 overflow-hidden">
        <div className="border-b border-[var(--line)] px-5 py-4">
          <h2 className="text-[15px] font-semibold">最近考试</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="a-table min-w-[760px]">
            <thead>
              <tr>
                <th>试卷</th>
                <th>模式</th>
                <th>状态</th>
                <th>MCQ</th>
                <th>FRQ</th>
                <th>时间</th>
              </tr>
            </thead>
            <tbody>
              {attempts.map((attempt) => (
                <tr key={attempt.id}>
                  <td className="font-medium">{attempt.paper_title}</td>
                  <td>{attempt.mode}</td>
                  <td><span className="a-badge">{attempt.status}</span></td>
                  <td className="font-mono">
                    {attempt.mcq_score ?? "—"}/{attempt.mcq_total ?? "—"}
                  </td>
                  <td className="font-mono">
                    {attempt.frq_score ?? "—"}/{attempt.frq_total ?? "—"}
                  </td>
                  <td className="text-[11.5px] text-[var(--muted)]">
                    {date(attempt.created_at)}
                  </td>
                </tr>
              ))}
              {attempts.length === 0 && (
                <tr>
                  <td colSpan={6} className="py-10 text-center text-[12px] text-[var(--faint)]">
                    暂无考试记录
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="a-card mt-4 overflow-hidden">
        <div className="border-b border-[var(--line)] px-5 py-4">
          <h2 className="text-[15px] font-semibold">最近练习</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="a-table min-w-[760px]">
            <thead>
              <tr>
                <th>章节</th>
                <th>来源</th>
                <th>状态</th>
                <th>已答</th>
                <th>正确</th>
                <th>时间</th>
              </tr>
            </thead>
            <tbody>
              {sessions.map((session) => (
                <tr key={session.id}>
                  <td className="font-medium">
                    {session.topic_title || session.group_title || "练习"}
                  </td>
                  <td>{session.source}</td>
                  <td><span className="a-badge">{session.status}</span></td>
                  <td className="font-mono">
                    {session.answered}/{session.total_questions}
                  </td>
                  <td className="font-mono">{session.correct}</td>
                  <td className="text-[11.5px] text-[var(--muted)]">
                    {date(session.created_at)}
                  </td>
                </tr>
              ))}
              {sessions.length === 0 && (
                <tr>
                  <td colSpan={6} className="py-10 text-center text-[12px] text-[var(--faint)]">
                    暂无练习记录
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
