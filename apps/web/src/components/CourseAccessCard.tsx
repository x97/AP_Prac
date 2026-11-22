"use client";

import { CheckCircle2, KeyRound, LockKeyhole, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { RedeemCodeModal } from "@/components/RedeemCodeModal";
import { apiGet } from "@/lib/api";
import { useLanguage } from "@/lib/i18n";
import type { SubjectEntitlement } from "@/lib/types";

const SUBJECT_NAMES: Record<string, string> = {
  psychology: "AP Psychology",
  statistics: "AP Statistics",
};

function formatDate(value: string | null) {
  if (!value) return "—";
  return new Date(value).toLocaleDateString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
}

export function CourseAccessCard({ embedded = false }: { embedded?: boolean }) {
  const { t } = useLanguage();
  const [items, setItems] = useState<SubjectEntitlement[] | null>(null);
  const [activeCount, setActiveCount] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);

  const load = useCallback(() => {
    apiGet<{ entitlements: SubjectEntitlement[]; active_count?: number }>(
      "/me/entitlements",
    )
      .then((response) => {
        setItems(response.entitlements);
        setActiveCount(
          response.active_count ??
            response.entitlements.filter((item) => item.active).length,
        );
        setError(null);
      })
      .catch((e: Error) => setError(e.message));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className={embedded ? "" : "card card-pad"}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-[11px] uppercase tracking-[0.1em] text-[var(--faint)]">
            {t("课程权限")}
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <h2 className="h2">{t("已激活科目")}</h2>
            <span className="badge badge-core">{t("{count} 个", { count: activeCount })}</span>
          </div>
          <p className="mt-1 text-[11.5px] text-[var(--muted)]">
            {t("这里列出你已激活的科目及有效期。即使尚未激活的科目，也有部分免费内容可以体验。")}
          </p>
        </div>
        <button type="button" className="btn btn-primary btn-sm" onClick={() => setOpen(true)}>
          <KeyRound size={13} /> {t("使用激活码")}
        </button>
      </div>

      {error && <div className="mt-3 text-[11.5px] text-[var(--danger)]">{error}</div>}

      <div className="mt-3 divide-y divide-[var(--line)]">
        {!items && (
          <div className="flex items-center gap-2 py-4 text-[12px] text-[var(--muted)]">
            <RefreshCw size={13} className="animate-spin" /> {t("正在读取课程权限…")}
          </div>
        )}
        {items
          ?.filter((item) => item.enabled || item.active)
          .map((item) => (
          <div key={item.subject_id} className="flex flex-wrap items-center justify-between gap-3 py-3">
            <div className="flex items-center gap-2.5">
              <span
                className={[
                  "grid h-8 w-8 place-items-center rounded-full",
                  item.active
                    ? "bg-[var(--success-soft)] text-[var(--success)]"
                    : "bg-[var(--surface-2)] text-[var(--faint)]",
                ].join(" ")}
              >
                {item.active ? <CheckCircle2 size={16} /> : <LockKeyhole size={15} />}
              </span>
              <div>
                <div className="text-[13px] font-medium">
                  {item.name || SUBJECT_NAMES[item.subject_id] || item.subject_id}
                  {!item.enabled && (
                    <span className="ml-2 text-[10px] text-[var(--accent)]">{t("内容暂未开放")}</span>
                  )}
                </div>
                <div className="mt-0.5 text-[11px] text-[var(--muted)]">
                  {item.active
                    ? t("已激活 · 有效期至 {date}", { date: formatDate(item.expires_at) })
                    : item.free_unit_ids.length > 0 || item.free_paper_ids.length > 0
                      ? t("未激活 · 可免费体验部分内容")
                      : t("未激活")}
                </div>
              </div>
            </div>
            <span
              className={
                item.active
                  ? "badge badge-core"
                  : "badge"
              }
            >
              {item.active ? t("已激活") : t("未激活")}
            </span>
          </div>
        ))}
      </div>

      {items && activeCount === 0 && (
        <div className="mt-3 flex flex-wrap items-center gap-1.5 text-[12px] text-[var(--muted)]">
          {t("你还没有已激活的科目。")}
          <button
            type="button"
            className="text-[var(--primary)] hover:underline"
            onClick={() => setOpen(true)}
          >
            {t("输入激活码 →")}
          </button>
        </div>
      )}

      <RedeemCodeModal
        open={open}
        onClose={() => setOpen(false)}
        onRedeemed={() => load()}
      />
    </div>
  );
}
