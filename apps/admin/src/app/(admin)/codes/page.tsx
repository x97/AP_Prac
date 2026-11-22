"use client";

import {
  Download,
  Eye,
  FileText,
  KeyRound,
  Loader2,
  Plus,
  Trash2,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { apiDownload, apiGet, apiPost } from "@/lib/api";
import type { ActivationCode, ActivationCodeBatch } from "@/lib/types";

type SubjectOption = { subject_id: string; name: string; name_zh: string };

function date(value: string | null) {
  if (!value) return "—";
  return new Date(value).toLocaleString("zh-CN", { hour12: false });
}

function scopeText(batch: ActivationCodeBatch) {
  if (batch.scope_type === "all") return "全部科目";
  return batch.subject_ids.join(", ");
}

function termText(batch: ActivationCodeBatch) {
  if (batch.expires_on) return `至 ${batch.expires_on}`;
  if (batch.duration_days === 365) return "1 年";
  if (batch.duration_days === 180) return "6 个月";
  if (batch.duration_days === 90) return "3 个月";
  if (batch.duration_days === 30) return "1 个月";
  if (batch.duration_days === 7) return "1 周";
  return `${batch.duration_days ?? "—"} 天`;
}

export default function CodesPage() {
  const [subjects, setSubjects] = useState<SubjectOption[]>([]);
  const [batches, setBatches] = useState<ActivationCodeBatch[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [scope, setScope] = useState<"all" | "subject">("subject");
  const [subjectId, setSubjectId] = useState("psychology");
  const [mode, setMode] = useState<"duration" | "date">("duration");
  const [durationDays, setDurationDays] = useState(365);
  const [expiresOn, setExpiresOn] = useState("");
  const [count, setCount] = useState(10);
  const [note, setNote] = useState("");

  const [expandedBatch, setExpandedBatch] = useState<string | null>(null);
  const [codes, setCodes] = useState<ActivationCode[]>([]);
  const [codesLoading, setCodesLoading] = useState(false);

  const load = useCallback(async () => {
    const [subjectData, batchData] = await Promise.all([
      apiGet<{ subjects: SubjectOption[] }>("/subjects"),
      apiGet<{ batches: ActivationCodeBatch[] }>("/codes/batches?limit=50"),
    ]);
    setSubjects(subjectData.subjects);
    setBatches(batchData.batches);
    if (
      subjectData.subjects.length > 0 &&
      !subjectData.subjects.some((item) => item.subject_id === subjectId)
    ) {
      setSubjectId(subjectData.subjects[0].subject_id);
    }
  }, [subjectId]);

  useEffect(() => {
    let alive = true;
    load()
      .catch((e: Error) => alive && setError(e.message))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [load]);

  async function downloadBatch(batchId: string) {
    const { blob, filename } = await apiDownload(`/codes/batches/${batchId}/download`);
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  async function generate(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const response = await apiPost<{
        batch: ActivationCodeBatch;
        codes: string[];
      }>("/codes/batches", {
        scope_type: scope,
        subject_id: scope === "subject" ? subjectId : undefined,
        duration_days: mode === "duration" ? durationDays : undefined,
        expires_on: mode === "date" ? expiresOn || undefined : undefined,
        count,
        note: note.trim() || undefined,
      });
      await load();
      await downloadBatch(response.batch.id);
      setNotice(
        `已生成 ${response.codes.length} 个激活码，并开始下载 ${response.batch.id}.txt`,
      );
      setNote("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "生成失败");
    } finally {
      setBusy(false);
    }
  }

  async function loadCodes(batchId: string) {
    setCodesLoading(true);
    setError(null);
    try {
      const response = await apiGet<{
        batch: ActivationCodeBatch;
        codes: ActivationCode[];
      }>(`/codes/batches/${batchId}/codes`);
      setCodes(response.codes);
    } catch (e) {
      setError(e instanceof Error ? e.message : "读取激活码失败");
    } finally {
      setCodesLoading(false);
    }
  }

  async function openCodes(batchId: string) {
    if (expandedBatch === batchId) {
      setExpandedBatch(null);
      setCodes([]);
      return;
    }
    setExpandedBatch(batchId);
    await loadCodes(batchId);
  }

  async function voidBatch(batch: ActivationCodeBatch) {
    if (!window.confirm(`作废批次 ${batch.id} 中所有未使用激活码？`)) return;
    setError(null);
    try {
      await apiPost(`/codes/batches/${batch.id}/void`);
      await load();
      if (expandedBatch === batch.id) setExpandedBatch(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "作废失败");
    }
  }

  async function voidCode(code: ActivationCode) {
    if (!window.confirm(`作废激活码 ${code.hint}？`)) return;
    setError(null);
    try {
      await apiPost(`/codes/${code.id}/void`);
      if (expandedBatch) await loadCodes(expandedBatch);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "作废失败");
    }
  }

  if (loading) {
    return (
      <div className="grid place-items-center py-24">
        <Loader2 size={24} className="animate-spin text-[var(--primary)]" />
      </div>
    );
  }

  return (
    <div>
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="text-[11px] uppercase tracking-[0.14em] text-[var(--faint)]">
            Activation codes
          </div>
          <h1 className="mt-1 text-[27px] font-semibold tracking-[-0.03em]">课程激活码</h1>
          <p className="mt-1 text-[12.5px] text-[var(--muted)]">
            批量生成科目激活码，学生登录后在「我的」或锁定内容处兑换。激活时长可叠加。
          </p>
        </div>
        <span className="a-badge">
          <KeyRound size={13} /> {batches.length} 个批次
        </span>
      </div>

      {error && (
        <div className="mb-3 rounded-xl border border-[#f6d5d2] bg-[var(--danger-soft)] px-3 py-2 text-[12px] text-[var(--danger)]">
          {error}
        </div>
      )}
      {notice && (
        <div className="mb-3 rounded-xl border border-[#cfe8d8] bg-[var(--success-soft)] px-3 py-2 text-[12px] text-[var(--success)]">
          {notice}
        </div>
      )}

      <form className="a-card mb-5 p-5" onSubmit={generate}>
        <div className="mb-4 flex items-center gap-2">
          <Plus size={16} className="text-[var(--primary)]" />
          <h2 className="text-[15px] font-semibold">生成新批次</h2>
        </div>

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <label className="block">
            <span className="text-[11px] text-[var(--muted)]">激活范围</span>
            <select
              className="a-input mt-1.5"
              value={scope}
              onChange={(event) => setScope(event.target.value as "all" | "subject")}
            >
              <option value="subject">指定科目</option>
              <option value="all">全部现有科目</option>
            </select>
          </label>

          <label className="block">
            <span className="text-[11px] text-[var(--muted)]">科目</span>
            <select
              className="a-input mt-1.5"
              value={subjectId}
              onChange={(event) => setSubjectId(event.target.value)}
              disabled={scope === "all"}
            >
              {subjects.map((subject) => (
                <option key={subject.subject_id} value={subject.subject_id}>
                  {subject.name_zh} ({subject.subject_id})
                </option>
              ))}
            </select>
          </label>

          <label className="block">
            <span className="text-[11px] text-[var(--muted)]">有效期类型</span>
            <select
              className="a-input mt-1.5"
              value={mode}
              onChange={(event) => setMode(event.target.value as "duration" | "date")}
            >
              <option value="duration">按时长叠加</option>
              <option value="date">指定到期日</option>
            </select>
          </label>

          {mode === "duration" ? (
            <label className="block">
              <span className="text-[11px] text-[var(--muted)]">有效时长</span>
              <select
                className="a-input mt-1.5"
                value={durationDays}
                onChange={(event) => setDurationDays(Number(event.target.value))}
              >
                <option value={365}>1 年</option>
                <option value={180}>6 个月</option>
                <option value={90}>3 个月</option>
                <option value={30}>1 个月</option>
                <option value={7}>1 周</option>
              </select>
            </label>
          ) : (
            <label className="block">
              <span className="text-[11px] text-[var(--muted)]">指定到期日</span>
              <input
                className="a-input mt-1.5"
                type="date"
                value={expiresOn}
                onChange={(event) => setExpiresOn(event.target.value)}
                required
              />
            </label>
          )}

          <label className="block">
            <span className="text-[11px] text-[var(--muted)]">生成数量</span>
            <input
              className="a-input mt-1.5"
              type="number"
              min={1}
              max={500}
              value={count}
              onChange={(event) => setCount(Number(event.target.value))}
              required
            />
          </label>

          <label className="block md:col-span-2 xl:col-span-3">
            <span className="text-[11px] text-[var(--muted)]">备注（可选）</span>
            <input
              className="a-input mt-1.5"
              value={note}
              onChange={(event) => setNote(event.target.value)}
              placeholder="例如：小红书 11 月活动 / 老学员续费"
              maxLength={1000}
            />
          </label>
        </div>

        <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
          <p className="text-[11px] text-[var(--faint)]">
            每个激活码只能使用一次；时长码在现有到期时间上累加，指定日期码会延长到该日期。
          </p>
          <button className="a-btn a-btn-primary" type="submit" disabled={busy}>
            {busy ? <Loader2 size={15} className="animate-spin" /> : <KeyRound size={15} />}
            {busy ? "生成中…" : "生成并下载 TXT"}
          </button>
        </div>
      </form>

      <div className="a-card overflow-hidden">
        <div className="flex items-center gap-2 border-b border-[var(--line)] px-5 py-4">
          <FileText size={16} className="text-[var(--primary)]" />
          <h2 className="text-[15px] font-semibold">批次历史</h2>
        </div>
        {batches.length === 0 ? (
          <div className="px-5 py-12 text-center text-[12.5px] text-[var(--muted)]">
            还没有生成过激活码。
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="a-table min-w-[960px]">
              <thead>
                <tr>
                  <th>批次</th>
                  <th>范围</th>
                  <th>有效期</th>
                  <th>数量</th>
                  <th>已用 / 可用</th>
                  <th>状态</th>
                  <th>创建时间</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {batches.map((batch) => (
                  <tr key={batch.id}>
                    <td>
                      <div className="font-mono text-[11px]">{batch.id.slice(0, 8)}…</div>
                      {batch.note && (
                        <div className="mt-0.5 max-w-[180px] truncate text-[10.5px] text-[var(--faint)]">
                          {batch.note}
                        </div>
                      )}
                    </td>
                    <td>{scopeText(batch)}</td>
                    <td>{termText(batch)}</td>
                    <td>{batch.count}</td>
                    <td>
                      {batch.used} / {batch.available}
                    </td>
                    <td>
                      <span
                        className={
                          batch.status === "voided"
                            ? "a-badge a-badge-danger"
                            : "a-badge a-badge-success"
                        }
                      >
                        {batch.status === "voided" ? "已作废" : "有效"}
                      </span>
                    </td>
                    <td>{date(batch.created_at)}</td>
                    <td>
                      <div className="flex flex-wrap justify-end gap-1.5">
                        <button
                          className="a-btn a-btn-sm"
                          type="button"
                          onClick={() => downloadBatch(batch.id)}
                        >
                          <Download size={12} /> TXT
                        </button>
                        <button
                          className="a-btn a-btn-sm"
                          type="button"
                          onClick={() => openCodes(batch.id)}
                        >
                          <Eye size={12} /> 明细
                        </button>
                        {batch.status !== "voided" && (
                          <button
                            className="a-btn a-btn-sm text-[var(--danger)]"
                            type="button"
                            onClick={() => voidBatch(batch)}
                          >
                            <Trash2 size={12} /> 作废
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {expandedBatch && (
        <div className="a-card mt-4 overflow-hidden">
          <div className="flex items-center justify-between gap-3 border-b border-[var(--line)] px-5 py-4">
            <h2 className="text-[14px] font-semibold">批次明细</h2>
            <div className="flex gap-2">
              <button
                className="a-btn a-btn-sm"
                type="button"
                onClick={() => downloadBatch(expandedBatch)}
              >
                <Download size={12} /> 下载 TXT
              </button>
              <button
                className="a-btn a-btn-sm"
                type="button"
                onClick={() => {
                  setExpandedBatch(null);
                  setCodes([]);
                }}
              >
                收起
              </button>
            </div>
          </div>
          {codesLoading ? (
            <div className="grid place-items-center py-12">
              <Loader2 size={20} className="animate-spin text-[var(--primary)]" />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="a-table min-w-[720px]">
                <thead>
                  <tr>
                    <th>激活码</th>
                    <th>状态</th>
                    <th>使用次数</th>
                    <th>创建时间</th>
                    <th>最近使用</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {codes.map((code) => (
                    <tr key={code.id}>
                      <td className="font-mono text-[11px]">{code.hint}</td>
                      <td>
                        <span
                          className={
                            code.status === "voided"
                              ? "a-badge a-badge-danger"
                              : code.status === "used"
                                ? "a-badge"
                                : "a-badge a-badge-success"
                          }
                        >
                          {code.status === "voided"
                            ? "已作废"
                            : code.status === "used"
                              ? "已使用"
                              : "未使用"}
                        </span>
                      </td>
                      <td>
                        {code.used_count} / {code.max_uses}
                      </td>
                      <td>{date(code.created_at)}</td>
                      <td>{date(code.last_used_at)}</td>
                      <td>
                        {code.status === "active" && code.used_count === 0 && (
                          <button
                            className="a-btn a-btn-sm text-[var(--danger)]"
                            type="button"
                            onClick={() => voidCode(code)}
                          >
                            <Trash2 size={12} /> 作废
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
