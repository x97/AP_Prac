"use client";

import { Loader2, ScrollText } from "lucide-react";
import { useEffect, useState } from "react";

import { apiGet } from "@/lib/api";
import type { AuditLog } from "@/lib/types";

function date(value: string) {
  return new Date(value).toLocaleString("zh-CN", { hour12: false });
}

export default function AuditPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    apiGet<{ logs: AuditLog[] }>("/audit?limit=100")
      .then((value) => alive && setLogs(value.logs))
      .catch((e: Error) => alive && setError(e.message))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, []);

  return (
    <div>
      <div className="mb-5">
        <div className="text-[11px] uppercase tracking-[0.14em] text-[var(--faint)]">
          Operations
        </div>
        <h1 className="mt-1 text-[27px] font-semibold tracking-[-0.03em]">审计日志</h1>
        <p className="mt-1 text-[12.5px] text-[var(--muted)]">
          管理员登录和后续内容发布操作会记录在这里。
        </p>
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
            <table className="a-table min-w-[760px]">
              <thead>
                <tr>
                  <th>时间</th>
                  <th>管理员</th>
                  <th>操作</th>
                  <th>对象</th>
                  <th>IP</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log) => (
                  <tr key={log.id}>
                    <td className="text-[11.5px] text-[var(--muted)]">{date(log.created_at)}</td>
                    <td className="font-mono text-[11.5px]">{log.admin_username || "—"}</td>
                    <td><span className="a-badge">{log.action}</span></td>
                    <td className="font-mono text-[10.5px] text-[var(--faint)]">
                      {log.target_type || "—"}{log.target_id ? ` · ${log.target_id}` : ""}
                    </td>
                    <td className="font-mono text-[10.5px] text-[var(--faint)]">{log.ip || "—"}</td>
                  </tr>
                ))}
                {logs.length === 0 && (
                  <tr>
                    <td colSpan={5} className="py-16 text-center">
                      <ScrollText size={22} className="mx-auto text-[var(--faint)]" />
                      <div className="mt-2 text-[12px] text-[var(--faint)]">暂无审计记录</div>
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
