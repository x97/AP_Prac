"use client";

import {
  AlertTriangle,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Eye,
  Loader2,
  RotateCcw,
  Search,
  XCircle,
} from "lucide-react";
import { useEffect, useState } from "react";

import { useAdmin, useAdminSubject } from "@/components/AdminShell";
import { QuestionPreview } from "@/components/QuestionPreview";
import { apiGet, apiPatch } from "@/lib/api";
import type {
  AdminQuestionReport,
  AdminQuestionReportList,
} from "@/lib/types";

const LIMIT = 30;

type StatusFilter = "open" | "done" | "all";

const REASON_LABEL: Record<string, string> = {
  wrong_answer: "答案错误",
  typo: "题干/选项错误",
  bad_explanation: "解析问题",
  image_missing: "图片缺失",
  other: "其他",
};

const STATUS_LABEL: Record<string, string> = {
  open: "待处理",
  resolved: "已处理",
  ignored: "已忽略",
};

const STATUS_CLASS: Record<string, string> = {
  open: "a-badge a-badge-primary",
  resolved: "a-badge",
  ignored: "a-badge",
};

function timeLabel(value: string) {
  return new Date(value).toLocaleString("zh-CN", {
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

function reporterLabel(report: AdminQuestionReport) {
  return (
    report.reporter.nickname ||
    report.reporter.email_masked ||
    report.reporter.phone_masked ||
    "未知学生"
  );
}

export default function QuestionReportsPage() {
  const admin = useAdmin();
  const { subjectId } = useAdminSubject();
  const canEdit = Boolean(admin?.can_edit_content);
  const [status, setStatus] = useState<StatusFilter>("open");
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<AdminQuestionReportList | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionId, setActionId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [reload, setReload] = useState(0);
  const [previewId, setPreviewId] = useState<string | null>(null);

  useEffect(() => {
    setOffset(0);
  }, [subjectId, status, search]);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError(null);
    const params = new URLSearchParams({
      subject: subjectId,
      status,
      limit: String(LIMIT),
      offset: String(offset),
    });
    if (search) params.set("q", search);
    apiGet<AdminQuestionReportList>(`/question-reports?${params.toString()}`)
      .then((value) => {
        if (!alive) return;
        setData(value);
      })
      .catch((e: Error) => {
        if (alive) setError(e.message);
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [subjectId, status, search, offset, reload]);

  async function updateStatus(
    report: AdminQuestionReport,
    next: "open" | "resolved" | "ignored",
  ) {
    setActionId(report.id);
    setActionError(null);
    try {
      await apiPatch(`/question-reports/${report.id}`, { status: next });
      setReload((value) => value + 1);
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "更新失败");
    } finally {
      setActionId(null);
    }
  }

  const counts = data?.counts;
  const totalPages = data ? Math.max(1, Math.ceil(data.total / LIMIT)) : 1;
  const currentPage = Math.floor(offset / LIMIT) + 1;

  return (
    <div>
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="text-[11px] uppercase tracking-[0.14em] text-[var(--faint)]">
            Question Reports
          </div>
          <h1 className="mt-1 text-[27px] font-semibold tracking-[-0.03em]">
            题目报错
          </h1>
          <p className="mt-1 max-w-[760px] text-[12.5px] leading-6 text-[var(--muted)]">
            学生在 Web 端提交的题目报错会出现在这里。可以查看原题、学生选择和反馈，处理后标记状态。
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="a-badge a-badge-primary">
            <AlertTriangle size={13} /> 待处理 {counts?.open ?? 0}
          </span>
          <span className="a-badge">已处理 {counts?.resolved ?? 0}</span>
          <span className="a-badge">已忽略 {counts?.ignored ?? 0}</span>
        </div>
      </div>

      <div className="mb-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
        {[
          ["待处理", counts?.open ?? 0, "text-[var(--danger)]"],
          ["已处理", counts?.resolved ?? 0, "text-[var(--success)]"],
          ["已忽略", counts?.ignored ?? 0, "text-[var(--muted)]"],
          ["累计报错", counts?.total ?? 0, ""],
        ].map(([label, value, className]) => (
          <div key={String(label)} className="a-card px-4 py-3">
            <div className="text-[11px] text-[var(--faint)]">{label}</div>
            <div className={`mt-1 text-[24px] font-semibold ${className}`}>
              {value}
            </div>
          </div>
        ))}
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <div className="a-segment">
          {(
            [
              ["open", "待处理"],
              ["done", "已处理"],
              ["all", "全部"],
            ] as Array<[StatusFilter, string]>
          ).map(([value, label]) => (
            <button
              key={value}
              type="button"
              className={status === value ? "is-active" : ""}
              onClick={() => setStatus(value)}
            >
              {label}
            </button>
          ))}
        </div>
        <form
          className="flex min-w-[280px] max-w-lg flex-1 gap-2"
          onSubmit={(event) => {
            event.preventDefault();
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
              placeholder="搜索题目 ID、反馈内容或学生"
            />
          </div>
          <button className="a-btn" type="submit">
            搜索
          </button>
        </form>
      </div>

      {error && <div className="a-error mb-4">{error}</div>}
      {actionError && <div className="a-error mb-4">{actionError}</div>}

      {loading && !data ? (
        <div className="grid place-items-center py-24">
          <Loader2 size={24} className="animate-spin text-[var(--primary)]" />
        </div>
      ) : data && data.reports.length > 0 ? (
        <div className="a-card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="a-table min-w-[1280px]">
              <thead>
                <tr>
                  <th>时间</th>
                  <th>原因</th>
                  <th>状态</th>
                  <th>题目</th>
                  <th>学生选择</th>
                  <th>反馈</th>
                  <th>报告人</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {data.reports.map((report) => (
                  <tr key={report.id}>
                    <td className="whitespace-nowrap text-[11px] text-[var(--muted)]">
                      {timeLabel(report.created_at)}
                    </td>
                    <td>
                      <span className="a-badge">
                        {REASON_LABEL[report.reason] || report.reason}
                      </span>
                    </td>
                    <td>
                      <span className={STATUS_CLASS[report.status] || "a-badge"}>
                        {STATUS_LABEL[report.status] || report.status}
                      </span>
                    </td>
                    <td className="max-w-[380px]">
                      <div className="line-clamp-2 text-[12px] leading-5">
                        {report.question?.stem || "题目不在当前科目内容库"}
                      </div>
                      <div className="mt-1 flex flex-wrap items-center gap-2 text-[10.5px] text-[var(--faint)]">
                        <span className="font-mono">{report.question_id}</span>
                        {report.question && (
                          <span>
                            {report.question.section} {report.question.number}
                          </span>
                        )}
                        {report.question && (
                          <button
                            type="button"
                            className="inline-flex items-center gap-0.5 text-[var(--primary)] hover:underline"
                            onClick={() => setPreviewId(report.question_id)}
                          >
                            <Eye size={11} /> 查看原题
                          </button>
                        )}
                      </div>
                    </td>
                    <td className="whitespace-nowrap text-[11.5px]">
                      <div>学生：{report.selected_label || "—"}</div>
                      <div className="text-[var(--success)]">
                        正确：{report.question?.correct_answer || "—"}
                      </div>
                    </td>
                    <td className="max-w-[260px] text-[11.5px] leading-5 text-[var(--muted)]">
                      <div className="line-clamp-3">{report.detail || "—"}</div>
                    </td>
                    <td className="max-w-[160px]">
                      <div className="truncate text-[11.5px]">
                        {reporterLabel(report)}
                      </div>
                    </td>
                    <td>
                      {canEdit ? (
                        <div className="flex flex-wrap gap-1.5">
                          {report.status === "open" ? (
                            <>
                              <button
                                type="button"
                                className="a-btn a-btn-sm a-btn-primary"
                                disabled={actionId === report.id}
                                onClick={() => updateStatus(report, "resolved")}
                              >
                                {actionId === report.id ? (
                                  <Loader2 size={12} className="animate-spin" />
                                ) : (
                                  <CheckCircle2 size={12} />
                                )}
                                已处理
                              </button>
                              <button
                                type="button"
                                className="a-btn a-btn-sm"
                                disabled={actionId === report.id}
                                onClick={() => updateStatus(report, "ignored")}
                              >
                                <XCircle size={12} /> 忽略
                              </button>
                            </>
                          ) : (
                            <button
                              type="button"
                              className="a-btn a-btn-sm"
                              disabled={actionId === report.id}
                              onClick={() => updateStatus(report, "open")}
                            >
                              {actionId === report.id ? (
                                <Loader2 size={12} className="animate-spin" />
                              ) : (
                                <RotateCcw size={12} />
                              )}
                              重新打开
                            </button>
                          )}
                        </div>
                      ) : (
                        <span className="text-[11px] text-[var(--faint)]">
                          只读
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[var(--line)] px-4 py-3">
            <span className="text-[11.5px] text-[var(--muted)]">
              共 {data.total} 条 · 第 {currentPage} / {totalPages} 页
            </span>
            <div className="flex gap-2">
              <button
                type="button"
                className="a-btn a-btn-sm"
                disabled={offset === 0}
                onClick={() => setOffset(Math.max(0, offset - LIMIT))}
              >
                <ChevronLeft size={13} /> 上一页
              </button>
              <button
                type="button"
                className="a-btn a-btn-sm"
                disabled={offset + LIMIT >= data.total}
                onClick={() => setOffset(offset + LIMIT)}
              >
                下一页 <ChevronRight size={13} />
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div className="a-card grid min-h-[220px] place-items-center p-8 text-center">
          <div>
            <CheckCircle2
              size={34}
              className="mx-auto text-[var(--success)]"
            />
            <div className="mt-3 text-[13px] font-medium">
              {status === "open" ? "没有待处理的题目报错" : "没有符合条件的报错"}
            </div>
            <p className="mt-1 text-[11.5px] text-[var(--muted)]">
              学生在 Web 端提交报错后，会出现在这里。
            </p>
          </div>
        </div>
      )}

      <QuestionPreview
        questionId={previewId}
        subjectId={subjectId}
        onClose={() => setPreviewId(null)}
      />
    </div>
  );
}
