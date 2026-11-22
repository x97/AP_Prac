"use client";

import { ChevronLeft, ChevronRight, Loader2, Search, Users } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { apiGet } from "@/lib/api";
import type { StudentList } from "@/lib/types";

const LIMIT = 50;

function date(value: string | null) {
  if (!value) return "—";
  return new Date(value).toLocaleDateString("zh-CN");
}

function percent(value: number | null) {
  return value === null ? "—" : `${Math.round(value * 100)}%`;
}

function gradeText(grade: string | null) {
  if (!grade) return "—";
  return grade === "other" ? "其他" : `${grade} 年级`;
}

function studyModeText(value: string | null) {
  const labels: Record<string, string> = {
    school: "学校教授",
    tutoring: "机构辅导",
    self: "自学",
    not_yet: "还未学习",
  };
  return value ? labels[value] || value : "—";
}

function examTimeText(value: string | null) {
  if (!value) return "—";
  return value === "undecided" ? "观望中" : value;
}

export default function StudentsPage() {
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<StudentList | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    const params = new URLSearchParams({ limit: String(LIMIT), offset: String(offset) });
    if (search) params.set("q", search);
    apiGet<StudentList>(`/students?${params.toString()}`)
      .then((value) => {
        if (alive) {
          setData(value);
          setError(null);
        }
      })
      .catch((e: Error) => alive && setError(e.message))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [search, offset]);

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setOffset(0);
    setSearch(query.trim());
  }

  const total = data?.total ?? 0;

  return (
    <div>
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="text-[11px] uppercase tracking-[0.14em] text-[var(--faint)]">
            Students
          </div>
          <h1 className="mt-1 text-[27px] font-semibold tracking-[-0.03em]">学生</h1>
          <p className="mt-1 text-[12.5px] text-[var(--muted)]">
            查看学生学习进度、练习和考试记录。学生数据只读。
          </p>
        </div>
        <span className="a-badge">
          <Users size={13} /> 共 {total} 人
        </span>
      </div>

      <form className="mb-4 flex max-w-xl gap-2" onSubmit={submit}>
        <div className="relative flex-1">
          <Search
            size={15}
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--faint)]"
          />
          <input
            className="a-input pl-9"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="搜索邮箱、手机号或昵称"
          />
        </div>
        <button className="a-btn a-btn-primary" type="submit">
          搜索
        </button>
      </form>

      {error && (
        <div className="mb-3 rounded-xl border border-[#f6d5d2] bg-[var(--danger-soft)] px-3 py-2 text-[12px] text-[var(--danger)]">
          {error}
        </div>
      )}

      <div className="a-card overflow-hidden">
        {loading ? (
          <div className="grid place-items-center py-20">
            <Loader2 size={22} className="animate-spin text-[var(--primary)]" />
          </div>
        ) : data && data.students.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="a-table min-w-[1060px]">
              <thead>
                <tr>
                  <th>学生</th>
                  <th>年级 / 地区</th>
                  <th>目标分</th>
                  <th>学习方式</th>
                  <th>考试时间</th>
                  <th>已答</th>
                  <th>正确率</th>
                  <th>练习</th>
                  <th>考试次数</th>
                  <th>注册时间</th>
                  <th>最近活跃</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {data.students.map((student) => (
                  <tr key={student.id}>
                    <td>
                      <Link
                        href={`/students/${student.id}`}
                        className="font-medium hover:text-[var(--primary)]"
                      >
                        {student.nickname || student.email_masked || student.phone_masked}
                      </Link>
                      <div className="mt-0.5 font-mono text-[10.5px] text-[var(--faint)]">
                        {student.email_masked || student.phone_masked || "—"}
                      </div>
                    </td>
                    <td className="text-[12px] text-[var(--muted)]">
                      <div>{gradeText(student.grade)}</div>
                      <div className="text-[10.5px] text-[var(--faint)]">
                        {student.region || "—"}
                      </div>
                    </td>
                    <td className="font-mono">{student.target_score ?? "—"}</td>
                    <td>
                      <span className="a-badge">{studyModeText(student.study_mode)}</span>
                    </td>
                    <td className="font-mono">{examTimeText(student.exam_time)}</td>
                    <td className="font-mono">{student.answered.toLocaleString()}</td>
                    <td>{percent(student.accuracy)}</td>
                    <td className="font-mono">{student.practice_count}</td>
                    <td className="font-mono">{student.attempt_count}</td>
                    <td className="text-[12px] text-[var(--muted)]">
                      {date(student.created_at)}
                    </td>
                    <td className="text-[12px] text-[var(--muted)]">
                      {date(student.last_active_at)}
                    </td>
                    <td className="text-right">
                      <Link
                        href={`/students/${student.id}`}
                        className="a-btn a-btn-sm"
                      >
                        详情
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="py-20 text-center">
            <Users size={24} className="mx-auto text-[var(--faint)]" />
            <div className="mt-3 text-[13px] font-medium">没有找到学生</div>
            <p className="mt-1 text-[12px] text-[var(--muted)]">
              尝试清空搜索条件，或等待学生注册。
            </p>
          </div>
        )}
      </div>

      <div className="mt-3 flex items-center justify-between text-[12px] text-[var(--muted)]">
        <span>
          {total === 0 ? "0" : `${offset + 1}–${Math.min(offset + LIMIT, total)}`} / {total}
        </span>
        <div className="flex gap-2">
          <button
            className="a-btn a-btn-sm"
            disabled={offset === 0}
            onClick={() => setOffset(Math.max(0, offset - LIMIT))}
          >
            <ChevronLeft size={14} /> 上一页
          </button>
          <button
            className="a-btn a-btn-sm"
            disabled={offset + LIMIT >= total}
            onClick={() => setOffset(offset + LIMIT)}
          >
            下一页 <ChevronRight size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}
