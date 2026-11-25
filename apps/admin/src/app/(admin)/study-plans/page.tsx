"use client";

import {
  CalendarRange,
  ChevronLeft,
  ChevronRight,
  Loader2,
  Plus,
  Search,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { useAdmin, useAdminSubject } from "@/components/AdminShell";
import { AdminModal } from "@/components/AdminModal";
import { apiGet, apiPatch, apiPost } from "@/lib/api";
import type { StudyPlanList } from "@/lib/types";

const LIMIT = 50;
const COLORS = [
  ["primary", "经典蓝"],
  ["accent", "琥珀"],
  ["success", "森林绿"],
  ["violet", "紫罗兰"],
  ["cyan", "青碧"],
  ["rose", "樱花粉"],
  ["slate", "石墨灰"],
];

const COLOR_HEX: Record<string, string> = {
  primary: "#2f5be8",
  accent: "#b45309",
  success: "#177245",
  violet: "#7c3aed",
  cyan: "#0891b2",
  rose: "#e11d48",
  slate: "#475569",
};

export default function StudyPlansPage() {
  const admin = useAdmin();
  const { subjectId } = useAdminSubject();
  const canEdit = Boolean(admin?.can_edit_content);
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<StudyPlanList | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [note, setNote] = useState("");
  const [category, setCategory] = useState("");
  const [color, setColor] = useState("primary");
  const [creating, setCreating] = useState(false);

  function reload() {
    setLoading(true);
    const params = new URLSearchParams({
      subject: subjectId,
      status: "active",
      limit: String(LIMIT),
      offset: String(offset),
    });
    if (search) params.set("q", search);
    apiGet<StudyPlanList>(`/study-plans?${params.toString()}`)
      .then((value) => {
        setData(value);
        setError(null);
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }

  useEffect(reload, [subjectId, search, offset]);

  async function createPlan() {
    if (!title.trim()) return;
    setCreating(true);
    setError(null);
    try {
      const plan = await apiPost<{ id: string }>(
        `/study-plans?subject=${subjectId}`,
        {
          title: title.trim(),
          note,
          category: category || null,
          color,
        },
      );
      window.location.href = `/study-plans/${plan.id}`;
    } catch (e) {
      setError(e instanceof Error ? e.message : "创建失败");
    } finally {
      setCreating(false);
    }
  }

  async function archive(planId: string, planTitle: string) {
    if (!window.confirm(`归档学习计划「${planTitle}」？已指派的学生不受影响。`)) return;
    try {
      await apiPatch(`/study-plans/${planId}?subject=${subjectId}`, {
        status: "archived",
      });
      reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "归档失败");
    }
  }

  return (
    <div>
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="text-[11px] uppercase tracking-[0.14em] text-[var(--faint)]">
            Study plans
          </div>
          <h1 className="mt-1 text-[27px] font-semibold tracking-[-0.03em]">学习计划</h1>
          <p className="mt-1 max-w-[760px] text-[14px] leading-6 text-[var(--muted)]">
            把课堂作业组织成学习项，指派给学生后自动排到开始/结束日期内的每一天。
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="a-badge">
            <CalendarRange size={13} /> {data?.total ?? 0} 个
          </span>
          {canEdit && (
            <button
              className="a-btn a-btn-primary"
              onClick={() => setCreateOpen(true)}
            >
              <Plus size={14} /> 新建学习计划
            </button>
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
            placeholder="搜索计划标题或备注"
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
        ) : data && data.plans.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="a-table min-w-[780px]">
              <thead>
                <tr>
                  <th>学习计划</th>
                  <th>分类</th>
                  <th>学习项</th>
                  <th>进行中学生</th>
                  <th>更新时间</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {data.plans.map((plan) => (
                  <tr key={plan.id}>
                    <td>
                      <div className="flex items-start gap-2">
                        <i
                          className="mt-1.5 inline-block h-2.5 w-2.5 shrink-0 rounded-full"
                          style={{
                            background: COLOR_HEX[plan.color] || COLOR_HEX.primary,
                          }}
                          aria-hidden="true"
                        />
                        <div className="min-w-0">
                          <Link
                            href={`/study-plans/${plan.id}`}
                            className="font-medium hover:text-[var(--primary)]"
                          >
                            {plan.title}
                          </Link>
                          <div className="mt-0.5 max-w-[360px] truncate text-[11px] text-[var(--muted)]">
                            {plan.note || "—"}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td>
                      <span className="a-badge">{plan.category || "未分类"}</span>
                    </td>
                    <td className="font-mono">{plan.item_count}</td>
                    <td>
                      <span className="a-badge a-badge-primary">
                        {plan.active_assignment_count || 0} 人
                      </span>
                    </td>
                    <td className="text-[11.5px] text-[var(--muted)]">
                      {new Date(plan.updated_at).toLocaleDateString("zh-CN")}
                    </td>
                    <td>
                      <div className="flex justify-end gap-1">
                        <Link
                          href={`/study-plans/${plan.id}`}
                          className="a-btn a-btn-sm"
                        >
                          编辑 / 指派
                        </Link>
                        {canEdit && (
                          <button
                            className="a-btn a-btn-sm"
                            onClick={() => archive(plan.id, plan.title)}
                          >
                            归档
                          </button>
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
            <CalendarRange size={24} className="mx-auto text-[var(--faint)]" />
            <div className="mt-3 text-[13px] font-medium">还没有学习计划</div>
            <p className="mt-1 text-[12px] text-[var(--muted)]">
              新建计划 → 添加课堂作业作为学习项 → 指派给学生。
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

      <AdminModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        title="新建学习计划"
      >
        <div className="space-y-3">
          <label className="block">
            <span className="mb-1 block text-[11.5px] text-[var(--muted)]">标题</span>
            <input
              className="a-input"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="例如：Unit 1–2 基础陪跑"
              autoFocus
            />
          </label>
          <label className="block">
            <span className="mb-1 block text-[11.5px] text-[var(--muted)]">备注</span>
            <textarea
              className="a-input min-h-[80px]"
              value={note}
              onChange={(event) => setNote(event.target.value)}
            />
          </label>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block">
              <span className="mb-1 block text-[11.5px] text-[var(--muted)]">
                分类
              </span>
              <select
                className="a-input"
                value={category}
                onChange={(event) => setCategory(event.target.value)}
              >
                <option value="">未分类</option>
                <option value="基础">基础</option>
                <option value="强化">强化</option>
                <option value="冲刺">冲刺</option>
                <option value="陪跑">陪跑</option>
              </select>
            </label>
            <label className="block">
              <span className="mb-1 block text-[11.5px] text-[var(--muted)]">
                月历颜色
              </span>
              <select
                className="a-input"
                value={color}
                onChange={(event) => setColor(event.target.value)}
              >
                {COLORS.map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
              <p className="mt-1 text-[11px] leading-5 text-[var(--faint)]">
                用于在学生端「学习日历」中区分不同计划：日历里的任务标签和右侧任务卡片背景会使用这个颜色，不影响任务状态。
              </p>
            </label>
          </div>
          <div className="flex justify-end gap-2 border-t border-[var(--line)] pt-3">
            <button className="a-btn" onClick={() => setCreateOpen(false)}>
              取消
            </button>
            <button
              className="a-btn a-btn-primary"
              onClick={createPlan}
              disabled={creating || !title.trim()}
            >
              {creating ? <Loader2 size={14} className="animate-spin" /> : null}
              创建并添加学习项
            </button>
          </div>
        </div>
      </AdminModal>
    </div>
  );
}
