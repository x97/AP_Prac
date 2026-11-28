"use client";

import {
  AlertTriangle,
  CheckCircle2,
  Download,
  FileSpreadsheet,
  Loader2,
  Upload,
} from "lucide-react";
import Link from "next/link";
import { useRef, useState } from "react";

import { useAdmin, useAdminSubject } from "@/components/AdminShell";
import { ApiError, apiDownload, apiUpload } from "@/lib/api";
import type {
  SelfQuestionImportPreview,
  SelfQuestionImportResult,
} from "@/lib/types";

const MAX_FILE_BYTES = 10 * 1024 * 1024;
const PREVIEW_ROWS = 200;

const ACTION_LABEL: Record<string, string> = {
  create: "新增",
  update: "更新",
  unchanged: "无变化",
};

const ACTION_CLASS: Record<string, string> = {
  create: "a-badge a-badge-primary",
  update: "a-badge",
  unchanged: "a-badge",
};

function formatBytes(size: number) {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

function errorDetails(error: unknown): string[] {
  if (!(error instanceof ApiError)) return [];
  const details = error.details as { errors?: unknown } | undefined;
  if (!details || !Array.isArray(details.errors)) return [];
  return details.errors.map((item) => String(item));
}

export default function QuestionImportPage() {
  const admin = useAdmin();
  const { subjects, subjectId, subject, setSubjectId } = useAdminSubject();
  const canEdit = Boolean(admin?.can_edit_content);
  const enabledSubjects = subjects.filter((item) => item.enabled);

  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<SelfQuestionImportPreview | null>(null);
  const [result, setResult] = useState<SelfQuestionImportResult | null>(null);
  const [busy, setBusy] = useState<"preview" | "save" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [details, setDetails] = useState<string[]>([]);
  const [downloading, setDownloading] = useState(false);
  const [templateError, setTemplateError] = useState<string | null>(null);

  function resetImport() {
    setFile(null);
    setPreview(null);
    setResult(null);
    setError(null);
    setDetails([]);
    if (inputRef.current) inputRef.current.value = "";
  }

  function changeSubject(value: string) {
    setSubjectId(value);
    resetImport();
  }

  function pickFile(next: File | null) {
    setPreview(null);
    setResult(null);
    setError(null);
    setDetails([]);
    if (!next) {
      setFile(null);
      return;
    }
    if (!next.name.toLowerCase().endsWith(".xlsx")) {
      setFile(null);
      setError("请选择 .xlsx 文件");
      return;
    }
    if (next.size > MAX_FILE_BYTES) {
      setFile(null);
      setError("Excel 文件不能超过 10MB");
      return;
    }
    setFile(next);
  }

  async function downloadTemplate() {
    setDownloading(true);
    setTemplateError(null);
    try {
      const { blob, filename } = await apiDownload(
        "/content/questions/import/template",
      );
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filename || "自研题导入模板.xlsx";
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) {
      setTemplateError(e instanceof Error ? e.message : "下载模板失败");
    } finally {
      setDownloading(false);
    }
  }

  function formData() {
    const form = new FormData();
    if (file) form.append("file", file);
    form.append("subject", subjectId);
    return form;
  }

  async function parsePreview() {
    if (!file || busy) return;
    setBusy("preview");
    setError(null);
    setDetails([]);
    setResult(null);
    try {
      const value = await apiUpload<SelfQuestionImportPreview>(
        "/content/questions/import/preview",
        formData(),
      );
      setPreview(value);
    } catch (e) {
      setError(e instanceof Error ? e.message : "解析失败");
      setDetails(errorDetails(e));
    } finally {
      setBusy(null);
    }
  }

  async function saveImport() {
    if (!file || !preview || busy) return;
    const changes = preview.summary.create + preview.summary.update;
    if (changes === 0) return;
    if (
      !window.confirm(
        `确认把 ${changes} 道题导入「${subject?.name_zh || subjectId}」题库？`,
      )
    ) {
      return;
    }
    setBusy("save");
    setError(null);
    setDetails([]);
    try {
      const value = await apiUpload<SelfQuestionImportResult>(
        "/content/questions/import",
        formData(),
      );
      setResult(value);
    } catch (e) {
      setError(e instanceof Error ? e.message : "导入失败");
      setDetails(errorDetails(e));
    } finally {
      setBusy(null);
    }
  }

  if (!canEdit) {
    return (
      <div>
        <h1 className="text-[27px] font-semibold tracking-[-0.03em]">批量导入</h1>
        <div className="a-card mt-5 p-5 text-[13px] text-[var(--muted)]">
          当前账号没有内容编辑权限，无法导入题目。
        </div>
      </div>
    );
  }

  const changes = preview ? preview.summary.create + preview.summary.update : 0;

  return (
    <div>
      <div className="mb-5">
        <div className="text-[11px] uppercase tracking-[0.14em] text-[var(--faint)]">
          Content
        </div>
        <h1 className="mt-1 text-[27px] font-semibold tracking-[-0.03em]">
          批量导入选择题
        </h1>
        <p className="mt-1 text-[12.5px] text-[var(--muted)]">
          先选择科目，再上传自研题 Excel。解析预览确认后才会写入题库。
        </p>
      </div>

      <div className="grid gap-4 xl:grid-cols-[360px_1fr]">
        <div className="a-card h-fit p-5">
          <div className="text-[14px] font-semibold">1. 选择科目</div>
          <select
            className="a-input mt-3"
            value={subjectId}
            onChange={(event) => changeSubject(event.target.value)}
          >
            {enabledSubjects.map((item) => (
              <option key={item.subject_id} value={item.subject_id}>
                {item.name_zh}（{item.subject_id}）
              </option>
            ))}
            {enabledSubjects.length === 0 && (
              <option value={subjectId}>暂无已启用科目</option>
            )}
          </select>
          <p className="mt-2 text-[11.5px] leading-5 text-[var(--muted)]">
            题目会进入{" "}
            <code className="rounded bg-[var(--surface-2)] px-1 py-0.5">
              {subjectId}-self-question-bank
            </code>
            ，不会影响学生端试卷列表。导入后在「题目」和课堂作业选题器里，
            来源筛选选「自研题」即可单独查看。
          </p>

          <div className="mt-5 text-[14px] font-semibold">2. 上传 Excel</div>
          <input
            ref={inputRef}
            type="file"
            accept=".xlsx"
            className="hidden"
            onChange={(event) => pickFile(event.target.files?.[0] || null)}
          />
          <button
            type="button"
            className="a-btn mt-3 w-full"
            onClick={() => inputRef.current?.click()}
            disabled={busy !== null}
          >
            <FileSpreadsheet size={15} />
            {file ? "重新选择文件" : "选择 Excel 文件"}
          </button>
          {file ? (
            <div className="mt-3 rounded-xl border border-[var(--line)] bg-[var(--surface-2)] px-3 py-2.5">
              <div className="truncate text-[12.5px] font-medium">{file.name}</div>
              <div className="mt-1 text-[11px] text-[var(--faint)]">
                {formatBytes(file.size)}
              </div>
            </div>
          ) : (
            <p className="mt-2 text-[11.5px] leading-5 text-[var(--muted)]">
              使用「自研题导入模板.xlsx」。单次最多 500 道题，文件不超过 10MB。
            </p>
          )}

          <div className="mt-2 flex items-center justify-between gap-2">
            <span className="text-[11.5px] text-[var(--muted)]">没有模板？</span>
            <button
              type="button"
              className="inline-flex items-center gap-1 text-[11.5px] font-medium text-[var(--primary)] hover:underline disabled:opacity-60"
              onClick={downloadTemplate}
              disabled={downloading}
            >
              {downloading ? (
                <Loader2 size={12} className="animate-spin" />
              ) : (
                <Download size={12} />
              )}
              下载模板
            </button>
          </div>
          {templateError && (
            <div className="mt-1 text-[11px] text-[var(--danger)]">
              {templateError}
            </div>
          )}

          <button
            type="button"
            className="a-btn a-btn-primary mt-4 w-full"
            onClick={parsePreview}
            disabled={!file || busy !== null}
          >
            {busy === "preview" ? (
              <Loader2 size={15} className="animate-spin" />
            ) : (
              <Upload size={15} />
            )}
            解析预览
          </button>
        </div>

        <div className="space-y-4">
          {error && (
            <div className="rounded-xl border border-[#f6d5d2] bg-[var(--danger-soft)] px-4 py-3 text-[12.5px] text-[var(--danger)]">
              <div className="flex items-center gap-2 font-medium">
                <AlertTriangle size={15} /> {error}
              </div>
              {details.length > 0 && (
                <ul className="mt-2 list-disc space-y-1 pl-5">
                  {details.slice(0, 20).map((item, index) => (
                    <li key={`${index}-${item}`}>{item}</li>
                  ))}
                  {details.length > 20 && (
                    <li>还有 {details.length - 20} 条，请修正后重新上传。</li>
                  )}
                </ul>
              )}
            </div>
          )}

          {result && (
            <div className="a-card border border-[#cce8d8] p-5">
              <div className="flex items-center gap-2 text-[15px] font-semibold text-[var(--success)]">
                <CheckCircle2 size={18} /> 导入完成
              </div>
              <div className="mt-2 text-[12.5px] text-[var(--muted)]">
                科目 {result.subject_id} · 新增 {result.summary.create} · 更新{" "}
                {result.summary.update} · 无变化 {result.summary.unchanged}
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                <Link
                  href={`/content/papers/${result.paper_id}?subject=${encodeURIComponent(result.subject_id)}`}
                  className="a-btn a-btn-primary"
                >
                  查看自研题库
                </Link>
                <Link
                  href={`/homeworks?subject=${encodeURIComponent(result.subject_id)}`}
                  className="a-btn"
                >
                  去建课堂作业
                </Link>
                <button type="button" className="a-btn" onClick={resetImport}>
                  继续导入
                </button>
              </div>
            </div>
          )}

          {!preview && !result && (
            <div className="a-card grid min-h-[260px] place-items-center p-8 text-center">
              <div>
                <FileSpreadsheet
                  size={34}
                  className="mx-auto text-[var(--faint)]"
                />
                <div className="mt-3 text-[13px] font-medium">
                  上传并解析后，这里会显示预览
                </div>
                <p className="mt-1 text-[11.5px] text-[var(--muted)]">
                  预览不会写入数据库；确认无误后再点「确认导入」。
                </p>
              </div>
            </div>
          )}

          {preview && !result && (
            <div className="a-card overflow-hidden">
              <div className="border-b border-[var(--line)] px-5 py-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="text-[15px] font-semibold">导入预览</div>
                    <div className="mt-1 text-[11.5px] text-[var(--muted)]">
                      {subject?.name_zh || preview.subject_id} ·{" "}
                      {preview.paper_title} ·{" "}
                      <code>{preview.paper_id}</code>
                      {preview.paper_exists ? "（已存在）" : "（将创建）"}
                    </div>
                  </div>
                  <span className="a-badge">{preview.summary.total} 道题</span>
                </div>
                <div className="mt-4 grid grid-cols-3 gap-2">
                  {[
                    ["新增", preview.summary.create],
                    ["更新", preview.summary.update],
                    ["无变化", preview.summary.unchanged],
                  ].map(([label, value]) => (
                    <div
                      key={String(label)}
                      className="rounded-xl border border-[var(--line)] bg-[var(--surface-2)] px-3 py-2.5"
                    >
                      <div className="text-[10.5px] text-[var(--faint)]">
                        {label}
                      </div>
                      <div className="mt-0.5 text-[18px] font-semibold">
                        {value}
                      </div>
                    </div>
                  ))}
                </div>
                {preview.warnings.length > 0 && (
                  <div className="mt-3 rounded-xl bg-[#fff8e8] px-3 py-2 text-[11.5px] leading-5 text-[#8a5a00]">
                    {preview.warnings.slice(0, 5).map((item, index) => (
                      <div key={`${index}-${item}`}>{item}</div>
                    ))}
                    {preview.warnings.length > 5 && (
                      <div>还有 {preview.warnings.length - 5} 条提示。</div>
                    )}
                  </div>
                )}
              </div>

              <div className="overflow-x-auto">
                <table className="a-table min-w-[860px]">
                  <thead>
                    <tr>
                      <th>行</th>
                      <th>状态</th>
                      <th>题号</th>
                      <th>题干</th>
                      <th>选项</th>
                      <th>答案</th>
                      <th>提示</th>
                    </tr>
                  </thead>
                  <tbody>
                    {preview.rows.slice(0, PREVIEW_ROWS).map((row) => (
                      <tr key={`${row.row_number}-${row.question_id}`}>
                        <td className="text-[var(--faint)]">{row.row_number}</td>
                        <td>
                          <span className={ACTION_CLASS[row.action]}>
                            {ACTION_LABEL[row.action] || row.action}
                          </span>
                        </td>
                        <td className="font-mono text-[11px]">{row.number}</td>
                        <td className="max-w-[420px]">
                          <div className="line-clamp-2 text-[12px]">{row.stem}</div>
                          <div className="mt-0.5 truncate font-mono text-[10px] text-[var(--faint)]">
                            {row.question_id}
                          </div>
                        </td>
                        <td>{row.option_count}</td>
                        <td className="font-mono">{row.correct_answer}</td>
                        <td className="max-w-[220px] text-[11px] text-[#8a5a00]">
                          {row.warnings.join("；") || "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[var(--line)] px-5 py-4">
                <div className="text-[11.5px] text-[var(--muted)]">
                  {preview.rows.length > PREVIEW_ROWS
                    ? `仅显示前 ${PREVIEW_ROWS} 行，共 ${preview.rows.length} 行`
                    : `共 ${preview.rows.length} 行`}
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    className="a-btn"
                    onClick={resetImport}
                    disabled={busy !== null}
                  >
                    取消
                  </button>
                  <button
                    type="button"
                    className="a-btn a-btn-primary"
                    onClick={saveImport}
                    disabled={busy !== null || changes === 0}
                  >
                    {busy === "save" ? (
                      <Loader2 size={15} className="animate-spin" />
                    ) : (
                      <CheckCircle2 size={15} />
                    )}
                    {changes === 0 ? "没有需要导入的变化" : `确认导入 ${changes} 道题`}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
