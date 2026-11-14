"use client";

import { FileText, Loader2, Search } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { useAdminSubject } from "@/components/AdminShell";
import { apiGet } from "@/lib/api";
import type { Paper } from "@/lib/types";

const TYPE_LABEL: Record<string, string> = {
  real_exam: "真题",
  mock_exam: "模拟题",
  unit_practice: "单元练习",
  practice_bundle: "练习包",
  bundle: "题包",
};

export default function PapersPage() {
  const { subjectId, subject } = useAdminSubject();
  const [papers, setPapers] = useState<Paper[]>([]);
  const [query, setQuery] = useState("");
  const [type, setType] = useState("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError(null);
    apiGet<{ papers: Paper[] }>(
      `/content/papers?subject=${encodeURIComponent(subjectId)}`,
    )
      .then((value) => {
        if (alive) setPapers(value.papers);
      })
      .catch((e: Error) => alive && setError(e.message))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [subjectId]);

  const types = useMemo(
    () => Array.from(new Set(papers.map((paper) => paper.paper_type))),
    [papers],
  );
  const filtered = papers.filter((paper) => {
    if (type !== "all" && paper.paper_type !== type) return false;
    const needle = query.trim().toLowerCase();
    if (!needle) return true;
    return (
      paper.paper_id.toLowerCase().includes(needle) ||
      (paper.title || "").toLowerCase().includes(needle) ||
      (paper.chinese_title || "").toLowerCase().includes(needle)
    );
  });

  return (
    <div>
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="text-[11px] uppercase tracking-[0.14em] text-[var(--faint)]">
            Content
          </div>
          <h1 className="mt-1 text-[27px] font-semibold tracking-[-0.03em]">试卷</h1>
          <p className="mt-1 text-[12.5px] text-[var(--muted)]">
            当前内容分类：{subject?.name || subjectId}。试卷、题目和知识点都按该科目筛选。
          </p>
        </div>
        <span className="a-badge"><FileText size={13} /> {papers.length} 套 · {subject?.name || subjectId}</span>
      </div>

      <div className="mb-4 flex flex-wrap gap-2">
        <div className="relative min-w-[240px] flex-1">
          <Search size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--faint)]" />
          <input
            className="a-input pl-9"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="搜索试卷标题或 ID"
          />
        </div>
        <select className="a-input w-auto" value={type} onChange={(event) => setType(event.target.value)}>
          <option value="all">全部类型</option>
          {types.map((value) => (
            <option key={value} value={value}>{TYPE_LABEL[value] || value}</option>
          ))}
        </select>
      </div>

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
        ) : (
          <div className="overflow-x-auto">
            <table className="a-table min-w-[900px]">
              <thead>
                <tr>
                  <th>年份</th>
                  <th>试卷</th>
                  <th>类型</th>
                  <th>题目</th>
                  <th>MCQ</th>
                  <th>FRQ</th>
                  <th>考试配置</th>
                  <th>完整性</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {filtered.map((paper) => (
                  <tr key={paper.paper_id}>
                    <td className="font-mono">{paper.year}</td>
                    <td>
                      <div className="max-w-[440px] font-medium">{paper.title || paper.paper_id}</div>
                      <div className="mt-0.5 font-mono text-[10.5px] text-[var(--faint)]">{paper.paper_id}</div>
                    </td>
                    <td><span className="a-badge">{TYPE_LABEL[paper.paper_type] || paper.paper_type}</span></td>
                    <td className="font-mono">{paper.actual_questions}</td>
                    <td className="font-mono">{paper.mcq_count}</td>
                    <td className="font-mono">{paper.frq_count}</td>
                    <td className="text-[11.5px] text-[var(--muted)]">
                      {paper.config?.mcq_count || "—"} MCQ · {paper.config?.frq_count || 0} FRQ
                      {paper.config?.format_code ? ` · ${paper.config.format_code}` : ""}
                    </td>
                    <td>
                      {paper.config?.frq_rubric_complete === 0 ? (
                        <span className="a-badge a-badge-warn">FRQ 评分不完整</span>
                      ) : paper.config?.is_complete === 0 ? (
                        <span className="a-badge a-badge-warn">配置不完整</span>
                      ) : (
                        <span className="a-badge a-badge-success">完整</span>
                      )}
                    </td>
                    <td className="text-right">
                      <Link
                        href={`/content/papers/${paper.paper_id}?subject=${encodeURIComponent(subjectId)}`}
                        className="a-btn a-btn-sm"
                      >
                        查看题目
                      </Link>
                    </td>
                  </tr>
                ))}
                {filtered.length === 0 && (
                  <tr>
                    <td colSpan={9} className="py-16 text-center text-[12px] text-[var(--faint)]">
                      没有匹配的试卷
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
