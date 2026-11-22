"use client";

import { ArrowLeft, Loader2, Save } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { apiGet, apiPatch } from "@/lib/api";
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

function gradeText(grade: string | null | undefined) {
  if (!grade) return "—";
  return grade === "other" ? "其他" : `${grade} 年级`;
}

export default function StudentDetailPage() {
  const params = useParams<{ userId: string }>();
  const [data, setData] = useState<StudentDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [teacherNote, setTeacherNote] = useState("");
  const [savingNote, setSavingNote] = useState(false);
  const [noteError, setNoteError] = useState<string | null>(null);
  const [noteSaved, setNoteSaved] = useState(false);

  useEffect(() => {
    let alive = true;
    apiGet<StudentDetail>(`/students/${params.userId}`)
      .then((value) => {
        if (!alive) return;
        setData(value);
        setTeacherNote(value.student.teacher_note || "");
      })
      .catch((e: Error) => alive && setError(e.message));
    return () => {
      alive = false;
    };
  }, [params.userId]);

  async function saveNote() {
    setSavingNote(true);
    setNoteError(null);
    setNoteSaved(false);
    try {
      await apiPatch(`/students/${params.userId}`, {
        teacher_note: teacherNote,
      });
      setNoteSaved(true);
    } catch (e) {
      setNoteError(e instanceof Error ? e.message : "保存失败");
    } finally {
      setSavingNote(false);
    }
  }

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

      <div className="mb-4 grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
        <section className="a-card p-5">
          <h2 className="text-[15px] font-semibold">学生档案</h2>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {[
              ["年级", gradeText(student.grade)],
              ["地区", student.region || "—"],
              ["目标分数", student.target_score ? `${student.target_score} 分` : "—"],
              [
                "是否学过心理课",
                student.studied_psychology === null ||
                student.studied_psychology === undefined
                  ? "未填写"
                  : student.studied_psychology
                    ? "学过"
                    : "没有学过",
              ],
            ].map(([label, value]) => (
              <div
                key={label}
                className="rounded-xl border border-[var(--line)] bg-[var(--surface-2)] px-3 py-2.5"
              >
                <div className="text-[10.5px] uppercase tracking-[0.1em] text-[var(--faint)]">
                  {label}
                </div>
                <div className="mt-1 text-[13.5px] font-medium">{value}</div>
              </div>
            ))}
          </div>
          <p className="mt-3 text-[10.5px] text-[var(--faint)]">
            {student.profile_completed_at
              ? `资料完善于 ${date(student.profile_completed_at)}`
              : "学生尚未完善个人资料"}
          </p>
        </section>

        <section className="a-card p-5">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-[15px] font-semibold">老师备注</h2>
            {noteSaved && (
              <span className="text-[11px] text-[var(--success)]">已保存</span>
            )}
          </div>
          <textarea
            className="a-input mt-3 min-h-[132px] resize-y"
            value={teacherNote}
            onChange={(event) => {
              setTeacherNote(event.target.value);
              setNoteSaved(false);
            }}
            maxLength={5000}
            placeholder="记录学生的学习情况、沟通要点或需要跟进的事项…"
          />
          <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
            <span className="text-[10.5px] text-[var(--faint)]">
              {teacherNote.length}/5000 · 仅后台可见
            </span>
            <button
              type="button"
              className="a-btn a-btn-primary a-btn-sm"
              onClick={saveNote}
              disabled={savingNote}
            >
              {savingNote ? (
                <Loader2 size={13} className="animate-spin" />
              ) : (
                <Save size={13} />
              )}
              保存备注
            </button>
          </div>
          {noteError && (
            <div className="mt-2 text-[11px] text-[var(--danger)]">{noteError}</div>
          )}
        </section>
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
