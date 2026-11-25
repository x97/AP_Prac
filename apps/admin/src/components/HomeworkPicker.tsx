"use client";

import { Loader2, Plus, RefreshCw, Search } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { AdminModal } from "@/components/AdminModal";
import { apiGet } from "@/lib/api";
import type { ClassroomHomework, ClassroomHomeworkList } from "@/lib/types";

export function HomeworkPicker({
  open,
  subjectId,
  excludeIds = [],
  onClose,
  onConfirm,
}: {
  open: boolean;
  subjectId: string;
  excludeIds?: string[];
  onClose: () => void;
  onConfirm: (homeworks: ClassroomHomework[]) => void;
}) {
  const [query, setQuery] = useState("");
  const [appliedQuery, setAppliedQuery] = useState("");
  const [rows, setRows] = useState<ClassroomHomework[]>([]);
  const [selected, setSelected] = useState<ClassroomHomework[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setQuery("");
    setAppliedQuery("");
    setSelected([]);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const timer = window.setTimeout(() => setAppliedQuery(query.trim()), 300);
    return () => window.clearTimeout(timer);
  }, [query, open]);

  useEffect(() => {
    if (!open) return;
    let alive = true;
    setLoading(true);
    setError(null);
    const params = new URLSearchParams({
      subject: subjectId,
      status: "active",
      limit: "100",
    });
    if (appliedQuery) params.set("q", appliedQuery);
    apiGet<ClassroomHomeworkList>(`/homeworks?${params.toString()}`)
      .then((value) => alive && setRows(value.homeworks))
      .catch((e: Error) => alive && setError(e.message))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [open, subjectId, appliedQuery]);

  const excluded = new Set(excludeIds);
  const selectedIds = new Set(selected.map((row) => row.id));

  function toggle(row: ClassroomHomework) {
    if (excluded.has(row.id)) return;
    setSelected((current) =>
      current.some((item) => item.id === row.id)
        ? current.filter((item) => item.id !== row.id)
        : [...current, row],
    );
  }

  return (
    <AdminModal open={open} onClose={onClose} title="选择课堂作业" wide>
      <div className="space-y-3">
        <div className="relative">
          <Search
            size={15}
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--faint)]"
          />
          <input
            className="a-input pl-9"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="搜索课堂作业标题"
            autoFocus
          />
        </div>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="text-[11.5px] text-[var(--muted)]">
            已选 {selected.length} 个；添加后按选择顺序生成学习项。
          </div>
          <div className="flex gap-2">
            <Link
              href="/homeworks/new"
              target="_blank"
              className="a-btn a-btn-sm"
            >
              <Plus size={13} /> 新建课堂作业
            </Link>
            <button
              className="a-btn a-btn-sm"
              type="button"
              onClick={() => setAppliedQuery(query.trim())}
            >
              <RefreshCw size={13} /> 刷新
            </button>
          </div>
        </div>
        {error && (
          <div className="rounded-xl border border-[#f6d5d2] bg-[var(--danger-soft)] px-3 py-2 text-[12px] text-[var(--danger)]">
            {error}
          </div>
        )}
        <div className="a-card max-h-[420px] overflow-y-auto">
          {loading ? (
            <div className="grid place-items-center py-16">
              <Loader2 size={20} className="animate-spin text-[var(--primary)]" />
            </div>
          ) : rows.length === 0 ? (
            <div className="py-16 text-center text-[12px] text-[var(--faint)]">
              还没有课堂作业，请先在「课堂作业」中创建。
            </div>
          ) : (
            <table className="a-table">
              <thead>
                <tr>
                  <th className="w-10" />
                  <th>课堂作业</th>
                  <th>Unit / 章节</th>
                  <th>题目数</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => {
                  const disabled = excluded.has(row.id);
                  return (
                    <tr
                      key={row.id}
                      className={disabled ? "opacity-45" : "cursor-pointer"}
                      onClick={() => toggle(row)}
                    >
                      <td>
                        <input
                          type="checkbox"
                          className="h-4 w-4 accent-[var(--primary)]"
                          checked={selectedIds.has(row.id)}
                          disabled={disabled}
                          onChange={() => toggle(row)}
                        />
                      </td>
                      <td>
                        <div className="font-medium">{row.title}</div>
                        {disabled && (
                          <div className="text-[10.5px] text-[var(--faint)]">
                            已在计划中
                          </div>
                        )}
                      </td>
                      <td className="text-[12px] text-[var(--muted)]">
                        <div>
                          Unit {row.unit_id || "—"}
                          {row.topic_code ? ` · ${row.topic_code}` : ""}
                        </div>
                        <div className="text-[10.5px] text-[var(--faint)]">
                          {row.topic_title || "—"}
                        </div>
                      </td>
                      <td className="font-mono">{row.question_count}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
        <div className="flex justify-end gap-2 border-t border-[var(--line)] pt-3">
          <button className="a-btn" type="button" onClick={onClose}>
            取消
          </button>
          <button
            className="a-btn a-btn-primary"
            type="button"
            disabled={selected.length === 0}
            onClick={() => {
              onConfirm(selected);
              onClose();
            }}
          >
            添加 {selected.length} 个学习项
          </button>
        </div>
      </div>
    </AdminModal>
  );
}
