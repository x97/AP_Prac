"use client";

import {
  Archive,
  CheckCircle2,
  History,
  Loader2,
  Rocket,
  RotateCcw,
  UploadCloud,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { AdminModal } from "@/components/AdminModal";
import { apiGet, apiPost } from "@/lib/api";
import type { Release, ReleaseJob } from "@/lib/types";

function date(value: string | null) {
  if (!value) return "—";
  return new Date(value).toLocaleString("zh-CN", { hour12: false });
}

type ReleasesPayload = {
  active_release_id: string;
  releases: Release[];
  archived: Release[];
};

export default function ReleasesPage() {
  const [data, setData] = useState<ReleasesPayload | null>(null);
  const [jobs, setJobs] = useState<ReleaseJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [activating, setActivating] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastJob, setLastJob] = useState<ReleaseJob | null>(null);
  const [buildConfirmOpen, setBuildConfirmOpen] = useState(false);
  const [releaseAction, setReleaseAction] = useState<
    { kind: "archive" | "restore"; release: Release } | null
  >(null);
  const [actionBusy, setActionBusy] = useState(false);

  const load = useCallback(async () => {
    const [releaseData, jobData] = await Promise.all([
      apiGet<ReleasesPayload>("/releases"),
      apiGet<{ jobs: ReleaseJob[] }>("/releases/jobs?limit=20"),
    ]);
    setData(releaseData);
    setJobs(jobData.jobs);
  }, []);

  useEffect(() => {
    let alive = true;
    load()
      .catch((e: Error) => alive && setError(e.message))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [load]);

  async function build() {
    setBusy(true);
    setError(null);
    setLastJob(null);
    try {
      const response = await apiPost<{ job: ReleaseJob }>("/releases/build");
      setLastJob(response.job);
      if (response.job.status !== "succeeded") {
        setError(response.job.error || "构建失败，请查看日志");
      }
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "构建失败");
    } finally {
      setBusy(false);
    }
  }

  async function runReleaseAction() {
    if (!releaseAction) return;
    setActionBusy(true);
    setError(null);
    try {
      await apiPost(
        `/releases/${encodeURIComponent(releaseAction.release.release_id)}/${releaseAction.kind}`,
      );
      setReleaseAction(null);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "操作失败");
    } finally {
      setActionBusy(false);
    }
  }

  async function activate(releaseId: string) {
    if (
      !window.confirm(
        `将学生端切换到 ${releaseId}？\n\n切换后新请求会使用这个 release；确认内容已经校验和备份。`,
      )
    ) {
      return;
    }
    setActivating(releaseId);
    setError(null);
    try {
      await apiPost(`/releases/${encodeURIComponent(releaseId)}/activate`);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "切换失败");
    } finally {
      setActivating(null);
    }
  }

  if (loading) {
    return (
      <div className="grid place-items-center py-24">
        <Loader2 size={24} className="animate-spin text-[var(--primary)]" />
      </div>
    );
  }

  if (!data) {
    return <div className="a-card p-5 text-[13px] text-[var(--danger)]">{error}</div>;
  }

  return (
    <div>
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="text-[11px] uppercase tracking-[0.14em] text-[var(--faint)]">
            Publishing
          </div>
          <h1 className="mt-1 text-[27px] font-semibold tracking-[-0.03em]">发布</h1>
          <p className="mt-1 max-w-2xl text-[12.5px] leading-5 text-[var(--muted)]">
            从内容源构建不可变 release，校验通过后原子切换 student API 的 active release。
          </p>
        </div>
        <button
          className="a-btn a-btn-primary"
          onClick={() => setBuildConfirmOpen(true)}
          disabled={busy}
        >
          {busy ? <Loader2 size={15} className="animate-spin" /> : <UploadCloud size={15} />}
          {busy ? "构建中…" : "构建新 Release"}
        </button>
      </div>

      <AdminModal
        open={buildConfirmOpen}
        onClose={() => setBuildConfirmOpen(false)}
        title="构建新 Release？"
      >
        <div className="space-y-3 text-[13px] leading-6 text-[var(--muted)]">
          <p>
            系统会读取 <code>config/subjects/*.json</code> 中启用的科目，从
            <code>data/content/&lt;subject&gt;/&lt;subject&gt;_exam.db</code> /{" "}
            <code>&lt;subject&gt;_knowledge.db</code> 复制源库，合并成一个不可变 release，并运行完整校验。
          </p>
          <div className="rounded-xl border border-[var(--line)] bg-[var(--surface-2)] p-3 text-[12px]">
            <div className="flex items-center justify-between gap-3">
              <span>当前线上版本</span>
              <span className="break-all font-mono text-[11px]">
                {data.active_release_id}
              </span>
            </div>
          </div>
          <p className="rounded-xl border border-[#f4dfc4] bg-[var(--accent-soft)] p-3 text-[12px] text-[var(--accent)]">
            构建阶段不会影响学生端。只有构建成功并在下方点击“切换到此版本”后，新内容才会生效。
          </p>
        </div>
        <div className="mt-5 grid grid-cols-2 gap-2">
          <button className="a-btn" onClick={() => setBuildConfirmOpen(false)}>
            取消
          </button>
          <button
            className="a-btn a-btn-primary"
            onClick={() => {
              setBuildConfirmOpen(false);
              void build();
            }}
          >
            <UploadCloud size={15} /> 开始构建
          </button>
        </div>
      </AdminModal>

      {error && (
        <div className="mb-4 rounded-xl border border-[#f6d5d2] bg-[var(--danger-soft)] px-4 py-3 text-[12px] text-[var(--danger)]">
          {error}
        </div>
      )}

      {lastJob && (
        <div className="a-card mb-4 p-5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <div className="text-[11px] text-[var(--muted)]">最近构建</div>
              <div className="mt-1 font-mono text-[12px]">{lastJob.release_id}</div>
            </div>
            <span
              className={
                lastJob.status === "succeeded"
                  ? "a-badge a-badge-success"
                  : "a-badge a-badge-danger"
              }
            >
              {lastJob.status}
            </span>
          </div>
          {lastJob.log && (
            <details className="mt-3">
              <summary className="cursor-pointer text-[11.5px] text-[var(--primary)]">
                查看构建日志
              </summary>
              <pre className="mt-2 max-h-72 overflow-auto rounded-lg bg-[#111827] p-3 text-[10.5px] leading-5 text-[#d1d5db]">
                {lastJob.log}
              </pre>
            </details>
          )}
        </div>
      )}

      <div className="a-card mb-4 p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="text-[11px] text-[var(--muted)]">当前 active release</div>
            <div className="mt-1 break-all font-mono text-[12px]">
              {data.active_release_id}
            </div>
          </div>
          <span className="a-badge a-badge-success">
            <CheckCircle2 size={13} /> Active
          </span>
        </div>
      </div>

      <div className="a-card overflow-hidden">
        <div className="flex items-center gap-2 border-b border-[var(--line)] px-5 py-4">
          <Rocket size={16} className="text-[var(--primary)]" />
          <h2 className="text-[15px] font-semibold">Release 历史</h2>
        </div>
        <div className="divide-y divide-[var(--line)]">
          {data.releases.map((release) => (
            <div
              key={release.release_id}
              className="flex flex-wrap items-center justify-between gap-3 px-5 py-4"
            >
              <div className="min-w-0">
                <div className="break-all font-mono text-[12px] font-medium">
                  {release.release_id}
                </div>
                <div className="mt-1 text-[10.5px] text-[var(--faint)]">
                  {date(release.created_at)}
                </div>
                <div className="mt-1 flex flex-wrap gap-1">
                  {release.subjects.map((subject) => (
                    <span key={subject} className="a-badge">
                      {subject}
                    </span>
                  ))}
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <span className="a-badge">题目 {release.counts.questions ?? "—"}</span>
                <span className="a-badge">概念 {release.counts.concepts ?? "—"}</span>
                {release.active ? (
                  <span className="a-badge a-badge-success">
                    <CheckCircle2 size={12} /> 当前
                  </span>
                ) : (
                  <>
                    <button
                      className="a-btn a-btn-sm"
                      onClick={() => activate(release.release_id)}
                      disabled={activating !== null || actionBusy}
                    >
                      {activating === release.release_id ? (
                        <Loader2 size={13} className="animate-spin" />
                      ) : (
                        <History size={13} />
                      )}
                      切换到此版本
                    </button>
                    <button
                      className="a-btn a-btn-sm"
                      onClick={() => setReleaseAction({ kind: "archive", release })}
                      disabled={activating !== null || actionBusy}
                      title="归档后仍可从归档列表恢复"
                    >
                      <Archive size={13} /> 归档
                    </button>
                  </>
                )}
              </div>
            </div>
          ))}
          {data.releases.length === 0 && (
            <div className="py-16 text-center text-[12px] text-[var(--faint)]">
              暂无 release
            </div>
          )}
        </div>
      </div>

      <div className="a-card mt-4 overflow-hidden">
        <div className="flex items-center gap-2 border-b border-[var(--line)] px-5 py-4">
          <Archive size={16} className="text-[var(--muted)]" />
          <h2 className="text-[15px] font-semibold">已归档 Release</h2>
          <span className="a-badge">{data.archived.length}</span>
        </div>
        <div className="divide-y divide-[var(--line)]">
          {data.archived.map((release) => (
            <div
              key={release.release_id}
              className="flex flex-wrap items-center justify-between gap-3 px-5 py-4"
            >
              <div className="min-w-0">
                <div className="break-all font-mono text-[12px] font-medium">
                  {release.release_id}
                </div>
                <div className="mt-1 text-[10.5px] text-[var(--faint)]">
                  {date(release.created_at)}
                </div>
                <div className="mt-1 flex flex-wrap gap-1">
                  {release.subjects.map((subject) => (
                    <span key={subject} className="a-badge">
                      {subject}
                    </span>
                  ))}
                </div>
              </div>
              <button
                className="a-btn a-btn-sm"
                onClick={() => setReleaseAction({ kind: "restore", release })}
                disabled={actionBusy}
              >
                <RotateCcw size={13} /> 恢复
              </button>
            </div>
          ))}
          {data.archived.length === 0 && (
            <div className="py-10 text-center text-[12px] text-[var(--faint)]">
              暂无归档版本
            </div>
          )}
        </div>
      </div>

      <div className="a-card mt-4 overflow-hidden">
        <div className="border-b border-[var(--line)] px-5 py-4">
          <h2 className="text-[15px] font-semibold">构建记录</h2>
        </div>
        <div className="divide-y divide-[var(--line)]">
          {jobs.map((job) => (
            <div key={job.id} className="flex flex-wrap items-center justify-between gap-2 px-5 py-3">
              <div>
                <div className="font-mono text-[11.5px]">{job.release_id}</div>
                <div className="mt-0.5 text-[10px] text-[var(--faint)]">{date(job.created_at)}</div>
              </div>
              <span
                className={
                  job.status === "succeeded"
                    ? "a-badge a-badge-success"
                    : job.status === "failed"
                      ? "a-badge a-badge-danger"
                      : "a-badge a-badge-warn"
                }
              >
                {job.status}
              </span>
            </div>
          ))}
          {jobs.length === 0 && (
            <div className="py-12 text-center text-[12px] text-[var(--faint)]">
              还没有构建记录
            </div>
          )}
        </div>
      </div>

      <AdminModal
        open={releaseAction !== null}
        onClose={() => {
          if (!actionBusy) setReleaseAction(null);
        }}
        title={releaseAction?.kind === "restore" ? "恢复 Release？" : "归档 Release？"}
      >
        <p className="text-[13px] leading-6 text-[var(--muted)]">
          {releaseAction?.kind === "restore"
            ? "恢复后会重新出现在 Release 历史中，但不会自动切换学生端版本。"
            : "归档后该版本会从正常历史中移出，但仍保留在归档列表，可随时恢复；不会影响当前学生端版本。"}
        </p>
        <div className="mt-3 rounded-xl border border-[var(--line)] bg-[var(--surface-2)] p-3 font-mono text-[11.5px]">
          {releaseAction?.release.release_id}
        </div>
        {error && (
          <div className="mt-3 rounded-xl border border-[#f6d5d2] bg-[var(--danger-soft)] px-3 py-2 text-[12px] text-[var(--danger)]">
            {error}
          </div>
        )}
        <div className="mt-5 grid grid-cols-2 gap-2">
          <button
            className="a-btn"
            onClick={() => setReleaseAction(null)}
            disabled={actionBusy}
          >
            取消
          </button>
          <button
            className="a-btn a-btn-primary"
            onClick={runReleaseAction}
            disabled={actionBusy}
          >
            {actionBusy ? <Loader2 size={14} className="animate-spin" /> : null}
            {releaseAction?.kind === "restore" ? "恢复" : "归档"}
          </button>
        </div>
      </AdminModal>
    </div>
  );
}
