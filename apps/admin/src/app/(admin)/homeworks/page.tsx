"use client";

import {
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  Copy,
  Loader2,
  Plus,
  Search,
  Trash2,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { useAdmin, useAdminSubject } from "@/components/AdminShell";
import { apiDelete, apiGet, apiPost } from "@/lib/api";
import type { ClassroomHomeworkList } from "@/lib/types";

const LIMIT = 50;

export default function HomeworksPage() {
  const admin = useAdmin();
  const { subjectId, subject } = useAdminSubject();
  const canEdit = Boolean(admin?.can_edit_content);
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<ClassroomHomeworkList | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  function reload() {
    setLoading(true);
    const params = new URLSearchParams({
      subject: subjectId,
      status: "active",
      limit: String(LIMIT),
      offset: String(offset),
    });
    if (search) params.set("q", search);
    apiGet<ClassroomHomeworkList>(`/homeworks?${params.toString()}`)
      .then((value) => {
        setData(value);
        setError(null);
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }

  useEffect(reload, [subjectId, search, offset]);

  async function duplicate(homeworkId: string) {
    try {
      await apiPost(`/homeworks/${homeworkId}/duplicate?subject=${subjectId}`);
      reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "复制失败");
    }
  }

  async function remove(homeworkId: string, title: string) {
    if (!window.confirm(`删除课堂作业「${title}」？已被计划引用时不能删除。`)) return;
    try {
      await apiDelete(`/homeworks/${homeworkId}?subject=${subjectId}`);
      reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "删除失败");
    }
  }

  return (
    <div>
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="text-[11px] uppercase tracking-[0.14em] text-[var(--faint)]">
            Classroom
          </div>
          <h1 className="mt-1 text-[27px] font-semibold tracking-[-0.03em]">课堂作业</h1>
          <p className="mt-1 max-w-[760px] text-[14px] leading-6 text-[var(--muted)]">
            可复用的题目集合：标题、备注、Unit/Chapter 和 MCQ 题目。学习计划通过引用课堂作业来组织学习项。
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="a-badge">
            <ClipboardList size={13} /> {data?.total ?? 0} 份
          </span>
          {canEdit && (
            <Link href="/homeworks/new" className="a-btn a-btn-primary">
              <Plus size={14} /> 新建课堂作业
            </Link>
          )}
        </div>
      </div>

      <form
        className="mb-4 flex max-w-xl gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          setOffset(0);
          setSearch(query.trim());
        }}
      >
        <div className="relative flex-1">
          <Search
            size={15}
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--faint)]"
          />
          <input
            className="a-input pl-9"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="搜索标题或备注"
          />
        </div>
        <button className="a-btn" type="submit">
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
        ) : data && data.homeworks.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="a-table min-w-[880px]">
              <thead>
                <tr>
                  <th>课堂作业</th>
                  <th>Unit / 章节</th>
                  <th>题目数</th>
                  <th>被计划引用</th>
                  <th>更新时间</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {data.homeworks.map((homework) => (
                  <tr key={homework.id}>
                    <td>
                      <Link
                        href={`/homeworks/${homework.id}`}
                        className="font-medium hover:text-[var(--primary)]"
                      >
                        {homework.title}
                      </Link>
                      <div className="mt-0.5 max-w-[360px] truncate text-[11px] text-[var(--muted)]">
                        {homework.note || "—"}
                      </div>
                    </td>
                    <td className="text-[12px] text-[var(--muted)]">
                      <div>
                        Unit {homework.unit_id || "—"}
                        {homework.topic_code ? ` · ${homework.topic_code}` : ""}
                      </div>
                      <div className="text-[10.5px] text-[var(--faint)]">
                        {homework.topic_title || "—"}
                      </div>
                    </td>
                    <td className="font-mono">{homework.question_count}</td>
                    <td className="text-[12px]">
                      {homework.used_in_plans ? (
                        <span className="a-badge a-badge-primary">
                          {homework.used_in_plans} 个计划
                        </span>
                      ) : (
                        <span className="text-[var(--faint)]">未使用</span>
                      )}
                    </td>
                    <td className="text-[11.5px] text-[var(--muted)]">
                      {new Date(homework.updated_at).toLocaleDateString("zh-CN")}
                    </td>
                    <td>
                      <div className="flex justify-end gap-1">
                        <Link href={`/homeworks/${homework.id}`} className="a-btn a-btn-sm">
                          编辑
                        </Link>
                        {canEdit && (
                          <>
                            <button
                              className="a-btn a-btn-sm"
                              onClick={() => duplicate(homework.id)}
                              title="复制"
                            >
                              <Copy size={13} />
                            </button>
                            <button
                              className="a-btn a-btn-sm"
                              onClick={() => remove(homework.id, homework.title)}
                              title="删除"
                            >
                              <Trash2 size={13} />
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="py-20 text-center">
            <ClipboardList size={24} className="mx-auto text-[var(--faint)]" />
            <div className="mt-3 text-[13px] font-medium">还没有课堂作业</div>
            <p className="mt-1 text-[12px] text-[var(--muted)]">
              先创建一个课堂作业，再从题库按 Unit/Chapter 批量加入 MCQ。
            </p>
          </div>
        )}
        <div className="flex items-center justify-between border-t border-[var(--line)] px-5 py-3 text-[11.5px] text-[var(--muted)]">
          <span>
            {(data?.total ?? 0) === 0
              ? "0"
              : `${offset + 1}–${Math.min(offset + LIMIT, data?.total ?? 0)}`}{" "}
            / {data?.total ?? 0}
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
              disabled={offset + LIMIT >= (data?.total ?? 0)}
              onClick={() => setOffset(offset + LIMIT)}
            >
              下一页 <ChevronRight size={14} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
